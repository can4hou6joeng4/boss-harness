#!/usr/bin/env python3
"""核对启动自检文本与桌面解析上限的一致性，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STARTUP = "harness/src/boss_harness/startup_check.py"
CONFIG_ERRORS = "harness/src/boss_harness/models/config_errors.py"
DESKTOP = "apps/desktop/src/main/startupCheck.ts"
PROTOCOL = "packages/protocol/src/index.ts"
USER_GUIDE = "docs/USER_GUIDE.md"
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}$")
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
DESKTOP_LIMIT = re.compile(r"const MAX_TEXT_LENGTH = (\d+);")
TICKED_CODE = re.compile(r"`([A-Z][A-Z0-9_]{1,63})`")
DOC_TABLES = (
    ("| 固定检查码 | 含义与处理 |", "模型配置错误码"),
    ("| 目录错误码 | 含义与处理 |", "目录错误码"),
    ("| 固定检查码 | 环境变量与处理 |", "运行参数错误码"),
)
STATUSES = frozenset({"ok", "warning", "error"})
# 与桌面 CONTROL_PATTERN 相同的码位：C0/C1 控制字符与行分隔符。
CONTROL_RANGES = ((0x00, 0x1F), (0x7F, 0x9F))
CONTROL_POINTS = frozenset({0x2028, 0x2029})
DESKTOP_FRAGMENTS = (
    "const MAX_REPORT_BYTES = 64 * 1024;",
    "const MAX_CHECKS = 16;",
    "const CHECK_TIMEOUT_MS = 10_000;",
    "const NAME_PATTERN = /^[A-Za-z][A-Za-z0-9]{0,31}$/;",
    "const CODE_PATTERN = /^[A-Z][A-Z0-9_]{1,63}$/;",
    "const CONTROL_PATTERN = /[\\u0000-\\u001f\\u007f-\\u009f\\u2028\\u2029]/;",
    'return typeof value === "string" && value.length > 0 && value.length <= MAX_TEXT_LENGTH',
    "&& !CONTROL_PATTERN.test(value);",
    'if (typeof name !== "string" || !NAME_PATTERN.test(name)) return null;',
    'if (typeof code !== "string" || !CODE_PATTERN.test(code)) return null;',
    'if (status !== "ok" && status !== "warning" && status !== "error") return null;',
    "if (!plainText(message) || !plainText(hint)) return null;",
    "report.schemaVersion !== 1 || typeof report.ok !== \"boolean\" || !Array.isArray(report.checks)",
    "report.ok !== checks.every((entry) => entry.status !== \"error\")",
)
PROTOCOL_FRAGMENTS = (
    "export interface StartupCheckEntry {",
    "name: string;",
    'status: "ok" | "warning" | "error";',
    "code: string;",
    "message: string;",
    "hint: string;",
)
STARTUP_FRAGMENTS = (
    'return {"name": name, "status": status, "code": code, "message": message, "hint": hint}',
    '"schemaVersion": 1,',
    '"ok": all(check["status"] != "error" for check in checks),',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _parse(source: str, relative: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _constant(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return value
    raise ValueError(f"缺少顶层赋值 {name}")


def _js_length(text: str) -> int:
    """按 JavaScript 的 UTF-16 码元计数，与桌面 `value.length` 同一口径。"""
    return len(text.encode("utf-16-le")) // 2


def _validate_text(label: str, value: str, limit: int) -> int:
    if not value:
        raise ValueError(f"{label} 为空")
    if _js_length(value) > limit:
        raise ValueError(f"{label} 超过桌面 {limit} 个 UTF-16 码元的文本上限")
    for char in value:
        point = ord(char)
        if any(low <= point <= high for low, high in CONTROL_RANGES) or point in CONTROL_POINTS:
            raise ValueError(f"{label} 包含桌面拒绝的控制字符")
    return 1


def _validate_code(label: str, value: str) -> int:
    if not CODE_PATTERN.fullmatch(value):
        raise ValueError(f"{label} 不符合桌面 CODE_PATTERN：{value}")
    return 1


def _parents(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _owner(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return "<module>"


def _dynamic_allowed(owner: str, node: ast.AST, kind: str) -> bool:
    """动态文本只允许来自已单独校验的来源：配置错误诊断、运行参数表与回退提示常量。"""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "exc":
        return owner == "_model_check" and node.attr == kind
    if isinstance(node, ast.Name):
        return owner == "_runtime_check" and node.id == kind
    return (kind == "hint" and owner == "_model_check" and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == "_unconfigured_hint")


def _check_calls(tree: ast.Module, parents: dict[ast.AST, ast.AST], limit: int) -> int:
    checked = 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_check"):
            continue
        if len(node.args) != 5:
            raise ValueError("_check 必须接收名称、状态、检查码、说明与建议五个参数")
        name, status, code, message, hint = node.args
        owner = _owner(node, parents)
        name_value = _constant(name)
        if name_value is None or not NAME_PATTERN.fullmatch(name_value):
            raise ValueError(f"{owner} 的自检名称不符合桌面 NAME_PATTERN")
        status_value = _constant(status)
        if status_value not in STATUSES:
            raise ValueError(f"{owner} 的自检状态必须是 ok、warning 或 error 字面量")
        checked += 2
        for kind, argument in (("code", code), ("message", message), ("hint", hint)):
            value = _constant(argument)
            if value is not None:
                checked += (_validate_code if kind == "code" else
                            lambda label, text: _validate_text(label, text, limit))(f"{owner} 的{kind}", value)
            elif not _dynamic_allowed(owner, argument, kind):
                raise ValueError(f"{owner} 的自检 {kind} 必须是字面量或已登记的动态来源")
            else:
                checked += 1
    return checked


def _runtime_options(tree: ast.Module, limit: int) -> int:
    options = _assignment(tree, "_RUNTIME_OPTIONS")
    if not isinstance(options, ast.Tuple) or not options.elts:
        raise ValueError("_RUNTIME_OPTIONS 必须是非空元组字面量")
    checked = 0
    for entry in options.elts:
        if not isinstance(entry, ast.Tuple) or len(entry.elts) != 4:
            raise ValueError("_RUNTIME_OPTIONS 的每一项必须是四元组")
        code, message, hint = (_constant(entry.elts[0]), _constant(entry.elts[2]),
                               _constant(entry.elts[3]))
        if code is None or message is None or hint is None:
            raise ValueError("_RUNTIME_OPTIONS 的检查码、说明与建议必须是字符串字面量")
        checked += _validate_code("_RUNTIME_OPTIONS 的检查码", code)
        checked += _validate_text("_RUNTIME_OPTIONS 的说明", message, limit)
        checked += _validate_text("_RUNTIME_OPTIONS 的建议", hint, limit)
    return checked


def _diagnostics(tree: ast.Module, limit: int) -> int:
    diagnostics = _assignment(tree, "_DIAGNOSTICS")
    if not isinstance(diagnostics, ast.Dict) or not diagnostics.keys:
        raise ValueError("_DIAGNOSTICS 必须是非空字典字面量")
    codes: set[str] = set()
    checked = 0
    for key, value in zip(diagnostics.keys, diagnostics.values):
        code = _constant(key)
        if code is None or not isinstance(value, ast.Tuple) or len(value.elts) != 2:
            raise ValueError("_DIAGNOSTICS 的每一项必须是检查码与两条说明的二元组")
        message, hint = _constant(value.elts[0]), _constant(value.elts[1])
        if message is None or hint is None:
            raise ValueError("_DIAGNOSTICS 的说明与建议必须是字符串字面量")
        codes.add(code)
        checked += _validate_code("模型配置诊断码", code)
        checked += _validate_text("模型配置诊断说明", message, limit)
        checked += _validate_text("模型配置诊断建议", hint, limit)
    literal = _assignment(tree, "ModelConfigErrorCode")
    if not (isinstance(literal, ast.Subscript) and isinstance(literal.value, ast.Name)
            and literal.value.id == "Literal" and isinstance(literal.slice, ast.Tuple)):
        raise ValueError("ModelConfigErrorCode 必须是 Literal 元组")
    declared = {value.value for value in literal.slice.elts
                if isinstance(value, ast.Constant) and isinstance(value.value, str)}
    if declared != codes or len(literal.slice.elts) != len(codes):
        raise ValueError("ModelConfigErrorCode 与 _DIAGNOSTICS 的检查码不一致")
    checked += len(declared)
    return checked


def _hint_constants(tree: ast.Module, limit: int) -> int:
    checked = 0
    for name in ("_UNCONFIGURED_HINT", "_OPENAI_AVAILABLE_HINT"):
        value = _constant(_assignment(tree, name))
        if value is None:
            raise ValueError(f"{name} 必须是字符串字面量")
        checked += _validate_text(name, value, limit)
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "_unconfigured_hint"), None)
    if function is None:
        raise ValueError("缺少 _unconfigured_hint")
    returns = {node.value.id for node in ast.walk(function)
               if isinstance(node, ast.Return) and isinstance(node.value, ast.Name)}
    if returns != {"_UNCONFIGURED_HINT", "_OPENAI_AVAILABLE_HINT"}:
        raise ValueError("_unconfigured_hint 必须只返回两条已登记的提示常量")
    return checked + 1


def _literal_codes(tree: ast.Module) -> set[str]:
    codes: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_check" and len(node.args) == 5):
            code = _constant(node.args[2])
            if code is not None:
                codes.add(code)
    return codes


def _state_error_codes(tree: ast.Module) -> set[str]:
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "_state_check"), None)
    if function is None:
        raise ValueError("缺少 _state_check")
    codes: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_check":
            if len(node.args) != 5 or _constant(node.args[2]) is None:
                raise ValueError("_state_check 的检查码必须是五个参数中的字面量")
            if _constant(node.args[1]) == "error":
                codes.add(_constant(node.args[2]))
    if not codes:
        raise ValueError("_state_check 没有错误检查码")
    return codes


def _table(document: str, header: str, label: str) -> set[str]:
    lines = document.splitlines()
    try:
        start = lines.index(header)
    except ValueError:
        raise ValueError(f"使用指南缺少表格：{label}") from None
    codes: list[str] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        codes.extend(TICKED_CODE.findall(line.strip().strip("|").split("|")[0]))
    if not codes:
        raise ValueError(f"使用指南表格没有检查码：{label}")
    if len(codes) != len(set(codes)):
        raise ValueError(f"使用指南表格有重复检查码：{label}")
    return set(codes)


def _docs_codes(tree: ast.Module, config_tree: ast.Module, guide: str) -> int:
    diagnostics = _assignment(config_tree, "_DIAGNOSTICS")
    diagnostic_codes = {key.value for key in diagnostics.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)}
    options = _assignment(tree, "_RUNTIME_OPTIONS")
    runtime_codes = {entry.elts[0].value for entry in options.elts
                     if isinstance(entry, ast.Tuple) and entry.elts
                     and isinstance(entry.elts[0], ast.Constant)}
    if not diagnostic_codes or not runtime_codes:
        raise ValueError("模型配置诊断或运行参数表为空")
    tables = {
        "模型配置错误码": diagnostic_codes,
        "目录错误码": _state_error_codes(tree),
        "运行参数错误码": runtime_codes,
    }
    for header, label in DOC_TABLES:
        listed = _table(guide, header, label)
        if listed != tables[label]:
            missing = sorted(tables[label] - listed)
            stale = sorted(listed - tables[label])
            raise ValueError(f"使用指南{label}与内核不一致：缺少 {missing}，残留 {stale}")
    emitted = _literal_codes(tree) | diagnostic_codes | runtime_codes
    missing = sorted(emitted - set(TICKED_CODE.findall(guide)))
    if missing:
        raise ValueError("使用指南缺少检查码：" + "、".join(missing))
    return len(emitted)


def check_startup_diagnostics() -> tuple[int, int]:
    desktop = _read(DESKTOP)
    guards = _expect(DESKTOP_FRAGMENTS, desktop, "startupCheck.ts")
    match = DESKTOP_LIMIT.search(desktop)
    if match is None:
        raise ValueError("startupCheck.ts 缺少 MAX_TEXT_LENGTH")
    limit = int(match.group(1))
    if not 0 < limit <= 4096:
        raise ValueError("startupCheck.ts 的 MAX_TEXT_LENGTH 超出可核对范围")
    guards += 1
    guards += _expect(PROTOCOL_FRAGMENTS, _read(PROTOCOL), "协议 StartupCheckEntry")
    startup = _read(STARTUP)
    startup_tree = _parse(startup, STARTUP)
    guards += _expect(STARTUP_FRAGMENTS, startup, "startup_check.py")
    config_source = _read(CONFIG_ERRORS)
    config_tree = _parse(config_source, CONFIG_ERRORS)
    checked = _check_calls(startup_tree, _parents(startup_tree), limit)
    checked += _runtime_options(startup_tree, limit)
    checked += _hint_constants(startup_tree, limit)
    checked += _diagnostics(config_tree, limit)
    checked += _docs_codes(startup_tree, config_tree, _read(USER_GUIDE))
    return 5, guards + checked


def main() -> int:
    try:
        paths, guards = check_startup_diagnostics()
    except (ValueError, SyntaxError) as error:
        print(f"启动自检字段核对失败，{error}", file=sys.stderr)
        return 2
    print(f"启动自检字段一致：{paths} 条读取路径、{guards} 项文本、桌面解析与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
