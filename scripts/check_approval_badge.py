#!/usr/bin/env python3
"""核对待审批列表校验、徽标计数、到期文案与分组。

`pendingApprovals.ts` 校验 `approval/list`：外层不可读或截断标记类型错误时抛错，
单条缺关键字段、到期时间不可读或 approvalId 重复时丢弃；持久计数任一项非法时
整体丢弃，未截断时计数与可见条目必须一致，偏大按「至少」处理。到期时间低于
`1e12` 按 Unix 秒换算为毫秒；倒计时区分已过期、即将过期、分钟与小时；徽标超过
9 条显示 `9+`，截断文案使用「至少」；键盘索引在条目间循环；通知点击目标与按
会话分组只接受可定位的字段。这里用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PENDING = "apps/desktop/src/renderer/src/data/pendingApprovals.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

PENDING_FRAGMENTS = (
    "const FIELD_LIMIT = 200;",
    "const SUMMARY_LIMIT = 400;",
    "const DIGEST_LIMIT = 128;",
    'if (typeof value !== "string") return null;',
    "return trimmed && trimmed.length <= limit ? trimmed : null;",
    "function optionalText(value: unknown, limit: number): string | undefined {",
    "if (!approvalId || !threadId || !itemId || !toolName) return null;",
    "if (deadline === undefined) return null;",
    'summary: summary ?? "",',
    'paramsDigest: paramsDigest ?? "",',
    "count: list.total ?? list.approvals.length,",
    "truncated: list.truncated && list.total === undefined,",
    "counts: list.threadCounts ?? countPendingApprovalsByThread(list.approvals),",
    "function threadCountsOf(value: unknown, approvals: readonly PendingApproval[], truncated: boolean): ThreadCountsRead {",
    "const visible: Record<string, number> = Object.create(null) as Record<string, number>;",
    'if (!Number.isSafeInteger(total + count)) return "invalid";',
    'if (total < approvals.length) return "invalid";',
    'if (!Object.prototype.hasOwnProperty.call(counts, threadId)) return "invalid";',
    'if (recorded === undefined || recorded < count) return "invalid";',
    'if (!truncated && recorded !== count) return "incomplete";',
    'if (!truncated) return total === approvals.length ? { counts, total } : "incomplete";',
    "export function mapPendingApprovals(value: unknown, limit = 100): PendingApprovalList {",
    'throw new Error("内核审批列表无法识别");',
    'if (truncated !== undefined && typeof truncated !== "boolean") {',
    "if (!approval || seen.has(approval.approvalId)) continue;",
    "if (approvals.length >= limit) break;",
    "const result: PendingApprovalList = { approvals, truncated: truncated === true };",
    "result.truncated = true;",
    "result.threadCounts = threadCounts.counts;",
    "const APPROVAL_DEADLINE_MS_THRESHOLD = 1e12;",
    "return value > 0 && value < APPROVAL_DEADLINE_MS_THRESHOLD ? value * MILLISECONDS_PER_SECOND : value;",
    'export function approvalUrgency(deadline: number, now = Date.now()): "expired" | "soon" | "normal" | "unknown" {',
    'if (remaining <= 0) return "expired";',
    'return remaining < APPROVAL_SOON_MS ? "soon" : "normal";',
    'if (remaining < MINUTE) return "即将过期";',
    "if (remaining < HOUR) return `${Math.ceil(remaining / MINUTE)} 分钟后过期`;",
    'return count > 9 ? "9+" : String(Math.floor(count));',
    "return truncated ? `至少 ${visible} 项待审批` : `${visible} 项待审批`;",
    'return method === "approval/requested" || method === "approval/decided";',
    "return (current + delta + count) % count;",
    "export function groupPendingApprovals(approvals: PendingApproval[]): PendingApprovalGroup[] {",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  mapPendingApprovals, approvalBadgeState, approvalDeadlineMs, approvalUrgency,
  approvalRemainingText, approvalBadgeText, approvalBadgeLabel, isApprovalCountEvent,
  nextApprovalIndex, readApprovalFocus, countPendingApprovalsByThread, groupPendingApprovals,
  APPROVAL_SOON_MS,
} = await import(pathToFileURL(process.argv[1]).href);
const approval = (over = {}) => ({ approvalId: "a1", threadId: "t1", itemId: "i1", toolName: "boss_hr_greet", deadline: 1700000000, ...over });
const thrown = (fn) => { try { fn(); return "no-throw"; } catch (error) { return error.message; } };
const now = 1_000_000;
const results = {
  map: [
    [
      thrown(() => mapPendingApprovals(null)),
      thrown(() => mapPendingApprovals({})),
      thrown(() => mapPendingApprovals({ approvals: {} })),
      thrown(() => mapPendingApprovals([])),
    ],
    [
      thrown(() => mapPendingApprovals({ approvals: [], truncated: "yes" })),
      thrown(() => mapPendingApprovals({ approvals: [], truncated: 1 })),
    ],
    (() => {
      const mapped = mapPendingApprovals({ approvals: [{
        approvalId: " a1 ", threadId: " t1 ", itemId: " i1 ", toolName: " boss_hr_greet ",
        deadline: 1700000000, summary: " s ", paramsDigest: " d ", turnId: " u ",
      }] });
      return [mapped.approvals[0], mapped.truncated, mapped.total === undefined, mapped.threadCounts === undefined];
    })(),
    (() => {
      const mapped = mapPendingApprovals({ approvals: [
        approval(),
        approval({ approvalId: "" }),
        approval({ toolName: " " }),
        null,
        "x",
        42,
        approval({ deadline: "soon" }),
        approval({ summary: "x".repeat(401), paramsDigest: "d".repeat(129), turnId: "u".repeat(201) }),
      ] });
      return [mapped.approvals.length, mapped.approvals[0].summary, mapped.approvals[0].paramsDigest, "turnId" in mapped.approvals[0]];
    })(),
    mapPendingApprovals({ approvals: [approval(), approval(), approval({ approvalId: "a2" })] }).approvals.map(item => item.approvalId),
    (() => {
      const mapped = mapPendingApprovals({ approvals: [
        approval(), approval({ approvalId: "a2" }), approval({ approvalId: "a3" }),
        approval({ approvalId: "a4" }), approval({ approvalId: "a5" }),
      ] }, 3);
      return [mapped.approvals.map(item => item.approvalId), mapped.truncated];
    })(),
    (() => {
      const list = mapPendingApprovals({ approvals: [approval(), approval({ approvalId: "a2", threadId: "t2" })], threadCounts: { t1: 1, t2: 1 } });
      return [list.truncated, list.total, list.threadCounts];
    })(),
    (() => {
      const list = mapPendingApprovals({ approvals: [approval(), approval({ approvalId: "a2" })], threadCounts: { t1: 1 } });
      return [list.threadCounts === undefined, list.total === undefined, list.truncated];
    })(),
    (() => {
      const list = mapPendingApprovals({ approvals: [approval()], threadCounts: { t1: 2 } });
      return [list.truncated, list.threadCounts === undefined, list.total === undefined];
    })(),
    (() => {
      const list = mapPendingApprovals({ approvals: [approval()], truncated: true, threadCounts: { t1: 5 } });
      return [list.truncated, list.total, list.threadCounts, list.approvals.length];
    })(),
    [
      mapPendingApprovals({ approvals: [], threadCounts: { "": 1 } }),
      mapPendingApprovals({ approvals: [], threadCounts: { t1: 1.5 } }),
      mapPendingApprovals({ approvals: [], threadCounts: { t1: -1 } }),
      mapPendingApprovals({ approvals: [], threadCounts: [] }),
    ].map(list => [list.threadCounts === undefined, list.total === undefined]),
    (() => {
      const list = mapPendingApprovals({ approvals: [approval()] });
      return [list.threadCounts === undefined, approvalBadgeState(list)];
    })(),
  ],
  badge: [
    approvalBadgeState({ approvals: [approval(), approval({ approvalId: "a2" })], truncated: true, total: 7, threadCounts: { t1: 2 } }),
    approvalBadgeState({ approvals: [approval(), approval({ approvalId: "a2" })], truncated: true }),
    approvalBadgeState({ approvals: [approval(), approval({ approvalId: "a2" })], truncated: false }),
  ],
  deadline: [
    approvalDeadlineMs(1700000000),
    approvalDeadlineMs(1700000000000),
    approvalDeadlineMs(0),
    approvalDeadlineMs(-5),
    approvalDeadlineMs(1e12),
    approvalDeadlineMs("1"),
    approvalDeadlineMs(Number.NaN),
    approvalDeadlineMs(Number.POSITIVE_INFINITY),
  ],
  urgency: [
    approvalUrgency(now - 1, now),
    approvalUrgency(now, now),
    approvalUrgency(now + 1, now),
    approvalUrgency(now + APPROVAL_SOON_MS - 1, now),
    approvalUrgency(now + APPROVAL_SOON_MS, now),
    approvalUrgency(Number.NaN, now),
    approvalUrgency(now, Number.NaN),
    approvalUrgency(Number.POSITIVE_INFINITY, now),
  ],
  remaining: [
    approvalRemainingText(now - 1, now),
    approvalRemainingText(now, now),
    approvalRemainingText(now + 1, now),
    approvalRemainingText(now + 59_999, now),
    approvalRemainingText(now + 60_000, now),
    approvalRemainingText(now + 3_600_000, now),
    approvalRemainingText(now + 3_600_001, now),
    approvalRemainingText(Number.NaN, now),
    approvalRemainingText(now, Number.NaN),
  ],
  text: [
    [0, 1.9, 9, 10, Number.POSITIVE_INFINITY, "3"].map(approvalBadgeText),
    [approvalBadgeLabel(1, false), approvalBadgeLabel(1, true), approvalBadgeLabel(2.7, false), approvalBadgeLabel(0, false), approvalBadgeLabel(-1, true)],
    ["approval/requested", "approval/decided", "approval/list", "turn/started", null].map(isApprovalCountEvent),
  ],
  index: [
    nextApprovalIndex(0, 0, 1),
    nextApprovalIndex(-1, 5, 1),
    nextApprovalIndex(-1, 5, -1),
    nextApprovalIndex(5, 5, 1),
    nextApprovalIndex(5, 5, -1),
    nextApprovalIndex(2, 5, 1),
    nextApprovalIndex(0, 5, -1),
    nextApprovalIndex(4, 5, 1),
    nextApprovalIndex(3, 4, -5),
    nextApprovalIndex(0, 5, 7),
  ],
  focus: [
    [null, {}, { threadId: " " }, { threadId: "t", itemId: "" }].map(readApprovalFocus),
    readApprovalFocus({ threadId: " t1 ", itemId: " i1 " }),
    readApprovalFocus({ threadId: "x".repeat(201), itemId: "i1" }),
  ],
  counts: (() => {
    const counts = countPendingApprovalsByThread([approval(), approval({ approvalId: "a2" }), approval({ approvalId: "a3", threadId: "t2" })]);
    const special = countPendingApprovalsByThread([approval({ threadId: "__proto__" })]);
    return [counts, Object.getPrototypeOf(counts), Object.keys(special), special["__proto__"], ({}).polluted === undefined];
  })(),
  group: (() => {
    const groups = groupPendingApprovals([
      approval({ approvalId: "b1", threadId: "t2" }),
      approval({ approvalId: "a1", threadId: "t1" }),
      approval({ approvalId: "b2", threadId: "t2" }),
    ]);
    return groups.map(item => [item.threadId, item.approvals.map(entry => entry.approvalId)]);
  })(),
};
process.stdout.write(JSON.stringify(results));
"""

