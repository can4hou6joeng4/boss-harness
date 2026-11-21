#!/usr/bin/env python3
"""核对分支指针 `set_leaf` 的目标校验、收尾条件与叶记录一致性。

切换分支会写一条持久 leaf 记录，之后所有分支读取、fork 与续接都以它选择分支。
这里固定写入路径的规则：目标必须是已结束回合的最后一条记录；会话里不能还有未结束
的回合、运行中条目或未决审批；已在目标位置时幂等返回不写记录；写入前先用候选条目
模拟投影并要求位置与目标一致；叶记录必须带 `targetId` / `turnId` / `fromTurnId`，
只追加一次并重建索引。避免重构后允许切到运行中回合、写入重复叶记录或让记录与
回合边界不一致。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 写入顺序：参数校验 → 锁与索引 → 幂等 → 目标回合终态 → 会话收尾 → 候选模拟 →
# 追加一次 → 重建索引 → 返回位置。
LEAF_ORDER = (
    "def set_leaf(self, thread_id: str, turn_id: str | None, *, _with_entry_id: bool = False) -> dict:",
    '_identifier(turn_id, "turnId")',
    "with self._lock, self._index.transaction() as connection:",
    "self.require_thread(thread_id)",
    "self._index_thread(thread_id, connection)",
    "entries = self.read_entries(thread_id)",
    "current = self._leaf_state(thread_id, entries)",
    'if current["leafTurnId"] == turn_id and (turn_id is not None or current["activeTurnCount"] == 0):',
    'return {**current, "changed": False}',
    'records = [entry for entry in entries if entry.get("type") == "turn"',
    'and entry["payload"].get("turnId") == turn_id]',
    'if (not records or not isinstance(records[-1]["payload"].get("status"), str)',
    'or records[-1]["payload"].get("status") not in _TERMINAL):',
    'raise ValueError("仅可把分支指针移到已经结束的回合")',
    'target_id = records[-1]["id"]',
    "all_turns = self._turns(entries, thread_id)",
    'raise ValueError("会话仍有未结束的回合，不能切换分支")',
    "for item in self._project_items(thread_id, entries):",
    'raise ValueError("会话中仍有未收尾条目或审批，不能切换分支")',
    "entry = Entry(type=LEAF_ENTRY_TYPE, parent_id=target_id,",
    'payload={"targetId": target_id, "turnId": turn_id,',
    '"fromTurnId": current["leafTurnId"]})',
    "candidate = entries + [entry.to_dict()]",
    "state = self._leaf_state(thread_id, candidate)",
    'if state["leafTurnId"] != turn_id:',
    'raise ValueError("分支指针目标与回合边界不一致")',
    "self._append_line(self.path_for(thread_id), entry.to_dict())",
    "self._index_thread(thread_id, connection)",
    'result = {**state, "changed": True}',
    "if _with_entry_id:",
    'result["_leafEntryId"] = entry.id',
    "return result",
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


def check_set_leaf() -> int:
    source = _read(SESSION)
    start = source.index("def set_leaf(")
    end = source.find("\n    def ", start + 1)
    leaf = source[start:] if end < 0 else source[start:end]
    checked = _ordered(LEAF_ORDER, leaf, SESSION)
    # 叶记录只追加一次，且必须带完整来源信息。
    if leaf.count("entry.to_dict()") != 2 or leaf.count("self._append_line(") != 1:
        raise ValueError(f"{SESSION} 的分支指针必须只追加一条叶记录")
    checked += 1
    for fragment in ('"targetId": target_id', '"turnId": turn_id', '"fromTurnId": current["leafTurnId"]'):
        if fragment not in leaf:
            raise ValueError(f"{SESSION} 的叶记录缺少 {fragment}")
        checked += 1
    # 目标必须是最后一条同名回合记录，不能退回首条或任意一条。
    if "records[-1]" not in leaf or "records[0]" in leaf:
        raise ValueError(f"{SESSION} 的分支指针目标必须取最后一条回合记录")
    checked += 1
    # 幂等分支必须返回 changed False，成功分支必须返回 changed True。
    if leaf.count('"changed": False') != 1 or leaf.count('"changed": True') != 1:
        raise ValueError(f"{SESSION} 的分支指针幂等与成功结果必须区分 changed")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_set_leaf()
    except ValueError as error:
        print(f"分支指针核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支指针一致：{checked} 项目标校验、收尾与叶记录一致性校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
