#!/usr/bin/env python3
"""核对冻结快照存储的预算、发布顺序与宽容读取边界。

snapshot_store.py 把会话投影写入私有 SQLite 快照：记录、条目、源文件与缓存各有
上限，构建在临时文件完成后才原子发布并同步目录，读取对损坏行宽容降级。任一预算
或顺序被删改都不会触发构建失败，因此静态固定；随后用临时目录、内存源与合成
SQLite 实际执行解码、投影、分页与生命周期。
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/snapshot_store.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.rpc import RpcError  # noqa: E402
from boss_harness.snapshot_store import (  # noqa: E402
    MAX_SNAPSHOT_RECORD_BYTES,
    SnapshotStore,
    _clean_item_fields,
    _decode_item,
    _decode_text,
    _lines,
    _require_item_id,
    read_projection_entries,
    read_source_entries,
)

CONSTANT_FRAGMENTS = (
    "MAX_SNAPSHOT_RECORD_BYTES = MAX_SESSION_LINE_BYTES\n",
    "MAX_SNAPSHOT_SOURCE_BYTES = 1024 * 1024 * 1024\n",
    "MAX_SNAPSHOT_ITEM_BYTES = 128 * 1024 * 1024\n",
    "MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024\n",
    "MAX_SNAPSHOT_CACHE_BYTES = 512 * 1024 * 1024\n",
    "MAX_SNAPSHOTS = 16\n",
    "SNAPSHOT_TTL_SECONDS = 120\n",
    "MAX_STALE_SNAPSHOTS = 64\n",
    "_CONTEXT_EDIT_MAX_CHARS = 32_000\n",
    "_CONTEXT_EDIT_MAX_BYTES = 128 * 1024\n",
)
DECODE_FRAGMENTS = (
    # 快照库可被外部改写：非法 UTF-8 降级而不是让分页变成内部错误。
    'return raw.decode("utf-8", "replace")',
    "connection.text_factory = _decode_text",
    "if not isinstance(payload, str):",
    'raise ValueError("会话快照已损坏；请重新打开会话")',
    "except (TypeError, ValueError, RecursionError):",
    "raise ValueError(\"会话快照已损坏；请重新打开会话\") from None",
    "if not isinstance(item, dict):",
    "if not isinstance(item.get(\"id\"), str) or not item[\"id\"]:",
)
LINE_FRAGMENTS = (
    "chunk = source.read(min(64 * 1024, remaining))",
    "if len(pending) > MAX_SNAPSHOT_RECORD_BYTES:",
    'raise ValueError("会话记录超过冻结快照读取上限")',
    "yield bytes(pending)",
)
READ_FRAGMENTS = (
    "if size > maximum:",
    'raise ValueError("会话文件超过冻结快照读取上限")',
    "source.seek(0)",
    "finally:\n        source.seek(0)",
)
CLEAN_FRAGMENTS = (
    "cleaned = dict(payload)",
    "del cleaned[field]",
    'del cleaned["approval"]',
)
BUILDER_FRAGMENTS = (
    "descriptor = open_private_file(path, os.O_RDWR | os.O_EXCL)",
    "os.close(descriptor)",
    'self.connection.execute("PRAGMA journal_mode=OFF")',
    'self.connection.execute("PRAGMA synchronous=OFF")',
    'self.connection.execute("PRAGMA cache_size=-256")',
    'self.connection.execute("PRAGMA temp_store=FILE")',
    # 预算换算留一页余量：超限由 SQLite 先抛内部错误，事后再给出可读说明。
    "max_pages = MAX_SNAPSHOT_BYTES // page_size + 1",
    "self.connection.execute(f\"PRAGMA max_page_count={max_pages}\")",
    "if actual_max_pages > max_pages:",
    'raise ValueError("无法为冻结快照设置磁盘预算")',
    'CREATE TABLE items (ordinal INTEGER PRIMARY KEY, item_id TEXT NOT NULL, payload TEXT NOT NULL)',
    "CREATE INDEX items_by_id ON items(item_id)",
    'CREATE TABLE aliases (alias TEXT PRIMARY KEY, ordinal INTEGER NOT NULL)',
    'CREATE TABLE edits (item_id TEXT PRIMARY KEY, entry_id TEXT NOT NULL, excluded INTEGER NOT NULL)',
    'CREATE TABLE queue_items (queue_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, payload TEXT NOT NULL)',
    "CREATE INDEX queue_items_order ON queue_items(ordinal)",
)
WRITE_FRAGMENTS = (
    "encoded = json.dumps(item, ensure_ascii=False, allow_nan=False, separators=(\",\", \":\"))",
    "size = len(encoded.encode(\"utf-8\"))",
    "self.item_bytes += size - previous_size",
    "if self.item_bytes > MAX_SNAPSHOT_ITEM_BYTES:",
    'raise ValueError("冻结会话超过快照条目存储上限")',
    "INSERT INTO items(ordinal,item_id,payload) VALUES(?,?,?)",
    "UPDATE items SET payload=? WHERE ordinal=?",
)
ENTRY_FRAGMENTS = (
    # 先保存修订目标再清理本条载荷：合并后再清理会误删合法编号。
    'target_id = _record_id(payload.get("revises")) or ""',
    "payload = _clean_item_fields(payload)",
    "if self._alias(entry_id) is not None:",
    "ordinal = self.count",
    'merged = {**payload, "id": entry_id, "threadId": self.thread_id}',
    "ON CONFLICT(alias) DO UPDATE SET ordinal=excluded.ordinal",
    # 上下文编辑与队列记录沿用宽松契约：损坏条目跳过，不让整次构建失败。
    'set(payload) != {"targetItemId", "replacementText"}',
    "len(replacement) > _CONTEXT_EDIT_MAX_CHARS",
    'len(replacement.encode("utf-8")) > _CONTEXT_EDIT_MAX_BYTES',
    "record = queue_record(payload)",
    'self.item_bytes += len(encoded.encode("utf-8")) - previous_size',
    "ON CONFLICT(queue_id) DO UPDATE SET payload=excluded.payload",
)
BUILD_FRAGMENTS = (
    "self.connection.execute(\"BEGIN IMMEDIATE\")",
    "if line_count % 128 == 0 and cancelled():",
    'raise ValueError("会话快照已因删除或关闭而取消")',
    "if keep_ids is not None and entry.get(\"id\") not in keep_ids:",
    "if pages * page_size > MAX_SNAPSHOT_BYTES:",
    'raise ValueError("冻结会话超过快照磁盘预算")',
    "for item_id, delta in live.items():",
    'if item.get("status") == "running":',
    "dangling_edit = self.connection.execute",
    "if dangling_edit is not None:",
    'raise ValueError("会话上下文编辑引用了不存在的条目；已停止生成模型上下文")',
    "self.connection.commit()",
    "self.connection.close()",
    "self.connection = None",
    "restrict_private_file(self.path)",
    "size_on_disk = self.path.stat().st_size",
    "if size_on_disk > MAX_SNAPSHOT_BYTES:",
    "return size_on_disk",
    "except sqlite3.OperationalError:",
    "_remove_snapshot_files(self.path)",
    'raise ValueError("冻结快照写入失败；会话可能超过快照磁盘预算，请重新打开会话") from None',
    "except BaseException:",
)
REMOVE_FRAGMENTS = (
    'for suffix in ("", "-journal", "-wal", "-shm"):',
    "Path(str(path) + suffix).unlink(missing_ok=True)",
)
STORE_FRAGMENTS = (
    'self.root = Path(root).absolute() / "resume-snapshots"',
    "ensure_private_directory(self.root)",
    "for path in self.root.iterdir():",
    'path.name.endswith((".sqlite", ".building", ".sqlite-journal", ".building-journal",',
    "self._lock = threading.RLock()",
    "self._snapshots: dict[str, tuple[str, Path, float, int, int]] = {}",
    "self._bindings: dict[str, tuple[str, str | None]] = {}",
    "self._current_leaf: dict[str, str | None] = {}",
    "self._stale: dict[str, tuple[str, float]] = {}",
    "self._active_builds = 0",
    "self._builds_by_thread: dict[str, set[SnapshotBuild]] = {}",
    "self._closed = False",
)
BEGIN_FRAGMENTS = (
    'raise ValueError("冻结快照存储已关闭")',
    "if self._active_builds >= 2:",
    'raise ValueError("冻结快照构建已达到并发上限，请稍后重试")',
    "self._builds_by_thread.setdefault(thread_id, set()).add(build)",
    "self._active_builds += 1",
)
RELEASE_FRAGMENTS = (
    "if build.released:",
    "build.released = True",
    "builds.discard(build)",
    "self._builds_by_thread.pop(build.thread_id, None)",
    "self._active_builds -= 1",
)
PRUNE_FRAGMENTS = (
    "for key in [key for key, value in self._stale.items() if value[1] <= now]:",
    "expired = [key for key, value in self._snapshots.items() if value[2] <= now]",
    "while len(self._snapshots) > MAX_SNAPSHOTS or sum(value[4] for value in self._snapshots.values()) > MAX_SNAPSHOT_CACHE_BYTES:",
    "_remove_snapshot_files(path)",
)
CREATE_FRAGMENTS = (
    "if build.released:",
    'raise ValueError("冻结快照构建已结束")',
    "building = self.root / f\".{snapshot_id}.{uuid.uuid4().hex}.building\"",
    "final = self.root / f\"{snapshot_id}.sqlite\"",
    "if self._closed or build.invalidated or build.released:",
    "builder = SnapshotBuilder(building, thread_id, snapshot_id)",
    "builder.build(source, size, live, lambda: self._build_cancelled(build), keep_ids)",
    "os.replace(building, final)",
    "restrict_private_file(final)",
    # 原子改名的目录项必须立即落盘，成功回执后掉电不能留下悬空缓存。
    "_fsync_directory(self.root)",
    "disk_size = final.stat().st_size",
    "if disk_size > MAX_SNAPSHOT_BYTES:",
    "if (view == \"branch\" and thread_id in self._current_leaf",
    "raise snapshot_leaf_changed(snapshot_id)",
    "self._prune_locked(time.monotonic())",
    "self._snapshots[snapshot_id] = (thread_id, final, time.monotonic() + SNAPSHOT_TTL_SECONDS,",
    "self._bindings[snapshot_id] = (view, leaf_entry_id)",
    "_remove_snapshot_files(building)\n            _remove_snapshot_files(final)",
    "finally:\n            with self._lock:\n                self._release_build_locked(build)",
)
PAGE_FRAGMENTS = (
    'bound_view = self._bindings.get(snapshot_id, ("log", None))[0]',
    "if bound_view != view:",
    "raise snapshot_view_mismatch(snapshot_id, bound_view)",
    "if offset > count:",
    'raise ValueError("条目分页游标超出结果范围")',
    "payload_bytes += len(payload.encode(\"utf-8\"))",
    "if result and payload_bytes > max_payload_bytes:",
    "if isinstance(row[1], str) and type(row[2]) is int and row[2] in (0, 1):",
    "result.append((_require_item_id(_decode_item(payload)), edit))",
)
EDIT_FRAGMENTS = (
    "row = connection.execute(\"SELECT entry_id,excluded FROM edits WHERE item_id=?\", (item_id,)).fetchone()",
    "if (not row or not isinstance(row[0], str)",
    "or type(row[1]) is not int or row[1] not in (0, 1)):",
    "return None",
    'return {"entryId": row[0], "excluded": row[1] == 1}',
)
QUEUE_FRAGMENTS = (
    "pending: deque[tuple[int, str]] = deque(maxlen=MAX_QUEUE_VIEW_ITEMS)",
    "paused: deque[tuple[int, str]] = deque(maxlen=MAX_QUEUE_VIEW_ITEMS)",
    "terminal: deque[tuple[int, str]] = deque(maxlen=MAX_QUEUE_VIEW_TERMINAL_ITEMS)",
    "total += 1",
    "if status in ACTIVE_QUEUE_STATUSES:",
    'if status in {"queued", "delivering"}:',
    "selected = sorted((*pending, *paused, *terminal), key=lambda row: row[0])",
    "return project_queue(items, total_items=total, active_items=active, counts=counts)",
)
METADATA_FRAGMENTS = (
    "self._prune_locked(time.monotonic())",
    "stale = self._stale.get(snapshot_id)",
    "raise snapshot_leaf_changed(snapshot_id)",
    "if value is None or value[0] != thread_id:",
    'raise ValueError("会话快照已过期；请重新 resume")',
)
INVALIDATE_FRAGMENTS = (
    "self._current_leaf[thread_id] = leaf_entry_id",
    "for key, value in list(self._snapshots.items()):",
    "if value[0] != thread_id or view != \"branch\" or leaf == leaf_entry_id:",
    "self._stale[key] = (thread_id, max(value[2], now + 1))",
    "while len(self._stale) > MAX_STALE_SNAPSHOTS:",
)
CLOSE_FRAGMENTS = (
    "self._closed = True",
    "for builds in self._builds_by_thread.values():\n                for build in builds:\n                    build.invalidated = True",
    "self._snapshots.clear()",
    "self._bindings.clear()",
    "self._stale.clear()",
    'for pattern in (".*.building", ".*.building-journal", ".*.building-wal", ".*.building-shm",',
    "path.unlink(missing_ok=True)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "普通读取和冻结快照不会静默省略中间记录，失败时不发布部分快照"),
    (TECHNICAL_REFERENCE, "冻结快照用于读取一致的历史切面，不会让模型重新执行已经完成的工具。"),
    (USER_GUIDE, "`thread/read` 和 `thread/resume` 的 `snapshot` 使用布尔 true / false，不能用字符串或 null。true 返回冻结快照，缺省或 false 返回普通读取。"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_snapshot_store() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(DECODE_FRAGMENTS, module, MODULE)
    checked += _expect(LINE_FRAGMENTS, module, MODULE)
    checked += _expect(READ_FRAGMENTS, module, MODULE)
    checked += _expect(CLEAN_FRAGMENTS, module, MODULE)
    checked += _expect(BUILDER_FRAGMENTS, module, MODULE)
    checked += _expect(WRITE_FRAGMENTS, module, MODULE)
    checked += _expect(ENTRY_FRAGMENTS, module, MODULE)
    checked += _expect(BUILD_FRAGMENTS, module, MODULE)
    checked += _expect(REMOVE_FRAGMENTS, module, MODULE)
    checked += _expect(STORE_FRAGMENTS, module, MODULE)
    checked += _expect(BEGIN_FRAGMENTS, module, MODULE)
    checked += _expect(RELEASE_FRAGMENTS, module, MODULE)
    checked += _expect(PRUNE_FRAGMENTS, module, MODULE)
    checked += _expect(CREATE_FRAGMENTS, module, MODULE)
    checked += _expect(PAGE_FRAGMENTS, module, MODULE)
    checked += _expect(EDIT_FRAGMENTS, module, MODULE)
    checked += _expect(QUEUE_FRAGMENTS, module, MODULE)
    checked += _expect(METADATA_FRAGMENTS, module, MODULE)
    checked += _expect(INVALIDATE_FRAGMENTS, module, MODULE)
    checked += _expect(CLOSE_FRAGMENTS, module, MODULE)
    # 构建器：临时文件 → 建库 → 写入 → 提交关闭 → 收紧权限 → 磁盘预算 → 返回。
    checked += _ordered(
        (
            "max_pages = MAX_SNAPSHOT_BYTES // page_size + 1",
            "CREATE INDEX items_by_id ON items(item_id)",
            "CREATE TABLE queue_items (queue_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, payload TEXT NOT NULL)",
            "self.connection.execute(\"BEGIN IMMEDIATE\")",
            "self.connection.commit()",
            "restrict_private_file(self.path)",
            "size_on_disk = self.path.stat().st_size",
            "return size_on_disk",
            "except sqlite3.OperationalError:",
            "except BaseException:",
        ),
        module,
        MODULE,
    )
    # 发布：构建 → 原子改名 → 收紧权限 → 目录同步 → 叶校验 → 登记缓存。
    checked += _ordered(
        (
            "builder = SnapshotBuilder(building, thread_id, snapshot_id)",
            "os.replace(building, final)",
            "restrict_private_file(final)",
            "_fsync_directory(self.root)",
            "disk_size = final.stat().st_size",
            "raise snapshot_leaf_changed(snapshot_id)",
            "self._snapshots[snapshot_id] = (thread_id, final, time.monotonic() + SNAPSHOT_TTL_SECONDS,",
            "return count, disk_size",
            "_remove_snapshot_files(building)\n            _remove_snapshot_files(final)",
            "finally:\n            with self._lock:\n                self._release_build_locked(build)",
        ),
        module,
        MODULE,
    )
    # 读取：视图校验 → 游标校验 → 载荷预算 → 编辑状态 → 条目校验。
    checked += _ordered(
        (
            "if bound_view != view:",
            "if offset > count:",
            "if result and payload_bytes > max_payload_bytes:",
            "if isinstance(row[1], str) and type(row[2]) is int and row[2] in (0, 1):",
            "result.append((_require_item_id(_decode_item(payload)), edit))",
        ),
        module,
        MODULE,
    )
    # 条目合并：先保存修订目标再清理载荷，重复 id 保留先出现的记录。
    checked += _ordered(
        (
            'target_id = _record_id(payload.get("revises")) or ""',
            "payload = _clean_item_fields(payload)",
            "if self._alias(entry_id) is not None:",
        ),
        module,
        MODULE,
    )
    # 失效：记录新叶 → 只处理同线程分支快照 → 移除并留墓碑 → 墓碑有界。
    checked += _ordered(
        (
            "self._current_leaf[thread_id] = leaf_entry_id",
            "for key, value in list(self._snapshots.items()):",
            "self._stale[key] = (thread_id, max(value[2], now + 1))",
            "while len(self._stale) > MAX_STALE_SNAPSHOTS:",
        ),
        module,
        MODULE,
    )
    # 所有序列化都必须拒绝 NaN 并保留非 ASCII；严格 UTF-8 解码会让损坏行变成内部错误。
    if module.count("json.dumps(") != module.count("allow_nan=False"):
        raise ValueError(f"{MODULE} 的每个 json.dumps 都必须 allow_nan=False")
    if 'decode("utf-8")' in module:
        raise ValueError(f"{MODULE} 的快照文本必须宽容解码")
    # 清理只按缺失容忍；裸 unlink 会把并发删除变成构建失败。
    if ".unlink()" in module:
        raise ValueError(f"{MODULE} 的清理必须容忍文件已缺失")
    if "shutil.rmtree" in module or "os.remove(" in module:
        raise ValueError(f"{MODULE} 不得删除快照目录之外的路径")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"冻结快照行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"冻结快照行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"冻结快照行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"冻结快照行为变化 {label}：未抛出错误")


def _expect_rpc(call, code: int, message: str, expected: dict, label: str) -> int:
    try:
        call()
    except RpcError as error:
        checked = _expect_value(error.code, code, label + "错误码")
        checked += _expect_value(str(error), message, label + "消息")
        for key, value in expected.items():
            checked += _expect_value(error.data.get(key), value, f"{label} {key}")
        return checked
    except Exception as error:
        raise ValueError(
            f"冻结快照行为变化 {label}：期望 RpcError，实际 {type(error).__name__}") from None
    raise ValueError(f"冻结快照行为变化 {label}：未抛出错误")


def _jsonl(*records: dict) -> io.BytesIO:
    raw = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    return io.BytesIO(raw.encode("utf-8"))


def _record(kind: str, record_id: str, payload: dict, **extra: object) -> dict:
    return {"type": kind, "id": record_id, "timestamp": "2026-01-01T00:00:00Z",
            "payload": payload, **extra}


def _snapshot_db(path: Path, items: list[tuple[int, str, str]],
                 edits: list[tuple[str, object, int]] = ()) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE items (ordinal INTEGER PRIMARY KEY, item_id TEXT NOT NULL, payload TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE edits (item_id TEXT PRIMARY KEY, entry_id TEXT NOT NULL, excluded INTEGER NOT NULL)")
        connection.executemany("INSERT INTO items VALUES (?, ?, ?)", items)
        connection.executemany("INSERT INTO edits VALUES (?, ?, ?)", edits)
        connection.commit()
    finally:
        connection.close()


def _register(store: SnapshotStore, snapshot_id: str, thread_id: str, path: Path, count: int,
              *, expires: float | None = None, view: str = "log",
              leaf: str | None = None) -> None:
    deadline = time.monotonic() + 60 if expires is None else expires
    store._snapshots[snapshot_id] = (thread_id, path, deadline, count, 0)
    store._bindings[snapshot_id] = (view, leaf)


def _behavior_checks() -> int:
    checked = 0
    message_corrupt = "会话快照已损坏；请重新打开会话"
    message_expired = "会话快照已过期；请重新 resume"
    checked += _expect_value(_decode_text(b"abc"), "abc", "合法文本解码")
    checked += _expect_value(_decode_text("你好".encode("utf-8")), "你好", "非 ASCII 解码")
    checked += _expect_value(_decode_text(b"a\xffb"), "a�b", "非法字节降级")
    checked += _expect_value(_decode_item('{"id": "a"}'), {"id": "a"}, "条目解码")
    for label, payload in (("非字符串", b'{"id": "a"}'), ("非法 JSON", "not json"),
                           ("数组", "[1]"), ("字符串", '"x"'), ("null", "null"),
                           ("深嵌套", "[" * 50000 + "]" * 50000),
                           # 3.10 / 3.11 的 json.loads 在约 995 层抛 RecursionError，
                           # 3.12+ 能解析；解析前按会话日志同一上限拒绝，结论不随版本变化。
                           ("可解析深嵌套", '{"id": "a", "payload": '
                            + "[" * 1200 + "]" * 1200 + "}")):
        checked += _expect_error(lambda: _decode_item(payload), message_corrupt,
                                 f"条目载荷 {label}")
    item = {"id": "a"}
    checked += _expect_value(_require_item_id(item), item, "条目 id 校验")
    for label, value in (("缺失", {}), ("空串", {"id": ""}), ("非字符串", {"id": 1})):
        checked += _expect_error(lambda: _require_item_id(value), message_corrupt,
                                 f"条目 id {label}")

    checked += _expect_value(list(_lines(io.BytesIO(b"a\nb"), 3)), [b"a"], "无换行残段丢弃")
    checked += _expect_value(list(_lines(io.BytesIO(b"a\n\nb\n"), 5)), [b"a", b"", b"b"],
                             "空行保留")
    checked += _expect_value(list(_lines(io.BytesIO(b"a\r\nb\r\n"), 6)),
                             [b"a", b"", b"b", b""], "CRLF 双分隔保留空行")
    boundary = b"a" * 65535 + b"\r" + b"\n" + b"next\n"
    checked += _expect_value(list(_lines(io.BytesIO(boundary), len(boundary))),
                             [b"a" * 65535, b"next"], "跨块 CRLF")
    checked += _expect_value(list(_lines(io.BytesIO(b"a\nb\n"), 2)), [b"a"], "按 size 截断")
    oversized = b"x" * (MAX_SNAPSHOT_RECORD_BYTES + 1) + b"\n"
    checked += _expect_error(lambda: list(_lines(io.BytesIO(oversized), len(oversized))),
                             "会话记录超过冻结快照读取上限", "超限记录")

    header = {"type": "session", "id": "s1", "timestamp": "", "payload": {}}
    first = _record("item", "i1", {"id": "i1", "kind": "message"})
    second = _record("turn", "r1", {"turnId": "turn-1", "status": "completed"})
    source = _jsonl(header, first, second)
    size = len(source.getvalue())
    entries = read_source_entries(source, size)
    checked += _expect_value(entries, [first, second], "跳过会话头")
    checked += _expect_value(source.tell(), 0, "读取后回绕")
    source = io.BytesIO(json.dumps(header).encode() + b"\n\n"
                        + json.dumps(first).encode() + b"\n")
    checked += _expect_value(read_source_entries(source, len(source.getvalue())), [first],
                             "跳过空行")
    malformed = {"type": "item", "id": "i1", "payload": {}}
    source = _jsonl(header, malformed)
    checked += _expect_error(lambda: read_source_entries(source, len(source.getvalue())),
                             "会话日志第 2 行格式无效，读取已停止", "格式错误行号")
    source = _jsonl(first)
    checked += _expect_error(lambda: read_source_entries(source, len(source.getvalue()),
                                                         maximum=1),
                             "会话文件超过冻结快照读取上限", "源读取上限")

    projected = read_projection_entries(
        _jsonl(first, _record("turn", "r2", {"turnId": "turn-2", "secret": "drop"},
                             parentId="i1")),
        len(_jsonl(first, _record("turn", "r2", {"turnId": "turn-2", "secret": "drop"},
                                  parentId="i1")).getvalue()))
    checked += _expect_value(projected[0], {
        "id": "i1", "type": "item",
        "payload": {"kind": "message"},
    }, "条目投影裁剪")
    checked += _expect_value(projected[1]["payload"], {"turnId": "turn-2", "secret": "drop"},
                             "回合载荷保留")
    checked += _expect_value((projected[1]["parentId"], projected[1]["timestamp"]),
                             ("i1", "2026-01-01T00:00:00Z"), "回合父链与时间")
    cleaned = _clean_item_fields({"turnId": 1, "kind": "message", "approval": "x",
                                  "revises": 2, "toolBatchId": "batch-1"})
    checked += _expect_value(cleaned, {"kind": "message", "toolBatchId": "batch-1"},
                             "编号字段清理")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        store = SnapshotStore(base / "state")
        checked += _expect_value(store.root, (base / "state" / "resume-snapshots").absolute(),
                                 "快照根目录")
        checked += _expect_value(stat.S_IMODE(store.root.stat().st_mode), 0o700, "根目录权限")
        (store.root / "stale.sqlite").write_text("x", encoding="utf-8")
        (store.root / "stale.building").write_text("x", encoding="utf-8")
        (store.root / "keep.txt").write_text("x", encoding="utf-8")
        reopened = SnapshotStore(base / "state")
        checked += _expect_value(
            sorted(path.name for path in reopened.root.iterdir()), ["keep.txt"],
            "陈旧快照文件清理")

        page_path = reopened.root / "page.sqlite"
        _snapshot_db(page_path,
                     [(0, "i0", json.dumps({"id": "i0", "n": 1})),
                      (1, "i1", json.dumps({"id": "i1", "n": 2}))],
                     [("i0", "entry-1", 1), ("i1", "entry-2", 2)])
        _register(reopened, "page", "thread-1", page_path, 2)
        rows, count = reopened.page("page", "thread-1", 0, 2)
        checked += _expect_value(count, 2, "分页总数")
        checked += _expect_value(rows[0], ({"id": "i0", "n": 1},
                                           {"entryId": "entry-1", "excluded": True}),
                                 "分页首条与编辑状态")
        checked += _expect_value(rows[1][1], None, "损坏编辑状态降级")
        checked += _expect_value(reopened.page("page", "thread-1", 1, 2)[0],
                                 [({"id": "i1", "n": 2}, None)], "分页偏移")
        checked += _expect_value(reopened.page("page", "thread-1", 2, 2)[0], [],
                                 "偏移等于总数")
        checked += _expect_error(lambda: reopened.page("page", "thread-1", 3, 2),
                                 "条目分页游标超出结果范围", "偏移超出范围")
        checked += _expect_value(len(reopened.page("page", "thread-1", 0, 2,
                                                   max_payload_bytes=1)[0]), 1,
                                 "载荷预算截断")
        checked += _expect_rpc(
            lambda: reopened.page("page", "thread-1", 0, 2, view="branch"), -32011,
            "快照视图与读取视图不一致；分支快照只能用 view=branch 分页，日志快照不能用 view=branch",
            {"code": "SNAPSHOT_VIEW_MISMATCH", "snapshotId": "page",
             "snapshotView": "log"}, "视图不匹配")
        checked += _expect_value(reopened.metadata("page", "thread-1"), (page_path, 2),
                                 "元数据")
        checked += _expect_value(reopened.item("page", "thread-1", "i0"),
                                 {"id": "i0", "n": 1}, "条目读取")
        checked += _expect_value(reopened.item("page", "thread-1", "missing"), None,
                                 "缺失条目")
        checked += _expect_value(reopened.edit_state("page", "thread-1", "i0"),
                                 {"entryId": "entry-1", "excluded": True}, "编辑状态")
        checked += _expect_value(reopened.edit_state("page", "thread-1", "i1"), None,
                                 "损坏编辑状态")

        corrupt_path = reopened.root / "corrupt.sqlite"
        _snapshot_db(corrupt_path, [(0, "bad", json.dumps({"n": 3}))])
        _register(reopened, "corrupt", "thread-1", corrupt_path, 1)
        checked += _expect_error(lambda: reopened.page("corrupt", "thread-1", 0, 1),
                                 message_corrupt, "分页损坏条目")
        checked += _expect_error(lambda: reopened.item("corrupt", "thread-1", "bad"),
                                 message_corrupt, "条目读取损坏载荷")
        checked += _expect_error(lambda: reopened.metadata("missing", "thread-1"),
                                 message_expired, "未知快照")

        expired_path = reopened.root / "expired.sqlite"
        expired_path.write_text("x", encoding="utf-8")
        _register(reopened, "expired", "thread-1", expired_path, 0,
                  expires=time.monotonic() - 1)
        checked += _expect_error(lambda: reopened.metadata("expired", "thread-1"),
                                 message_expired, "过期快照")
        checked += _expect_value(expired_path.exists(), False, "过期文件删除")

        branch_path = reopened.root / "branch.sqlite"
        branch_path.write_text("x", encoding="utf-8")
        log_path = reopened.root / "log.sqlite"
        log_path.write_text("x", encoding="utf-8")
        other_path = reopened.root / "other.sqlite"
        other_path.write_text("x", encoding="utf-8")
        _register(reopened, "branch-1", "thread-1", branch_path, 0, view="branch",
                  leaf="leaf-old")
        _register(reopened, "log-1", "thread-1", log_path, 0)
        _register(reopened, "branch-2", "thread-2", other_path, 0, view="branch",
                  leaf="leaf-old")
        checked += _expect_value(reopened.invalidate_branch("thread-1", "leaf-new"),
                                 ["branch-1"], "分支失效列表")
        checked += _expect_value(branch_path.exists(), False, "失效快照文件删除")
        checked += _expect_value((log_path.exists(), other_path.exists()), (True, True),
                                 "其他快照保留")
        checked += _expect_rpc(
            lambda: reopened.metadata("branch-1", "thread-1"), -32011,
            "会话分支指针已变化，该分支快照已失效；请重新 thread/resume snapshot=true view=branch",
            {"code": "SNAPSHOT_LEAF_CHANGED", "snapshotId": "branch-1",
             "recoveryMethod": "thread/resume", "view": "branch", "snapshot": True},
            "失效墓碑")
        checked += _expect_value(reopened.invalidate_branch("thread-1", "leaf-new"), [],
                                 "重复失效无快照")
        same_path = reopened.root / "same.sqlite"
        same_path.write_text("x", encoding="utf-8")
        _register(reopened, "branch-3", "thread-1", same_path, 0, view="branch",
                  leaf="leaf-new")
        checked += _expect_value(reopened.invalidate_branch("thread-1", "leaf-new"), [],
                                 "同叶分支保留")

        reopened.delete_snapshot("log-1")
        checked += _expect_value(log_path.exists(), False, "按快照删除文件")
        reopened.delete_snapshot("log-1")
        checked += _expect_value(reopened.metadata("branch-2", "thread-2"),
                                 (other_path, 0), "删除不影响其他会话")

        build = reopened.begin_build("thread-2")
        second_build = reopened.begin_build("thread-1")
        checked += _expect_error(lambda: reopened.begin_build("thread-3"),
                                 "冻结快照构建已达到并发上限，请稍后重试", "并发构建上限")
        reopened.cancel_build(build)
        reopened.cancel_build(build)
        third = reopened.begin_build("thread-3")
        checked += _expect_value(reopened._active_builds, 2, "取消后释放槽位")
        reopened.cancel_build(third)
        reopened.cancel_build(second_build)

        build = reopened.begin_build("thread-2")
        reopened.delete_thread("thread-2")
        checked += _expect_value(build.invalidated, True, "删除会话标记构建失效")
        checked += _expect_value(other_path.exists(), False, "删除会话快照文件")
        checked += _expect_value(reopened.metadata("branch-3", "thread-1"),
                                 (same_path, 0), "按会话删除不影响其他会话")

        reopened.close()
        checked += _expect_value(same_path.exists(), False, "关闭删除快照文件")
        checked += _expect_value(reopened._snapshots, {}, "关闭清空缓存")
        reopened.close()
        checked += _expect_error(lambda: reopened.begin_build("thread-1"),
                                 "冻结快照存储已关闭", "关闭后拒绝构建")
    return checked


def main() -> int:
    try:
        checked = check_snapshot_store()
        scenarios = _behavior_checks()
    except ValueError as error:
        print(f"冻结快照存储核对失败，{error}", file=sys.stderr)
        return 2
    print(f"冻结快照存储一致：{checked} 项预算、发布与读取防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
