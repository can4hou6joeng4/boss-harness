#!/usr/bin/env python3
"""对照启动恢复 `recover` 的阶段收尾、条目结算与回合中断口径。

`recover` 遍历全部会话（含归档），跳过无法读取的损坏会话，按最新的
`task_phase` 为已终态回合补 `terminalStateRecovered` / `closed` 收尾、为未终态
回合写 `processExit` / `manual` 中断；随后把仍为 `running` 的条目或失效审批结算
为失败修订，并把受影响回合改为 `interrupted`。进程异常退出后这是唯一把遗留
`running` 状态收敛到终态的路径。本脚本在临时目录构造 `SessionStore` 做行为对照，
不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import Entry, SessionStore  # noqa: E402

RECOVERY_ORDER = (
    "def recover(self) -> None:",
    "for thread in self.list_threads(include_archived=True):",
    "entries = self.read_entries(thread_id)",
    "except (OSError, ValueError):",
    "turns = self._turns(entries, thread_id)",
    'last_activity = _valid_timestamp(entries[-1].get("timestamp")) if entries else None',
    'turns_by_id = {turn["turnId"]: turn for turn in turns}',
    "latest_phases: dict[str, dict[str, Any]] = {}",
    'if entry.get("type") != "task_phase" or not isinstance(entry.get("payload"), dict):',
    'task_id, phase = payload.get("taskId"), payload.get("phase")',
    'if (payload.get("ownerKind") == "turn" and isinstance(task_id, str)',
    "and _IDENTIFIER.fullmatch(task_id)",
    "and isinstance(phase, str) and phase in _TASK_PHASES):",
    "latest_phases[task_id] = payload",
    "for task_id, phase in latest_phases.items():",
    "turn = turns_by_id.get(task_id)",
    "if turn is None:",
    'if isinstance(turn.get("status"), str) and turn.get("status") in _TERMINAL:',
    'status = turn["status"]',
    'reason = "terminalStateRecovered"',
    'policy = "closed"',
    'status = "interrupted"',
    'reason = "processExit"',
    'policy = "manual"',
    'if (phase.get("phase") == "finish" and phase.get("status") == status',
    'and (phase.get("resumePolicy") == policy or policy == "closed")):',
    "attempt = phase.get(\"attempt\", 1)",
    "attempt = 1",
    'restart_limit = phase.get("restartLimit", 0)',
    "restart_limit = 0",
    'phase_was_running = phase.get("status") == "running"',
    "if phase_was_running:",
    "self.record_task_phase(",
    'if phase.get("phase") != "finish" or not phase_was_running:',
    'self.record_task_phase(thread_id, task_id, "finish", status,',
    "turn_by_item = self._item_owners(entries)",
    "items = self._project_items(thread_id, entries)",
    "recovered_turns: set[str] = set()",
    'pending_approval = isinstance(approval, dict) and not approval.get("decision")',
    'if item.get("status") != "running" and not pending_approval:',
    'affected_turn = item.get("turnId") or turn_by_item.get(item["id"])',
    "if (pending_approval and isinstance(owner_status, str)",
    'and owner_status in {"running", "interrupted"}',
    "and self._valid_approval_item(item, pending_only=True)",
    'and approval["deadline"] > time.time()):',
    "payload = self._abandoned_item_payload(",
    "self.append(thread_id, Entry(type=\"item\", parent_id=self.last_entry_id(thread_id), payload=payload))",
    "recovered_turns.add(affected_turn)",
    "for turn in turns:",
    'if turn.get("status") == "running" or turn["turnId"] in recovered_turns:',
    'fields: dict[str, Any] = {"recoveryReason": "processExit"}',
    'self.record_turn(thread_id, turn["turnId"], "interrupted", **fields)',
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


def _add_item(store: SessionStore, thread_id: str, **payload) -> None:
    store.append(thread_id, Entry(type="item", parent_id=store.last_entry_id(thread_id),
                                  payload=payload))


def _entries(store: SessionStore, thread_id: str) -> list[dict]:
    return store.read_entries(thread_id)


def _turns(entries: list[dict]) -> list[tuple]:
    return [(entry["payload"].get("turnId"), entry["payload"].get("status"),
             entry["payload"].get("recoveryReason"))
            for entry in entries if entry.get("type") == "turn"]


def _phases(entries: list[dict]) -> list[tuple]:
    return [(entry["payload"].get("phase"), entry["payload"].get("status"),
             entry["payload"].get("recoveryReason"), entry["payload"].get("resumePolicy"))
            for entry in entries if entry.get("type") == "task_phase"]


def _items(entries: list[dict]) -> list[tuple]:
    return [(entry["payload"].get("status"), entry["payload"].get("executionState"),
             entry["payload"].get("errorCode"))
            for entry in entries if entry.get("type") == "item"]


def _expect(actual, expected, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} 恢复结果变化：期望 {expected!r}，实际 {actual!r}")


def check_recovery() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    recover = _method(tree, source, "SessionStore", "recover")
    checked = _ordered(RECOVERY_ORDER, recover, SESSION)
    if recover.count("include_archived=True") != 1:
        raise ValueError(f"{SESSION} 的启动恢复必须覆盖归档会话")
    checked += 1
    handler_at = recover.find("except (OSError, ValueError):")
    resume_at = recover.find("turns = self._turns(", handler_at)
    if (recover.count("except (OSError, ValueError):") != 1 or handler_at < 0
            or resume_at < 0 or "continue" not in recover[handler_at:resume_at]):
        raise ValueError(f"{SESSION} 的启动恢复必须跳过损坏会话")
    checked += 1
    if recover.count("latest_phases") != 3:
        raise ValueError(f"{SESSION} 的启动恢复必须按最新阶段归并")
    checked += 1
    if recover.count('"terminalStateRecovered"') != 1 or recover.count('"processExit"') != 2:
        raise ValueError(f"{SESSION} 的启动恢复原因必须各按其位")
    checked += 1
    if recover.count("self.record_task_phase(") != 2:
        raise ValueError(f"{SESSION} 的启动恢复必须最多补两条阶段记录")
    checked += 1
    if recover.count("self.record_turn(") != 1 or recover.count("self.append(") != 1:
        raise ValueError(f"{SESSION} 的启动恢复必须各写一条回合与条目记录")
    checked += 1
    if recover.count("SESSION_INTERRUPTED") != 1:
        raise ValueError(f"{SESSION} 的启动恢复必须使用固定错误码")
    checked += 1
    if recover.count('approval["deadline"] > time.time()') != 1:
        raise ValueError(f"{SESSION} 的启动恢复必须按截止时间保留审批")
    checked += 1
    # 行为：running 回合与阶段、running 条目一起收敛到终态。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("中断恢复")["id"]
            store.record_turn(thread_id, "turn-a", "running")
            store.record_task_phase(thread_id, "turn-a", "model_request", "running")
            _add_item(store, thread_id, kind="toolCall", turnId="turn-a", status="running",
                      executionState="queued", toolName="boss_hr_greet", toolArguments={})
            store.recover()
            entries = _entries(store, thread_id)
            _expect(_turns(entries)[-1], ("turn-a", "interrupted", "processExit"), "回合中断")
            checked += 1
            _expect(_phases(entries), [
                ("model_request", "running", None, None),
                ("model_request", "interrupted", "processExit", "manual"),
                ("finish", "interrupted", "processExit", "manual"),
            ], "阶段中断")
            checked += 1
            _expect(_items(entries)[-1], ("failed", "not_executed", "SESSION_INTERRUPTED"),
                    "条目结算")
            checked += 1
        finally:
            store.close()
    # 行为：已终态回合只补终态收尾，不中断回合。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("终态恢复")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            store.record_task_phase(thread_id, "turn-a", "model_request", "running")
            store.recover()
            entries = _entries(store, thread_id)
            _expect(_turns(entries), [("turn-a", "completed", None)], "终态不回写")
            checked += 1
            _expect(_phases(entries)[-1],
                    ("finish", "completed", "terminalStateRecovered", "closed"), "终态收尾")
            checked += 1
        finally:
            store.close()
    # 行为：已收尾的阶段与终态回合幂等，不追加记录。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("幂等恢复")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            store.record_task_phase(thread_id, "turn-a", "finish", "completed",
                                    recovery_reason="terminalStateRecovered", resume_policy="closed")
            before = len(_entries(store, thread_id))
            store.recover()
            after = len(_entries(store, thread_id))
            if after != before:
                raise ValueError(f"已收尾的会话不得追加记录：{before} → {after}")
            checked += 1
        finally:
            store.close()
    # 行为：已完成条目与未知阶段的回合被跳过。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("跳过恢复")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            _add_item(store, thread_id, kind="toolCall", turnId="turn-a", status="completed",
                      executionState="succeeded", toolName="boss_hr_greet", toolArguments={})
            store.record_task_phase(thread_id, "turn-z", "model_request", "running")
            before = len(_entries(store, thread_id))
            store.recover()
            after = len(_entries(store, thread_id))
            if after != before:
                raise ValueError(f"已完成条目与未知回合不得被恢复改写：{before} → {after}")
            checked += 1
        finally:
            store.close()
    # 行为：损坏会话不阻断其他会话的恢复。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            broken = store.create("损坏会话")["id"]
            store.path_for(broken).write_text("{not-json\n", encoding="utf-8")
            healthy = store.create("健康会话")["id"]
            store.record_turn(healthy, "turn-a", "running")
            store.recover()
            entries = _entries(store, healthy)
            _expect(_turns(entries)[-1], ("turn-a", "interrupted", "processExit"), "跳过损坏会话")
            checked += 1
        finally:
            store.close()
    # 行为：归档会话同样被恢复。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("归档会话")["id"]
            store.record_turn(thread_id, "turn-a", "running")
            store.archive_thread(thread_id)
            store.recover()
            entries = _entries(store, thread_id)
            _expect(_turns(entries)[-1], ("turn-a", "interrupted", "processExit"), "归档恢复")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_recovery()
    except (ValueError, SyntaxError) as error:
        print(f"启动恢复核对失败，{error}", file=sys.stderr)
        return 2
    print(f"启动恢复一致：{checked} 项阶段收尾、条目结算与回合中断校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