SENTINEL = "内核审批列表无法识别"
EXPECTED_MAP = (
    [SENTINEL, SENTINEL, SENTINEL, SENTINEL],
    [SENTINEL, SENTINEL],
    [
        {
            "approvalId": "a1", "threadId": "t1", "itemId": "i1", "toolName": "boss_hr_greet",
            "deadline": 1700000000000, "summary": "s", "paramsDigest": "d", "turnId": "u",
        },
        False,
        True,
        True,
    ],
    [1, "", "", False],
    ["a1", "a2"],
    [["a1", "a2", "a3"], False],
    [False, 2, {"t1": 1, "t2": 1}],
    [True, True, False],
    [True, True, True],
    [True, 5, {"t1": 5}, 1],
    [[True, True], [True, True], [True, True], [True, True]],
    [True, {"count": 1, "truncated": False, "counts": {"t1": 1}}],
)
EXPECTED_BADGE = (
    {"count": 7, "truncated": False, "counts": {"t1": 2}},
    {"count": 2, "truncated": True, "counts": {"t1": 2}},
    {"count": 2, "truncated": False, "counts": {"t1": 2}},
)
EXPECTED_DEADLINE = (1700000000000, 1700000000000, 0, -5, 1e12, None, None, None)
EXPECTED_URGENCY = ("expired", "expired", "soon", "soon", "normal", "unknown", "unknown", "unknown")
EXPECTED_REMAINING = (
    "已过期", "已过期", "即将过期", "即将过期", "1 分钟后过期",
    "1 小时后过期", "2 小时后过期", "到期时间未知", "到期时间未知",
)
EXPECTED_TEXT = (
    [None, "1", "9", "9+", None, None],
    ["1 项待审批", "至少 1 项待审批", "2 项待审批", None, None],
    [True, True, False, False, False],
)
EXPECTED_INDEX = (-1, 0, 4, 0, 4, 3, 4, 0, 2, 2)
EXPECTED_FOCUS = (
    [None, None, None, None],
    {"threadId": "t1", "itemId": "i1"},
    None,
)
EXPECTED_COUNTS = (
    {"t1": 2, "t2": 1},
    None,
    ["__proto__"],
    1,
    True,
)
EXPECTED_GROUP = (["t2", ["b1", "b2"]], ["t1", ["a1"]])


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / PENDING)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 待审批试算失败，请核对 Node.js 24+ 与 pendingApprovals.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的待审批结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回待审批矩阵")
    for key in ("map", "badge", "deadline", "urgency", "remaining", "text", "index", "focus", "counts"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"待审批{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"待审批{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["map"], EXPECTED_MAP, "映射")
    checked += _compare(payload["badge"], EXPECTED_BADGE, "徽标")
    checked += _compare(payload["deadline"], EXPECTED_DEADLINE, "到期")
    checked += _compare(payload["urgency"], EXPECTED_URGENCY, "紧急度")
    checked += _compare(payload["remaining"], EXPECTED_REMAINING, "倒计时")
    checked += _compare(payload["text"], EXPECTED_TEXT, "文案")
    checked += _compare(payload["index"], EXPECTED_INDEX, "索引")
    checked += _compare(payload["focus"], EXPECTED_FOCUS, "焦点")
    checked += _compare(payload["counts"], EXPECTED_COUNTS, "计数")
    checked += _compare(payload["group"], EXPECTED_GROUP, "分组")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_approval_badge.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_approval_badge.py")
    if "共 41 项结构、63 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_approval_badge.py 检查 41 项结构、63 项行为")
    return 2


def check_pending_approvals() -> tuple[int, int]:
    structure = _expect(PENDING_FRAGMENTS, _read(PENDING), PENDING)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_pending_approvals()
    except (OSError, ValueError) as error:
        print(f"待审批规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"待审批规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
