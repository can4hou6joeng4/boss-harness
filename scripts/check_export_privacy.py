#!/usr/bin/env python3
"""核对会话导出的默认脱敏与请求边界。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SOURCE = ROOT / "harness/src/boss_harness/session_export.py"
APPLICATION_SOURCE = ROOT / "harness/src/boss_harness/application.py"
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


def check_export_privacy() -> int:
    export_text = EXPORT_SOURCE.read_text(encoding="utf-8")
    application_text = APPLICATION_SOURCE.read_text(encoding="utf-8")
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
    return 5


def main() -> int:
    try:
        guards = check_export_privacy()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"会话导出隐私边界核对失败，{error}", file=sys.stderr)
        return 2
    print(
        "会话导出隐私边界一致：3 种格式、请求字段与默认脱敏、"
        f"4 个脱敏标记、字节上限有序且低于 1 MiB、导出模块不写盘（{guards} 项）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
