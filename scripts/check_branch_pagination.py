#!/usr/bin/env python3
"""核对分支读取期间的位置变化不会被拼成一条列表。

分支端点与当前分支回合始终分多次读取，内核每次请求都按当下的 leaf 计算回合集合，
并在同一响应里报告该位置。两次请求之间位置变化时，各页分属不同位置，且不会出现
重复回合可供查重；界面必须逐页比较响应报告的位置（含单页读取与切走又切回），
不一致就放弃本次结果。旧内核的回合页不带位置时，翻页才回退到端点复核。

逐页比较依赖内核响应自身一致：分支视图回合页的 `turns` 与 `branch` 必须出自同一次
加锁读取的同一份条目，处理器不得在释放锁后另行读取位置。`thread/read` 的非快照
分支视图同理：条目、末回合、回合页与位置都从处理器读到的同一份条目快照算出。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGED = "apps/desktop/src/renderer/src/data/pagedRead.ts"
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"
PAGES = "apps/desktop/src/renderer/src/data/branchPages.ts"
SESSION = "harness/src/boss_harness/session.py"
APPLICATION = "harness/src/boss_harness/application.py"

KERNEL_SESSION = (
    "active_turns = self._turns(self._active_entries(entries), thread_id)",
    'active_ids = {turn["turnId"] for turn in active_turns}',
    "leaf = self._leaf_state(thread_id, entries, turns=active_turns)",
    '"branch": leaf}',
    "def _leaf_state(self, thread_id: str, entries: list[dict], active: list[dict] | None = None, *,",
    "turns: list[dict] | None = None) -> dict:",
)

KERNEL_PINNED = (
    "def list_branch_turns(self, thread_id: str, *, cursor: str | None = None, limit: int = 50,",
    "entries: list[dict] | None = None) -> dict:",
    "pinned = entries",
    "entries = self.read_entries(thread_id) if pinned is None else pinned",
    "def branch_last_turn(self, thread_id: str, *, entries: list[dict] | None = None) -> dict | None:",
    "def read_leaf(self, thread_id: str, *, entries: list[dict] | None = None) -> dict:",
)

THREAD_READ = (
    "entries = self.sessions.read_entries_snapshot(thread_id)",
    "pinned = entries",
    "entries = self.sessions._active_entries(pinned)",
    'thread = {**thread, "lastTurn": self.sessions.branch_last_turn(thread_id, entries=pinned)}',
    "self.sessions.list_branch_turns(thread_id, entries=pinned) if branch",
    'result["branch"] = self.sessions.read_leaf(thread_id, entries=pinned)',
)

KERNEL_HANDLER = (
    'return {"turns": result["turns"], "nextCursor": result["nextCursor"],',
    '"view": "branch", "branch": result["branch"]}',
)

DRIFT_CHECK = (
    'const LEAF_DRIFT = "分支在读取期间发生变化：当前位置已改变（切换了分支或开始了新回合），'
    '本次列表可能混用两个位置的结果，已放弃；请刷新后重试。";',
    "const pageLeaves: { seen: (string | null)[]; missing: boolean } = { seen: [], missing: false };",
    "pageLeaves.seen.push(page.leafTurnId);",
    "const leaf = branchPageLeafOf(page.branch, id);",
    'if (leaf === "invalid") throw new Error("当前分支回合响应的位置信息不属于当前会话或无法识别");',
    'if (leaf === "missing") pageLeaves.missing = true;',
    "else pageLeaves.seen.push(leaf.leafTurnId);",
    "if (!sameLeafAcrossPages(pageLeaves.seen)) {",
    "if (pageLeaves.missing && (endpointPage.pages > 1 || turnPage.pages > 1)) {",
    "const check = await listThreadBranches(id);",
    "if (check.threadId !== id || !Array.isArray(check.endpoints)) {",
    "if ((check.leafTurnId ?? null) !== (pageLeaves.seen[0] ?? null)) {",
)

PAGE_LEAF_FRAGMENTS = (
    'export function branchPageLeafOf(branch: unknown, threadId: string): '
    '{ leafTurnId: string | null } | "missing" | "invalid" {',
    'if (branch === undefined) return "missing";',
    'if (!branch || typeof branch !== "object" || Array.isArray(branch)) return "invalid";',
    'if (raw.threadId !== threadId) return "invalid";',
    "if (leaf === null) return { leafTurnId: null };",
    'return text(leaf, TURN_ID_LIMIT) ? { leafTurnId: leaf } : "invalid";',
    "export function sameLeafAcrossPages(leaves: readonly (string | null)[]): boolean {",
    "return leaves.every(leaf => leaf === leaves[0]);",
)

PAGED_FRAGMENTS = (
    "/** 实际请求的页数；多于 1 页说明结果由多次读取拼成，不是同一时刻的快照。 */",
    "pages: number;",
    "if (next === null) return { items, truncated: false, pages: pages + 1 };",
    "return { items, truncated: true, pages: maxPages };",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, path: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{path} 缺少：" + "、".join(missing))
    return len(fragments)


def check_branch_pagination() -> int:
    paged = _read(PAGED)
    branches = _read(BRANCHES)
    pages = _read(PAGES)
    checked = _expect(PAGED_FRAGMENTS, paged, PAGED)
    checked += _expect(DRIFT_CHECK, branches, BRANCHES)
    checked += _expect(PAGE_LEAF_FRAGMENTS, pages, PAGES)

    # 顺序：两段列表拼完 → 逐页比较 → 旧内核回退复核 → 摘要读取。
    # 摘要读取失败不能掩盖放弃本次结果，回退复核也不能先于逐页比较。
    position = -1
    for marker in ("if (!uniqueTurnIds(turnPage.items))", "if (!sameLeafAcrossPages(pageLeaves.seen)) {",
                   "if (pageLeaves.missing && (endpointPage.pages > 1 || turnPage.pages > 1)) {",
                   "const context = await readContext(id);"):
        index = branches.find(marker)
        if index < 0 or index <= position:
            raise ValueError(f"位置核对步骤缺少或顺序变化：{marker}")
        position = index
        checked += 1

    compare_index = branches.find("if (!sameLeafAcrossPages(pageLeaves.seen)) {")
    context_index = branches.find("const context = await readContext(id);")
    aborted = branches[compare_index:context_index]
    # 发现位置变化后必须立即结束：不能让后续摘要读取写入旧 leaf 与端点。
    if "update(id, state => ({ ...state, loading: false, loaded: true" in aborted:
        raise ValueError("位置变化后仍继续写入分支状态")
    if aborted.count("update(id, { loading: false, error: LEAF_DRIFT });\n        return;") != 1 \
            or aborted.count("update(id, { loading: false, error: LEAF_DRIFT });\n          return;") != 1:
        raise ValueError("逐页比较与回退复核发现变化后都必须提示并立即返回")
    checked += 2
    # 回合页带位置时不再多发端点请求：复核只允许出现在「缺失且翻页」的回退分支里。
    if branches.count("const check = await listThreadBranches(id);") != 1:
        raise ValueError("端点复核只应出现一次")
    fallback_index = branches.find("if (pageLeaves.missing && (endpointPage.pages > 1 || turnPage.pages > 1)) {")
    if not fallback_index < branches.find("const check = await listThreadBranches(id);") < context_index:
        raise ValueError("端点复核必须位于旧内核回退分支内")
    checked += 1

    # 旧形态不再出现：只在翻页时复核、只比较首尾位置，或把缺失的位置当作空位置。
    for stale in ("if (endpointPage.pages > 1 || turnPage.pages > 1) {", "const firstLeaf = leafOfHead();",
                  "当前位置已被切换，本次列表可能混用两条分支"):
        if stale in branches:
            raise ValueError(f"仍保留只在翻页时复核的旧实现：{stale}")
        checked += 1
    if "truncated: false }" in paged or "truncated: true }" in paged:
        raise ValueError("分页结果仍缺少页数统计")
    checked += 1

    # 内核：回合集合与位置同源。位置必须在持锁读取条目之后、释放锁之前由同一份回合算出。
    session = _read(SESSION)
    application = _read(APPLICATION)
    checked += _expect(KERNEL_SESSION, session, SESSION)
    checked += _expect(KERNEL_HANDLER, application, APPLICATION)
    start = session.find("def list_branch_turns(")
    end = session.find("def branch_last_turn(", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少分支回合读取或其收尾标记")
    body = session[start:end]
    position = -1
    for marker in ("with self._lock:", "entries = self.read_entries(thread_id)",
                   "leaf = self._leaf_state(thread_id, entries, turns=active_turns)",
                   "with self._index.connection() as connection:", "selected = []"):
        index = body.find(marker)
        if index < 0 or index <= position:
            raise ValueError(f"分支回合读取步骤缺少或顺序变化：{marker}")
        position = index
        checked += 1
    if body.count("self.read_entries(thread_id)") != 1 or "self.read_leaf(" in body:
        raise ValueError("分支回合读取只能读取一次条目，不得另行读取位置")
    checked += 1
    handler_start = application.find("def on_turn_list(")
    handler_end = application.find("\n    @contextmanager", handler_start)
    if handler_start < 0 or handler_end < 0:
        raise ValueError(f"{APPLICATION} 缺少回合列表处理器或其收尾标记")
    handler = application[handler_start:handler_end]
    if "read_leaf(" in handler or "**result" in handler:
        raise ValueError("回合列表处理器不得另行读取位置，也不得透传未声明的字段")
    checked += 1

    # thread/read 非快照分支视图：四项都从处理器读到的同一份条目快照算出。
    checked += _expect(KERNEL_PINNED, session, SESSION)
    snapshot_start = application.find("            entries = self.sessions.read_entries_snapshot(thread_id)")
    snapshot_end = application.find("self._check_response_budget(result)", snapshot_start)
    if snapshot_start < 0 or snapshot_end < 0:
        raise ValueError(f"{APPLICATION} 缺少会话读取的条目快照或其收尾标记")
    thread_read = application[snapshot_start:snapshot_end]
    position = -1
    for marker in THREAD_READ:
        index = thread_read.find(marker)
        if index < 0 or index <= position:
            raise ValueError(f"会话读取的分支视图缺少同源步骤或顺序变化：{marker}")
        position = index
        checked += 1
    # 旧形态：不带快照的调用会在处理器内重新读取条目，位置变化后与 items 分属两条分支。
    for stale in ("self.sessions.branch_last_turn(thread_id)", "self.sessions.list_branch_turns(thread_id)",
                  "self.sessions.read_leaf(thread_id)\n"):
        if stale in thread_read:
            raise ValueError(f"会话读取的分支视图仍重新读取条目：{stale.strip()}")
        checked += 1
    # 带快照的位置读取不加锁重读；未带快照时保持原有持锁读取。
    for name, end_marker in (("def branch_last_turn(", "self._sync_thread(thread_id)"), ("def read_leaf(", "def branch_snapshot_projection(")):
        start = session.find(name)
        end = session.find(end_marker, start)
        if start < 0 or end < 0:
            raise ValueError(f"{SESSION} 缺少 {name} 或其收尾标记")
        part = session[start:end]
        pinned_index = part.find("if entries is not None:")
        if pinned_index < 0 or part.count("self.read_entries(thread_id)") != 1 \
                or not pinned_index < part.find("self.read_entries(thread_id)"):
            raise ValueError(f"{name} 带快照时不得重新读取条目")
        checked += 1
    return checked


def main() -> int:
    try:
        checked = check_branch_pagination()
    except ValueError as error:
        print(f"分支分页一致性核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支分页一致：{checked} 项页数统计、逐页位置核对与内核同源读取（回合页与会话读取）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())