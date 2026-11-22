#!/usr/bin/env python3
"""核对会话读取缓存与增量解析口径。

`SessionStore.read_entries` 以 `(size, mtime_ns, ino)` 三元组命中缓存，命中时
返回副本；未命中时优先按「同一 inode、严格更短、旧前缀末尾仍是换行」做增量
解析，否则全量重解。只有完整记录边界才写缓存，空文件不缓存。快照路径在锁内
查缓存、锁外解码，随后复核文件 stamp 未变才写回。缓存按 `_MAX_ENTRIES_CACHE_THREADS`
做最近使用淘汰。这里按源码顺序固定这些条件，避免截断重写、追加掩盖或副本语义
被重构放松。
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import (  # noqa: E402
    Entry,
    SessionStore,
    _encode_session_line,
)

READ_ORDER = (
    "def read_entries(self, thread_id: str) -> list[dict]:",
    "with self._lock:",
    "self.require_thread(thread_id)",
    'with self.path_for(thread_id).open("rb") as handle:',
    "stat_result = os.fstat(handle.fileno())",
    "stamp = (stat_result.st_size, stat_result.st_mtime_ns, stat_result.st_ino)",
    "cached = self._touch_cached_entries(thread_id, stamp)",
    "if cached is not None:",
    "return list(cached[2])",
    "previous = self._appendable_entries(thread_id, stamp, handle)",
    "if previous is not None:",
    "entries, line_count = self._read_appended_entries(handle, previous, stamp)",
    "else:",
    "entries, line_count = self._read_all_entries(handle, stamp)",
    "if self._line_boundary(handle, stamp[0]):",
    "self._store_entries(thread_id, stamp, line_count, entries)",
    "return list(entries)",
)
SNAPSHOT_ORDER = (
    "def read_entries_snapshot(self, thread_id: str) -> list[dict]:",
    "with self._lock:",
    "self.require_thread(thread_id)",
    "stamp = self._entries_stamp(thread_id)",
    "cached = self._touch_cached_entries(thread_id, stamp)",
    "if cached is not None:",
    "return list(cached[2])",
    "with self.open_entries_snapshot(thread_id) as snapshot:",
    "entries = list(snapshot)",
    "line_count = snapshot.line_count",
    "with self._lock:",
    "current = self._entries_stamp(thread_id)",
    "except (FileNotFoundError, ValueError):",
    "current = None",
    "if current == snapshot.stamp:",
    "self._store_entries(thread_id, current, line_count, entries)",
    "return list(entries)",
)
TOUCH_ORDER = (
    "def _touch_cached_entries(self, thread_id: str, stamp: tuple[int, int, int]):",
    "cached = self._entries_cache.get(thread_id)",
    "if cached is None or cached[0] != stamp:",
    "return None",
    "self._entries_cache.pop(thread_id, None)",
    "self._entries_cache[thread_id] = cached",
    "return cached",
)
APPENDABLE_ORDER = (
    "def _appendable_entries(self, thread_id: str, stamp: tuple[int, int, int], handle):",
    "cached = self._entries_cache.get(thread_id)",
    "if cached is None:",
    "return None",
    "(size, _, inode), line_count, entries = cached",
    "if inode != stamp[2] or not 0 < size < stamp[0]:",
    "return None",
    "handle.seek(size - 1)",
    'if handle.read(1) != b"\\n":',
    "return None",
    "self._entries_cache.pop(thread_id, None)",
    "self._entries_cache[thread_id] = cached",
    "return size, line_count, entries",
)
ALL_ORDER = (
    "def _read_all_entries(self, handle, stamp: tuple[int, int, int]) -> tuple[list[dict], int]:",
    "handle.seek(0)",
    "out: list[dict] = []",
    "line_count = 0",
    "for line_count, line in enumerate(_iter_bounded_raw_lines_from_handle(",
    'handle, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",',
    "universal_newlines=True, byte_limit=stamp[0]), start=1):",
    "if not line.strip():",
    "data = _decode_session_record(line, line_number=line_count)",
    "return out, line_count",
)
APPENDED_ORDER = (
    "def _read_appended_entries(self, handle, previous: tuple[int, int, list[dict]],",
    "stamp: tuple[int, int, int]) -> tuple[list[dict], int]:",
    "size, line_count, entries = previous",
    "handle.seek(size)",
    "appended: list[dict] = []",
    "added = 0",
    "for added, line in enumerate(_iter_bounded_raw_lines_from_handle(",
    'handle, maximum=MAX_SESSION_LINE_BYTES, label="会话日志",',
    "universal_newlines=True, byte_limit=stamp[0] - size), start=1):",
    "data = _decode_session_record(line, line_number=line_count + added)",
    "return entries + appended, line_count + added",
)
BOUNDARY_ORDER = (
    "def _line_boundary(self, handle, size: int) -> bool:",
    "if size <= 0:",
    "return False",
    "handle.seek(size - 1)",
    'return handle.read(1) == b"\\n"',
)
STORE_ORDER = (
    "def _store_entries(self, thread_id: str, stamp: tuple[int, int, int], line_count: int,",
    "entries: list[dict]) -> None:",
    "self._entries_cache.pop(thread_id, None)",
    "self._entries_cache[thread_id] = (stamp, line_count, entries)",
    "while len(self._entries_cache) > _MAX_ENTRIES_CACHE_THREADS:",
    "self._entries_cache.pop(next(iter(self._entries_cache)))",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SessionStore":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SessionStore.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _entry(entry_id: str, text: str = "记录") -> dict:
    return Entry(type="item", id=entry_id,
                 payload={"kind": "assistantMessage", "text": text}).to_dict()


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"会话读取缓存行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"会话读取缓存行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"会话读取缓存行为变化 {label}：期望错误 {message!r}，实际未抛出")


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        thread = store.create("缓存")["id"]
        path = store.path_for(thread)
        header = path.read_bytes()

        entries = store.read_entries(thread)
        checked += _expect_value(entries, [], "空会话条目")
        cached = store._entries_cache.get(thread)
        checked += _expect_value(cached is not None and cached[1], 1, "完整边界写入缓存")
        entries.append(_entry("leak"))
        second = store.read_entries(thread)
        checked += _expect_value((second, entries is second), ([], False), "命中返回副本")

        store.append(thread, Entry(type="item", id="a1",
                                   payload={"kind": "assistantMessage", "text": "A"}))
        checked += _expect_value([row["id"] for row in store.read_entries(thread)], ["a1"],
                                 "追加后读取")
        cached = store._entries_cache.get(thread)
        stat = path.stat()
        checked += _expect_value(cached[0], (stat.st_size, stat.st_mtime_ns, stat.st_ino),
                                 "追加后缓存 stamp")

        store._append_line(path, _entry("a2", "B"))
        checked += _expect_value([row["id"] for row in store.read_entries(thread)],
                                 ["a1", "a2"], "外部追增读取")
        checked += _expect_value(store._entries_cache[thread][1], 3, "增量解析接续行号")

        path.write_bytes(header + _encode_session_line(_entry("b1", "短")))
        checked += _expect_value([row["id"] for row in store.read_entries(thread)], ["b1"],
                                 "截断重写不返回前缀")

        path.write_bytes(header + _encode_session_line(_entry("c1", "X")))
        store.read_entries(thread)
        path.write_bytes(header + _encode_session_line(_entry("c1", "Y")))
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        checked += _expect_value(store.read_entries(thread)[0]["payload"]["text"], "Y",
                                 "同尺寸改写重新解析")

        path.write_bytes(header + _encode_session_line(_entry("d1", "更长的记录" * 3)))
        checked += _expect_value([row["id"] for row in store.read_entries(thread)], ["d1"],
                                 "旧前缀非换行时重新解析")

        replacement = Path(str(path) + ".new")
        replacement.write_bytes(header + _encode_session_line(_entry("e1", "替换记录" * 4)))
        os.replace(replacement, path)
        checked += _expect_value([row["id"] for row in store.read_entries(thread)], ["e1"],
                                 "inode 替换重新解析")

        before_partial = path.stat().st_size
        line = _encode_session_line(_entry("f1", "补齐"))
        with path.open("ab") as handle:
            handle.write(line[: len(line) // 2])
        checked += _expect_value([row["id"] for row in store.read_entries(thread)], ["e1"],
                                 "尾残段不进入条目")
        checked += _expect_value(store._entries_cache[thread][0][0], before_partial,
                                 "尾残段不推进缓存")
        with path.open("ab") as handle:
            handle.write(line[len(line) // 2:])
        checked += _expect_value([row["id"] for row in store.read_entries(thread)],
                                 ["e1", "f1"], "补齐残段后读取")

        with path.open("rb") as handle:
            checked += _expect_value(store._line_boundary(handle, 0), False,
                                     "空文件无完整边界")
            checked += _expect_value(store._line_boundary(handle, len(header)), True,
                                     "换行结尾为完整边界")
        with path.open("ab") as handle:
            handle.write(b"{")
        with path.open("rb") as handle:
            checked += _expect_value(
                store._line_boundary(handle, path.stat().st_size), False,
                "无换行结尾非完整边界")

    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        threads = [store.create(f"缓存 {index}")["id"] for index in range(4)]
        for thread_id in threads:
            store.read_entries(thread_id)
        checked += _expect_value(len(store._entries_cache), 4, "缓存达到上限")
        store.read_entries(threads[0])
        fifth = store.create("缓存 4")["id"]
        store.read_entries(fifth)
        checked += _expect_value(
            (threads[0] in store._entries_cache, threads[1] in store._entries_cache,
             threads[2] in store._entries_cache, len(store._entries_cache)),
            (True, False, True, 4), "最近使用淘汰")

        thread = threads[2]
        checked += _expect_value(store.read_entries_snapshot(thread), [], "快照空会话")
        store.append(thread, Entry(type="item", id="g1",
                                   payload={"kind": "assistantMessage", "text": "快照"}))
        checked += _expect_value([row["id"] for row in store.read_entries_snapshot(thread)],
                                 ["g1"], "快照包含追加条目")
        snapshot = store.read_entries_snapshot(thread)
        snapshot.append(_entry("leak"))
        checked += _expect_value(
            [row["id"] for row in store.read_entries_snapshot(thread)], ["g1"],
            "快照命中返回副本")

    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        thread = store.create("损坏")["id"]
        path = store.path_for(thread)
        path.write_bytes(path.read_bytes() + b"{}\n")
        for label in ("首次", "再次"):
            checked += _expect_error(
                lambda: store.read_entries(thread),
                "会话日志第 2 行格式无效，读取已停止", f"损坏行{label}拒绝")
        checked += _expect_value(store._entries_cache[thread][0][0], len(header),
                                 "损坏行不推进缓存")
    return checked


def check_entries_cache() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    read = _method(tree, source, "read_entries")
    snapshot = _method(tree, source, "read_entries_snapshot")
    touch = _method(tree, source, "_touch_cached_entries")
    appendable = _method(tree, source, "_appendable_entries")
    all_entries = _method(tree, source, "_read_all_entries")
    appended = _method(tree, source, "_read_appended_entries")
    boundary = _method(tree, source, "_line_boundary")
    store = _method(tree, source, "_store_entries")
    checked = _ordered(READ_ORDER, read, SESSION)
    checked += _ordered(SNAPSHOT_ORDER, snapshot, SESSION)
    checked += _ordered(TOUCH_ORDER, touch, SESSION)
    checked += _ordered(APPENDABLE_ORDER, appendable, SESSION)
    checked += _ordered(ALL_ORDER, all_entries, SESSION)
    checked += _ordered(APPENDED_ORDER, appended, SESSION)
    checked += _ordered(BOUNDARY_ORDER, boundary, SESSION)
    checked += _ordered(STORE_ORDER, store, SESSION)
    # 读取路径只能通过辅助函数访问缓存，返回的列表必须是副本。
    if "_entries_cache" in read:
        raise ValueError(f"{SESSION} 的 read_entries 必须经缓存辅助函数访问")
    checked += 1
    if read.count("return list(cached[2])") != 1 or read.count("return list(entries)") != 1:
        raise ValueError(f"{SESSION} 的 read_entries 必须返回缓存副本")
    checked += 1
    if snapshot.count("return list(cached[2])") != 1 or snapshot.count("return list(entries)") != 1:
        raise ValueError(f"{SESSION} 的快照读取必须返回缓存副本")
    checked += 1
    # 空文件或半条记录不进入缓存。
    if '                if self._line_boundary(handle, stamp[0]):\n                    self._store_entries(thread_id, stamp, line_count, entries)' not in read:
        raise ValueError(f"{SESSION} 的 read_entries 必须只在完整记录边界缓存")
    checked += 1
    if boundary.count("if size <= 0:") != 1 or 'return handle.read(1) == b"\\n"' not in boundary:
        raise ValueError(f"{SESSION} 的完整边界必须拒绝空文件并以换行判定")
    checked += 1
    # 快照：解码后复核 stamp 未变才缓存，缺失或损坏时不缓存。
    if '            if current == snapshot.stamp:\n                self._store_entries(thread_id, current, line_count, entries)' not in snapshot:
        raise ValueError(f"{SESSION} 的快照必须复核 stamp 后才缓存")
    checked += 1
    if "            except (FileNotFoundError, ValueError):\n                current = None" not in snapshot:
        raise ValueError(f"{SESSION} 的快照必须把缺失或损坏按不缓存处理")
    checked += 1
    if '        with self._lock:\n            self.require_thread(thread_id)\n            stamp = self._entries_stamp(thread_id)\n            cached = self._touch_cached_entries(thread_id, stamp)' not in snapshot:
        raise ValueError(f"{SESSION} 的快照必须先于锁外解码检查缓存")
    checked += 1
    # 缓存命中要求三元组完全一致，并把命中项移到末尾。
    if touch.count("if cached is None or cached[0] != stamp:") != 1:
        raise ValueError(f"{SESSION} 的缓存命中必须比较完整 stamp")
    checked += 1
    if touch.count("self._entries_cache.pop(thread_id, None)") != 1 or touch.count("self._entries_cache[thread_id] = cached") != 1:
        raise ValueError(f"{SESSION} 的缓存命中必须把该会话移到最近使用")
    checked += 1
    # 增量解析：同一 inode、严格更短的前缀，且旧末尾必须是换行。
    if appendable.count("if inode != stamp[2] or not 0 < size < stamp[0]:") != 1:
        raise ValueError(f"{SESSION} 的增量解析必须要求同一 inode 与严格更短的前缀")
    checked += 1
    if appendable.count("handle.seek(size - 1)") != 1 or 'if handle.read(1) != b"\\n":' not in appendable:
        raise ValueError(f"{SESSION} 的增量解析必须核对旧前缀的末尾换行")
    checked += 1
    if appendable.count("return size, line_count, entries") != 1:
        raise ValueError(f"{SESSION} 的增量解析必须返回缓存前缀")
    checked += 1
    # 全量解析：从 0 开始、按快照字节数设限、行号从 1 开始。
    if all_entries.count("handle.seek(0)") != 1:
        raise ValueError(f"{SESSION} 的全量解析必须从头读取")
    checked += 1
    if all_entries.count("byte_limit=stamp[0]), start=1):") != 1:
        raise ValueError(f"{SESSION} 的全量解析必须按快照字节数设限")
    checked += 1
    if all_entries.count("line_number=line_count") != 1:
        raise ValueError(f"{SESSION} 的全量解析必须使用真实行号")
    checked += 1
    # 增量解析：从旧前缀字节处开始、只读新增范围、行号接续。
    if appended.count("handle.seek(size)") != 1:
        raise ValueError(f"{SESSION} 的增量解析必须从旧前缀末尾读取")
    checked += 1
    if appended.count("byte_limit=stamp[0] - size), start=1):") != 1:
        raise ValueError(f"{SESSION} 的增量解析必须只读新增范围")
    checked += 1
    if appended.count("line_number=line_count + added") != 1:
        raise ValueError(f"{SESSION} 的增量解析必须接续行号")
    checked += 1
    # 写入缓存：先移除再插入，超过会话数上限时按最久未用淘汰。
    if store.count("while len(self._entries_cache) > _MAX_ENTRIES_CACHE_THREADS:") != 1:
        raise ValueError(f"{SESSION} 的缓存必须按会话数上限淘汰")
    checked += 1
    if store.count("self._entries_cache.pop(next(iter(self._entries_cache)))") != 1:
        raise ValueError(f"{SESSION} 的缓存必须淘汰最久未用的会话")
    checked += 1
    if store.count("self._entries_cache[thread_id] = (stamp, line_count, entries)") != 1:
        raise ValueError(f"{SESSION} 的缓存必须以 stamp 与行数登记")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_entries_cache()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError, OSError) as error:
        print(f"会话读取缓存核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话读取缓存一致：{checked} 项命中、增量与边界校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
