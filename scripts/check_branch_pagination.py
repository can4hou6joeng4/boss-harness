#!/usr/bin/env python3
"""核对分支列表分页期间的位置变化不会被拼成一条列表。

分支端点与当前分支回合分多次读取，内核每次请求都按当下的 leaf 计算回合集合。
翻页期间位置被切换时，两页分属两条分支，且不会出现重复回合可供查重；界面必须
在拼接后复核 leaf，发现变化就放弃本次结果，而不是展示混用的列表。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGED = "apps/desktop/src/renderer/src/data/pagedRead.ts"
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"

DRIFT_CHECK = (
    "if (endpointPage.pages > 1 || turnPage.pages > 1) {",
    "const leafOfHead = (): string | null => head?.leafTurnId ?? null;",
    "const firstLeaf = leafOfHead();",
    "const check = await listThreadBranches(id);",
    "if (check.threadId !== id || !Array.isArray(check.endpoints)) {",
    "if ((check.leafTurnId ?? null) !== firstLeaf) {",
    "分支在读取期间发生变化：当前位置已被切换，本次列表可能混用两条分支，已放弃；请刷新后重试。",
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
    checked = _expect(PAGED_FRAGMENTS, paged, PAGED)
    checked += _expect(DRIFT_CHECK, branches, BRANCHES)

    # 复核必须发生在两段列表都拼完之后、摘要读取之前：摘要读取失败不能掩盖放弃本次结果。
    turn_index = branches.find("if (!uniqueTurnIds(turnPage.items))")
    check_index = branches.find(DRIFT_CHECK[0])
    context_index = branches.find("const context = await readContext(id);")
    if min(turn_index, check_index, context_index) < 0:
        raise ValueError("找不到回合校验、位置复核或摘要读取")
    if not turn_index < check_index < context_index:
        raise ValueError("位置复核必须位于回合校验之后、摘要读取之前")
    checked += 1

    # 发现位置变化后必须立即结束：不能让后续摘要读取写入旧 leaf 与端点。
    aborted = branches[check_index:context_index]
    if "await readContext(id);" in aborted or "update(id, state => ({ ...state, loading: false, loaded: true" in aborted:
        raise ValueError("位置变化后仍继续写入分支状态")
    checked += 1

    # 旧形态不再出现：页数未统计，或放弃分支后继续读取摘要。
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
    print(f"分支分页一致：{checked} 项页数统计与位置复核")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())