#!/usr/bin/env python3
"""对照任务归属投影与关系判定的行为口径。

`task_ownership.py` 是 `task/read` 的只读投影层：`turn_snapshot` 归并回合与
任务阶段并按查询集合过滤，`queue_snapshot` 投影队列身份并标记冲突，
`user_message_refs` 只投影用户消息的身份事实，`resolve_queue_relation` /
`resolve_compaction_relation` 用多重证据判定归属，`recovery_policy` 给出恢复
策略。本脚本直接调用这些纯函数做行为对照，并固定关系判定的优先级顺序；
不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/task_ownership.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.task_ownership import (  # noqa: E402
    recovery_policy,
    resolve_compaction_relation,
    resolve_queue_relation,
    queue_snapshot,
    turn_snapshot,
    user_message_refs,
)

QUEUE_RELATION_ORDER = (
    'queue_id = queue.get("id")',
    'turn_links = {turn["turnId"] for turn in turns if turn.get("queueId") == queue_id}',
    "for item in user_items:",
    'receipt_turn = queue.get("turnId")',
    "candidates = turn_links | normal_user_links | steering_user_links",
    "if (identity_conflict or conflicting_item or duplicate_user_message or revision_conflict",
    "if candidates & duplicate_turns:",
    'if kind == "followUp":',
    'if kind == "steering":',
    'target = queue.get("expectedTurnId")',
)

COMPACTION_RELATION_ORDER = (
    'if job.get("threadId") != thread_id:',
    'turn_id, reason = job.get("turnId"), job.get("reason")',
    "if turn_id is None and reason is None:",
    'return {"ownership": "independent", "turnId": None}',
    "if checkpoint_turn_id is not None and checkpoint_turn_id != turn_id:",
    "if turn_id in (duplicate_turns or set()):",
    'matches = [turn for turn in turns if turn.get("turnId") == turn_id]',
    "if len(matches) != 1:",
)

RECOVERY_POLICY_ORDER = (
    'if not isinstance(status, str) or status == "unknown":',
    'return "manual_review"',
    "if runtime_owned:",
    'return "process_owned"',
    'if (kind == "turn" and persisted_policy == "manual" and status == "interrupted"):',
    'if (kind == "turn" and persisted_policy == "closed" and status in _TERMINAL_TURNS - {"interrupted"}):',
    'if kind == "queue":',
    'if status == "queued":',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"{label} 投影结果变化：期望 {expected!r}，实际 {actual!r}")
    return 1


def _turn(turn_id: str, status: str, **extra) -> dict:
    return {"type": "turn", "payload": {"turnId": turn_id, "status": status, **extra}}


def _phase(task_id: str, phase: str, status: str, **extra) -> dict:
    return {"type": "task_phase", "payload": {
        "ownerKind": "turn", "taskId": task_id, "phase": phase, "status": status,
        "attempt": 1, "restartLimit": 0, **extra}}


def _queue(queue_id: str, **extra) -> dict:
    return {"type": "queue", "payload": {"id": queue_id, **extra}}


def _item(item_id: str, **payload) -> dict:
    return {"id": item_id, "type": "item", "payload": payload}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def check_task_relation() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    checked = _ordered(QUEUE_RELATION_ORDER, _function(tree, source, "resolve_queue_relation"),
                       "resolve_queue_relation")
    checked += _ordered(COMPACTION_RELATION_ORDER,
                        _function(tree, source, "resolve_compaction_relation"),
                        "resolve_compaction_relation")
    checked += _ordered(RECOVERY_POLICY_ORDER, _function(tree, source, "recovery_policy"),
                        "recovery_policy")
    # 行为：回合按查询集合与队列关联过滤，非法状态与标识被跳过。
    entries = [
        _turn("turn-a", "completed"),
        _turn("turn-b", "running"),
        _turn("turn-c", "running", queueId="queue-1"),
        {"type": "turn", "payload": {"turnId": "bad id", "status": "running"}},
        {"type": "turn", "payload": {"turnId": "turn-d", "status": "unknown"}},
        {"type": "turn", "payload": "not-a-dict"},
    ]
    turns, duplicates, overflow = turn_snapshot(entries, turn_ids={"turn-a"},
                                                queue_ids={"queue-1"})
    checked += _expect([turn["turnId"] for turn in turns], ["turn-a", "turn-c"], "回合过滤")
    checked += _expect((duplicates, overflow), (set(), False), "回合过滤标记")
    # 行为：终态后 running 视为重复，running 后终态不标记。
    turns, duplicates, _ = turn_snapshot([
        _turn("turn-a", "completed"), _turn("turn-a", "running")])
    checked += _expect((turns[0]["status"], duplicates), ("running", {"turn-a"}), "终态后运行")
    turns, duplicates, _ = turn_snapshot([
        _turn("turn-a", "running"), _turn("turn-a", "completed")])
    checked += _expect((turns[0]["status"], duplicates), ("completed", set()), "运行后终态")
    # 行为：queueId 变化与非法值标记重复，非法值不写入投影。
    turns, duplicates, _ = turn_snapshot([
        _turn("turn-a", "running", queueId="queue-1"),
        _turn("turn-a", "running", queueId="queue-2")])
    checked += _expect((turns[0]["queueId"], duplicates), ("queue-2", {"turn-a"}), "队列身份变化")
    turns, duplicates, _ = turn_snapshot([_turn("turn-a", "running", queueId=5)])
    checked += _expect(("queueId" in turns[0], duplicates), (False, {"turn-a"}), "非法队列身份")
    turns, duplicates, _ = turn_snapshot([_turn("turn-a", "running", queueId="bad id")])
    checked += _expect(("queueId" in turns[0], duplicates), (False, {"turn-a"}), "非法队列标识")
    # 行为：回合数量达到上限后不再收新回合，重复回合仍可更新。
    turns, _, overflow = turn_snapshot([
        _turn("turn-a", "running"), _turn("turn-b", "running"), _turn("turn-c", "running")],
        limit=2)
    checked += _expect(([turn["turnId"] for turn in turns], overflow),
                       (["turn-a", "turn-b"], True), "回合上限")
    turns, duplicates, overflow = turn_snapshot([
        _turn("turn-a", "running"), _turn("turn-b", "running"), _turn("turn-a", "completed")],
        limit=2)
    checked += _expect((turns[0]["status"], duplicates, overflow),
                       ("completed", set(), False), "上限内重复回合")
    # 行为：阶段按最新记录归并，恢复原因与策略只认固定枚举。
    turns, _, _ = turn_snapshot([
        _turn("turn-a", "interrupted"),
        _phase("turn-a", "model_request", "interrupted", attempt=2, restartLimit=3,
               recoveryReason="processExit", resumePolicy="manual"),
    ])
    checked += _expect(
        {key: turns[0].get(key) for key in ("taskPhase", "taskPhaseStatus", "taskAttempt",
                                            "taskRestartLimit", "taskRecoveryReason",
                                            "taskResumePolicy")},
        {"taskPhase": "model_request", "taskPhaseStatus": "interrupted", "taskAttempt": 2,
         "taskRestartLimit": 3, "taskRecoveryReason": "processExit",
         "taskResumePolicy": None}, "阶段归并")
    turns, _, _ = turn_snapshot([
        _turn("turn-a", "completed"),
        _phase("turn-a", "finish", "completed", recoveryReason="terminalStateRecovered",
               resumePolicy="closed"),
    ])
    checked += _expect(turns[0].get("taskResumePolicy"), "closed", "终态收尾策略")
    turns, _, _ = turn_snapshot([
        _turn("turn-a", "completed"),
        _phase("turn-a", "finish", "completed", resumePolicy="manual"),
    ])
    checked += _expect(turns[0].get("taskResumePolicy"), None, "策略与状态不符")
    turns, _, _ = turn_snapshot([
        _turn("turn-a", "running"),
        _phase("turn-a", "finish", "running", attempt=0),
        _phase("turn-a", "finish", "running", restartLimit=33),
        _phase("turn-a", "finish", "running", recoveryReason="unknown"),
    ])
    checked += _expect((turns[0].get("taskAttempt"), turns[0].get("taskRestartLimit"),
                        turns[0].get("taskRecoveryReason"), turns[0].get("taskPhase")),
                       (1, 0, None, "finish"), "阶段非法字段")
    turns, _, _ = turn_snapshot([
        _turn("turn-a", "running"),
        {"type": "task_phase", "payload": {"ownerKind": "queue", "taskId": "turn-a",
                                           "phase": "finish", "status": "running",
                                           "attempt": 1, "restartLimit": 0}},
        _phase("turn-b", "finish", "running"),
    ], turn_ids={"turn-a"})
    checked += _expect(turns[0].get("taskPhase"), None, "阶段归属过滤")
    # 行为：队列按直接集合、目标回合与回执回合三条来源选中。
    entries = [_queue("queue-1", kind="followUp", status="queued", input="你好")]
    states, conflicts, overflow = queue_snapshot(entries, queue_ids={"queue-1"})
    checked += _expect(states, {"queue-1": {
        "id": "queue-1", "kind": "followUp", "status": "queued", "turnId": None,
        "expectedTurnId": None, "clientUserMessageId": None, "inputDigest": _digest("你好"),
    }}, "队列投影")
    checked += _expect((conflicts, overflow), (set(), False), "队列投影标记")
    entries = [_queue("queue-1", kind="steering", status="queued", input="x",
                      expectedTurnId="turn-a")]
    states, _, _ = queue_snapshot(entries, queue_ids={"queue-2"}, target_turn_id="turn-a")
    checked += _expect(set(states), {"queue-1"}, "目标回合选中")
    entries = [_queue("queue-1", kind="followUp", status="delivered", input="x",
                      turnId="turn-b")]
    states, _, _ = queue_snapshot(entries, queue_ids={"queue-2"}, receipt_turn_id="turn-b")
    checked += _expect(set(states), {"queue-1"}, "回执回合选中")
    # 行为：身份字段变化与非法值标记冲突，非法值不进入投影。
    entries = [
        _queue("queue-1", kind="followUp", status="queued", input="a"),
        _queue("queue-1", kind="followUp", status="queued", input="b"),
    ]
    states, conflicts, _ = queue_snapshot(entries, queue_ids={"queue-1"})
    checked += _expect((states["queue-1"]["inputDigest"], conflicts),
                       (_digest("b"), {"queue-1"}), "队列摘要冲突")
    states, conflicts, _ = queue_snapshot(
        [_queue("queue-1", kind="other", status="queued", input=5)],
        queue_ids={"queue-1"})
    checked += _expect((states["queue-1"]["kind"], states["queue-1"]["status"],
                        states["queue-1"]["inputDigest"], conflicts),
                       (None, "queued", None, {"queue-1"}), "队列枚举与摘要")
    states, conflicts, _ = queue_snapshot(
        [_queue("queue-1", kind="followUp", status="paused", input="x",
                turnId="bad id", expectedTurnId="bad id", clientUserMessageId="bad id")],
        queue_ids={"queue-1"})
    checked += _expect((states["queue-1"]["turnId"], states["queue-1"]["expectedTurnId"],
                        states["queue-1"]["clientUserMessageId"], conflicts),
                       (None, None, None, {"queue-1"}), "队列标识冲突")
    states, _, overflow = queue_snapshot([
        _queue("queue-1", kind="followUp", status="queued", input="a"),
        _queue("queue-2", kind="followUp", status="queued", input="b"),
    ], queue_ids={"queue-1", "queue-2"}, limit=1)
    checked += _expect((set(states), overflow), ({"queue-1"}, True), "队列上限")
    # 行为：用户消息引用按每队列上限与修订上限截断，只投影身份字段。
    entries = [
        _item("item-1", kind="userMessage", queueId="queue-1", turnId="turn-a"),
        _item("item-2", kind="userMessage", queueId="queue-1", turnId="turn-a"),
        _item("item-3", kind="userMessage", queueId="queue-1", turnId="turn-a"),
    ]
    refs, duplicates, conflicts = user_message_refs(entries, {"queue-1"})
    checked += _expect(([ref["id"] for ref in refs], duplicates, conflicts),
                       (["item-1", "item-2"], {"queue-1"}, set()), "用户消息上限")
    checked += _expect(refs[0], {"kind": "userMessage", "queueId": "queue-1",
                                 "turnId": "turn-a", "id": "item-1",
                                 "inferredTurnId": "turn-a", "revisionOverflow": False},
                       "用户消息引用")
    refs, duplicates, conflicts = user_message_refs(entries, {"queue-1"}, per_queue_limit=1)
    checked += _expect((len(refs), duplicates), (1, {"queue-1"}), "用户消息条数上限")
    # 行为：修订链更新根引用，非法字段被归一化并标记冲突。
    entries = [
        _item("item-1", kind="userMessage", queueId="queue-1", turnId="turn-a"),
        _item("item-2", revises="item-1", turnId="turn-b"),
    ]
    refs, duplicates, conflicts = user_message_refs(entries, {"queue-1"})
    checked += _expect((len(refs), refs[0]["turnId"], duplicates, conflicts),
                       (1, "turn-b", set(), set()), "修订更新")
    entries = [
        _item("item-1", kind="userMessage", queueId="queue-1", turnId="turn-a"),
        _item("item-2", revises="item-1", kind="other", source="other", turnId="bad id"),
    ]
    refs, _, conflicts = user_message_refs(entries, {"queue-1"})
    checked += _expect((refs[0]["kind"], refs[0]["source"], refs[0]["turnId"], conflicts),
                       ("invalid", "invalid", "", {"queue-1"}), "修订非法字段")
    entries = [
        _item("item-1", kind="userMessage", queueId="queue-1", turnId="turn-a"),
        _item("item-2", revises="item-1", queueId="queue-2"),
    ]
    refs, _, conflicts = user_message_refs(entries, {"queue-1", "queue-2"})
    checked += _expect((refs[0]["queueId"], conflicts),
                       ("queue-1", {"queue-1", "queue-2"}), "修订队列变化")
    refs, _, conflicts = user_message_refs(entries, {"queue-1", "queue-2"},
                                           revision_id_limit=1)
    checked += _expect((len(refs), refs[0]["revisionOverflow"], conflicts),
                       (1, True, {"queue-1"}), "修订上限")
    refs, _, conflicts = user_message_refs(
        [_item("item-1", kind="userMessage", queueId="queue-1", turnId="turn-a")],
        {"queue-1"}, revision_id_limit=0)
    checked += _expect((refs[0]["revisionOverflow"], conflicts),
                       (True, {"queue-1"}), "修订标识上限")
    # 行为：缺失显式回合时从首个回合与当前运行回合推断归属。
    entries = [
        _item("item-1", kind="userMessage", queueId="queue-1"),
        _turn("turn-a", "running"),
        _item("item-2", kind="userMessage", queueId="queue-1"),
    ]
    refs, _, _ = user_message_refs(entries, {"queue-1"})
    checked += _expect([ref["inferredTurnId"] for ref in refs], ["turn-a", "turn-a"],
                       "推断回合")
    entries = [
        _turn("turn-a", "completed"),
        _item("item-1", kind="userMessage", queueId="queue-1"),
    ]
    refs, _, _ = user_message_refs(entries, {"queue-1"})
    checked += _expect(refs[0]["inferredTurnId"], None, "终态后推断")
    # 行为：followUp 需要回执、回合关联与用户消息三方一致才解析。
    queue = {"id": "queue-1", "kind": "followUp", "status": "delivering", "turnId": None}
    turns = [{"turnId": "turn-a", "queueId": "queue-1"}]
    user_items = [{"kind": "userMessage", "queueId": "queue-1", "turnId": "turn-a",
                   "inferredTurnId": "turn-a"}]
    checked += _expect(resolve_queue_relation(queue, turns, user_items), {
        "ownership": "resolved", "turnId": "turn-a", "relation": "delivered_as",
        "candidates": {"turn-a"}}, "投递归属")
    checked += _expect(resolve_queue_relation(
        {"id": "queue-1", "kind": "followUp", "status": "queued", "turnId": None},
        [], []), {"ownership": "unassigned", "turnId": None, "relation": None,
                  "candidates": set()}, "未分配归属")
    checked += _expect(resolve_queue_relation(
        {"id": "queue-1", "kind": "followUp", "status": "delivered", "turnId": None},
        [], [])["ownership"], "root", "根队列归属")
    checked += _expect(resolve_queue_relation(queue, turns, [])["ownership"],
                       "unresolved", "缺少用户消息")
    checked += _expect(resolve_queue_relation(queue, turns, user_items + [
        {"kind": "userMessage", "queueId": "queue-1", "turnId": "turn-a",
         "inferredTurnId": "turn-a", "source": "steering"}])["ownership"],
                       "conflict", "转向消息冲突")
    checked += _expect(resolve_queue_relation(queue, turns + [
        {"turnId": "turn-b", "queueId": "queue-1"}], [])["ownership"],
                       "conflict", "多回合关联")
    checked += _expect(resolve_queue_relation(queue, turns, user_items,
                                              duplicate_turns={"turn-a"})["ownership"],
                       "conflict", "重复回合归属")
    checked += _expect(resolve_queue_relation(queue, turns, user_items,
                                              identity_conflict=True)["ownership"],
                       "conflict", "身份冲突归属")
    checked += _expect(resolve_queue_relation(queue, turns, user_items,
                                              revision_conflict=True)["ownership"],
                       "conflict", "修订冲突归属")
    checked += _expect(resolve_queue_relation(queue, turns, user_items,
                                              duplicate_user_message=True)["ownership"],
                       "conflict", "重复消息归属")
    checked += _expect(resolve_queue_relation(queue, turns, [
        {"kind": "userMessage", "queueId": "queue-1", "turnId": "turn-a",
         "inferredTurnId": "turn-b"}])["ownership"], "conflict", "显式与推断不符")
    checked += _expect(resolve_queue_relation({"id": "queue-1", "kind": "other",
                                               "status": "queued", "turnId": None},
                                              [], [])["ownership"], "conflict", "未知队列种类")
    # 行为：steering 以目标回合与转向消息为准，回执只作复核。
    steering = {"id": "queue-1", "kind": "steering", "status": "delivered",
                "expectedTurnId": "turn-a", "turnId": None}
    steering_items = [{"kind": "userMessage", "queueId": "queue-1", "source": "steering",
                       "turnId": "turn-a", "inferredTurnId": "turn-a"}]
    checked += _expect(resolve_queue_relation(steering, [{"turnId": "turn-a"}],
                                              steering_items), {
        "ownership": "resolved", "turnId": "turn-a", "relation": "targets",
        "candidates": {"turn-a"}}, "转向归属")
    checked += _expect(resolve_queue_relation(
        steering, [{"turnId": "turn-a"}], [])["ownership"],
        "unresolved", "转向缺少消息")
    checked += _expect(resolve_queue_relation(
        {**steering, "expectedTurnId": "turn-z"}, [{"turnId": "turn-a"}],
        steering_items)["ownership"], "unresolved", "转向目标缺失")
    checked += _expect(resolve_queue_relation(
        {**steering, "turnId": "turn-b"}, [{"turnId": "turn-a"}],
        steering_items)["ownership"], "conflict", "转向回执不符")
    checked += _expect(resolve_queue_relation(
        {**steering, "turnId": "bad id"}, [], [])["candidates"], set(), "非法回执")
    checked += _expect(resolve_queue_relation(
        steering, [{"turnId": "turn-a", "queueId": "queue-1"}],
        steering_items)["ownership"], "conflict", "转向回合关联")
    # 行为：压缩任务只在回合唯一匹配且理由合法时归属该回合。
    job = {"threadId": "thread-1", "turnId": "turn-a", "reason": "threshold"}
    checked += _expect(resolve_compaction_relation(job, "thread-1", [{"turnId": "turn-a"}]),
                       {"ownership": "resolved", "turnId": "turn-a"}, "压缩归属")
    for reason in ("threshold", "budget", "overflow"):
        checked += _expect(resolve_compaction_relation(
            {**job, "reason": reason}, "thread-1", [{"turnId": "turn-a"}])["ownership"],
            "resolved", f"压缩理由 {reason}")
    checked += _expect(resolve_compaction_relation(job, "thread-2",
                                                   [{"turnId": "turn-a"}]),
                       {"ownership": "conflict", "turnId": None}, "压缩会话不符")
    checked += _expect(resolve_compaction_relation({"threadId": "thread-1"}, "thread-1", []),
                       {"ownership": "independent", "turnId": None}, "独立压缩")
    checked += _expect(resolve_compaction_relation({"threadId": "thread-1"}, "thread-1", [],
                                                   checkpoint_turn_id="turn-a")["ownership"],
                       "conflict", "独立压缩带检查点")
    checked += _expect(resolve_compaction_relation(
        {**job, "reason": "other"}, "thread-1", [{"turnId": "turn-a"}]),
        {"ownership": "unresolved", "turnId": None}, "压缩理由非法")
    checked += _expect(resolve_compaction_relation(
        job, "thread-1", [{"turnId": "turn-a"}], checkpoint_turn_id="turn-b")["ownership"],
        "conflict", "压缩检查点不符")
    checked += _expect(resolve_compaction_relation(
        job, "thread-1", [{"turnId": "turn-a"}], duplicate_turns={"turn-a"})["ownership"],
        "conflict", "压缩重复回合")
    checked += _expect(resolve_compaction_relation(job, "thread-1", []),
                       {"ownership": "unresolved", "turnId": None}, "压缩回合缺失")
    checked += _expect(resolve_compaction_relation(
        job, "thread-1", [{"turnId": "turn-a"}, {"turnId": "turn-a"}]),
        {"ownership": "unresolved", "turnId": None}, "压缩回合重复")
    # 行为：恢复策略对未知状态一律人工核对，其余按种类与状态分支。
    checked += _expect(recovery_policy("turn", "unknown", runtime_owned=True),
                       "manual_review", "未知状态优先")
    checked += _expect(recovery_policy("turn", None, runtime_owned=False),
                       "manual_review", "缺失状态")
    checked += _expect(recovery_policy("turn", "completed", runtime_owned=True),
                       "process_owned", "进程持有")
    checked += _expect(recovery_policy("turn", "interrupted", runtime_owned=False,
                                       persisted_policy="manual"),
                       "manual_review", "人工中断策略")
    checked += _expect(recovery_policy("turn", "completed", runtime_owned=False,
                                       persisted_policy="closed"),
                       "closed", "已关闭终态策略")
    checked += _expect(recovery_policy("turn", "interrupted", runtime_owned=False,
                                       persisted_policy="closed"),
                       "manual_review", "中断不采用关闭策略")
    checked += _expect(recovery_policy("turn", "running", runtime_owned=False),
                       "manual_review", "运行中的回合")
    checked += _expect(recovery_policy("turn", "completed", runtime_owned=False),
                       "closed", "已完成回合")
    checked += _expect(recovery_policy("queue", "queued", runtime_owned=False),
                       "queue_pending", "排队队列")
    checked += _expect(recovery_policy("queue", "delivering", runtime_owned=False),
                       "manual_review", "投递中的队列")
    checked += _expect(recovery_policy("queue", "paused", runtime_owned=False),
                       "manual_review", "暂停队列")
    checked += _expect(recovery_policy("queue", "delivered", runtime_owned=False),
                       "closed", "已投递队列")
    checked += _expect(recovery_policy("queue", "cancelled", runtime_owned=False),
                       "closed", "取消队列")
    checked += _expect(recovery_policy("compaction", "completed", runtime_owned=False),
                       "closed", "已完成压缩")
    checked += _expect(recovery_policy("compaction", "failed", runtime_owned=False),
                       "manual_review", "失败压缩")
    checked += _expect(recovery_policy("compaction", "other", runtime_owned=False),
                       "manual_review", "未知压缩状态")
    return checked


def main() -> int:
    try:
        checked = check_task_relation()
    except (ValueError, SyntaxError) as error:
        print(f"任务归属关系核对失败，{error}", file=sys.stderr)
        return 2
    print(f"任务归属关系一致：{checked} 项投影、归属与恢复策略校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
