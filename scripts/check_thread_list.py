#!/usr/bin/env python3
"""核对会话列表回执的逐项校验、去重与末回合来源。

侧栏把条目直接映射为会话：标识用于去重与操作目标，标题与时间用于展示，
末回合决定状态、失败标记与继续目标。这里固定必填与可选字段的边界、角色与状态
白名单、失败码与恢复策略，以及重复 id 的拒绝，避免部分可疑列表被展示。

切换过分支位置的会话，日志末回合 `lastTurn` 可能属于已放弃的分支：内核另报
`branchLastTurn`（只由本会话条目推导），桌面端有该字段时按它计算，位置变化后刷新列表。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
THREADS = "apps/desktop/src/renderer/src/data/threadList.ts"
BRIDGE = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
APP = "apps/desktop/src/renderer/src/App.tsx"
PROTOCOL = "packages/protocol/src/index.ts"
SESSION = "harness/src/boss_harness/session.py"
APPLICATION = "harness/src/boss_harness/application.py"

FRAGMENTS = (
    'import type { ThreadSummary } from "@boss-harness/protocol";',
    "const ID_LIMIT = 200;",
    "const TITLE_LIMIT = 500;",
    "const TIME_LIMIT = 64;",
    "const CODE_LIMIT = 120;",
    'const TURN_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "interrupted", "blocked", "error"]);',
    "function text(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    "function optionalText(value: unknown, limit: number): string | null | undefined {",
    "if (value === undefined || value === null) return null;",
    'return typeof value === "string" && value.length <= limit ? value : undefined;',
    "export function threadSummaryOf(value: unknown): ThreadSummary | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const raw = value as Record<string, unknown>;",
    "if (!text(raw.id, ID_LIMIT)) return null;",
    'if (typeof raw.title !== "string" || raw.title.length > TITLE_LIMIT) return null;',
    'if (typeof raw.updatedAt !== "string" || raw.updatedAt.length > TIME_LIMIT) return null;',
    'if (raw.archived !== undefined && typeof raw.archived !== "boolean") return null;',
    'if (raw.toolPolicy !== undefined && raw.toolPolicy !== "readOnly" && raw.toolPolicy !== "approval") return null;',
    "const provider = optionalText(raw.provider, ID_LIMIT);",
    "if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;",
    "if (!summaryTurnValid(raw.lastTurn) || !summaryTurnValid(raw.branchLastTurn)) return null;",
    "return raw as unknown as ThreadSummary;",
    "function summaryTurnValid(value: unknown): boolean {",
    "if (value === undefined || value === null) return true;",
    'if (typeof value !== "object" || Array.isArray(value)) return false;',
    "if (!text(turn.turnId, ID_LIMIT)) return false;",
    'if (typeof turn.status !== "string" || !TURN_STATUSES.has(turn.status)) return false;',
    "if (optionalText(turn.failureCode, CODE_LIMIT) === undefined) return false;",
    "return optionalText(turn.taskResumePolicy, CODE_LIMIT) !== undefined;",
    'export function summaryTurnOf(thread: ThreadSummary): ThreadSummary["lastTurn"] {',
    "return thread.branchLastTurn !== undefined ? thread.branchLastTurn : thread.lastTurn;",
    "export function uniqueThreadIds(items: { id: string }[]): boolean {",
    "return new Set(items.map(item => item.id)).size === items.length;",
)

ORDERED = (
    # 条目：对象判定 → 标识 → 标题与时间 → 归档与策略 → 可选文本 → 最近回合 → 放行。
    (
        "export function threadSummaryOf(value: unknown): ThreadSummary | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!text(raw.id, ID_LIMIT)) return null;",
        "raw.title.length > TITLE_LIMIT",
        "raw.updatedAt.length > TIME_LIMIT",
        "raw.archived !== undefined",
        "raw.toolPolicy !== undefined",
        "const provider = optionalText(raw.provider, ID_LIMIT);",
        "if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;",
        "if (!summaryTurnValid(raw.lastTurn) || !summaryTurnValid(raw.branchLastTurn)) return null;",
        "return raw as unknown as ThreadSummary;",
    ),
    # 末回合：缺省放行 → 对象判定 → 回合编号 → 状态白名单 → 失败码 → 恢复策略。
    (
        "function summaryTurnValid(value: unknown): boolean {",
        "if (value === undefined || value === null) return true;",
        'if (typeof value !== "object" || Array.isArray(value)) return false;',
        "if (!text(turn.turnId, ID_LIMIT)) return false;",
        "!TURN_STATUSES.has(turn.status)",
        "optionalText(turn.failureCode, CODE_LIMIT) === undefined",
        "return optionalText(turn.taskResumePolicy, CODE_LIMIT) !== undefined;",
    ),
    # 去重：集合大小必须等于条目数。
    (
        "export function uniqueThreadIds(items: { id: string }[]): boolean {",
        "return new Set(items.map(item => item.id)).size === items.length;",
    ),
)


# 内核索引：先写日志末回合，再清掉外来同名值，只对切换过位置的会话按位置推导；
# 分支无法投影时不写字段，列表不因此失败。
KERNEL_INDEX = (
    "def _index_thread(self, thread_id: str, connection: sqlite3.Connection) -> None:",
    'metadata["lastTurn"] = self._public_turn(turns[-1]) if turns else None',
    'metadata.pop("branchLastTurn", None)',
    'if any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):',
    'leaf_turn_id = self._leaf_state(thread_id, entries)["leafTurnId"]',
    "except ValueError:",
    'metadata["branchLastTurn"] = next(',
    '(self._public_turn(turn) for turn in turns if turn["turnId"] == leaf_turn_id), None)',
    "queue_counts = self._queue_status_counts(entries)",
)

# 分支视图：两个末回合字段取自本次读取的同一个值；未切换过位置的会话不补字段。
KERNEL_VIEW = (
    "def _branch_view_thread(thread: dict, last_turn: dict | None) -> dict:",
    'view = {**thread, "lastTurn": last_turn}',
    'if "branchLastTurn" in view:',
    'view["branchLastTurn"] = last_turn',
    "return view",
)

LEAF_REFRESH = 'if (event.method === "thread/leafChanged") { void replica.reload(id); void refresh(); return; }'


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


def check_thread_list() -> int:
    source = _read(THREADS)
    checked = 0
    checked += _expect(FRAGMENTS, source, THREADS)
    for group in ORDERED:
        checked += _ordered(group, source, THREADS)
    # 反向断言：可选字段的非法与缺省必须分开；重复 id 不得放行；必须校验三项可选文本。
    if "return typeof value === \"string\" ? value : null;" in source:
        raise ValueError(f"{THREADS} 的非法可选字段不能当作缺省")
    if "new Set(items.map(item => item.id)).size >= items.length" in source:
        raise ValueError(f"{THREADS} 的重复 id 必须拒绝")
    if "provider === undefined || model === undefined)" in source:
        raise ValueError(f"{THREADS} 必须同时校验 provider、model 与 reasoningEffort")
    checked += 3
    # 两个末回合字段共用一个校验函数：分别内联会让其中一个漏掉字段。
    if source.count("summaryTurnValid(") != 3:
        raise ValueError(f"{THREADS} 的末回合校验必须恰好定义一次并用于 lastTurn 与 branchLastTurn")
    checked += 1
    # 桌面映射：侧栏状态、回合编号、失败码与恢复策略都取自 summaryTurnOf 选出的回合。
    bridge = _read(BRIDGE)
    if 'import { summaryTurnOf, threadSummaryOf, uniqueThreadIds } from "./threadList";' not in bridge:
        raise ValueError(f"{BRIDGE} 缺少 summaryTurnOf 导入")
    if bridge.count("const turn = summaryTurnOf(thread);") != 2:
        raise ValueError(f"{BRIDGE} 的两处会话摘要映射都必须经 summaryTurnOf 选出末回合")
    for stale in ("thread.lastTurn", "thread.branchLastTurn"):
        if stale in bridge:
            raise ValueError(f"{BRIDGE} 不能绕过 summaryTurnOf 直接读取 {stale}")
    for fragment in ('status: turn?.status === "running" ? "running"', "turnId: turn?.turnId", "lastTurnStatus: turn?.status",
                     "lastTurnErrorCode: turn?.failureCode", "taskResumePolicy: turn?.taskResumePolicy"):
        if bridge.count(fragment) != 2:
            raise ValueError(f"{BRIDGE} 的两处会话摘要映射缺少：{fragment}")
    checked += 9
    # 位置变化后当前分支末回合随之改变：重读会话之外还要刷新列表，继续检查随列表刷新重做。
    app = _read(APP)
    if app.count(LEAF_REFRESH) != 1 or app.count('event.method === "thread/leafChanged"') != 1:
        raise ValueError(f"{APP} 收到位置变化通知后必须重读会话并刷新会话列表，且只处理一次")
    for fragment in ('const sourceTurnId = session.lastTurnStatus === "interrupted" ? session.turnId : undefined;',
                     "activeRef.current = summary; setActiveSession(summary);", "void readContinuationCheck(summary);"):
        if app.count(fragment) != 1:
            raise ValueError(f"{APP} 的继续检查必须取自刷新后的会话摘要：{fragment}")
    checked += 5
    protocol = _read(PROTOCOL)
    if protocol.count('branchLastTurn?: ThreadSummary["lastTurn"];') != 1:
        raise ValueError(f"{PROTOCOL} 的会话摘要缺少与 lastTurn 同形的可选 branchLastTurn")
    checked += 1
    # 内核：字段只由本会话条目推导，日志末回合保持不变；分叉的新会话头不继承。
    session = _read(SESSION)
    start = session.find(KERNEL_INDEX[0])
    end = session.find("def _sync_thread(", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少会话索引函数或其收尾标记")
    checked += _ordered(KERNEL_INDEX, session[start:end], SESSION)
    if session.count('metadata["branchLastTurn"] =') != 1 or session.count('metadata["lastTurn"] =') != 1:
        raise ValueError(f"{SESSION} 的两个末回合字段各只能在索引函数里写入一次")
    if session.count('"branchLastTurn", "queueActiveItems", "queueCounts",') != 1:
        raise ValueError(f"{SESSION} 的分叉会话头必须排除 branchLastTurn")
    checked += 3
    application = _read(APPLICATION)
    start = application.find(KERNEL_VIEW[0])
    end = application.find("def _snapshot(", start)
    if start < 0 or end < 0:
        raise ValueError(f"{APPLICATION} 缺少分支视图摘要函数或其收尾标记")
    checked += _ordered(KERNEL_VIEW, application[start:end], APPLICATION)
    if application.count("self._branch_view_thread(") != 2:
        raise ValueError(f"{APPLICATION} 的分支视图（冻结快照与普通读取）都必须经 _branch_view_thread 生成摘要")
    if 'thread = {**thread, "lastTurn":' in application:
        raise ValueError(f"{APPLICATION} 的分支视图不能只替换 lastTurn 而留下索引里的 branchLastTurn")
    return checked + 2


def main() -> int:
    try:
        checked = check_thread_list()
    except ValueError as error:
        print(f"会话列表核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话列表一致：{checked} 项校验、可选字段、去重、当前分支末回合与位置变化刷新")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
