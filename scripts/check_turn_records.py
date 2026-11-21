#!/usr/bin/env python3
"""核对回合记录 `_turns` 的阶段合并、终态边界与内部字段保护。

`_turns` 把条目日志归并成回合表：`task_phase` 只在归属回合、合法阶段 / 状态 /
尝试次数与重启上限下合并，可选恢复原因与恢复策略有长度和枚举边界；回合首现时按
上一条终态记录的序号加一记下 `firstOrdinal`，持久载荷不得覆盖内部记账字段；终态
记录只保留首个 `boundaryOrdinal` 与 `completedAt`，并推进「上一条已结束回合」。
这张表驱动分支列表、冻结快照、fork 边界切分与列表索引，这里固定规则，避免重构后
边界切片拿到错误序号或内部字段泄漏到公开回合。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 归并顺序：阶段合并 → 合法标识符 → 首次创建与 firstOrdinal → 载荷过滤内部字段 →
# 首条终态记录的边界与完成时间 → 推进上一条终态序号。
TURN_ORDER = (
    "def _turns(entries: list[dict], thread_id: str) -> list[dict]:",
    "turns: dict[str, dict] = {}",
    "previous_end = -1",
    'if entry.get("type") == "task_phase":',
    'task_id = payload.get("taskId")',
    "turn = turns.get(task_id) if isinstance(task_id, str) else None",
    'phase, status = payload.get("phase"), payload.get("status")',
    'attempt, restart_limit = payload.get("attempt"), payload.get("restartLimit")',
    'if (payload.get("ownerKind") == "turn" and turn is not None',
    "and isinstance(phase, str) and phase in _TASK_PHASES",
    'and isinstance(status, str) and status in _TERMINAL | {"running"}',
    "and type(attempt) is int and 1 <= attempt <= 1_000",
    "and type(restart_limit) is int and 0 <= restart_limit <= 32):",
    "turn.update(taskPhase=phase, taskPhaseStatus=status, taskAttempt=attempt,",
    "taskRestartLimit=restart_limit)",
    'if (isinstance(payload.get("recoveryReason"), str)',
    'and len(payload["recoveryReason"]) <= 256):',
    'if (isinstance(payload.get("resumePolicy"), str)',
    'and payload["resumePolicy"] in {"manual", "closed"}):',
    'if entry.get("type") != "turn":',
    'turn_id = payload.get("turnId")',
    "if not isinstance(turn_id, str) or not _IDENTIFIER.fullmatch(turn_id):",
    "turn = turns.get(turn_id)",
    "if turn is None:",
    '"firstOrdinal": previous_end + 1}',
    'first_ordinal = turn["firstOrdinal"]',
    "turn.update({key: value for key, value in payload.items()",
    "if key not in _TURN_INTERNAL_FIELDS})",
    "turn.update(threadId=thread_id, turnId=turn_id, firstOrdinal=first_ordinal,",
    'lastOrdinal=ordinal, updatedAt=entry.get("timestamp", ""))',
    'if isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL:',
    'turn.setdefault("boundaryOrdinal", ordinal)',
    'turn.setdefault("completedAt", entry.get("timestamp", ""))',
    "previous_end = ordinal",
    "return list(turns.values())",
)
INTERNAL_FIELDS = '_TURN_INTERNAL_FIELDS = frozenset({"firstOrdinal", "lastOrdinal", "boundaryOrdinal"})'


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


def _indent(text: str, fragment: str) -> int:
    for line in text.splitlines():
        if fragment in line:
            return len(line) - len(line.lstrip(" "))
    raise ValueError(f"{SESSION} 缺少行：{fragment}")


def check_turn_records() -> int:
    source = _read(SESSION)
    start = source.index("def _turns(")
    end = source.find("\n    def ", start + 1)
    turns = source[start:] if end < 0 else source[start:end]
    checked = _ordered(TURN_ORDER, turns, SESSION)
    if INTERNAL_FIELDS not in source:
        raise ValueError(f"{SESSION} 的内部回合字段必须保持 firstOrdinal / lastOrdinal / boundaryOrdinal")
    checked += 1
    # 公开回合必须过滤内部字段：内部序号泄漏到快照或分叉会破坏边界切分。
    public_start = source.index("def _public_turn(")
    public_end = source.find("\n    def ", public_start + 1)
    public = source[public_start:] if public_end < 0 else source[public_start:public_end]
    if "if key not in _TURN_INTERNAL_FIELDS}" not in public or "dict(turn)" in public:
        raise ValueError(f"{SESSION} 的公开回合必须过滤内部记账字段")
    checked += 1
    # 终态边界与「上一条终态序号」必须在终态分支内，不能提前到任意回合记录。
    terminal = 'if isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL:'
    guard = _indent(turns, terminal)
    for fragment in ('turn.setdefault("boundaryOrdinal"', 'turn.setdefault("completedAt"', "previous_end = ordinal"):
        if _indent(turns, fragment) <= guard:
            raise ValueError(f"{SESSION} 的 {fragment} 必须位于终态分支内")
        checked += 1
    # 首条终态记录命中：boundaryOrdinal 与 completedAt 都只能用 setdefault。
    if turns.count("turn.setdefault(") != 2 or turns.count("turn[" + '"boundaryOrdinal"]') != 0:
        raise ValueError(f"{SESSION} 的终态边界必须保留首条记录且不被覆盖")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_turn_records()
    except ValueError as error:
        print(f"回合记录核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合记录一致：{checked} 项阶段合并、终态边界与内部字段保护校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
