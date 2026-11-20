#!/usr/bin/env python3
"""核对队列读取的代数票据与失效语义。

事件通知、手动刷新与提交核对会并发发起 `queue/list`，返回顺序不保证与
发出顺序一致。这里按会话维护代数：每次读取领票并推进代数，只有票据仍是
最新一代时才允许写入；本地变更通过 `invalidate` 推进代数，让此前发出的
读取全部失效。固定这些语义，避免旧数据覆盖已撤回或已编辑的条目。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARD = "apps/desktop/src/renderer/src/data/queueReadGuard.ts"

FRAGMENTS = (
    "export interface QueueReadTicket {",
    "commit(apply: () => void): void;",
    "isCurrent(): boolean;",
    "export interface QueueReadGuard {",
    "issue(threadId: string): QueueReadTicket;",
    "invalidate(threadId: string): void;",
    "export function createQueueReadGuard(): QueueReadGuard {",
    "const generations = new Map<string, number>();",
    "const current = (threadId: string): number => generations.get(threadId) ?? 0;",
    "const bump = (threadId: string): number => {",
    "const next = current(threadId) + 1;",
    "generations.set(threadId, next);",
    "return next;",
    "issue(threadId: string): QueueReadTicket {",
    "const generation = bump(threadId);",
    "const isCurrent = (): boolean => current(threadId) === generation;",
    "if (isCurrent()) apply();",
    "invalidate(threadId: string): void {",
    "bump(threadId);",
)

ORDERED = (
    # 票据接口：写入与只读判断。
    (
        "export interface QueueReadTicket {",
        "commit(apply: () => void): void;",
        "isCurrent(): boolean;",
    ),
    # 守卫接口：领票与失效。
    (
        "export interface QueueReadGuard {",
        "issue(threadId: string): QueueReadTicket;",
        "invalidate(threadId: string): void;",
    ),
    # 代数：读取当前值、加一、写回、返回。
    (
        "export function createQueueReadGuard(): QueueReadGuard {",
        "const generations = new Map<string, number>();",
        "const current = (threadId: string): number => generations.get(threadId) ?? 0;",
        "const bump = (threadId: string): number => {",
        "const next = current(threadId) + 1;",
        "generations.set(threadId, next);",
        "return next;",
    ),
    # 领票：先推进代数，再快照己方代。
    (
        "issue(threadId: string): QueueReadTicket {",
        "const generation = bump(threadId);",
        "const isCurrent = (): boolean => current(threadId) === generation;",
    ),
    # 写入：只有仍为最新一代才执行。
    (
        "return {",
        "isCurrent,",
        "commit(apply: () => void): void {",
        "if (isCurrent()) apply();",
    ),
    # 失效：只推进代数。
    (
        "invalidate(threadId: string): void {",
        "bump(threadId);",
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


def check_queue_read_guard() -> int:
    source = _read(GUARD)
    checked = 0
    checked += _expect(FRAGMENTS, source, GUARD)
    for group in ORDERED:
        checked += _ordered(group, source, GUARD)
    # 反向断言：写入必须经过当前代检查；失效不得删除记录；缺失会话从 0 起算。
    if source.count("apply();") != 1:
        raise ValueError(f"{GUARD} 的写入必须经过当前代检查")
    if "generations.delete" in source:
        raise ValueError(f"{GUARD} 的失效必须推进代数，不能删除记录")
    if "?? -1" in source:
        raise ValueError(f"{GUARD} 的缺失会话必须从 0 起算")
    return checked + 3


def main() -> int:
    try:
        checked = check_queue_read_guard()
    except ValueError as error:
        print(f"队列读取守卫核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列读取守卫一致：{checked} 项代数票据与失效")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
