#!/usr/bin/env python3
"""核对会话导出的默认脱敏与请求边界。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SOURCE = ROOT / "harness/src/boss_harness/session_export.py"
APPLICATION_SOURCE = ROOT / "harness/src/boss_harness/application.py"
SECURITY_SOURCE = ROOT / "apps/desktop/src/main/security.ts"
DESKTOP_EXPORT = re.compile(r"const EXPORT_MAX_BYTES = (\d+(?:\s*\*\s*\d+)*);")
DESKTOP_EXPORT_CHECK = 'Buffer.byteLength(value.content, "utf8") > EXPORT_MAX_BYTES'
EXPECTED_FORMATS = ("markdown", "json", "html")
REQUEST_BOUNDARY = (
    'if not set(params) <= {"threadId", "view", "format", "includeToolResults", "maxBytes"}:'
)
DEFAULT_REDACTION = 'include_tool_results=params.get("includeToolResults", False)'
REDACTION_FRAGMENTS = (
    "from boss_harness.models.secret import redact_secrets",
    'SECRET_MARK = "[已脱敏:凭据]"',
    'ENV_MARK = "[已脱敏:环境变量]"',
    'PATH_MARK = "[已脱敏:本机路径]"',
    'PII_MARK = "[已打码:候选人信息]"',
    "redact_secrets(",
)
FORBIDDEN_WRITES = (
    "write_text(",
    "write_bytes(",
    "open(",
    "os.replace(",
    "unlink(",
    "mkdir(",
)
SENSITIVE_PIPELINE = (
    "self.secrets = sorted({value for value in secrets if isinstance(value, str) and len(value) >= 6}",
    "self.paths = sorted({value.rstrip(\"/\\\\\") for value in paths",
    'self.counts = {"secrets": 0, "environment": 0, "paths": 0, "personalInfo": 0}',
    "if depth > 32 or len(self.pii_values) >= MAX_PII_VALUES:",
    "if _normalize_key(key) in _PII_KEYS:",
    "if 2 <= len(text) <= 4_000 and text not in self.pii_values:",
    "self.pii_values.sort(key=len, reverse=True)",
    "self.counts[counter] += count",
    'self.counts["paths"] += count',
    "if value in text:",
    'self.counts["secrets"] += text.count(value)',
    "text = text.replace(value, SECRET_MARK)",
    "scrubbed = redact_secrets(text)",
    'scrubbed.count("<redacted>")',
    'scrubbed.replace("<redacted>", SECRET_MARK)',
    "text = self._sub(_TOKEN_PATTERNS[0], SECRET_MARK, text, \"secrets\")",
    "text = self._sub(_TOKEN_PATTERNS[1],",
    "text = self._sub(_TOKEN_PATTERNS[2],",
    "text = self._sub(_KEY_PATTERN, SECRET_MARK, text, \"secrets\")",
    "text = self._sub(_URL_USERINFO,",
    "text = self._sub(_ENV_ASSIGNMENT,",
    "for pattern in self.path_patterns:",
    "text = self._sub_paths(_ABSOLUTE_PATH, text)",
    "text = self._sub_paths(_SINGLE_SEGMENT_PATH, text)",
    "return self._sub(_TOKEN_PATTERNS[3], SECRET_MARK, text, \"secrets\")",
    "for value in self.pii_values:",
    'self.counts["personalInfo"] += text.count(value)',
    "text = text.replace(value, PII_MARK)",
    "text = self._sub(_PII_PATTERNS[0], PII_MARK, text, \"personalInfo\")",
    "text = self._sub(_PII_PATTERNS[1], PII_MARK, text, \"personalInfo\")",
    "text = self._sub(_PII_PATTERNS[2], PII_MARK, text, \"personalInfo\")",
    "return self._sub(_PII_PATTERNS[3],",
    "return _clip(self.personal(self.sensitive(value)), limit)",
    "_PII_KEYS = frozenset({",
    "_PII_PATTERNS = (",
    "_TOKEN_PATTERNS = (",
    '_SENSITIVE_ENV = re.compile(r"(?i)(key|token|secret|password|passwd|cookie|auth|credential|session)")',
)


def _module_assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            return node.value
    raise ValueError(f"session_export.py 缺少 {name}")


def _int_constant(node: ast.AST, name: str) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_constant(node.left, name) * _int_constant(node.right, name)
    raise ValueError(f"session_export.py 的 {name} 必须是正整数常量表达式")


def _ts_product(literal: str) -> int:
    value = 1
    for part in literal.split("*"):
        value *= int(part.strip())
    return value


def _method_source(tree: ast.Module, source: str, method_name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"session_export.py 缺少 Redactor.{method_name}")


def _ordered_steps(body: str, steps: tuple[str, ...], name: str) -> None:
    positions = [body.find(fragment) for fragment in steps]
    missing = [fragment for fragment, position in zip(steps, positions) if position < 0]
    if missing:
        raise ValueError(f"{name} 缺少脱敏步骤：" + "、".join(missing))
    if positions != sorted(positions):
        raise ValueError(f"{name} 的脱敏步骤顺序被改变")


def _check_sensitive_pipeline(tree: ast.Module, source: str) -> int:
    _ordered_steps(_method_source(tree, source, "sensitive"), (
        "if value in text:",
        "scrubbed = redact_secrets(text)",
        "text = self._sub(_TOKEN_PATTERNS[0],",
        "text = self._sub(_ENV_ASSIGNMENT,",
        "for pattern in self.path_patterns:",
        "text = self._sub_paths(_ABSOLUTE_PATH, text)",
        "return self._sub(_TOKEN_PATTERNS[3],",
    ), "sensitive()")
    _ordered_steps(_method_source(tree, source, "personal"), (
        "for value in self.pii_values:",
        "text = text.replace(value, PII_MARK)",
        "text = self._sub(_PII_PATTERNS[0],",
        "return self._sub(_PII_PATTERNS[3],",
    ), "personal()")
    missing = [fragment for fragment in SENSITIVE_PIPELINE if fragment not in source]
    if missing:
        raise ValueError("会话导出脱敏管线缺少：" + "、".join(missing))
    return len(SENSITIVE_PIPELINE) + 2


def check_export_privacy() -> int:
    export_text = EXPORT_SOURCE.read_text(encoding="utf-8")
    application_text = APPLICATION_SOURCE.read_text(encoding="utf-8")
    security_text = SECURITY_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(export_text, filename=str(EXPORT_SOURCE))
    formats = _module_assignment(tree, "EXPORT_FORMATS")
    values = (
        tuple(
            item.value
            for item in formats.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )
        if isinstance(formats, ast.Tuple)
        else ()
    )
    if (
        not isinstance(formats, ast.Tuple)
        or len(formats.elts) != len(EXPECTED_FORMATS)
        or values != EXPECTED_FORMATS
    ):
        raise ValueError(
            "session_export.py 的 EXPORT_FORMATS 应恰为 markdown / json / html"
        )
    minimum = _int_constant(
        _module_assignment(tree, "MIN_EXPORT_BYTES"), "MIN_EXPORT_BYTES"
    )
    default = _int_constant(
        _module_assignment(tree, "DEFAULT_EXPORT_BYTES"), "DEFAULT_EXPORT_BYTES"
    )
    maximum = _int_constant(
        _module_assignment(tree, "MAX_EXPORT_BYTES"), "MAX_EXPORT_BYTES"
    )
    if not minimum <= default <= maximum:
        raise ValueError(
            "会话导出字节上限必须满足 MIN_EXPORT_BYTES ≤ DEFAULT_EXPORT_BYTES ≤ MAX_EXPORT_BYTES"
        )
    if maximum >= 1024 * 1024:
        raise ValueError("会话导出 MAX_EXPORT_BYTES 必须低于传输单页上限 1 MiB")
    desktop_cap = DESKTOP_EXPORT.search(security_text)
    if desktop_cap is None:
        raise ValueError("security.ts 缺少 EXPORT_MAX_BYTES")
    desktop_maximum = _ts_product(desktop_cap.group(1))
    if desktop_maximum != maximum:
        raise ValueError(
            f"主进程 EXPORT_MAX_BYTES {desktop_maximum} 与内核 MAX_EXPORT_BYTES {maximum} 不一致"
        )
    if DESKTOP_EXPORT_CHECK not in security_text:
        raise ValueError("security.ts 必须按 UTF-8 字节数核对导出正文上限")
    if REQUEST_BOUNDARY not in application_text:
        raise ValueError("thread/export 的请求字段白名单缺失或被改动")
    if DEFAULT_REDACTION not in application_text:
        raise ValueError("thread/export 的 includeToolResults 必须默认 False")
    missing = [
        fragment for fragment in REDACTION_FRAGMENTS if fragment not in export_text
    ]
    if missing:
        raise ValueError("会话导出缺少脱敏标记或调用：" + "、".join(missing))
    writes = [token for token in FORBIDDEN_WRITES if token in export_text]
    if writes:
        raise ValueError("session_export.py 不得触碰目标文件：" + "、".join(writes))
    pipeline = _check_sensitive_pipeline(tree, export_text)
    return 7 + pipeline


def main() -> int:
    try:
        guards = check_export_privacy()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"会话导出隐私边界核对失败，{error}", file=sys.stderr)
        return 2
    print(
        "会话导出隐私边界一致：3 种格式、请求字段与默认脱敏、"
        f"4 个脱敏标记、字节上限有序且低于 1 MiB 并与主进程一致、脱敏管线顺序与导出模块不写盘（{guards} 项）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
