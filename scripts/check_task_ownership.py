#!/usr/bin/env python3
"""核对任务读取的所有权、阶段绑定与恢复策略。

task_ownership.py 决定 task/read 的归属判定与恢复策略：标识符必须整串匹配，
快照有界，任务阶段只接受固定枚举，队列身份字段变化视为冲突，关系判定需要多重
独立证据，未知状态一律人工核对。检查固定源码结构，并用临时合成记录执行优先级、
关系与投影场景。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/task_ownership.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.task_ownership import (  # noqa: E402
    _input_digest,
    queue_snapshot,
    recovery_policy,
    resolve_compaction_relation,
    resolve_queue_relation,
    turn_snapshot,
    user_message_refs,
)

CONSTANT_FRAGMENTS = (
    # 数值与枚举按整行锚定：257 改成 2570 之类的后缀扩展不能因前缀相同而通过。
    r'_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")' + "\n",
    '_AUTO_COMPACTION_REASONS = frozenset({"threshold", "budget", "overflow"})\n',
    '_QUEUE_IDENTITY_FIELDS = ("kind", "inputDigest", "expectedTurnId", "clientUserMessageId")\n',
    '_TERMINAL_TURNS = frozenset({"completed", "interrupted", "blocked", "error"})\n',
    '_TASK_PHASES = frozenset({"admission", "prepare", "model_request", "tool_execution", "finish"})\n',
)
TURN_FRAGMENTS = (
    "limit: int = 257\n",
    "for offset in range(0, len(value), 4_096):\n",
    # 终态之后又出现 running 说明持久记录自相矛盾，必须标记重复而不是覆盖。
    'if (turn.get("status") in _TERMINAL_TURNS and status == "running"):',
    'if ("queueId" in payload and "queueId" in turn',
    'payload.get("ownerKind") == "turn"',
    "and 1 <= attempt <= 1_000 and type(restart_limit) is int\n",
    "and 0 <= restart_limit <= 32):\n",
    '"processExit", "terminalStateRecovered"',
    '{"manual", "closed"} else None',
    # 恢复策略只由内核在 finish 阶段按状态显式给出，缺省不推断。
    'expected_policy = "manual" if phase.get("status") == "interrupted" else "closed"',
    'phase.get("phase") == "finish" and phase.get("status") in _TERMINAL_TURNS',
)
QUEUE_FRAGMENTS = (
    "if queue_id not in states and len(states) >= limit:",
    'payload.get("kind") == "steering"',
    'payload.get("expectedTurnId") == target_turn_id',
    'payload.get("turnId") == receipt_turn_id',
    "input_digest = _input_digest(input_value)",
    "except UnicodeEncodeError:",
    "not isinstance(client_id, str)",
    're.fullmatch(r"[A-Za-z0-9_-]{1,128}", client_id) is None',
    # 同一条队列记录的身份字段在多份持久快照间变化时必须视为冲突。
    "if previous is not None and any(previous.get(key) != current.get(key)",
    "for key in _QUEUE_IDENTITY_FIELDS):",
)
USER_MESSAGE_FRAGMENTS = (
    "per_queue_limit: int = 2,\n",
    "revision_id_limit: int = 1_024\n",
    "if counts[queue_id] > per_queue_limit:",
    'refs[root]["revisionOverflow"] = True',
    'if source not in (None, "steering"):',
    # 引用只投影身份事实，正文永不进入任务读取。
    '"kind": "userMessage", "queueId": queue_id,',
    '"revisionOverflow": False})',
    "reference[key] = value",
)
RELATION_FRAGMENTS = (
    'turn_map = {turn["turnId"]: turn for turn in turns if isinstance(turn.get("turnId"), str)}',
    'turn_links = {turn["turnId"] for turn in turns if turn.get("queueId") == queue_id}',
    "if (identity_conflict or conflicting_item or duplicate_user_message or revision_conflict",
    "or len(turn_links | normal_user_links | steering_user_links) > 1):",
    "if candidates & duplicate_turns:",
    # delivered_as 需要队列回执、回合记录与用户消息引用三者一致。
    "if len(turn_links) == 1 and turn_links == normal_user_links:",
    '"relation": "delivered_as"',
    'ownership = "unassigned" if queue.get("status") in {"queued", "delivering"} else "root"',
    "if turn_links or normal_user_links:",
    "if (steering_user_links and steering_user_links != {target}) or (",
    'if queue.get("status") == "delivered" and steering_user_links != {target}:',
    '"relation": "targets"',
)
COMPACTION_FRAGMENTS = (
    'if job.get("threadId") != thread_id:',
    "if turn_id is None and reason is None:",
    '"ownership": "independent"',
    "if checkpoint_turn_id is not None and checkpoint_turn_id != turn_id:",
    "if turn_id in (duplicate_turns or set()):",
    "if len(matches) != 1:",
)
RECOVERY_FRAGMENTS = (
    # 缺失或损坏的状态与 unknown 一样不能按各分支默认终态处理。
    'if not isinstance(status, str) or status == "unknown":',
    "if runtime_owned:",
    'return "process_owned"',
    'if (kind == "turn" and persisted_policy == "manual" and status == "interrupted"):',
    'if (kind == "turn" and persisted_policy == "closed" and status in _TERMINAL_TURNS - {"interrupted"}):',
    'if status == "interrupted" or status == "running":',
    'return "queue_pending"',
    'if status in {"delivering", "paused"}:',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, '队列任务的持久状态缺失或非法时，`task/read` 返回字符串 `unknown` 与 `recoveryPolicy: "manual_review"`'),
    (USER_GUIDE, "回合 owner 可手动核对 `task/read` 持久记录：展示持久状态、归属、当前进程持有情况、恢复策略、任务阶段与已验证关联"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"任务读取所有权行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _follow_up(**overrides) -> dict:
    value = {"id": "q1", "kind": "followUp", "status": "delivered", "turnId": "t1"}
    value.update(overrides)
    return value


def _relation(result: dict, ownership: str, turn_id, relation, label: str) -> int:
    return _expect_value(
        (result["ownership"], result["turnId"], result["relation"]),
        (ownership, turn_id, relation), label,
    )


def _behavior_checks() -> int:
    checked = _expect_value(
        recovery_policy("turn", "unknown", runtime_owned=False), "manual_review", "未知状态"
    )
    checked += _expect_value(
        recovery_policy("turn", None, runtime_owned=False), "manual_review", "非字符串状态"
    )
    checked += _expect_value(
        recovery_policy("turn", "completed", runtime_owned=True), "process_owned", "进程持有"
    )
    checked += _expect_value(
        recovery_policy("turn", "unknown", runtime_owned=True), "manual_review", "未知优先"
    )
    checked += _expect_value(
        recovery_policy("turn", "interrupted", runtime_owned=False, persisted_policy="manual"),
        "manual_review", "手动策略",
    )
    checked += _expect_value(
        recovery_policy("turn", "completed", runtime_owned=False, persisted_policy="closed"),
        "closed", "关闭策略",
    )
    checked += _expect_value(
        recovery_policy("turn", "interrupted", runtime_owned=False, persisted_policy="closed"),
        "manual_review", "关闭不覆盖中断",
    )
    checked += _expect_value(
        recovery_policy("turn", "running", runtime_owned=False), "manual_review", "运行中回合"
    )
    checked += _expect_value(
        recovery_policy("turn", "completed", runtime_owned=False), "closed", "无持久终态"
    )
    checked += _expect_value(
        recovery_policy("queue", "queued", runtime_owned=False), "queue_pending", "排队待投递"
    )
    checked += _expect_value(
        recovery_policy("queue", "delivering", runtime_owned=False), "manual_review", "投递中"
    )
    checked += _expect_value(
        recovery_policy("queue", "delivered", runtime_owned=False), "closed", "队列终态"
    )
    checked += _expect_value(
        recovery_policy("task", "failed", runtime_owned=False), "manual_review", "任务失败"
    )
    checked += _expect_value(
        recovery_policy("task", "completed", runtime_owned=False), "closed", "任务完成"
    )

    checked += _expect_value(
        _input_digest("演示文本"), hashlib.sha256("演示文本".encode("utf-8")).hexdigest(), "输入摘要"
    )
    long_text = "甲" * 10_000
    checked += _expect_value(
        _input_digest(long_text), hashlib.sha256(long_text.encode("utf-8")).hexdigest(), "分块摘要"
    )

    job = {"threadId": "th1", "turnId": "t1", "reason": "threshold"}
    turns = [{"turnId": "t1"}]
    checked += _expect_value(
        resolve_compaction_relation(job, "other", turns),
        {"ownership": "conflict", "turnId": None}, "压缩线程冲突",
    )
    checked += _expect_value(
        resolve_compaction_relation({"threadId": "th1"}, "th1", turns),
        {"ownership": "independent", "turnId": None}, "压缩独立",
    )
    checked += _expect_value(
        resolve_compaction_relation({"threadId": "th1"}, "th1", turns, checkpoint_turn_id="t1"),
        {"ownership": "conflict", "turnId": None}, "压缩未知归属",
    )
    checked += _expect_value(
        resolve_compaction_relation({"threadId": "th1", "turnId": "t1", "reason": "other"}, "th1", turns),
        {"ownership": "unresolved", "turnId": None}, "压缩非法归属",
    )
    checked += _expect_value(
        resolve_compaction_relation(job, "th1", turns, checkpoint_turn_id="t2"),
        {"ownership": "conflict", "turnId": None}, "压缩检查点冲突",
    )
    checked += _expect_value(
        resolve_compaction_relation(job, "th1", turns, duplicate_turns={"t1"}),
        {"ownership": "conflict", "turnId": None}, "压缩重复回合",
    )
    checked += _expect_value(
        resolve_compaction_relation(job, "th1", []),
        {"ownership": "unresolved", "turnId": None}, "压缩回合缺失",
    )
    checked += _expect_value(
        resolve_compaction_relation(job, "th1", turns),
        {"ownership": "resolved", "turnId": "t1"}, "压缩已归属",
    )

    user_link = {"kind": "userMessage", "queueId": "q1", "turnId": "t1", "inferredTurnId": "t1"}
    delivered = _follow_up()
    checked += _relation(
        resolve_queue_relation(delivered, [{"turnId": "t1", "queueId": "q1"}], [user_link]),
        "resolved", "t1", "delivered_as", "投递一致",
    )
    checked += _relation(
        resolve_queue_relation(delivered, [{"turnId": "t1", "queueId": "q1"}], []),
        "unresolved", None, None, "投递缺用户消息",
    )
    checked += _relation(
        resolve_queue_relation({"id": "q1", "kind": "followUp", "status": "queued"}, [], []),
        "unassigned", None, None, "排队未绑定",
    )
    checked += _relation(
        resolve_queue_relation({"id": "q1", "kind": "followUp", "status": "delivered"}, [], []),
        "root", None, None, "投递根消息",
    )
    steering = {"id": "q1", "kind": "steering", "status": "delivering", "expectedTurnId": "t1"}
    checked += _relation(
        resolve_queue_relation(steering, [{"turnId": "t1"}], []),
        "resolved", "t1", "targets", "steering 目标",
    )
    delivered_steering = {**steering, "status": "delivered"}
    checked += _relation(
        resolve_queue_relation(delivered_steering, [{"turnId": "t1"}], []),
        "unresolved", None, None, "steering 缺用户链接",
    )
    steering_link = {
        "kind": "userMessage", "queueId": "q1", "turnId": "t1",
        "inferredTurnId": "t1", "source": "steering",
    }
    checked += _relation(
        resolve_queue_relation(delivered_steering, [{"turnId": "t1"}], [steering_link]),
        "resolved", "t1", "targets", "steering 已投递",
    )
    other_link = {**steering_link, "turnId": "t2", "inferredTurnId": "t2"}
    checked += _relation(
        resolve_queue_relation(delivered_steering, [{"turnId": "t1"}, {"turnId": "t2"}], [other_link]),
        "conflict", None, None, "steering 链接不一致",
    )
    checked += _relation(
        resolve_queue_relation({**steering, "expectedTurnId": "t9"}, [{"turnId": "t1"}], []),
        "unresolved", None, None, "steering 目标缺失",
    )
    checked += _relation(
        resolve_queue_relation(delivered, [{"turnId": "t1", "queueId": "q1"}], [steering_link]),
        "conflict", None, None, "followUp 携带 steering",
    )
    checked += _relation(
        resolve_queue_relation(
            delivered,
            [{"turnId": "t1", "queueId": "q1"}, {"turnId": "t2", "queueId": "q1"}], [],
        ),
        "conflict", None, None, "多链接",
    )
    checked += _relation(
        resolve_queue_relation(
            delivered, [{"turnId": "t1", "queueId": "q1"}], [user_link], duplicate_turns={"t1"}
        ),
        "conflict", None, None, "重复候选",
    )
    invalid_receipt = resolve_queue_relation({**delivered, "turnId": "bad id!"}, [], [])
    checked += _relation(invalid_receipt, "conflict", None, None, "非法回执")
    checked += _expect_value(invalid_receipt["candidates"], set(), "非法回执候选")
    checked += _relation(
        resolve_queue_relation(
            delivered, [{"turnId": "t1", "queueId": "q1"}], [user_link], identity_conflict=True
        ),
        "conflict", None, None, "身份冲突",
    )
    checked += _relation(
        resolve_queue_relation({**delivered, "turnId": "t2"}, [{"turnId": "t1", "queueId": "q1"}], [user_link]),
        "conflict", None, None, "回执不一致",
    )

    snapshot, duplicates, overflow = turn_snapshot(
        [{"type": "turn", "payload": {"turnId": "t1", "status": "running"}}]
    )
    checked += _expect_value(
        (snapshot, duplicates, overflow),
        ([{"turnId": "t1", "status": "running"}], set(), False), "回合快照",
    )
    snapshot, _, _ = turn_snapshot(
        [{"type": "turn", "payload": {"turnId": "t1", "status": "completed", "queueId": "q1"}}],
        turn_ids={"other"}, queue_ids={"q1"},
    )
    checked += _expect_value([item["turnId"] for item in snapshot], ["t1"], "队列过滤")
    snapshot, duplicates, _ = turn_snapshot([
        {"type": "turn", "payload": {"turnId": "t1", "status": "completed"}},
        {"type": "turn", "payload": {"turnId": "t1", "status": "running"}},
    ])
    checked += _expect_value((snapshot[0]["status"], duplicates), ("running", {"t1"}), "终态后运行")
    snapshot, duplicates, _ = turn_snapshot([
        {"type": "turn", "payload": {"turnId": "t1", "status": "running", "queueId": "q1"}},
        {"type": "turn", "payload": {"turnId": "t1", "status": "running", "queueId": "q2"}},
    ])
    checked += _expect_value(duplicates, {"t1"}, "队列标识变化")
    snapshot, _, overflow = turn_snapshot(
        [{"type": "turn", "payload": {"turnId": f"t{index}", "status": "running"}} for index in range(3)],
        limit=2,
    )
    checked += _expect_value((len(snapshot), overflow), (2, True), "回合溢出")
    snapshot, _, _ = turn_snapshot([
        {"type": "turn", "payload": {"turnId": "t1", "status": "completed"}},
        {"type": "task_phase", "payload": {
            "ownerKind": "turn", "taskId": "t1", "phase": "finish", "status": "completed",
            "attempt": 2, "restartLimit": 3, "recoveryReason": "processExit", "resumePolicy": "closed",
        }},
    ])
    checked += _expect_value(
        (snapshot[0].get("taskPhase"), snapshot[0].get("taskAttempt"), snapshot[0].get("taskRestartLimit"),
         snapshot[0].get("taskRecoveryReason"), snapshot[0].get("taskResumePolicy")),
        ("finish", 2, 3, "processExit", "closed"), "阶段绑定",
    )

    states, conflicts, overflow = queue_snapshot([
        {"type": "queue", "payload": {"id": "q1", "kind": "steering", "status": "queued", "input": "消息"}},
        {"type": "queue", "payload": {"id": "q2", "kind": "followUp", "status": "delivered", "input": "x"}},
    ], queue_ids={"q1"})
    checked += _expect_value(
        (sorted(states), conflicts, overflow, states["q1"]["inputDigest"]),
        (["q1"], set(), False, hashlib.sha256("消息".encode("utf-8")).hexdigest()), "队列快照选择",
    )
    states, _, _ = queue_snapshot(
        [{"type": "queue", "payload": {"id": "q3", "kind": "steering", "status": "queued",
                                       "expectedTurnId": "t1", "input": "x"}}],
        queue_ids=set(), target_turn_id="t1",
    )
    checked += _expect_value(sorted(states), ["q3"], "steering 目标选择")
    states, _, _ = queue_snapshot(
        [{"type": "queue", "payload": {"id": "q4", "kind": "followUp", "status": "delivered",
                                       "turnId": "t1", "input": "x"}}],
        queue_ids=set(), receipt_turn_id="t1",
    )
    checked += _expect_value(sorted(states), ["q4"], "回执选择")
    states, conflicts, _ = queue_snapshot([
        {"type": "queue", "payload": {"id": "q1", "kind": "followUp", "status": "delivered", "input": "a"}},
        {"type": "queue", "payload": {"id": "q1", "kind": "followUp", "status": "delivered", "input": "b"}},
    ], queue_ids={"q1"})
    checked += _expect_value(conflicts, {"q1"}, "队列身份冲突")
    states, conflicts, _ = queue_snapshot(
        [{"type": "queue", "payload": {"id": "q1", "kind": "other", "status": "unknown", "input": "x"}}],
        queue_ids={"q1"},
    )
    checked += _expect_value(conflicts, {"q1"}, "队列字段冲突")
    states, _, overflow = queue_snapshot(
        [{"type": "queue", "payload": {"id": f"q{index}", "kind": "followUp",
                                       "status": "delivered", "input": "x"}} for index in range(3)],
        queue_ids={"q0", "q1", "q2"}, limit=2,
    )
    checked += _expect_value((len(states), overflow), (2, True), "队列溢出")
    states, conflicts, _ = queue_snapshot(
        [{"type": "queue", "payload": {"id": "q1", "kind": "followUp", "status": "delivered",
                                       "input": "甲\ud800"}}],
        queue_ids={"q1"},
    )
    checked += _expect_value((states["q1"]["inputDigest"], conflicts), (None, {"q1"}), "输入非 UTF-8")

    refs, duplicates, conflicts = user_message_refs([
        {"type": "item", "id": "m1", "payload": {
            "kind": "userMessage", "queueId": "q1", "turnId": "t1", "source": "steering", "input": "秘密",
        }},
    ], {"q1"})
    checked += _expect_value(
        (refs[0]["inferredTurnId"], "input" in refs[0], refs[0]["revisionOverflow"]),
        ("t1", False, False), "用户消息引用",
    )
    refs, duplicates, _ = user_message_refs([
        {"type": "item", "id": f"m{index}", "payload": {
            "kind": "userMessage", "queueId": "q1", "turnId": "t1",
        }} for index in range(3)
    ], {"q1"}, per_queue_limit=2)
    checked += _expect_value((len(refs), duplicates), (2, {"q1"}), "每队列上限")
    refs, _, conflicts = user_message_refs([
        {"type": "item", "id": "m1", "payload": {"kind": "userMessage", "queueId": "q1", "turnId": "t1"}},
        {"type": "item", "id": "m2", "payload": {"kind": "userMessage", "queueId": "q2", "turnId": "t2"}},
    ], {"q1", "q2"}, revision_id_limit=1)
    checked += _expect_value((refs[1]["revisionOverflow"], "q2" in conflicts), (True, True), "修订上限")
    refs, _, _ = user_message_refs([
        {"type": "item", "id": "m1", "payload": {"kind": "userMessage", "queueId": "q1"}},
        {"type": "turn", "payload": {"turnId": "t1", "status": "running"}},
    ], {"q1"})
    checked += _expect_value(refs[0]["inferredTurnId"], "t1", "推断回合")
    return checked


def check_task_ownership() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(TURN_FRAGMENTS, module, MODULE)
    checked += _expect(QUEUE_FRAGMENTS, module, MODULE)
    checked += _expect(USER_MESSAGE_FRAGMENTS, module, MODULE)
    checked += _expect(RELATION_FRAGMENTS, module, MODULE)
    checked += _expect(COMPACTION_FRAGMENTS, module, MODULE)
    checked += _expect(RECOVERY_FRAGMENTS, module, MODULE)
    # 未知状态优先于进程持有与持久策略：先判 unknown，才轮到 process_owned。
    checked += _ordered(
        (
            'if not isinstance(status, str) or status == "unknown":',
            "if runtime_owned:",
            'if (kind == "turn" and persisted_policy == "manual" and status == "interrupted"):',
        ),
        module,
        MODULE,
    )
    # 标识符必须整串匹配；search 会把包含非法片段的损坏标识当成合法。
    if "_IDENTIFIER.search(" in module:
        raise ValueError(f"{MODULE} 的标识符必须整串匹配")
    # 用户消息引用只投影身份事实，任何正文键都会把会话原文带进任务读取。
    if '"input": ' in module:
        raise ValueError(f"{MODULE} 的用户消息引用不得投影正文")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_task_ownership()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"任务读取所有权核对失败，{error}", file=sys.stderr)
        return 2
    print(f"任务读取所有权一致：{checked} 项归属、阶段与恢复防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
