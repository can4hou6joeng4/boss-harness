#!/usr/bin/env python3
"""核对被放弃分支的推导 `abandoned_branch` 与摘要写入 `append_branch_summary`。

切换分支后，界面与内核要说明哪些回合被放弃：`abandoned_branch` 以目标回合的祖先
链为界，从旧叶回溯到共同祖先（不含），再反转成时间顺序；`append_branch_summary`
只允许在请求摘要的叶记录仍是最后一条叶记录、且其后没有新回合或摘要时写入，长度
为 1 到 32000 字符，并在追加后执行提交回调与重建索引。这里固定这些规则，避免
重构后把摘要写到已经切换走的分支，或让放弃列表与共同祖先错位。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 放弃列表：读取条目与回合树 → 目标必须存在 → 目标祖先链 → 旧叶回溯到共同祖先 →
# 反转成时间顺序 → 固定结果字段。
ABANDONED_ORDER = (
    "def abandoned_branch(self, thread_id: str, target_turn_id: str | None,",
    "entries = self.read_entries(thread_id) if entries is None else entries",
    "parent, _ = self._turn_tree(entries)",
    'leaf = self._leaf_state(thread_id, entries)',
    "if target_turn_id is not None and target_turn_id not in parent:",
    'raise ValueError("目标回合不存在")',
    "ancestors: set[str] = set()",
    "cursor = target_turn_id",
    "ancestors.add(cursor)",
    "cursor = parent.get(cursor)",
    "abandoned: list[str] = []",
    'cursor = leaf["leafTurnId"]',
    "while cursor is not None and cursor not in ancestors:",
    "abandoned.append(cursor)",
    "cursor = parent.get(cursor)",
    "abandoned.reverse()",
    'return {"fromTurnId": leaf["leafTurnId"], "targetTurnId": target_turn_id,',
    '"commonTurnId": cursor, "abandonedTurnIds": abandoned}',
)
# 摘要写入：长度与内容 → 锁内读取 → 最后一条叶记录 → 其后无新回合或摘要 →
# 绑定叶记录追加 → 提交回调 → 重建索引。
SUMMARY_ORDER = (
    "def append_branch_summary(self, thread_id: str, leaf_entry_id: str, payload: dict,",
    "*, on_committed: Callable[[], None] | None = None) -> Entry:",
    'summary = payload.get("summary")',
    'if not isinstance(summary, str) or not summary.strip() or len(summary) > MAX_BRANCH_SUMMARY_CHARS:',
    'raise ValueError("被放弃分支摘要必须是 1 到 32000 字符")',
    "with self._lock, self._index.transaction() as connection:",
    "self.require_thread(thread_id)",
    "entries = self.read_entries(thread_id)",
    "index = next((position for position in range(len(entries) - 1, -1, -1)",
    'if entries[position].get("type") == LEAF_ENTRY_TYPE), None)',
    'if index is None or entries[index]["id"] != leaf_entry_id:',
    'raise ValueError("分支指针已变化，未写入被放弃分支摘要")',
    'if any(entry.get("type") in {"turn", BRANCH_SUMMARY_ENTRY_TYPE} for entry in entries[index + 1:]):',
    'raise ValueError("切换后已有新回合或摘要，未写入被放弃分支摘要")',
    'entry = Entry(type=BRANCH_SUMMARY_ENTRY_TYPE, payload={**payload, "leafEntryId": leaf_entry_id})',
    "self._append_line(self.path_for(thread_id), entry.to_dict())",
    "if on_committed is not None:",
    "on_committed()",
    "self._index_thread(thread_id, connection)",
    "return entry",
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


def check_branch_summary() -> int:
    source = _read(SESSION)
    abandoned = _region(source, "def abandoned_branch(")
    summary = _region(source, "def append_branch_summary(")
    checked = _ordered(ABANDONED_ORDER, abandoned, SESSION)
    checked += _ordered(SUMMARY_ORDER, summary, SESSION)
    # 放弃列表必须反转成时间顺序，且共同祖先来自回溯终点游标。
    if abandoned.count("abandoned.reverse()") != 1:
        raise ValueError(f"{SESSION} 的被放弃回合必须按时间顺序返回")
    checked += 1
    # 摘要只能绑定最后一条叶记录：反向扫描索引、不得正向扫描。
    if "range(len(entries) - 1, -1, -1)" not in summary or "range(len(entries))" in summary:
        raise ValueError(f"{SESSION} 的摘要绑定必须从最后一条叶记录反向扫描")
    checked += 1
    # 摘要只追加一次且携带请求的叶记录 id。
    if summary.count("self._append_line(") != 1 or summary.count('"leafEntryId": leaf_entry_id') != 1:
        raise ValueError(f"{SESSION} 的摘要必须只追加一次并绑定叶记录")
    checked += 1
    # 长度上限只出现一次，不能再放宽第二个上限。
    if summary.count("MAX_BRANCH_SUMMARY_CHARS") != 1:
        raise ValueError(f"{SESSION} 的摘要长度上限必须唯一")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_branch_summary()
    except ValueError as error:
        print(f"被放弃分支核对失败，{error}", file=sys.stderr)
        return 2
    print(f"被放弃分支一致：{checked} 项祖先、目标与摘要绑定校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
