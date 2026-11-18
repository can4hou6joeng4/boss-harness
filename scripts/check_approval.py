#!/usr/bin/env python3
"""核对审批裁决的字段、归属与过期边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = "harness/src/boss_harness/application.py"
AGENT = "harness/src/boss_harness/agent.py"
SESSION = "harness/src/boss_harness/session.py"
RESPOND_FRAGMENTS = (
    'if not isinstance(params, dict) or set(params) != {"approvalId", "approved"}:',
    'approval_id = _text(params, "approvalId", maximum=64)',
    "if type(approved) is not bool:",
    "runners = [job[\"runner\"] for job in tuple(self.runtimes.active.values())]",
    "if self.runner not in runners:",
    "result = self.sessions.decide_approval(approval_id, approved, live_owner=True)",
    "runner.resolve_approval(approval_id, approved, persist=persist_decision)",
    'raise RpcError(-32004, str(exc), {"code": exc.code, "approvalId": approval_id})',
    "request_id = self._server_approvals.pop(approval_id, None)",
    "self.server.cancel_request(request_id)",
    '"durable": True, "executionPending": True',
    "self.sessions.decide_approval(approval_id, approved, live_owner=False)",
    "self._publish_recovered_approval_decision(result)",
    '"recovered": True,',
)
AGENT_FRAGMENTS = (
    "if (wait is None or wait.decision is not None or self.cancelled()",
    "wait.decision_record = persist()",
    'else "approve" if approved else "deny"',
    "wait.event.set()",
    "if wait is not None and wait.decision is None:",
    'wait.decision = "expired"',
    "remaining = wait.deadline - time.monotonic()",
    "wait.event.wait(min(0.2, remaining))",
    "self._pending_approvals.clear()",
)
SESSION_FRAGMENTS = (
    "if not isinstance(approval_id, str) or not _EVENT_ID.fullmatch(approval_id):",
    "type(expire_only) is not bool",
    "(expire_only and live_owner)",
    "if len(rows) != 1:",
    'code = "APPROVAL_NOT_FOUND" if not rows else "APPROVAL_AMBIGUOUS"',
    "if thread_id in self._pending_deletion_ids():",
    'raise ApprovalDecisionError("APPROVAL_INVALID", "审批索引与会话记录不一致")',
    "if not self._valid_approval_item(item, pending_only=False):",
    'raise ApprovalDecisionError("APPROVAL_CONFLICT", "该审批已经按相反决策处理")',
    'raise ApprovalDecisionError("APPROVAL_CLOSED", "已归档会话中的审批不能裁决")',
    "if not self._valid_approval_item(item, pending_only=True):",
    "if approval[\"deadline\"] <= now:",
    "return self._append_approval_decision(thread[\"id\"], item, \"expired\", live_owner=False)",
    "if turn.get(\"status\") != \"running\":",
    "if turn.get(\"status\") != \"interrupted\":",
    'code = "APPROVAL_BUSY" if turn.get("status") == "running" else "APPROVAL_CLOSED"',
    "return self._append_approval_decision(thread[\"id\"], item, requested, live_owner=live_owner)",
    "def expired_pending_approvals(self, *, limit: int = 32) -> list[str]:",
    "_limit(limit, maximum=128)",
    "AND r.status='interrupted'",
)
APPLICATION_EXTRA = (
    "expired = self.sessions.expired_pending_approvals()",
    "result = self.sessions.expire_approval(approval_id)",
    "failures[approval_id] = failures.get(approval_id, 0) + 1",
    'job["runner"].expire_approval(approval_id)',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_approval() -> tuple[int, int]:
    application = _read(APPLICATION)
    agent = _read(AGENT)
    session = _read(SESSION)
    application_tree = ast.parse(application)
    agent_tree = ast.parse(agent)
    session_tree = ast.parse(session)
    checked = 0
    checked += _expect(RESPOND_FRAGMENTS, _function(
        application_tree, application, "on_approval_respond"), "on_approval_respond")
    checked += _expect(AGENT_FRAGMENTS, agent, "agent.py")
    checked += _expect(SESSION_FRAGMENTS, _function(
        session_tree, session, "decide_approval") + _function(
        session_tree, session, "expired_pending_approvals"), "session.py")
    checked += _expect(APPLICATION_EXTRA, application, "application.py 过期回收")
    return 3, checked


def main() -> int:
    try:
        modules, guards = check_approval()
    except (ValueError, SyntaxError) as error:
        print(f"审批裁决边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批裁决边界一致：{modules} 个模块、{guards} 项字段与归属防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
