#!/usr/bin/env python3
"""核对会话条目快照的生命周期、读取边界与冻结快照读取源。

`open_entries_snapshot` 在写锁内打开日志、用 `_complete_record_limit` 把可读前缀
钉在最后一条完整记录上，再交出 `SessionEntriesSnapshot`；打不开或取长度失败时必须
关闭文件。快照对象可重入读取：每次迭代回到开头、行号从零计数、按钉住的前缀字节
上限逐行读取、跳过空行、解码失败由解码器报错；已关闭的快照在进入与迭代时都拒绝。
冻结快照还依赖 `snapshot_projection`（删除意图、索引同源、最多 50 回合、逐回合
UTF-8 字节预算与截断）与 `open_snapshot_source`（事件检查点同源、事件游标、完整
记录前缀）；这里固定这些规则，避免重构后读到半写记录、重复读取从中间继续或泄漏
文件描述符，并直接实例化快照、打开真实临时日志核对运行行为。
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
import boss_harness.session as session_module  # noqa: E402
from boss_harness.session import SessionEntriesSnapshot, SessionStore  # noqa: E402

# 打开顺序：写锁 → 会话存在 → 二进制打开 → fstat → 完整记录前缀 → 交出快照；
# 任何异常都必须先关闭文件。
OPEN_ORDER = (
    "def open_entries_snapshot(self, thread_id: str) -> SessionEntriesSnapshot:",
    "with self._lock:",
    "self.require_thread(thread_id)",
    'source = self.path_for(thread_id).open("rb")',
    "stat_result = os.fstat(source.fileno())",
    "size = _complete_record_limit(source, stat_result.st_size)",
    "return SessionEntriesSnapshot(source, size,",
    "stat_result.st_mtime_ns, stat_result.st_ino)",
    "except BaseException:",
    "source.close()",
    "raise",
)
# 快照对象：存储前缀标识 → stamp 顺序 → 进入 / 退出 → 关闭 → 重入迭代边界。
CLASS_ORDER = (
    "class SessionEntriesSnapshot:",
    "def __init__(self, source: io.BufferedReader, size: int, mtime_ns: int, inode: int) -> None:",
    "self._source = source",
    "self._size = size",
    "self.mtime_ns = mtime_ns",
    "self.inode = inode",
    "self.line_count = 0",
    "def stamp(self) -> tuple[int, int, int]:",
    "return self._size, self.mtime_ns, self.inode",
    "def __enter__(self) -> SessionEntriesSnapshot:",
    "if self._source.closed:",
    'raise ValueError("会话快照已关闭")',
    "def __exit__(self, *_: object) -> None:",
    "self.close()",
    "def close(self) -> None:",
    "self._source.close()",
    "def __iter__(self):",
    "if self._source.closed:",
    "self._source.seek(0)",
    "self.line_count = 0",
    "for line_number, raw_line in enumerate(_iter_bounded_raw_lines_from_handle(",
    'self._source, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",',
    "universal_newlines=True, byte_limit=self._size), start=1):",
    "self.line_count = line_number",
    "if not raw_line.strip():",
    "continue",
    "data = _decode_session_record(raw_line, line_number=line_number)",
    "yield data",
)
# 快照投影：删除意图 → 索引读取与同源校验 → 可跳过回合 → 上限 50 → 逐回合字节
# 预算与截断 → 损坏重建。
PROJECTION_ORDER = (
    "def snapshot_projection(self, thread_id: str, *, include_turns: bool = True,",
    "if self._delete_intent_path(thread_id).exists():",
    'raise ValueError("会话正在删除，暂不可读取")',
    '"SELECT id,metadata_json,indexed_size,indexed_mtime_ns FROM threads WHERE id=?"',
    'raise ValueError("会话不存在")',
    'raise ValueError("会话索引与日志不同步，请重试冻结快照")',
    'if not include_turns:\n                        return metadata, turns, False',
    'WHERE thread_id=? ORDER BY first_ordinal,turn_id LIMIT 50"',
    'turn_bytes += len(raw.encode("utf-8"))',
    "if turn_bytes > max_turn_bytes:\n                            return metadata, turns, True",
    "\n                return metadata, turns, False",
    "return self._with_repaired_index(read)",
)
# 快照源：写锁 → 会话存在 → 事件检查点与日志同源 → 事件游标 → 二进制打开 →
# 完整记录前缀 → 读回起点；失败时关闭文件。
SNAPSHOT_SOURCE_ORDER = (
    "def open_snapshot_source(self, thread_id: str) -> tuple[io.BufferedReader, int, str]:",
    "with self._lock:",
    "self.require_thread(thread_id)",
    "\"SELECT value FROM checkpoints WHERE name='events'\"",
    "if self.events_path.exists():",
    "if event_checkpoint is None or event_checkpoint[\"value\"] != fingerprint:",
    'raise ValueError("事件索引与日志不同步，请重试冻结快照")',
    '"SELECT COALESCE(MAX(cursor),0) FROM events"',
    'source = self.path_for(thread_id).open("rb")',
    "size = _complete_record_limit(source, os.fstat(source.fileno()).st_size)",
    "source.seek(0)",
    "return source, size, cursor",
    "source.close()",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


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
        raise ValueError(
            f"条目快照行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"条目快照行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"条目快照行为变化 {label}：期望 ValueError")


_HEADER = b'{"type": "session", "id": "s1", "timestamp": "t0", "payload": {}}\n'


def _record(record_id: str) -> bytes:
    payload = {"type": "turn", "id": record_id, "timestamp": "t",
               "parentId": None, "payload": {}}
    return (json.dumps(payload) + "\n").encode("utf-8")


def _snapshot(data: bytes, size: int | None = None) -> SessionEntriesSnapshot:
    return SessionEntriesSnapshot(
        io.BytesIO(data), len(data) if size is None else size, 123, 456)


class _Tracked:
    def __init__(self, handle) -> None:
        self._handle = handle
        self.closed = False

    def fileno(self) -> int:
        return self._handle.fileno()

    def seek(self, *args):
        return self._handle.seek(*args)

    def read(self, *args):
        return self._handle.read(*args)

    def close(self) -> None:
        self.closed = True
        self._handle.close()


class _PathProxy:
    def __init__(self, path: Path, events: list[str], tracker=None) -> None:
        self._path = path
        self._events = events
        self._tracker = tracker

    def open(self, mode: str):
        self._events.append("open")
        handle = self._path.open(mode)
        return self._tracker(handle) if self._tracker is not None else handle


class _QueryStore:
    def __init__(self, path: Path) -> None:
        self._lock = threading.Lock()
        self.events: list[str] = []
        self._path = path
        self.tracker = None

    def require_thread(self, thread_id: str) -> dict:
        self.events.append("locked" if self._lock.locked() else "unlocked")
        return {"id": thread_id}

    def path_for(self, thread_id: str) -> _PathProxy:
        self.events.append("path")
        return _PathProxy(self._path, self.events, self.tracker)


def _snapshot_behavior_checks() -> int:
    header, first, second = _HEADER, _record("a"), _record("b")
    checked = 0
    # 前缀与行计数：空文件与只有会话头都不产出记录。
    empty = _snapshot(b"")
    checked += _expect_value(list(empty), [], "空前缀记录")
    checked += _expect_value(empty.line_count, 0, "空前缀行数")
    only_header = _snapshot(header)
    checked += _expect_value(list(only_header), [], "会话头跳过")
    checked += _expect_value(only_header.line_count, 1, "会话头行数")
    # 记录按行解码，空行跳过但计入行号。
    data = header + first + b"\n" + second
    snapshot = _snapshot(data)
    checked += _expect_value([r["id"] for r in snapshot], ["a", "b"], "记录顺序")
    checked += _expect_value(snapshot.line_count, 4, "空行计入行号")
    # 重入迭代：回到开头并重置行数。
    checked += _expect_value([r["id"] for r in snapshot], ["a", "b"], "重入迭代")
    checked += _expect_value(snapshot.line_count, 4, "重入行数")
    # 前缀字节上限：固定范围之外的记录不可见。
    pinned = _snapshot(header + first + second, size=len(header) + len(first))
    checked += _expect_value([r["id"] for r in pinned], ["a"], "前缀上限")
    checked += _expect_value(pinned.line_count, 2, "前缀行数")
    # 固定范围超过实际内容时按读取不完整报错。
    checked += _expect_error(
        lambda: list(_snapshot(header, size=len(header) + 1)),
        "会话日志快照读取不完整", "前缀不足")
    # stamp 携带固定范围、mtime 与 inode。
    checked += _expect_value(_snapshot(data).stamp, (len(data), 123, 456), "stamp")
    # 关闭后进入与迭代都拒绝；上下文管理器退出即关闭。
    closed = _snapshot(data)
    closed.close()
    checked += _expect_error(lambda: list(closed), "会话快照已关闭", "关闭后迭代")
    checked += _expect_error(closed.__enter__, "会话快照已关闭", "关闭后进入")
    with _snapshot(data) as managed:
        checked += _expect_value([r["id"] for r in managed], ["a", "b"], "上下文迭代")
    checked += _expect_error(lambda: list(managed), "会话快照已关闭", "退出即关闭")
    # 损坏记录：格式无效、重复会话头、坏 JSON 与非 UTF-8 都停止读取。
    checked += _expect_error(
        lambda: list(_snapshot(header + b"{}\n")),
        "会话日志第 2 行格式无效，读取已停止", "格式无效")
    checked += _expect_error(
        lambda: list(_snapshot(header + header)),
        "会话日志第 2 行出现重复会话头，读取已停止", "重复会话头")
    checked += _expect_error(
        lambda: list(_snapshot(header + b"{\n")),
        "会话日志第 2 行损坏，读取已停止", "坏 JSON")
    checked += _expect_error(
        lambda: list(_snapshot(header + b"\xff\n")),
        "会话日志第 2 行损坏，读取已停止", "非 UTF-8")
    # CRLF 记录与 LF 等价。
    checked += _expect_value(
        [r["id"] for r in _snapshot(header.replace(b"\n", b"\r\n")
                                    + first.replace(b"\n", b"\r\n"))],
        ["a"], "CRLF 记录")
    return checked


def _open_behavior_checks() -> int:
    header, first, second = _HEADER, _record("a"), _record("b")
    checked = 0
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        # 完整记录：范围等于文件大小，锁内先核对会话再打开。
        full = root / "full.jsonl"
        full.write_bytes(header + first + second)
        store = _QueryStore(full)
        snapshot = SessionStore.open_entries_snapshot(store, "thread")
        checked += _expect_value([r["id"] for r in snapshot], ["a", "b"], "打开后迭代")
        checked += _expect_value(store.events, ["locked", "path", "open"], "锁内顺序")
        stat_result = full.stat()
        checked += _expect_value(
            (snapshot.stamp[0], snapshot.inode, snapshot.mtime_ns),
            (stat_result.st_size, stat_result.st_ino, stat_result.st_mtime_ns),
            "打开后身份")
        # 末尾残段被裁掉，只读取完整记录。
        partial = root / "partial.jsonl"
        partial.write_bytes(header + first + b'{"type": "tu')
        snapshot = SessionStore.open_entries_snapshot(_QueryStore(partial), "thread")
        checked += _expect_value([r["id"] for r in snapshot], ["a"], "残段裁剪")
        checked += _expect_value(
            snapshot.stamp[0], len(header) + len(first), "残段范围")
        # 空文件与纯残段都固定为空前缀。
        blank = root / "blank.jsonl"
        blank.write_bytes(b"")
        checked += _expect_value(
            SessionStore.open_entries_snapshot(_QueryStore(blank), "thread").stamp[0],
            0, "空文件范围")
        residue = root / "residue.jsonl"
        residue.write_bytes(b'{"type"')
        checked += _expect_value(
            SessionStore.open_entries_snapshot(_QueryStore(residue), "thread").stamp[0],
            0, "纯残段范围")
        # 无任何换行且超过单行窗口时拒绝固定前缀。
        oversized = root / "oversized.jsonl"
        oversized.write_bytes(b"x" * 10)
        original_limit = session_module.MAX_SESSION_LINE_BYTES
        session_module.MAX_SESSION_LINE_BYTES = 8
        try:
            checked += _expect_error(
                lambda: SessionStore.open_entries_snapshot(_QueryStore(oversized), "thread"),
                "会话日志末尾缺少完整记录边界", "超长残段")
        finally:
            session_module.MAX_SESSION_LINE_BYTES = original_limit
        # 取长度失败时关闭已打开的文件并上报原始异常。
        def boom(handle, size):
            raise RuntimeError("boom")

        original_complete = session_module._complete_record_limit
        tracked = _Tracked(tempfile.TemporaryFile())
        store = _QueryStore(full)
        store.tracker = lambda handle: tracked
        session_module._complete_record_limit = boom
        try:
            SessionStore.open_entries_snapshot(store, "thread")
        except RuntimeError as error:
            checked += _expect_value(str(error), "boom", "取长度失败上报")
        else:
            raise ValueError("条目快照行为变化 取长度失败：期望 RuntimeError")
        finally:
            session_module._complete_record_limit = original_complete
        checked += _expect_value(tracked.closed, True, "取长度失败关闭")
        # 打不开时直接上报，不再尝试关闭不存在的句柄。
        store = _QueryStore(root / "missing.jsonl")
        try:
            SessionStore.open_entries_snapshot(store, "thread")
        except FileNotFoundError:
            checked += _expect_value(store.events, ["locked", "path", "open"], "打开失败顺序")
        else:
            raise ValueError("条目快照行为变化 打开失败：期望 FileNotFoundError")
    return checked


def _snapshot_source_checks() -> int:
    # 冻结快照读取源：投影的预算 / 上限 / 同源与快照源的游标 / 完整记录边界。
    checked = 0
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("快照投影")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            store.record_turn(thread_id, "turn-b", "completed")
            metadata, turns, truncated = store.snapshot_projection(thread_id)
            checked += _expect_value(
                (metadata.get("id"), metadata.get("title"),
                 [turn.get("turnId") for turn in turns], truncated),
                (thread_id, "快照投影", ["turn-a", "turn-b"], False), "投影缺省")
            checked += _expect_value(
                store.snapshot_projection(thread_id, include_turns=False)[1:],
                ([], False), "跳过回合")
            checked += _expect_value(
                store.snapshot_projection(thread_id, max_turn_bytes=10)[1:],
                ([], True), "预算截断")
            # 损坏的回合投影按会话重建后返回。
            with store._index.transaction() as connection:
                connection.execute(
                    "UPDATE turns SET metadata_json='not-json'"
                    " WHERE thread_id=? AND turn_id='turn-a'", (thread_id,))
            repaired = store.snapshot_projection(thread_id)[1]
            checked += _expect_value(
                [turn.get("turnId") for turn in repaired], ["turn-a", "turn-b"], "损坏重建")
            intent = store._delete_intent_path(thread_id)
            intent.write_text("deleting", encoding="utf-8")
            checked += _expect_error(
                lambda: store.snapshot_projection(thread_id),
                "会话正在删除，暂不可读取", "删除意图")
            intent.unlink()
            checked += _expect_error(
                lambda: store.snapshot_projection("000000000000"),
                "会话不存在", "未知会话")
            # 源文件大小变化使索引不同步。
            with store.path_for(thread_id).open("ab") as handle:
                handle.write(b"{}\n")
            checked += _expect_error(
                lambda: store.snapshot_projection(thread_id),
                "会话索引与日志不同步，请重试冻结快照", "索引不同步")
        finally:
            store.close()
    # 50 回合上限单独用新会话，避免上面的损坏与追加影响。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("回合上限")["id"]
            for index in range(51):
                store.record_turn(thread_id, f"turn-{index:02d}", "completed")
            projection = store.snapshot_projection(thread_id)
            checked += _expect_value(
                ([turn.get("turnId") for turn in projection[1]][:2],
                 len(projection[1]), projection[2]),
                (["turn-00", "turn-01"], 50, False), "回合上限")
        finally:
            store.close()
    # 快照源：完整记录前缀、事件游标递增、残段边界、损坏检查点与未知会话。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("快照源")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            path = store.path_for(thread_id)
            expected = path.read_bytes()
            source, size, cursor = store.open_snapshot_source(thread_id)
            try:
                data = source.read()
            finally:
                source.close()
            checked += _expect_value(
                (size, len(data), data == expected, cursor),
                (len(expected), len(expected), True, "0"), "快照源")
            store.append_event("probe/event", {"x": 1})
            source, size, cursor = store.open_snapshot_source(thread_id)
            source.close()
            checked += _expect_value(cursor, "1", "事件游标")
            # 末尾半写记录只固定到最后一个完整换行。
            with path.open("ab") as handle:
                handle.write(b'{"partial"')
            source, size, cursor = store.open_snapshot_source(thread_id)
            try:
                clipped = source.read()
            finally:
                source.close()
            checked += _expect_value(
                (size, clipped[:size] == expected, size <= path.stat().st_size),
                (len(expected), True, True), "残段边界")
            with store._index.transaction() as connection:
                connection.execute(
                    "UPDATE checkpoints SET value='999' WHERE name='events'")
            checked += _expect_error(
                lambda: store.open_snapshot_source(thread_id),
                "事件索引与日志不同步，请重试冻结快照", "检查点不同步")
            checked += _expect_error(
                lambda: store.open_snapshot_source("000000000000"),
                "会话不存在", "未知会话源")
        finally:
            store.close()
    return checked


def check_entries_snapshot() -> int:
    source = _read(SESSION)
    start = source.index("def open_entries_snapshot(")
    end = source.find("\n    def ", start + 1)
    opener = source[start:] if end < 0 else source[start:end]
    class_start = source.index("class SessionEntriesSnapshot:")
    class_end = source.find("\n\ndef ", class_start + 1)
    snapshot = source[class_start:] if class_end < 0 else source[class_start:class_end]
    projection_start = source.index("def snapshot_projection(")
    projection_end = source.find("\n    def ", projection_start + 1)
    projection = (source[projection_start:] if projection_end < 0
                  else source[projection_start:projection_end])
    source_start = source.index("def open_snapshot_source(")
    source_end = source.find("\n    def ", source_start + 1)
    snapshot_source = (source[source_start:] if source_end < 0
                       else source[source_start:source_end])
    checked = _ordered(OPEN_ORDER, opener, SESSION)
    checked += _ordered(CLASS_ORDER, snapshot, SESSION)
    checked += _ordered(PROJECTION_ORDER, projection, SESSION)
    checked += _ordered(SNAPSHOT_SOURCE_ORDER, snapshot_source, SESSION)
    # 投影回合上限必须唯一，损坏投影必须交给单会话重建重试。
    if projection.count('LIMIT 50"') != 1 or projection.count("_with_repaired_index(read)") != 1:
        raise ValueError(f"{SESSION} 的快照投影必须固定 50 回合上限并重建重试")
    checked += 1
    # 快照源失败路径必须在 BaseException 上关闭已打开文件。
    if (snapshot_source.count("except BaseException:") != 1
            or snapshot_source.count("source.close()") != 1):
        raise ValueError(f"{SESSION} 的快照源失败路径必须关闭文件")
    checked += 1
    # 可读前缀必须钉在最后一条完整记录上，不能直接使用文件大小。
    if "stat_result.st_size)" not in opener or "size = stat_result.st_size" in opener:
        raise ValueError(f"{SESSION} 的快照前缀必须裁到完整记录")
    checked += 1
    # 已关闭快照必须在进入与迭代两处拒绝。
    if snapshot.count('raise ValueError("会话快照已关闭")') != 2:
        raise ValueError(f"{SESSION} 的已关闭快照必须在进入与迭代时拒绝")
    checked += 1
    # 迭代必须钉住字节上限并跳过空行，不能读穿前缀。
    if "byte_limit=self._size" not in snapshot or "MAX_SESSION_LINE_BYTES" not in snapshot:
        raise ValueError(f"{SESSION} 的快照迭代必须受前缀与行长度上限约束")
    checked += 1
    # stamp 必须同时携带前缀大小、mtime 与 inode，供后续读取比对身份。
    if "return self._size, self.mtime_ns, self.inode" not in snapshot:
        raise ValueError(f"{SESSION} 的快照 stamp 必须携带 size / mtime / inode")
    checked += 1
    return (checked + _snapshot_behavior_checks() + _open_behavior_checks()
            + _snapshot_source_checks())


def main() -> int:
    try:
        checked = check_entries_snapshot()
    except ValueError as error:
        print(f"条目快照核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目快照一致：{checked} 项前缀、生命周期、冻结读取源与重入读取校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
