#!/usr/bin/env python3
"""核对会话写入路径的批量追加、新建发布与附件引用顺序。

`SessionStore` 的 JSONL 是会话事实源，写入顺序决定并发下的可见性：
`append_many` 先校验批次并完成编码，再进入唯一写事务；末尾缺换行时上限
按 1 字节前缀计入，写前与写后各刷新一次索引投影。`append` 保持单条
「require → 刷新 → 追加 → 刷新」。`_write_new` 只在临时文件 fsync 后
用 `os.link` 发布完整会话。`append_attachment` 先逐行校验历史，再发布
内容、fsync 附件目录，最后写引用行；清理只删除未被任何会话引用的摘要。
这里先按源码顺序固定这些边界，再用临时目录与合成 `SessionStore` 实际执行
四个写入方法，覆盖失败路径与顺序不变量。
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import (  # noqa: E402
    MAX_SESSION_HEADER_BYTES,
    MAX_SESSION_LINE_BYTES,
    Entry,
    SessionSizeLimitExceeded,
    SessionStore,
)

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


_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def _header(thread_id: str, title: str = "会话") -> dict:
    return {"type": "session", "version": 2, "id": thread_id,
            "sessionId": f"sess-{thread_id}", "title": title,
            "createdAt": _TIMESTAMP, "archived": False}


def _build(base: Path, name: str) -> tuple[SessionStore, str, Path]:
    sessions = base / name / "sessions"
    sessions.mkdir(parents=True, mode=0o700)
    (sessions.parent / "attachments").mkdir(mode=0o700)
    store = SessionStore(sessions)
    return store, store.create("会话")["id"], sessions


def _encoded_size(entry: Entry) -> int:
    return len(json.dumps(entry.to_dict(), ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")) + 1


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"会话写入行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _no_error(call, label: str) -> int:
    try:
        call()
    except Exception as error:
        raise ValueError(
            f"会话写入行为变化 {label}：未预期 {type(error).__name__}: {error}") from None
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"会话写入行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"会话写入行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"会话写入行为变化 {label}：未抛出错误")


def _expect_raises(call, kind: type[BaseException], label: str) -> int:
    try:
        call()
    except kind:
        return 1
    except Exception as error:
        raise ValueError(
            f"会话写入行为变化 {label}：期望 {kind.__name__}，实际 "
            f"{type(error).__name__}") from None
    raise ValueError(f"会话写入行为变化 {label}：未抛出错误")


def _behavior_checks() -> int:
    checked = 0
    batch_message = "会话追加批次必须是 Entry 列表"
    limit_message = "会话追加上限必须是正整数"
    size_message = "会话历史超过续接读取上限。"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        # 批量追加：批次与上限校验、空批次、严格字节边界。
        store, thread, sessions = _build(base, "batch")
        path = sessions / f"{thread}.jsonl"
        checked += _expect_error(lambda: store.append_many(thread, ("x",)),
                                 batch_message, "非列表批次")
        checked += _expect_error(
            lambda: store.append_many(thread, [Entry(type="item"), "x"]),
            batch_message, "非 Entry 条目")
        checked += _expect_error(lambda: store.append_many(thread, [], maximum_bytes=0),
                                 limit_message, "零上限")
        checked += _expect_error(lambda: store.append_many(thread, [], maximum_bytes=True),
                                 limit_message, "布尔上限")
        checked += _expect_error(lambda: store.append_many(thread, [], maximum_bytes="10"),
                                 limit_message, "字符串上限")
        before = path.read_bytes()
        empty = store.append_many(thread, [])
        checked += _expect_value((empty, path.read_bytes()), ([], before), "空批次早退")
        batch = [Entry(type="item", payload={"kind": "message", "n": index})
                 for index in range(3)]
        allowed = path.stat().st_size + sum(_encoded_size(item) for item in batch)
        checked += _expect_error(
            lambda: store.append_many(thread, batch, maximum_bytes=allowed - 1),
            size_message, "超限一字节")
        checked += _expect_value(path.read_bytes(), before, "超限文件不变")
        returned = store.append_many(thread, batch, maximum_bytes=allowed)
        checked += _expect_value([item.id for item in returned],
                                 [item.id for item in batch], "边界上限追加")
        checked += _expect_value(len(path.read_text(encoding="utf-8").splitlines()), 4,
                                 "批次逐行写入")

        # 缺失结尾换行：上限按 1 字节前缀计入，写入前截掉残段。
        store, thread, sessions = _build(base, "partial")
        path = sessions / f"{thread}.jsonl"
        path.write_bytes(path.read_bytes() + b'{"type":"item","id":"partial"')
        entry = Entry(type="item", payload={"kind": "message"})
        size = path.stat().st_size
        checked += _expect_error(
            lambda: store.append_many(thread, [entry],
                                      maximum_bytes=size + _encoded_size(entry)),
            size_message, "缺失换行差一字节")
        checked += _no_error(
            lambda: store.append_many(thread, [entry],
                                      maximum_bytes=size + 1 + _encoded_size(entry)),
            "缺失换行边界追加")
        text = path.read_text(encoding="utf-8")
        checked += _expect_value(text.endswith("\n"), True, "缺失换行补齐")
        checked += _expect_value(len(text.splitlines()), 2, "残段截断后追加")

        # 单条追加：缺失会话拒绝且不建文件，成功时只写一行并返回原条目。
        store, thread, sessions = _build(base, "single")
        path = sessions / f"{thread}.jsonl"
        checked += _expect_error(
            lambda: store.append("ffffffffffff", Entry(type="item")),
            "会话不存在", "缺失会话")
        checked += _expect_value((sessions / "ffffffffffff.jsonl").exists(), False,
                                 "缺失会话不建文件")
        entry = Entry(type="item", payload={"kind": "message"})
        returned = store.append(thread, entry)
        checked += _expect_value(returned is entry, True, "单条追加返回原条目")
        checked += _expect_value(len(path.read_text(encoding="utf-8").splitlines()), 2,
                                 "单条追加一行")

        # 新建：冲突不覆盖、临时文件清理、编码上限与成功发布。
        store, thread, sessions = _build(base, "new")
        path = sessions / f"{thread}.jsonl"
        original = path.read_bytes()
        checked += _expect_raises(lambda: store._write_new(_header(thread)),
                                  FileExistsError, "新建冲突")
        checked += _expect_value(path.read_bytes(), original, "冲突不覆盖")
        checked += _expect_value(list(sessions.glob(f".{thread}.jsonl.*.tmp")), [],
                                 "冲突清理临时")
        checked += _expect_error(lambda: store._write_new({"id": "bad id"}),
                                 "threadId 格式无效", "非法会话号")
        checked += _expect_raises(
            lambda: store._write_new(_header("cccccccccccc"), [
                {"type": "item", "id": "x", "parentId": None, "timestamp": _TIMESTAMP,
                 "payload": {"value": float("nan")}}]),
            ValueError, "NaN 载荷")
        checked += _expect_value((sessions / "cccccccccccc.jsonl").exists(), False,
                                 "NaN 不建文件")
        big = {"type": "item", "id": "big", "parentId": None, "timestamp": _TIMESTAMP,
               "payload": {"text": "x" * MAX_SESSION_LINE_BYTES}}
        checked += _expect_error(
            lambda: store._write_new(_header("dddddddddddd"), [big]),
            "会话日志单行超过大小限制", "条目超限")
        checked += _expect_value((sessions / "dddddddddddd.jsonl").exists(), False,
                                 "条目超限不建文件")
        checked += _expect_error(
            lambda: store._write_new(_header("eeeeeeeeeeee",
                                             title="x" * MAX_SESSION_HEADER_BYTES)),
            "会话头单行超过大小限制", "会话头超限")
        created = store._write_new(_header("ffffffffffff", title="新会话"), [
            {"type": "item", "id": "i1", "parentId": None, "timestamp": _TIMESTAMP,
             "payload": {"kind": "message"}}])
        checked += _expect_value((created.get("id"), created.get("title")),
                                 ("ffffffffffff", "新会话"), "新建成功返回会话")
        checked += _expect_value(
            len((sessions / "ffffffffffff.jsonl").read_text(
                encoding="utf-8").splitlines()), 2, "新建写入头与条目")

        # 附件引用：类型 / 摘要 / 发布器校验，发布先于引用行，失败不留引用。
        store, thread, sessions = _build(base, "attachment")
        path = sessions / f"{thread}.jsonl"
        digest = hashlib.sha256(b"object").hexdigest()
        checked += _expect_error(
            lambda: store.append_attachment(
                thread, Entry(type="item", payload={"digest": digest}), lambda: None),
            "附件记录格式无效", "附件类型无效")
        checked += _expect_error(
            lambda: store.append_attachment(
                thread, Entry(type="attachment", payload={"digest": "x"}), lambda: None),
            "附件记录格式无效", "附件摘要无效")
        checked += _expect_error(
            lambda: store.append_attachment(
                thread, Entry(type="attachment", payload={"digest": digest.upper()}),
                lambda: None),
            "附件记录格式无效", "大写摘要")
        checked += _expect_error(
            lambda: store.append_attachment(
                thread, Entry(type="attachment", payload={"digest": digest}), None),
            "附件发布器无效", "发布器不可调用")
        seen: list[int] = []

        def publish_ok() -> None:
            seen.append(path.read_text(encoding="utf-8").count(digest))

        attachment = Entry(type="attachment",
                           payload={"digest": digest, "name": "notes.txt"})
        result = store.append_attachment(thread, attachment, publish_ok)
        checked += _expect_value(seen, [0], "发布先于引用行")
        checked += _expect_value(result is attachment, True, "附件返回原条目")
        checked += _expect_value(path.read_text(encoding="utf-8").count(digest), 1,
                                 "引用只写一行")
        before = path.read_bytes()

        def publish_fail() -> None:
            raise RuntimeError("publish failed")

        other = hashlib.sha256(b"other").hexdigest()
        checked += _expect_raises(
            lambda: store.append_attachment(
                thread, Entry(type="attachment", payload={"digest": other}), publish_fail),
            RuntimeError, "发布失败传播")
        checked += _expect_value(path.read_bytes(), before, "发布失败不留引用")

        # 历史损坏时先拒绝，发布器不得被调用。
        sessions2 = base / "corrupt" / "sessions"
        sessions2.mkdir(parents=True, mode=0o700)
        (sessions2.parent / "attachments").mkdir(mode=0o700)
        (sessions2 / "dddddddddddd.jsonl").write_text(
            json.dumps(_header("dddddddddddd")) + "\n{broken\n", encoding="utf-8")
        store2 = SessionStore(sessions2)
        calls: list[str] = []
        checked += _expect_error(
            lambda: store2.append_attachment(
                "dddddddddddd",
                Entry(type="attachment", payload={"digest": other}),
                lambda: calls.append("publish")),
            "会话日志第 2 行损坏，读取已停止", "历史损坏")
        checked += _expect_value(calls, [], "历史损坏不发布")
    return checked


def main() -> int:
    try:
        checked = check_session_batch()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"会话写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话写入一致：{checked} 项批量追加与附件引用校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
