#!/usr/bin/env python3
"""核对条目归属 `_item_owners` 与回合树 `_turn_tree` 的推导规则。

两者是分支与历史判定的共同输入：归属决定迟到修订、旧记录工具调用回退、显式
回合号优先级、无归属条目挂起与活动回合的清空；回合树决定父回合、首次出现顺序
与条目尾部。分支投影、fork 前缀选择、分支列表与上下文读取都依赖这些结果，这里
固定规则，避免重构后静默改变归属或父回合链，并直接调用两个入口核对归属与父回合。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore  # noqa: E402

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"条目归属行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _turn(turn_id: object, status: object = "running") -> dict:
    return {
        "type": "turn",
        "id": f"turn:{turn_id}",
        "payload": {"turnId": turn_id, "status": status},
    }


def _item(entry_id: str, **payload: object) -> dict:
    return {"type": "item", "id": entry_id, "payload": payload}


def _behavior_checks() -> int:
    owners = SessionStore._item_owners
    checked = _expect_value(
        owners([_item("i1", kind="message", turnId="turn-a")]),
        {"i1": "turn-a"}, "显式回合")
    checked += _expect_value(
        owners([_turn("turn-a"), _item("i1", kind="message")]),
        {"i1": "turn-a"}, "活动回合")
    checked += _expect_value(
        owners([_item("i1", kind="message"), _turn("turn-a")]),
        {"i1": "turn-a"}, "挂起收割")
    checked += _expect_value(
        owners([_turn("turn-a"), _item("i1", kind="message"),
                _turn("turn-a", "completed"), _turn("turn-b"),
                _item("i2", kind="message", revises="i1")]),
        {"i1": "turn-a", "i2": "turn-a"}, "修订继承")
    checked += _expect_value(
        owners([_turn("turn-a"), _item("i1", kind="message"),
                _turn("turn-a", "completed"), _turn("turn-b"),
                {"type": "item", "id": "i2", "parentId": "i1",
                 "payload": {"kind": "toolCall", "status": "completed"}}]),
        {"i1": "turn-a", "i2": "turn-a"}, "工具调用回退")
    checked += _expect_value(
        owners([_item("i1", kind="message", turnId="turn-a"),
                {"type": "item", "id": "i2", "parentId": "i1",
                 "payload": {"kind": "toolCall", "status": "running"}}]),
        {"i1": "turn-a", "i2": None}, "running 工具调用不回退")
    checked += _expect_value(
        owners([_item("same", kind="message", turnId="turn-a"),
                _item("same", kind="message", turnId="turn-b")]),
        {"same": "turn-a"}, "重复编号保留首个")
    checked += _expect_value(
        owners([_item("i1", kind="message")]), {"i1": None}, "无归属挂起")
    checked += _expect_value(
        owners([_turn("turn-a"), _item("i1", kind="message"),
                _turn("turn-a", "completed"), _item("i2", kind="message")]),
        {"i1": "turn-a", "i2": None}, "终态清空")
    checked += _expect_value(
        owners([_item("i1", kind="message"), _turn("bad id!"),
                _item("i2", kind="message")]),
        {"i1": None, "i2": None}, "非法回合号跳过")
    checked += _expect_value(
        owners([_turn("turn-a"), _turn("turn-a", "completed"),
                _item("i2", kind="message"), _turn("turn-a")]),
        {"i2": None}, "重复回合不重复收割")
    checked += _expect_value(
        owners([_turn("turn-a"), _turn("turn-b"),
                _turn("turn-a", "completed"), _item("i1", kind="message")]),
        {"i1": "turn-b"}, "终态不误清其它回合")

    tree = SessionStore._turn_tree
    checked += _expect_value(
        tree([_turn("t1"), _turn("t2"), _turn("t3")]),
        ({"t1": None, "t2": "t1", "t3": "t2"}, ["t1", "t2", "t3"]), "父回合链")
    checked += _expect_value(
        tree([_turn("t1"), _item("i1", kind="message", turnId="t1"), _turn("t2")]),
        ({"t1": None, "t2": "t1"}, ["t1", "t2"]), "条目推进尾部")
    checked += _expect_value(
        tree([_turn("t1"),
              {"type": "task_phase", "id": "p1", "payload": {"turnId": "t1"}},
              {"type": "tool_batch", "id": "b1", "payload": {"taskId": "t1"}},
              _turn("t2")]),
        ({"t1": None, "t2": "t1"}, ["t1", "t2"]), "任务与批次归属")
    checked += _expect_value(
        tree([_item("i1", kind="message", turnId="ghost"), _turn("t1")]),
        ({"t1": None}, ["t1"]), "未知归属跳过")
    checked += _expect_value(
        tree([_turn("t1"), _turn("t1"), _turn("t2")]),
        ({"t1": None, "t2": "t1"}, ["t1", "t2"]), "重复回合不重复入列")
    checked += _expect_value(
        tree([_turn("bad id!"), _turn("t1")]),
        ({"t1": None}, ["t1"]), "非法回合号不进入树")
    return checked


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
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_item_ownership()
    except ValueError as error:
        print(f"条目归属核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目归属与回合树一致：{checked} 项修订、回退、显式归属、父回合与行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
