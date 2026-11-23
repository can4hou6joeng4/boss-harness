#!/usr/bin/env python3
"""核对队列投影的项校验、计数元数据与本地合入。

`queueMapping.ts` 拒绝畸形队列项（任一项非法即整页不可用），并要求分类计数是
三个非负安全整数且与待处理总数一致；总数不能小于已载入条目，待处理数不能小于
已载入的待处理条目且不能超过总数，投影规模不一致时强制标记截断。提交结果查找
只有投影完整时才允许返回 `missing`；本地合入按状态变化更新待处理数与总数，截断
投影保留分类增量供徽标校正。这里用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
QUEUE = "apps/desktop/src/renderer/src/data/queueMapping.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

QUEUE_FRAGMENTS = (
    'export function isQueueActive(status: QueueItem["status"]): status is "queued" | "delivering" | "paused" {',
    'return status === "queued" || status === "delivering" || status === "paused";',
    "export function queueCountsDelta(previous: readonly QueueItem[], next: readonly QueueItem[]): QueueStatusDelta {",
    "for (const item of previous) if (isQueueActive(item.status)) delta[item.status] -= 1;",
    "for (const item of next) if (isQueueActive(item.status)) delta[item.status] += 1;",
    'const QUEUE_KINDS: ReadonlySet<string> = new Set(["steering", "followUp"]);',
    'const QUEUE_STATUSES: ReadonlySet<string> = new Set(["queued", "delivering", "delivered", "paused", "cancelled"]);',
    'const QUEUE_PAUSE_REASONS: ReadonlySet<string> = new Set(["COMPACTION_FAILED", "THREAD_ARCHIVED", "TURN_NOT_COMPLETED"]);',
    "function isRecord(value: unknown): value is Record<string, unknown> {",
    'return typeof value === "object" && value !== null && !Array.isArray(value);',
    'if (value.enabled !== undefined && typeof value.enabled !== "boolean") return false;',
    "if (value.triggerPercent !== undefined && !Number.isSafeInteger(value.triggerPercent)) return false;",
    "if (value.keepRecentTokens !== undefined && !Number.isSafeInteger(value.keepRecentTokens)) return false;",
    "export function isQueueItem(value: unknown): value is QueueItem {",
    'if (typeof value.id !== "string" || value.id.length === 0) return false;',
    'if (typeof value.kind !== "string" || !QUEUE_KINDS.has(value.kind)) return false;',
    'if (typeof value.input !== "string") return false;',
    'if (typeof value.status !== "string" || !QUEUE_STATUSES.has(value.status)) return false;',
    'if (value.expectedTurnId != null && typeof value.expectedTurnId !== "string") return false;',
    'if (value.clientUserMessageId != null && typeof value.clientUserMessageId !== "string") return false;',
    '&& !(Array.isArray(value.skillIds) && value.skillIds.every(id => typeof id === "string"))) return false;',
    "if (value.autoCompaction !== undefined && !isAutoCompaction(value.autoCompaction)) return false;",
    'if (value.failureCode !== undefined && value.failureCode !== "TURN_START_FAILED") return false;',
    "|| !QUEUE_PAUSE_REASONS.has(value.pausedReason))) return false;",
    'if (value.executionStarted !== undefined && value.executionStarted !== false) return false;',
    'if (value.turnId !== undefined && typeof value.turnId !== "string") return false;',
    'if (value.inputPersisted !== undefined && typeof value.inputPersisted !== "boolean") return false;',
    'if (value.deduplicated !== undefined && typeof value.deduplicated !== "boolean") return false;',
    'if (value.inputTruncated !== undefined && typeof value.inputTruncated !== "boolean") return false;',
    "function isSafeCount(value: unknown): value is number {",
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0;',
    "export function queueStatusCountsOf(value: unknown, activeItems: number): QueueStatusCounts | null {",
    "if (counts.queued + counts.delivering + counts.paused !== activeItems) return null;",
    "export function threadQueueCountsOf(activeItems: unknown, counts: unknown): {",
    "if (active === undefined) return {};",
    "return parsed ? { activeItems: active, counts: parsed } : { activeItems: active };",
    "export function queueItemsOf(value: unknown): QueueItem[] | null {",
    "if (!isQueueItem(item)) return null;",
    "export function queuePageOf(response: QueueListResponse | null | undefined): QueuePage | null {",
    "if ((page.totalItems !== undefined && page.totalItems > items.length)",
    "page.truncated = true;",
    '} else if (typeof metadata.truncated === "boolean") {',
    "page.truncated = metadata.truncated;",
    "const counts = queueStatusCountsOf(metadata.counts, page.activeItems);",
    "page.counts = counts;",
    "export function queuePageOfSnapshot(snapshot: {",
    "export function queueSubmissionLookup(page: QueuePage, clientUserMessageId: string): QueueSubmissionLookup {",
    'if (item) return item.status === "cancelled" ? { status: "cancelled", item } : { status: "found", item };',
    'return page.truncated === true ? { status: "unknown" } : { status: "missing" };',
    "export function patchQueuePage(page: QueuePage | undefined, item: QueueItem): QueuePage {",
    "const delta = (!wasActive && nowActive) ? 1 : (wasActive && !nowActive) ? -1 : 0;",
    "activeItems = Math.max(0, page.activeItems + delta);",
    "totalItems = Math.max(page.totalItems + (exists ? 0 : 1), items.length);",
    "const countsDelta = page?.truncated === true ? delta : undefined;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  isQueueActive, queueCountsDelta, isQueueItem, queueStatusCountsOf, threadQueueCountsOf,
  queueItemsOf, queuePageOf, queuePageOfSnapshot, queueSubmissionLookup, patchQueuePage,
} = await import(pathToFileURL(process.argv[1]).href);
const item = (over = {}) => ({ id: "i1", kind: "followUp", input: "hello", status: "queued", ...over });
const pageOf = (items, over = {}) => queuePageOf({ items, ...over });
const summarize = page => page === null ? null
  : [page.totalItems ?? null, page.activeItems ?? null, page.counts ?? null, page.truncated ?? null];
const summarizePatch = page => [
  page.items.length, page.totalItems ?? null, page.activeItems ?? null,
  page.counts ?? null, page.truncated ?? null, page.countsDelta ?? null,
];
const results = {
  active: [
    ["queued", "delivering", "paused", "delivered", "cancelled", "other", undefined].map(isQueueActive),
    queueCountsDelta(
      [item(), item({ id: "i2", status: "paused" }), item({ id: "i3", status: "delivered" })],
      [item({ status: "paused" }), item({ id: "i4", status: "delivering" })],
    ),
  ],
  items: [
    [
      item(), null, [],
      item({ id: "" }), item({ kind: "steer" }), item({ input: 42 }), item({ status: "running" }),
      item({ expectedTurnId: 42 }), item({ clientUserMessageId: null }), item({ skillIds: [1] }),
      item({ skillIds: ["s1"] }), item({ autoCompaction: { enabled: "yes" } }),
      item({ autoCompaction: { triggerPercent: 80, keepRecentTokens: 1000 } }),
      item({ failureCode: "OTHER" }), item({ pausedReason: "other" }), item({ pausedReason: "TURN_NOT_COMPLETED" }),
      item({ executionStarted: true }), item({ turnId: 42 }), item({ inputPersisted: "yes" }),
      item({ deduplicated: "yes" }), item({ inputTruncated: "yes" }),
    ].map(value => isQueueItem(value) ? "ok" : "bad"),
  ],
  counts: [
    queueStatusCountsOf({ queued: 1, delivering: 2, paused: 0 }, 3),
    queueStatusCountsOf({ queued: 1, delivering: 2, paused: 0 }, 4),
    queueStatusCountsOf({ queued: -1, delivering: 2, paused: 0 }, 1),
    queueStatusCountsOf(null, 0),
    threadQueueCountsOf(-1, { queued: 0, delivering: 0, paused: 0 }),
    threadQueueCountsOf(2, { queued: 1, delivering: 1, paused: 0 }),
    threadQueueCountsOf(2, { queued: 1, delivering: 1, paused: 1 }),
  ],
  lists: [
    queueItemsOf([item()])?.length,
    queueItemsOf([item(), {}]),
    queueItemsOf({}),
    queuePageOf(null),
    queuePageOfSnapshot({ queue: "x" }),
  ],
  metadata: [
    summarize(pageOf([item()], { totalItems: 5, activeItems: 2, counts: { queued: 2, delivering: 0, paused: 0 }, truncated: true })),
    summarize(pageOf([item()], { totalItems: 0, activeItems: 0, counts: { queued: 0, delivering: 0, paused: 0 }, truncated: false })),
  ],
  invalidMetadata: [
    summarize(pageOf([item()], { totalItems: 1.5 })),
    summarize(pageOf([item()], { activeItems: 0 })),
    summarize(pageOf([item()], { totalItems: 3, activeItems: 4 })),
    summarize(pageOf([item()], { activeItems: 1, counts: { queued: 1, delivering: 0, paused: 1 } })),
    summarize(pageOf([item()], { truncated: "yes" })),
    summarize(queuePageOfSnapshot({ queue: [item()], queueTotalItems: 2, queueActiveItems: 1, queueCounts: { queued: 1, delivering: 0, paused: 0 }, queueTruncated: true })),
  ],
  lookup: [
    queueSubmissionLookup(pageOf([item({ clientUserMessageId: "m1" })]), "m1"),
    queueSubmissionLookup(pageOf([item({ clientUserMessageId: "m1", status: "cancelled" })]), "m1"),
    queueSubmissionLookup(pageOf([item()]), "m1"),
    queueSubmissionLookup(pageOf([item()], { truncated: true }), "m1"),
  ],
  patch: [
    summarizePatch(patchQueuePage(undefined, item())),
    summarizePatch(patchQueuePage({ items: [item()], activeItems: 1, totalItems: 1, counts: { queued: 1, delivering: 0, paused: 0 } }, item({ status: "delivered" }))),
    summarizePatch(patchQueuePage({ items: [item()], activeItems: 1, totalItems: 3, truncated: true }, item({ id: "i2", status: "queued" }))),
    summarizePatch(patchQueuePage({ items: [item()] }, item({ id: "i2", status: "queued" }))),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_ACTIVE = (
    [True, True, True, False, False, False, False],
    {"queued": -1, "delivering": 1, "paused": 0},
)
EXPECTED_ITEMS = (
    ["ok", "bad", "bad", "bad", "bad", "bad", "bad", "bad", "ok", "bad", "ok", "bad", "ok",
     "bad", "bad", "ok", "bad", "bad", "bad", "bad", "bad"],
)
EXPECTED_COUNTS = (
    {"queued": 1, "delivering": 2, "paused": 0},
    None,
    None,
    None,
    {},
    {"activeItems": 2, "counts": {"queued": 1, "delivering": 1, "paused": 0}},
    {"activeItems": 2},
)
EXPECTED_LISTS = (1, None, None, None, None)
EXPECTED_METADATA = (
    [5, 2, {"queued": 2, "delivering": 0, "paused": 0}, True],
    [None, None, None, False],
)
EXPECTED_INVALID_METADATA = (
    [None, None, None, None],
    [None, None, None, None],
    [3, None, None, True],
    [None, 1, None, None],
    [None, None, None, None],
    [2, 1, {"queued": 1, "delivering": 0, "paused": 0}, True],
)
FOUND_ITEM = {"id": "i1", "kind": "followUp", "input": "hello", "status": "queued", "clientUserMessageId": "m1"}
EXPECTED_LOOKUP = (
    {"status": "found", "item": FOUND_ITEM},
    {"status": "cancelled", "item": {**FOUND_ITEM, "status": "cancelled"}},
    {"status": "missing"},
    {"status": "unknown"},
)
EXPECTED_PATCH = (
    [1, 1, 1, None, None, None],
    [1, 1, 0, {"queued": 0, "delivering": 0, "paused": 0}, None, None],
    [2, 4, 2, None, True, {"queued": 1, "delivering": 0, "paused": 0}],
    [2, 2, 2, None, None, None],
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / QUEUE)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 队列映射试算失败，请核对 Node.js 24+ 与 queueMapping.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的队列映射结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回队列映射矩阵")
    for key in ("active", "items", "counts", "lists", "metadata", "invalidMetadata", "lookup", "patch"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"队列映射{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"队列映射{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["active"], EXPECTED_ACTIVE, "活动状态")
    checked += _compare(payload["items"], EXPECTED_ITEMS, "条目")
    checked += _compare(payload["counts"], EXPECTED_COUNTS, "计数")
    checked += _compare(payload["lists"], EXPECTED_LISTS, "列表")
    checked += _compare(payload["metadata"], EXPECTED_METADATA, "元数据")
    checked += _compare(payload["invalidMetadata"], EXPECTED_INVALID_METADATA, "非法元数据")
    checked += _compare(payload["lookup"], EXPECTED_LOOKUP, "提交查找")
    checked += _compare(payload["patch"], EXPECTED_PATCH, "本地合入")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_mapping.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_mapping.py")
    if "共 54 项结构、31 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_mapping.py 检查 54 项结构、31 项行为")
    return 2


def check_queue_mapping() -> tuple[int, int]:
    structure = _expect(QUEUE_FRAGMENTS, _read(QUEUE), QUEUE)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_mapping()
    except (OSError, ValueError) as error:
        print(f"队列映射规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列映射规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
