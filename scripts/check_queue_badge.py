#!/usr/bin/env python3
"""核对队列徽标的分类优先级与增量校正。

`queue/list` 的条目是有界投影：截断时按条目统计的分项会偏小，内核持久
分类计数优先；旧内核缺省时只保留待处理总数。本地变更带分类增量时，只有
已知计数与旧总数一致才应用增量，且结果必须非负并与新总数一致，否则放弃
分类，避免徽标显示自相矛盾的分项。结构侧固定分类优先级与未变化判定；行为
侧把真实模块复制到临时目录、改写类型导入，由 Node 加载 `queueBadgeOf` 与
`patchQueueBadge` 驱动投影、合并与补丁。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
BADGE = "apps/desktop/src/renderer/src/data/queueBadge.ts"

EXPECTED = 23

NODE_SCRIPT = """\
import { patchQueueBadge, queueBadgeOf } from "./queueBadge.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);
const item = (status: string) => ({ status });

const full = queueBadgeOf({
  items: [item("queued"), item("queued"), item("delivering"), item("paused")],
});
expect(
  "完整投影累计分类",
  same(full, { activeItems: 4, counts: { queued: 2, delivering: 1, paused: 1 } }),
);

const mixed = queueBadgeOf({ items: [item("queued"), item("done"), item("failed")] });
expect(
  "非待处理状态忽略",
  same(mixed, { activeItems: 1, counts: { queued: 1, delivering: 0, paused: 0 } }),
);

const truncated = queueBadgeOf({ items: [item("queued")], activeItems: 5, truncated: true });
expect("截断投影只保留总数", same(truncated, { activeItems: 5 }));

const persistent = { queued: 8, delivering: 2, paused: 1 };
const withCounts = queueBadgeOf({
  items: [item("queued")],
  activeItems: 11,
  truncated: true,
  counts: persistent,
});
expect(
  "持久计数优先",
  same(withCounts, { activeItems: 11, counts: persistent }) && withCounts.counts === persistent,
);

const delta = { queued: 1, delivering: 0, paused: 0 };
const withDelta = queueBadgeOf({
  items: [item("queued")],
  activeItems: 3,
  truncated: true,
  countsDelta: delta,
});
expect(
  "截断投影保留增量",
  same(withDelta, { activeItems: 3, delta }) && withDelta.delta === delta,
);

const inconsistent = queueBadgeOf({ items: [item("queued")], activeItems: 4, truncated: false });
expect("条目数与总数不一致放弃分类", same(inconsistent, { activeItems: 4 }));

const empty = queueBadgeOf({ items: [], activeItems: 0, counts: persistent });
expect("零待处理不带分类", same(empty, { activeItems: 0 }));

const legacy = queueBadgeOf({ items: [item("paused"), item("delivering")], truncated: true });
expect("旧内核回退已载入条数", same(legacy, { activeItems: 2 }));

const sessions = [
  { id: "a", queueActiveItems: 2, queueCounts: { queued: 1, delivering: 1, paused: 0 } },
  { id: "b" },
];
const patched = patchQueueBadge(sessions, "b", {
  activeItems: 3,
  counts: { queued: 2, delivering: 0, paused: 1 },
});
expect(
  "目标会话写入分类",
  patched !== null
    && same(patched![1], {
      id: "b",
      queueActiveItems: 3,
      queueCounts: { queued: 2, delivering: 0, paused: 1 },
    }),
);
expect("其他会话保持引用", patched !== null && patched![0] === sessions[0]);
expect("原数组不被修改", sessions[1].queueActiveItems === undefined && sessions.length === 2);

expect(
  "未命中返回 null",
  patchQueueBadge(sessions, "missing", {
    activeItems: 1,
    counts: { queued: 1, delivering: 0, paused: 0 },
  }) === null,
);
const steady = [{ id: "a", queueActiveItems: 2, queueCounts: { queued: 1, delivering: 1, paused: 0 } }];
expect(
  "数值未变返回 null",
  patchQueueBadge(steady, "a", {
    activeItems: 2,
    counts: { queued: 1, delivering: 1, paused: 0 },
  }) === null,
);
expect(
  "零增量未变返回 null",
  patchQueueBadge(steady, "a", { activeItems: 2, delta: { queued: 0, delivering: 0, paused: 0 } })
    === null,
);
const pausedOnly = patchQueueBadge(
  [{ id: "a", queueActiveItems: 3, queueCounts: { queued: 1, delivering: 1, paused: 1 } }],
  "a",
  { activeItems: 3, counts: { queued: 1, delivering: 1, paused: 2 } },
);
expect(
  "仅分类变化返回新数组",
  pausedOnly !== null && pausedOnly![0].queueCounts!.paused === 2,
);

