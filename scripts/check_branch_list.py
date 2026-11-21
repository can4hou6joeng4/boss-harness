#!/usr/bin/env python3
"""核对分支列表 `list_branches` 的端点推导、预览与分页规则。

分支列表把条目推导成界面「分支」弹窗的端点：同一次加锁读取条目、回合树、位置、
回合与归属；用户消息按归属回合取首个预览并按上限截断；端点按「无子回合」与首次
出现顺序排列，翻页键是 (位置, turnId)；每个端点还要算出深度、最近分叉点、分支
首回合、是否包含当前叶、是否为叶与是否可选（仅终态回合）。这里固定这些规则，
避免重构后分支弹窗显示错误分支、漏页或允许选择运行中的回合。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 端点推导顺序：参数与游标 → 同一把锁内读取 → 首个用户消息预览 → 子回合 /
# 位置 / 当前叶路径 → 端点与翻页过滤 → 逐端点深度、分叉点与可选性 → 下一页游标。
LIST_ORDER = (
    "def list_branches(self, thread_id: str, *, cursor: str | None = None, limit: int = 50) -> dict:",
    "_limit(limit)",
    "self.path_for(thread_id)",
    'scope = {"threadId": thread_id, "view": "endpoints"}',
    'key = _read_page_cursor(cursor, "branches", scope)',
    "if len(key) != 2 or type(key[0]) is not int or key[0] < 0:",
    'raise ValueError("分支分页游标无效")',
    '_identifier(key[1], "turnId")',
    "with self._lock:",
    "entries = self.read_entries(thread_id)",
    "parent, order = self._turn_tree(entries)",
    'leaf = self._leaf_state(thread_id, entries)',
    'turns = {turn["turnId"]: turn for turn in self._turns(entries, thread_id)}',
    'owners = self._item_owners([entry for entry in entries if entry.get("type") != LEAF_ENTRY_TYPE])',
    'if (entry.get("type") == "item" and isinstance(payload, dict)',
    'and payload.get("kind") == "userMessage" and isinstance(payload.get("text"), str)):',
    "if isinstance(owner, str) and owner not in previews:",
    'text = " ".join(payload["text"].split())',
    'previews[owner] = text[:MAX_BRANCH_PREVIEW_CHARS] + ("…" if len(text) > MAX_BRANCH_PREVIEW_CHARS else "")',
    "children.setdefault(parent[turn_id], []).append(turn_id)",
    "position = {turn_id: index for index, turn_id in enumerate(order)}",
    'cursor_turn = leaf["leafTurnId"]',
    "cursor_turn = parent.get(cursor_turn)",
    "endpoints = [turn_id for turn_id in order if turn_id not in children]",
    "endpoints = [turn_id for turn_id in endpoints if (position[turn_id], turn_id) > (key[0], key[1])]",
    "page = endpoints[:limit]",
    "while parent[path[-1]] is not None:",
    "path.reverse()",
    "fork_point = next((ancestor for ancestor in reversed(path[:-1])",
    "if len(children.get(ancestor, [])) > 1), None)",
    '"depth": len(path), "forkTurnId": fork_point, "branchTurnId": branch_turn,',
    '"containsLeaf": leaf["leafTurnId"] in path,',
    '"isLeaf": leaf["leafTurnId"] == turn_id,',
    '"selectable": isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL})',
    'next_cursor = (_page_cursor("branches", scope, [position[page[-1]], page[-1]])',
    "if len(endpoints) > limit else None)",
    '"turnCount": len(order), "endpoints": result, "nextCursor": next_cursor}',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_branch_list() -> int:
    source = _read(SESSION)
    start = source.index("def list_branches(")
    end = source.find("\n    def ", start + 1)
    listing = source[start:] if end < 0 else source[start:end]
    checked = _ordered(LIST_ORDER, listing, SESSION)
    # 条目、回合树、位置、回合与归属必须在同一把锁内读取，预览循环不能回到锁外。
    locked = listing[listing.index("with self._lock:"):listing.index("previews: dict[str, str] = {}")]
    for fragment in ("entries = self.read_entries(thread_id)", "self._turn_tree(entries)",
                     "self._leaf_state(thread_id, entries)", "self._turns(entries, thread_id)",
                     "self._item_owners("):
        if fragment not in locked:
            raise ValueError(f"{SESSION} 的分支列表必须在同一把锁内读取 {fragment}")
        checked += 1
    # 首条预览只在尚无预览时写入，截断上限出现两次（比较与切片）。
    if listing.count("owner not in previews") != 1:
        raise ValueError(f"{SESSION} 的分支预览必须保留归属回合的首条用户消息")
    checked += 1
    if listing.count("MAX_BRANCH_PREVIEW_CHARS") != 2:
        raise ValueError(f"{SESSION} 的分支预览必须按上限截断并加省略号")
    checked += 1
    # 翻页必须按键过滤而不是切片截断；下一页游标只在仍有剩余时生成。
    if "endpoints = endpoints[" in listing:
        raise ValueError(f"{SESSION} 的分支翻页不得用切片截断替代游标过滤")
    checked += 1
    if "if len(endpoints) > limit else None)" not in listing:
        raise ValueError(f"{SESSION} 的下一页游标必须只在仍有剩余端点时生成")
    checked += 1
    # 包含当前叶与是否为叶是两种判定，不能互相替代。
    if listing.count('leaf["leafTurnId"] in path') != 1 or listing.count('leaf["leafTurnId"] == turn_id') != 1:
        raise ValueError(f"{SESSION} 的 containsLeaf 与 isLeaf 必须分别判定")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_branch_list()
    except ValueError as error:
        print(f"分支列表核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支列表一致：{checked} 项端点、预览、分叉点与分页校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
