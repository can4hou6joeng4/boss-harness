"""Bounded reads for durable assistant text and thinking content."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re

INLINE_ITEM_CONTENT_BYTES = 64 * 1024
DEFAULT_ITEM_CONTENT_CHARS = 16_384
MAX_ITEM_CONTENT_CHARS = 32_768

_REPLACEMENT = "�"

#: 游标载荷的规范形式：urlsafe base64，可带规范填充或省略尾部填充。
_CURSOR_B64 = re.compile(r"[A-Za-z0-9_-]*={0,2}\Z")


def decode_cursor_base64(encoded: str) -> bytes:
    """解码游标载荷的 urlsafe base64，接受集合固定在 3.10–3.14 的交集。

    ``base64.b64decode(validate=True)`` 的填充校验随版本变化：3.10 接受多余尾部
    填充，3.11 又接受 ``AAAA====`` 这类 3.12+ 拒绝的写法，畸形游标因此在一个版本上
    推进分页、在另一个版本上被判无效。游标由本进程生成，规范形式是 urlsafe base64，
    可带规范填充或全部省略；这里先固定字符集与填充数量，再补齐缺失填充后解码规范
    形式，多余填充、夹带字符与非法长度在各版本上一致拒绝。
    """
    if not isinstance(encoded, str) or _CURSOR_B64.fullmatch(encoded) is None:
        raise ValueError("游标编码无效")
    data = encoded.rstrip("=")
    padding = len(encoded) - len(data)
    required = (-len(data)) % 4
    if len(data) % 4 == 1 or padding not in (0, required):
        raise ValueError("游标编码无效")
    return base64.b64decode((data + "=" * required).encode("ascii"), altchars=b"-_", validate=True)


def wire_text(value: str) -> str:
    """传输文本：把无法编码为 UTF-8 的孤立代理项替换为 U+FFFD。

    持久记录可能含孤立代理项（损坏记录、surrogateescape 路径或旧版本写入）。
    JSON-RPC 帧按 `ensure_ascii=False` 编码，孤立代理项会让整次响应变成
    `RESPONSE_INVALID`；这里只替换代理项，其余字符与长度不变，分页 offset 仍按原文计算。
    """
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    return "".join(_REPLACEMENT if 0xD800 <= ord(char) <= 0xDFFF else char for char in value)


_WIRE_MAX_DEPTH = 64
_WIRE_DEPTH_PLACEHOLDER = "[嵌套层级超出显示上限]"


def wire_value(value, _depth: int = 0):
    """递归清理投影中的字符串；正常数据原样返回，坏记录降级为可传输文本。

    持久记录可能被外部改写或由旧版本写入任意深度的结构；纯 Python 递归超过
    解释器上限会抛 ``RecursionError``，让 ``thread/read`` 等投影整体返回
    ``-32603``。超过上限的子树按占位文本投影，正常数据逐值不变。

    非有限浮点（``inf``/``nan``）同样无法被会话落库接受（``allow_nan=False``）；
    模型参数里的 ``1e999`` 解码后就是 ``inf``，这里一并降级为 ``None``，
    与孤立代理项的降级同一层。
    """
    if _depth > _WIRE_MAX_DEPTH:
        return _WIRE_DEPTH_PLACEHOLDER
    if isinstance(value, str):
        return wire_text(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, list):
        return [wire_value(item, _depth + 1) for item in value]
    if isinstance(value, dict):
        return {wire_text(key): wire_value(item, _depth + 1) for key, item in value.items()}
    return value


def _utf8_size(value: str) -> int:
    # 内联阈值按原文字节数判断；每个代理项替换为 U+FFFD 后仍占 3 字节，分页长度不变。
    return len(value.encode("utf-8", "surrogatepass"))


def item_content_reference(thread_id: str, item_id: str, part: str, text: str,
                           snapshot_id: str | None = None) -> dict:
    """摘要覆盖实际传输文本，客户端才能对分页拼接结果做一致性校验。

    ``read_item_content`` 返回 ``wire_text`` 后的文本；若摘要按仍含孤立代理项的原文
    计算，客户端按收到的字节重算会得到不同结果。代理项与 U+FFFD 同为 3 字节，
    因此 ``byteLength`` 与 ``characterLength`` 不受影响。
    """
    if not isinstance(part, str) or part not in {"text", "thinking"}:
        raise ValueError("内容字段必须是 text 或 thinking")
    if not isinstance(text, str):
        raise ValueError("会话内容必须是文本")
    digest = hashlib.sha256()
    byte_length = 0
    for offset in range(0, len(text), 16_384):
        encoded = wire_text(text[offset:offset + 16_384]).encode("utf-8")
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
        _stale(reference)
    offset = 0
    if cursor is not None:
        try:
            if not isinstance(cursor, str) or not cursor.startswith("ic1_") or len(cursor) > 2048:
                raise ValueError
            encoded = cursor[4:]
            value = json.loads(decode_cursor_base64(encoded))
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


def _stale(reference: dict) -> None:
    from boss_harness.rpc import RpcError

    raise RpcError(-32011, "会话内容已变化，请重新读取条目并确认新内容引用",
                   {"code": "STALE_CONTENT", "currentRef": reference})