const dropped = patchQueueBadge(
  [{ id: "a", queueActiveItems: 4, queueCounts: { queued: 2, delivering: 1, paused: 1 } }],
  "a",
  { activeItems: 5 },
);
expect(
  "总数变化无增量放弃分类",
  dropped !== null && dropped![0].queueActiveItems === 5 && dropped![0].queueCounts === undefined,
);

const adjusted = patchQueueBadge(
  [{ id: "a", queueActiveItems: 5, queueCounts: { queued: 3, delivering: 1, paused: 1 } }],
  "a",
  { activeItems: 6, delta: { queued: 2, delivering: 0, paused: -1 } },
);
expect(
  "增量校正已知计数",
  adjusted !== null && same(adjusted![0].queueCounts, { queued: 5, delivering: 1, paused: 0 }),
);

const negative = patchQueueBadge(
  [{ id: "a", queueActiveItems: 1, queueCounts: { queued: 1, delivering: 0, paused: 0 } }],
  "a",
  { activeItems: 0, delta: { queued: -2, delivering: 1, paused: 0 } },
);
expect(
  "负增量放弃分类",
  negative !== null && negative![0].queueCounts === undefined && negative![0].queueActiveItems === 0,
);

const mismatched = patchQueueBadge(
  [{ id: "a", queueActiveItems: 2, queueCounts: { queued: 2, delivering: 0, paused: 0 } }],
  "a",
  { activeItems: 5, delta: { queued: 1, delivering: 0, paused: 0 } },
);
expect(
  "增量合计不符放弃分类",
  mismatched !== null && mismatched![0].queueCounts === undefined,
);

const brokenBase = patchQueueBadge(
  [{ id: "a", queueActiveItems: 3, queueCounts: { queued: 1, delivering: 1, paused: 0 } }],
  "a",
  { activeItems: 4, delta: { queued: 2, delivering: 0, paused: 0 } },
);
expect(
  "基数不一致放弃增量",
  brokenBase !== null && brokenBase![0].queueCounts === undefined,
);

const replaced = patchQueueBadge(
  [{ id: "a", queueActiveItems: 9, queueCounts: { queued: 9, delivering: 0, paused: 0 } }],
  "a",
  { activeItems: 2, counts: { queued: 1, delivering: 0, paused: 1 } },
);
expect(
  "持久分类覆盖旧分类",
  replaced !== null
    && same(replaced![0].queueCounts, { queued: 1, delivering: 0, paused: 1 })
    && replaced![0].queueActiveItems === 2,
);

const cleared = patchQueueBadge(
  [{ id: "a", queueActiveItems: 1, queueCounts: { queued: 1, delivering: 0, paused: 0 } }],
  "a",
  { activeItems: 0 },
);
expect(
  "清零清除分类",
  cleared !== null && cleared![0].queueActiveItems === 0 && cleared![0].queueCounts === undefined,
);

const legacyFull = patchQueueBadge([{ id: "a" }], "a", {
  activeItems: 1,
  counts: { queued: 1, delivering: 0, paused: 0 },
});
expect(
  "旧会话直接写入分类",
  legacyFull !== null
    && same(legacyFull![0], {
      id: "a",
      queueActiveItems: 1,
      queueCounts: { queued: 1, delivering: 0, paused: 0 },
    }),
);

console.log(`PASS ${passed}`);
"""

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


def _rewrite(source: str) -> str:
    rewritten = source.replace(
        'import type { QueueStatusCounts } from "@boss-harness/protocol";',
        "type QueueStatusCounts = { queued: number; delivering: number; paused: number };",
    )
    rewritten = rewritten.replace(
        'import type { QueuePage, QueueStatusDelta } from "./queueMapping";',
        "type QueueStatusDelta = { queued: number; delivering: number; paused: number };\n"
        "type QueueItem = { status: string };\n"
        "type QueuePage = {\n"
        "  items: QueueItem[];\n"
        "  activeItems?: number;\n"
        "  counts?: QueueStatusCounts;\n"
        "  truncated?: boolean;\n"
        "  countsDelta?: QueueStatusDelta;\n"
        "};",
    )
    if "@boss-harness/protocol" in rewritten or "./queueMapping" in rewritten:
        raise ValueError(f"{BADGE} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
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


def _check_behaviors() -> int:
    source = _read(BADGE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "queueBadge.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("队列徽标行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"队列徽标行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_badge.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_badge.py")
    if "共 73 项结构、23 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_badge.py 检查 73 项结构、23 项行为")
    return 2


def check_queue_badge() -> tuple[int, int]:
    source = _read(BADGE)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_badge()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"队列徽标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列徽标一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
