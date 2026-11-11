"""Bounded transport projections and content-addressed reads of durable results.

Pi reference: 5ba1cbaf3d96d204d847c84ce235c62dae23e0fd, coding-agent rpc.md,
session-format.md, SessionManager and agent-loop toolResult messages. Adopt the
separation of canonical messages, model context and RPC presentation. Chunked
result references are this project's independent transport contract, not Pi RPC.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from boss_harness.item_content import project_item_content, wire_text, wire_value
from boss_harness.models.types import (
    DEFAULT_MODEL_TOOL_RESULT_BYTES, MAX_MODEL_TOOL_RESULT_BYTES, MIN_MODEL_TOOL_RESULT_BYTES,
)
from boss_harness.rpc import RpcError

MAX_INLINE_TOOL_RESULT_BYTES = 64 * 1024
MAX_PAGE_BYTES = 1024 * 1024
DEFAULT_RESULT_CHARS = 16_384
MAX_RESULT_CHARS = 32_768
MODEL_RESULT_READ_CHARS = 8_192


def result_text(result: Any) -> str:
    """Stable JSON spelling; character offsets are Unicode code points, not bytes."""
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def result_reference(thread_id: str, item_id: str, text: str) -> dict:
    # 持久记录可能含孤立代理项；surrogatepass 让摘要与读取路径对同一文本给出相同结果。
    encoded = text.encode("utf-8", "surrogatepass")
    return {"threadId": thread_id, "itemId": item_id, "encoding": "json",
            "sha256": hashlib.sha256(encoded).hexdigest(), "byteLength": len(encoded),
            "characterLength": len(text)}


def _json_size(value: Any, *, ensure_ascii: bool = False) -> int | None:
    """JSON 拼写的 UTF-8 字节数；无法编码的值返回 None，由调用方按超限处理。"""
    try:
        return len(json.dumps(value, ensure_ascii=ensure_ascii, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError):
        return None


def _fits(projected: dict[str, Any], max_bytes: int) -> bool:
    """正常路径按 ensure_ascii=False 输出，兜底路径按 True；两种拼写都必须落在预算内。"""
    plain = _json_size(projected)
    escaped = _json_size(projected, ensure_ascii=True)
    return plain is not None and escaped is not None and plain <= max_bytes and escaped <= max_bytes


def _command_text(value: Any) -> str:
    """命令来自模型输入或持久记录；非字符串按 JSON 拼写投影。"""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            text = ""
    return wire_text(text)


def _fit_projection(projected: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """固定字段同样受预算约束：超长 command 保留前缀并标注，可选 source 在必要时让位。"""
    if _fits(projected, max_bytes):
        return projected
    # 固定字段中只有 command 与 source 可能无界。保留 source 时连空命令都放不下，
    # 才丢弃仅用于溯源的 source；丢弃后完整命令已能放下时也不必误标截断。
    if not _fits({**projected, "command": ""}, max_bytes):
        without_source = {key: value for key, value in projected.items() if key != "source"}
        if _fits(without_source, max_bytes):
            return without_source
        projected = without_source
    projected = {**projected, "commandTruncated": True}
    # 留一半预算给结果预览；二分查找 JSON 转义后仍能放下的最长前缀。
    text = _command_text(projected.get("command"))
    low, high = 0, min(len(text), max_bytes // 2)
    while low < high:
        middle = (low + high + 1) // 2
        if _fits({**projected, "command": text[:middle]}, max_bytes):
            low = middle
        else:
            high = middle - 1
    projected["command"] = text[:low]
    return projected


def model_result_content(result: dict, item_id: str | None, *, source: dict | None,
                         max_bytes: int, preview: str) -> str:
    """Keep small results structured; replace oversized model payloads with a verifiable reference."""
    if (type(max_bytes) is not int
            or not MIN_MODEL_TOOL_RESULT_BYTES <= max_bytes <= MAX_MODEL_TOOL_RESULT_BYTES):
        max_bytes = DEFAULT_MODEL_TOOL_RESULT_BYTES
    payload = {**result, **({"source": source} if source is not None else {})}
    size = _json_size(payload)
    if size is not None and size <= max_bytes:
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)

    projected: dict[str, Any] = {
        "ok": result.get("ok"),
        "command": result.get("command"),
        "resultOmitted": True,
    }
    if source is not None:
        projected["source"] = source
    if item_id is not None:
        text = result_text(result)
        reference = result_reference("", item_id, text)
        projected["resultRef"] = {key: reference[key] for key in
                                  ("itemId", "sha256", "byteLength", "characterLength")}
    else:
        projected["resultUnavailable"] = True
    projected = _fit_projection(projected, max_bytes)

    preview = preview if isinstance(preview, str) else ""
    keep = min(len(preview), max_bytes // 2)
    while True:
        if keep:
            projected["resultPreview"] = preview[:keep]
        candidate = json.dumps(projected, ensure_ascii=False, allow_nan=False)
        try:
            if len(candidate.encode("utf-8")) <= max_bytes:
                return candidate
        except UnicodeEncodeError:
            pass
        projected.pop("resultPreview", None)
        if keep <= 1:
            return json.dumps(projected, ensure_ascii=True, allow_nan=False)
        keep //= 2


def model_result_for_item(item: dict) -> str:
    """Bound legacy history projections without changing their durable source records.

    持久记录可能含孤立代理项（损坏记录、``surrogateescape`` 路径或旧版本写入）。
    ``_json_size`` 对不可编码值返回 None，坏字符会让本可内联的小结果被误判为超限；
    兜底转义则把非法 ``\\uD800`` 送进模型请求。这里与 RPC 展示、导出和压缩材料
    统一按 ``wire_text`` 约定降级：长度不变，干净记录逐字节不变。
    """
    limit = item.get("modelResultLimitBytes", DEFAULT_MODEL_TOOL_RESULT_BYTES)
    if type(limit) is not int or not MIN_MODEL_TOOL_RESULT_BYTES <= limit <= MAX_MODEL_TOOL_RESULT_BYTES:
        limit = DEFAULT_MODEL_TOOL_RESULT_BYTES
    existing = item.get("modelResult")
    if isinstance(existing, str):
        existing = wire_text(existing)
        try:
            if len(existing.encode("utf-8")) <= limit:
                return existing
        except UnicodeEncodeError:
            pass
    summary = item.get("resultSummary")
    preview = wire_text(summary) if isinstance(summary, str) else summary
    result = item.get("result")
    if isinstance(result, dict) and isinstance(item.get("id"), str):
        source = item.get("source")
        return model_result_content(wire_value(result), item["id"],
                                    source=wire_value(source) if isinstance(source, dict) else source,
                                    max_bytes=limit, preview=preview)
    return model_result_content({}, None, source=None, max_bytes=limit,
                                preview=preview or existing or "")


def project_error(error: dict | None) -> dict | None:
    """An error preview must not reintroduce an omitted result's large body."""
    if error is None:
        return None
    if wire_size(error) <= 4096:
        return wire_value(error)
    preview = {key: str(error.get(key) or "")[:maximum]
               for key, maximum in (("code", 128), ("message", 2000), ("recovery_action", 1000))}
    return wire_value({**preview, "detailsOmitted": True})


