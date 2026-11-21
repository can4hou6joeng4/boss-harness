#!/usr/bin/env python3
"""对照会话删除时事件日志重写的校验、游标与原子发布。

`_rewrite_events_for_deletion` 在删除会话时重写 `events.jsonl`：源文件必须
是私有普通文件，打开后 (dev, ino) 与可见路径一致，写入后再复核九元组签名；
逐行校验事件帧、游标与事件编号唯一、会话编号合法，只丢弃目标会话的事件，
匹配恢复标记的删除事件必须形态正确，缺失时按高水位加一补齐；临时文件独占
创建，最后以硬链接或替换发布并刷新目录。`_event_high_water` 取索引最大游标
与自增序列的较大者；`_previous_deletion_event` 从索引查找已完成的删除事件，
损坏行跳过而不阻断删除。本脚本在临时目录构造 `SessionStore` 做行为对照并
扫描源码；不访问网络、模型或招聘平台。
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

REWRITE_ORDER = (
    "def _rewrite_events_for_deletion(self, connection: sqlite3.Connection,",
    "intent: dict[str, Any]) -> dict:",
    'thread_id = intent["threadId"]',
    "target = self.events_path",
    "original = target.lstat()",
    "if not stat.S_ISREG(original.st_mode) or original.st_nlink != 1:",
    'raise ValueError("事件日志不是普通私有文件，清理已暂停")',
    "restrict_private_file(target)",
    "descriptor = open_private_file(target, os.O_RDONLY)",
    'source_handle = os.fdopen(descriptor, "rb")',
    "opened = os.fstat(descriptor)",
    "source_signature = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,",
    "visible = target.lstat()",
    "if (visible.st_dev, visible.st_ino) != (opened.st_dev, opened.st_ino):",
    "source_handle.close()",
    'raise ValueError("事件日志在删除期间变化，清理已暂停")',
    'temporary = target.with_name(f".events.jsonl.delete-{thread_id}.{uuid.uuid4().hex}.tmp")',
    "descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)",
    "maximum_cursor = self._event_high_water(connection)",
    "seen_cursors: set[int] = set()",
    "seen_event_ids: set[str] = set()",
    'last_byte = b"\\n"',
    "if not raw_line.strip():",
    'output.write(raw_line + b"\\n")',
    "record = _decode_jsonl_object(",
    "except ValueError as exc:",
    'raise ValueError(f"事件日志损坏，无法安全删除会话：{exc}") from None',
    'if not isinstance(record, dict):',
    'raise ValueError("事件日志格式无效，无法安全删除会话")',
    'if (record.get("type") != "event"',
    'cursor = _event_cursor(params.get("eventCursor"))',
    'if cursor < 1 or not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id):',
    'raise ValueError("事件日志游标无效，无法安全删除会话")',
    "if cursor in seen_cursors:",
    'raise ValueError("事件日志存在重复游标，无法安全删除会话")',
    "if event_id in seen_event_ids:",
    'raise ValueError("事件日志存在重复事件 ID，无法安全删除会话")',
    "seen_cursors.add(cursor)",
    "seen_event_ids.add(event_id)",
    "maximum_cursor = max(maximum_cursor, cursor)",
    'if event_id == intent["eventId"]:',
    "event_count += 1",
    'raise ValueError("会话删除事件与恢复标记冲突")',
    'event = {"method": record["method"], "params": params}',
    'elif params.get("threadId") != thread_id:',
    "if event_count > 1:",
    'raise ValueError("事件日志含重复的会话删除事件")',
    "if event is None:",
    "if maximum_cursor >= 2**63 - 1:",
    'raise ValueError("事件游标已耗尽，无法完成会话删除")',
    'params = {"deletedThreadId": thread_id, "eventId": intent["eventId"],',
    '"eventCursor": str(maximum_cursor + 1)}',
    'event = {"method": "thread/deleted", "params": params}',
    'if last_byte != b"\\n":',
    'output.write((_json({"type": "event", "timestamp": _now(), **event}) + "\\n").encode("utf-8"))',
    "output.flush()",
    "os.fsync(output.fileno())",
    "if current_signature != source_signature:",
    "if original is None:",
    "os.link(temporary, target)",
    "temporary.unlink()",
    "os.replace(temporary, target)",
    "_fsync_directory(target.parent)",
    "temporary.unlink(missing_ok=True)",
    'raise RuntimeError("删除事件未能生成")',
    "return event",
)
HIGH_WATER_ORDER = (
    "def _event_high_water(connection: sqlite3.Connection) -> int:",
    'maximum = int(connection.execute("SELECT COALESCE(MAX(cursor),0) FROM events").fetchone()[0])',
    'sequence = connection.execute("SELECT seq FROM sqlite_sequence WHERE name=\'events\'").fetchone()',
    "except sqlite3.OperationalError:",
    "return max(maximum, int(sequence[0]) if sequence else 0)",
)
PREVIOUS_ORDER = (
    "def _previous_deletion_event(connection: sqlite3.Connection, thread_id: str) -> dict | None:",
    "for row in connection.execute(\"SELECT method,params_json FROM events WHERE method='thread/deleted'\"):",
    'params = json.loads(row["params_json"])',
    "except (TypeError, ValueError, RecursionError):",
    "continue",
    "if not isinstance(params, dict):",
    'if params.get("deletedThreadId") == thread_id:',
    'return {"method": row["method"], "params": params}',
    "return None",
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


def _append_record(store: SessionStore, method: str, params: dict) -> None:
    record = {"type": "event", "timestamp": "2026-01-01T00:00:00+00:00",
              "method": method, "params": params}
    with store.events_path.open("ab") as handle:
        handle.write((json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))


def _intent(thread_id: str, event_id: str) -> dict:
    return {"version": 1, "threadId": thread_id, "attachmentDigests": [], "eventId": event_id}


def _lines(store: SessionStore) -> list[dict]:
    return [json.loads(line) for line in store.events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def check_event_rewrite() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    rewrite = _method(tree, source, "SessionStore", "_rewrite_events_for_deletion")
    high_water = _method(tree, source, "SessionStore", "_event_high_water")
    previous = _method(tree, source, "SessionStore", "_previous_deletion_event")
    checked = _ordered(REWRITE_ORDER, rewrite, SESSION)
    checked += _ordered(HIGH_WATER_ORDER, high_water, SESSION)
    checked += _ordered(PREVIOUS_ORDER, previous, SESSION)
    # 三类变化拒绝、两类格式拒绝、两类会话编号拒绝各就各位。
    if rewrite.count('raise ValueError("事件日志在删除期间变化，清理已暂停")') != 3:
        raise ValueError(f"{SESSION} 的事件日志变化必须恰好三处拒绝")
    checked += 1
    if rewrite.count('raise ValueError("事件日志格式无效，无法安全删除会话")') != 2:
        raise ValueError(f"{SESSION} 的事件日志格式必须恰好两处拒绝")
    checked += 1
    if rewrite.count('raise ValueError("事件日志会话 ID 无效，无法安全删除会话")') != 2:
        raise ValueError(f"{SESSION} 的事件日志会话编号必须恰好两处拒绝")
    checked += 1
    if rewrite.count("os.link(temporary, target)") != 1 or rewrite.count("os.replace(temporary, target)") != 1:
        raise ValueError(f"{SESSION} 的事件日志发布必须恰好包含硬链接与替换各一次")
    checked += 1
    if rewrite.count("seen_cursors") != 3 or rewrite.count("seen_event_ids") != 3:
        raise ValueError(f"{SESSION} 的游标与事件编号去重必须各三处（声明、检查、登记）")
    checked += 1
    if rewrite.count("MAX_EVENT_LINE_BYTES") != 1 or rewrite.count("_EVENT_ID.fullmatch") != 1:
        raise ValueError(f"{SESSION} 的单行上限与事件编号校验必须各一处")
    checked += 1
    if rewrite.count('temporary = target.with_name(f".events.jsonl.delete-{thread_id}.{uuid.uuid4().hex}.tmp")') != 1:
        raise ValueError(f"{SESSION} 的临时文件必须带会话与随机后缀")
    checked += 1
    if rewrite.count("os.fsync(output.fileno())") != 1 or rewrite.count("_fsync_directory(target.parent)") != 1:
        raise ValueError(f"{SESSION} 的事件日志必须落盘并刷新目录")
    checked += 1
    # 源签名复核必须在发布之前；删除事件最多一条。
    if rewrite.index("if current_signature != source_signature:") > rewrite.index("if original is None:"):
        raise ValueError(f"{SESSION} 的来源签名复核必须先于发布")
    checked += 1
    if rewrite.count("if event_count > 1:") != 1:
        raise ValueError(f"{SESSION} 的删除事件必须恰好一条")
    checked += 1
    # 高水位取索引与序列较大者；旧删除事件按会话匹配。
    if high_water.count("MAX(cursor)") != 1 or high_water.count("sqlite_sequence") != 1:
        raise ValueError(f"{SESSION} 的高水位必须同时读取最大游标与自增序列")
    checked += 1
    if previous.count("thread/deleted") != 1 or previous.count("continue") != 2:
        raise ValueError(f"{SESSION} 的旧删除事件查找必须跳过两类损坏行")
    checked += 1
    # 行为：删除重写、幂等与事件保留。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            kept = store.create("保留")["id"]
            gone = store.create("删除")["id"]
            store.append_event("turn/stream", {"threadId": gone, "turnId": "t1"})
            store.append_event("turn/stream", {"threadId": kept, "turnId": "t2"})
            store.append_event("queue/updated", {})
            event = store.delete_thread(gone)
            if event.get("method") != "thread/deleted":
                raise ValueError("删除会话必须生成删除事件")
            checked += 1
            if (event.get("params", {}).get("deletedThreadId") != gone
                    or event.get("params", {}).get("eventCursor") != "4"
                    or len(event.get("params", {}).get("eventId", "")) != 32):
                raise ValueError("删除事件必须携带会话、下一个游标与 32 位事件编号")
            checked += 1
            lines = _lines(store)
            if len(lines) != 3:
                raise ValueError("重写后的事件日志必须保留其他会话与无会话事件并追加删除事件")
            checked += 1
            if any(line.get("params", {}).get("threadId") == gone for line in lines):
                raise ValueError("被删除会话的事件必须从日志移除")
            checked += 1
            if [line.get("params", {}).get("threadId") for line in lines[:2]] != [kept, None]:
                raise ValueError("保留事件的相对顺序不得变化")
            checked += 1
            again = store.delete_thread(gone)
            if again.get("params", {}).get("eventId") != event["params"]["eventId"]:
                raise ValueError("重复删除必须返回同一删除事件")
            checked += 1
            if len(_lines(store)) != 3:
                raise ValueError("重复删除不得重写事件日志")
            checked += 1
        finally:
            store.close()
    # 行为：预置删除事件复用。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("预置")["id"]
            store.append_event("turn/stream", {"threadId": thread_id})
            intent = store._write_delete_intent(thread_id, store.read_entries(thread_id))
            _append_record(store, "thread/deleted",
                           {"deletedThreadId": thread_id, "eventId": intent["eventId"],
                            "eventCursor": "9"})
            event = store.delete_thread(thread_id)
            if event.get("params", {}).get("eventId") != intent["eventId"]:
                raise ValueError("预置的删除事件必须被复用")
            checked += 1
            lines = _lines(store)
            if len(lines) != 1 or lines[0].get("method") != "thread/deleted":
                raise ValueError("复用删除事件时不得新增或保留目标会话事件")
            checked += 1
        finally:
            store.close()
    # 行为：删除事件与恢复标记冲突。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("冲突")["id"]
            intent = store._write_delete_intent(thread_id, store.read_entries(thread_id))
            _append_record(store, "turn/stream",
                           {"deletedThreadId": thread_id, "eventId": intent["eventId"],
                            "eventCursor": "1"})
            _expect_error(lambda: store.delete_thread(thread_id),
                          "会话删除事件与恢复标记冲突", "删除事件冲突")
            checked += 1
        finally:
            store.close()
    # 行为：损坏、重复与非法帧都必须拒绝。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("拒绝")["id"]
            with store.events_path.open("ab") as handle:
                handle.write(b'{"type": "event"\n')
            with store._index.transaction() as connection:
                _expect_error(lambda: store._rewrite_events_for_deletion(connection, _intent(thread_id, "a" * 32)),
                              "事件日志损坏，无法安全删除会话", "损坏行")
                checked += 1
            store.events_path.write_bytes(b"")
            for label, record, message in (
                ("格式", {"type": "event"}, "事件日志格式无效，无法安全删除会话"),
                ("游标", {"type": "event", "timestamp": "t", "method": "m",
                          "params": {"eventId": "a" * 32, "eventCursor": "0"}},
                 "事件日志游标无效，无法安全删除会话"),
                ("会话编号", {"type": "event", "timestamp": "t", "method": "m",
                              "params": {"eventId": "a" * 32, "eventCursor": "1", "threadId": "zzz"}},
                 "事件日志会话 ID 无效，无法安全删除会话"),
            ):
                with store.events_path.open("ab") as handle:
                    handle.write((json.dumps(record) + "\n").encode("utf-8"))
                with store._index.transaction() as connection:
                    _expect_error(lambda: store._rewrite_events_for_deletion(connection, _intent(thread_id, "b" * 32)),
                                  message, label)
                    checked += 1
                store.events_path.write_bytes(b"")
            repeated = {"type": "event", "timestamp": "t", "method": "m",
                        "params": {"eventId": "c" * 32, "eventCursor": "1", "threadId": thread_id}}
            other = {"type": "event", "timestamp": "t", "method": "m",
                     "params": {"eventId": "d" * 32, "eventCursor": "1", "threadId": thread_id}}
            with store.events_path.open("ab") as handle:
                handle.write((json.dumps(repeated) + "\n").encode("utf-8"))
                handle.write((json.dumps(other) + "\n").encode("utf-8"))
            with store._index.transaction() as connection:
                _expect_error(lambda: store._rewrite_events_for_deletion(connection, _intent(thread_id, "b" * 32)),
                              "事件日志存在重复游标，无法安全删除会话", "重复游标")
                checked += 1
            store.events_path.write_bytes(b"")
            with store.events_path.open("ab") as handle:
                handle.write((json.dumps(repeated) + "\n").encode("utf-8"))
                handle.write((json.dumps({**repeated, "params": {**repeated["params"], "eventCursor": "2"}}) + "\n").encode("utf-8"))
            with store._index.transaction() as connection:
                _expect_error(lambda: store._rewrite_events_for_deletion(connection, _intent(thread_id, "b" * 32)),
                              "事件日志存在重复事件 ID，无法安全删除会话", "重复事件")
                checked += 1
        finally:
            store.close()
    # 行为：符号链接日志与缺失日志。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("链接")["id"]
            target = Path(temporary) / "elsewhere.jsonl"
            target.write_bytes(b"")
            store.events_path.unlink(missing_ok=True)
            store.events_path.symlink_to(target)
            with store._index.transaction() as connection:
                _expect_error(lambda: store._rewrite_events_for_deletion(connection, _intent(thread_id, "a" * 32)),
                              "事件日志不是普通私有文件，清理已暂停", "符号链接")
                checked += 1
            store.events_path.unlink()
            event = store.delete_thread(thread_id)
            lines = _lines(store)
            if (event.get("params", {}).get("eventCursor") != "1"
                    or len(lines) != 1 or lines[0].get("method") != "thread/deleted"):
                raise ValueError("缺失事件日志时必须新建并写入删除事件")
            checked += 1
        finally:
            store.close()
    # 行为：高水位与旧删除事件查找。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("高水位")["id"]
            with store._index.transaction() as connection:
                if store._event_high_water(connection) != 0:
                    raise ValueError("空索引的高水位必须为零")
                checked += 1
                connection.execute("INSERT INTO events(cursor,event_id,method,thread_id,params_json) "
                                   "VALUES(5,?,'turn/stream',NULL,'{}')", ("b" * 32,))
                if store._event_high_water(connection) != 5:
                    raise ValueError("高水位必须取索引最大游标")
                checked += 1
            with store._index.transaction() as connection:
                if store._previous_deletion_event(connection, thread_id) is not None:
                    raise ValueError("没有删除事件时必须返回空")
                checked += 1
                connection.execute("INSERT INTO events(cursor,event_id,method,thread_id,params_json) "
                                   "VALUES(11,?,'thread/deleted',NULL,?)", ("c" * 32, "not json"))
                if store._previous_deletion_event(connection, thread_id) is not None:
                    raise ValueError("无法解析的索引行必须跳过")
                checked += 1
                connection.execute("INSERT INTO events(cursor,event_id,method,thread_id,params_json) "
                                   "VALUES(12,?,'thread/deleted',NULL,'[]')", ("d" * 32,))
                if store._previous_deletion_event(connection, thread_id) is not None:
                    raise ValueError("非对象的索引行必须跳过")
                checked += 1
                connection.execute("INSERT INTO events(cursor,event_id,method,thread_id,params_json) "
                                   "VALUES(13,?,'thread/deleted',NULL,?)",
                                   ("e" * 32, json.dumps({"deletedThreadId": thread_id})))
                found = store._previous_deletion_event(connection, thread_id)
                if found != {"method": "thread/deleted", "params": {"deletedThreadId": thread_id}}:
                    raise ValueError("匹配的删除事件必须按会话返回")
                checked += 1
                if store._previous_deletion_event(connection, "000000000000") is not None:
                    raise ValueError("其他会话不得匹配删除事件")
                checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_event_rewrite()
    except (ValueError, SyntaxError) as error:
        print(f"事件日志重写核对失败，{error}", file=sys.stderr)
        return 2
    print(f"事件日志重写一致：{checked} 项校验、游标与发布校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
