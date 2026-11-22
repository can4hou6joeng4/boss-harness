#!/usr/bin/env python3
"""对照回合阶段检查点与失败回合收尾的字段、枚举与幂等口径。

`record_task_phase` 只记录有界的阶段观察：任务编号、阶段、状态、attempt 与
restartLimit 固定，恢复原因与恢复策略只在提供时写入。`_abandoned_item_payload`
是启动恢复与在线结算共用的终态修订规则：剥离身份字段、状态恒为 failed、
待决审批结算为 expired、工具调用按执行状态区分「未执行」与「结果不确定」。
`settle_abandoned_turn` 在锁内把属于该回合的 running 条目与待决审批补上终态并
返回条目数，重复调用幂等；归属既认显式 `turnId`，也认 running 回合上下文与
首个同名回合的回溯。本脚本在临时目录构造 `SessionStore` 做行为对照并
扫描源码；不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import (Entry, SessionStore,  # noqa: E402
                                  _TASK_PHASES, _TERMINAL)

PHASE_ORDER = (
    "def record_task_phase(self, thread_id: str, task_id: str, phase: str, status: str, *,",
    "attempt: int = 1, restart_limit: int = 0,",
    "recovery_reason: str | None = None,",
    "resume_policy: str | None = None) -> None:",
    '_identifier(task_id, "taskId")',
    "if not isinstance(phase, str) or phase not in _TASK_PHASES:",
    'raise ValueError("任务阶段无效")',
    'if not isinstance(status, str) or status not in _TERMINAL | {"running"}:',
    'raise ValueError("任务阶段状态无效")',
    "if type(attempt) is not int or not 1 <= attempt <= 1_000:",
    'raise ValueError("任务阶段 attempt 必须是 1 到 1000 之间的整数")',
    "if type(restart_limit) is not int or not 0 <= restart_limit <= 32:",
    'raise ValueError("任务阶段 restartLimit 必须是 0 到 32 之间的整数")',
    'for name, value in (("recoveryReason", recovery_reason), ("resumePolicy", resume_policy)):',
    "if value is not None and (not isinstance(value, str) or not value or len(value) > 256):",
    'raise ValueError(f"{name} 格式无效")',
    'if recovery_reason not in {None, "processExit", "terminalStateRecovered"}:',
    'raise ValueError("recoveryReason 无效")',
    'if resume_policy not in {None, "manual", "closed"}:',
    'raise ValueError("resumePolicy 无效")',
    'payload: dict[str, Any] = {"taskId": task_id, "ownerKind": "turn", "phase": phase,',
    '"status": status, "attempt": attempt,',
    '"restartLimit": restart_limit}',
    "if recovery_reason is not None:",
    'payload["recoveryReason"] = recovery_reason',
    "if resume_policy is not None:",
    'payload["resumePolicy"] = resume_policy',
    'self.append(thread_id, Entry(type="task_phase", parent_id=self.last_entry_id(thread_id),',
)
ABANDONED_ORDER = (
    "def _abandoned_item_payload(item: dict, *, error_code: str, unknown_summary: str,",
    "not_executed_summary: str) -> dict:",
    'payload = {key: value for key, value in item.items() if key not in {"id", "threadId"}}',
    'payload.update(status="failed", revises=item["id"])',
    'approval = item.get("approval")',
    'if isinstance(approval, dict) and not approval.get("decision"):',
    'payload["approval"] = {**approval, "decision": "expired", "decidedAt": _now()}',
    'if item.get("kind") == "toolCall":',
    "payload.update(errorCode=error_code, resultSummary=unknown_summary)",
    'phase = item.get("executionState")',
    "payload[\"executionState\"] = \"not_executed\" if (",
    "isinstance(phase, str)",
    'and phase in {"queued", "pending_approval", "approved", "not_approved"}',
    ') else "outcome_unknown"',
    'if payload["executionState"] == "not_executed":',
    'payload["resultSummary"] = not_executed_summary',
    "return payload",
)
SETTLE_ORDER = (
    "def settle_abandoned_turn(self, thread_id: str, turn_id: str) -> int:",
    "with self._lock:",
    "self.require_thread(thread_id)",
    "entries = self.read_entries(thread_id)",
    "owners = self._item_owners(entries)",
    "settled = 0",
    "for item in self._project_items(thread_id, entries):",
    'approval = item.get("approval")',
    'pending_approval = isinstance(approval, dict) and not approval.get("decision")',
    'if item.get("status") != "running" and not pending_approval:',
    "continue",
    'if (item.get("turnId") or owners.get(item["id"])) != turn_id:',
    "continue",
    "payload = self._abandoned_item_payload(",
    'item, error_code="TURN_FAILED",',
    'unknown_summary="回合在工具收尾前失败，结果不确定；先核对平台状态，不要直接重试。",',
    'not_executed_summary="回合在工具执行前失败，该操作未执行；旧审批已经失效。")',
    'self.append(thread_id, Entry(type="item", parent_id=self.last_entry_id(thread_id),',
    "payload=payload))",
    "settled += 1",
    "return settled",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def _add_item(store: SessionStore, thread_id: str, *, parent: bool = True, **payload) -> str:
    entry = store.append(thread_id, Entry(
        type="item", parent_id=store.last_entry_id(thread_id) if parent else None, payload=payload))
    return entry.id if hasattr(entry, "id") else entry["id"]


def _add_turn(store: SessionStore, thread_id: str, turn_id: str, status: str) -> None:
    store.append(thread_id, Entry(
        type="turn", parent_id=store.last_entry_id(thread_id),
        payload={"turnId": turn_id, "status": status}))


def _items(store: SessionStore, thread_id: str) -> dict[str, dict]:
    return {item["id"]: item for item in store.read_items(thread_id)}


def check_turn_phase() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    phase = _method(tree, source, "SessionStore", "record_task_phase")
    abandoned = _method(tree, source, "SessionStore", "_abandoned_item_payload")
    settle = _method(tree, source, "SessionStore", "settle_abandoned_turn")
    checked = _ordered(PHASE_ORDER, phase, SESSION)
    checked += _ordered(ABANDONED_ORDER, abandoned, SESSION)
    checked += _ordered(SETTLE_ORDER, settle, SESSION)
    # 阶段记录恰好一条，枚举各用一次，可选键只在提供时写入。
    if phase.count('Entry(type="task_phase"') != 1:
        raise ValueError(f"{SESSION} 的阶段记录必须恰好一条")
    checked += 1
    if phase.count("_TASK_PHASES") != 1 or phase.count('_TERMINAL | {"running"}') != 1:
        raise ValueError(f"{SESSION} 的阶段与状态枚举必须各用一次")
    checked += 1
    if phase.count('payload["recoveryReason"] = recovery_reason') != 1:
        raise ValueError(f"{SESSION} 的恢复原因只在提供时写入")
    checked += 1
    if phase.count('payload["resumePolicy"] = resume_policy') != 1:
        raise ValueError(f"{SESSION} 的恢复策略只在提供时写入")
    checked += 1
    if phase.index("payload: dict[str, Any]") > phase.index("self.append("):
        raise ValueError(f"{SESSION} 的阶段载荷必须先于追加")
    checked += 1
    if phase.count('"ownerKind": "turn"') != 1:
        raise ValueError(f"{SESSION} 的阶段归属必须恒为回合")
    checked += 1
    # 终态修订不得写出身份字段，状态恒为 failed，审批结算先于工具分支。
    if abandoned.count('if key not in {"id", "threadId"}') != 1:
        raise ValueError(f"{SESSION} 的终态修订必须剥离身份字段")
    checked += 1
    if abandoned.count('status="failed"') != 1 or 'status="failed", revises=item["id"]' not in abandoned:
        raise ValueError(f"{SESSION} 的终态修订必须固定 failed 并指向原条目")
    checked += 1
    if abandoned.index("not approval.get(\"decision\")") > abandoned.index('if item.get("kind") == "toolCall":'):
        raise ValueError(f"{SESSION} 的审批结算必须先于工具分支")
    checked += 1
    if abandoned.count('"not_executed"') != 2 or abandoned.count('"outcome_unknown"') != 1:
        raise ValueError(f"{SESSION} 的执行状态必须只有两种出口")
    checked += 1
    # 在线结算先锁后读、归属判断晚于状态判断、计数恰好一次。
    if settle.count("continue") != 2:
        raise ValueError(f"{SESSION} 的在线结算必须有状态与归属两处跳过")
    checked += 1
    if settle.count("settled += 1") != 1 or settle.count("return settled") != 1:
        raise ValueError(f"{SESSION} 的在线结算必须只计一次并返回")
    checked += 1
    if settle.count('error_code="TURN_FAILED"') != 1:
        raise ValueError(f"{SESSION} 的在线结算必须使用回合失败错误码")
    checked += 1
    if settle.index("self.require_thread(thread_id)") > settle.index("self.read_entries(thread_id)"):
        raise ValueError(f"{SESSION} 的在线结算必须先确认会话再读取")
    checked += 1
    # 行为：阶段检查点。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("阶段")["id"]
            store.record_task_phase(thread_id, "task-1", "admission", "running")
            last = store.read_entries(thread_id)[-1]
            expected = {"taskId": "task-1", "ownerKind": "turn", "phase": "admission",
                        "status": "running", "attempt": 1, "restartLimit": 0}
            if last.get("type") != "task_phase" or last.get("payload") != expected:
                raise ValueError("最小阶段记录必须只含固定字段")
            checked += 1
            store.record_task_phase(thread_id, "task-2", "model_request", "completed", attempt=3,
                                    restart_limit=2, recovery_reason="processExit",
                                    resume_policy="manual")
            last = store.read_entries(thread_id)[-1]
            if (last["payload"].get("recoveryReason") != "processExit"
                    or last["payload"].get("resumePolicy") != "manual"
                    or last["payload"].get("attempt") != 3
                    or last["payload"].get("restartLimit") != 2):
                raise ValueError("阶段记录必须写入提供的可选项")
            checked += 1
            for label, kwargs, message in (
                ("任务编号为空", {"task_id": "", "phase": "admission", "status": "running"}, "taskId 格式无效"),
                ("任务编号非字符串", {"task_id": 3, "phase": "admission", "status": "running"}, "taskId 格式无效"),
                ("任务编号超长", {"task_id": "t" * 129, "phase": "admission", "status": "running"}, "taskId 格式无效"),
                ("阶段未知", {"task_id": "task-3", "phase": "unknown", "status": "running"}, "任务阶段无效"),
                ("阶段非字符串", {"task_id": "task-3", "phase": 1, "status": "running"}, "任务阶段无效"),
                ("状态未知", {"task_id": "task-3", "phase": "finish", "status": "failed"}, "任务阶段状态无效"),
                ("状态非字符串", {"task_id": "task-3", "phase": "finish", "status": None}, "任务阶段状态无效"),
                ("尝试为零", {"task_id": "task-3", "phase": "finish", "status": "running", "attempt": 0},
                 "任务阶段 attempt 必须是 1 到 1000 之间的整数"),
                ("尝试超限", {"task_id": "task-3", "phase": "finish", "status": "running", "attempt": 1001},
                 "任务阶段 attempt 必须是 1 到 1000 之间的整数"),
                ("尝试为布尔", {"task_id": "task-3", "phase": "finish", "status": "running", "attempt": True},
                 "任务阶段 attempt 必须是 1 到 1000 之间的整数"),
                ("重启为负", {"task_id": "task-3", "phase": "finish", "status": "running", "restart_limit": -1},
                 "任务阶段 restartLimit 必须是 0 到 32 之间的整数"),
                ("重启超限", {"task_id": "task-3", "phase": "finish", "status": "running", "restart_limit": 33},
                 "任务阶段 restartLimit 必须是 0 到 32 之间的整数"),
                ("恢复原因为空", {"task_id": "task-3", "phase": "finish", "status": "running",
                                 "recovery_reason": ""}, "recoveryReason 格式无效"),
                ("恢复原因超长", {"task_id": "task-3", "phase": "finish", "status": "running",
                                 "recovery_reason": "r" * 257}, "recoveryReason 格式无效"),
                ("恢复原因非字符串", {"task_id": "task-3", "phase": "finish", "status": "running",
                                     "recovery_reason": 1}, "recoveryReason 格式无效"),
                ("恢复策略为空", {"task_id": "task-3", "phase": "finish", "status": "running",
                                 "resume_policy": ""}, "resumePolicy 格式无效"),
                ("恢复策略非字符串", {"task_id": "task-3", "phase": "finish", "status": "running",
                                     "resume_policy": []}, "resumePolicy 格式无效"),
                ("恢复原因枚举", {"task_id": "task-3", "phase": "finish", "status": "running",
                                 "recovery_reason": "crash"}, "recoveryReason 无效"),
                ("恢复策略枚举", {"task_id": "task-3", "phase": "finish", "status": "running",
                                 "resume_policy": "auto"}, "resumePolicy 无效"),
            ):
                _expect_error(lambda kwargs=kwargs: store.record_task_phase(thread_id, **kwargs),
                              message, label)
                checked += 1
            for task_phase in sorted(_TASK_PHASES):
                store.record_task_phase(thread_id, f"task-{task_phase}", task_phase, "running")
                checked += 1
            for status in sorted(_TERMINAL) + ["running"]:
                store.record_task_phase(thread_id, f"status-{status}", "finish", status)
                checked += 1
            _expect_error(lambda: store.record_task_phase("000000000000", "task-3", "finish", "running"),
                          "会话不存在", "会话不存在")
            checked += 1
            for label, attempt, restart_limit in (("下界", 1, 0), ("上界", 1000, 32)):
                store.record_task_phase(thread_id, f"edge-{attempt}", "finish", "running",
                                        attempt=attempt, restart_limit=restart_limit)
                last = store.read_entries(thread_id)[-1]
                if (last["payload"].get("attempt") != attempt
                        or last["payload"].get("restartLimit") != restart_limit):
                    raise ValueError(f"{label}阶段边界必须被接受并原样写入")
                checked += 1
            store.record_task_phase(thread_id, "enum-recovery", "finish", "running",
                                    recovery_reason="terminalStateRecovered", resume_policy="closed")
            last = store.read_entries(thread_id)[-1]
            if (last["payload"].get("recoveryReason") != "terminalStateRecovered"
                    or last["payload"].get("resumePolicy") != "closed"):
                raise ValueError("其余恢复枚举值必须被接受并写入")
            checked += 1
        finally:
            store.close()
    # 行为：失败回合收尾。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("收尾")["id"]
            turn = "turn-1"
            if store.settle_abandoned_turn(thread_id, turn) != 0:
                raise ValueError("没有遗留条目时必须返回零")
            checked += 1
            message_id = _add_item(store, thread_id, kind="message", turnId=turn,
                                   role="assistant", status="running")
            if store.settle_abandoned_turn(thread_id, turn) != 1:
                raise ValueError("遗留消息条目必须被结算")
            checked += 1
            item = _items(store, thread_id)[message_id]
            if item.get("status") != "failed" or item.get("revises") != message_id:
                raise ValueError("消息条目必须收敛到 failed 并指向原条目")
            checked += 1
            if "errorCode" in item or "executionState" in item:
                raise ValueError("非工具条目不得带工具终态字段")
            checked += 1
            for label, execution_state in (
                ("排队", "queued"),
                ("待审批", "pending_approval"),
                ("已批准", "approved"),
                ("未批准", "not_approved"),
            ):
                call_id = _add_item(store, thread_id, kind="toolCall", turnId=turn,
                                    toolName="boss_hr_greet", status="running",
                                    executionState=execution_state)
                if store.settle_abandoned_turn(thread_id, turn) != 1:
                    raise ValueError(f"{label}工具条目必须被结算")
                item = _items(store, thread_id)[call_id]
                if (item.get("executionState") != "not_executed"
                        or item.get("errorCode") != "TURN_FAILED"
                        or "该操作未执行" not in item.get("resultSummary", "")):
                    raise ValueError(f"{label}工具条目必须按未执行结算")
                checked += 1
            for label, execution_state in (("已执行", "executed"), ("缺失", None), ("非字符串", 3)):
                call_id = _add_item(store, thread_id, kind="toolCall", turnId=turn,
                                    toolName="boss_hr_greet", status="running",
                                    **({} if execution_state is None else {"executionState": execution_state}))
                if store.settle_abandoned_turn(thread_id, turn) != 1:
                    raise ValueError(f"{label}工具条目必须被结算")
                item = _items(store, thread_id)[call_id]
                if (item.get("executionState") != "outcome_unknown"
                        or "结果不确定" not in item.get("resultSummary", "")):
                    raise ValueError(f"{label}工具条目必须按结果不确定结算")
                checked += 1
            approval_id = _add_item(store, thread_id, parent=False, kind="toolCall", turnId=turn,
                                    toolName="boss_hr_greet", status="completed",
                                    approval={"approvalId": "approval-1", "deadline": 1.0,
                                              "paramsDigest": "a" * 64})
            if store.settle_abandoned_turn(thread_id, turn) != 1:
                raise ValueError("待决审批必须被结算")
            checked += 1
            item = _items(store, thread_id)[approval_id]
            approval = item.get("approval") or {}
            if (approval.get("decision") != "expired" or not isinstance(approval.get("decidedAt"), str)
                    or approval.get("approvalId") != "approval-1"
                    or approval.get("paramsDigest") != "a" * 64):
                raise ValueError("待决审批必须结算为 expired 且保留原有字段")
            checked += 1
            if item.get("status") != "failed":
                raise ValueError("待决审批所属条目必须收敛到 failed")
            checked += 1
            other = _add_item(store, thread_id, kind="message", turnId="turn-2",
                              role="assistant", status="running")
            if store.settle_abandoned_turn(thread_id, turn) != 0:
                raise ValueError("其他回合的遗留条目不得被结算")
            checked += 1
            if _items(store, thread_id)[other].get("status") != "running":
                raise ValueError("其他回合的条目必须保持 running")
            checked += 1
            done_id = _add_item(store, thread_id, kind="message", turnId=turn,
                                role="assistant", status="completed")
            if store.settle_abandoned_turn(thread_id, turn) != 0:
                raise ValueError("已终态条目不得被重复结算")
            checked += 1
            if _items(store, thread_id)[done_id].get("status") != "completed":
                raise ValueError("已终态条目必须保持原状态")
            checked += 1
            first = _add_item(store, thread_id, kind="message", turnId=turn,
                              role="assistant", status="running")
            second = _add_item(store, thread_id, kind="message", turnId=turn,
                               role="assistant", status="running")
            if store.settle_abandoned_turn(thread_id, turn) != 2:
                raise ValueError("同一回合的多条遗留条目必须逐条结算")
            checked += 1
            items = _items(store, thread_id)
            if items[first].get("status") != "failed" or items[second].get("status") != "failed":
                raise ValueError("多条遗留条目必须全部收敛")
            checked += 1
            before = len(store.read_entries(thread_id))
            if store.settle_abandoned_turn(thread_id, turn) != 0:
                raise ValueError("重复结算必须幂等")
            checked += 1
            if len(store.read_entries(thread_id)) != before:
                raise ValueError("重复结算不得写入记录")
            checked += 1
            _expect_error(lambda: store.settle_abandoned_turn("000000000000", turn),
                          "会话不存在", "收尾会话不存在")
            checked += 1
            # 归属：显式 turnId 之外，还认 running 回合上下文与首个同名回合的回溯。
            context_thread = store.create("归属")["id"]
            _add_turn(store, context_thread, "ctx-1", "running")
            contextual = _add_item(store, context_thread, kind="message", role="assistant", status="running")
            contextual_call = _add_item(store, context_thread, kind="toolCall", toolName="boss_hr_greet",
                                        status="running", executionState="pending_approval",
                                        approval={"approvalId": "b" * 32})
            if store.settle_abandoned_turn(context_thread, "ctx-1") != 2:
                raise ValueError("上下文归属的遗留条目必须被结算")
            checked += 1
            context_items = _items(store, context_thread)
            if (context_items[contextual]["status"] != "failed"
                    or context_items[contextual_call]["executionState"] != "not_executed"
                    or context_items[contextual_call]["approval"].get("decision") != "expired"):
                raise ValueError("上下文归属的工具条目必须按未执行结算")
            checked += 1
            _add_turn(store, context_thread, "ctx-1", "completed")
            orphan = _add_item(store, context_thread, kind="message", role="assistant", status="running")
            if store.settle_abandoned_turn(context_thread, "ctx-1") != 0:
                raise ValueError("回合终态后的无归属条目不得被结算")
            checked += 1
            if _items(store, context_thread)[orphan]["status"] != "running":
                raise ValueError("回合终态后的无归属条目必须保持 running")
            checked += 1
            legacy_thread = store.create("回溯")["id"]
            legacy = _add_item(store, legacy_thread, kind="message", role="assistant", status="running")
            _add_turn(store, legacy_thread, "legacy-1", "running")
            if store.settle_abandoned_turn(legacy_thread, "legacy-1") != 1:
                raise ValueError("回合条目之前写入的遗留条目必须被结算")
            checked += 1
            if _items(store, legacy_thread)[legacy]["status"] != "failed":
                raise ValueError("回溯归属必须收敛到 failed")
            checked += 1
            explicit_thread = store.create("显式")["id"]
            _add_turn(store, explicit_thread, "explicit-1", "running")
            explicit = _add_item(store, explicit_thread, kind="message", role="assistant",
                                 status="running", turnId="explicit-2")
            if store.settle_abandoned_turn(explicit_thread, "explicit-1") != 0:
                raise ValueError("上下文不得覆盖显式 turnId")
            checked += 1
            if _items(store, explicit_thread)[explicit]["status"] != "running":
                raise ValueError("显式 turnId 的条目在错误回合必须保持 running")
            checked += 1
            if store.settle_abandoned_turn(explicit_thread, "explicit-2") != 1:
                raise ValueError("显式 turnId 的条目必须在所属回合结算")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_turn_phase()
    except (ValueError, SyntaxError) as error:
        print(f"回合阶段核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合阶段一致：{checked} 项阶段、收尾与幂等校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
