#!/usr/bin/env python3
"""核对回合启动与续接入口：turn/start、turn/continue。

`turn/start` 先校验线程 / 正文 / 客户端请求编号，再在准入锁内检查归档、摘要与持久化
围栏；成功启动返回 `turnId` 与 `clientUserMessageId`，同一请求编号重试返回 `deduplicated`
与同一回合，不同输入报 `CLIENT_REQUEST_CONFLICT`。`turn/continue` 严格限定三项参数，
校验来源回合与续接编号格式，已完成回合以 `CONTINUATION_NOT_INTERRUPTED` 与原因拒绝。
这里在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），验证拒绝
分支、回合落库与幂等投影；静态部分锁定两个 handler 的校验顺序。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer, RpcError  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
TURN_START = (
    '        params = params or {}',
    '        if queue_item is None:',
    '            thread_id, text = _text(params, "threadId"), _text(params, "input")',
    '            client_id = params.get("clientUserMessageId")',
    '                raise ValueError("clientUserMessageId 格式无效")',
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    '                if thread.get("archived"):',
    '                    raise ValueError("请先恢复归档会话")',
    '                    raise RpcError(-32004, "该会话已有回合运行",',
    '                                   {"turnId": self.runtimes.active[thread_id]["turnId"]})',
    '                    raise RpcError(-32004, "该会话正在生成摘要，请等待完成或先取消摘要")',
    '                    raise RpcError(-32004, "该会话的工具结果尚未完成持久化核对，请重启内核后重新读取状态",',
    '                                   {"code": "THREAD_REQUIRES_REVIEW"})',
    '                    raise RpcError(-32005, "已有更早排队的后续回合等待并发槽位",',
    '                                   {"code": "TURN_ADMISSION_WAITING", "limit": self.runtimes.capacity})',
    "            return self._on_turn_start(params, queue_item=queue_item)",
)
TURN_CONTINUE = (
    '        if set(params) != {"threadId", "sourceTurnId", "continuationId"}:',
    '            raise ValueError("turn/continue 参数无效")',
    '        thread_id = _text(params, "threadId")',
    '        source_turn_id = _text(params, "sourceTurnId", maximum=128)',
    '        continuation_id = _text(params, "continuationId", maximum=128)',
    '        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", source_turn_id) is None:',
    '            raise ValueError("sourceTurnId 格式无效")',
    '        if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", continuation_id) is None:',
    '            raise ValueError("continuationId 格式无效")',
    "                self.sessions.require_thread(thread_id)",
    '                    raise RpcError(-32004, "会话历史超过续接读取上限。",',
    '                                   {"code": "CONTINUATION_ID_CONFLICT"})',
    "            plan = self._turn_continuation_plan(thread_id, source_turn_id)",
    '            if not plan["eligible"]:',
    '                raise RpcError(-32004, plan.get("reason", "中断回合当前不能续接。"),',
    '                               {"code": plan.get("reasonCode", "CONTINUATION_REJECTED"),',
    '        return {"turnId": job["turnId"], "continuedFromTurnId": source_turn_id,',
    '                "continuationId": continuation_id}',
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
    for name, fragments in (("on_turn_start", TURN_START), ("on_turn_continue", TURN_CONTINUE)):
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
        raise ValueError(f"回合启动行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"回合启动行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"回合启动行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if (error.code, str(error), error.data) != (code, message, data):
            raise ValueError(f"回合启动行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                             f"实际 ({error.code}, {str(error)!r}, {error.data!r})") from None
        return 1
    raise ValueError(f"回合启动行为变化 {label}：期望 RpcError，实际未抛出")


def _wait_completed(service: ApplicationService, thread_id: str) -> dict:
    read = service.on_thread_read({"threadId": thread_id})
    for _ in range(100):
        read = service.on_thread_read({"threadId": thread_id})
        turns = read["turns"]
        if read["activeTurnId"] is None and turns and turns[-1].get("status") == "completed":
            return read
        time.sleep(0.05)
    return read


def _start_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": "000000000000", "input": "x"}), "会话不存在", "启动未知线程")
            checked += _expect_error(lambda: service.on_turn_start({"threadId": thread_id, "input": ""}),
                                     "input 必须是非空字符串（最多 100000 字符）", "启动空正文")
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "clientUserMessageId": "bad id"}),
                "clientUserMessageId 格式无效", "启动请求编号格式")
            checked += _expect_rpc(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "provider": "anthropic"}),
                -32013, "provider 由会话模型选择决定，不能按回合切换",
                {"code": "MODEL_PROVIDER_MISMATCH", "provider": "none"}, "启动线路不匹配")
            checked += _expect_rpc(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "model": "other"}),
                -32013, "回合模型不属于会话模型线路",
                {"code": "MODEL_ROUTE_MISMATCH", "provider": "none", "model": "other",
                 "available": ["none"]}, "启动模型不匹配")
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "skillIds": ["missing"]}),
                "技能不存在或不可读取", "启动未知技能")
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "attachmentIds": ["missing"]}),
                "附件不属于该会话", "启动未知附件")
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "maxModelRequests": 0}),
                "maxModelRequests 必须是 1 到 6 的整数", "启动请求上限")
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "x", "autoCompaction": {"x": 1}}),
                "autoCompaction 必须是只包含 enabled、triggerPercent、keepRecentTokens 的对象",
                "启动压缩覆盖")
            workspace.take()
            first = service.on_turn_start({"threadId": thread_id, "input": "你好",
                                           "clientUserMessageId": "client-9"})
            checked += _expect_value(set(first), {"turnId", "clientUserMessageId"}, "启动返回键")
            checked += _expect_value((isinstance(first["turnId"], str) and len(first["turnId"]) > 0,
                                      first["clientUserMessageId"]), (True, "client-9"), "启动返回投影")
            read = _wait_completed(service, thread_id)
            checked += _expect_value([(turn["turnId"], turn["status"]) for turn in read["turns"]],
                                     [(first["turnId"], "completed")], "启动回合落库")
            events = workspace.take()
            checked += _expect_value(any(event.get("method") == "turn/started"
                                         and event.get("params", {}).get("turnId") == first["turnId"]
                                         for event in events), True, "启动广播")
            repeat = service.on_turn_start({"threadId": thread_id, "input": "你好",
                                            "clientUserMessageId": "client-9"})
            checked += _expect_value((repeat, set(repeat)), ({"turnId": first["turnId"],
                                                              "clientUserMessageId": "client-9",
                                                              "deduplicated": True},
                                                             {"turnId", "clientUserMessageId", "deduplicated"}),
                                     "启动幂等重试")
            checked += _expect_rpc(lambda: service.on_turn_start(
                {"threadId": thread_id, "input": "另一条", "clientUserMessageId": "client-9"}),
                -32004, "clientUserMessageId 已用于不同输入",
                {"code": "CLIENT_REQUEST_CONFLICT"}, "启动客户端冲突")
            archived = service.on_thread_start({})["thread"]["id"]
            service.on_thread_archive({"threadId": archived})
            checked += _expect_error(lambda: service.on_turn_start(
                {"threadId": archived, "input": "x"}), "请先恢复归档会话", "启动归档会话")
        finally:
            service.close()
    return checked


def _continue_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_error(lambda: service.on_turn_continue({"threadId": thread_id}),
                                     "turn/continue 参数无效", "续接缺键")
            checked += _expect_error(lambda: service.on_turn_continue(
                {"threadId": thread_id, "sourceTurnId": "turn-1", "continuationId": "c-1",
                 "extra": 1}), "turn/continue 参数无效", "续接多余键")
            checked += _expect_error(lambda: service.on_turn_continue(
                {"threadId": "000000000000", "sourceTurnId": "turn-1", "continuationId": "c-1"}),
                "会话不存在", "续接未知线程")
            checked += _expect_error(lambda: service.on_turn_continue(
                {"threadId": thread_id, "sourceTurnId": "bad id!", "continuationId": "c-1"}),
                "sourceTurnId 格式无效", "续接来源格式")
            checked += _expect_error(lambda: service.on_turn_continue(
                {"threadId": thread_id, "sourceTurnId": "turn-1", "continuationId": "bad id!"}),
                "continuationId 格式无效", "续接编号格式")
            service.sessions.record_turn(thread_id, "turn-1", "completed")
            checked += _expect_rpc(lambda: service.on_turn_continue(
                {"threadId": thread_id, "sourceTurnId": "turn-1", "continuationId": "c-1"}),
                -32004, "来源回合不是可检查的中断状态。",
                {"code": "CONTINUATION_NOT_INTERRUPTED", "threadId": thread_id,
                 "sourceTurnId": "turn-1"}, "续接已完成回合")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_turn.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_turn.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少回合启动检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_start_checks(), _continue_checks()))
    _check_documentation(structures, behaviors)
    print(f"回合启动与续接入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
