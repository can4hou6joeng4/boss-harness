#!/usr/bin/env python3
"""核对附件分页读取的游标绑定与解码边界。

`AttachmentStore.read_chunk` 以 `contentRef` 绑定 `threadId` / `attachmentId` /
`sha256` / 字符长度：`limit` 只接受 1 到 `MAX_READ_CHARS` 的整数；继续读取时
`sha256` 必须匹配当前摘要，否则返回 `STALE_ATTACHMENT`（`-32011`）；游标载荷
是四元组，偏移必须严格小于文本长度，`end` 取 `min(offset + limit, len(text))`，
只有未读完时才生成 `at1_` 游标。记录字段与对象内容都可能被外部改写，摘要、
名称与字节范围按损坏处理，解码错误转为产品错误而不是内部错误。这里先按源码
顺序固定这些边界，再用合成条目与临时对象实际执行 `read_chunk` 与 `read`。
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.resources import AttachmentStorageLimits, AttachmentStore  # noqa: E402
from boss_harness.rpc import RpcError  # noqa: E402

READ_ORDER = (
    "def read(self, thread_id: str, attachment_id: str, *, include_content: bool = True) -> dict:",
    "return self._read_from_entries(thread_id, attachment_id, self.sessions.read_entries(thread_id),",
    "include_content=include_content)",
)
CHUNK_ORDER = (
    "def read_chunk(self, thread_id: str, attachment_id: str, *, cursor: str | None = None,",
    "limit: int = DEFAULT_READ_CHARS, sha256: str | None = None) -> dict:",
    "if type(limit) is not int or not 1 <= limit <= self.MAX_READ_CHARS:",
    'raise ValueError(f"limit 必须是 1 到 {self.MAX_READ_CHARS} 的整数")',
    "item = self._attachment_entry(thread_id, attachment_id)",
    'data = self._read_object(item["digest"], item["bytes"])',
    "if data is None:",
    'raise ValueError("附件内容已损坏；请重新添加")',
    "text = _decode_attachment_text(data)",
    'reference = {"threadId": thread_id, "attachmentId": item["id"], "name": item["name"],',
    '"sha256": item["digest"], "byteLength": item["bytes"],',
    '"characterLength": len(text)}',
    "offset = 0",
    "if sha256 is not None:",
    'if not isinstance(sha256, str) or re.fullmatch(r"[a-f0-9]{64}", sha256) is None:',
    'raise ValueError("sha256 必须是附件内容引用中的 64 位小写十六进制摘要")',
    'if sha256 != item["digest"]:',
    "raise _stale_attachment(reference)",
    "if cursor is not None:",
    "offset = _attachment_cursor_offset(cursor, reference, len(text))",
    "end = min(offset + limit, len(text))",
    "next_cursor = None",
    "if end < len(text):",
    'raw = json.dumps([thread_id, item["id"], item["digest"], end],',
    'ensure_ascii=False, separators=(",", ":")).encode("utf-8")',
    'next_cursor = "at1_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")',
    'return {"text": wire_text(text[offset:end]), "offset": offset, "nextCursor": next_cursor,',
    '"contentRef": reference}',
)
ENTRY_ORDER = (
    "def _attachment_entry(self, thread_id: str, attachment_id: str) -> dict:",
    "entries = self.sessions.read_entries(thread_id)",
    "return self._attachment_from_entries(thread_id, attachment_id, entries)",
)
FROM_ENTRIES_ORDER = (
    "def _attachment_from_entries(self, thread_id: str, attachment_id: str, entries: list[dict]) -> dict:",
    'item = next((entry["payload"] for entry in entries',
    'if entry["type"] == "attachment" and entry["payload"].get("id") == attachment_id), None)',
    "if item is None:",
    'raise ValueError("附件不属于该会话")',
    'digest = item.get("digest")',
    'if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):',
    'raise ValueError("附件记录已损坏；请重新添加")',
    'name, size = item.get("name"), item.get("bytes")',
    "if (not isinstance(name, str) or not name or len(name) > 1024",
    "or type(size) is not int or not 0 <= size <= self.MAX_BYTES):",
    'raise ValueError("附件记录已损坏；请重新添加")',
    'return {**item, "name": wire_text(name)}',
)
READ_FROM_ENTRIES_ORDER = (
    "def _read_from_entries(self, thread_id: str, attachment_id: str, entries: list[dict], *,",
    "include_content: bool = True) -> dict:",
    "item = self._attachment_from_entries(thread_id, attachment_id, entries)",
    "result = dict(item)",
    "if include_content:",
    'data = self._read_object(item["digest"], item["bytes"])',
    "if data is None:",
    'raise ValueError("附件内容已损坏；请重新添加")',
    'result["content"] = _decode_attachment_text(data)',
    "return result",
)
CURSOR_ORDER = (
    "def _attachment_cursor_offset(cursor: Any, reference: dict, length: int) -> int:",
    'if not isinstance(cursor, str) or not cursor.startswith("at1_") or len(cursor) > 2048:',
    "encoded = cursor[4:]",
    'value = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4),',
    'altchars=b"-_", validate=True))',
    "if (not isinstance(value, list) or len(value) != 4",
    'or value[:3] != [reference["threadId"], reference["attachmentId"], reference["sha256"]]',
    "or type(value[3]) is not int or not 0 <= value[3] < length):",
    "return value[3]",
    "except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, RecursionError):",
    'raise ValueError("附件分页游标无效、归属不匹配或内容已变化") from None',
)
DECODE_ORDER = (
    "def _decode_attachment_text(data: bytes) -> str:",
    'return data.decode("utf-8")',
    "except UnicodeDecodeError:",
    'raise ValueError("附件内容不是 UTF-8 文本；请重新添加") from None',
)
STALE_ORDER = (
    "def _stale_attachment(reference: dict) -> Exception:",
    "from boss_harness.rpc import RpcError",
    'return RpcError(-32011, "附件内容已变化，请重新读取附件并确认新的内容引用",',
    '{"code": "STALE_ATTACHMENT", "currentRef": reference})',
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


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_attachment_read() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    read = _method(tree, source, "read")
    chunk = _method(tree, source, "read_chunk")
    entry = _method(tree, source, "_attachment_entry")
    from_entries = _method(tree, source, "_attachment_from_entries")
    read_from_entries = _method(tree, source, "_read_from_entries")
    cursor = _function(tree, source, "_attachment_cursor_offset")
    decode = _function(tree, source, "_decode_attachment_text")
    stale = _function(tree, source, "_stale_attachment")
    checked = _ordered(READ_ORDER, read, RESOURCES)
    checked += _ordered(CHUNK_ORDER, chunk, RESOURCES)
    checked += _ordered(ENTRY_ORDER, entry, RESOURCES)
    checked += _ordered(FROM_ENTRIES_ORDER, from_entries, RESOURCES)
    checked += _ordered(READ_FROM_ENTRIES_ORDER, read_from_entries, RESOURCES)
    checked += _ordered(CURSOR_ORDER, cursor, RESOURCES)
    checked += _ordered(DECODE_ORDER, decode, RESOURCES)
    checked += _ordered(STALE_ORDER, stale, RESOURCES)
    # 读取入口只复用条目投影，不直接触碰对象文件。
    if read.count("self._read_from_entries(") != 1 or "_read_object" in read:
        raise ValueError(f"{RESOURCES} 的附件读取必须经条目投影复用")
    checked += 1
    # 记录字段不可信：摘要、名称与字节范围不合法时按损坏处理。
    if from_entries.count('raise ValueError("附件记录已损坏；请重新添加")') != 2:
        raise ValueError(f"{RESOURCES} 的附件记录必须有两处损坏判定")
    checked += 1
    if 'if entry["type"] == "attachment" and entry["payload"].get("id") == attachment_id), None)' not in from_entries:
        raise ValueError(f"{RESOURCES} 的附件查找必须按条目 id 精确匹配")
    checked += 1
    if 'return {**item, "name": wire_text(name)}' not in from_entries:
        raise ValueError(f"{RESOURCES} 的附件名必须经 wire_text 降级")
    checked += 1
    # 完整读取复制记录，只在需要正文时读对象。
    if "result = dict(item)" not in read_from_entries:
        raise ValueError(f"{RESOURCES} 的附件读取必须复制记录")
    checked += 1
    if "if include_content:\n            data = self._read_object(" not in read_from_entries:
        raise ValueError(f"{RESOURCES} 的附件读取必须按 include_content 决定是否读对象")
    checked += 1
    if 'result["content"] = _decode_attachment_text(data)' not in read_from_entries:
        raise ValueError(f"{RESOURCES} 的附件正文必须经解码辅助函数")
    checked += 1
    # 分页：限制严格范围，先取记录再读对象。
    if chunk.count("if type(limit) is not int or not 1 <= limit <= self.MAX_READ_CHARS:") != 1:
        raise ValueError(f"{RESOURCES} 的分页 limit 必须是严格范围内的整数")
    checked += 1
    if chunk.count('data = self._read_object(item["digest"], item["bytes"])') != 1:
        raise ValueError(f"{RESOURCES} 的分页必须按记录读取对象")
    checked += 1
    # 继续读取必须绑定同一摘要，否则返回 STALE_ATTACHMENT。
    if chunk.count("raise _stale_attachment(reference)") != 1:
        raise ValueError(f"{RESOURCES} 的摘要变化必须返回 STALE_ATTACHMENT")
    checked += 1
    if "offset = _attachment_cursor_offset(cursor, reference, len(text))" not in chunk:
        raise ValueError(f"{RESOURCES} 的游标必须绑定当前引用与文本长度")
    checked += 1
    # 分页只返回已读范围，游标只在未读完时生成。
    if chunk.count("end = min(offset + limit, len(text))") != 1:
        raise ValueError(f"{RESOURCES} 的分页必须截断到文本长度")
    checked += 1
    if chunk.count("next_cursor = None") != 1:
        raise ValueError(f"{RESOURCES} 的分页必须默认没有后续游标")
    checked += 1
    if "if end < len(text):\n            raw = json.dumps([thread_id, item[\"id\"], item[\"digest\"], end]," not in chunk:
        raise ValueError(f"{RESOURCES} 的后续游标必须只在未读完时生成")
    checked += 1
    if 'ensure_ascii=False' not in chunk or 'separators=(",", ":")' not in chunk:
        raise ValueError(f"{RESOURCES} 的游标载荷必须是紧凑 JSON")
    checked += 1
    if 'next_cursor = "at1_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")' not in chunk:
        raise ValueError(f"{RESOURCES} 的游标必须使用 at1_ 前缀与无填充编码")
    checked += 1
    if 'return {"text": wire_text(text[offset:end]), "offset": offset, "nextCursor": next_cursor,' not in chunk:
        raise ValueError(f"{RESOURCES} 的分页正文必须经 wire_text 降级")
    checked += 1
    if '"characterLength": len(text)}' not in chunk or '"byteLength": item["bytes"],' not in chunk:
        raise ValueError(f"{RESOURCES} 的 contentRef 必须带字节与字符长度")
    checked += 1
    # 游标解析：前缀、长度、四元组、严格偏移范围与异常集合。
    if cursor.count('cursor.startswith("at1_")') != 1 or cursor.count("len(cursor) > 2048") != 1:
        raise ValueError(f"{RESOURCES} 的游标必须校验前缀与长度")
    checked += 1
    if cursor.count('validate=True') != 1 or cursor.count('altchars=b"-_"') != 1:
        raise ValueError(f"{RESOURCES} 的游标必须严格解码 base64url")
    checked += 1
    if cursor.count("len(value) != 4") != 1 or "0 <= value[3] < length" not in cursor:
        raise ValueError(f"{RESOURCES} 的游标载荷必须是四元组且偏移严格小于长度")
    checked += 1
    if cursor.count("except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, RecursionError):") != 1:
        raise ValueError(f"{RESOURCES} 的游标必须捕获全部解析异常")
    checked += 1
    if 'raise ValueError("附件分页游标无效、归属不匹配或内容已变化") from None' not in cursor:
        raise ValueError(f"{RESOURCES} 的游标错误必须是产品错误")
    checked += 1
    # 解码与陈旧引用：错误码与消息保持稳定。
    if decode.count("except UnicodeDecodeError:") != 1:
        raise ValueError(f"{RESOURCES} 的附件正文必须捕获解码错误")
    checked += 1
    if 'raise ValueError("附件内容不是 UTF-8 文本；请重新添加") from None' not in decode:
        raise ValueError(f"{RESOURCES} 的解码错误必须转为产品错误")
    checked += 1
    if stale.count("-32011") != 1 or stale.count("STALE_ATTACHMENT") != 1:
        raise ValueError(f"{RESOURCES} 的陈旧附件必须使用固定错误码")
    checked += 1
    if stale.count('"currentRef": reference') != 1:
        raise ValueError(f"{RESOURCES} 的陈旧附件必须返回当前引用")
    checked += 1
    return checked


class _Sessions:
    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries

    def read_entries(self, thread_id: str) -> list[dict]:
        return self.entries

    def cleanup_attachment_temporaries(self) -> None:
        return None


def _payload(data: bytes, **overrides: object) -> dict:
    payload = {"id": "a1", "name": "note.txt", "digest": hashlib.sha256(data).hexdigest(),
               "bytes": len(data), "mediaType": "text/plain; charset=utf-8"}
    payload.update(overrides)
    return payload


def _store(root: Path, payload: dict, object_data: bytes | None = None) -> AttachmentStore:
    # 对象文件按记录摘要落盘；损坏记录与缺失对象用例不写文件。
    if object_data is not None:
        root.mkdir(parents=True, exist_ok=True)
        (root / payload["digest"]).write_bytes(object_data)
    sessions = _Sessions([{"type": "attachment", "payload": payload}])
    return AttachmentStore(sessions, root, root, limits=AttachmentStorageLimits())


def _cursor(payload: list) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "at1_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _cursor_payload(cursor: str) -> list:
    encoded = cursor[4:]
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"附件分页读取行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"附件分页读取行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"附件分页读取行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"附件分页读取行为变化 {label}：未抛出错误")


def _expect_rpc(call, message: str, label: str) -> int:
    try:
        call()
    except RpcError as error:
        checked = _expect_value(error.code, -32011, label + "错误码")
        checked += _expect_value(str(error), message, label + "消息")
        checked += _expect_value(error.data.get("code"), "STALE_ATTACHMENT", label + "数据码")
        return checked
    except Exception as error:
        raise ValueError(
            f"附件分页读取行为变化 {label}：期望 RpcError，实际 {type(error).__name__}") from None
    raise ValueError(f"附件分页读取行为变化 {label}：未抛出错误")


def _behavior_checks() -> int:
    checked = 0
    message_corrupt = "附件内容已损坏；请重新添加"
    message_record = "附件记录已损坏；请重新添加"
    message_cursor = "附件分页游标无效、归属不匹配或内容已变化"
    message_limit = f"limit 必须是 1 到 {AttachmentStore.MAX_READ_CHARS} 的整数"
    message_sha = "sha256 必须是附件内容引用中的 64 位小写十六进制摘要"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        text = "abcdef"
        data = text.encode("utf-8")
        payload = _payload(data)
        digest = payload["digest"]
        store = _store(base / "base", payload, data)

        full = store.read_chunk("thread-1", "a1")
        checked += _expect_value(full["text"], text, "完整一页正文")
        checked += _expect_value(full["offset"], 0, "完整一页偏移")
        checked += _expect_value(full["nextCursor"], None, "完整一页无后续游标")
        reference = {"threadId": "thread-1", "attachmentId": "a1", "name": "note.txt",
                     "sha256": digest, "byteLength": 6, "characterLength": 6}
        checked += _expect_value(full["contentRef"], reference, "内容引用字段")

        first = store.read_chunk("thread-1", "a1", limit=4)
        checked += _expect_value(first["text"], "abcd", "首段正文")
        checked += _expect_value(first["offset"], 0, "首段偏移")
        checked += _expect_value(isinstance(first["nextCursor"], str), True, "后续游标类型")
        checked += _expect_value(first["nextCursor"].startswith("at1_"), True, "后续游标前缀")
        checked += _expect_value(_cursor_payload(first["nextCursor"]),
                                 ["thread-1", "a1", digest, 4], "后续游标载荷")
        second = store.read_chunk("thread-1", "a1", cursor=first["nextCursor"], limit=4,
                                  sha256=digest)
        checked += _expect_value((second["text"], second["offset"], second["nextCursor"]),
                                 ("ef", 4, None), "次段读完")
        tail = store.read_chunk("thread-1", "a1", cursor=_cursor(["thread-1", "a1", digest, 5]),
                                limit=4, sha256=digest)
        checked += _expect_value((tail["text"], tail["offset"], tail["nextCursor"]),
                                 ("f", 5, None), "末页截断")
        restart = store.read_chunk("thread-1", "a1", limit=2,
                                   cursor=_cursor(["thread-1", "a1", digest, 0]))
        checked += _expect_value((restart["text"], restart["offset"]), ("ab", 0), "零偏移游标")
        verified = store.read_chunk("thread-1", "a1", limit=2, sha256=digest)
        checked += _expect_value((verified["text"], verified["offset"]), ("ab", 0),
                                 "摘要校验后从头读取")

        # 分页按字符计数：同一游标在 12 字节 / 4 字符的文本上按 2 字符推进。
        unicode_data = "你好世界".encode("utf-8")
        unicode_store = _store(base / "unicode", _payload(unicode_data), unicode_data)
        unicode_first = unicode_store.read_chunk("thread-1", "a1", limit=2)
        checked += _expect_value(unicode_first["text"], "你好", "按字符分页正文")
        checked += _expect_value(unicode_first["contentRef"]["characterLength"], 4, "字符长度")
        checked += _expect_value(unicode_first["contentRef"]["byteLength"], 12, "字节长度")
        unicode_second = unicode_store.read_chunk("thread-1", "a1", limit=2,
                                                  cursor=unicode_first["nextCursor"])
        checked += _expect_value(
            (unicode_second["text"], unicode_second["offset"], unicode_second["nextCursor"]),
            ("世界", 2, None), "按字符续读")

        for limit in (0, AttachmentStore.MAX_READ_CHARS + 1, True, 1.0, "2"):
            checked += _expect_error(
                lambda: store.read_chunk("thread-1", "a1", limit=limit),
                message_limit, f"limit={limit!r}")
        for value in ("a" * 63, "A" * 64, 123):
            checked += _expect_error(
                lambda: store.read_chunk("thread-1", "a1", sha256=value),
                message_sha, f"sha256={value!r}")
        checked += _expect_rpc(
            lambda: store.read_chunk("thread-1", "a1", sha256="b" * 64),
            "附件内容已变化，请重新读取附件并确认新的内容引用", "摘要不匹配")
        try:
            store.read_chunk("thread-1", "a1", sha256="b" * 64)
        except RpcError as error:
            checked += _expect_value(error.data.get("currentRef"), reference,
                                     "陈旧引用携带当前引用")

        invalid_cursors = (
            "bad",
            b"at1_x",
            _cursor(["thread-2", "a1", digest, 2]),
            _cursor(["thread-1", "a2", digest, 2]),
            _cursor(["thread-1", "a1", "c" * 64, 2]),
            _cursor(["thread-1", "a1", digest]),
            _cursor(["thread-1", "a1", digest, 6]),
            _cursor(["thread-1", "a1", digest, -1]),
            _cursor(["thread-1", "a1", digest, True]),
            "at1_!!!",
            "at1_" + "A" * 2045,
        )
        for cursor in invalid_cursors:
            checked += _expect_error(
                lambda: store.read_chunk("thread-1", "a1", cursor=cursor),
                message_cursor, f"游标 {cursor!r}",)

        checked += _expect_error(lambda: store.read_chunk("thread-1", "a2"),
                                 "附件不属于该会话", "未知附件")
        broken = (
            {"digest": "XY"},
            {"name": ""},
            {"name": None},
            {"name": "x" * 1025},
            {"bytes": -1},
            {"bytes": True},
            {"bytes": AttachmentStore.MAX_BYTES + 1},
        )
        for index, overrides in enumerate(broken):
            broken_payload = _payload(data)
            broken_payload.update(overrides)
            broken_store = _store(base / f"broken-{index}", broken_payload)
            checked += _expect_error(lambda: broken_store.read_chunk("thread-1", "a1"),
                                     message_record, f"损坏记录 {overrides}")

        missing_store = _store(base / "missing", _payload(data))
        checked += _expect_error(lambda: missing_store.read_chunk("thread-1", "a1"),
                                 message_corrupt, "对象缺失")
        tampered_store = _store(base / "tampered", _payload(data), b"abcdeX")
        checked += _expect_error(lambda: tampered_store.read_chunk("thread-1", "a1"),
                                 message_corrupt, "对象内容被替换")
        binary_data = b"\xff\xfe\x00"
        binary_store = _store(base / "binary", _payload(binary_data), binary_data)
        checked += _expect_error(lambda: binary_store.read_chunk("thread-1", "a1"),
                                 "附件内容不是 UTF-8 文本；请重新添加", "非 UTF-8 对象")

        surrogate_store = _store(base / "surrogate", _payload(data, name="\ud800bad.txt"), data)
        degraded = surrogate_store.read_chunk("thread-1", "a1", limit=1)
        checked += _expect_value(degraded["contentRef"]["name"], "�bad.txt", "附件名降级")
        checked += _expect_value(degraded["contentRef"]["characterLength"], 6,
                                 "降级不改字符长度")

        record = store.read("thread-1", "a1", include_content=False)
        checked += _expect_value("content" in record, False, "不含正文读取")
        checked += _expect_value(record["name"], "note.txt", "不含正文仍返回记录")
        with_content = store.read("thread-1", "a1")
        checked += _expect_value(with_content["content"], text, "完整读取正文")
    return checked


def main() -> int:
    try:
        checked = check_attachment_read()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"附件分页读取核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件分页读取一致：{checked} 项游标、范围与解码校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