def project_item(thread_id: str, item: dict, *, snapshot_id: str | None = None) -> dict:
    """Never mutate durable/model history while preparing renderer-facing items."""
    projected = {key: value for key, value in item.items()
                 if key not in {"modelResult", "modelResultLimitBytes", "resultOmitted", "resultRef",
                                "_anthropicContinuation"}}
    projected = project_item_content(thread_id, projected, snapshot_id=snapshot_id)
    result = item.get("result")
    if isinstance(result, dict):
        text = result_text(result)
        if len(text.encode("utf-8", "surrogatepass")) > MAX_INLINE_TOOL_RESULT_BYTES:
            projected.pop("result", None)
            projected.update(resultOmitted=True, resultRef=result_reference(thread_id, str(item["id"]), text))
            for key, maximum in (("errorCode", 128), ("recoveryAction", 1000), ("resultSummary", 4000)):
                if key in projected:
                    projected[key] = wire_text(str(projected[key])[:maximum]) if projected[key] is not None else None
    return wire_value(projected)


def wire_size(value: Any) -> int:
    """Match the transport JSON spelling, leaving room for response ID and framing."""
    try:
        return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) + 512
    except UnicodeEncodeError:
        # 含孤立代理项的值无法写成 JSON-RPC 帧：按超过任何预算处理，由调用方省略或分页。
        return MAX_PAGE_BYTES + 1


def _cursor(reference: dict, offset: int) -> str:
    data = [reference["threadId"], reference["itemId"], reference["sha256"], offset]
    return "tr1_" + base64.urlsafe_b64encode(result_text(data).encode("utf-8")).decode().rstrip("=")


def read_result_chunk(thread_id: str, item: dict, *, sha256: str, cursor: str | None = None,
                      limit: int = DEFAULT_RESULT_CHARS) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:
        raise ValueError(f"limit 必须是 1 到 {MAX_RESULT_CHARS} 的整数")
    if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):
        raise ValueError("该条目没有可读取的完整工具结果")
    if not isinstance(sha256, str) or re.fullmatch(r"[a-f0-9]{64}", sha256) is None:
        raise ValueError("sha256 必须是结果引用中的 64 位小写十六进制摘要")
    text = result_text(item["result"])
    reference = result_reference(thread_id, str(item["id"]), text)
    if sha256 != reference["sha256"]:
        raise RpcError(-32011, "工具结果已变化，请重新读取条目并确认新结果引用", {"code": "STALE_RESULT"})
    return read_result_text_chunk(thread_id, str(item["id"]), text, sha256=sha256,
                                  cursor=cursor, limit=limit)


def read_result_text_chunk(thread_id: str, item_id: str, text: str, *, sha256: str,
                           cursor: str | None = None, limit: int = DEFAULT_RESULT_CHARS) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:
        raise ValueError(f"limit 必须是 1 到 {MAX_RESULT_CHARS} 的整数")
    reference = result_reference(thread_id, item_id, text)
    if not isinstance(sha256, str) or sha256 != reference["sha256"]:
        raise RpcError(-32011, "工具结果已变化，请重新读取条目并确认新结果引用", {"code": "STALE_RESULT"})
    offset = 0
    if cursor is not None:
        try:
            if not isinstance(cursor, str) or not cursor.startswith("tr1_") or len(cursor) > 2048:
                raise ValueError()
            encoded = cursor[4:]
            value = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True))
            if (not isinstance(value, list) or len(value) != 4
                    or value[:3] != [thread_id, item_id, reference["sha256"]]
                    or type(value[3]) is not int or not 0 <= value[3] < len(text)):
                raise ValueError()
            offset = value[3]
        except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, RecursionError):
            raise ValueError("工具结果游标无效、归属不匹配或结果已变化") from None
    end = min(offset + limit, len(text))
    return {"text": wire_text(text[offset:end]), "offset": offset, "resultRef": reference,
            "nextCursor": _cursor(reference, end) if end < len(text) else None}
