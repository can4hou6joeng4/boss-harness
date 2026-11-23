#!/usr/bin/env python3
"""核对事件总线的持久化、发布与观察顺序。

`EventHub` 是内核事件唯一出口：事件先写入持久游标，再按 `publish` / `observe`
开关通知客户端与生命周期 hook；同名条目的文本与思考增量在 `live` 投影中累积，
`item/completed` 清除运行条目；`publish_persisted` 只重播已持久事件，不重复追加。
这里按源码顺序固定这些边界，并用假 server / 假 hooks 与临时 `SessionStore` 直接
执行发布、观察、重播与截止逻辑；不启动真实会话或桌面。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/application.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import EventHub  # noqa: E402
from boss_harness.session import Entry, SessionStore  # noqa: E402

# 事件发布：持久化 → live 投影 → publish → observe，完成事件清除运行条目。
EMIT_ORDER = (
    "def _emit_locked(self, method: str, params: dict | None, *, publish: bool,",
    "observe: bool) -> dict:",
    "notification = params or {}",
    "stored_params = notification",
    'if method == "item/completed" and notification.get("kind") == "agentMessage":',
    'stored_params = project_item(str(notification.get("threadId") or ""), {',
    'stored_params.pop("id", None)',
    "event = self.sessions.append_event(method, stored_params)",
    'payload = event["params"]',
    'live_payload = {**notification, "eventId": payload["eventId"],',
    '"eventCursor": payload["eventCursor"]}',
    "if thread_id and item_id:",
    'if method in {"agentMessage/delta", "agentThinking/delta"}:',
    'item = current.setdefault(item_id, {"text": "", "thinking": ""})',
    'key = "text" if method == "agentMessage/delta" else "thinking"',
    'item[key] += payload.get("delta", "")',
    'elif method == "item/completed":',
    "current.pop(item_id, None)",
    "if publish:",
    "self.server.notify(method, live_payload)",
    "except (ConnectionError, BrokenPipeError):",
    "pass  # Durable state survives a disappearing observer.",
    "if observe:",
    "self.lifecycle_hooks.observe_event(method, payload)",
    "return event",
)
# 重播：只通知与观察，不追加事件。
PUBLISH_ORDER = (
    "def publish_persisted(self, event: dict) -> None:",
    "with self.lock:",
    'method, payload = event["method"], event["params"]',
    "self.server.notify(method, payload)",
    "except (ConnectionError, BrokenPipeError):",
    "self.lifecycle_hooks.observe_event(method, payload)",
)
# 条目读取：仅运行中条目叠加 live 投影。
ITEMS_ORDER = (
    "def items(self, thread_id: str, *, entries: list[dict] | None = None) -> list[dict]:",
    "with self.lock:",
    "source = (self.sessions.read_items(thread_id) if entries is None",
    "else self.sessions._project_items(thread_id, entries))",
    'return [{**item, **(self.live.get(thread_id, {}).get(item["id"], {}) '
    'if item.get("status") == "running" else {})}',
    "for item in source]",
)
# 截止发布：先算剩余时间再尝试锁，超时直接放弃并释放锁。
UNTIL_ORDER = (
    "def emit_until(self, method: str, params: dict | None = None, *, deadline: float,",
    "publish: bool = True, observe: bool = True) -> dict | None:",
    "remaining = deadline - time.monotonic()",
    "if remaining <= 0 or not self.lock.acquire(timeout=remaining):",
    "return None",
    "try:",
    "return self._emit_locked(method, params, publish=publish, observe=observe)",
    "finally:",
    "self.lock.release()",
)


class _Server:
    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.error = error

    def notify(self, method: str, payload: dict | None = None) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((method, payload))


class _Hooks:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def observe_event(self, method: str, payload: dict | None = None) -> None:
        self.events.append((method, payload))


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
        raise ValueError(f"事件总线行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_raise(call, error_type: type[BaseException], message: str, label: str) -> int:
    try:
        call()
    except error_type as error:
        if str(error) != message:
            raise ValueError(
                f"事件总线行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"事件总线行为变化 {label}：期望 {error_type.__name__}")


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        server, hooks = _Server(), _Hooks()
        hub = EventHub(server, store, hooks)
        thread = store.create("事件")["id"]
        store.append(thread, Entry(type="item", id="m1", payload={
            "kind": "agentMessage", "text": "", "status": "running"}))
        store.append(thread, Entry(type="item", id="done", payload={
            "kind": "agentMessage", "text": "完成文", "status": "completed"}))
        first = hub.emit("agentMessage/delta", {"threadId": thread, "itemId": "m1", "delta": "你"})
        second = hub.emit("agentMessage/delta", {"threadId": thread, "itemId": "m1", "delta": "好"})
        third = hub.emit("agentThinking/delta", {"threadId": thread, "itemId": "m1", "delta": "想"})
        checked += _expect_value(
            (first["params"]["eventCursor"], second["params"]["eventCursor"],
             third["params"]["eventCursor"]), ("1", "2", "3"), "事件游标递增")
        checked += _expect_value(hub.live[thread]["m1"], {"text": "你好", "thinking": "想"},
                                 "增量归并")
        checked += _expect_value(
            [(item["id"], item.get("text"), item.get("thinking")) for item in hub.items(thread)],
            [("m1", "你好", "想"), ("done", "完成文", None)], "运行条目叠加 live")
        checked += _expect_value(
            (server.calls[0][1]["itemId"], server.calls[0][1]["eventCursor"],
             server.calls[0][1]["delta"]), ("m1", "1", "你"), "发布保留通知字段与游标")
        checked += _expect_value(
            [(method, payload["eventCursor"]) for method, payload in hooks.events],
            [("agentMessage/delta", "1"), ("agentMessage/delta", "2"),
             ("agentThinking/delta", "3")], "观察按持久顺序")

        quiet, quiet_hooks = _Server(), _Hooks()
        quiet_hub = EventHub(quiet, store, quiet_hooks)
        persisted = quiet_hub.emit("turn/started", {"threadId": thread, "turnId": "turn-1"},
                                   publish=False)
        checked += _expect_value((quiet.calls, len(quiet_hooks.events)), ([], 1),
                                 "publish 关闭仍观察")
        checked += _expect_value(persisted["params"]["turnId"], "turn-1", "publish 关闭仍持久化")
        unobserved = _Server()
        unobserved_hub = EventHub(unobserved, store, _Hooks())
        unobserved_hub.emit("turn/started", {"threadId": thread, "turnId": "turn-2"},
                            observe=False)
        checked += _expect_value([method for method, _ in unobserved.calls], ["turn/started"],
                                 "observe 关闭仍发布")

        hub.emit("item/completed", {"threadId": thread, "itemId": "m1", "kind": "agentMessage",
                                    "text": "你好", "status": "completed"})
        checked += _expect_value(hub.live.get(thread, {}), {}, "完成清除运行条目")
        completed_event = store.events_after("5")["events"][-1]
        checked += _expect_value(
            (completed_event["method"], "id" in completed_event["params"],
             completed_event["params"]["text"]),
            ("item/completed", False, "你好"), "完成事件持久投影")
        hub.emit("agentMessage/delta", {"threadId": thread, "itemId": "done", "delta": "增量"})
        checked += _expect_value(
            [item["text"] for item in hub.items(thread) if item["id"] == "done"],
            ["完成文"], "完成条目不叠加 live")
        snapshot = store.read_entries(thread)
        checked += _expect_value(
            [item["id"] for item in hub.items(thread, entries=snapshot)], ["m1", "done"],
            "固定条目快照读取")

        broken_hooks = _Hooks()
        broken_event = EventHub(_Server(ConnectionError("观察者已断开")), store,
                                broken_hooks).emit(
            "turn/started", {"threadId": thread, "turnId": "turn-5"})
        checked += _expect_value(
            (len(broken_hooks.events), broken_event["params"]["turnId"]), (1, "turn-5"),
            "发布吞掉观察者断开仍持久观察")
        checked += _expect_raise(
            lambda: EventHub(_Server(RuntimeError("故障")), store, _Hooks()).emit(
                "turn/started", {"threadId": thread, "turnId": "turn-6"}),
            RuntimeError, "故障", "发布传播其他错误")

        cursor = store.latest_event_cursor()
        replay = {"method": "thread/deleted", "params": {"threadId": thread}}
        hub.publish_persisted(replay)
        checked += _expect_value(store.latest_event_cursor(), cursor, "重播不追加事件")
        checked += _expect_value(server.calls[-1], ("thread/deleted", replay["params"]),
                                 "重播通知原样参数")
        checked += _expect_value(hooks.events[-1], ("thread/deleted", replay["params"]),
                                 "重播观察原样参数")
        broken, broken_hooks = _Server(ConnectionError("观察者已断开")), _Hooks()
        EventHub(broken, store, broken_hooks).publish_persisted(replay)
        checked += _expect_value(len(broken_hooks.events), 1, "重播吞掉连接错误仍观察")
        checked += _expect_raise(
            lambda: EventHub(_Server(RuntimeError("故障")), store, _Hooks()).publish_persisted(replay),
            RuntimeError, "故障", "重播传播其他错误")

        before = store.latest_event_cursor()
        expired = hub.emit_until("turn/started", {"threadId": thread, "turnId": "turn-3"},
                                 deadline=0)
        checked += _expect_value(
            (expired, store.latest_event_cursor(), "turn-3" in str(hub.live)),
            (None, before, False), "过期截止放弃发布")
        fresh = hub.emit_until("turn/started", {"threadId": thread, "turnId": "turn-4"},
                               deadline=time.monotonic() + 30)
        checked += _expect_value((fresh or {}).get("params", {}).get("turnId"), "turn-4",
                                 "有效截止发布")
    return checked


def check_event_hub() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    emit = _function(tree, source, "_emit_locked")
    publish = _function(tree, source, "publish_persisted")
    items = _function(tree, source, "items")
    until = _function(tree, source, "emit_until")
    checked = _ordered(EMIT_ORDER, emit, MODULE)
    checked += _ordered(PUBLISH_ORDER, publish, MODULE)
    checked += _ordered(ITEMS_ORDER, items, MODULE)
    checked += _ordered(UNTIL_ORDER, until, MODULE)
    # 持久化必须先于发布与观察，且各自只有一处。
    if emit.count("append_event(") != 1 or emit.count("self.server.notify(") != 1:
        raise ValueError(f"{MODULE} 的事件发布必须一次持久化、一次通知")
    checked += 1
    if emit.count("self.lifecycle_hooks.observe_event(") != 1:
        raise ValueError(f"{MODULE} 的事件发布必须一次观察")
    checked += 1
    # 吞错范围只限观察者断开，不能吃掉其他故障。
    if emit.count("except (ConnectionError, BrokenPipeError):") != 1:
        raise ValueError(f"{MODULE} 的事件发布必须只吞观察者断开")
    checked += 1
    # 重播不得重复追加事件。
    if "append_event(" in publish:
        raise ValueError(f"{MODULE} 的事件重播不得重复持久化")
    checked += 1
    if until.count("self.lock.release()") != 1:
        raise ValueError(f"{MODULE} 的截止发布必须释放锁")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_event_hub()
    except (ValueError, SyntaxError) as error:
        print(f"事件总线核对失败，{error}", file=sys.stderr)
        return 2
    print(f"事件总线一致：{checked} 项持久化、发布与观察校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
