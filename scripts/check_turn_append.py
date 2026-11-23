#!/usr/bin/env python3
"""核对回合条目的持久化与工具结算投影。

`TurnRunner.append_user` / `append_agent` 把用户与助手消息挂到最后一条记录之后，
后者只在 `emit` 时发送完成通知；`finish_tool_call` 按工具结果结算终态、来源、
重试安全（`disposition`）与模型可见预算，先持久化再通知，通知失败以
`ToolCompletionNotificationError` 上报且不回滚已写入的结果。这里按源码顺序固定
这些边界，并用临时 `SessionStore` 与真实 `TurnRunner` 执行写入与结算；不调用
模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/agent.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness import agent, toolkit  # noqa: E402
from boss_harness.session import Entry, SessionStore  # noqa: E402

APPEND_ORDER = (
    "def append_user(self, thread_id: str, text: str, **metadata: Any) -> Entry:",
    "return self.sessions.append(",
    'type="item",',
    "parent_id=self.sessions.last_entry_id(thread_id),",
    'payload={"kind": "userMessage", "text": text, "turnId": self.turn_id, **metadata},',
)
APPEND_AGENT_ORDER = (
    "def append_agent(self, thread_id: str, text: str, *, emit: bool = True) -> Entry:",
    "entry = self.sessions.append(",
    'type="item",',
    "parent_id=self.sessions.last_entry_id(thread_id),",
    'payload={"kind": "agentMessage", "text": text, "turnId": self.turn_id},',
    "if emit:",
    'self.notify(N_ITEM_COMPLETED, {"threadId": thread_id, "itemId": entry.id,',
    '"kind": "agentMessage", "text": text})',
    "return entry",
)
FINISH_ORDER = (
    "def finish_tool_call(",
    'status = "completed" if result.ok else "failed"',
    'arguments = dict((entry.payload or {}).get("toolArguments") or {})',
    "source = tool_source(thread_id, entry, name)",
    "final_state = execution_state or status",
    "disposition = disposition_for_state(final_state, write=name in self.approval_required)",
    '"toolCallId": call_id or entry.id,',
    '"resultSummary": summarize_result(result),',
    '"revises": entry.id,',
    '"errorCode": (result.error or {}).get("code"),',
    '"recoveryAction": (result.error or {}).get("recovery_action"),',
    '"executionState": final_state,',
    '"modelResult": model_result(result, source=source, item_id=entry.id,',
    "if disposition is not None:",
    'payload["disposition"] = disposition',
    "if duration_ms is not None:",
    'payload["durationMs"] = duration_ms',
    "if approval is not None:",
    'payload["approval"] = approval',
    "_, recovered = self.sessions.append_tool_revision(thread_id, revision)",
    "if self.lifecycle_hooks is not None:",
    'transport = project_item(thread_id, {"id": entry.id, **payload})',
    "self.notify(",
    "N_TOOL_CALL_COMPLETED,",
    "except Exception as exc:",
    "raise ToolCompletionNotificationError from exc",
    "return recovered",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"回合条目行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, error_type: type[BaseException], label: str) -> int:
    try:
        call()
    except error_type:
        return 1
    raise ValueError(f"回合条目行为变化 {label}：期望 {error_type.__name__}")


def _last_item(store: SessionStore, thread: str) -> dict:
    entries = store.read_entries(thread)
    return next(entry for entry in reversed(entries) if entry.get("type") == "item")


def _runner(store: SessionStore, notified: list[tuple[str, dict]]) -> agent.TurnRunner:
    runner = agent.TurnRunner(
        sessions=store, tool_bridge=None, handlers={}, provider=None, config=None,
        notify=lambda method, params: notified.append((method, params)),
        approval_required=frozenset({"boss_hr_greet"}))
    runner.turn_id = "turn-1"
    return runner


def _tool_call(store: SessionStore, thread: str, name: str = "boss_status") -> Entry:
    entry = Entry(type="item", payload={"kind": "toolCall", "toolName": name,
                                        "toolArguments": {"query": "x"}})
    store.append(thread, entry)
    return entry


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        thread = store.create("回合")["id"]
        notified: list[tuple[str, dict]] = []
        runner = _runner(store, notified)

        parent = store.last_entry_id(thread)
        user = runner.append_user(thread, "你好", source="steering", queueId="q1")
        user_record = _last_item(store, thread)
        checked += _expect_value(
            (user_record["id"], user_record.get("parentId"), user_record["payload"]),
            (user.id, parent, {"kind": "userMessage", "text": "你好", "turnId": "turn-1",
                               "source": "steering", "queueId": "q1"}), "用户条目投影")
        overridden = runner.append_user(thread, "覆盖", turnId="turn-9")
        checked += _expect_value(_last_item(store, thread)["payload"]["turnId"], "turn-9",
                                 "元数据可覆盖回合")

        notified.clear()
        replied = runner.append_agent(thread, "回答")
        agent_record = _last_item(store, thread)
        checked += _expect_value(
            (agent_record["id"], agent_record.get("parentId"), agent_record["payload"]),
            (replied.id, overridden.id,
             {"kind": "agentMessage", "text": "回答", "turnId": "turn-1"}), "助手条目投影")
        checked += _expect_value(
            notified, [("item/completed", {"threadId": thread, "itemId": replied.id,
                                           "kind": "agentMessage", "text": "回答"})],
            "助手完成通知")
        notified.clear()
        silent = runner.append_agent(thread, "静默", emit=False)
        checked += _expect_value(
            (len(notified), _last_item(store, thread).get("parentId")), (0, replied.id),
            "静默助手条目不通知")
        checked += _expect_value(silent.id, _last_item(store, thread)["id"], "静默条目返回")

        tool = _tool_call(store, thread)
        notified.clear()
        recovered = runner.finish_tool_call(
            thread, tool, "boss_status",
            toolkit.ToolResult(ok=True, command="boss_status", data={"count": 2},
                               hints={"next": "1"}),
            call_id="call-1", duration_ms=12)
        payload = _last_item(store, thread)["payload"]
        checked += _expect_value(
            (recovered, payload["status"], payload["executionState"], payload["revises"],
             payload["toolCallId"], payload["toolArguments"]),
            (False, "completed", "completed", tool.id, "call-1", {"query": "x"}), "成功结算投影")
        checked += _expect_value(
            (payload["result"], isinstance(payload["resultSummary"], str),
             isinstance(payload["modelResult"], str), payload["modelResult"].startswith("{")),
            ({"ok": True, "command": "boss_status", "data": {"count": 2},
              "pagination": None, "error": None, "hints": {"next": "1"}}, True, True, True),
            "结果与模型投影")
        checked += _expect_value(
            (payload["source"]["ref"], payload["source"]["tool"], payload["durationMs"],
             "disposition" in payload),
            (f"tool:{thread}:{tool.id}", "boss_status", 12, False), "来源与时长")
        notification = notified[0]
        checked += _expect_value(
            (notification[0], {key: notification[1][key] for key in (
                "itemId", "toolName", "status", "executionState", "ok", "error", "durationMs",
                "source", "approval")}),
            ("toolCall/completed", {"itemId": tool.id, "toolName": "boss_status",
                                    "status": "completed", "executionState": "completed",
                                    "ok": True, "error": None, "durationMs": 12,
                                    "source": payload["source"], "approval": None}),
            "完成通知字段")

        failed = _tool_call(store, thread)
        runner.finish_tool_call(
            thread, failed, "boss_status",
            toolkit.ToolResult(ok=False, command="boss_status",
                               error={"code": "TOOL_ERROR", "message": "失败",
                                      "recovery_action": "retry"}))
        failed_payload = _last_item(store, thread)["payload"]
        checked += _expect_value(
            (failed_payload["status"], failed_payload["executionState"],
             failed_payload["disposition"], failed_payload["errorCode"],
             failed_payload["recoveryAction"]),
            ("failed", "failed", {"delivery": "not_delivered", "retry": "safe"},
             "TOOL_ERROR", "retry"), "只读失败结算")

        write = _tool_call(store, thread, "boss_hr_greet")
        runner.finish_tool_call(
            thread, write, "boss_hr_greet",
            toolkit.ToolResult(ok=False, command="boss_hr_greet",
                               error={"code": "TOOL_ERROR", "message": "失败"}))
        checked += _expect_value(
            _last_item(store, thread)["payload"]["disposition"],
            {"delivery": "unknown", "retry": "unknown"}, "写工具失败结算")

        unknown = _tool_call(store, thread)
        runner.finish_tool_call(
            thread, unknown, "boss_status", toolkit.ToolResult(ok=True, command="boss_status"),
            execution_state="outcome_unknown")
        unknown_payload = _last_item(store, thread)["payload"]
        checked += _expect_value(
            (unknown_payload["status"], unknown_payload["executionState"],
             unknown_payload["disposition"]),
            ("completed", "outcome_unknown",
             {"delivery": "delivery_uncertain", "retry": "unsafe"}), "结果未知结算")

        bare = _tool_call(store, thread)
        runner.finish_tool_call(thread, bare, "boss_status",
                                toolkit.ToolResult(ok=True, command="boss_status"))
        checked += _expect_value(_last_item(store, thread)["payload"]["toolCallId"], bare.id,
                                 "缺省调用编号")

        approved = _tool_call(store, thread)
        runner.finish_tool_call(
            thread, approved, "boss_status", toolkit.ToolResult(ok=True, command="boss_status"),
            approval={"decision": "approve"})
        checked += _expect_value(_last_item(store, thread)["payload"]["approval"],
                                 {"decision": "approve"}, "审批随结算持久化")

        def boom(method: str, params: dict | None = None) -> None:
            raise RuntimeError("观察者断开")

        runner.notify = boom
        broken = _tool_call(store, thread)
        checked += _expect_error(
            lambda: runner.finish_tool_call(
                thread, broken, "boss_status", toolkit.ToolResult(ok=True, command="boss_status")),
            agent.ToolCompletionNotificationError, "通知失败上报")
        checked += _expect_value(_last_item(store, thread)["payload"]["status"], "completed",
                                 "通知失败仍已落库")
    return checked


def check_turn_append() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    user = _function(tree, source, "append_user")
    reply = _function(tree, source, "append_agent")
    finish = _function(tree, source, "finish_tool_call")
    checked = _ordered(APPEND_ORDER, user, MODULE)
    checked += _ordered(APPEND_AGENT_ORDER, reply, MODULE)
    checked += _ordered(FINISH_ORDER, finish, MODULE)
    # 助手完成通知只在 emit 分支出现一次。
    if reply.count("self.notify(") != 1 or reply.count("if emit:") != 1:
        raise ValueError(f"{MODULE} 的助手条目必须只在 emit 时通知")
    checked += 1
    # 工具结算只追加一次修订并返回恢复标记。
    if finish.count("append_tool_revision(") != 1 or finish.count("return recovered") != 1:
        raise ValueError(f"{MODULE} 的工具结算必须只追加一次修订")
    checked += 1
    # 重试安全只由执行事实推导，不按错误码猜测。
    if "disposition_for_state(" not in finish or "result.ok" in finish.split(
            "disposition_for_state(")[1].split(")", 1)[0]:
        raise ValueError(f"{MODULE} 的结算必须由执行事实推导重试安全")
    checked += 1
    # 通知失败在持久化之后上报，不得回滚结果。
    if finish.find("append_tool_revision(") > finish.find("self.notify("):
        raise ValueError(f"{MODULE} 的工具结算必须先落库再通知")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_turn_append()
    except (ValueError, SyntaxError) as error:
        print(f"回合条目核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合条目一致：{checked} 项消息追加、工具结算与通知校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
