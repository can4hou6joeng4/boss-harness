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
APPLICATION = "harness/src/boss_harness/application.py"
DESKTOP = "apps/desktop/src/main/startupCheck.ts"
PROTOCOL = "packages/protocol/src/index.ts"
USER_GUIDE = "docs/USER_GUIDE.md"
SETUP_GUIDE = "SETUP.md"
ENTRY = "harness/src/boss_harness/__main__.py"
STRICT_ORDERED = (
    'parser.add_argument("--strict", action="store_true",',
    "if args.strict and not args.check:",
    'parser.error("--strict 只能与 --check 一起使用")',
    "if args.check:",
    'print(render_text(report) if args.format == "text" else json.dumps(report, ensure_ascii=False))',
    'if not report["ok"]:\n            return 2',
    'warned = any(check["status"] == "warning" for check in report["checks"])',
    "return 1 if args.strict and warned else 0",
)
STRICT_GUIDE = "存在错误仍为 2，没有错误但有警告为 1，全部通过为 0"
CONNECTION_NOTICE = "apps/desktop/src/renderer/src/data/connectionNotice.ts"
CONNECTION_SETTINGS = "apps/desktop/src/renderer/src/components/ConnectionSettings.tsx"
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}$")
CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
DESKTOP_LIMIT = re.compile(r"const MAX_TEXT_LENGTH = (\d+);")
TICKED_CODE = re.compile(r"`([A-Z][A-Z0-9_]{1,63})`")
CHECK_TITLE = re.compile(r'\["([A-Za-z][A-Za-z0-9]*)", "([^"]+)"\]')
DOC_CHECK_TABLE = "| 检查项 | 固定检查码 | 检查范围与限制 |"
SETUP_TABLE = "| 检查结果 | 让用户做什么 |"
SETUP_WILDCARD = re.compile(r"`([A-Z][A-Z0-9_]*_)\*`")
DOC_TABLES = (
    ("| 固定检查码 | 含义与处理 |", "模型配置错误码"),
    ("| 目录错误码 | 含义与处理 |", "目录错误码"),
    ("| 固定检查码 | 环境变量与处理 |", "运行参数错误码"),
)
STATUSES = frozenset({"ok", "warning", "error"})
# 自检文本会被复制到 Issue 或日志：渲染函数只允许读取已校验的报告字段。
TEXT_REPORT_KEYS = frozenset({"version", "protocolVersion", "pythonVersion", "checks"})
TEXT_CHECK_KEYS = frozenset({"name", "status", "code", "message", "hint"})
TEXT_FORBIDDEN = ("os", "sys", "open", "Path", "environ", "subprocess", "socket")
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


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else ""
    return ""


def _environment_loader_calls(node: ast.AST, calls: list[str]) -> None:
    if isinstance(node, ast.Call):
        name = _dotted(node.func)
        if name.rsplit(".", 1)[-1].endswith("from_environment"):
            calls.append(name)
    for child in ast.iter_child_nodes(node):
        _environment_loader_calls(child, calls)


def _runtime_order(tree: ast.Module, application_tree: ast.Module) -> int:
    options = _assignment(tree, "_RUNTIME_OPTIONS")
    loaders = [_dotted(entry.elts[1]) for entry in options.elts
               if isinstance(entry, ast.Tuple) and len(entry.elts) == 4]
    if not loaders or any(not loader for loader in loaders):
        raise ValueError("_RUNTIME_OPTIONS 的加载函数必须是名称或属性访问")
    application = next((node for node in ast.walk(application_tree)
                        if isinstance(node, ast.ClassDef) and node.name == "ApplicationService"), None)
    if application is None:
        raise ValueError("缺少 ApplicationService")
    init = next((node for node in application.body
                 if isinstance(node, ast.FunctionDef) and node.name == "__init__"), None)
    if init is None:
        raise ValueError("缺少 ApplicationService.__init__")
    calls: list[str] = []
    _environment_loader_calls(init, calls)
    if calls != loaders:
        raise ValueError(f"自检运行参数顺序与应用启动不一致：自检 {loaders}，启动 {calls}")
    return len(loaders)


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
    for name in ("_UNCONFIGURED_HINT", "_OPENAI_AVAILABLE_HINT", "_OPENAI_SDK_MISSING_HINT"):
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
    if returns != {"_UNCONFIGURED_HINT", "_OPENAI_AVAILABLE_HINT", "_OPENAI_SDK_MISSING_HINT"}:
        raise ValueError("_unconfigured_hint 必须只返回三条已登记的提示常量")
    return checked + 1


