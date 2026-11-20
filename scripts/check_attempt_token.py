#!/usr/bin/env python3
"""核对在途请求标记的推进、作废与比较。

弹窗等待异步结果期间可以被关闭、重新打开或发起新请求；旧请求返回时
只在与当前标记一致时才允许写回。开始提交与关闭弹窗都推进标记，标记
从 0 起算，`attemptCurrent` 做严格相等比较。这里固定这些语义，避免
旧回调把提示、输入正文或忙碌态写回新界面。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = "apps/desktop/src/renderer/src/data/attemptToken.ts"

FRAGMENTS = (
    "export type AttemptToken = { current: number };",
    "export function createAttemptToken(): AttemptToken {",
    "return { current: 0 };",
    "export function startAttempt(tracker: AttemptToken): number {",
    "tracker.current += 1;",
    "return tracker.current;",
    "export function invalidateAttempts(tracker: AttemptToken): void {",
    "export function attemptCurrent(tracker: AttemptToken, token: number): boolean {",
    "return token === tracker.current;",
)

ORDERED = (
    # 新建：标记从 0 起算。
    (
        "export function createAttemptToken(): AttemptToken {",
        "return { current: 0 };",
    ),
    # 开始提交：推进后返回新标记。
    (
        "export function startAttempt(tracker: AttemptToken): number {",
        "tracker.current += 1;",
        "return tracker.current;",
    ),
    # 作废：只推进标记。
    (
        "export function invalidateAttempts(tracker: AttemptToken): void {",
        "tracker.current += 1;",
    ),
    # 当前判断：严格相等。
    (
        "export function attemptCurrent(tracker: AttemptToken, token: number): boolean {",
        "return token === tracker.current;",
    ),
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_attempt_token() -> int:
    source = _read(ATTEMPT)
    checked = 0
    checked += _expect(FRAGMENTS, source, ATTEMPT)
    for group in ORDERED:
        checked += _ordered(group, source, ATTEMPT)
    # 反向断言：开始与作废都要推进；开始不得重置；比较不得放宽。
    if source.count("tracker.current += 1;") != 2:
        raise ValueError(f"{ATTEMPT} 的开始与作废都必须推进标记")
    if "tracker.current = 0" in source:
        raise ValueError(f"{ATTEMPT} 的开始提交不得重置标记")
    if "token <=" in source:
        raise ValueError(f"{ATTEMPT} 的当前判断必须是严格相等")
    return checked + 3


def main() -> int:
    try:
        checked = check_attempt_token()
    except ValueError as error:
        print(f"在途标记核对失败，{error}", file=sys.stderr)
        return 2
    print(f"在途标记一致：{checked} 项推进、作废与比较")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
