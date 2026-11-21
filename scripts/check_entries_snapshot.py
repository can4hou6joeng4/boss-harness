#!/usr/bin/env python3
"""核对会话条目快照的生命周期与读取边界。

`open_entries_snapshot` 在写锁内打开日志、用 `_complete_record_limit` 把可读前缀
钉在最后一条完整记录上，再交出 `SessionEntriesSnapshot`；打不开或取长度失败时必须
关闭文件。快照对象可重入读取：每次迭代回到开头、行号从零计数、按钉住的前缀字节
上限逐行读取、跳过空行、解码失败由解码器报错；已关闭的快照在进入与迭代时都拒绝。
这里固定这些规则，避免重构后读到半写记录、重复读取从中间继续或泄漏文件描述符。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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


def check_entries_snapshot() -> int:
    source = _read(SESSION)
    start = source.index("def open_entries_snapshot(")
    end = source.find("\n    def ", start + 1)
    opener = source[start:] if end < 0 else source[start:end]
    class_start = source.index("class SessionEntriesSnapshot:")
    class_end = source.find("\n\ndef ", class_start + 1)
    snapshot = source[class_start:] if class_end < 0 else source[class_start:class_end]
    checked = _ordered(OPEN_ORDER, opener, SESSION)
    checked += _ordered(CLASS_ORDER, snapshot, SESSION)
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
    return checked


def main() -> int:
    try:
        checked = check_entries_snapshot()
    except ValueError as error:
        print(f"条目快照核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目快照一致：{checked} 项前缀、生命周期与重入读取校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