def _titles(tree: ast.Module, name: str) -> dict[str, str]:
    node = _assignment(tree, name)
    if not isinstance(node, ast.Dict):
        raise ValueError(f"{name} 必须是字典字面量")
    values: dict[str, str] = {}
    for key, value in zip(node.keys, node.values):
        label = _constant(key) if key is not None else None
        text = _constant(value) if value is not None else None
        if label is None or text is None:
            raise ValueError(f"{name} 的键值必须是字符串字面量")
        values[label] = text
    return values


def _text_output(tree: ast.Module, source: str, limit: int) -> int:
    """自检文本常被复制到 Issue：渲染函数只能使用报告字段，不读取环境或直接打印。"""
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "render_text"), None)
    if function is None:
        raise ValueError("缺少 render_text")
    labels = _assignment(tree, "_STATUS_TEXT")
    if not isinstance(labels, ast.Dict):
        raise ValueError("_STATUS_TEXT 必须是字典字面量")
    statuses: dict[str, str] = {}
    for key, value in zip(labels.keys, labels.values):
        name = _constant(key) if key is not None else None
        text = _constant(value) if value is not None else None
        if name is None or text is None:
            raise ValueError("_STATUS_TEXT 的键值必须是字符串字面量")
        statuses[name] = text
    if set(statuses) != STATUSES:
        raise ValueError("_STATUS_TEXT 的状态集合与桌面不一致")
    checked = sum(_validate_text(f"_STATUS_TEXT[{name}]", text, limit)
                  for name, text in statuses.items()) + 1
    titles = _titles(tree, "_CHECK_TITLES")
    checked += sum(_validate_text(f"_CHECK_TITLES[{name}]", text, limit)
                   for name, text in titles.items()) + 1
    checked += len(TEXT_FORBIDDEN)
    nodes = [node for statement in function.body for node in ast.walk(statement)]
    for node in nodes:
        if isinstance(node, ast.Name) and node.id in TEXT_FORBIDDEN:
            raise ValueError(f"render_text 不得访问 {node.id}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            raise ValueError("render_text 必须返回文本，不能直接打印")
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in {"report", "check"}):
            raise ValueError("render_text 只能按固定字段读取报告")
        if isinstance(node, ast.Subscript):
            base = node.value.id if isinstance(node.value, ast.Name) else ""
            key = _constant(node.slice) if isinstance(node.slice, ast.Constant) else None
            allowed = {"report": TEXT_REPORT_KEYS, "check": TEXT_CHECK_KEYS}.get(base)
            if key is None or allowed is None or key not in allowed:
                raise ValueError(f"render_text 读取了未登记字段 {base}[{key!r}]")
    checked += 1
    # 错误与警告并存时结论行必须同时给出警告数量；只查行为不查文案，允许等价重构。
    error_branch = next((node for node in function.body
                         if isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                         and node.test.id == "errors"), None)
    if error_branch is None:
        raise ValueError("render_text 缺少 errors 结论分支")
    if not any(isinstance(node, ast.Name) and node.id == "warnings"
               for statement in error_branch.body for node in ast.walk(statement)):
        raise ValueError("render_text 的 errors 结论分支必须同时给出 warnings 数量")
    checked += 1
    segment = ast.get_source_segment(source, function) or ""
    checked += _expect(("说明：", "建议：", "_STATUS_TEXT.get", "_CHECK_TITLES.get"), segment, "render_text")
    return checked


def _function_source(tree: ast.Module, source: str, name: str) -> str:
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == name), None)
    if function is None:
        raise ValueError(f"缺少 {name}")
    return ast.get_source_segment(source, function) or ""


def _warning_order(tree: ast.Module, source: str) -> int:
    """警告优先级写在使用指南里：更根本的问题先报，避免次要警告掩盖主因。"""
    checks = (
        ("_runtime_check", "APPROVAL_TIMEOUT_DEFAULTED", "RETRY_CONFIG_DEFAULTED"),
        ("_cli_check", "BOSS_CLI_UNAVAILABLE", "BOSS_CLI_BIN_IGNORED"),
        ("_state_check", "STATE_DIRECTORY_IN_REPO", "STATE_DIRECTORY_TILDE"),
        ("_state_check", "STATE_DIRECTORY_TILDE", "LEGACY_STATE_ENV_PRESENT"),
        ("_state_check", "LEGACY_STATE_ENV_PRESENT", "STATE_DIRECTORY_LOW_SPACE"),
    )
    for name, first, second in checks:
        segment = _function_source(tree, source, name)
        for code in (first, second):
            if code not in segment:
                raise ValueError(f"{name} 缺少 {code}")
        if segment.index(first) > segment.index(second):
            raise ValueError(f"{name} 必须先报告 {first} 再报告 {second}")
    return len(checks)


