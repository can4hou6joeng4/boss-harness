#!/usr/bin/env python3
"""核对条目归属 `_item_owners` 与回合树 `_turn_tree` 的推导规则。

两者是分支与历史判定的共同输入：归属决定迟到修订、旧记录工具调用回退、显式
回合号优先级、无归属条目挂起与活动回合的清空；回合树决定父回合、首次出现顺序
与条目尾部。分支投影、fork 前缀选择、分支列表与上下文读取都依赖这些结果，这里
固定规则，避免重构后静默改变归属或父回合链。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 归属顺序：修订目标 → 非 running 工具调用的 parentId 回退 → 显式 turnId 优先 →
# 重复编号保留首个 → 无归属挂起 → 下一个新回合收割 → running / 终态维护活动回合。
OWNER_ORDER = (
    "def _item_owners(entries: list[dict]) -> dict[str, str | None]:",
    "owners: dict[str, str | None] = {}",
    "pending: list[str] = []",
    "seen_turns: set[str] = set()",
    "active: str | None = None",
    'if entry.get("type") == "item":',
    'target = _record_id(payload.get("revises"))',
    'if not target and payload.get("kind") == "toolCall" and payload.get("status") != "running":',
    'target = _record_id(entry.get("parentId"))',
    'explicit = _record_id(payload.get("turnId"))',
    "owner = explicit if explicit is not None else owners.get(target) or active",
    'if entry["id"] not in owners:',
    'owners[entry["id"]] = owner',
    'pending.append(entry["id"])',
    'elif entry.get("type") == "turn":',
    "if not isinstance(turn_id, str) or not _IDENTIFIER.fullmatch(turn_id):",
    "if turn_id not in seen_turns:",
    "for entry_id in pending:",
    "owners[entry_id] = turn_id",
    "pending.clear()",
    "seen_turns.add(turn_id)",
    'if payload.get("status") == "running":',
    "active = turn_id",
    'and payload.get("status") in _TERMINAL and active == turn_id):',
    "active = None",
    "return owners",
)

# 回合树顺序：先经投影校验 → 归属与 known 回合集合 → 逐条按追加时尾部推导 →
# 自父回合记为无 → 非回合条目推进尾部并记录条目尾部。
TREE_ORDER = (
    "def _turn_tree(cls, entries: list[dict]) -> tuple[dict[str, str | None], list[str]]:",
    "cls._active_entries(entries)",
    "owners = cls._item_owners([entry for entry in entries if entry.get(\"type\") != LEAF_ENTRY_TYPE])",
    'known = {entry["payload"].get("turnId") for entry in entries if entry.get("type") == "turn"',
    'and _IDENTIFIER.fullmatch(entry["payload"]["turnId"])}',
    "parent: dict[str, str | None] = {}",
    "order: list[str] = []",
    "record_turn: dict[str, str | None] = {}",
    "tail: str | None = None",
    "tail = record_turn.get(target) if isinstance(target, str) else None",
    'if kind == "turn":',
    'owner = payload.get("turnId")',
    'elif kind == "item":',
    'owner = owners.get(entry["id"])',
    'elif kind in {"task_phase", "tool_batch"}:',
    'owner = payload.get("turnId", payload.get("taskId"))',
    "if isinstance(owner, str) and owner in known:",
    "if owner not in parent:",
    "parent[owner] = tail if tail != owner else None",
    "order.append(owner)",
    "tail = owner",
    'record_turn[entry["id"]] = tail',
    "return parent, order",
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


def _region(source: str, marker: str) -> str:
    start = source.index(marker)
    end = source.find("\n    def ", start + 1)
    return source[start:] if end < 0 else source[start:end]


def check_item_ownership() -> int:
    source = _read(SESSION)
    owners = _region(source, "def _item_owners(")
    tree = _region(source, "def _turn_tree(")
    checked = _ordered(OWNER_ORDER, owners, SESSION)
    checked += _ordered(TREE_ORDER, tree, SESSION)
    # 唯一允许读取 parentId 的位置是旧版工具调用回退：不得再多读或从 payload 读。
    if owners.count('entry.get("parentId")') != 1 or 'payload.get("parentId")' in owners:
        raise ValueError(f"{SESSION} 的归属推导只允许非 running 工具调用回退读取 parentId")
    checked += 1
    # 回合树必须恰好校验一次投影，且不信任任何写入方 parentId。
    if tree.count("cls._active_entries(entries)") != 1 or "parentId" in tree:
        raise ValueError(f"{SESSION} 的回合树必须先经投影校验且不读取写入方 parentId")
    checked += 1
    # 重复编号保留首个归属：守卫必须在写入 owners 之前出现且只有一次。
    if owners.count('if entry["id"] not in owners:') != 1:
        raise ValueError(f"{SESSION} 的归属推导必须保留首个重复编号归属")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_item_ownership()
    except ValueError as error:
        print(f"条目归属核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目归属与回合树一致：{checked} 项修订、回退、显式归属与父回合推导校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
