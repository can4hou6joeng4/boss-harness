#!/usr/bin/env python3
"""核对模型重试的退避上限、环境解析与观测事件边界。

retry.py 只决定「等多久、最多几次」：环境变量去空白后按整数解析并在 1–10 与
非负基数内收敛；网关 Retry-After 优先于指数退避，两者都封顶 8 秒；观测事件
只带次数、毫秒与错误说明，retry_end 在首个非错误事件补成功、在错误事件补失败。
任一放宽都会让等待无界或让观测事件与真实尝试次数不符，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/retry.py"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    "return float(str(raw).strip()) * scale",
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
    # 响应头：ms 优先于秒 → 跳过空值 → 解析失败继续 → 无值返回 None。
    checked += _ordered(
        (
            'for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):',
            "raw = headers.get(name)",
            "if not raw:",
            "return float(str(raw).strip()) * scale",
            "except ValueError:\n            continue\n    return None",
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
    if "time.sleep(" in module:
        raise ValueError(f"{MODULE} 只计算退避时长，不得在模块内睡眠")
    if "headers[" in module:
        raise ValueError(f"{MODULE} 必须用 get 读取响应头")
    if 'type="retry_start", content' in module:
        raise ValueError(f"{MODULE} 的观测事件不得携带内容")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_retry()
    except ValueError as error:
        print(f"模型重试核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型重试一致：{checked} 项退避、解析与观测防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