def _conclusion_fragments(tree: ast.Module) -> list[str]:
    """收集 render_text 结论文本的中文片段，作为桌面结论的对照基准。"""
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "render_text"), None)
    if function is None:
        raise ValueError("缺少 render_text")
    fragments: list[str] = []
    for node in ast.walk(function):
        if not (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "conclusion"
                        for target in node.targets)):
            continue
        for part in ast.walk(node.value):
            if isinstance(part, ast.Constant) and isinstance(part.value, str) and part.value:
                if part.value not in fragments:
                    fragments.append(part.value)
    if len(fragments) < 4 or "通过" not in fragments or not any("错误" in item for item in fragments):
        raise ValueError("render_text 的结论片段不完整")
    return fragments


def _ts_function(source: str, name: str) -> str:
    """截取桌面顶层函数源码；模板字符串里的 ${...} 花括号成对，按花括号配对即可。"""
    start = source.find(f"export function {name}(")
    if start < 0:
        raise ValueError(f"connectionNotice.ts 缺少 {name}")
    opening = source.find("{", start)
    if opening < 0:
        raise ValueError(f"{name} 缺少函数体")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(f"{name} 的函数体不完整")


def _conclusion_parity(tree: ast.Module, notice: str, component: str) -> int:
    """内核文本结论与桌面手动自检结论各写一份：措辞与计数口径必须一致。"""
    fragments = _conclusion_fragments(tree)
    conclusion = _ts_function(notice, "startupConclusion")
    missing = [fragment for fragment in fragments if fragment not in conclusion]
    if missing:
        raise ValueError(f"startupConclusion 与内核文本结论不一致，缺少片段 {missing}")
    required = ('kind !== "report"', 'return ""',
                'check.status === "error"', 'check.status === "warning"')
    missing = [item for item in required if item not in conclusion]
    if missing:
        raise ValueError(f"startupConclusion 缺少结论口径 {missing}")
    if "startupConclusion" not in component or "自检结论：" not in component:
        raise ValueError("连接设置页必须使用 startupConclusion 展示自检结论")
    if "运行于 " not in component:
        raise ValueError("连接设置页必须展示手动自检的运行时间")
    if "diagnosis: manualUnavailable" not in component:
        raise ValueError("手动自检复制必须包含不可用说明")
    return len(fragments) + len(required) + 3


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


def _report_names(tree: ast.Module) -> list[str]:
    report = next((node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "startup_report"), None)
    if report is None:
        raise ValueError("缺少 startup_report")
    checks = next((node.value for node in ast.walk(report)
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "checks"
                           for target in node.targets)), None)
    if not (isinstance(checks, ast.List) and checks.elts):
        raise ValueError("startup_report 的 checks 必须是列表字面量")
    names: list[str] = []
    for element in checks.elts:
        if not (isinstance(element, ast.Call) and isinstance(element.func, ast.Name)):
            raise ValueError("startup_report 的 checks 只允许直接调用检查函数")
        function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)
                         and node.name == element.func.id), None)
        if function is None:
            raise ValueError(f"缺少检查函数 {element.func.id}")
        literals = {_constant(node.args[0]) for node in ast.walk(function)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "_check" and len(node.args) == 5}
        if len(literals) != 1 or None in literals:
            raise ValueError(f"{element.func.id} 必须在所有分支返回同一个字面检查项名称")
        names.append(literals.pop())
    if len(names) != len(set(names)):
        raise ValueError("startup_report 的检查项名称必须唯一")
    return names


def _renderer_titles(source: str) -> list[tuple[str, str]]:
    line = next((line for line in source.splitlines() if "const CHECK_TITLES = new Map([" in line), None)
    if line is None:
        raise ValueError("connectionNotice.ts 缺少 CHECK_TITLES")
    titles = CHECK_TITLE.findall(line)
    if not titles or len({name for name, _ in titles}) != len(titles):
        raise ValueError("CHECK_TITLES 必须是非空且不重复的名称与标签对")
    return titles


