#!/usr/bin/env python3
"""核对队列写入、回合中断与审批入口：queue/add、queue/update、queue/steer、queue/remove、
turn/interrupt、turn/steer、approval/list、approval/respond。

队列写入以 `clientUserMessageId` 为幂等键：相同输入重试返回同一队列项，不同输入报
`CLIENT_REQUEST_CONFLICT`；归档会话在无既有队列项的请求上直接拒绝。`queue/update` /
`queue/remove` 只作用于排队中的条目。`queue/steer` / `turn/steer` 在没有匹配活跃回合时
以 `STEER_UNAVAILABLE` 或同步拒绝结束；`turn/interrupt` 无回合返回 `{"interrupted": false}`。
审批读取返回三项投影，响应严格限定两个参数并区分 `APPROVAL_INVALID` / `APPROVAL_NOT_FOUND`。
这里在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），逐项验证
拒绝分支与投影；静态部分锁定这些 handler 的源码顺序。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer, RpcError  # noqa: E402
from boss_harness.session import Entry  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
QUEUE_ADD = (
    '        params = params or {}',
    '        thread_id, text = _text(params, "threadId"), _text(params, "input")',
    "        with self.runtimes.lock:",
    "            if self.runtimes.closed:",
    '                raise RpcError(-32003, "内核正在关闭")',
    "            self.sessions.require_thread(thread_id)",
    '            skill_ids = [skill["id"] for skill in self.skills.load(params.get("skillIds"))[1]]',
    '            identity = resolve_request(self.sessions, thread_id, params.get("clientUserMessageId"), text)',
    '            if thread.get("archived") and identity.queue is None and identity.turn is None:',
    '                raise RpcError(-32004, "请先恢复归档会话，再添加排队消息")',
    "                self._thread_route(thread)",
    '                    raise RpcError(-32004, "clientUserMessageId 已用于不同技能组合",',
    '                                   {"code": "CLIENT_REQUEST_CONFLICT"})',
    '                raise RpcError(-32004, "clientUserMessageId 已用于不同自动压缩覆盖",',
    '                raise RpcError(-32004, "该会话的工具结果尚未完成持久化核对，请重启内核后重新读取状态",',
    "            item = identity.queue or self.queue.add(",
    "                item = self.queue._associate_request(thread_id, item[\"id\"], identity)",
    "            notice = self._retain_receipt_notice_locked(thread_id, item[\"id\"])",
    "            if changed:",
    "                self._publish_receipt_notice(notice, finish=False)",
    '            if item["status"] == "queued":',
    "                self._start_follow_up(thread_id)",
    '            return {"queueItem": queue_view_record(self.queue.get(thread_id, item["id"]))}',
    "            self._finish_receipt_notice(notice)",
)
QUEUE_UPDATE = (
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    "            if self.runtimes.closed:",
    '                raise RpcError(-32003, "内核正在关闭")',
    "            self.sessions.require_thread(thread_id)",
    "            item = self.queue.update_input(thread_id, queue_id, text)",
    '        self._emit_queue_updated(thread_id, item["id"])',
    '        return {"queueItem": queue_view_record(item)}',
)
QUEUE_STEER = (
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    "            self.sessions.require_thread(thread_id)",
    '            job = self.runtimes.active.get(thread_id)',
    '            if job is None or job["turnId"] != expected or job["cancel"].is_set():',
    '                raise RpcError(-32004, "目标回合已经结束或发生变化",',
    '                               {"code": "STEER_UNAVAILABLE"})',
    "                item = self.queue.promote_to_steering(thread_id, queue_id, expected)",
    '                raise RpcError(-32004, str(exc), {"code": "STEER_UNAVAILABLE"}) from None',
    "                self._forget_capacity_waiter_locked(thread_id)",
    '        return {"queueItem": queue_view_record(item)}',
)
QUEUE_REMOVE = (
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    '            item = self.queue.transition(thread_id, _text(params, "queueId"), "cancelled")',
    "                self._forget_capacity_waiter_locked(thread_id)",
    '        return {"queueItem": queue_view_record(item)}',
)
TURN_INTERRUPT = (
    "        # 只有缺省才允许取消当前回合；显式空值不能绕过目标保护。",
    '        turn_id = _text(params, "turnId", maximum=128) if "turnId" in params else None',
    "        with self.runtimes.lock:",
    "            turn = self.runtimes.prepare_interrupt(thread_id, turn_id, interrupt=False)",
    "            if turn is None:",
    '                return {"interrupted": False}',
    '            aborts = [turn["_shutdown_abort"]]',
    '            job = self._compaction_jobs.get(self._compaction_by_thread.get(thread_id))',
    '            if job is not None and job.get("turnId") == turn["turnId"] and job["status"] == "running":',
    "                aborts.append(self._claim_compaction_abort_locked(job))",
    "        return {\"interrupted\": True}",
)
TURN_STEER = (
    "        with self.runtimes.lock:",
    '            job = self.runtimes.active.get(thread_id)',
    '            expected = _text(params, "expectedTurnId")',
    '            if job is None or job["turnId"] != expected or job["cancel"].is_set():',
    '                raise RpcError(-32004, "目标回合已经结束或发生变化")',
    '            item = self.queue.add(thread_id, _text(params, "input"), kind="steering", turn_id=expected,',
    "                                  client_id=params.get(\"clientUserMessageId\"))",
    '        self._emit_queue_updated(thread_id, item["id"])',
    '        return {"accepted": True, "queueItem": queue_view_record(item)}',
)
APPROVAL_LIST = (
    "        if params is not None and not isinstance(params, dict):",
    '            raise ValueError("审批查询参数必须是对象")',
    '        if set(params) - {"threadId", "limit"}:',
    '            raise ValueError("审批查询只接受 threadId 和 limit")',
    '        limit = params.get("limit", 100)',
    "        if type(limit) is not int or not 1 <= limit <= 200:",
    '            raise ValueError("limit 必须是 1 到 200 之间的整数")',
    "        approvals, truncated = self.sessions.pending_approvals(thread_id, limit=limit)",
    '        return {"approvals": approvals, "truncated": truncated,',
    '                "threadCounts": self.sessions.pending_approval_counts(thread_id)}',
)
APPROVAL_RESPOND = (
    '        if not isinstance(params, dict) or set(params) != {"approvalId", "approved"}:',
    '            raise ValueError("审批响应只能包含 approvalId 和 approved")',
    '        approval_id = _text(params, "approvalId", maximum=64)',
    '        approved = params["approved"]',
    "        if type(approved) is not bool:",
    '            raise ValueError("approved 必须是布尔值")',
    '        runners = [job["runner"] for job in tuple(self.runtimes.active.values())]',
    "                resolved_live = runner.resolve_approval(approval_id, approved, persist=persist_decision)",
    '                raise RpcError(-32004, str(exc), {"code": exc.code, "approvalId": approval_id}) from None',
    "        request_id = self._server_approvals.pop(approval_id, None)",
    "            if live_result and live_result.get(\"decision\") == \"expired\":",
    '            return {"approvalId": approval_id, "approved": approved, "accepted": True,',
    '                    "durable": True, "executionPending": True}',
    "            result = self.sessions.decide_approval(approval_id, approved, live_owner=False)",
    "        self._publish_recovered_approval_decision(result)",
    '        return {"approvalId": approval_id, "approved": approved, "accepted": True,',
    '                "executed": result["executed"], "recovered": True,',
    '                "executionState": result["executionState"], "status": result["status"]}',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _tree(relative: str) -> ast.Module:
    try:
        return ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ApplicationService":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"application.py 缺少 ApplicationService.{name}")


def _check_structures() -> int:
    source = _read(MODULE)
    tree = _tree(MODULE)
    checked = 0
    methods = (("on_queue_add", QUEUE_ADD), ("on_queue_update", QUEUE_UPDATE),
               ("on_queue_steer", QUEUE_STEER), ("on_queue_remove", QUEUE_REMOVE),
               ("on_turn_interrupt", TURN_INTERRUPT), ("on_turn_steer", TURN_STEER),
               ("on_approval_list", APPROVAL_LIST), ("on_approval_respond", APPROVAL_RESPOND))
    for name, fragments in methods:
        body = _method(tree, source, name)
        position = -1
        for fragment in fragments:
            found = body.find(fragment, position + 1)
            if found < 0:
                raise ValueError(f"ApplicationService.{name} 的顺序缺少：{fragment}")
            position = found
            checked += 1
    return checked


@contextmanager
def _clean_environment(overrides: dict[str, str] | None = None):
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        if overrides:
            os.environ.update(overrides)
        yield


class _Workspace:
    def __init__(self, directory: str) -> None:
        self.root = Path(directory)
        self.state = self.root / "state"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.server: JsonRpcServer | None = None

    def service(self, **kwargs) -> ApplicationService:
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, self.state, ModelConfig(provider="none", model="none"),
                                     None, workspace=self.workspace, **kwargs)
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                               "protocolVersion": "0.2.0"})
        service.on_initialized(None)
        self.server = server
        return service

    def take(self) -> list[dict]:
        assert self.server is not None
        lines = self.server._out.getvalue().splitlines()
        self.server._out = io.StringIO()
        return [json.loads(line) for line in lines if line.strip()]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"队列写入行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"队列写入行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"队列写入行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if (error.code, str(error), error.data) != (code, message, data):
            raise ValueError(f"队列写入行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                             f"实际 ({error.code}, {str(error)!r}, {error.data!r})") from None
        return 1
    raise ValueError(f"队列写入行为变化 {label}：期望 RpcError，实际未抛出")


def _add_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        skill_dir = workspace.workspace / ".boss-harness" / "skills" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: 演示技能\ndescription: 队列冲突检查\n---\n正文\n", encoding="utf-8")
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_error(lambda: service.on_queue_add({"threadId": "000000000000",
                                                                   "input": "x"}),
                                     "会话不存在", "入队未知线程")
            checked += _expect_error(lambda: service.on_queue_add({"threadId": thread_id, "input": ""}),
                                     "input 必须是非空字符串（最多 100000 字符）", "入队空正文")
            checked += _expect_error(lambda: service.on_queue_add({"threadId": thread_id, "input": "x",
                                                                   "skillIds": ["missing"]}),
                                     "技能不存在或不可读取", "入队未知技能")
            first = service.on_queue_add({"threadId": thread_id, "input": "排队消息",
                                          "clientUserMessageId": "client-1"})
            queue_id = first["queueItem"]["id"]
            checked += _expect_value(set(first), {"queueItem"}, "入队返回键")
            checked += _expect_value((first["queueItem"]["id"], first["queueItem"]["kind"],
                                      first["queueItem"]["input"], first["queueItem"]["clientUserMessageId"]),
                                     (queue_id, "followUp", "排队消息", "client-1"), "入队投影")
            retry = service.on_queue_add({"threadId": thread_id, "input": "排队消息",
                                          "clientUserMessageId": "client-1"})
            checked += _expect_value((retry["queueItem"]["id"], retry["queueItem"].get("deduplicated")),
                                     (queue_id, True), "入队幂等重试")
            checked += _expect_rpc(
                lambda: service.on_queue_add({"threadId": thread_id, "input": "另一条",
                                              "clientUserMessageId": "client-1"}),
                -32004, "clientUserMessageId 已用于不同输入",
                {"code": "CLIENT_REQUEST_CONFLICT"}, "入队客户端冲突")
            skilled = service.on_queue_add({"threadId": thread_id, "input": "技能消息",
                                            "clientUserMessageId": "client-2"})
            checked += _expect_value(skilled["queueItem"]["skillIds"], [], "入队技能空投影")
            checked += _expect_rpc(
                lambda: service.on_queue_add({"threadId": thread_id, "input": "技能消息",
                                              "clientUserMessageId": "client-2",
                                              "skillIds": ["demo"]}),
                -32004, "clientUserMessageId 已用于不同技能组合",
                {"code": "CLIENT_REQUEST_CONFLICT"}, "入队技能冲突")
            archived = service.on_thread_start({})["thread"]["id"]
            service.on_thread_archive({"threadId": archived})
            checked += _expect_rpc(lambda: service.on_queue_add({"threadId": archived, "input": "x"}),
                                    -32004, "请先恢复归档会话，再添加排队消息", None, "入队归档会话")
            events = workspace.take()
            checked += _expect_value(any(event.get("method") == "queue/updated"
                                         for event in events), True, "入队广播")
        finally:
            service.close()
    return checked


def _update_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            service.sessions.append(thread_id, Entry(type="queue", payload={
                "id": "q-edit", "kind": "followUp", "status": "queued", "input": "旧正文"}))
            service.sessions.append(thread_id, Entry(type="queue", payload={
                "id": "q-done", "kind": "followUp", "status": "delivered", "input": "已投递"}))
            workspace.take()
            updated = service.on_queue_update({"threadId": thread_id, "queueId": "q-edit",
                                               "input": "新正文"})
            checked += _expect_value(updated, {"queueItem": {"id": "q-edit", "kind": "followUp",
                                                             "status": "queued", "input": "新正文"}},
                                     "编辑投影")
            checked += _expect_value(service.on_queue_get({"threadId": thread_id,
                                                           "queueId": "q-edit"}),
                                     {"queueItem": {"id": "q-edit", "kind": "followUp",
                                                    "status": "queued", "input": "新正文"}}, "编辑回读")
            checked += _expect_error(lambda: service.on_queue_update(
                {"threadId": thread_id, "queueId": "q-done", "input": "x"}),
                "只有排队中的消息可以编辑", "编辑已投递")
            checked += _expect_error(lambda: service.on_queue_update(
                {"threadId": thread_id, "queueId": "nope", "input": "x"}),
                "队列项不存在", "编辑未知项")
            checked += _expect_error(lambda: service.on_queue_update(
                {"threadId": thread_id, "queueId": "q-edit", "input": ""}),
                "input 必须是非空字符串（最多 100000 字符）", "编辑空正文")
            checked += _expect_error(lambda: service.on_queue_update(
                {"threadId": "000000000000", "queueId": "q-edit", "input": "x"}),
                "会话不存在", "编辑未知线程")
            events = workspace.take()
            checked += _expect_value(any(event.get("method") == "queue/updated"
                                         and event.get("params", {}).get("queueId") == "q-edit"
                                         for event in events), True, "编辑广播")
        finally:
            service.close()
    return checked


def _remove_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            service.sessions.append(thread_id, Entry(type="queue", payload={
                "id": "q-drop", "kind": "followUp", "status": "queued", "input": "待取消"}))
            workspace.take()
            removed = service.on_queue_remove({"threadId": thread_id, "queueId": "q-drop"})
            checked += _expect_value(removed, {"queueItem": {"id": "q-drop", "kind": "followUp",
                                                             "status": "cancelled", "input": "待取消"}},
                                     "取消投影")
            checked += _expect_value(service.on_queue_get({"threadId": thread_id,
                                                           "queueId": "q-drop"})["queueItem"]["status"],
                                     "cancelled", "取消回读")
            checked += _expect_error(lambda: service.on_queue_remove(
                {"threadId": thread_id, "queueId": "q-drop"}),
                "队列项已投递或状态不允许此操作", "取消重试")
            checked += _expect_error(lambda: service.on_queue_remove(
                {"threadId": thread_id, "queueId": "nope"}),
                "队列项不存在", "取消未知项")
            checked += _expect_error(lambda: service.on_queue_remove(
                {"threadId": "000000000000", "queueId": "q-drop"}),
                "会话不存在", "取消未知线程")
            events = workspace.take()
            checked += _expect_value(any(event.get("method") == "queue/updated"
                                         and event.get("params", {}).get("queueId") == "q-drop"
                                         for event in events), True, "取消广播")
        finally:
            service.close()
    return checked


def _steer_interrupt_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_value(service.on_turn_interrupt({"threadId": thread_id}),
                                     {"interrupted": False}, "中断无回合")
            checked += _expect_value(service.on_turn_interrupt({"threadId": thread_id,
                                                                "turnId": "turn-1"}),
                                     {"interrupted": False}, "中断指定回合")
            checked += _expect_error(lambda: service.on_turn_interrupt({}),
                                     "threadId 必须是非空字符串（最多 100000 字符）", "中断缺线程")
            checked += _expect_error(lambda: service.on_turn_interrupt({"threadId": thread_id,
                                                                        "turnId": "x" * 129}),
                                     "turnId 必须是非空字符串（最多 128 字符）", "中断回合上限")
            checked += _expect_rpc(lambda: service.on_turn_steer(
                {"threadId": thread_id, "expectedTurnId": "turn-1", "input": "插话"}),
                -32004, "目标回合已经结束或发生变化", None, "插话无回合")
            checked += _expect_rpc(lambda: service.on_turn_steer(
                {"threadId": "000000000000", "expectedTurnId": "turn-1", "input": "插话"}),
                -32004, "目标回合已经结束或发生变化", None, "插话未知线程")
            checked += _expect_rpc(lambda: service.on_queue_steer(
                {"threadId": thread_id, "queueId": "q-edit", "expectedTurnId": "turn-1"}),
                -32004, "目标回合已经结束或发生变化", {"code": "STEER_UNAVAILABLE"}, "排队转插话无回合")
            checked += _expect_error(lambda: service.on_queue_steer(
                {"threadId": "000000000000", "queueId": "q-edit", "expectedTurnId": "turn-1"}),
                "会话不存在", "排队转插话未知线程")
        finally:
            service.close()
    return checked


def _approval_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            empty = service.on_approval_list(None)
            checked += _expect_value(empty, {"approvals": [], "truncated": False, "threadCounts": {}},
                                     "审批列表空投影")
            checked += _expect_value(service.on_approval_list({"threadId": thread_id}), empty,
                                     "审批列表线程过滤")
            checked += _expect_error(lambda: service.on_approval_list([]),
                                     "审批查询参数必须是对象", "审批列表参数类型")
            checked += _expect_error(lambda: service.on_approval_list({"cursor": "x"}),
                                     "审批查询只接受 threadId 和 limit", "审批列表多余键")
            checked += _expect_error(lambda: service.on_approval_list({"limit": 0}),
                                     "limit 必须是 1 到 200 之间的整数", "审批列表范围")
            checked += _expect_error(lambda: service.on_approval_list({"limit": True}),
                                     "limit 必须是 1 到 200 之间的整数", "审批列表布尔")
            checked += _expect_error(lambda: service.on_approval_list({"threadId": "x" * 65}),
                                     "threadId 必须是非空字符串（最多 64 字符）", "审批列表线程上限")
            checked += _expect_error(lambda: service.on_approval_list({"threadId": "000000000000"}),
                                     "会话不存在", "审批列表未知线程")
            checked += _expect_error(lambda: service.on_approval_respond(
                {"approvalId": "a" * 32, "approved": True, "extra": 1}),
                "审批响应只能包含 approvalId 和 approved", "审批响应多余键")
            checked += _expect_error(lambda: service.on_approval_respond(
                {"approvalId": "a" * 32, "approved": "yes"}),
                "approved 必须是布尔值", "审批响应非布尔")
            checked += _expect_error(lambda: service.on_approval_respond(
                {"approvalId": "x" * 65, "approved": True}),
                "approvalId 必须是非空字符串（最多 64 字符）", "审批响应标识上限")
            checked += _expect_rpc(lambda: service.on_approval_respond(
                {"approvalId": "approval-" + "0" * 23, "approved": True}),
                -32004, "approvalId 格式无效",
                {"code": "APPROVAL_INVALID", "approvalId": "approval-" + "0" * 23}, "审批响应格式")
            checked += _expect_rpc(lambda: service.on_approval_respond(
                {"approvalId": "ab" * 16, "approved": True}),
                -32004, "审批不存在或所属会话已删除",
                {"code": "APPROVAL_NOT_FOUND", "approvalId": "ab" * 16}, "审批响应未知")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_queue.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_queue.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少队列写入检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_add_checks(), _update_checks(), _remove_checks(),
                     _steer_interrupt_checks(), _approval_checks()))
    _check_documentation(structures, behaviors)
    print(f"队列写入与审批入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
