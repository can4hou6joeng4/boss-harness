"""Bounded reads for durable assistant text and thinking content."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re

INLINE_ITEM_CONTENT_BYTES = 64 * 1024
DEFAULT_ITEM_CONTENT_CHARS = 16_384
MAX_ITEM_CONTENT_CHARS = 32_768

_REPLACEMENT = "�"


def wire_text(value: str) -> str:
    """传输文本：把无法编码为 UTF-8 的孤立代理项替换为 U+FFFD。

    持久记录可能含孤立代理项（损坏记录、surrogateescape 路径或旧版本写入）。
    JSON-RPC 帧按 `ensure_ascii=False` 编码，孤立代理项会让整次响应变成
    `RESPONSE_INVALID`；这里只替换代理项，其余字符与长度不变，分页 offset 仍按原文计算。
    """
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    return "".join(_REPLACEMENT if 0xD800 <= ord(char) <= 0xDFFF else char for char in value)


def wire_value(value):
    """递归清理投影中的字符串；正常数据原样返回，坏记录降级为可传输文本。"""
    if isinstance(value, str):
        return wire_text(value)
    if isinstance(value, list):
        return [wire_value(item) for item in value]
    if isinstance(value, dict):
        return {wire_text(key): wire_value(item) for key, item in value.items()}
    return value


def _utf8_size(value: str) -> int:
    # 与 result_reference 同一约定：摘要与字节数对含孤立代理项的原文给出相同结果。
    return len(value.encode("utf-8", "surrogatepass"))


def item_content_reference(thread_id: str, item_id: str, part: str, text: str,
                           snapshot_id: str | None = None) -> dict:
    if not isinstance(part, str) or part not in {"text", "thinking"}:
        raise ValueError("内容字段必须是 text 或 thinking")
    if not isinstance(text, str):
        raise ValueError("会话内容必须是文本")
    digest = hashlib.sha256()
    byte_length = 0
    for offset in range(0, len(text), 16_384):
        encoded = text[offset:offset + 16_384].encode("utf-8", "surrogatepass")
        digest.update(encoded)
        byte_length += len(encoded)
    reference = {"threadId": thread_id, "itemId": item_id, "part": part, "encoding": "text",
                 "sha256": digest.hexdigest(), "byteLength": byte_length,
                 "characterLength": len(text)}
    if snapshot_id is not None:
        reference["snapshotId"] = snapshot_id
    return reference


def project_item_content(thread_id: str, item: dict, *, snapshot_id: str | None = None) -> dict:
    projected = dict(item)
    if item.get("kind") != "agentMessage":
        return projected
    item_id = str(item["id"])
    for part in ("text", "thinking"):
        projected.pop(part + "Omitted", None)
        projected.pop(part + "Ref", None)
        text = item.get(part)
        if not isinstance(text, str):
            continue
        if len(text) <= INLINE_ITEM_CONTENT_BYTES and _utf8_size(text) <= INLINE_ITEM_CONTENT_BYTES:
            # 未省略的正文直接进入响应帧，先把孤立代理项换成可编码的替换字符。
            projected[part] = wire_text(text)
            continue
        projected.pop(part, None)
        projected[part + "Omitted"] = True
        projected[part + "Ref"] = item_content_reference(
            thread_id, item_id, part, text, snapshot_id
        )
    return projected


def read_item_content(thread_id: str, item: dict, *, part: str, sha256: str,
                      cursor: str | None = None, limit: int = DEFAULT_ITEM_CONTENT_CHARS,
                      snapshot_id: str | None = None) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_ITEM_CONTENT_CHARS:
        raise ValueError(f"limit 必须是 1 到 {MAX_ITEM_CONTENT_CHARS} 之间的整数")
    if (not isinstance(part, str) or part not in {"text", "thinking"}
            or item.get("kind") != "agentMessage"):
        raise ValueError("该条目没有可读取的文本或思考内容")
    if not isinstance(sha256, str) or re.fullmatch(r"[a-f0-9]{64}", sha256) is None:
        raise ValueError("sha256 必须是内容引用中的 64 位小写十六进制摘要")
    if snapshot_id is not None and (not isinstance(snapshot_id, str)
            or re.fullmatch(r"[a-f0-9]{32}", snapshot_id) is None):
        raise ValueError("snapshotId 格式无效")
    text = item.get(part)
    if not isinstance(text, str):
        raise ValueError("该条目没有可读取的文本或思考内容")
    reference = item_content_reference(thread_id, str(item["id"]), part, text, snapshot_id)
    if reference["sha256"] != sha256:
        _stale()
    offset = 0
    if cursor is not None:
        try:
            if not isinstance(cursor, str) or not cursor.startswith("ic1_") or len(cursor) > 2048:
                raise ValueError
            encoded = cursor[4:]
            value = json.loads(base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            ))
            expected = [thread_id, str(item["id"]), part, sha256, snapshot_id]
            if (not isinstance(value, list) or len(value) != 6 or value[:5] != expected
                    or type(value[5]) is not int or not 0 <= value[5] < len(text)):
                raise ValueError
            offset = value[5]
        except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, RecursionError):
            raise ValueError("内容游标无效、归属不匹配或快照已变化") from None
    end = min(offset + limit, len(text))
    next_cursor = None
    if end < len(text):
        payload = [thread_id, str(item["id"]), part, sha256, snapshot_id, end]
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        next_cursor = "ic1_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return {"text": wire_text(text[offset:end]), "offset": offset, "nextCursor": next_cursor,
            "contentRef": wire_value(reference)}


def _stale() -> None:
    from boss_harness.rpc import RpcError

    raise RpcError(-32011, "会话内容已变化，请重新读取条目并确认新内容引用",
                   {"code": "STALE_CONTENT"})
