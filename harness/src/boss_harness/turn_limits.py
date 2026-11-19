"""Host-controlled model request limits, independent of provider retry policy."""
from __future__ import annotations

import os
import re


DEFAULT_MAX_MODEL_REQUESTS = 6
MAX_MODEL_REQUESTS = 64


def model_request_limit(value: object, *, ceiling: int = MAX_MODEL_REQUESTS) -> int:
    """Validate an exact integer; a per-turn request can only tighten the host cap."""
    if type(value) is not int or not 1 <= value <= ceiling:
        raise ValueError(f"maxModelRequests 必须是 1 到 {ceiling} 的整数")
    return value


def model_request_limit_from_environment() -> int:
    raw = os.environ.get("BOSS_HARNESS_MAX_MODEL_REQUESTS")
    # 空值或只有空白按未设置处理，与其余数值上限一致；首尾空白不影响合法数字的判定。
    value = "" if raw is None else raw.strip()
    if not value:
        return DEFAULT_MAX_MODEL_REQUESTS
    # Bound the textual input before converting it; do not include it in errors.
    if len(value) > 2 or re.fullmatch(r"[1-9][0-9]?", value) is None:
        raise ValueError("BOSS_HARNESS_MAX_MODEL_REQUESTS 必须是 1 到 64 的十进制整数")
    try:
        return model_request_limit(int(value))
    except ValueError:
        raise ValueError("BOSS_HARNESS_MAX_MODEL_REQUESTS 必须是 1 到 64 的十进制整数") from None
