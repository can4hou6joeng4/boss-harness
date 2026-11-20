#!/usr/bin/env python3
"""核对单飞读取的尾随补跑与取消语义。

轮询、聚焦与通知防抖共用一个读取动作：在途期间的调用只记录尾随标记，
结束后补跑一次；同步抛错也要释放单飞标记；卸载取消后不再补跑。这里固定
入口守卫、标记流转、`catch().finally()` 链与收尾顺序，避免最后一次变化
被丢掉，或卸载后的任务继续写状态。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RELOAD = "apps/desktop/src/renderer/src/data/singleFlightReload.ts"

FRAGMENTS = (
    "export interface SingleFlightReload {",
    "run(): void;",
    "cancel(): void;",
    "export function createSingleFlightReload(",
    "task: () => Promise<void>,",
    "canRun: () => boolean = () => true,",
    "): SingleFlightReload {",
    "let inFlight = false;",
    "let pending = false;",
    "let cancelled = false;",
    "if (cancelled || !canRun()) return;",
    "if (inFlight) {",
    "pending = true;",
    "inFlight = true;",
    "flight = task();",
    "flight = Promise.resolve();",
    "void flight.catch(() => {",
    "}).finally(() => {",
    "if (cancelled || !pending) return;",
    "pending = false;",
    "run();",
    "cancelled = true;",
)

ORDERED = (
    # 入口：先判取消与 canRun，再判在途。
    (
        "const run = (): void => {",
        "if (cancelled || !canRun()) return;",
        "if (inFlight) {",
        "pending = true;",
        "return;",
        "}",
        "inFlight = true;",
    ),
    # 同步抛错也转成已解决的 Promise。
    (
        "let flight: Promise<void>;",
        "try {",
        "flight = task();",
        "} catch {",
        "flight = Promise.resolve();",
    ),
    # 链尾释放单飞标记，再按取消与尾随标记决定是否补跑。
    (
        "void flight.catch(() => {",
        "}).finally(() => {",
        "inFlight = false;",
        "if (cancelled || !pending) return;",
        "pending = false;",
        "run();",
    ),
    # 取消：清除取消与尾随标记，不直接补跑。
    (
        "cancel() {",
        "cancelled = true;",
        "pending = false;",
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


def check_single_flight() -> int:
    source = _read(RELOAD)
    checked = 0
    checked += _expect(FRAGMENTS, source, RELOAD)
    for group in ORDERED:
        checked += _ordered(group, source, RELOAD)
    # 反向断言：单飞标记只在声明与收尾出现；尾随标记只在补跑与取消清除；
    # 不得用延时轮询代替尾随补跑。
    if source.count("inFlight = false;") != 2:
        raise ValueError(f"{RELOAD} 的单飞标记只能在收尾释放")
    if source.count("pending = false;") != 3:
        raise ValueError(f"{RELOAD} 的尾随标记只在补跑与取消时清除")
    if "setTimeout" in source:
        raise ValueError(f"{RELOAD} 不得用延时轮询代替尾随补跑")
    return checked + 3


def main() -> int:
    try:
        checked = check_single_flight()
    except ValueError as error:
        print(f"单飞读取核对失败，{error}", file=sys.stderr)
        return 2
    print(f"单飞读取一致：{checked} 项尾随补跑与取消")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
