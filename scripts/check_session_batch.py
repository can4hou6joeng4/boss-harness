#!/usr/bin/env python3
"""核对会话写入路径的批量追加、新建发布与附件引用顺序。

`SessionStore` 的 JSONL 是会话事实源，写入顺序决定并发下的可见性：
`append_many` 先校验批次并完成编码，再进入唯一写事务；末尾缺换行时上限
按 1 字节前缀计入，写前与写后各刷新一次索引投影。`append` 保持单条
「require → 刷新 → 追加 → 刷新」。`_write_new` 只在临时文件 fsync 后
用 `os.link` 发布完整会话。`append_attachment` 先逐行校验历史，再发布
内容、fsync 附件目录，最后写引用行；清理只删除未被任何会话引用的摘要。
这里按源码顺序固定这些边界，避免事务、上限或发布顺序被重构放松。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

BATCH_ORDER = (
    "def append_many(self, thread_id: str, entries: list[Entry], *, maximum_bytes: int | None = None) -> list[Entry]:",
    "if not isinstance(entries, list) or any(not isinstance(entry, Entry) for entry in entries):",
    'raise ValueError("会话追加批次必须是 Entry 列表")',
    "if maximum_bytes is not None and (type(maximum_bytes) is not int or maximum_bytes < 1):",
    'raise ValueError("会话追加上限必须是正整数")',
    "if not entries:",
    "return []",
    "encoded = [_encode_session_line(entry.to_dict()) for entry in entries]",
    "path = self.path_for(thread_id)",
    "with self._lock, self._index.transaction() as connection:",
    "self.require_thread(thread_id)",
    "current_size = path.stat().st_size",
    "if maximum_bytes is not None:",
    "prefix_size = 0",
    "if current_size:",
    "handle.seek(-1, os.SEEK_END)",
    "prefix_size = int(handle.read(1) != bytes([10]))",
    "if current_size + prefix_size + sum(map(len, encoded)) > maximum_bytes:",
    'raise SessionSizeLimitExceeded("会话历史超过续接读取上限。")',
    "self._index_thread(thread_id, connection)",
    "for entry in entries:",
    "self._append_line(path, entry.to_dict())",
    "self._index_thread(thread_id, connection)",
    "return entries",
)
APPEND_ORDER = (
    "def append(self, thread_id: str, entry: Entry) -> Entry:",
    "with self._lock, self._index.transaction() as connection:",
    "self.require_thread(thread_id)",
    "self._index_thread(thread_id, connection)",
    "self._append_line(self.path_for(thread_id), entry.to_dict())",
    "self._index_thread(thread_id, connection)",
    "return entry",
)
NEW_ORDER = (
    "def _write_new(self, header: dict, entries: list[dict] | None = None) -> dict:",
    'path = self.path_for(header["id"])',
    'encoded = b"".join([',
    '_encode_session_line(header, maximum=MAX_SESSION_HEADER_BYTES, label="会话头"),',
    "*(_encode_session_line(entry) for entry in entries or []),",
    'temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")',
    "with self._lock, self._index.transaction() as connection:",
    "descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)",
    'with os.fdopen(descriptor, "wb") as handle:',
    "handle.write(encoded)",
    "handle.flush()",
    "os.fsync(handle.fileno())",
    "os.link(temporary, path)",
    "finally:",
    "temporary.unlink(missing_ok=True)",
    'self._index_thread(header["id"], connection)',
    'return self.get_thread(header["id"])',
)
ATTACH_ORDER = (
    "def append_attachment(self, thread_id: str, entry: Entry, publish: Callable[[], None]) -> Entry:",
    "payload = entry.payload or {}",
    'digest = payload.get("digest")',
    'if entry.type != "attachment" or not isinstance(digest, str) or not _ATTACHMENT_DIGEST.fullmatch(digest):',
    'raise ValueError("附件记录格式无效")',
    "if not callable(publish):",
    'raise ValueError("附件发布器无效")',
    "with self._lock, self._index.transaction() as connection:",
    "with self.open_entries_snapshot(thread_id) as entries:",
    "for _entry in entries:\n                    pass",
    "publish()",
    "_fsync_directory(self.attachments_root)",
    "self._append_line(self.path_for(thread_id), entry.to_dict())",
    "self._index_thread(thread_id, connection)",
    "return entry",
)
CLEANUP_ORDER = (
    "def cleanup_unreferenced_attachments(self, digests: list[str]) -> None:",
    "with self._lock, self._index.transaction():",
    "self._purge_unreferenced_attachments(digests)",
)
TEMP_ORDER = (
    "def cleanup_attachment_temporaries(self) -> None:",
    "with self._lock, self._index.transaction():",
    "if _ATTACHMENT_TEMP.fullmatch(entry.name) is None:",
    "restrict_private_file(path)",
    "path.unlink()",
    "changed = True",
    "if changed:",
    "_fsync_directory(self.attachments_root)",
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


def check_session_batch() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    batch = _method(tree, source, "append_many")
    append = _method(tree, source, "append")
    new = _method(tree, source, "_write_new")
    attach = _method(tree, source, "append_attachment")
    cleanup = _method(tree, source, "cleanup_unreferenced_attachments")
    temporary = _method(tree, source, "cleanup_attachment_temporaries")
    checked = _ordered(BATCH_ORDER, batch, SESSION)
    checked += _ordered(APPEND_ORDER, append, SESSION)
    checked += _ordered(NEW_ORDER, new, SESSION)
    checked += _ordered(ATTACH_ORDER, attach, SESSION)
    checked += _ordered(CLEANUP_ORDER, cleanup, SESSION)
    checked += _ordered(TEMP_ORDER, temporary, SESSION)
    # 批量追加：整批只编码一次，逐行直写，不得回退到单条事务。
    if batch.count("_encode_session_line(") != 1:
        raise ValueError(f"{SESSION} 的批量追加必须每批只编码一次")
    checked += 1
    if batch.count("self._append_line(") != 1 or batch.count("self.append(") != 0:
        raise ValueError(f"{SESSION} 的批量追加必须逐行直写，不得回退到单条事务")
    checked += 1
    if batch.count("self._index_thread(thread_id, connection)") != 2:
        raise ValueError(f"{SESSION} 的批量追加必须在写入前后各刷新一次索引")
    checked += 1
    if batch.count("return []") != 1 or batch.count("return entries") != 1:
        raise ValueError(f"{SESSION} 的空批次必须早退并返回原批次")
    checked += 1
    if ">= maximum_bytes" in batch or "> maximum_bytes" not in batch:
        raise ValueError(f"{SESSION} 的批量追加上限必须严格大于")
    checked += 1
    if batch.count("prefix_size = int(handle.read(1) != bytes([10]))") != 1:
        raise ValueError(f"{SESSION} 的批量追加必须把缺失的末尾换行计入上限")
    checked += 1
    if batch.count("sum(map(len, encoded))") != 1:
        raise ValueError(f"{SESSION} 的批量追加上限必须按整批编码字节计算")
    checked += 1
    if batch.count("SessionSizeLimitExceeded(") != 1:
        raise ValueError(f"{SESSION} 的批量追加超限必须抛 SessionSizeLimitExceeded")
    checked += 1
    # 单条追加：同一事务内两次刷新，且不得委托批量路径。
    if append.count("self._index_thread(thread_id, connection)") != 2:
        raise ValueError(f"{SESSION} 的单条追加必须在写入前后各刷新一次索引")
    checked += 1
    if append.count("self._append_line(") != 1 or "append_many" in append:
        raise ValueError(f"{SESSION} 的单条追加只能写入一行")
    checked += 1
    # 新建：整卷编码、临时名、fsync 后硬链接发布，临时名必须清理。
    if new.count("_encode_session_line(") != 2:
        raise ValueError(f"{SESSION} 的新建必须同时编码会话头与初始条目")
    checked += 1
    if new.count(".tmp") != 1:
        raise ValueError(f"{SESSION} 的新建必须使用 .tmp 临时名")
    checked += 1
    if new.count("os.fsync(") != 1 or new.count("os.link(") != 1:
        raise ValueError(f"{SESSION} 的新建必须在 fsync 后硬链接发布")
    checked += 1
    if "os.replace" in new or "os.rename" in new:
        raise ValueError(f"{SESSION} 的新建不得覆盖已有会话文件")
    checked += 1
    if new.count("unlink(missing_ok=True)") != 1:
        raise ValueError(f"{SESSION} 的新建必须清理临时文件")
    checked += 1
    # 附件引用：内容先发布并 fsync 目录，再写引用行；引用行只写一次。
    if attach.count("entry.to_dict()") != 1 or attach.count("self._append_line(") != 1:
        raise ValueError(f"{SESSION} 的附件引用必须只写一行")
    checked += 1
    if attach.count("publish()") != 1 or attach.count("_fsync_directory(") != 1:
        raise ValueError(f"{SESSION} 的附件引用必须先发布内容并 fsync 目录")
    checked += 1
    if attach.count("self._index_thread(") != 1:
        raise ValueError(f"{SESSION} 的附件引用写入后必须刷新一次索引")
    checked += 1
    if attach.count("_ATTACHMENT_DIGEST.fullmatch(digest)") != 1:
        raise ValueError(f"{SESSION} 的附件引用必须校验摘要格式")
    checked += 1
    if attach.index("open_entries_snapshot") > attach.index("publish()"):
        raise ValueError(f"{SESSION} 的附件发布必须在历史校验之后")
    checked += 1
    if attach.index("_fsync_directory(") > attach.index("self._append_line("):
        raise ValueError(f"{SESSION} 的附件目录必须在写引用行之前 fsync")
    checked += 1
    # 清理：唯一入口在写锁与索引事务内，且不得内联删除。
    if cleanup.count("self._purge_unreferenced_attachments(digests)") != 1:
        raise ValueError(f"{SESSION} 的附件清理必须委托 _purge_unreferenced_attachments")
    checked += 1
    if "unlink" in cleanup:
        raise ValueError(f"{SESSION} 的附件清理不得绕过引用扫描直接删除")
    checked += 1
    # 临时清理只匹配受限临时名，删除后 fsync 目录。
    if temporary.count("_ATTACHMENT_TEMP.fullmatch(entry.name) is None") != 1:
        raise ValueError(f"{SESSION} 的临时清理必须只匹配受限临时名")
    checked += 1
    if temporary.count("path.unlink()") != 1 or temporary.count("_fsync_directory(") != 1:
        raise ValueError(f"{SESSION} 的临时清理必须落盘删除结果")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_session_batch()
    except (ValueError, SyntaxError) as error:
        print(f"会话写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话写入一致：{checked} 项批量追加与附件引用校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
