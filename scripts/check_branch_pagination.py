#!/usr/bin/env python3
"""核对分支读取期间的位置变化不会被拼成一条列表。

分支端点与当前分支回合始终分多次读取，内核每次请求都按当下的 leaf 计算回合集合，
并在同一响应里报告该位置。两次请求之间位置变化时，各页分属不同位置，且不会出现
重复回合可供查重；界面必须逐页比较响应报告的位置（含单页读取与切走又切回），
不一致就放弃本次结果。旧内核的回合页不带位置时，翻页才回退到端点复核。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGED = "apps/desktop/src/renderer/src/data/pagedRead.ts"
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"
PAGES = "apps/desktop/src/renderer/src/data/branchPages.ts"

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
    return checked


def main() -> int:
    try:
        checked = check_branch_pagination()
    except ValueError as error:
        print(f"分支分页一致性核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支分页一致：{checked} 项页数统计与逐页位置核对")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())