#!/usr/bin/env python3
"""核对附件添加的工作区边界、配额与原子发布。

`AttachmentStore.add` 只读取工作区内受支持后缀的普通文本文件：路径解析后必须
仍在允许根下，路径段不得命中保留目录或以 `.env` 开头；打开使用
`O_RDONLY | O_NONBLOCK | O_NOFOLLOW`，再按描述符确认普通文件，读取上限为
2 MiB + 1。正文必须是 UTF-8，摘要为 SHA-256。`_publish_object` 先查重，再按
增量计数判定字节与对象两项配额；候选文件为 `tmp-` + uuid，独占创建、fsync 后
`os.replace` 发布，记账完成才回调，finally 清理临时名。`add` 在发布之后失败时
清理未引用对象，只有清理成功才回退计数。这里先按源码顺序固定这些边界，再用
临时工作区与合成会话实际执行 `add`、配额判定与对象校验。
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.resources import (  # noqa: E402
    _MAX_ATTACHMENT_STORAGE_LIMIT,
    AttachmentQuotaExceeded,
    AttachmentStorageLimits,
    AttachmentStore,
)

ADD_ORDER = (
    "def add(self, thread_id: str, path: str) -> dict:",
    "self.sessions.require_thread(thread_id)",
    "if not isinstance(path, str) or not path:",
    'raise ValueError("path 必须是工作区内的文本文件")',
    "source = _resolved_or_absolute(self.allowed_root / path)",
    "if (not source.is_relative_to(self.allowed_root) or source.suffix.lower() not in self.EXTENSIONS",
    'or any(p in {".git", "node_modules", ".venv", ".boss-cli", ".boss-harness"} or p.startswith(".env")',
    "for p in source.relative_to(self.allowed_root).parts)):",
    'raise ValueError("附件必须是工作区内支持的文本文件")',
    'descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))',
    'raise ValueError("附件必须是工作区内可读取的普通文本文件") from None',
    "if not stat.S_ISREG(os.fstat(descriptor).st_mode):",
    'raise ValueError("附件必须是工作区内的普通文本文件")',
    "data = handle.read(self.MAX_BYTES + 1)",
    "if len(data) > self.MAX_BYTES:",
    'raise ValueError("文本附件不得超过 2 MiB")',
    'data.decode("utf-8")',
    'raise ValueError("文本附件必须是 UTF-8 文本") from None',
    "digest = hashlib.sha256(data).hexdigest()",
    'attachment = {"id": uuid.uuid4().hex, "name": wire_text(source.name), "digest": digest,',
    '"bytes": len(data), "mediaType": "text/plain; charset=utf-8"}',
    "published = False",
    "def mark_published() -> None:",
    "published = True",
    "self.sessions.append_attachment(",
    'thread_id, Entry(type="attachment", payload=attachment),',
    "lambda: self._publish_object(digest, data, mark_published),",
    "except BaseException:",
    "self.sessions.cleanup_unreferenced_attachments([digest])",
    "self._used_bytes -= len(data)",
    "self._used_objects -= 1",
    "return attachment",
)
PUBLISH_ORDER = (
    "def _publish_object(self, digest: str, data: bytes, on_published: Callable[[], None]) -> None:",
    "existing = self._read_object(digest, len(data))",
    "if existing is not None:",
    "return",
    "used_bytes, used_objects = self._storage_usage()",
    "exceeds_bytes = used_bytes + len(data) > self.limits.max_bytes",
    "exceeds_objects = used_objects + 1 > self.limits.max_objects",
    "if exceeds_bytes or exceeds_objects:",
    "raise AttachmentQuotaExceeded(self.limits, used_bytes, used_objects, len(data))",
    'temporary = self.root / ("tmp-" + uuid.uuid4().hex)',
    "descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)",
    "handle.write(data)",
    "handle.flush()",
    "os.fsync(handle.fileno())",
    "os.replace(temporary, self.root / digest)",
    "self._used_bytes += len(data)",
    "self._used_objects += 1",
    "on_published()",
    "temporary.unlink(missing_ok=True)",
)
READ_OBJECT_ORDER = (
    "def _read_object(self, digest: str, expected_bytes: int) -> bytes | None:",
    "path = self.root / digest",
    "observed = path.lstat()",
    "except FileNotFoundError:",
    "return None",
    "if (not stat.S_ISREG(observed.st_mode) or observed.st_uid != os.getuid()",
    "or observed.st_nlink != 1 or observed.st_size != expected_bytes):",
    'raise ValueError("附件内容已损坏；请重新添加")',
    "restrict_private_file(path)",
    'descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))',
    "opened = os.fstat(descriptor)",
    "if ((opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino)",
    "data = handle.read(self.MAX_BYTES + 1)",
    'raise ValueError("附件内容不可读取；请重新添加") from None',
    "os.close(descriptor)",
    'if (len(data) != expected_bytes or hashlib.sha256(data).hexdigest() != digest):',
    "return data",
)
STORAGE_ORDER = (
    "def _storage_usage(self) -> tuple[int, int]:",
    "root_stat = self.root.lstat()",
    "except FileNotFoundError:",
    'raise ValueError("附件目录不可用") from None',
    "if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.getuid():",
    'raise ValueError("附件目录不可信，写入已停止")',
    "return self._used_bytes, self._used_objects",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AttachmentStore":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 AttachmentStore.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_attachment_add() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    add = _method(tree, source, "add")
    publish = _method(tree, source, "_publish_object")
    read_object = _method(tree, source, "_read_object")
    storage = _method(tree, source, "_storage_usage")
    checked = _ordered(ADD_ORDER, add, RESOURCES)
    checked += _ordered(PUBLISH_ORDER, publish, RESOURCES)
    checked += _ordered(READ_OBJECT_ORDER, read_object, RESOURCES)
    checked += _ordered(STORAGE_ORDER, storage, RESOURCES)
    # 工作区路径：解析后仍须在允许根下，后缀与保留路径段都受限于固定集合。
    if add.count("source.is_relative_to(self.allowed_root)") != 1:
        raise ValueError(f"{RESOURCES} 的附件路径必须限定在允许根下")
    checked += 1
    if add.count("source.suffix.lower() not in self.EXTENSIONS") != 1:
        raise ValueError(f"{RESOURCES} 的附件后缀必须匹配固定扩展名集合")
    checked += 1
    if add.count('p.startswith(".env")') != 1:
        raise ValueError(f"{RESOURCES} 的附件路径必须拒绝环境文件")
    checked += 1
    if "O_NOFOLLOW" not in add or "O_NONBLOCK" not in add:
        raise ValueError(f"{RESOURCES} 的附件必须非阻塞且不跟随符号链接打开")
    checked += 1
    if add.count("self.MAX_BYTES + 1") != 1 or add.count("if len(data) > self.MAX_BYTES:") != 1:
        raise ValueError(f"{RESOURCES} 的附件必须读取上限 + 1 字节后拒绝超限")
    checked += 1
    if add.count('data.decode("utf-8")') != 1:
        raise ValueError(f"{RESOURCES} 的附件必须是 UTF-8 文本")
    checked += 1
    if add.count("name\": wire_text(source.name)") != 1:
        raise ValueError(f"{RESOURCES} 的附件名必须经 wire_text 降级")
    checked += 1
    # 发布标记：只在发布回调中置一次，失败路径按标记决定是否清理。
    if add.count("def mark_published() -> None:\n            nonlocal published\n            published = True") != 1:
        raise ValueError(f"{RESOURCES} 的发布标记必须只置一次")
    checked += 1
    if add.count("self.sessions.cleanup_unreferenced_attachments([digest])") != 1:
        raise ValueError(f"{RESOURCES} 的发布失败必须清理未引用对象")
    checked += 1
    if add.count('                except Exception:\n                    pass\n                else:') != 1:
        raise ValueError(f"{RESOURCES} 的清理失败不得影响原异常")
    checked += 1
    if add.count("self._used_bytes -= len(data)") != 1 or add.count("self._used_objects -= 1") != 1:
        raise ValueError(f"{RESOURCES} 的清理成功必须回退配额计数")
    checked += 1
    if "\n            raise\n        return attachment" not in add:
        raise ValueError(f"{RESOURCES} 的失败必须重新抛出原异常")
    checked += 1
    # 发布：先查重，再按两项配额判定，临时文件独占创建后 fsync 替换。
    if publish.count("existing = self._read_object(digest, len(data))") != 1:
        raise ValueError(f"{RESOURCES} 的附件发布必须先查重")
    checked += 1
    if publish.count("exceeds_bytes = used_bytes + len(data) > self.limits.max_bytes") != 1:
        raise ValueError(f"{RESOURCES} 的附件字节配额必须严格大于")
    checked += 1
    if publish.count("exceeds_objects = used_objects + 1 > self.limits.max_objects") != 1:
        raise ValueError(f"{RESOURCES} 的附件对象配额必须严格大于")
    checked += 1
    if publish.count('temporary = self.root / ("tmp-" + uuid.uuid4().hex)') != 1:
        raise ValueError(f"{RESOURCES} 的附件临时名必须使用 tmp- 前缀")
    checked += 1
    if publish.count("os.O_WRONLY | os.O_EXCL") != 1:
        raise ValueError(f"{RESOURCES} 的附件临时文件必须独占创建")
    checked += 1
    if publish.count("os.fsync(handle.fileno())") != 1:
        raise ValueError(f"{RESOURCES} 的附件候选文件必须 fsync")
    checked += 1
    if publish.count("os.replace(temporary, self.root / digest)") != 1:
        raise ValueError(f"{RESOURCES} 的附件必须原子替换发布")
    checked += 1
    if publish.count("self._used_bytes += len(data)") != 1 or publish.count("self._used_objects += 1") != 1:
        raise ValueError(f"{RESOURCES} 的附件发布必须先记账")
    checked += 1
    if publish.index("self._used_objects += 1") > publish.index("on_published()"):
        raise ValueError(f"{RESOURCES} 的附件回调必须在记账之后")
    checked += 1
    if publish.count("temporary.unlink(missing_ok=True)") != 1:
        raise ValueError(f"{RESOURCES} 的附件临时文件必须在 finally 清理")
    checked += 1
    # 读取对象：lstat、打开后 fstat 与内容摘要三层校验。
    if read_object.count('raise ValueError("附件内容已损坏；请重新添加")') != 3:
        raise ValueError(f"{RESOURCES} 的附件读取必须有三处损坏判定")
    checked += 1
    if read_object.count("O_NOFOLLOW") != 1 or read_object.count("O_NONBLOCK") != 1:
        raise ValueError(f"{RESOURCES} 的附件读取必须非阻塞且不跟随符号链接")
    checked += 1
    if read_object.count("os.close(descriptor)") != 1:
        raise ValueError(f"{RESOURCES} 的附件读取必须关闭未移交的描述符")
    checked += 1
    if read_object.count("hashlib.sha256(data).hexdigest() != digest") != 1:
        raise ValueError(f"{RESOURCES} 的附件读取必须复核 SHA-256")
    checked += 1
    # 配额快照：只校验目录身份并返回增量计数，不重扫对象。
    if "iterdir" in storage:
        raise ValueError(f"{RESOURCES} 的配额读取不得重扫附件目录")
    checked += 1
    if "class AttachmentQuotaExceeded(" not in source:
        raise ValueError(f"{RESOURCES} 缺少 AttachmentQuotaExceeded")
    checked += 1
    return checked


class _Sessions:
    def __init__(self, *, fail_before_publish: Exception | None = None,
                 fail_after_publish: Exception | None = None,
                 fail_cleanup: Exception | None = None) -> None:
        self.entries: list = []
        self.cleaned: list[list[str]] = []
        self.threads: list[str] = []
        self.fail_before_publish = fail_before_publish
        self.fail_after_publish = fail_after_publish
        self.fail_cleanup = fail_cleanup

    def require_thread(self, thread_id: str) -> None:
        self.threads.append(thread_id)

    def append_attachment(self, thread_id: str, entry, publish) -> None:
        if self.fail_before_publish is not None:
            raise self.fail_before_publish
        publish()
        self.entries.append(entry)
        if self.fail_after_publish is not None:
            raise self.fail_after_publish

    def cleanup_unreferenced_attachments(self, digests: list[str]) -> None:
        self.cleaned.append(list(digests))
        if self.fail_cleanup is not None:
            raise self.fail_cleanup

    def cleanup_attachment_temporaries(self) -> None:
        return None


def _store(base: Path, name: str, sessions: _Sessions,
           limits: AttachmentStorageLimits | None = None) -> tuple[AttachmentStore, Path]:
    workspace = base / f"{name}-workspace"
    workspace.mkdir(parents=True)
    store = AttachmentStore(sessions, base / f"{name}-state", workspace,
                            limits=limits if limits is not None else AttachmentStorageLimits())
    return store, workspace


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"附件添加行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"附件添加行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"附件添加行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"附件添加行为变化 {label}：未抛出错误")


def _expect_quota(call, label: str, **expected: int) -> int:
    try:
        call()
    except AttachmentQuotaExceeded as error:
        checked = _expect_value(
            str(error), "附件存储空间或对象数量已达到上限；请清理状态目录或调整内核配置",
            label + "消息")
        data = error.data
        checked += _expect_value(data.get("code"), "ATTACHMENT_STORAGE_LIMIT", label + "数据码")
        for key, value in expected.items():
            checked += _expect_value(data.get(key), value, f"{label} {key}")
        return checked
    except Exception as error:
        raise ValueError(
            f"附件添加行为变化 {label}：期望 AttachmentQuotaExceeded，实际 "
            f"{type(error).__name__}") from None
    raise ValueError(f"附件添加行为变化 {label}：未抛出错误")


def _read_limit(value: str) -> int:
    name = AttachmentStore.MAX_STORAGE_BYTES_ENV
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        return AttachmentStore._read_limit(name, 99)
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _behavior_checks() -> int:
    checked = 0
    message_path = "path 必须是工作区内的文本文件"
    message_workspace = "附件必须是工作区内支持的文本文件"
    message_readable = "附件必须是工作区内可读取的普通文本文件"
    message_regular = "附件必须是工作区内的普通文本文件"
    message_corrupt = "附件内容已损坏；请重新添加"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        sessions = _Sessions()
        store, workspace = _store(base, "paths", sessions)
        (workspace / "notes.txt").write_text("hello", encoding="utf-8")

        checked += _expect_error(lambda: store.add("thread-1", ""), message_path, "空路径")
        checked += _expect_error(lambda: store.add("thread-1", 123), message_path, "非字符串路径")
        checked += _expect_error(lambda: store.add("thread-1", "../escape.txt"),
                                 message_workspace, "越界路径")
        (workspace / "notes.bin").write_text("x", encoding="utf-8")
        checked += _expect_error(lambda: store.add("thread-1", "notes.bin"),
                                 message_workspace, "不支持后缀")
        (workspace / ".git").mkdir()
        (workspace / ".git" / "hook.txt").write_text("x", encoding="utf-8")
        checked += _expect_error(lambda: store.add("thread-1", ".git/hook.txt"),
                                 message_workspace, "保留目录")
        (workspace / ".env").write_text("SECRET=1", encoding="utf-8")
        checked += _expect_error(lambda: store.add("thread-1", ".env"),
                                 message_workspace, ".env 文件")
        # 带支持后缀的 .env 前缀文件只能被路径段规则拒绝，隔离后缀检查。
        (workspace / ".env.txt").write_text("SECRET=1", encoding="utf-8")
        checked += _expect_error(lambda: store.add("thread-1", ".env.txt"),
                                 message_workspace, ".env 前缀")
        checked += _expect_error(lambda: store.add("thread-1", "missing.txt"),
                                 message_readable, "缺失文件")
        (workspace / "folder.txt").mkdir()
        checked += _expect_error(lambda: store.add("thread-1", "folder.txt"),
                                 message_regular, "目录")
        (base / "outside.txt").write_text("secret", encoding="utf-8")
        (workspace / "escape-link.txt").symlink_to(base / "outside.txt")
        checked += _expect_error(lambda: store.add("thread-1", "escape-link.txt"),
                                 message_workspace, "符号链接越界")
        # 工作区内链接先解析再打开：记录按目标文件名与内容登记。
        (workspace / "alias.txt").symlink_to(workspace / "notes.txt")
        alias = store.add("thread-1", "alias.txt")
        checked += _expect_value((alias["name"], alias["digest"]),
                                 ("notes.txt", hashlib.sha256(b"hello").hexdigest()),
                                 "符号链接按解析目标读取")
        (workspace / "huge.txt").write_bytes(b"a" * (AttachmentStore.MAX_BYTES + 1))
        checked += _expect_error(lambda: store.add("thread-1", "huge.txt"),
                                 "文本附件不得超过 2 MiB", "超限文件")
        (workspace / "binary.txt").write_bytes(b"\xff\xfe")
        checked += _expect_error(lambda: store.add("thread-1", "binary.txt"),
                                 "文本附件必须是 UTF-8 文本", "非 UTF-8")

        success_sessions = _Sessions()
        success_store, success_ws = _store(base, "success", success_sessions)
        (success_ws / "notes.txt").write_text("hello", encoding="utf-8")
        attachment = success_store.add("thread-1", "notes.txt")
        digest = hashlib.sha256(b"hello").hexdigest()
        checked += _expect_value(
            (attachment["name"], attachment["bytes"], attachment["mediaType"]),
            ("notes.txt", 5, "text/plain; charset=utf-8"), "记录字段")
        checked += _expect_value(attachment["digest"], digest, "内容摘要")
        checked += _expect_value(len(attachment["id"]), 32, "附件 id 长度")
        checked += _expect_value(
            all(char in "0123456789abcdef" for char in attachment["id"]), True,
            "附件 id 十六进制")
        checked += _expect_value((success_store._used_bytes, success_store._used_objects),
                                 (5, 1), "添加后计数")
        checked += _expect_value((success_store.root / digest).read_bytes(), b"hello",
                                 "对象落盘")
        checked += _expect_value(success_sessions.threads, ["thread-1"], "会话校验")
        checked += _expect_value(
            (success_sessions.entries[0].type, success_sessions.entries[0].payload),
            ("attachment", attachment), "发布条目")

        again = success_store.add("thread-1", "notes.txt")
        checked += _expect_value(again["id"] != attachment["id"], True, "重复添加新 id")
        checked += _expect_value((success_store._used_bytes, success_store._used_objects),
                                 (5, 1), "重复添加不重复计数")
        checked += _expect_value(len(list(success_store.root.iterdir())), 1,
                                 "重复添加不重复落盘")

        empty_sessions = _Sessions()
        empty_store, empty_ws = _store(base, "empty", empty_sessions)
        (empty_ws / "empty.txt").write_bytes(b"")
        empty = empty_store.add("thread-1", "empty.txt")
        checked += _expect_value(
            (empty["bytes"], empty_store._used_bytes, empty_store._used_objects),
            (0, 0, 1), "空文件")

        boundary_sessions = _Sessions()
        boundary_store, boundary_ws = _store(
            base, "boundary", boundary_sessions,
            AttachmentStorageLimits(max_bytes=5, max_objects=10))
        (boundary_ws / "five.txt").write_text("hello", encoding="utf-8")
        boundary_store.add("thread-1", "five.txt")
        checked += _expect_value((boundary_store._used_bytes, boundary_store._used_objects),
                                 (5, 1), "字节配额等于上限允许")

        quota_sessions = _Sessions()
        quota_store, quota_ws = _store(
            base, "bytes-quota", quota_sessions,
            AttachmentStorageLimits(max_bytes=4, max_objects=10))
        (quota_ws / "five.txt").write_text("hello", encoding="utf-8")
        checked += _expect_quota(
            lambda: quota_store.add("thread-1", "five.txt"), "字节配额",
            usedBytes=0, limitBytes=4, requestedBytes=5, usedObjects=0,
            limitObjects=10, requestedObjects=1)
        checked += _expect_value((quota_store._used_bytes, quota_store._used_objects),
                                 (0, 0), "配额拒绝不计数")
        checked += _expect_value(list(quota_store.root.iterdir()), [], "配额拒绝不落盘")

        objects_sessions = _Sessions()
        objects_store, objects_ws = _store(
            base, "objects-quota", objects_sessions,
            AttachmentStorageLimits(max_bytes=1024, max_objects=1))
        (objects_ws / "a.txt").write_text("aaa", encoding="utf-8")
        (objects_ws / "b.txt").write_text("bbb", encoding="utf-8")
        objects_store.add("thread-1", "a.txt")
        checked += _expect_quota(
            lambda: objects_store.add("thread-1", "b.txt"), "对象配额",
            usedBytes=3, limitBytes=1024, requestedBytes=3, usedObjects=1,
            limitObjects=1, requestedObjects=1)
        checked += _expect_value((objects_store._used_bytes, objects_store._used_objects),
                                 (3, 1), "对象配额拒绝不计数")

        dedupe_sessions = _Sessions()
        dedupe_store, dedupe_ws = _store(
            base, "dedupe-quota", dedupe_sessions,
            AttachmentStorageLimits(max_bytes=3, max_objects=1))
        (dedupe_ws / "a.txt").write_text("aaa", encoding="utf-8")
        dedupe_store.add("thread-1", "a.txt")
        dedupe_store.add("thread-1", "a.txt")
        checked += _expect_value((dedupe_store._used_bytes, dedupe_store._used_objects),
                                 (3, 1), "去重优先于配额")

        fail_sessions = _Sessions(fail_after_publish=RuntimeError("发布后失败"))
        fail_store, fail_ws = _store(base, "rollback", fail_sessions)
        (fail_ws / "a.txt").write_text("hello", encoding="utf-8")
        try:
            fail_store.add("thread-1", "a.txt")
        except RuntimeError as error:
            checked += _expect_value(str(error), "发布后失败", "原异常重新抛出")
        else:
            raise ValueError("附件添加行为变化 发布后失败：未抛出错误")
        checked += _expect_value(fail_sessions.cleaned, [[digest]], "发布失败清理未引用对象")
        checked += _expect_value((fail_store._used_bytes, fail_store._used_objects),
                                 (0, 0), "清理成功回退计数")

        pre_sessions = _Sessions(fail_before_publish=RuntimeError("发布前失败"))
        pre_store, pre_ws = _store(base, "pre-failure", pre_sessions)
        (pre_ws / "a.txt").write_text("hello", encoding="utf-8")
        try:
            pre_store.add("thread-1", "a.txt")
        except RuntimeError as error:
            checked += _expect_value(str(error), "发布前失败", "发布前异常原样抛出")
        else:
            raise ValueError("附件添加行为变化 发布前失败：未抛出错误")
        checked += _expect_value(pre_sessions.cleaned, [], "未发布失败不清理")
        checked += _expect_value((pre_store._used_bytes, pre_store._used_objects),
                                 (0, 0), "未发布失败不计数")

        both_sessions = _Sessions(fail_after_publish=RuntimeError("发布后失败"),
                                  fail_cleanup=RuntimeError("清理失败"))
        both_store, both_ws = _store(base, "cleanup-failure", both_sessions)
        (both_ws / "a.txt").write_text("hello", encoding="utf-8")
        try:
            both_store.add("thread-1", "a.txt")
        except RuntimeError as error:
            checked += _expect_value(str(error), "发布后失败", "清理失败仍抛原异常")
        else:
            raise ValueError("附件添加行为变化 清理失败：未抛出错误")
        checked += _expect_value((both_store._used_bytes, both_store._used_objects),
                                 (5, 1), "清理失败不回退计数")

        guard_sessions = _Sessions()
        guard_store, guard_ws = _store(base, "missing-root", guard_sessions)
        (guard_ws / "a.txt").write_text("hello", encoding="utf-8")
        guard_store.root.rmdir()
        checked += _expect_error(lambda: guard_store.add("thread-1", "a.txt"),
                                 "附件目录不可用", "目录缺失")

        file_sessions = _Sessions()
        file_store, file_ws = _store(base, "file-root", file_sessions)
        (file_ws / "a.txt").write_text("hello", encoding="utf-8")
        file_store.root.rmdir()
        file_store.root.write_text("x", encoding="utf-8")
        checked += _expect_error(lambda: file_store._storage_usage(),
                                 "附件目录不可信，写入已停止", "配额读取拒绝非目录")

        tampered_sessions = _Sessions()
        tampered_store, tampered_ws = _store(base, "tampered-object", tampered_sessions)
        (tampered_ws / "a.txt").write_text("hello", encoding="utf-8")
        (tampered_store.root / digest).write_bytes(b"HELLO")
        checked += _expect_error(lambda: tampered_store.add("thread-1", "a.txt"),
                                 message_corrupt, "对象内容被替换")

        short_sessions = _Sessions()
        short_store, short_ws = _store(base, "short-object", short_sessions)
        (short_ws / "a.txt").write_text("hello", encoding="utf-8")
        (short_store.root / digest).write_bytes(b"hell")
        checked += _expect_error(lambda: short_store.add("thread-1", "a.txt"),
                                 message_corrupt, "对象长度不符")

        link_sessions = _Sessions()
        link_store, link_ws = _store(base, "linked-object", link_sessions)
        (link_ws / "a.txt").write_text("hello", encoding="utf-8")
        (link_store.root / digest).write_bytes(b"hello")
        os.link(link_store.root / digest, link_store.root / "linked")
        checked += _expect_error(lambda: link_store.add("thread-1", "a.txt"),
                                 message_corrupt, "对象硬链接")

        limit_name = AttachmentStore.MAX_STORAGE_BYTES_ENV
        limit_message = f"{limit_name} 必须是 1 至 {_MAX_ATTACHMENT_STORAGE_LIMIT} 的十进制整数"
        checked += _expect_value(_read_limit(""), 99, "空白环境变量取默认值")
        checked += _expect_value(_read_limit("   "), 99, "全空白环境变量取默认值")
        checked += _expect_value(_read_limit(" 7 "), 7, "带空白数字")
        checked += _expect_error(lambda: _read_limit("0"), limit_message, "零值")
        checked += _expect_error(lambda: _read_limit("abc"), limit_message, "非数字")
        checked += _expect_error(lambda: _read_limit("9" * 20), limit_message, "超长数字")

        bytes_name = AttachmentStore.MAX_STORAGE_BYTES_ENV
        objects_name = AttachmentStore.MAX_STORAGE_OBJECTS_ENV
        previous_bytes = os.environ.get(bytes_name)
        previous_objects = os.environ.get(objects_name)
        os.environ[bytes_name] = "7"
        os.environ[objects_name] = "3"
        try:
            limits = AttachmentStore.limits_from_environment()
        finally:
            for name, previous in ((bytes_name, previous_bytes), (objects_name, previous_objects)):
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous
        checked += _expect_value((limits.max_bytes, limits.max_objects), (7, 3),
                                 "环境变量组合")
    return checked


def main() -> int:
    try:
        checked = check_attachment_add()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"附件添加核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件添加一致：{checked} 项边界、配额与发布校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
