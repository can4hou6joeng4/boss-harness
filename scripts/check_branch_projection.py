#!/usr/bin/env python3
"""核对分支投影 `_active_entries` 的叶指针、归属与跨分支保留规则。

分支投影决定所有分支读取看到的条目集合：位置由持久 leaf 记录选择，路径按追加时
的投影尾部推导而不信任写入方 parentId；损坏的叶指针按缺失处理，重复条目编号严格
拒绝；迟到修订跟随所属回合，附件 / 会话信息 / 队列跨分支保留，回合、阶段、工具
批次、上下文编辑与摘要检查点按归属回合筛选。这里固定这些规则，避免重构后分支
读取、续接预检与 fork 静默拿到错误的条目集合。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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
    except ValueError as error:
        print(f"分支投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支投影一致：{checked} 项叶指针、归属与跨分支保留校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
