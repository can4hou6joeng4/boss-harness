#!/usr/bin/env python3
"""核对模型类型契约：计数规整、用量求和、消息投影、诊断裁剪与恢复预算并发。

`models/types.py` 是模型层与执行循环共用的类型契约：`token_count` 决定哪些
provider 计数算“已上报”，`Usage.total` 决定回合用量，`AssistantMessage` 投影
文本与工具调用，`ModelErrorInfo.event_payload` 裁剪公开诊断，`ModelRecoveryBudget`
在多个请求之间共享有限的重试额度。这里直接构造对象与多线程场景，固定这些语义；
静态部分锁定计数规则、预算锁与预留 / 提交 / 释放的拒绝分支。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/types.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    ModelErrorInfo,
    ModelRecoveryBudget,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
    Usage,
    token_count,
)

TOKEN_COUNT = (
    "    if value is None or isinstance(value, bool):",
    "        return None",
    "    if isinstance(value, int):",
    "        return value",
    "    if isinstance(value, float):",
    "        return int(value) if value.is_integer() else None",
    "        text = value.strip()",
    '        digits = text[1:] if text.startswith("-") else text',
    "        if digits.isascii() and digits.isdigit():",
    "            return int(text)",
)
USAGE_TOTAL = (
    "    def total(self) -> int:",
    "        return self.input + self.output",
)
MESSAGE_PROJECTION = (
    "    def text(self) -> str:",
    '        return "".join(block.text for block in self.blocks if isinstance(block, TextBlock))',
    "    def tool_calls(self) -> tuple[ToolCallBlock, ...]:",
    "        return tuple(block for block in self.blocks if isinstance(block, ToolCallBlock))",
)
EVENT_PAYLOAD = (
    '        payload: dict[str, Any] = {"provider": self.provider, "source": self.source}',
    "        if self.code is not None:",
    '            payload["code"] = self.code',
    "        if self.provider_code is not None:",
    '            payload["providerCode"] = self.provider_code',
    "        if self.status_code is not None:",
    '            payload["statusCode"] = self.status_code',
    "        if self.retryable is not None:",
    '            payload["retryable"] = self.retryable',
    "        if self.transport_cause is not None:",
    '            payload["transportCause"] = self.transport_cause',
    "        if self.transport_code is not None:",
    '            payload["transportCode"] = self.transport_code',
    "        return payload",
)
BUDGET_INIT = (
    "    def __init__(self, retries: int = DEFAULT_MODEL_RECOVERY_RETRIES) -> None:",
    "        if type(retries) is not int or not 0 <= retries <= 64:",
    '            raise ValueError("模型恢复次数必须是 0 到 64 的整数")',
    "        self._remaining = retries",
    "        self._reserved = 0",
    "        self._lock = threading.Lock()",
)
BUDGET_REMAINING = (
    "    def remaining(self) -> int:",
    "            return self._remaining",
)
BUDGET_RESERVE = (
    "        if cancel_event is not None and cancel_event.is_set():",
    "            if ((cancel_event is not None and cancel_event.is_set()) or self._remaining <= 0):",
    "            self._remaining -= 1",
    "            self._reserved += 1",
    "            return _RecoveryReservation(self)",
)
CONSUME = (
    "        reservation = self.reserve_retry(cancel_event)",
    "        return reservation.commit() if reservation is not None else False",
)
RESERVATION_COMMIT = (
    "if not self._active:",
    "return False",
    "self._active = False",
    "self._budget._reserved -= 1",
    "return True",
)
RESERVATION_RELEASE = (
    "if not self._active:",
    "return False",
    "self._active = False",
    "self._budget._reserved -= 1",
    "self._budget._remaining += 1",
    "return True",
)
STREAM_EVENT_DEFAULTS = (
    "    error_info: ModelErrorInfo | None = None",
    "    attempt: int = 0",
    "    max_attempts: int = 0",
    "    delay_ms: int = 0",
)
PROBES = (
    ("token_count", TOKEN_COUNT),
    ("usage_total", USAGE_TOTAL),
    ("message_projection", MESSAGE_PROJECTION),
    ("event_payload", EVENT_PAYLOAD),
    ("budget_init", BUDGET_INIT),
    ("budget_remaining", BUDGET_REMAINING),
    ("budget_reserve", BUDGET_RESERVE),
    ("consume", CONSUME),
    ("stream_event_defaults", STREAM_EVENT_DEFAULTS),
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _expect(fragment: str, source: str, label: str) -> int:
    count = source.splitlines().count(fragment)
    if count != 1:
        raise ValueError(f"模型类型契约变化 {label}：片段出现 {count} 次：{fragment}")
    return 1


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型类型行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_value_error(call, label: str) -> int:
    try:
        call()
    except ValueError:
        return 1
    raise ValueError(f"模型类型行为变化 {label}：未抛出 ValueError")


def _expect_frozen(call, label: str) -> int:
    try:
        call()
    except FrozenInstanceError:
        return 1
    raise ValueError(f"模型类型行为变化 {label}：未抛出 FrozenInstanceError")


def _method_segment(source: str, name: str) -> str:
    start = source.find(f"    def {name}(")
    if start < 0:
        raise ValueError(f"types.py 缺少方法 {name}")
    end = source.find("\n    def ", start + 1)
    return source[start:] if end < 0 else source[start:end]


def _check_structures() -> int:
    source = _read(MODULE)
    checked = 0
    for name, fragments in PROBES:
        for fragment in fragments:
            checked += _expect(fragment, source, name)
    for method, fragments in (("commit", RESERVATION_COMMIT), ("release", RESERVATION_RELEASE)):
        segment = _method_segment(source, method)
        position = -1
        for fragment in fragments:
            index = segment.find(fragment, position + 1)
            if index < 0:
                raise ValueError(f"_RecoveryReservation.{method} 的顺序缺少：{fragment}")
            position = index
            checked += 1
    for fragment in ("DEFAULT_MODEL_RECOVERY_RETRIES = 8",
                     '            raise ValueError("模型恢复次数必须是 0 到 64 的整数")'):
        checked += _expect(fragment, source, "budget_boundary")
    return checked


def _token_checks() -> int:
    checked = 0
    checked += _expect_value(token_count(None), None, "缺失计数")
    checked += _expect_value((token_count(True), token_count(False)), (None, None), "布尔不是计数")
    checked += _expect_value((token_count(0), token_count(-3), token_count(10**9)),
                             (0, -3, 10**9), "整数原样")
    checked += _expect_value((token_count(2.0), token_count(2.5)), (2, None), "浮点计数")
    checked += _expect_value((token_count(float("nan")), token_count(float("inf"))),
                             (None, None), "非有限浮点")
    checked += _expect_value((token_count(" 12 "), token_count("-7"), token_count("007")),
                             (12, -7, 7), "字符串计数")
    checked += _expect_value((token_count(""), token_count("-"), token_count("+5"),
                              token_count("1.5"), token_count("abc")),
                             (None, None, None, None, None), "非法字符串")
    checked += _expect_value((token_count("١٢"), token_count("１２")), (None, None),
                             "非 ASCII 数字")
    return checked


def _usage_checks() -> int:
    checked = 0
    checked += _expect_value(Usage().total, 0, "空用量")
    usage = Usage(input=3, output=4, cache_read=100, cache_write=50, reasoning=9)
    checked += _expect_value(usage.total, 7, "用量只计输入与输出")
    checked += _expect_frozen(lambda: setattr(usage, "input", 1), "用量不可变")
    return checked


def _message_checks() -> int:
    checked = 0
    message = AssistantMessage(blocks=(TextBlock("a"), ThinkingBlock("想", "s"),
                                      ToolCallBlock("c1", "boss_search", {"keyword": "x"}),
                                      TextBlock("b")))
    checked += _expect_value(message.text(), "ab", "消息文本投影")
    calls = message.tool_calls()
    checked += _expect_value([(call.id, call.name, dict(call.arguments)) for call in calls],
                             [("c1", "boss_search", {"keyword": "x"})], "工具调用投影")
    empty = AssistantMessage()
    checked += _expect_value((empty.text(), empty.tool_calls()), ("", ()), "空消息投影")
    checked += _expect_frozen(lambda: setattr(message, "stop_reason", "error"), "消息不可变")
    return checked


def _payload_checks() -> int:
    checked = 0
    full = ModelErrorInfo(provider="anthropic", source="http_error", code="CONTEXT_OVERFLOW",
                          provider_code="overloaded_error", status_code=529, retryable=False,
                          transport_cause="read_timeout", transport_code="ETIMEDOUT")
    checked += _expect_value(full.event_payload(), {
        "provider": "anthropic", "source": "http_error", "code": "CONTEXT_OVERFLOW",
        "providerCode": "overloaded_error", "statusCode": 529, "retryable": False,
        "transportCause": "read_timeout", "transportCode": "ETIMEDOUT",
    }, "完整诊断裁剪")
    minimal = ModelErrorInfo(provider="openai", source="stream_error")
    checked += _expect_value(minimal.event_payload(),
                             {"provider": "openai", "source": "stream_error"}, "未知事实省略")
    edge = ModelErrorInfo(provider="openai", source="stream_error", provider_code="",
                          status_code=0, retryable=True)
    checked += _expect_value(edge.event_payload(),
                             {"provider": "openai", "source": "stream_error",
                              "providerCode": "", "statusCode": 0, "retryable": True},
                             "零值与假值保留")
    return checked


def _budget_checks() -> int:
    checked = 0
    budget = ModelRecoveryBudget()
    checked += _expect_value(budget.remaining, 8, "默认恢复额度")
    for retries in (0, 64):
        checked += _expect_value(ModelRecoveryBudget(retries).remaining, retries, "额度边界")
    for invalid in (-1, 65, True, False, 1.0, "3", None):
        checked += _expect_value_error(lambda value=invalid: ModelRecoveryBudget(value),
                                       f"非法额度 {invalid!r}")

    budget = ModelRecoveryBudget(2)
    first = budget.reserve_retry()
    second = budget.reserve_retry()
    checked += _expect_value((first is not None, second is not None, budget.remaining),
                             (True, True, 0), "预留扣减额度")
    checked += _expect_value(first.commit(), True, "提交预留")
    checked += _expect_value((budget.remaining, first.commit()), (0, False), "重复提交不归还")
    checked += _expect_value((first.release(), second.release()), (False, True), "释放预留")
    checked += _expect_value(budget.remaining, 1, "释放归还额度")
    checked += _expect_value(second.release(), False, "重复释放不归还")

    budget = ModelRecoveryBudget(1)
    checked += _expect_value(budget.consume_retry(), True, "消费一次恢复")
    checked += _expect_value((budget.remaining, budget.consume_retry()), (0, False), "额度耗尽")
    checked += _expect_value(budget.reserve_retry(), None, "耗尽不预留")

    cancel = threading.Event()
    budget = ModelRecoveryBudget(1)
    cancel.set()
    checked += _expect_value((budget.reserve_retry(cancel), budget.remaining), (None, 1),
                             "已取消不预留")
    cancel.clear()
    reservation = budget.reserve_retry(cancel)
    cancel.set()
    checked += _expect_value(reservation.release(), True, "取消后退避释放")
    checked += _expect_value(budget.remaining, 1, "取消释放归还额度")

    budget = ModelRecoveryBudget(8)
    reservations: list[object] = []
    lock = threading.Lock()
    barrier = threading.Barrier(8)

    def reserve() -> None:
        barrier.wait()
        reservation = budget.reserve_retry()
        with lock:
            reservations.append(reservation)

    threads = [threading.Thread(target=reserve) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    checked += _expect_value((sum(item is not None for item in reservations), budget.remaining),
                             (8, 0), "并发预留不超发")
    for reservation in reservations:
        reservation.commit()
    checked += _expect_value(budget.remaining, 0, "并发提交后额度不变")

    budget = ModelRecoveryBudget(8)
    outcomes: list[bool] = []
    barrier = threading.Barrier(16)

    def consume() -> None:
        barrier.wait()
        value = budget.consume_retry()
        with lock:
            outcomes.append(value)

    threads = [threading.Thread(target=consume) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    checked += _expect_value((sum(outcomes), budget.remaining), (8, 0), "并发消费恰好用满")
    return checked


def _stream_event_checks() -> int:
    checked = 0
    event = StreamEvent(type="start")
    checked += _expect_value((event.content_index, event.delta, event.text, event.tool_call,
                              event.reason, event.message, event.error, event.error_info,
                              event.attempt, event.max_attempts, event.delay_ms),
                             (0, "", "", None, "", None, "", None, 0, 0, 0), "流事件默认值")
    retry = StreamEvent(type="retry_start", attempt=2, max_attempts=3, delay_ms=1500,
                        error="失败")
    checked += _expect_value((retry.attempt, retry.max_attempts, retry.delay_ms, retry.error),
                             (2, 3, 1500, "失败"), "重试事件字段")
    checked += _expect_frozen(lambda: setattr(event, "type", "done"), "流事件不可变")
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _token_checks()
    checked += _usage_checks()
    checked += _message_checks()
    checked += _payload_checks()
    checked += _budget_checks()
    checked += _stream_event_checks()
    return checked


def check_model_types() -> tuple[int, int]:
    return _check_structures(), _behavior_checks()


def main() -> int:
    try:
        structures, behaviors = check_model_types()
    except ValueError as error:
        print(f"模型类型契约核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型类型契约一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
