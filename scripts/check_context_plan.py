#!/usr/bin/env python3
"""核对整理计划回执的形状校验。

`contextPlan.ts` 在上下文面板渲染前整体校验 `context/compact/plan` 回执：会话
归属、回合边界、来源摘要、计数与保留回合必须合法；`firstKeptItemId` 与保留条目数
必须自洽；选择方式声明为 `keepRecentTokens` 时保留目标须与请求一致；面板不渲染的
协议字段缺失时兼容旧内核、出现时必须合法；声明使用了用量校准时锚点计数必须
大于零。无法识别时抛出统一错误。这里用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = "apps/desktop/src/renderer/src/data/contextPlan.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

PLAN_FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const MAX_RETAINED_TURNS = 10_000;",
    "const SOURCE_DIGEST = /^[0-9a-f]{64}$/;",
    'const SELECTIONS: ReadonlySet<string> = new Set(["explicit", "keepRecentTokens"]);',
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0;',
    'typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;',
    'value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;',
    'throw new Error("整理计划回执无法识别");',
    "export function contextPlanOf(value: unknown, expected: ContextPlanExpectation): ContextPlan {",
    "if (!raw || raw.threadId !== expected.threadId) invalid();",
    "if (!isId(raw.throughTurnId)) invalid();",
    'if (typeof raw.sourceDigest !== "string" || !SOURCE_DIGEST.test(raw.sourceDigest)) invalid();',
    "if (!isCount(raw.sourceItemCount) || raw.sourceItemCount < 1) invalid();",
    "if (!isId(raw.firstItemId) || !isId(raw.lastItemId)) invalid();",
    "if (!isCount(raw.retainedItemCount) || !isCount(raw.estimatedRetainedTokens)) invalid();",
    "if (!Array.isArray(raw.retainedTurnIds) || raw.retainedTurnIds.length > MAX_RETAINED_TURNS) invalid();",
    "if (!isId(item) || retainedTurnIds.includes(item)) invalid();",
    "if (raw.firstKeptItemId !== undefined && raw.firstKeptItemId !== null) {",
    "if (!isId(raw.firstKeptItemId)) invalid();",
    "if ((raw.retainedItemCount > 0) !== (firstKeptItemId !== null)) invalid();",
    'if (typeof raw.selection !== "string" || !SELECTIONS.has(raw.selection)) invalid();',
    'if (raw.selection === "keepRecentTokens" && raw.keepRecentTokens !== expected.keepRecentTokens) invalid();',
    "if (raw.keepRecentTokens !== undefined && raw.keepRecentTokens !== null && !isCount(raw.keepRecentTokens)) invalid();",
    "if (!Array.isArray(raw.sourceItemIds) || raw.sourceItemIds.length !== raw.sourceItemCount) invalid();",
    "if (raw.sourceItemIds.some(item => !isId(item))) invalid();",
    "if (raw.digestVersion !== undefined && raw.digestVersion !== 2) invalid();",
    "if (raw.checkpointDigest !== undefined && raw.checkpointDigest !== null",
    '&& (typeof raw.checkpointDigest !== "string" || !SOURCE_DIGEST.test(raw.checkpointDigest))) invalid();',
    'if (raw.retentionUsageApplied !== undefined && typeof raw.retentionUsageApplied !== "boolean") invalid();',
    "if (raw.retentionUsageAnchorCount !== undefined && !isCount(raw.retentionUsageAnchorCount)) invalid();",
    "const retentionUsageApplied = raw.retentionUsageApplied === true;",
    "const retentionUsageAnchorCount = isCount(raw.retentionUsageAnchorCount) ? raw.retentionUsageAnchorCount : 0;",
    "if (retentionUsageApplied && retentionUsageAnchorCount < 1) invalid();",
    "threadId: expected.threadId,",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { contextPlanOf } = await import(pathToFileURL(process.argv[1]).href);
const DIGEST = "a".repeat(64);
const expected = { threadId: "t1", keepRecentTokens: 2000 };
const base = {
  threadId: "t1", throughTurnId: "turn-9", sourceDigest: DIGEST, sourceItemCount: 3,
  firstItemId: "i1", lastItemId: "i3", retainedItemCount: 1, retainedTurnIds: ["turn-8", "turn-9"],
  firstKeptItemId: "i3", estimatedRetainedTokens: 120,
};
const plan = value => { try { return contextPlanOf(value, expected); } catch (error) { return `bad:${error.message}`; } };
const check = over => typeof plan({ ...base, ...over }) === "string" ? "bad" : "ok";
const usage = over => {
  const result = plan({ ...base, ...over });
  return typeof result === "string" ? "bad" : [result.retentionUsageApplied, result.retentionUsageAnchorCount];
};
const results = {
  valid: [
    plan(base),
    plan({ ...base, retainedItemCount: 0, retainedTurnIds: [], firstKeptItemId: undefined }),
    plan({ ...base, selection: "keepRecentTokens", keepRecentTokens: 2000, sourceItemIds: ["i1", "i2", "i3"],
      digestVersion: 2, checkpointDigest: DIGEST, retentionUsageApplied: true, retentionUsageAnchorCount: 2, extra: "x" }),
    plan({ ...base, threadId: "t2" }),
  ],
  identity: [
    plan(null) === "bad:整理计划回执无法识别" ? "bad" : "ok",
    typeof plan(Object.assign([], base)) === "string" ? "bad" : "ok",
    check({ throughTurnId: "" }),
    check({ throughTurnId: "x".repeat(200) }),
    check({ throughTurnId: "x".repeat(201) }),
    check({ sourceDigest: "A".repeat(64) }),
    check({ sourceDigest: "a".repeat(63) }),
    check({ sourceDigest: "a".repeat(65) }),
    check({ sourceDigest: 5 }),
  ],
  counts: [
    check({ sourceItemCount: 0 }),
    check({ sourceItemCount: 1.5 }),
    check({ firstItemId: "" }),
    check({ lastItemId: 5 }),
    check({ estimatedRetainedTokens: -1 }),
    check({ estimatedRetainedTokens: "1" }),
    check({ estimatedRetainedTokens: 0 }),
  ],
  retained: [
    check({ retainedTurnIds: "turn-8" }),
    check({ retainedTurnIds: ["turn-8", "turn-8"] }),
    check({ retainedTurnIds: ["turn-8", ""] }),
    check({ retainedTurnIds: Array.from({ length: 10001 }, (_, index) => `t${index}`) }),
    check({ retainedTurnIds: [] }),
  ],
  firstKept: [
    check({ firstKeptItemId: null }),
    check({ retainedItemCount: 0 }),
    check({ firstKeptItemId: "" }),
    check({ retainedItemCount: 0, firstKeptItemId: null }),
    check({ firstKeptItemId: 5 }),
  ],
  selection: [
    check({ selection: "other" }),
    check({ selection: 5 }),
    check({ selection: "explicit" }),
    check({ selection: "explicit", keepRecentTokens: 9 }),
    check({ selection: "keepRecentTokens", keepRecentTokens: 2000 }),
    check({ selection: "keepRecentTokens", keepRecentTokens: 9 }),
    check({ keepRecentTokens: -1 }),
    check({ keepRecentTokens: null }),
  ],
  compat: [
    check({ sourceItemIds: ["i1", "i2"] }),
    check({ sourceItemIds: ["i1", "i2", "i3"] }),
    check({ sourceItemIds: ["i1", "i2", ""] }),
    check({ sourceItemIds: "i1" }),
    check({ digestVersion: 1 }),
    check({ digestVersion: 2 }),
    check({ checkpointDigest: null }),
    check({ checkpointDigest: DIGEST }),
    check({ checkpointDigest: "xyz" }),
  ],
  usage: [
    usage({}),
    usage({ retentionUsageApplied: true, retentionUsageAnchorCount: 2 }),
    usage({ retentionUsageApplied: false, retentionUsageAnchorCount: 3 }),
    usage({ retentionUsageApplied: true }),
    usage({ retentionUsageApplied: true, retentionUsageAnchorCount: 0 }),
    usage({ retentionUsageApplied: "yes" }),
    usage({ retentionUsageAnchorCount: -1 }),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

DIGEST = "a" * 64
BASE_PLAN = {
    "threadId": "t1", "throughTurnId": "turn-9", "sourceDigest": DIGEST, "sourceItemCount": 3,
    "firstItemId": "i1", "lastItemId": "i3", "retainedItemCount": 1, "retainedTurnIds": ["turn-8", "turn-9"],
    "firstKeptItemId": "i3", "estimatedRetainedTokens": 120,
    "retentionUsageApplied": False, "retentionUsageAnchorCount": 0,
}
EXPECTED_VALID = (
    BASE_PLAN,
    {**BASE_PLAN, "retainedItemCount": 0, "retainedTurnIds": [], "firstKeptItemId": None},
    {**BASE_PLAN, "retentionUsageApplied": True, "retentionUsageAnchorCount": 2},
    "bad:整理计划回执无法识别",
)
EXPECTED_IDENTITY = ("bad", "bad", "bad", "ok", "bad", "bad", "bad", "bad", "bad")
EXPECTED_COUNTS = ("bad", "bad", "bad", "bad", "bad", "bad", "ok")
EXPECTED_RETAINED = ("bad", "bad", "bad", "bad", "ok")
EXPECTED_FIRST_KEPT = ("bad", "bad", "bad", "ok", "bad")
EXPECTED_SELECTION = ("bad", "bad", "ok", "ok", "ok", "bad", "bad", "ok")
EXPECTED_COMPAT = ("bad", "ok", "bad", "bad", "bad", "ok", "ok", "ok", "bad")
EXPECTED_USAGE = ([False, 0], [True, 2], [False, 3], "bad", "bad", "bad", "bad")


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / PLAN)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 整理计划试算失败，请核对 Node.js 24+ 与 contextPlan.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的整理计划结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回整理计划矩阵")
    for key in ("valid", "identity", "counts", "retained", "firstKept", "selection", "compat", "usage"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"整理计划{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"整理计划{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["valid"], EXPECTED_VALID, "收敛结果")
    checked += _compare(payload["identity"], EXPECTED_IDENTITY, "身份与摘要")
    checked += _compare(payload["counts"], EXPECTED_COUNTS, "计数与边界")
    checked += _compare(payload["retained"], EXPECTED_RETAINED, "保留回合")
    checked += _compare(payload["firstKept"], EXPECTED_FIRST_KEPT, "首个保留条目")
    checked += _compare(payload["selection"], EXPECTED_SELECTION, "选择方式")
    checked += _compare(payload["compat"], EXPECTED_COMPAT, "兼容字段")
    checked += _compare(payload["usage"], EXPECTED_USAGE, "用量校准")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_plan.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_plan.py")
    if "共 34 项结构、54 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_plan.py 检查 34 项结构、54 项行为")
    return 2


def check_context_plan() -> tuple[int, int]:
    structure = _expect(PLAN_FRAGMENTS, _read(PLAN), PLAN)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_plan()
    except (OSError, ValueError) as error:
        print(f"整理计划规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"整理计划规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
