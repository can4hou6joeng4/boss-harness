"""各 provider 共用的模型请求自动重试参数。

只负责「等多久、最多几次、网关建议等多久」；是否可重试由各 provider 按自己的错误形状判断，
重试只发生在向调用方产出首个内容事件之前，并受回合共享的模型恢复预算约束。
"""
from __future__ import annotations

import os
from collections.abc import Iterator, Mapping

from boss_harness.models.types import StreamEvent

#: 单次退避的上限（秒）。
MAX_RETRY_DELAY_SECONDS = 8.0
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BASE_MS = 500
_MIN_RETRY_ATTEMPTS = 1
_MAX_RETRY_ATTEMPTS = 10


def retry_settings_from_environment(
    environ: Mapping[str, str] | None = None,
) -> tuple[int, float, bool]:
    """返回 (重试次数, 基础退避秒, 显式值是否原样生效)。

    正常启动与自检共用这一解析：未设置或空值按默认且视为有效；不是整数时回退
    默认值，越界或负数收敛到边界。后两种情况第三项为 False，供启动自检提示，
    但启动行为与旧实现一致，不额外失败。
    """
    source = os.environ if environ is None else environ
    adjusted = False

    raw_attempts = source.get("BOSS_HARNESS_RETRY_ATTEMPTS")
    if raw_attempts is None or raw_attempts == "":
        attempts = DEFAULT_RETRY_ATTEMPTS
    else:
        try:
            attempts = int(raw_attempts)
        except ValueError:
            attempts = DEFAULT_RETRY_ATTEMPTS
            adjusted = True
        else:
            bounded = max(_MIN_RETRY_ATTEMPTS, min(attempts, _MAX_RETRY_ATTEMPTS))
            adjusted = adjusted or bounded != attempts
            attempts = bounded

    raw_base_ms = source.get("BOSS_HARNESS_RETRY_BASE_MS")
    if raw_base_ms is None or raw_base_ms == "":
        base_ms = DEFAULT_RETRY_BASE_MS
    else:
        try:
            base_ms = int(raw_base_ms)
        except ValueError:
            base_ms = DEFAULT_RETRY_BASE_MS
            adjusted = True
        else:
            bounded = max(0, base_ms)
            adjusted = adjusted or bounded != base_ms
            base_ms = bounded

    return attempts, base_ms / 1000.0, adjusted


def retry_settings() -> tuple[int, float]:
    """重试次数与基础退避；可用 BOSS_HARNESS_RETRY_ATTEMPTS / _BASE_MS 覆盖。"""
    attempts, base_delay, _ = retry_settings_from_environment()
    return attempts, base_delay


def retry_delay(base_delay: float, attempt: int, retry_after: float | None) -> float:
    """退避时长：网关给了 Retry-After 就听它的，否则指数退避，两者都设上限。"""
    if retry_after is not None:
        return max(0.0, min(retry_after, MAX_RETRY_DELAY_SECONDS))
    return min(base_delay * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)


def retry_after_seconds(exc: object) -> float | None:
    """读 SDK 状态错误上的 Retry-After / Retry-After-Ms 头；网关没给就返回 None 走指数退避。"""
    headers = getattr(exc, "response", None)
    headers = getattr(headers, "headers", None)
    if headers is None:
        return None
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        raw = headers.get(name)
        if not raw:
            continue
        try:
            return float(str(raw).strip()) * scale
        except ValueError:
            continue
    return None


def retry_start_event(next_attempt: int, attempts: int, delay: float, message: str) -> StreamEvent:
    """退避等待开始前发给调用方的观测事件；不携带任何内容，也不改变重试判定。"""
    return StreamEvent(type="retry_start", attempt=next_attempt, max_attempts=attempts,
                       delay_ms=max(0, int(round(delay * 1000))), error=message or "模型请求失败")


def retry_aborted_before_attempt_event(attempt: int) -> StreamEvent:
    """退避等待中被取消：本段重试以取消收尾，即将发起的那次尝试并未发出。"""
    return StreamEvent(type="retry_end", attempt=attempt, reason="aborted",
                       error=f"已在退避等待中停止，第 {attempt} 次尝试未发起")


def with_retry_outcome(events: Iterator[StreamEvent]) -> Iterator[StreamEvent]:
    """在一段已发过 retry_start 的流里补一条 retry_end。

    首个非错误事件即视为重试成功；错误事件（含取消）先补失败的 retry_end 再原样转出。
    provider 已自行产出 retry_end（如退避中取消）时不再重复补发。没有发生重试的流不会多出任何事件；
    调用方提前关闭流时这里无法再产出事件，由回合执行器负责收尾。
    """
    try:
        yield from _retry_outcome(events)
    finally:
        close = getattr(events, "close", None)
        if callable(close):
            close()


def _retry_outcome(events: Iterator[StreamEvent]) -> Iterator[StreamEvent]:
    pending = 0
    for event in events:
        if event.type == "retry_start":
            pending = event.attempt
        elif event.type == "retry_end":
            pending = 0
        elif pending:
            failed = event.type == "error"
            yield StreamEvent(type="retry_end", attempt=pending,
                              reason=(event.reason or "error") if failed else "success",
                              error=event.error if failed else "")
            pending = 0
        yield event
