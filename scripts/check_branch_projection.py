#!/usr/bin/env python3
"""核对分支投影 `_active_entries` 的叶指针、归属与跨分支保留规则。

分支投影决定所有分支读取看到的条目集合：位置由持久 leaf 记录选择，路径按追加时
的投影尾部推导而不信任写入方 parentId；损坏的叶指针按缺失处理，重复条目编号严格
拒绝；迟到修订跟随所属回合，附件 / 会话信息 / 队列跨分支保留，回合、阶段、工具
批次、上下文编辑与摘要检查点按归属回合筛选。这里固定这些规则，避免重构后分支
读取、续接预检与 fork 静默拿到错误的条目集合；并用合成条目实际执行分支投影。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import SessionStore  # noqa: E402

# 投影顺序：无叶早退 → 逐条记下追加时尾部 → 损坏叶指针沿用上一个有效叶 →
# 重复编号拒绝 → 回溯路径 → 按归属筛选。
PROJECTION_ORDER = (
    "def _active_entries(cls, entries: list[dict]) -> list[dict]:",
    'if not any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):',
    "return entries",
    'if entry.get("type") == LEAF_ENTRY_TYPE:',
    "tail = target",
    'if entry["id"] in records:',
    'raise ValueError("会话条目编号重复，无法投影分支")',
    'previous[entry["id"]] = tail',
    "tail = entry[\"id\"]",
    "cursor = previous[cursor]",
    "def keep(entry: dict) -> bool:",
    "if kind == LEAF_ENTRY_TYPE:",
    "return False",
    'return owner in included_turns if owner is not None else entry["id"] in path',
    'if entry["id"] in path:',
    "if kind in cls._BRANCH_INDEPENDENT_TYPES:",
    'if kind in {"turn", "task_phase", "tool_batch"}:',
    'if kind == "context_edit":',
    'if kind == "context_checkpoint":',
)
# 叶指针容错：目标缺失、不是字符串、未知或不是回合时按缺失处理，不整段失败。
LEAF_MARK = (
    'target = payload.get("targetId") if isinstance(payload, dict) else None',
    "if target is not None and (not isinstance(target, str) or target not in records",
    'or records[target].get("type") != "turn"):',
)
# 跨分支保留的会话级状态：附件、会话信息、队列。
BRANCH_TYPES = '_BRANCH_INDEPENDENT_TYPES = frozenset({"attachment", "thread_info", "queue"})'


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


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


def _record(kind: str, entry_id: str, payload: dict | None = None, *,
            parent: str | None = None) -> dict:
    return {"type": kind, "id": entry_id, "parentId": parent,
            "timestamp": "2026-01-01T00:00:00Z", "payload": {} if payload is None else payload}


def _ids(entries: list[dict]) -> list[str]:
    return [entry["id"] for entry in entries]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"分支投影行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _behavior_checks() -> int:
    checked = 0
    empty: list[dict] = []
    checked += _expect_value(SessionStore._active_entries(empty) is empty, True,
                             "无叶原样返回空表")
    branch = [
        _record("item", "u1", {"kind": "userMessage", "turnId": "t1", "text": "第一"}),
        _record("turn", "t1", {"turnId": "t1", "status": "completed"}),
        _record("item", "a1", {"kind": "assistantMessage", "turnId": "t1", "text": "回答"}),
        _record("leaf", "l1", {"targetId": "t1"}),
        _record("item", "u2", {"kind": "userMessage", "turnId": "t2", "text": "第二"}),
        _record("turn", "t2", {"turnId": "t2", "status": "running"}),
        _record("item", "a2", {"kind": "assistantMessage", "turnId": "t2", "text": "回答二"},
                parent="a1"),
        _record("leaf", "l2", {"targetId": "t1"}),
    ]
    snapshot = list(branch)
    checked += _expect_value(_ids(SessionStore._active_entries(branch)),
                             ["u1", "t1", "a1"], "切换到首分支")
    checked += _expect_value(branch, snapshot, "投影不修改输入")
    no_leaf = branch[:3]
    checked += _expect_value(SessionStore._active_entries(no_leaf) is no_leaf, True,
                             "无叶返回同一列表")

    extras = branch + [
        _record("attachment", "att", {"digest": "a" * 64}),
        _record("thread_info", "info", {"title": "标题"}),
        _record("queue", "q1", {"id": "q1"}),
        _record("task_phase", "p1", {"taskId": "t1", "ownerKind": "turn",
                                     "phase": "prepare", "status": "completed"}),
        _record("task_phase", "p2", {"taskId": "t2", "ownerKind": "turn",
                                     "phase": "prepare", "status": "running"}),
        _record("tool_batch", "b1", {"turnId": "t1"}),
        _record("tool_batch", "b2", {"turnId": "t2"}),
        _record("context_edit", "e1", {"targetItemId": "a1"}),
        _record("context_edit", "e2", {"targetItemId": "a2"}),
        _record("context_checkpoint", "c1", {"throughTurnId": "t1"}),
        _record("context_checkpoint", "c2", {"throughTurnId": "t2"}),
        _record("note", "n1", {"text": "未知"}),
        _record("leaf", "l3", {"targetId": "t1"}),
    ]
    checked += _expect_value(_ids(SessionStore._active_entries(extras)),
                             ["u1", "t1", "a1", "att", "info", "q1", "p1", "b1", "e1", "c1"],
                             "跨分支保留与归属筛选")

    revisions = branch + [
        _record("item", "r1", {"kind": "toolCall", "revises": "a1", "result": "结果"}),
        _record("item", "r2", {"kind": "toolCall", "revises": "a2", "result": "结果"}),
        _record("item", "r3", {"kind": "toolCall", "revises": "a2", "turnId": "t1",
                               "result": "结果"}),
    ]
    checked += _expect_value(_ids(SessionStore._active_entries(revisions)),
                             ["u1", "t1", "a1", "r1", "r3"], "迟到修订跟随 owner")

    closed = [
        _record("item", "u1", {"kind": "userMessage"}),
        _record("turn", "t1", {"turnId": "t1", "status": "completed"}),
        _record("leaf", "l1", {"targetId": "t1"}),
        _record("item", "orphan", {"kind": "assistantMessage"}),
        _record("leaf", "l2", {"targetId": "t1"}),
    ]
    checked += _expect_value(_ids(SessionStore._active_entries(closed)), ["u1", "t1"],
                             "无归属条目丢弃")

    for index, target in enumerate((123, "missing", "a1")):
        damaged = branch + [_record("leaf", f"bad{index}", {"targetId": target})]
        checked += _expect_value(_ids(SessionStore._active_entries(damaged)),
                                 ["u1", "t1", "a1"], f"损坏叶沿用有效叶 {target!r}")
    checked += _expect_value(_ids(SessionStore._active_entries(
        branch + [_record("leaf", "none", {})])), [], "缺目标叶回到空路径")
    checked += _expect_value(_ids(SessionStore._active_entries(
        branch + [{"type": "leaf", "id": "none2", "parentId": None,
                   "timestamp": "2026-01-01T00:00:00Z", "payload": None}])),
        [], "非对象载荷回到空路径")
    checked += _expect_value(_ids(SessionStore._active_entries(
        [_record("leaf", "only", {"targetId": None})])), [], "仅叶记录为空投影")

    duplicate = [
        _record("item", "u1", {"kind": "userMessage"}),
        _record("turn", "t1", {"turnId": "t1", "status": "running"}),
        _record("leaf", "l", {"targetId": "t1"}),
        _record("item", "u1", {"kind": "userMessage"}),
    ]
    try:
        SessionStore._active_entries(duplicate)
    except ValueError as error:
        checked += _expect_value(str(error), "会话条目编号重复，无法投影分支",
                                 "重复编号拒绝")
    else:
        raise ValueError("分支投影行为变化 重复编号：期望拒绝，实际未抛出")

    other = [
        _record("item", "u1", {"kind": "userMessage"}),
        _record("turn", "t1", {"turnId": "t1", "status": "completed"}),
        _record("item", "a1", {"kind": "assistantMessage"}),
        _record("leaf", "l1", {"targetId": "t1"}),
        _record("item", "u2", {"kind": "userMessage"}),
        _record("turn", "t2", {"turnId": "t2", "status": "running"}),
        _record("item", "a2", {"kind": "assistantMessage"}),
        _record("leaf", "l2", {"targetId": "t2"}),
    ]
    checked += _expect_value(_ids(SessionStore._active_entries(other)),
                             ["u1", "t1", "a1", "u2", "t2", "a2"], "切换到第二分支")
    return checked


def check_branch_projection() -> int:
    source = _read(SESSION)
    start = source.index("def _active_entries(")
    end = source.find("\n    def ", start + 1)
    projection = source[start:] if end < 0 else source[start:end]
    checked = _ordered(PROJECTION_ORDER, projection, SESSION)
    checked += _expect(LEAF_MARK, projection, SESSION)
    if BRANCH_TYPES not in source:
        raise ValueError(f"{SESSION} 的分支无关条目集合必须保持 attachment / thread_info / queue")
    checked += 1
    # 不信任写入方 parentId：路径只能由追加时的投影尾部推导。
    if '.get("parentId")' in projection or '["parentId"]' in projection:
        raise ValueError(f"{SESSION} 的分支投影不得读取写入方 parentId")
    checked += 1
    # 损坏叶指针必须按缺失处理：校验块之后是 continue，而不是 raise。
    leaf_block = projection[projection.index("if target is not None and"):projection.index("tail = target")]
    raises = [line for line in leaf_block.splitlines() if line.strip().startswith("raise")]
    if raises or "continue" not in leaf_block:
        raise ValueError(f"{SESSION} 的损坏叶指针必须按缺失处理")
    checked += 1
    # 无叶记录原样返回：不得复制或重排条目。
    if projection.count("return entries") != 1:
        raise ValueError(f"{SESSION} 的无叶投影必须原样返回")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_branch_projection()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"分支投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支投影一致：{checked} 项叶指针、归属与跨分支保留校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
