#!/usr/bin/env python3
"""核对工具参数中的空字符在审批前被拒绝，未启动的 CLI 不被记成可能已生效。

字符串参数携带 `\\u0000` 时，命令行参数无法构造、进程必然拒绝启动。注册表在参数
快照阶段就要拒绝它，不能让需批准的工具先消耗一轮审批再以「可能已生效」收尾。
子进程仍未启动时，CLI 层要返回独立的未启动错误码，收尾阶段据此结算为未执行并
暂停回合。除固定实现位置外，本脚本用真实注册表与执行器跑一遍这三段行为。
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
    "def _reject_unpassable_text(text: str) -> None:",
    "if any(char in text for char in _UNPASSABLE_STRING_CHARS) or any(",
    "0xD800 <= ord(char) <= 0xDFFF for char in text",
    "account(len(item) + 2)\n            _reject_unpassable_text(item)",
    "if type(key) is not str:\n                            raise ValueError\n                        _reject_unpassable_text(key)",
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
    from boss_harness import agent, session, tool_bundle, toolkit

    return agent, session, tool_bundle, toolkit


def _behaviour(checked: list[str]) -> None:
    agent, session, tool_bundle, toolkit = _load_harness()
    definition = tool_bundle.ToolDefinition(
        name="probe_tool", description="核对用工具", input_schema={
            "type": "object", "properties": {"message": {"type": "string"}},
            "required": ["message"], "additionalProperties": False},
        handler=lambda bridge, args: toolkit.ToolResult(ok=True, command="probe_tool"),
        requires_approval=True)
    registry = tool_bundle.ToolRegistry((definition,))

    try:
        registry.validate("probe_tool", {"message": "a\x00b"})
    except ValueError:
        checked.append("空字符参数在注册表被拒绝")
    else:
        raise ValueError("注册表仍接受含空字符的字符串参数")
    registry.validate("probe_tool", {"message": "正常文本"})
    checked.append("正常字符串参数通过注册表")

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


def check_tool_arguments() -> int:
    checked = []
    checked_count = _expect(SCHEMA_FRAGMENTS, _read(SCHEMA), SCHEMA)
    checked_count += _expect(CLI_FRAGMENTS, _read(CLI), CLI)
    checked_count += _expect(AGENT_FRAGMENTS, _read(AGENT), AGENT)
    _behaviour(checked)
    return checked_count + len(checked)


def main() -> int:
    try:
        checked = check_tool_arguments()
    except ValueError as error:
        print(f"工具参数边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具参数边界一致：{checked} 项空字符拒绝与未启动结算")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())