def _doc_check_labels(guide: str) -> list[str]:
    lines = guide.splitlines()
    try:
        start = lines.index(DOC_CHECK_TABLE)
    except ValueError:
        raise ValueError("使用指南缺少检查项表格") from None
    labels: list[str] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        labels.append(line.strip().strip("|").split("|")[0].strip())
    if not labels:
        raise ValueError("使用指南检查项表格为空")
    return labels


def _names_consistency(tree: ast.Module, guide: str, notice: str) -> int:
    names = _report_names(tree)
    titles = _renderer_titles(notice)
    labels = _doc_check_labels(guide)
    renderer_names = [name for name, _ in titles]
    if renderer_names != names:
        raise ValueError(f"桌面 CHECK_TITLES 与内核检查项顺序不一致：内核 {names}，桌面 {renderer_names}")
    renderer_labels = [label for _, label in titles]
    if renderer_labels != labels:
        raise ValueError(f"使用指南检查项与桌面标签不一致：桌面 {renderer_labels}，文档 {labels}")
    kernel_titles = _titles(tree, "_CHECK_TITLES")
    if kernel_titles != dict(titles):
        raise ValueError(f"内核 _CHECK_TITLES 与桌面 CHECK_TITLES 不一致：内核 {kernel_titles}，桌面 {dict(titles)}")
    return len(names) * 3


def _setup_codes(emitted: set[str], setup: str) -> int:
    """安装指南的检查结果表供 Agent 对照；表内检查码必须由内核实际产出。"""
    lines = setup.splitlines()
    try:
        start = lines.index(SETUP_TABLE)
    except ValueError:
        raise ValueError("安装指南缺少检查结果表格") from None
    codes: list[str] = []
    prefixes: list[str] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cell = line.strip().strip("|").split("|")[0]
        codes.extend(TICKED_CODE.findall(cell))
        prefixes.extend(SETUP_WILDCARD.findall(cell))
    if not codes:
        raise ValueError("安装指南检查结果表格没有检查码")
    if len(codes) != len(set(codes)) or len(prefixes) != len(set(prefixes)):
        raise ValueError("安装指南检查结果表格有重复检查码")
    stale = sorted(set(codes) - emitted)
    if stale:
        raise ValueError("安装指南检查结果表格残留内核未产出的检查码：" + "、".join(stale))
    for prefix in prefixes:
        if not any(code.startswith(prefix) for code in emitted):
            raise ValueError(f"安装指南检查结果表格的通配 {prefix}* 未匹配任何内核检查码")
    return len(codes) + len(prefixes)


def _strict_exit(entry: str, guide: str) -> int:
    """严格模式只改变退出码：报告先输出，错误优先于警告，且只能与 --check 一起使用。"""
    position = -1
    for fragment in STRICT_ORDERED:
        if entry.count(fragment) != 1:
            raise ValueError(f"__main__.py 的严格模式片段缺失或重复：{fragment.splitlines()[0]}")
        found = entry.index(fragment)
        if found < position:
            raise ValueError(f"__main__.py 的严格模式片段顺序不符：{fragment.splitlines()[0]}")
        position = found
    if STRICT_GUIDE not in guide:
        raise ValueError("使用指南缺少严格模式三种退出码的说明")
    return len(STRICT_ORDERED) + 1


def _docs_codes(tree: ast.Module, config_tree: ast.Module, guide: str, setup: str) -> int:
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
    return len(emitted) + _setup_codes(emitted, setup)


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
    checked += _runtime_order(startup_tree, _parse(_read(APPLICATION), APPLICATION))
    checked += _hint_constants(startup_tree, limit)
    checked += _text_output(startup_tree, startup, limit)
    checked += _warning_order(startup_tree, startup)
    checked += _diagnostics(config_tree, limit)
    guide = _read(USER_GUIDE)
    checked += _docs_codes(startup_tree, config_tree, guide, _read(SETUP_GUIDE))
    checked += _strict_exit(_read(ENTRY), guide)
    checked += _names_consistency(startup_tree, guide, _read(CONNECTION_NOTICE))
    checked += _conclusion_parity(startup_tree, _read(CONNECTION_NOTICE), _read(CONNECTION_SETTINGS))
    return 9, guards + checked


def main() -> int:
    try:
        paths, guards = check_startup_diagnostics()
    except (ValueError, SyntaxError) as error:
        print(f"启动自检字段核对失败，{error}", file=sys.stderr)
        return 2
    print(f"启动自检字段一致：{paths} 条读取路径、{guards} 项文本、桌面解析、文档与标签防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
