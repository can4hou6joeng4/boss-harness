#!/usr/bin/env python3
"""核对模型重试的退避上限、环境解析与观测事件边界。

retry.py 只决定「等多久、最多几次」：环境变量去空白后按整数解析并在 1–10 与
非负基数内收敛；网关 Retry-After 优先于指数退避，两者都封顶 8 秒，非有限值与
负数视为无效并回退指数退避；观测事件只带次数、毫秒与错误说明，retry_end 在首个
非错误事件补成功、在错误事件补失败。
任一放宽都会让等待无界或让观测事件与真实尝试次数不符，因此静态固定，并用
行为对照核对解析、退避与事件补发。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/retry.py"
USER_GUIDE = "docs/USER_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.retry import (  # noqa: E402
    retry_aborted_before_attempt_event,
    retry_after_seconds,
    retry_delay,
    retry_settings_from_environment,
    retry_start_event,
    with_retry_outcome,
)
from boss_harness.models.types import StreamEvent  # noqa: E402

CONSTANT_FRAGMENTS = (
    "MAX_RETRY_DELAY_SECONDS = 8.0\n",
    "DEFAULT_RETRY_ATTEMPTS = 3\n",
    "DEFAULT_RETRY_BASE_MS = 500\n",
    "_MIN_RETRY_ATTEMPTS = 1\n",
    "_MAX_RETRY_ATTEMPTS = 10\n",
)
ENV_FRAGMENTS = (
    "def retry_settings_from_environment(",
    "source = os.environ if environ is None else environ",
    "adjusted = False",
    'raw_attempts = source.get("BOSS_HARNESS_RETRY_ATTEMPTS")',
    "if raw_attempts is None or not raw_attempts.strip():",
    "attempts = DEFAULT_RETRY_ATTEMPTS",
    "attempts = int(raw_attempts)",
    "except ValueError:",
    "adjusted = True",
    "bounded = max(_MIN_RETRY_ATTEMPTS, min(attempts, _MAX_RETRY_ATTEMPTS))",
    "adjusted = adjusted or bounded != attempts",
    'raw_base_ms = source.get("BOSS_HARNESS_RETRY_BASE_MS")',
    "bounded = max(0, base_ms)",
    "return attempts, base_ms / 1000.0, adjusted",
    "def retry_settings() -> tuple[int, float]:",
    "attempts, base_delay, _ = retry_settings_from_environment()",
    "return attempts, base_delay",
)
DELAY_FRAGMENTS = (
    "def retry_delay(base_delay: float, attempt: int, retry_after: float | None) -> float:",
    "if retry_after is not None:",
    "return max(0.0, min(retry_after, MAX_RETRY_DELAY_SECONDS))",
    "return min(base_delay * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)",
)
HEADER_FRAGMENTS = (
    "def retry_after_seconds(exc: object) -> float | None:",
    'headers = getattr(exc, "response", None)',
    'headers = getattr(headers, "headers", None)',
    "if headers is None:",
    'for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):',
    "raw = headers.get(name)",
    "if not raw:",
    "continue",
    "seconds = float(str(raw).strip()) * scale",
    "if not math.isfinite(seconds) or seconds < 0:",
    "return seconds",
    "except ValueError:",
    "return None",
)
EVENT_FRAGMENTS = (
    "def retry_start_event(next_attempt: int, attempts: int, delay: float, message: str) -> StreamEvent:",
    'return StreamEvent(type="retry_start", attempt=next_attempt, max_attempts=attempts,',
    'delay_ms=max(0, int(round(delay * 1000))), error=message or "模型请求失败")',
    "def retry_aborted_before_attempt_event(attempt: int) -> StreamEvent:",
    'return StreamEvent(type="retry_end", attempt=attempt, reason="aborted",',
    'error=f"已在退避等待中停止，第 {attempt} 次尝试未发起")',
    "def with_retry_outcome(events: Iterator[StreamEvent]) -> Iterator[StreamEvent]:",
    "yield from _retry_outcome(events)",
    'close = getattr(events, "close", None)',
    "if callable(close):",
    "close()",
    "def _retry_outcome(events: Iterator[StreamEvent]) -> Iterator[StreamEvent]:",
    "pending = 0",
    'if event.type == "retry_start":',
    "pending = event.attempt",
    'elif event.type == "retry_end":',
    "pending = 0",
    "elif pending:",
    'failed = event.type == "error"',
    'yield StreamEvent(type="retry_end", attempt=pending,',
    'reason=(event.reason or "error") if failed else "success",',
    'error=event.error if failed else "")',
    "yield event",
)
DOC_FRAGMENTS = (
    (USER_GUIDE, "最多尝试次数，含首次；设为 `1` 即不自动重试"),
    (USER_GUIDE, "未设置、为空或只有空白时使用默认值；不是整数时使用默认值；超出范围时收敛到 1 或 10"),
    (USER_GUIDE, "自动重试的退避基数（毫秒），每次重试翻倍"),
    (USER_GUIDE, "负数按 0 处理"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型重试行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _summary(events) -> list[tuple[str, int, str, str]]:
    return [(event.type, event.attempt, event.reason, event.error) for event in events]


class _Response:
    def __init__(self, headers) -> None:
        self.headers = headers


class _Error:
    def __init__(self, headers=None) -> None:
        if headers is not None:
            self.response = _Response(headers)


class _Source:
    def __init__(self, events) -> None:
        self._events = list(events)
        self.closed = False

    def __iter__(self):
        return iter(self._events)

    def close(self) -> None:
        self.closed = True


def _behavior_checks() -> int:
    checked = 0
    # 环境解析：未设置与空白取默认，边界原样，越界与非整数收敛并标记。
    checked += _expect_value(retry_settings_from_environment({}), (3, 0.5, False), "未设置")
    checked += _expect_value(
        retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": "  "}),
        (3, 0.5, False), "空白次数")
    checked += _expect_value(
        retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": "5"}), (5, 0.5, False),
        "有效次数")
    checked += _expect_value(
        retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": "1"}), (1, 0.5, False),
        "次数下限")
    checked += _expect_value(
        retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": "10"}), (10, 0.5, False),
        "次数上限")
    for raw, expected in (("0", (1, 0.5, True)), ("99", (10, 0.5, True)),
                          ("abc", (3, 0.5, True)), ("3.5", (3, 0.5, True))):
        checked += _expect_value(
            retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": raw}), expected,
            f"次数收敛 {raw}")
    for raw, expected in (("250", (3, 0.25, False)), ("0", (3, 0.0, False)),
                          ("-100", (3, 0.0, True)), ("abc", (3, 0.5, True))):
        checked += _expect_value(
            retry_settings_from_environment({"BOSS_HARNESS_RETRY_BASE_MS": raw}), expected,
            f"基数解析 {raw}")
    checked += _expect_value(
        retry_settings_from_environment({"BOSS_HARNESS_RETRY_ATTEMPTS": "5",
                                         "BOSS_HARNESS_RETRY_BASE_MS": "-1"}),
        (5, 0.0, True), "两项独立")

    # 退避：指数增长与 8 秒封顶，网关建议优先且夹到 [0, 8]。
    checked += _expect_value(retry_delay(0.5, 1, None), 0.5, "首次退避")
    checked += _expect_value(retry_delay(0.5, 3, None), 2.0, "指数退避")
    checked += _expect_value(retry_delay(0.5, 10, None), 8.0, "指数封顶")
    checked += _expect_value(retry_delay(0.5, 1, 2.0), 2.0, "网关优先")
    checked += _expect_value(retry_delay(0.5, 1, 1000.0), 8.0, "网关封顶")
    checked += _expect_value(retry_delay(0.5, 1, -5.0), 0.0, "网关负数")
    checked += _expect_value(retry_delay(0.0, 5, None), 0.0, "零基数")

    # 网关头：毫秒优先于秒，空值与非法值跳过，缺失返回 None。
    checked += _expect_value(retry_after_seconds(object()), None, "无响应对象")
    checked += _expect_value(retry_after_seconds(_Error()), None, "无响应字段")
    checked += _expect_value(retry_after_seconds(_Error({})), None, "无响应头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after-ms": "1500"})), 1.5,
                             "毫秒头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": "2"})), 2.0, "秒头")
    checked += _expect_value(
        retry_after_seconds(_Error({"retry-after-ms": "500", "retry-after": "2"})), 0.5,
        "毫秒优先")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": ""})), None, "空头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": "abc"})), None, "非法头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": " 2 "})), 2.0, "头去空白")
    # 非有限值与负数无效：不得变成 0 毫秒立即重试或 8 秒封顶，统一回退指数退避。
    for raw in ("NaN", "nan", "inf", "-inf", "-5", "1e309", " Infinity "):
        checked += _expect_value(retry_after_seconds(_Error({"retry-after": raw})), None,
                                 f"无效秒头 {raw}")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after-ms": "NaN"})), None,
                             "无效毫秒头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": "0"})), 0.0, "零秒头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": "2.5"})), 2.5,
                             "小数秒头")
    checked += _expect_value(retry_after_seconds(_Error({"retry-after": "1e300"})), 1e300,
                             "有限大值")

    # 观测事件：次数、毫秒取整与错误说明，取消事件说明未发起的尝试。
    start = retry_start_event(2, 3, 0.75, "")
    checked += _expect_value((start.type, start.attempt, start.max_attempts, start.delay_ms,
                              start.error), ("retry_start", 2, 3, 750, "模型请求失败"),
                             "开始事件")
    checked += _expect_value(retry_start_event(1, 3, -1.0, "boom").delay_ms, 0, "负延迟归零")
    checked += _expect_value(retry_start_event(1, 3, 0.001, "boom").error, "boom", "错误说明")
    aborted = retry_aborted_before_attempt_event(2)
    checked += _expect_value((aborted.type, aborted.attempt, aborted.reason,
                              "第 2 次" in aborted.error), ("retry_end", 2, "aborted", True),
                             "取消事件")

    # 补发：成功补 success，错误补失败原因并透传，已有 retry_end 不重复补发。
    success = [retry_start_event(1, 3, 0.5, "boom"), StreamEvent(type="text", text="hi")]
    checked += _expect_value(
        _summary(with_retry_outcome(iter(success))),
        [("retry_start", 1, "", "boom"), ("retry_end", 1, "success", ""),
         ("text", 0, "", "")], "成功补发")
    failure = [retry_start_event(2, 3, 0.5, "boom"),
               StreamEvent(type="error", reason="rate_limit", error="限流")]
    checked += _expect_value(
        _summary(with_retry_outcome(iter(failure))),
        [("retry_start", 2, "", "boom"), ("retry_end", 2, "rate_limit", "限流"),
         ("error", 0, "rate_limit", "限流")], "失败补发")
    cancelling = [retry_start_event(1, 3, 0.5, "boom"), StreamEvent(type="error", error="取消")]
    checked += _expect_value(_summary(with_retry_outcome(iter(cancelling)))[1][2:],
                             ("error", "取消"), "失败原因兜底")
    existing = [retry_start_event(1, 3, 0.5, "boom"), retry_aborted_before_attempt_event(1)]
    checked += _expect_value(
        _summary(with_retry_outcome(iter(existing))),
        [("retry_start", 1, "", "boom"),
         ("retry_end", 1, "aborted", "已在退避等待中停止，第 1 次尝试未发起")],
        "不重复补发")
    checked += _expect_value(
        _summary(with_retry_outcome(iter([StreamEvent(type="text", text="hi")]))),
        [("text", 0, "", "")], "无重试流")
    chained = [retry_start_event(1, 3, 0.5, "a"), retry_start_event(2, 3, 0.5, "b"),
               StreamEvent(type="text", text="hi")]
    checked += _expect_value(_summary(with_retry_outcome(iter(chained)))[1][1], 2,
                             "连续开始取后者")

    # 来源关闭：正常耗尽与提前关闭都传播到底层迭代器。
    source = _Source([StreamEvent(type="text", text="hi")])
    list(with_retry_outcome(source))
    checked += _expect_value(source.closed, True, "完成后关闭")
    source = _Source([StreamEvent(type="text", text="hi")])
    iterator = with_retry_outcome(source)
    next(iterator)
    iterator.close()
    checked += _expect_value(source.closed, True, "提前关闭传播")
    return checked


def check_retry() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(ENV_FRAGMENTS, module, MODULE)
    checked += _expect(DELAY_FRAGMENTS, module, MODULE)
    checked += _expect(HEADER_FRAGMENTS, module, MODULE)
    checked += _expect(EVENT_FRAGMENTS, module, MODULE)
    # 环境解析：空白默认 → 整数 → 范围收敛 → 基数 → 返回生效值。
    checked += _ordered(
        (
            "if raw_attempts is None or not raw_attempts.strip():",
            "attempts = int(raw_attempts)",
            "bounded = max(_MIN_RETRY_ATTEMPTS, min(attempts, _MAX_RETRY_ATTEMPTS))",
            "bounded = max(0, base_ms)",
            "return attempts, base_ms / 1000.0, adjusted",
        ),
        module,
        MODULE,
    )
    # 次数与基数两处解析失败都必须标记 adjusted，供启动自检提示。
    if module.count("adjusted = True") != 2:
        raise ValueError(f"{MODULE} 的次数与基数解析失败都必须标记 adjusted")
    checked += 1
    # 待补尝试次数：循环前归零、retry_end 清零、补发后清零，共三处。
    if module.count("pending = 0") != 3:
        raise ValueError(f"{MODULE} 的待补尝试次数必须在循环前、retry_end 与补发后归零")
    checked += 1
    # 退避：网关值先夹到 [0, 8]，否则指数退避同样封顶。
    checked += _ordered(
        (
            "if retry_after is not None:",
            "return max(0.0, min(retry_after, MAX_RETRY_DELAY_SECONDS))",
            "return min(base_delay * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)",
        ),
        module,
        MODULE,
    )
    # 响应头：ms 优先于秒 → 跳过空值 → 解析失败继续 → 非有限或负数继续 → 无值返回 None。
    checked += _ordered(
        (
            'for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):',
            "raw = headers.get(name)",
            "if not raw:",
            "seconds = float(str(raw).strip()) * scale",
            "except ValueError:\n            continue",
            "if not math.isfinite(seconds) or seconds < 0:",
            "        return seconds\n    return None",
        ),
        module,
        MODULE,
    )
    # 观测：start 记录尝试 → end 清零 → 首个其它事件补终态 → 原事件继续透传。
    checked += _ordered(
        (
            'if event.type == "retry_start":',
            'elif event.type == "retry_end":',
            "elif pending:",
            "yield event",
        ),
        module,
        MODULE,
    )
    # 反向断言：模块只计算时长，不睡眠；事件不夹带内容字段。
    # 非有限网关头依赖 math.isfinite，缺少导入会让 nan / inf 重新进入夹取。
    if "import math\n" not in module:
        raise ValueError(f"{MODULE} 必须导入 math 以拒绝非有限网关头")
    checked += 1
    if "time.sleep(" in module:
        raise ValueError(f"{MODULE} 只计算退避时长，不得在模块内睡眠")
    if "headers[" in module:
        raise ValueError(f"{MODULE} 必须用 get 读取响应头")
    if 'type="retry_start", content' in module:
        raise ValueError(f"{MODULE} 的观测事件不得携带内容")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_retry()
    except (ValueError, OSError) as error:
        print(f"模型重试核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型重试一致：{checked} 项退避、解析与观测校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
