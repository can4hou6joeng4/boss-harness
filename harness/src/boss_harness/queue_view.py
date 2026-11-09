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
# kind 决定投递语义（steering 只属于当前回合）。缺失或未知 kind 的记录无法 claim、
# 恢复或展示，下游直接读取 kind 时还会抛 KeyError。
QUEUE_KINDS = frozenset({"steering", "followUp"})
_PENDING_QUEUE_STATUSES = frozenset({"queued", "delivering"})
# 与 queue/add 的上限一致：投影只保留最多 10 项技能，避免损坏记录放大只读响应。
MAX_QUEUE_SKILL_IDS = 10
_QUEUE_OPTIONAL_STRINGS = ("expectedTurnId", "clientUserMessageId")
_QUEUE_FLAGS = ("inputPersisted", "deduplicated", "inputTruncated")
# 与 runtime.PAUSE_REASON_* 保持一致；只有这里列出的来源能进入只读投影。
_QUEUE_PAUSE_REASONS = frozenset({"COMPACTION_FAILED", "THREAD_ARCHIVED", "TURN_NOT_COMPLETED"})
_MAX_SAFE_INTEGER = 2 ** 53 - 1


def queue_record(value: Any) -> dict | None:
    """持久队列记录的结构契约；单条坏记录跳过，不打断整次读取或快照构建。

    ``kind`` 是投递语义的一部分：缺失或未知时记录无法 claim、暂停结算或恢复，
    ``TurnQueue.recover`` 等下游直接读取时会抛 ``KeyError``，让内核启动失败。
    记录会直接进入 JSON-RPC 响应帧。损坏或旧版本写入的孤立代理项无法编码为
    UTF-8，会让 ``queue/list`` 退化成 ``RESPONSE_INVALID``，也会让
    ``thread/resume`` 被误判为响应过大；这里按 ``wire_text`` 约定把代理项
    降级为 U+FFFD，仍然无法编码的记录（如 NaN 或过深嵌套）按坏记录跳过。
    """
    if not (isinstance(value, dict) and isinstance(value.get("id"), str) and value["id"]
            and isinstance(value.get("kind"), str) and value["kind"] in QUEUE_KINDS
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


def _queue_view_auto_compaction(value: Any) -> dict:
    """只保留协议声明且类型正确的字段；`{}` 本身合法，表示全部继承默认值。"""
    cleaned: dict = {}
    if not isinstance(value, dict):
        return cleaned
    if type(value.get("enabled")) is bool:
        cleaned["enabled"] = value["enabled"]
    for key in ("triggerPercent", "keepRecentTokens"):
        item = value.get(key)
        if type(item) is int and 0 <= item <= _MAX_SAFE_INTEGER:
            cleaned[key] = item
    return cleaned


def queue_view_record(record: dict) -> dict:
    """按只读展示契约收敛一条已通过 ``queue_record`` 的队列记录。

    ``queue_record`` 保留运行时的完整记录；但 ``queue/list``、``thread/resume``
    与冻结快照共用 ``project_queue``，桌面会逐项校验可选字段，任一形状不符就拒绝
    整份列表并清空面板。必填字段已在 ``queue_record`` 校验，这里只删除或收敛
    类型不符合协议的可选字段，不改变条目身份、状态与计数。
    """
    value = dict(record)
    for key in _QUEUE_OPTIONAL_STRINGS:
        if key in value and value[key] is not None and not isinstance(value[key], str):
            del value[key]
    if "turnId" in value and not isinstance(value["turnId"], str):
        del value["turnId"]
    if "skillIds" in value:
        ids = value["skillIds"]
        if (isinstance(ids, list) and len(ids) <= MAX_QUEUE_SKILL_IDS
                and all(isinstance(item, str) and item for item in ids)):
            value["skillIds"] = list(dict.fromkeys(ids))
        else:
            del value["skillIds"]
    if "autoCompaction" in value:
        raw = value["autoCompaction"]
        cleaned = _queue_view_auto_compaction(raw)
        if cleaned or (isinstance(raw, dict) and not raw):
            value["autoCompaction"] = cleaned
        else:
            del value["autoCompaction"]
    if "failureCode" in value and value["failureCode"] != "TURN_START_FAILED":
        del value["failureCode"]
    # 暂停来源是内核拥有的有限枚举：只有暂停项能携带，未知来源按缺失处理，
    # 避免损坏记录把任意字符串带进界面并影响重试入口。
    paused_reason = value.get("pausedReason")
    if (value.get("status") != "paused" or not isinstance(paused_reason, str)
            or paused_reason not in _QUEUE_PAUSE_REASONS):
        value.pop("pausedReason", None)
    if "executionStarted" in value and value["executionStarted"] is not False:
        del value["executionStarted"]
    for key in _QUEUE_FLAGS:
        if key in value and type(value[key]) is not bool:
            del value[key]
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
        value = queue_view_record(item)
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
