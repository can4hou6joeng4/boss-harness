#!/usr/bin/env python3
"""核对任务读取的所有权、阶段绑定与恢复策略。

task_ownership.py 决定 task/read 的归属判定与恢复策略：标识符必须整串匹配，
快照有界，任务阶段只接受固定枚举，队列身份字段变化视为冲突，关系判定需要多重
独立证据，未知状态一律人工核对。放宽任一校验不会触发构建失败，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/task_ownership.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


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
    except ValueError as error:
        print(f"任务读取所有权核对失败，{error}", file=sys.stderr)
        return 2
    print(f"任务读取所有权一致：{checked} 项归属、阶段与恢复防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
