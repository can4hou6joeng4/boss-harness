#!/usr/bin/env python3
"""核对附件添加的工作区边界、配额与原子发布。

`AttachmentStore.add` 只读取工作区内受支持后缀的普通文本文件：路径解析后必须
仍在允许根下，路径段不得命中保留目录或以 `.env` 开头；打开使用
`O_RDONLY | O_NONBLOCK | O_NOFOLLOW`，再按描述符确认普通文件，读取上限为
2 MiB + 1。正文必须是 UTF-8，摘要为 SHA-256。`_publish_object` 先查重，再按
增量计数判定字节与对象两项配额；候选文件为 `tmp-` + uuid，独占创建、fsync 后
`os.replace` 发布，记账完成才回调，finally 清理临时名。`add` 在发布之后失败时
清理未引用对象，只有清理成功才回退计数。这里按源码顺序固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

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


def main() -> int:
    try:
        checked = check_attachment_add()
    except (ValueError, SyntaxError) as error:
        print(f"附件添加核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件添加一致：{checked} 项边界、配额与发布校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
