#!/usr/bin/env python3
"""核对回合记录 `_turns` 的阶段合并、终态边界与内部字段保护。

`_turns` 把条目日志归并成回合表：`task_phase` 只在归属回合、合法阶段 / 状态 /
尝试次数与重启上限下合并，可选恢复原因与恢复策略有长度和枚举边界；回合首现时按
上一条终态记录的序号加一记下 `firstOrdinal`，持久载荷不得覆盖内部记账字段；终态
记录只保留首个 `boundaryOrdinal` 与 `completedAt`，并推进「上一条已结束回合」。
这张表驱动分支列表、冻结快照、fork 边界切分与列表索引，这里固定规则，避免重构后
边界切片拿到错误序号或内部字段泄漏到公开回合，并直接调用 `_turns` 核对归并行为。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore  # noqa: E402

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"回合记录行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _entry(turn_id, timestamp: str = "ts", **payload) -> dict:
    return {"type": "turn", "timestamp": timestamp,
            "payload": {"turnId": turn_id, **payload}}


def _phase(task_id, **payload) -> dict:
    return {"type": "task_phase", "payload": {
        "taskId": task_id, "ownerKind": "turn", "phase": "prepare",
        "status": "running", "attempt": 1, "restartLimit": 0, **payload}}


def _turns(entries: list[dict]) -> list[dict]:
    return SessionStore._turns(entries, "thread")


def _behavior_checks() -> int:
    checked = 0
    # 基本归并：首次创建记录 firstOrdinal / startedAt，后续推进序号与时间。
    checked += _expect_value(_turns([]), [], "空列表")
    checked += _expect_value(
        _turns([{"type": "queue", "payload": {}}]), [], "非回合条目忽略")
    checked += _expect_value(
        _turns([_entry("t1", status="running")]),
        [{"turnId": "t1", "threadId": "thread", "startedAt": "ts",
          "firstOrdinal": 0, "status": "running", "lastOrdinal": 0,
          "updatedAt": "ts"}], "基本回合")
    checked += _expect_value(
        _turns([_entry("t1", "ts1", status="running"),
                _entry("t1", "ts2", status="running")]),
        [{"turnId": "t1", "threadId": "thread", "startedAt": "ts1",
          "firstOrdinal": 0, "status": "running", "lastOrdinal": 1,
          "updatedAt": "ts2"}], "序号与时间推进")
    # 终态：首次记录边界与完成时间，后续终态不得覆盖，并推进上一条终态序号。
    checked += _expect_value(
        _turns([_entry("t1", "ts1", status="running"),
                _entry("t1", "ts2", status="completed")]),
        [{"turnId": "t1", "threadId": "thread", "startedAt": "ts1",
          "firstOrdinal": 0, "status": "completed", "lastOrdinal": 1,
          "updatedAt": "ts2", "boundaryOrdinal": 1, "completedAt": "ts2"}],
        "终态边界")
    checked += _expect_value(
        _turns([_entry("t1", "ts1", status="running"),
                _entry("t1", "ts2", status="completed"),
                _entry("t1", "ts3", status="interrupted")]),
        [{"turnId": "t1", "threadId": "thread", "startedAt": "ts1",
          "firstOrdinal": 0, "status": "interrupted", "lastOrdinal": 2,
          "updatedAt": "ts3", "boundaryOrdinal": 1, "completedAt": "ts2"}],
        "终态不覆盖边界")
    checked += _expect_value(
        [turn["firstOrdinal"] for turn in _turns([
            _entry("t1", "ts1", status="running"),
            _entry("t1", "ts2", status="completed"),
            _entry("t2", "ts3", status="running")])],
        [0, 2], "上一条终态后推进")
    # 持久载荷不能覆盖内部记账字段。
    protected = _turns([_entry("t1", "ts1", status="running"),
                        _entry("t1", "ts2", status="completed", firstOrdinal=50,
                               lastOrdinal=50, boundaryOrdinal=50)])[0]
    checked += _expect_value(
        (protected["firstOrdinal"], protected["lastOrdinal"],
         protected["boundaryOrdinal"]), (0, 1, 1), "内部字段不可覆盖")
    # 回合编号必须是受限标识符。
    for label, entry in (
        ("缺编号", {"type": "turn", "timestamp": "t", "payload": {}}),
        ("非字符串编号", _entry(1, status="running")),
        ("含空格编号", _entry("t 1", status="running")),
        ("短横线开头", _entry("-t1", status="running")),
        ("超长编号", _entry("t" * 129, status="running")),
    ):
        checked += _expect_value(_turns([entry]), [], label)
    checked += _expect_value(
        [turn["turnId"] for turn in _turns([_entry("T_1-2", status="running")])],
        ["T_1-2"], "合法复杂编号")
    # 阶段合并：合法字段写入回合，且不改变序号与更新时间。
    merged = _turns([_entry("t1", status="running"),
                     _phase("t1", recoveryReason="原因", resumePolicy="manual")])[0]
    checked += _expect_value(
        {key: merged[key] for key in ("taskPhase", "taskPhaseStatus", "taskAttempt",
                                      "taskRestartLimit", "taskRecoveryReason",
                                      "taskResumePolicy")},
        {"taskPhase": "prepare", "taskPhaseStatus": "running", "taskAttempt": 1,
         "taskRestartLimit": 0, "taskRecoveryReason": "原因",
         "taskResumePolicy": "manual"}, "阶段合并")
    checked += _expect_value(
        (merged["lastOrdinal"], merged["updatedAt"]), (0, "ts"), "阶段不影响序号")
    # 阶段边界：归属、阶段、状态、尝试次数与重启上限不合法时整条跳过。
    for label, entry in (
        ("ownerKind 非 turn", _phase("t1", ownerKind="thread")),
        ("未知回合", _phase("ghost")),
        ("payload 非对象", {"type": "task_phase", "payload": None}),
        ("阶段未知", _phase("t1", phase="unknown")),
        ("状态未知", _phase("t1", status="paused")),
        ("尝试为零", _phase("t1", attempt=0)),
        ("尝试超限", _phase("t1", attempt=1001)),
        ("尝试布尔", _phase("t1", attempt=True)),
        ("尝试字符串", _phase("t1", attempt="1")),
        ("重启为负", _phase("t1", restartLimit=-1)),
        ("重启超限", _phase("t1", restartLimit=33)),
        ("重启布尔", _phase("t1", restartLimit=True)),
    ):
        checked += _expect_value(
            "taskPhase" in _turns([_entry("t1", status="running"), entry])[0],
            False, label)
    # 可选恢复字段只在有界时写入。
    checked += _expect_value(
        "taskRecoveryReason" in _turns([
            _entry("t1", status="running"),
            _phase("t1", recoveryReason="x" * 257)])[0], False, "恢复原因超长忽略")
    checked += _expect_value(
        _turns([_entry("t1", status="running"),
                _phase("t1", recoveryReason="x" * 256)])[0]["taskRecoveryReason"],
        "x" * 256, "恢复原因等于上限")
    checked += _expect_value(
        "taskResumePolicy" in _turns([
            _entry("t1", status="running"),
            _phase("t1", resumePolicy="auto")])[0], False, "恢复策略非法忽略")
    # 阶段记录在回合首次出现之前无法归属。
    checked += _expect_value(
        _turns([_phase("t1"), _entry("t1", status="running")])[0].get("taskPhase"),
        None, "阶段在回合前跳过")
    # threadId 由归并参数收敛；缺失时间戳按空串记录。
    checked += _expect_value(
        _turns([_entry("t1", status="running", threadId="other")])[0]["threadId"],
        "thread", "threadId 收敛")
    checked += _expect_value(
        _turns([{"type": "turn",
                 "payload": {"turnId": "t1", "status": "running"}}])[0]["startedAt"],
        "", "缺失时间戳")
    checked += _expect_value(
        _turns([{"type": "turn",
                 "payload": {"turnId": "t1", "status": "completed"}}])[0]["completedAt"],
        "", "终态缺失时间戳")
    return checked


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
    return checked + _behavior_checks()


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
