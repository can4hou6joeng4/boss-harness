"""有界队列读取投影。

持久队列保留每一条消息（包含已投递与已撤回项），长会话会无限累积。会话读取与
queue/list 因此只返回有界投影：全部待处理项、有限的已终结窗口，以及截断的正文
预览。需要完整正文的显式动作（例如重新排队）仍通过 queue/get 读取单项。
"""
from __future__ import annotations

import json
from typing import Any

from boss_harness.item_content import wire_value

MAX_QUEUE_VIEW_ITEMS = 200
MAX_QUEUE_VIEW_TERMINAL_ITEMS = 50
MAX_QUEUE_VIEW_INPUT_CHARS = 600
ACTIVE_QUEUE_STATUSES = frozenset({"queued", "delivering", "paused"})
TERMINAL_QUEUE_STATUSES = frozenset({"delivered", "cancelled"})
# 持久记录不可信：缺失或未知状态不进入投影，否则渲染层会整份拒绝，隐藏真实队列。
QUEUE_STATUSES = ACTIVE_QUEUE_STATUSES | TERMINAL_QUEUE_STATUSES
_PENDING_QUEUE_STATUSES = frozenset({"queued", "delivering"})


def queue_record(value: Any) -> dict | None:
    """持久队列记录的结构契约；单条坏记录跳过，不打断整次读取或快照构建。

    记录会直接进入 JSON-RPC 响应帧。损坏或旧版本写入的孤立代理项无法编码为
    UTF-8，会让 ``queue/list`` 退化成 ``RESPONSE_INVALID``，也会让
    ``thread/resume`` 被误判为响应过大；这里按 ``wire_text`` 约定把代理项
    降级为 U+FFFD，仍然无法编码的记录（如 NaN 或过深嵌套）按坏记录跳过。
    """
    if not (isinstance(value, dict) and isinstance(value.get("id"), str) and value["id"]
            and isinstance(value.get("status"), str) and value["status"] in QUEUE_STATUSES
            and isinstance(value.get("input"), str)):
        return None
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except UnicodeEncodeError:
        try:
            value = wire_value(value)
            json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError):
            return None
    except (TypeError, ValueError, RecursionError):
        return None
    return value


def project_queue(items: list[dict], *, total_items: int | None = None,
                  active_items: int | None = None) -> dict:
    """Return the bounded list projection plus the durable totals.

    ``active_items`` lets callers that already counted the full queue (such as the
    snapshot database) report the exact pending total even when only a bounded
    subset of items is passed in.
    """
    ordered = [item for item in (queue_record(value) for value in items)
               if item is not None]
    pending = [item for item in ordered if item.get("status") in _PENDING_QUEUE_STATUSES]
    paused = [item for item in ordered if item.get("status") == "paused"]
    terminal = [item for item in ordered if item.get("status") in TERMINAL_QUEUE_STATUSES]

    # 未投递的排队项优先保留；超限时保留最新的，暂停项随后占用剩余名额。
    kept_pending = pending[-MAX_QUEUE_VIEW_ITEMS:]
    paused_room = max(0, MAX_QUEUE_VIEW_ITEMS - len(kept_pending))
    kept_paused = paused[-paused_room:] if paused_room else []
    terminal_room = max(0, min(MAX_QUEUE_VIEW_TERMINAL_ITEMS,
                               MAX_QUEUE_VIEW_ITEMS - len(kept_pending) - len(kept_paused)))
    kept_terminal = terminal[-terminal_room:] if terminal_room else []

    kept_ids = {item["id"] for item in (*kept_pending, *kept_paused, *kept_terminal)}
    visible = []
    for item in ordered:
        if item["id"] not in kept_ids:
            continue
        value = dict(item)
        text = value.get("input")
        if isinstance(text, str) and len(text) > MAX_QUEUE_VIEW_INPUT_CHARS:
            value["input"] = text[:MAX_QUEUE_VIEW_INPUT_CHARS]
            value["inputTruncated"] = True
        visible.append(value)
    total = len(ordered) if total_items is None else total_items
    # 待处理数量按全部持久项统计，不受有界投影影响；旧调用方不传时按已载入项计算。
    active = len(pending) + len(paused) if active_items is None else active_items
    active = max(0, min(active, total))
    return {"items": visible, "totalItems": total, "activeItems": active,
            "truncated": len(visible) < total}
