#!/usr/bin/env python3
"""核对被放弃分支的推导 `abandoned_branch`、摘要写入 `append_branch_summary`
与当前分支条目读取 `read_active_entries`。

切换分支后，界面与内核要说明哪些回合被放弃：`abandoned_branch` 以目标回合的祖先
链为界，从旧叶回溯到共同祖先（不含），再反转成时间顺序；`append_branch_summary`
只允许在请求摘要的叶记录仍是最后一条叶记录、且其后没有新回合或摘要时写入，长度
为 1 到 32000 字符，并在追加后执行提交回调与重建索引。这里固定这些规则，避免
重构后把摘要写到已经切换走的分支，或让放弃列表与共同祖先错位，并直接调用
`abandoned_branch` 核对祖先链、共同祖先与时间顺序。`read_active_entries` 按最后
一条叶记录回溯当前分支：损坏叶指针忽略、重复编号拒绝、会话级条目跨分支保留、
被放弃回合的条目与叶记录不返回；这里同时固定该投影并用临时 `SessionStore` 对照
无叶直返、切换分支、损坏叶与重复编号的行为。
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import (  # noqa: E402
    BRANCH_SUMMARY_ENTRY_TYPE,
    Entry,
    SessionStore,
)

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
ACTIVE_READER = (
    "def read_active_entries(self, thread_id: str) -> list[dict]:\n"
    "        return self._active_entries(self.read_entries(thread_id))"
)
# 当前分支条目：无叶记录原样返回 → 损坏叶指针跳过 → 重复编号拒绝 →
# 按追加顺序回溯 path → 条目按归属回合过滤、会话级条目跨分支保留、叶记录自身不返回。
ACTIVE_ENTRIES_ORDER = (
    "def _active_entries(cls, entries: list[dict]) -> list[dict]:",
    'if not any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):\n            return entries',
    'or records[target].get("type") != "turn"):',
    'raise ValueError("会话条目编号重复，无法投影分支")',
    'previous[entry["id"]] = tail',
    "cursor = previous[cursor]",
    'if kind == LEAF_ENTRY_TYPE:\n                return False',
    'return owner in included_turns if owner is not None else entry["id"] in path',
    "if kind in cls._BRANCH_INDEPENDENT_TYPES:",
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
            f"被放弃分支行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"被放弃分支行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"被放弃分支行为变化 {label}：期望 ValueError")


class _Store:
    def __init__(self, parent: dict[str, str | None], leaf: str | None) -> None:
        self._parent = parent
        self._leaf = leaf

    def read_entries(self, thread_id: str) -> list[dict]:
        return []

    def _turn_tree(self, entries: list[dict]):
        return dict(self._parent), list(self._parent)

    def _leaf_state(self, thread_id: str, entries: list[dict]):
        return {"leafTurnId": self._leaf}


def _abandoned(parent: dict[str, str | None], leaf: str | None,
               target: str | None) -> dict:
    return SessionStore.abandoned_branch(_Store(parent, leaf), "thread", target, entries=[])


def _behavior_checks() -> int:
    linear = {"t1": None, "t2": "t1", "t3": "t2"}
    checked = _expect_value(
        _abandoned(linear, "t3", "t2"),
        {"fromTurnId": "t3", "targetTurnId": "t2", "commonTurnId": "t2",
         "abandonedTurnIds": ["t3"]}, "线性回退一级")
    checked += _expect_value(
        _abandoned(linear, "t3", "t1"),
        {"fromTurnId": "t3", "targetTurnId": "t1", "commonTurnId": "t1",
         "abandonedTurnIds": ["t2", "t3"]}, "线性回退两级")
    checked += _expect_value(
        _abandoned(linear, "t3", None),
        {"fromTurnId": "t3", "targetTurnId": None, "commonTurnId": None,
         "abandonedTurnIds": ["t1", "t2", "t3"]}, "目标为空")
    checked += _expect_value(
        _abandoned(linear, "t3", "t3"),
        {"fromTurnId": "t3", "targetTurnId": "t3", "commonTurnId": "t3",
         "abandonedTurnIds": []}, "原地目标")
    branch = {"t1": None, "t2": "t1", "t3": "t1"}
    checked += _expect_value(
        _abandoned(branch, "t3", "t2"),
        {"fromTurnId": "t3", "targetTurnId": "t2", "commonTurnId": "t1",
         "abandonedTurnIds": ["t3"]}, "分叉共同祖先")
    checked += _expect_error(
        lambda: _abandoned(linear, "t3", "ghost"), "目标回合不存在", "目标不存在")
    checked += _expect_value(
        _abandoned(linear, None, None),
        {"fromTurnId": None, "targetTurnId": None, "commonTurnId": None,
         "abandonedTurnIds": []}, "无叶记录")
    checked += _expect_value(
        set(_abandoned(linear, "t3", "t1")),
        {"fromTurnId", "targetTurnId", "commonTurnId", "abandonedTurnIds"},
        "结果字段")
    checked += _expect_value(
        _abandoned({}, None, None),
        {"fromTurnId": None, "targetTurnId": None, "commonTurnId": None,
         "abandonedTurnIds": []}, "空树")
    deep = {"t1": None, "t2": "t1", "t3": "t2", "t4": "t3"}
    checked += _expect_value(
        _abandoned(deep, "t4", "t1"),
        {"fromTurnId": "t4", "targetTurnId": "t1", "commonTurnId": "t1",
         "abandonedTurnIds": ["t2", "t3", "t4"]}, "四级链")
    return checked


def _active_entries_checks() -> int:
    # 当前分支条目：无叶直返原顺序 → 切到较早回合只留该分支 → 会话级条目保留 →
    # 损坏叶指针忽略 → 有叶时重复编号拒绝，无叶时不报错。
    checked = 0
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("分支读取")["id"]
            store.append(thread_id, Entry(
                type="thread_info", id="info-1", payload={"title": "新标题"}))
            store.record_turn(thread_id, "turn-a", "completed")
            store.append(thread_id, Entry(
                type="item", id="item-a",
                payload={"kind": "userMessage", "turnId": "turn-a", "text": "A"}))
            store.record_turn(thread_id, "turn-b", "completed")
            store.append(thread_id, Entry(
                type="item", id="item-b",
                payload={"kind": "agentMessage", "turnId": "turn-b", "text": "B"}))
            # 被放弃分支上的会话级条目也要跨分支保留。
            store.append(thread_id, Entry(
                type="thread_info", id="info-2", payload={"title": "另一个标题"}))
            linear = store.read_active_entries(thread_id)
            if ([entry.get("id") for entry in linear if entry.get("type") != "turn"]
                    != ["info-1", "item-a", "item-b", "info-2"]):
                raise ValueError("无叶记录时必须保持原条目顺序")
            checked += 1
            if [entry.get("type") for entry in linear].count("turn") != 2:
                raise ValueError("无叶记录时必须返回全部回合")
            checked += 1
            store.set_leaf(thread_id, "turn-a")
            # 叶记录之后的摘要条目属于当前分支，必须沿 path 保留。
            store.append(thread_id, Entry(
                type=BRANCH_SUMMARY_ENTRY_TYPE, id="sum-1",
                payload={"summary": "摘要"}))
            active = store.read_active_entries(thread_id)
            if ([entry.get("id") for entry in active if entry.get("type") != "turn"]
                    != ["info-1", "item-a", "info-2", "sum-1"]):
                raise ValueError("切换分支后必须丢弃被放弃回合的条目并保留会话级条目")
            checked += 1
            if any(entry.get("type") == "leaf" for entry in active):
                raise ValueError("叶记录不得出现在当前分支条目中")
            checked += 1
            if [entry.get("type") for entry in active].count("turn") != 1:
                raise ValueError("切换分支后只保留目标回合")
            checked += 1
            store.append(thread_id, Entry(
                type="leaf", payload={"targetId": "turn-ghost"}))
            ghost = store.read_active_entries(thread_id)
            if [entry.get("id") for entry in ghost] != [entry.get("id") for entry in active]:
                raise ValueError("损坏叶指针必须被忽略并沿用上一个有效叶")
            checked += 1
            store.append(thread_id, Entry(
                type="item", id="item-a",
                payload={"kind": "userMessage", "turnId": "turn-a", "text": "重复"}))
            checked += _expect_error(
                lambda: store.read_active_entries(thread_id),
                "会话条目编号重复，无法投影分支", "重复编号")
        finally:
            store.close()
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("无叶重复")["id"]
            store.append(thread_id, Entry(
                type="item", id="dup-1", payload={"kind": "userMessage", "text": "一"}))
            store.append(thread_id, Entry(
                type="item", id="dup-1", payload={"kind": "userMessage", "text": "二"}))
            if len(store.read_active_entries(thread_id)) != 2:
                raise ValueError("无叶记录时重复编号必须原样返回")
            checked += 1
            empty_id = store.create("空分支")["id"]
            if store.read_active_entries(empty_id) != []:
                raise ValueError("空会话必须返回空列表")
            checked += 1
        finally:
            store.close()
    return checked


def check_branch_summary() -> int:
    source = _read(SESSION)
    abandoned = _region(source, "def abandoned_branch(")
    summary = _region(source, "def append_branch_summary(")
    active = _region(source, "def _active_entries(")
    checked = _ordered(ABANDONED_ORDER, abandoned, SESSION)
    checked += _ordered(SUMMARY_ORDER, summary, SESSION)
    checked += _ordered(ACTIVE_ENTRIES_ORDER, active, SESSION)
    if ACTIVE_READER not in source:
        raise ValueError(f"{SESSION} 缺少 read_active_entries 入口")
    checked += 1
    # 当前分支投影必须按追加顺序延续 tail，不信任写入方提供的 parentId。
    if active.count('tail = entry["id"]') != 1:
        raise ValueError(f"{SESSION} 的当前分支投影必须按追加顺序延续 tail")
    checked += 1
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
    return checked + _behavior_checks() + _active_entries_checks()


def main() -> int:
    try:
        checked = check_branch_summary()
    except ValueError as error:
        print(f"被放弃分支核对失败，{error}", file=sys.stderr)
        return 2
    print(f"被放弃分支一致：{checked} 项祖先、目标、摘要绑定、当前分支条目与行为校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
