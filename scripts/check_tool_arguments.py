#!/usr/bin/env python3
"""核对工具参数的 schema 规则、不可传递字符与未启动结算。

`_validate_value` 在参数进入子进程前逐条核对类型、`anyOf`、枚举、最小值、长度、格式、
数组长度、元素递归与唯一性，错误文案只点名字段路径、不回显原始取值。字符串参数携带
`\\u0000` 或孤立代理项时，命令行参数无法构造、进程必然拒绝启动：注册表在参数快照阶段
就要拒绝它，不能让需批准的工具先消耗一轮审批再以「可能已生效」收尾。子进程仍未启动时，
CLI 层要返回独立的未启动错误码，收尾阶段据此结算为未执行并暂停回合。除固定实现位置外，
本脚本用真实注册表、临时可执行脚本与执行器跑一遍这些行为。
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "harness/src/boss_harness/tool_schema.py"
CLI = "harness/src/boss_harness/tools/boss_cli.py"
AGENT = "harness/src/boss_harness/agent.py"

SCHEMA_FRAGMENTS = (
    '_UNPASSABLE_STRING_CHARS = ("\\x00",)',
    '_UNPASSABLE_TEXT_ERROR = "工具参数包含无法作为命令行参数传递的字符（如空字符或孤立代理项），请去掉后重试"',
    "class _UnpassableTextError(ValueError):",
    "def _reject_unpassable_text(text: str) -> None:",
    "if any(char in text for char in _UNPASSABLE_STRING_CHARS) or any(",
    "0xD800 <= ord(char) <= 0xDFFF for char in text",
    "raise _UnpassableTextError",
    "account(len(item) + 2)\n            _reject_unpassable_text(item)",
    "if type(key) is not str:\n                            raise ValueError\n                        _reject_unpassable_text(key)",
    "except _UnpassableTextError:",
    "raise ValueError(_UNPASSABLE_TEXT_ERROR) from None",
)
CLI_FRAGMENTS = (
    "except OSError:",
    'return failure("CLI_ERROR", "上游 CLI 不可执行，请检查 BOSS_CLI_BIN")',
    "except ValueError:",
    'return failure("CLI_ARGUMENT_ERROR", "工具参数无法作为命令行参数传递，CLI 未启动；本次操作未发出，请修正参数后重新发起新回合。")',
)
AGENT_FRAGMENTS = (
    'unstarted = (result.error or {}).get("code") == "CLI_ARGUMENT_ERROR"',
    'if not result.ok and (pause or unstarted',
    'not in {"INVALID_PARAM", "CANCELLED", "CLI_ARGUMENT_ERROR"}',
    "or prepared.handler is None or unstarted",
)
VALIDATE_FRAGMENTS = (
    "def _validate_value(key: str, value: Any, rule: dict[str, Any]) -> None:",
    'if "anyOf" in rule:',
    'raise ValueError(f"参数类型或取值无效：{key}")',
    'kind = rule.get("type")',
    'if kind is not None and type(value) is not '
    '{"string": str, "integer": int, "array": list}.get(kind):',
    'if "enum" in rule and value not in rule["enum"]:',
    'if "minimum" in rule and value < rule["minimum"]:',
    'if "minLength" in rule and len(value) < rule["minLength"]:',
    'if "pattern" in rule and re.search(rule["pattern"], value) is None:',
    'raise ValueError(f"参数格式无效：{key}")',
    'if len(value) < rule.get("minItems", 0) or '
    'len(value) > rule.get("maxItems", len(value)):',
    'for index, item in enumerate(value):\n'
    '            _validate_value(f"{key}[{index}]", item, rule["items"])',
    'if rule.get("uniqueItems") and any('
    "item in value[:index] for index, item in enumerate(value)):",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _load_harness():
    source = str(ROOT / "harness" / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from boss_harness import agent, session, tool_bundle, tool_schema, toolkit
    from boss_harness.tools import boss_cli

    return agent, boss_cli, session, tool_bundle, tool_schema, toolkit


def _expect_valid(validate, key: str, value: object, rule: dict, label: str) -> int:
    try:
        validate(key, value, rule)
    except ValueError as error:
        raise ValueError(f"{label}：合法取值被拒绝（{error}）") from None
    return 1


def _expect_invalid(validate, key: str, value: object, rule: dict, expected: str, label: str, *,
                    absent: str | None = None) -> int:
    try:
        validate(key, value, rule)
    except ValueError as error:
        text = str(error)
        if not text.startswith(expected):
            raise ValueError(f"{label}：错误文案 {text!r}，期望以 {expected!r} 开头") from None
        if absent is not None and absent in text:
            raise ValueError(f"{label}：错误文案回显了原始取值") from None
        return 1
    raise ValueError(f"{label}：未抛出 ValueError")


def _rule_checks(validate) -> int:
    checked = _expect_valid(validate, "k", "abc", {"type": "string"}, "字符串放行")
    checked += _expect_invalid(validate, "k", 1, {"type": "string"},
                               "参数类型无效：k", "字符串类型拒绝")
    checked += _expect_valid(validate, "k", 3, {"type": "integer"}, "整数放行")
    checked += _expect_invalid(validate, "k", True, {"type": "integer"},
                               "参数类型无效：k", "布尔不算整数")
    checked += _expect_invalid(validate, "k", "x", {"type": "array"},
                               "参数类型无效：k", "数组类型拒绝")
    checked += _expect_valid(validate, "k", 3.5, {}, "无类型规则放行")
    checked += _expect_valid(validate, "k", "b", {"enum": ["a", "b"]}, "枚举放行")
    checked += _expect_invalid(validate, "k", "c", {"enum": ["a", "b"]},
                               "参数取值无效：k", "枚举拒绝")
    checked += _expect_valid(validate, "k", 1, {"type": "integer", "minimum": 1},
                             "最小值边界放行")
    checked += _expect_invalid(validate, "k", 0, {"type": "integer", "minimum": 1},
                               "参数小于最小值：k", "低于最小值拒绝")
    checked += _expect_valid(validate, "k", "ab", {"type": "string", "minLength": 2},
                             "最小长度边界放行")
    checked += _expect_invalid(validate, "k", "a", {"type": "string", "minLength": 2},
                               "参数短于最小长度：k", "短于最小长度拒绝")
    checked += _expect_valid(validate, "k", "ab12",
                             {"type": "string", "pattern": r"^[a-z]+[0-9]+$"}, "格式命中放行")
    checked += _expect_invalid(validate, "k", "sentinel-secret-9",
                               {"type": "string", "pattern": r"^[a-z]+[0-9]+$"},
                               "参数格式无效：k", "格式不符拒绝", absent="sentinel-secret-9")
    checked += _expect_valid(validate, "k", [1, 2],
                             {"type": "array", "minItems": 2, "maxItems": 3,
                              "items": {"type": "integer"}}, "数组长度边界放行")
    checked += _expect_invalid(validate, "k", [1],
                               {"type": "array", "minItems": 2,
                                "items": {"type": "integer"}}, "参数数组长度无效：k",
                               "数组过短拒绝")
    checked += _expect_invalid(validate, "k", [1, 2, 3, 4],
                               {"type": "array", "maxItems": 3,
                                "items": {"type": "integer"}}, "参数数组长度无效：k",
                               "数组过长拒绝")
    checked += _expect_invalid(validate, "k", ["x", 1],
                               {"type": "array", "items": {"type": "integer"}},
                               "参数类型无效：k[0]", "元素递归拒绝并点名下标的路径")
    checked += _expect_valid(validate, "k", [1, 2],
                             {"type": "array", "items": {"type": "integer"},
                              "uniqueItems": True}, "唯一元素放行")
    checked += _expect_invalid(validate, "k", [1, 1],
                               {"type": "array", "items": {"type": "integer"},
                                "uniqueItems": True}, "参数数组包含重复值：k", "重复元素拒绝")
    checked += _expect_valid(validate, "k", 5,
                             {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                             "anyOf 第二分支放行")
    checked += _expect_invalid(validate, "k", 3.5,
                               {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                               "参数类型或取值无效：k", "anyOf 全部分支拒绝")
    return checked


def _behaviour(checked: list[str]) -> int:
    agent, boss_cli, session, tool_bundle, tool_schema, toolkit = _load_harness()
    definition = tool_bundle.ToolDefinition(
        name="probe_tool", description="核对用工具", input_schema={
            "type": "object", "properties": {"message": {"type": "string"}},
            "required": ["message"], "additionalProperties": False},
        handler=lambda bridge, args: toolkit.ToolResult(ok=True, command="probe_tool"),
        requires_approval=True)
    registry = tool_bundle.ToolRegistry((definition,))

    try:
        registry.validate("probe_tool", {"message": "a\x00b"})
    except ValueError as error:
        if str(error) != tool_schema._UNPASSABLE_TEXT_ERROR:
            raise ValueError("空字符参数没有返回点名字符类别的错误文案") from None
        checked.append("空字符参数在注册表被拒绝并点名原因")
    else:
        raise ValueError("注册表仍接受含空字符的字符串参数")
    try:
        registry.validate("probe_tool", {"message": 1})
    except ValueError as error:
        if str(error) == tool_schema._UNPASSABLE_TEXT_ERROR:
            raise ValueError("普通 schema 不符被误报为不可传递字符") from None
        checked.append("普通 schema 不符保持通用文案")
    else:
        raise ValueError("注册表接受了错误类型的字符串参数")
    registry.validate("probe_tool", {"message": "正常文本"})
    checked.append("正常字符串参数通过注册表")
    # 空字符与孤立代理项走同一条拒绝路径；合法表情符号（代理对）不得误判。
    for label, arguments in (
        ("高代理项参数", {"message": "a\ud800b"}),
        ("低代理项参数", {"message": "\udc00"}),
        ("空字符参数", {"message": "\x00"}),
    ):
        try:
            registry.validate("probe_tool", arguments)
        except ValueError as error:
            if str(error) != tool_schema._UNPASSABLE_TEXT_ERROR:
                raise ValueError(f"{label}未返回点名字符类别的错误文案") from None
            checked.append(f"{label}在注册表被拒绝")
        else:
            raise ValueError(f"注册表接受了{label}")
    registry.validate("probe_tool", {"message": "😀 正常表情"})
    checked.append("表情符号参数通过注册表")

    with tempfile.TemporaryDirectory() as directory:
        marker = Path(directory) / "ran"
        binary = Path(directory) / "boss"
        binary.write_text(
            "#!/bin/sh\n"
            f"touch '{marker}'\n"
            "printf '%s' '{\"ok\":true,\"schema_version\":\"1.0\",\"command\":\"status\","
            "\"data\":{},\"pagination\":null,\"error\":null,\"hints\":null}'\n",
            encoding="utf-8")
        binary.chmod(0o755)
        tool = boss_cli.BossCliTool(binary=str(binary))
        result = tool.call("status")
        if not result.ok or not marker.exists():
            raise ValueError("合法参数没有真正执行上游脚本")
        checked.append("合法参数执行上游脚本")
        marker.unlink()
        result = tool.call("status", "a\x00b")
        if result.ok or (result.error or {}).get("code") != "CLI_ARGUMENT_ERROR":
            raise ValueError("空字符参数没有返回未启动错误码")
        if marker.exists():
            raise ValueError("空字符参数仍在子进程层被执行")
        checked.append("空字符参数在 CLI 层未启动")

    with tempfile.TemporaryDirectory() as directory:
        store = session.SessionStore(Path(directory) / "sessions")
        thread = store.create("探针")

        def finish(code: str) -> tuple[str, bool]:
            runner = agent.TurnRunner(
                sessions=store, tool_bridge=None,
                handlers={"probe_tool": lambda bridge, args: toolkit.ToolResult(
                    ok=False, command="probe_tool", error={"code": code, "message": "探针"})},
                provider=None, config=None, notify=lambda method, params: None,
                approval_required=frozenset({"probe_tool"}))
            runner.turn_id = "turn-probe"
            runner._cancel = threading.Event()
            runner._await_approval = lambda approval_id: "approve"
            runner.execute_tool(thread["id"], "probe_tool", {"message": "正常文本"}, call_id="call-probe")
            states = [entry["payload"].get("executionState") for entry in store.read_entries(thread["id"])
                      if entry.get("type") == "item" and (entry.get("payload") or {}).get("kind") == "toolCall"]
            return states[-1], runner._blocked is not None

        if finish("CLI_ARGUMENT_ERROR") != ("not_executed", True):
            raise ValueError("未启动的 CLI 没有结算为未执行并暂停回合")
        checked.append("未启动结算为未执行并暂停")
        if finish("TOOL_ERROR") != ("outcome_unknown", True):
            raise ValueError("已派发的失败不再按结果不确定结算")
        checked.append("已派发的失败仍按结果不确定结算")
    return _rule_checks(boss_cli._validate_value)


def check_tool_arguments() -> int:
    checked = []
    checked_count = _expect(SCHEMA_FRAGMENTS, _read(SCHEMA), SCHEMA)
    checked_count += _expect(CLI_FRAGMENTS, _read(CLI), CLI)
    checked_count += _expect(AGENT_FRAGMENTS, _read(AGENT), AGENT)
    checked_count += _expect(VALIDATE_FRAGMENTS, _read(CLI), CLI)
    checked_count += _behaviour(checked)
    return checked_count + len(checked)


def main() -> int:
    try:
        checked = check_tool_arguments()
    except ValueError as error:
        print(f"工具参数边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具参数边界一致：{checked} 项 schema 规则、不可传递字符与未启动结算")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())