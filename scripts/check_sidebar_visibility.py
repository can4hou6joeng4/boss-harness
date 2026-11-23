#!/usr/bin/env python3
"""核对侧栏会话可见性与「待你处理」分组规则。

`sidebarVisibility.ts` 决定隐藏开关、归档分组、隐藏计数与需要用户处理的会话。这里
静态核对模块契约，并用 Node 直接加载真实模块覆盖隐藏过滤、归档互斥、计数去重、
失败判定与审批计数等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/sidebarVisibility.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { SessionItem } from "./mockData";',
    " * 侧栏会话可见性：关闭「显示已隐藏的聊天」时过滤隐藏会话；开启时原样保留，",
    "export function visibleSessions(sessions: SessionItem[], hidden: ReadonlySet<string>, showHidden: boolean): SessionItem[] {",
    "return showHidden ? sessions : sessions.filter(session => !hidden.has(session.id));",
    "export function hideActionLabel(hidden: boolean): string {",
    'return hidden ? "取消隐藏" : "在侧栏隐藏";',
    "export function nonArchivedSessions(sessions: SessionItem[], hidden: ReadonlySet<string>, showHidden: boolean): SessionItem[] {",
    "return visibleSessions(sessions.filter(session => session.archived !== true), hidden, showHidden);",
    "export function archivedSessions(sessions: SessionItem[], hidden: ReadonlySet<string>, showHidden: boolean): SessionItem[] {",
    "return visibleSessions(sessions.filter(session => session.archived === true), hidden, showHidden);",
    " * 持久化 id 可能指向已删除或尚未加载的会话，直接按集合大小计数会虚高。",
    "export function hiddenSessionCount(sessions: SessionItem[], hidden: ReadonlySet<string>): number {",
    "return new Set(sessions.filter(session => hidden.has(session.id)).map(session => session.id)).size;",
    "export function sessionFailed(session: SessionItem): boolean {",
    'return session.status !== "running" && session.status !== "interrupted"',
    '&& (session.lastTurnStatus === "error" || session.lastTurnStatus === "blocked");',
    " * 审批挂起时回合仍是 running，既不算失败也不算中断，队列也没有暂停项；但审批有到期时间",
    "export function sessionNeedsAttention(session: SessionItem, approvalCount = 0): boolean {",
    "return session.archived !== true",
    '&& (sessionFailed(session) || session.status === "interrupted"',
    "|| (session.queueCounts?.paused ?? 0) > 0 || approvalCount > 0);",
    "export function attentionSessions(sessions: SessionItem[], hidden: ReadonlySet<string>, showHidden: boolean,",
    "approvalCounts: Readonly<Record<string, number>> = {}): SessionItem[] {",
    "return nonArchivedSessions(sessions, hidden, showHidden)",
    ".filter(session => sessionNeedsAttention(session, approvalCounts[session.id] ?? 0));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  visibleSessions, hideActionLabel, nonArchivedSessions, archivedSessions,
  hiddenSessionCount, sessionFailed, sessionNeedsAttention, attentionSessions,
} = await import(pathToFileURL(process.argv[1]).href);
const ids = list => list.map(item => item.id).join(",");
const all = [
  { id: "a", status: "idle" },
  { id: "b", status: "idle", archived: true },
  { id: "c", status: "idle" },
  { id: "d", status: "idle", archived: true },
];
const hidden = new Set(["c", "d", "ghost"]);
const group = [
  { id: "a", status: "idle", lastTurnStatus: "error" },
  { id: "b", status: "running" },
  { id: "c", status: "interrupted" },
  { id: "d", status: "idle", lastTurnStatus: "error", archived: true },
  { id: "e", status: "idle", lastTurnStatus: "completed" },
  { id: "f", status: "idle", queueCounts: { paused: 1 } },
];
const groupHidden = new Set(["c"]);
const result = {
  visible: [
    ids(visibleSessions(all, hidden, false)),
    visibleSessions(all, hidden, true) === all,
    ids(visibleSessions(all, hidden, true)),
  ],
  labels: [hideActionLabel(true), hideActionLabel(false)],
  archive: [
    ids(nonArchivedSessions(all, hidden, false)),
    ids(nonArchivedSessions(all, hidden, true)),
    ids(archivedSessions(all, hidden, false)),
    ids(archivedSessions(all, hidden, true)),
    ids(nonArchivedSessions([{ id: "x", archived: false }, { id: "y" }, { id: "z", archived: true }], new Set(), false)),
  ],
  counts: [
    hiddenSessionCount(all, hidden),
    hiddenSessionCount([all[2], all[2]], hidden),
    hiddenSessionCount(all, new Set()),
  ],
  failed: [
    sessionFailed({ id: "s", status: "idle", lastTurnStatus: "error" }),
    sessionFailed({ id: "s", status: "idle", lastTurnStatus: "blocked" }),
    sessionFailed({ id: "s", status: "running", lastTurnStatus: "error" }),
    sessionFailed({ id: "s", status: "interrupted", lastTurnStatus: "blocked" }),
    sessionFailed({ id: "s", status: "idle", lastTurnStatus: "completed" }),
    sessionFailed({ id: "s", status: "idle" }),
  ],
  attention: [
    sessionNeedsAttention({ id: "s", status: "idle", lastTurnStatus: "error" }),
    sessionNeedsAttention({ id: "s", status: "interrupted" }),
    sessionNeedsAttention({ id: "s", status: "idle", queueCounts: { paused: 1 } }),
    sessionNeedsAttention({ id: "s", status: "idle", queueCounts: { paused: 0 } }),
    sessionNeedsAttention({ id: "s", status: "running" }, 1),
    sessionNeedsAttention({ id: "s", status: "running" }),
    sessionNeedsAttention({ id: "s", status: "idle", lastTurnStatus: "error", archived: true }),
    sessionNeedsAttention({ id: "s", status: "running", archived: true }, 2),
  ],
  groups: [
    ids(attentionSessions(group, groupHidden, false, { b: 1 })),
    ids(attentionSessions(group, groupHidden, true, { b: 1 })),
    ids(attentionSessions(group, groupHidden, false)),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED = {
    "visible": ("a,b", True, "a,b,c,d"),
    "labels": ("取消隐藏", "在侧栏隐藏"),
    "archive": ("a", "a,c", "b", "b,d", "x,y"),
    "counts": (2, 1, 0),
    "failed": (True, True, False, False, False, False),
    "attention": (True, True, True, False, True, False, False, False),
    "groups": ("a,b,f", "a,b,c,f", "a,f"),
}
LABELS = {
    "visible": "隐藏开关",
    "labels": "菜单文案",
    "archive": "归档分组",
    "counts": "隐藏计数",
    "failed": "失败判定",
    "attention": "待处理判定",
    "groups": "待处理分组",
}


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 侧栏可见性试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 侧栏可见性试算失败，请核对 Node.js 24+ 与 sidebarVisibility.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的侧栏可见性结果") from None
    for key in EXPECTED:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"侧栏{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"侧栏{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return sum(_compare(payload[key], expected, LABELS[key]) for key, expected in EXPECTED.items())


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_sidebar_visibility.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_sidebar_visibility.py")
    if "共 25 项结构、30 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_sidebar_visibility.py 检查 25 项结构、30 项行为")
    return 2


def check_sidebar_visibility() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_sidebar_visibility()
    except (OSError, ValueError) as error:
        print(f"侧栏可见性规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"侧栏可见性规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
