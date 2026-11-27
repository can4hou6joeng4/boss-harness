#!/usr/bin/env python3
"""核对内核默认工具允许清单的静态边界，并实际执行参数与信封校验。"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS_SOURCE = ROOT / "harness/src/boss_harness/tools/boss_cli.py"
PROCESS_IO_SOURCE = ROOT / "harness/src/boss_harness/process_io.py"
CONTEXT_SOURCE = ROOT / "harness/src/boss_harness/context.py"
TOOL_RESULTS_SOURCE = ROOT / "harness/src/boss_harness/tool_results.py"
BUNDLE_SOURCE = ROOT / "harness/src/boss_harness/tools/bundle.py"
HARNESS_PACKAGE = ROOT / "harness/src/boss_harness"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.toolkit import ToolResult  # noqa: E402
from boss_harness.tools import boss_cli as boss_cli_module  # noqa: E402
from boss_harness.tools.boss_cli import (  # noqa: E402
    BROWSER_SOURCE_ENV,
    TOOLS,
    _decode_cli_envelope,
    _executable_path,
    approval_required_tools,
    binary_available,
    resolve_binary,
    resolve_browser_source_override,
    should_pause,
    tool_handlers,
    validate_arguments,
)
from boss_harness.tools.bundle import create_boss_bundle  # noqa: E402
from boss_harness.tools.commands import offline_reply  # noqa: E402
from boss_harness.tools.recruitment import compose_system_prompt  # noqa: E402
SHELL_APIS = (
    ("shell=True", "不得以 shell=True 启动子进程"),
    ("create_subprocess_shell(", "不得使用 create_subprocess_shell"),
    ("os.system(", "不得使用 os.system"),
    ("os.popen(", "不得使用 os.popen"),
)
CLI_OUTPUT_FRAGMENTS = (
    "MAX_CLI_OUTPUT_BYTES = 16 * 1024 * 1024",
    "BoundedProcessOutput(proc, stdin, MAX_CLI_OUTPUT_BYTES)",
    'return failure("CLI_OUTPUT_LIMIT"',
    "不要自动重试",
)
PROCESS_IO_FRAGMENTS = (
    "CHUNK_BYTES = 64 * 1024",
    "if self._bytes + len(chunk) > self._limit:",
    "self.overflow.set()",
    "except BrokenPipeError:",
    "self._remaining = 2 + (stdin is not None)",
)
BUNDLE_FRAGMENTS = (
    "handlers = tool_handlers()",
    "approval_required = approval_required_tools()",
    'name=spec["name"]',
    'description=spec["description"]',
    'input_schema=spec["input_schema"]',
    'requires_approval=spec["name"] in approval_required',
    "for spec in TOOLS",
)
EXPECTED_TOOLS = frozenset({
    "boss_search",
    "boss_detail",
    "boss_recommend",
    "boss_chat",
    "boss_status",
    "boss_stats",
    "boss_hr_jobs",
    "boss_hr_jobs_detail",
    "boss_hr_recommendations",
    "boss_hr_candidates",
    "boss_hr_chat",
    "boss_hr_resume",
    "boss_hr_greet",
    "boss_list_tools",
})
WRITE_TOOLS = frozenset({"boss_hr_greet"})
#: 数据目录与自检口径一致：去除首尾空白，空值或仅空白视为未设置。
DATA_DIR_FRAGMENTS = (
    'raw_dir = data_dir if data_dir is not None else os.environ.get("BOSS_CLI_DATA_DIR")',
    'self.data_dir = (raw_dir or "").strip() or None',
)
#: 业务 CLI 路径同口径：带空白的有效路径按去空白后的值采用。
BINARY_FRAGMENTS = (
    'explicit_path = (explicit or "").strip()',
    'if explicit_path and _executable_path(explicit_path):',
    'return BinaryChoice(explicit_path, "explicit")',
    'env = (os.environ.get(BINARY_ENV) or "").strip()',
    'if env and _executable_path(env):',
    'return BinaryChoice(env, "env")',
    'sibling = REPO_ROOT.parent / "boss-agent-cli" / ".venv" / "bin" / "boss"',
    'if _executable_path(str(sibling)):\n        return BinaryChoice(str(sibling), "sibling")',
    'found = which("boss")',
    'if found:\n        return BinaryChoice(found, "path")',
    'return BinaryChoice("boss", "path")',
    'return _executable_path(binary) if "/" in binary else which(binary) is not None',
)


def _literal_dict(node: ast.AST, where: str) -> dict[str, ast.AST]:
    if not isinstance(node, ast.Dict):
        raise ValueError(f"{where} 必须是字典字面量")
    fields: dict[str, ast.AST] = {}
    for key, value in zip(node.keys, node.values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ValueError(f"{where} 的键必须是字符串字面量")
        fields[key.value] = value
    return fields


def _string(fields: dict[str, ast.AST], key: str, where: str) -> str:
    node = fields.get(key)
    if (
        not isinstance(node, ast.Constant)
        or not isinstance(node.value, str)
        or not node.value.strip()
    ):
        raise ValueError(f"{where} 缺少非空字符串 {key}")
    return node.value


def _bool(fields: dict[str, ast.AST], key: str, where: str) -> bool:
    node = fields.get(key)
    if not isinstance(node, ast.Constant) or not isinstance(node.value, bool):
        raise ValueError(f"{where} 缺少布尔值 {key}")
    return node.value


def _tools_tuple(tree: ast.Module) -> ast.Tuple:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "TOOLS"
            for target in targets
        ):
            continue
        if not isinstance(node.value, ast.Tuple):
            raise ValueError("TOOLS 必须是元组字面量")
        return node.value
    raise ValueError("harness/src/boss_harness/tools/boss_cli.py 缺少 TOOLS 元组")


def _check_schema(node: ast.AST, where: str) -> None:
    fields = _literal_dict(node, f"{where} 的 input_schema")
    schema_type = fields.get("type")
    if (
        not isinstance(schema_type, ast.Constant)
        or schema_type.value != "object"
    ):
        raise ValueError(f"{where} 的 input_schema.type 必须是 object")
    properties = fields.get("properties")
    if not isinstance(properties, ast.Dict):
        raise ValueError(f"{where} 的 input_schema.properties 必须是字典字面量")
    declared: set[str] = set()
    for key in properties.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ValueError(f"{where} 的 input_schema.properties 键必须是字符串字面量")
        declared.add(key.value)
    required_node = fields.get("required")
    if not isinstance(required_node, ast.List):
        raise ValueError(f"{where} 的 input_schema.required 必须是列表字面量")
    required: list[str] = []
    for item in required_node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise ValueError(f"{where} 的 input_schema.required 只能包含字符串字面量")
        required.append(item.value)
    if len(set(required)) != len(required):
        raise ValueError(f"{where} 的 input_schema.required 不得重复")
    unknown = sorted(set(required) - declared)
    if unknown:
        raise ValueError(
            f"{where} 的 input_schema.required 含未声明属性：" + "、".join(unknown)
        )
    additional = fields.get("additionalProperties")
    if not isinstance(additional, ast.Constant) or additional.value is not False:
        raise ValueError(f"{where} 的 input_schema.additionalProperties 必须是 False")


def _frozenset_literal(node: ast.AST, where: str) -> set[str]:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Name)
        or node.func.id != "frozenset"
        or len(node.args) != 1
        or node.keywords
    ):
        raise ValueError(f"{where} 必须是 frozenset 字面量")
    items = node.args[0]
    if not isinstance(items, (ast.Set, ast.List, ast.Tuple)):
        raise ValueError(f"{where} 必须是 frozenset 字面量")
    values: set[str] = set()
    for item in items.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise ValueError(f"{where} 只能包含字符串字面量")
        values.add(item.value)
    return values


def _assigned_frozenset(path: Path, name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            continue
        return _frozenset_literal(node.value, f"{path.name} 的 {name}")
    raise ValueError(f"{path.name} 缺少 {name}")


def _write_tools_default(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        positional = node.args.posonlyargs + node.args.args
        defaults = node.args.defaults
        if not defaults:
            continue
        for argument, default in zip(positional[-len(defaults):], defaults):
            if argument.arg == "write_tools":
                return _frozenset_literal(
                    default, f"{path.name} 的 write_tools 默认值"
                )
    raise ValueError(f"{path.name} 缺少 write_tools 默认值")


def check_harness_tools() -> tuple[int, int, int, int, int, int, int, int]:
    tree = ast.parse(
        TOOLS_SOURCE.read_text(encoding="utf-8"), filename=str(TOOLS_SOURCE)
    )
    tools = _tools_tuple(tree)
    names: list[str] = []
    approval: set[str] = set()
    for index, element in enumerate(tools.elts, start=1):
        where = f"TOOLS 的第 {index} 项"
        fields = _literal_dict(element, where)
        name = _string(fields, "name", where)
        _string(fields, "description", where)
        if "handler" not in fields:
            raise ValueError(f"{where} 缺少 handler")
        if _bool(fields, "requires_approval", where):
            approval.add(name)
        schema = fields.get("input_schema")
        if schema is None:
            raise ValueError(f"{where} 缺少 input_schema")
        _check_schema(schema, where)
        names.append(name)
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError("TOOLS 工具名重复：" + "、".join(duplicates))
    if set(names) != EXPECTED_TOOLS:
        missing = sorted(EXPECTED_TOOLS - set(names))
        extra = sorted(set(names) - EXPECTED_TOOLS)
        raise ValueError(
            "TOOLS 工具名与允许清单不一致：缺少 " + ("、".join(missing) or "无")
            + "；多出 " + ("、".join(extra) or "无")
        )
    if approval != WRITE_TOOLS:
        raise ValueError(
            "TOOLS 的需批准工具应恰为 boss_hr_greet，实际为："
            + ("、".join(sorted(approval)) or "无")
        )
    write_sets = (
        ("context.py 的 _WRITE_TOOLS", _assigned_frozenset(CONTEXT_SOURCE, "_WRITE_TOOLS")),
        ("context.py 的 write_tools 默认值", _write_tools_default(CONTEXT_SOURCE)),
        (
            "tool_results.py 的 LEGACY_WRITE_TOOLS",
            _assigned_frozenset(TOOL_RESULTS_SOURCE, "LEGACY_WRITE_TOOLS"),
        ),
    )
    for label, values in write_sets:
        if values != WRITE_TOOLS:
            raise ValueError(
                f"{label} 应恰为 boss_hr_greet，实际为："
                + ("、".join(sorted(values)) or "无")
            )
    bundle_text = BUNDLE_SOURCE.read_text(encoding="utf-8")
    missing = [fragment for fragment in BUNDLE_FRAGMENTS if fragment not in bundle_text]
    if missing:
        raise ValueError(
            "bundle.py 的工具组合必须沿用 TOOLS 与审批标记："
            + "、".join(missing)
        )
    for path in sorted(HARNESS_PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token, message in SHELL_APIS:
            if token in text:
                raise ValueError(
                    f"{message}：{path.relative_to(ROOT).as_posix()}"
                )
    tools_source = TOOLS_SOURCE.read_text(encoding="utf-8")
    if "shell=False" not in tools_source:
        raise ValueError("boss_cli.py 的 subprocess.Popen 必须显式设置 shell=False")
    for fragment in DATA_DIR_FRAGMENTS:
        if fragment not in tools_source:
            raise ValueError("boss_cli.py 的业务 CLI 数据目录必须去除首尾空白并把空值视为未设置：缺少 " + fragment)
    if 'self.data_dir = data_dir or os.environ.get("BOSS_CLI_DATA_DIR")' in tools_source:
        raise ValueError("boss_cli.py 不得把未规范化的业务 CLI 数据目录原样传给上游")
    for fragment in BINARY_FRAGMENTS:
        if fragment not in tools_source:
            raise ValueError("boss_cli.py 的业务 CLI 路径必须去除首尾空白并把空值视为未设置：缺少 " + fragment)
    if "env = os.environ.get(BINARY_ENV)" in tools_source:
        raise ValueError("boss_cli.py 不得把未规范化的业务 CLI 路径原样用于查找")
    missing = [fragment for fragment in CLI_OUTPUT_FRAGMENTS if fragment not in tools_source]
    if missing:
        raise ValueError("boss_cli.py 的工具桥输出上限必须固定为 16 MiB 且超限不重试：缺少 " + "、".join(missing))
    process_io_source = PROCESS_IO_SOURCE.read_text(encoding="utf-8")
    missing = [fragment for fragment in PROCESS_IO_FRAGMENTS if fragment not in process_io_source]
    if missing:
        raise ValueError("process_io.py 必须保留分块上限、溢出标记与管道收尾：缺少 " + "、".join(missing))
    return (
        len(names),
        len(names) - len(approval),
        len(write_sets),
        len(BUNDLE_FRAGMENTS),
        len(SHELL_APIS) + 1,
        len(DATA_DIR_FRAGMENTS) + 1,
        len(BINARY_FRAGMENTS) + 1,
        len(CLI_OUTPUT_FRAGMENTS) + len(PROCESS_IO_FRAGMENTS),
    )


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"内核工具行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"内核工具行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"内核工具行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"内核工具行为变化 {label}：未抛出错误")


def _expect_raises(call, kind: type, label: str) -> int:
    try:
        call()
    except Exception as error:
        if not isinstance(error, kind):
            raise ValueError(
                f"内核工具行为变化 {label}：期望 {kind.__name__}，实际 "
                f"{type(error).__name__}") from None
        return 1
    raise ValueError(f"内核工具行为变化 {label}：未抛出错误")


def _no_error(call, label: str) -> int:
    try:
        call()
    except Exception as error:
        raise ValueError(
            f"内核工具行为变化 {label}：不应抛出 {type(error).__name__}: {error}") from None
    return 1


def _nested(depth: int) -> str:
    return "[" * depth + "]" * depth


def _result(ok: bool, code: str | None = None) -> ToolResult:
    return ToolResult(ok=ok, command="probe", error=None if code is None else {"code": code})


class _StubBridge:
    def __init__(self, available: bool, binary: str, source: str) -> None:
        self._available = available
        self.binary = binary
        self.source = source

    def available(self) -> bool:
        return self._available


def _bundle_checks() -> int:
    # 实际组装一次 ToolBundle：定义顺序、schema 快照、审批标记、校验闭包与回调
    # 都必须在组合阶段就固定，而不是只靠 bundle.py 的静态片段。
    handlers = tool_handlers()
    bundle = create_boss_bundle()
    checked = _expect_value(bundle.id, "boss", "组合 id")
    checked += _expect_value([tool.name for tool in bundle.tools], [spec["name"] for spec in TOOLS],
                             "工具顺序与名称")
    checked += _expect_value([tool.description for tool in bundle.tools],
                             [spec["description"] for spec in TOOLS], "工具描述")
    checked += _expect_value([tool.input_schema for tool in bundle.tools],
                             [spec["input_schema"] for spec in TOOLS], "schema 快照")
    checked += _expect_value(frozenset(tool.name for tool in bundle.tools if tool.requires_approval),
                             WRITE_TOOLS, "审批标记")
    checked += _expect_value([tool.name for tool in bundle.tools if tool.validate_arguments is not None],
                             [spec["name"] for spec in TOOLS], "参数校验绑定")
    checked += _expect_value(all(tool.handler is handlers[spec["name"]]
                                 for tool, spec in zip(bundle.tools, TOOLS)), True, "处理函数绑定")
    # 校验闭包必须绑定自身工具名：空参数工具接受空对象，检索工具接受合法关键词并拒绝错类型。
    status = next(tool for tool in bundle.tools if tool.name == "boss_status")
    checked += _expect_value(status.validate({}), {}, "空参数工具校验")
    search = next(tool for tool in bundle.tools if tool.name == "boss_search")
    checked += _expect_value(search.validate({"keyword": "Python"}), {"keyword": "Python"},
                             "检索工具校验")
    checked += _expect_error(lambda: search.validate({"keyword": 1}),
                             "工具参数不符合已注册的 schema", "检索工具拒绝类型")
    checked += _expect_value(bundle.system_prompt, compose_system_prompt(None), "默认系统提示")
    preamble = "自定义提示前缀"
    prefixed = create_boss_bundle(prompt_preamble=preamble)
    checked += _expect_value(prefixed.system_prompt, compose_system_prompt(preamble), "提示前缀透传")
    checked += _expect_value(preamble in prefixed.system_prompt, True, "系统提示包含前缀")
    checked += _expect_value(bundle.pause_on_result is should_pause, True, "暂停回调")
    checked += _expect_value(bundle.offline_reply is offline_reply, True, "离线回复回调")
    checked += _expect_value(bundle.describe_bridge(_StubBridge(True, "boss", "explicit")),
                             {"available": True, "binary": "boss", "binarySource": "explicit"},
                             "bridge 可用投影")
    checked += _expect_value(bundle.describe_bridge(_StubBridge(False, "/opt/boss", "path")),
                             {"available": False, "binary": "/opt/boss", "binarySource": "path"},
                             "bridge 不可用投影")
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _expect_value(_decode_cli_envelope('{"a": 1, "b": [true, null, "x"], "c": 1.5}'),
                             {"a": 1, "b": [True, None, "x"], "c": 1.5}, "合法信封")
    for label, raw in (("NaN", '{"a": NaN}'), ("Infinity", '{"a": Infinity}'),
                       ("-Infinity", '{"a": -Infinity}'), ("溢出浮点", '{"a": 1e400}')):
        checked += _expect_error(lambda: _decode_cli_envelope(raw), "JSON 数值必须有限",
                                 f"信封 {label}")
    checked += _expect_error(lambda: _decode_cli_envelope('{"a": 1, "a": 2}'),
                             "JSON 对象包含重复键", "信封重复键")
    checked += _expect_error(lambda: _decode_cli_envelope('{"a": "\\ud800"}'),
                             "JSON 字符串包含无效 Unicode 代理项", "信封孤立代理项")
    checked += _no_error(lambda: _decode_cli_envelope(_nested(65)), "信封深度边界")
    checked += _expect_error(lambda: _decode_cli_envelope(_nested(66)),
                             "JSON 嵌套层级超过限制", "信封超深嵌套")
    checked += _expect_raises(lambda: _decode_cli_envelope("not json"),
                              json.JSONDecodeError, "信封非法 JSON")

    previous = os.environ.pop(BROWSER_SOURCE_ENV, None)
    try:
        checked += _expect_value(resolve_browser_source_override(), None, "来源未设置")
        os.environ[BROWSER_SOURCE_ENV] = ""
        checked += _expect_value(resolve_browser_source_override(), None, "来源空串")
        os.environ[BROWSER_SOURCE_ENV] = "   "
        checked += _expect_value(resolve_browser_source_override(), None, "来源纯空白")
        os.environ[BROWSER_SOURCE_ENV] = " AUTO "
        checked += _expect_value(resolve_browser_source_override(), "auto", "来源大小写与空白")
        os.environ[BROWSER_SOURCE_ENV] = "auto"
        checked += _expect_value(resolve_browser_source_override("Stored-Cookie"),
                                 "stored-cookie", "显式来源覆盖环境变量")
        for value in ("auto", "existing-browser", "stored-cookie"):
            checked += _expect_value(resolve_browser_source_override(value), value,
                                     f"来源 {value}")
        for value in ("inherit", " INHERIT "):
            checked += _expect_value(resolve_browser_source_override(value), None,
                                     "显式 inherit 不覆盖")
        os.environ[BROWSER_SOURCE_ENV] = "inherit"
        checked += _expect_value(resolve_browser_source_override(), None,
                                 "环境 inherit 不覆盖")
        os.environ[BROWSER_SOURCE_ENV] = "auto"
        checked += _expect_value(resolve_browser_source_override("inherit"), None,
                                 "显式 inherit 优先于环境")
        checked += _expect_error(
            lambda: resolve_browser_source_override("cdp"),
            f"{BROWSER_SOURCE_ENV} 必须是以下值之一：auto, existing-browser, inherit, stored-cookie",
            "来源非法值")
    finally:
        if previous is None:
            os.environ.pop(BROWSER_SOURCE_ENV, None)
        else:
            os.environ[BROWSER_SOURCE_ENV] = previous

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        executable = base / "boss"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
        plain = base / "plain"
        plain.write_text("x", encoding="utf-8")
        plain.chmod(0o644)
        checked += _expect_value(_executable_path(str(executable)), True, "可执行文件")
        checked += _expect_value(_executable_path(str(plain)), False, "普通文件")
        checked += _expect_value(_executable_path(str(base)), False, "目录")
        linked = base / "linked"
        linked.symlink_to(executable)
        checked += _expect_value(_executable_path(str(linked)), True, "符号链接可执行")
        broken = base / "broken"
        broken.symlink_to(base / "missing")
        checked += _expect_value(_executable_path(str(broken)), False, "断链")
        choice = resolve_binary(f"  {executable}  ")
        checked += _expect_value((choice.path, choice.source), (str(executable), "explicit"),
                                 "显式二进制路径规范化")
        choice = resolve_binary("   ")
        checked += _expect_value(choice.source != "explicit", True, "空白显式路径不生效")
        second = base / "boss-env"
        second.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        second.chmod(0o755)
        empty_path = base / "empty-bin"
        empty_path.mkdir()
        with mock.patch.dict(os.environ,
                             {"BOSS_CLI_BIN": str(second), "PATH": str(empty_path)}):
            choice = resolve_binary(f"  {executable}  ")
        checked += _expect_value((choice.path, choice.source), (str(executable), "explicit"),
                                 "显式路径优先于环境变量")
        with mock.patch.dict(os.environ,
                             {"BOSS_CLI_BIN": f"  {second}  ", "PATH": str(empty_path)}):
            choice = resolve_binary()
        checked += _expect_value((choice.path, choice.source), (str(second), "env"),
                                 "环境变量二进制路径规范化")
        fake_root = base / "repo"
        fake_root.mkdir()
        previous_root = boss_cli_module.REPO_ROOT
        boss_cli_module.REPO_ROOT = fake_root
        try:
            with mock.patch.dict(os.environ,
                                 {"BOSS_CLI_BIN": str(plain), "PATH": str(empty_path)}):
                choice = resolve_binary()
            checked += _expect_value((choice.path, choice.source), ("boss", "path"),
                                     "不可执行的环境变量回退默认名")
            with mock.patch.dict(os.environ,
                                 {"BOSS_CLI_BIN": "   ", "PATH": str(empty_path)}):
                choice = resolve_binary()
            checked += _expect_value((choice.path, choice.source), ("boss", "path"),
                                     "空白环境变量被跳过")
            sibling_bin = base / "boss-agent-cli" / ".venv" / "bin"
            sibling_bin.mkdir(parents=True)
            sibling = sibling_bin / "boss"
            sibling.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            sibling.chmod(0o755)
            with mock.patch.dict(os.environ, {"BOSS_CLI_BIN": "", "PATH": str(empty_path)}):
                choice = resolve_binary()
            checked += _expect_value((choice.path, choice.source), (str(sibling), "sibling"),
                                     "并排上游虚拟环境")
            path_bin = base / "path-bin"
            path_bin.mkdir()
            path_boss = path_bin / "boss"
            path_boss.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path_boss.chmod(0o755)
            sibling.chmod(0o644)
            with mock.patch.dict(os.environ, {"BOSS_CLI_BIN": "", "PATH": str(path_bin)}):
                choice = resolve_binary()
            checked += _expect_value((choice.path, choice.source), (str(path_boss), "path"),
                                     "不可执行的并排候选被跳过并回退 PATH")
        finally:
            boss_cli_module.REPO_ROOT = previous_root
        checked += _expect_value((binary_available(str(executable)), binary_available(str(plain)),
                                  binary_available(str(base))), (True, False, False),
                                 "绝对路径可用性判定")
        with mock.patch.dict(os.environ, {"PATH": str(path_bin)}):
            checked += _expect_value((binary_available("boss"),
                                      binary_available("definitely-missing-boss")),
                                     (True, False), "PATH 名称可用性判定")

    for label, arguments in (
        ("未知工具", ("unknown_tool", {"x": 1})),
        ("合法检索", ("boss_search", {"keyword": "Python"})),
        ("合法筛选", ("boss_search", {"keyword": "Python", "city": "北京", "page": 2,
                                      "experience": ["应届"]})),
        ("空参数工具", ("boss_status", {})),
        ("合法推荐页", ("boss_recommend", {"page": 2})),
    ):
        checked += _expect_value(validate_arguments(*arguments), None, label)
    for label, arguments, message in (
        ("必填缺失", ("boss_search", {}), "缺少有效参数：keyword"),
        ("必填空白", ("boss_search", {"keyword": "   "}), "缺少有效参数：keyword"),
        ("额外字段", ("boss_search", {"keyword": "a", "x": 1}),
         "工具参数包含未知字段或不是对象"),
        ("非对象", ("boss_search", []), "工具参数包含未知字段或不是对象"),
        ("关键词类型", ("boss_search", {"keyword": 123}), "参数类型无效：keyword"),
        ("页码为零", ("boss_search", {"keyword": "a", "page": 0}),
         "参数小于最小值：page"),
        ("布尔页码", ("boss_search", {"keyword": "a", "page": True}),
         "参数类型无效：page"),
        ("非法城市", ("boss_search", {"keyword": "a", "city": "火星"}),
         "参数取值无效：city"),
        ("非法经验", ("boss_search", {"keyword": "a", "experience": "火星"}),
         "参数类型或取值无效：experience"),
        ("空经验数组", ("boss_search", {"keyword": "a", "experience": []}),
         "参数类型或取值无效：experience"),
        ("重复经验数组", ("boss_search", {"keyword": "a", "experience": ["应届", "应届"]}),
         "参数类型或取值无效：experience"),
        ("空工具额外字段", ("boss_status", {"x": 1}),
         "工具参数包含未知字段或不是对象"),
        ("推荐页码为零", ("boss_recommend", {"page": 0}), "参数小于最小值：page"),
    ):
        checked += _expect_error(lambda: validate_arguments(*arguments), message, label)

    names = [tool["name"] for tool in TOOLS]
    handlers = tool_handlers()
    checked += _expect_value(len(names), 14, "工具数量")
    checked += _expect_value(len(set(names)), len(names), "工具名唯一")
    checked += _expect_value(set(handlers), set(names), "处理函数覆盖")
    checked += _expect_value(all(callable(handler) for handler in handlers.values()), True,
                             "处理函数可调用")
    checked += _expect_value(approval_required_tools(), frozenset({"boss_hr_greet"}),
                             "审批工具集")

    checked += _expect_value(should_pause(_result(True, "RATE_LIMITED")), False,
                             "成功结果不暂停")
    for code in ("RATE_LIMITED", "CLI_OUTPUT_LIMIT", "CLI_CONTRACT_ERROR",
                 "ENVIRONMENT_RISK"):
        checked += _expect_value(should_pause(_result(False, code)), True, f"暂停代码 {code}")
    checked += _expect_value(should_pause(_result(False, "UNKNOWN_CODE")), False,
                             "未知错误不暂停")
    checked += _expect_value(should_pause(_result(False)), False, "无错误码不暂停")
    checked += _bundle_checks()
    return checked


def main() -> int:
    try:
        total, read_only, write_sets, bundle, shell, data_dir, binary, output_limits = check_harness_tools()
        scenarios = _behavior_checks()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"内核工具允许清单核对失败，{error}", file=sys.stderr)
        return 2
    print(
        f"内核工具允许清单一致：{total} 个工具"
        f"（{read_only} 个只读、{total - read_only} 个需批准）、"
        f"schema 边界完整、{write_sets} 处写工具集合一致、"
        f"bundle 保留 {bundle} 项审批投影、工具子进程 {shell} 项 shell 边界、"
        f"{data_dir} 项数据目录规范化与 {binary} 项业务 CLI 路径规范化、"
        f"{output_limits} 项输出上限与有界读取防护完整、{scenarios} 个行为场景"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
