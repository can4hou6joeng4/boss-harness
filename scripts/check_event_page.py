#!/usr/bin/env python3
"""对照内核事件回放的游标分页、筛选与索引重建。

`events_after` 以严格递增游标分页：查询取 `limit + 1` 行判定 `hasMore`，
`_event_rows` 再按 `params_json` 原始字节预算逐行读取，首行超预算也返回以
保证游标推进；`_event_page_entries` 要求 `params_json` 与游标列一致、`method`
是字符串，索引损坏时由 `_rebuild_event_index` 从 `events.jsonl` 重建并重试。
`append_event` 负责保护字段、方法名与参数校验、落盘与索引同步。本脚本在
临时目录构造 `SessionStore` 做行为对照，覆盖字节预算、首行超预算与四类索引
损坏，并扫描源码；不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore  # noqa: E402

EVENTS_ORDER = (
    "def events_after(self, cursor: str | None = None, thread_id: str | None = None, limit: int = 100,",
    "methods: tuple[str, ...] | list[str] | None = None) -> dict:",
    "position = _event_cursor(cursor)",
    "_limit(limit, 1000)",
    "if thread_id is not None:",
    "self.require_thread(thread_id)",
    'raise ValueError("事件方法筛选无效")',
    'query = "SELECT cursor,method,params_json FROM events WHERE cursor>?"',
    'query += " AND thread_id=?"',
    'query += " AND method IN (" + ",".join("?" for _ in methods) + ")"',
    'query += " ORDER BY cursor LIMIT ?"',
    "parameters.append(limit + 1)",
    "pending = sorted(self._pending_deletion_ids()) if thread_id is None else []",
    'query = query.replace(" ORDER BY cursor LIMIT ?",',
    '" AND (thread_id IS NULL OR thread_id NOT IN (" + ",".join("?" for _ in pending)',
    '+ ")) ORDER BY cursor LIMIT ?")',
    "parameters[-1:-1] = pending",
    "self._sync_events()",
    "rows, has_more = self._event_rows(query, parameters, limit)",
    "events = self._event_page_entries(rows, limit)",
    "self._rebuild_event_index()",
    'raise ValueError("事件索引已损坏，事件回放暂不可用") from None',
    'return {"events": events,',
    '"nextCursor": str(rows[-1]["cursor"]) if rows else str(position), "hasMore": has_more}',
)
ROWS_ORDER = (
    "def _event_rows(self, query: str, parameters: list[Any], limit: int) -> tuple[list[sqlite3.Row], bool]:",
    "rows: list[sqlite3.Row] = []",
    "raw_bytes = 0",
    "with self._index.connection() as connection:",
    "cursor = connection.execute(query, parameters)",
    "while True:",
    "row = cursor.fetchone()",
    "if row is None:",
    "return rows, False",
    "if len(rows) >= limit:",
    "return rows, True",
    'payload = row["params_json"]',
    'size = len(payload) if isinstance(payload, str) else 0',
    "if rows and raw_bytes + size > _EVENT_PAGE_RAW_BYTES:",
    "rows.append(row)",
    "raw_bytes += size",
)
ENTRIES_ORDER = (
    "def _event_page_entries(rows: list[sqlite3.Row], limit: int) -> list[dict[str, Any]]:",
    "for row in rows[:limit]:",
    'params = json.loads(row["params_json"])',
    "except (TypeError, ValueError, RecursionError):",
    'raise ValueError("事件索引已损坏") from None',
    "if not isinstance(params, dict):",
    'if params.get("eventCursor") != str(row["cursor"]):',
    'if not isinstance(row["method"], str) or not row["method"]:',
    'entries.append({"method": row["method"], "params": params})',
    "return entries",
)
APPEND_ORDER = (
    "def append_event(self, method: str, params: dict[str, Any] | None = None) -> dict:",
    'raise ValueError("事件方法名无效")',
    'raise ValueError("事件参数必须是对象")',
    "payload = dict(params or {})",
    'if {"eventId", "eventCursor"} & set(payload):',
    'raise ValueError("eventId 与 eventCursor 由存储层生成")',
    'thread_id = payload.get("threadId")',
    "_json(payload)",
    "self.require_thread(thread_id)",
    "self._index_events(connection)",
    "event_id = uuid.uuid4().hex",
    "payload.update(eventId=event_id, eventCursor=str(inserted.lastrowid))",
    'record = {"type": "event", "timestamp": _now(), **frame}',
    'if len(_json(record).encode("utf-8")) > MAX_EVENT_LINE_BYTES:',
    'raise ValueError("事件日志单行超过大小限制")',
    "self._append_line(self.events_path, record)",
    "UPDATE events SET params_json=? WHERE cursor=?",
    "INSERT INTO checkpoints(name,value) VALUES('events',?)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def check_event_page() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    events = _method(tree, source, "SessionStore", "events_after")
    rows_method = _method(tree, source, "SessionStore", "_event_rows")
    entries_method = _method(tree, source, "SessionStore", "_event_page_entries")
    append = _method(tree, source, "SessionStore", "append_event")
    checked = _ordered(EVENTS_ORDER, events, SESSION)
    checked += _ordered(ROWS_ORDER, rows_method, SESSION)
    checked += _ordered(ENTRIES_ORDER, entries_method, SESSION)
    checked += _ordered(APPEND_ORDER, append, SESSION)
    # 分页取 limit + 1 行，返回下一个游标而非最后一条事件编号。
    if events.count("limit + 1") != 1 or events.count('str(rows[-1]["cursor"])') != 1:
        raise ValueError(f"{SESSION} 的事件分页必须用 limit + 1 与游标推进")
    checked += 1
    if events.count("self._rebuild_event_index()") != 1:
        raise ValueError(f"{SESSION} 的事件分页必须在索引损坏时重建")
    checked += 1
    if events.count("self._pending_deletion_ids()") != 1:
        raise ValueError(f"{SESSION} 的事件分页必须过滤待删除会话")
    checked += 1
    # 原始字节预算必须允许首行超预算，否则游标无法推进。
    if "if rows and raw_bytes + size > _EVENT_PAGE_RAW_BYTES:" not in rows_method:
        raise ValueError(f"{SESSION} 的事件预算必须允许首行超预算")
    checked += 1
    if rows_method.count("if len(rows) >= limit:") != 1 or rows_method.count("return rows, True") != 2:
        raise ValueError(f"{SESSION} 的事件读取必须在条数与字节两处截断")
    checked += 1
    # 索引行必须与自身游标、method 列一致。
    if entries_method.count('raise ValueError("事件索引已损坏")') != 4:
        raise ValueError(f"{SESSION} 的事件投影必须固定四类索引损坏")
    checked += 1
    if entries_method.count("rows[:limit]") != 1:
        raise ValueError(f"{SESSION} 的事件投影必须按页上限截断")
    checked += 1
    # 保护字段在落盘前拒绝，方法名与参数形状先校验。
    if append.count('raise ValueError("事件方法名无效")') != 1:
        raise ValueError(f"{SESSION} 的事件追加必须校验方法名")
    checked += 1
    if append.count("_json(payload)") != 2 or append.count("self._index_events(connection)") != 1:
        raise ValueError(f"{SESSION} 的事件追加必须先校验可序列化并同步索引")
    checked += 1
    if append.count("MAX_EVENT_LINE_BYTES") != 1:
        raise ValueError(f"{SESSION} 的事件追加必须限制单行大小")
    checked += 1
    if append.index("self._append_line(self.events_path, record)") < append.index("event_id = uuid.uuid4().hex"):
        raise ValueError(f"{SESSION} 的事件必须先分配编号再落盘")
    checked += 1
    # 行为：追加、分页、筛选与重启回放。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        store = SessionStore(root)
        try:
            first = store.create("甲")["id"]
            second = store.create("乙")["id"]
            frames = [
                store.append_event("thread/updated", {"threadId": first}),
                store.append_event("queue/updated"),
                store.append_event("turn/stream", {"threadId": second, "value": 1}),
                store.append_event("turn/stream", {"threadId": first}),
            ]
            if [frame["params"]["eventCursor"] for frame in frames] != ["1", "2", "3", "4"]:
                raise ValueError("事件游标必须从 1 严格递增")
            checked += 1
            for frame in frames:
                if frame["method"] not in {"thread/updated", "queue/updated", "turn/stream"}:
                    raise ValueError("事件帧必须保留方法名")
                params = frame["params"]
                event_id = params.get("eventId")
                if (not isinstance(event_id, str) or len(event_id) != 32
                        or any(char not in "0123456789abcdef" for char in event_id)):
                    raise ValueError("事件帧必须包含 32 位事件编号")
                cursor = params.get("eventCursor")
                if not isinstance(cursor, str) or cursor != str(int(cursor)):
                    raise ValueError("事件帧的游标必须是十进制字符串")
            checked += 1
            page = store.events_after(limit=2)
            if [event["method"] for event in page["events"]] != ["thread/updated", "queue/updated"]:
                raise ValueError("首页必须按游标返回两条事件")
            checked += 1
            if page["hasMore"] is not True or page["nextCursor"] != "2":
                raise ValueError("首页必须报告更多并给出最后一条游标")
            checked += 1
            page = store.events_after(page["nextCursor"], limit=2)
            if [event["method"] for event in page["events"]] != ["turn/stream", "turn/stream"]:
                raise ValueError("续页必须从上次游标之后返回")
            checked += 1
            if page["hasMore"] is not False or page["nextCursor"] != "4":
                raise ValueError("末页必须报告没有更多")
            checked += 1
            empty = store.events_after(page["nextCursor"], limit=10)
            if empty["events"] or empty["hasMore"] or empty["nextCursor"] != "4":
                raise ValueError("越过末页必须返回空页并保持游标")
            checked += 1
            filtered = store.events_after(None, first, 10)
            if [event["method"] for event in filtered["events"]] != ["thread/updated", "turn/stream"]:
                raise ValueError("会话筛选必须只返回该会话事件")
            checked += 1
            filtered = store.events_after(None, None, 10, ("queue/updated",))
            if [event["method"] for event in filtered["events"]] != ["queue/updated"]:
                raise ValueError("方法筛选必须只返回指定方法")
            checked += 1
            filtered = store.events_after(None, None, 10, ["turn/stream", "queue/updated"])
            if len(filtered["events"]) != 3:
                raise ValueError("方法筛选必须接受列表并保留多个方法")
            checked += 1
            allowed = tuple(f"m{index}" for index in range(16))
            filtered = store.events_after(None, None, 10, allowed)
            if filtered["events"]:
                raise ValueError("十六个方法筛选必须通过且没有匹配事件")
            checked += 1
            if store.latest_event_cursor() != "4":
                raise ValueError("最新事件游标必须是最后一条")
            checked += 1
            for label, action in (
                ("limit 为零", lambda: store.events_after(limit=0)),
                ("limit 超限", lambda: store.events_after(limit=1001)),
                ("游标非法", lambda: store.events_after("abc")),
                ("方法筛选为空", lambda: store.events_after(methods=[])),
                ("方法筛选超限", lambda: store.events_after(methods=tuple("m%d" % index for index in range(17)))),
                ("方法筛选空串", lambda: store.events_after(methods=("",))),
                ("会话不存在", lambda: store.events_after(None, "000000000000", 10)),
                ("方法名为空", lambda: store.append_event("")),
                ("方法名过长", lambda: store.append_event("m" * 257)),
                ("方法名含控制符", lambda: store.append_event("m\n")),
                ("参数非对象", lambda: store.append_event("m", [])),
                ("保护 eventId", lambda: store.append_event("m", {"eventId": "x"})),
                ("保护 eventCursor", lambda: store.append_event("m", {"eventCursor": "1"})),
                ("会话不存在", lambda: store.append_event("m", {"threadId": "000000000000"})),
            ):
                try:
                    action()
                except ValueError:
                    checked += 1
                else:
                    raise ValueError(f"事件入参必须被拒绝：{label}")
            try:
                store.append_event("m", {"value": object()})
            except TypeError:
                checked += 1
            else:
                raise ValueError("事件入参必须被拒绝：参数不可序列化")
            # 索引损坏：篡改 params_json 后必须重建并返回正确帧。
            with store._index.transaction() as connection:
                connection.execute("UPDATE events SET params_json='{}' WHERE cursor=2")
            recovered = store.events_after(None, None, 10)
            if [event["method"] for event in recovered["events"]] != ["thread/updated", "queue/updated", "turn/stream", "turn/stream"]:
                raise ValueError("索引损坏后必须从事件日志重建")
            checked += 1
            cursors = [event["params"].get("eventCursor") for event in recovered["events"]]
            if cursors != ["1", "2", "3", "4"]:
                raise ValueError("索引重建后的事件游标必须与日志一致")
            checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE events SET params_json='[]' WHERE cursor=3")
            recovered = store.events_after(None, None, 10)
            if ([event["method"] for event in recovered["events"]]
                    != ["thread/updated", "queue/updated", "turn/stream", "turn/stream"]
                    or [event["params"].get("eventCursor") for event in recovered["events"]]
                    != ["1", "2", "3", "4"]):
                raise ValueError("非对象参数必须触发索引重建")
            checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE events SET method='' WHERE cursor=4")
            recovered = store.events_after(None, None, 10)
            if [event["method"] for event in recovered["events"]] != ["thread/updated", "queue/updated", "turn/stream", "turn/stream"]:
                raise ValueError("空方法名必须触发索引重建")
            checked += 1
            # 删除标记会话的事件不再出现在回放中。
            store._write_delete_intent(first, [])
            remaining = store.events_after(None, None, 10)
            if [event["method"] for event in remaining["events"]] != ["queue/updated", "turn/stream"]:
                raise ValueError("待删除会话的事件必须从回放中过滤")
            checked += 1
            _expect_error(lambda: store.events_after(None, first, 10), "会话正在删除，暂不可读取", "删除中会话")
            checked += 1
        finally:
            store.close()
        # 重启后完成删除会剔除该会话事件并追加 thread/deleted。
        restarted = SessionStore(root)
        try:
            replayed = restarted.events_after(None, None, 10)
            if [event["method"] for event in replayed["events"]] != ["queue/updated", "turn/stream", "thread/deleted"]:
                raise ValueError("重启后事件回放必须剔除已删除会话并追加删除事件")
            checked += 1
            deletion = replayed["events"][-1]["params"]
            if deletion.get("deletedThreadId") != first:
                raise ValueError("删除事件必须记录被删除的会话")
            checked += 1
            lines = (root.parent / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if len(lines) != 3 or any(json.loads(line).get("type") != "event" for line in lines):
                raise ValueError("事件日志必须逐行保存事件帧并剔除已删除会话")
            checked += 1
        finally:
            restarted.close()
    # 行为：原始字节预算、首行超预算与嵌套保护字段。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "page" / "sessions")
        try:
            store.append_event("budget/first", {"blob": "x" * (3 * 1024 * 1024)})
            store.append_event("budget/second", {"blob": "y" * (2 * 1024 * 1024)})
            page = store.events_after(limit=10)
            if [event["method"] for event in page["events"]] != ["budget/first"]:
                raise ValueError("字节预算必须在第二行前截断")
            checked += 1
            if page["hasMore"] is not True or page["nextCursor"] != "1":
                raise ValueError("字节预算截断必须报告更多并推进游标")
            checked += 1
            page = store.events_after(page["nextCursor"], limit=10)
            if [event["method"] for event in page["events"]] != ["budget/second"]:
                raise ValueError("续页必须从预算截断处继续")
            checked += 1
            if page["hasMore"] is not False or page["nextCursor"] != "2":
                raise ValueError("预算续页必须收尾到第二条")
            checked += 1
            nested = store.append_event("nested/event", {"meta": {"eventCursor": "keep"}})
            if nested["params"]["meta"]["eventCursor"] != "keep":
                raise ValueError("嵌套 eventCursor 必须保留")
            checked += 1
            page = store.events_after("2", limit=10)
            if [event["method"] for event in page["events"]] != ["nested/event"]:
                raise ValueError("嵌套保护字段事件必须可回放")
            checked += 1
        finally:
            store.close()
        single = SessionStore(Path(temporary) / "single" / "sessions")
        try:
            single.append_event("budget/single", {"blob": "z" * (5 * 1024 * 1024)})
            page = single.events_after(limit=10)
            if [event["method"] for event in page["events"]] != ["budget/single"]:
                raise ValueError("首行超预算必须仍返回该行")
            checked += 1
            if page["hasMore"] is not False or page["nextCursor"] != "1":
                raise ValueError("首行超预算后必须正常收尾")
            checked += 1
        finally:
            single.close()
    return checked


def main() -> int:
    try:
        checked = check_event_page()
    except (ValueError, SyntaxError) as error:
        print(f"事件分页核对失败，{error}", file=sys.stderr)
        return 2
    print(f"事件分页一致：{checked} 项游标、预算与重建校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
