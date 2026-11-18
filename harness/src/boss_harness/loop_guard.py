"""单次模型回合的重复工具调用提醒。

只观察当前回合里连续的同名同参调用，达到阈值时生成一条合成用户提醒；
不阻断执行、不保存状态，也不接触工具参数以外的业务数据。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

#: 提醒阈值：第 3 次提示一次，之后每累计 2 次再提示一次。
LOOP_REMINDER_THRESHOLDS = (3, 5)
#: 单次提醒的最大字符数；实际文本固定远低于此上限。
MAX_REMINDER_CHARS = 512
#: 超过此长度的规范参数不参与哈希，避免巨大 arguments 拖慢回路。
MAX_ARGUMENT_BYTES = 64 * 1024


def _argument_digest(tool_name: str, arguments: Mapping[str, Any]) -> str | None:
    """给工具名与规范化参数取摘要；不可安全序列化时放弃本次观察。"""
    try:
        canonical = json.dumps(
            arguments, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        return None
    if len(canonical.encode("utf-8")) > MAX_ARGUMENT_BYTES:
        return None
    payload = json.dumps(
        {"tool": tool_name, "arguments": canonical}, sort_keys=True,
        ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LoopGuard:
    """按回合隔离的内存观察器；不同调用链互不影响。"""

    def __init__(self) -> None:
        self._key: str | None = None
        self._count = 0

    def observe(self, tool_name: str, arguments: Mapping[str, Any]) -> str | None:
        """记录一次已执行的调用；命中阈值时返回一条合成用户提醒。"""
        digest = _argument_digest(tool_name, arguments)
        if digest is None:
            self.reset()
            return None
        if self._key != digest:
            self._key, self._count = digest, 0
        self._count += 1
        if self._count not in LOOP_REMINDER_THRESHOLDS:
            return None
        # 提醒不含参数、结果、路径或候选人信息；仅为执行循环层面的提示。
        label = tool_name[:64]
        text = (
            "内循环提醒（不是新的用户指令）：工具 "
            f"{label} 已连续以相同参数执行 {self._count} 次。"
            "请先核对已有结果，再决定是否继续相同操作。"
        )
        return text[:MAX_REMINDER_CHARS]

    def reset(self) -> None:
        """新用户指令或无法安全观察时清空连续计数。"""
        self._key, self._count = None, 0
