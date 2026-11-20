#!/usr/bin/env python3
"""核对队列徽标的分类优先级与增量校正。

`queue/list` 的条目是有界投影：截断时按条目统计的分项会偏小，内核持久
分类计数优先；旧内核缺省时只保留待处理总数。本地变更带分类增量时，只有
已知计数与旧总数一致才应用增量，且结果必须非负并与新总数一致，否则放弃
分类，避免徽标显示自相矛盾的分项。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BADGE = "apps/desktop/src/renderer/src/data/queueBadge.ts"

FRAGMENTS = (
    'import type { QueueStatusCounts } from "@boss-harness/protocol";',
    'import type { QueuePage, QueueStatusDelta } from "./queueMapping";',
    "export interface QueueBadge {",
    "counts?: QueueStatusCounts;",
    "delta?: QueueStatusDelta;",
    "export function queueBadgeOf(page: QueuePage): QueueBadge {",
    "const counts: QueueStatusCounts = { queued: 0, delivering: 0, paused: 0 };",
    "for (const item of page.items) {",
    'if (item.status === "queued" || item.status === "delivering" || item.status === "paused") counts[item.status] += 1;',
    "const loaded = counts.queued + counts.delivering + counts.paused;",
    "const activeItems = page.activeItems ?? loaded;",
    "if (page.counts && activeItems > 0) return { activeItems, counts: page.counts };",
    "const complete = page.truncated !== true && loaded === activeItems;",
    "if (complete && activeItems > 0) return { activeItems, counts };",
    "if (page.countsDelta && activeItems > 0) return { activeItems, delta: page.countsDelta };",
    "return { activeItems };",
    "function mergedQueueCounts(",
    "if (badge.counts) return badge.counts;",
    "const base = session.queueCounts;",
    "if (!base || base.queued + base.delivering + base.paused !== session.queueActiveItems) return undefined;",
    "if (!badge.delta) return badge.activeItems === session.queueActiveItems ? base : undefined;",
    "queued: base.queued + badge.delta.queued,",
    "delivering: base.delivering + badge.delta.delivering,",
    "paused: base.paused + badge.delta.paused,",
    "if (counts.queued < 0 || counts.delivering < 0 || counts.paused < 0) return undefined;",
    "if (counts.queued + counts.delivering + counts.paused !== badge.activeItems) return undefined;",
    "return counts;",
    "export function patchQueueBadge<T extends { id: string; queueActiveItems?: number; queueCounts?: QueueStatusCounts }>(",
    "sessions: readonly T[], threadId: string, badge: QueueBadge,",
    "): T[] | null {",
    "let changed = false;",
    "const next = sessions.map(session => {",
    "if (session.id !== threadId) return session;",
    "const counts = mergedQueueCounts(session, badge);",
    "if (session.queueActiveItems === badge.activeItems",
    "&& session.queueCounts?.queued === counts?.queued",
    "&& session.queueCounts?.delivering === counts?.delivering",
    "&& session.queueCounts?.paused === counts?.paused) return session;",
    "changed = true;",
    "return counts",
    "? { ...session, queueActiveItems: badge.activeItems, queueCounts: counts }",
    ": { ...session, queueActiveItems: badge.activeItems, queueCounts: undefined };",
    "return changed ? next : null;",
)

ORDERED = (
    # 徽标统计：逐项累计、待处理总数回退。
    (
        "const counts: QueueStatusCounts = { queued: 0, delivering: 0, paused: 0 };",
        "for (const item of page.items) {",
        'if (item.status === "queued" || item.status === "delivering" || item.status === "paused") counts[item.status] += 1;',
        "const loaded = counts.queued + counts.delivering + counts.paused;",
        "const activeItems = page.activeItems ?? loaded;",
    ),
    # 分类优先级：内核计数、完整投影、本地增量、只保留总数。
    (
        "if (page.counts && activeItems > 0) return { activeItems, counts: page.counts };",
        "const complete = page.truncated !== true && loaded === activeItems;",
        "if (complete && activeItems > 0) return { activeItems, counts };",
        "if (page.countsDelta && activeItems > 0) return { activeItems, delta: page.countsDelta };",
        "return { activeItems };",
    ),
    # 增量校正：基数一致、应用增量、非负与总数核对。
    (
        "if (badge.counts) return badge.counts;",
        "const base = session.queueCounts;",
        "if (!base || base.queued + base.delivering + base.paused !== session.queueActiveItems) return undefined;",
        "if (!badge.delta) return badge.activeItems === session.queueActiveItems ? base : undefined;",
        "queued: base.queued + badge.delta.queued,",
        "delivering: base.delivering + badge.delta.delivering,",
        "paused: base.paused + badge.delta.paused,",
        "if (counts.queued < 0 || counts.delivering < 0 || counts.paused < 0) return undefined;",
        "if (counts.queued + counts.delivering + counts.paused !== badge.activeItems) return undefined;",
        "return counts;",
    ),
    # 补丁：只改目标会话，四项都未变时返回 null。
    (
        "let changed = false;",
        "const next = sessions.map(session => {",
        "if (session.id !== threadId) return session;",
        "const counts = mergedQueueCounts(session, badge);",
        "if (session.queueActiveItems === badge.activeItems",
        "changed = true;",
        "return changed ? next : null;",
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


def check_queue_badge() -> int:
    source = _read(BADGE)
    checked = 0
    checked += _expect(FRAGMENTS, source, BADGE)
    for group in ORDERED:
        checked += _ordered(group, source, BADGE)
    # 反向断言：完整投影必须排除截断；未变化不得返回新数组；
    # 分类与总数对不上时必须放弃分类。
    if "page.truncated === true" in source:
        raise ValueError(f"{BADGE} 的完整投影必须排除截断")
    if "return next;" in source:
        raise ValueError(f"{BADGE} 的未变化会话必须返回 null")
    if "counts.queued + counts.delivering + counts.paused !== badge.activeItems" not in source:
        raise ValueError(f"{BADGE} 的分类必须与新的待处理总数核对")
    return checked + 3


def main() -> int:
    try:
        checked = check_queue_badge()
    except ValueError as error:
        print(f"队列徽标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列徽标一致：{checked} 项分类优先级与增量校正")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
