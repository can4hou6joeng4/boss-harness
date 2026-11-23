#!/usr/bin/env python3
"""核对续接、队列与关闭入口：turn/continuation/read、queue/list、queue/get、thread/resume、shutdown。

`turn/continuation/read` 只读判断来源回合是否可续接，并始终带上风险提示；不可续接时给出
固定的 `reasonCode` 与原因。`queue/list` 返回队列项、总数与按状态计数；`queue/get` 返回
单项并对超长正文按入队上限截断。`thread/resume` 是 `thread/read` 的只读别名；
`shutdown` 收敛服务状态并返回 `{"stopped": true}`。这里在临时工作区与状态目录中真实构造
`ApplicationService`（`provider=none`），写入已完成回合与队列条目，逐项验证投影与拒绝
分支；静态部分锁定这些 handler 的源码顺序。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402
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
CONTINUATION = (
    '        if set(params) != {"threadId", "sourceTurnId"}:',
    '            raise ValueError("turn/continuation/read 参数无效")',
    '        source_turn_id = _text(params, "sourceTurnId", maximum=128)',
    '        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", source_turn_id) is None:',
    '            raise ValueError("sourceTurnId 格式无效")',
    "        self.sessions.require_thread(thread_id)",
    "        plan = self._turn_continuation_plan(thread_id, source_turn_id)",
    '        result = {"threadId": thread_id, "sourceTurnId": source_turn_id,',
    '                  "eligible": plan["eligible"], "warning": CONTINUATION_WARNING}',
    '        for key in ("boundary", "completedToolCalls", "reasonCode", "reason"):',
)
QUEUE_LIST = (
    '        return self.queue.view(_text(params, "threadId"))',
)
QUEUE_GET = (
    '        item = queue_view_record(self.queue.get(_text(params, "threadId"), _text(params, "queueId")))',
    '        if len(item["input"]) > MAX_QUEUE_INPUT_CHARS:',
    '            item["input"] = item["input"][:MAX_QUEUE_INPUT_CHARS]',
    '            item["inputTruncated"] = True',
    '        return {"queueItem": item}',
)
RESUME = (
    "        return self.on_thread_read(params)",
)
SHUTDOWN = (
    "        self.close()",
    '        return {"stopped": True}',
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
    for name, fragments in (("on_turn_continuation_read", CONTINUATION),
                            ("on_queue_list", QUEUE_LIST), ("on_queue_get", QUEUE_GET),
                            ("on_thread_resume", RESUME), ("on_shutdown", SHUTDOWN)):
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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"续接入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"续接入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"续接入口行为变化 {label}：期望 ValueError，实际未抛出")


def _continuation_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            service.sessions.record_turn(thread_id, "turn-1", "completed")
            plan = service.on_turn_continuation_read({"threadId": thread_id, "sourceTurnId": "turn-1"})
            checked += _expect_value(set(plan), {"threadId", "sourceTurnId", "eligible", "warning",
                                                 "reasonCode", "reason"}, "续接读取键")
            checked += _expect_value((plan["threadId"], plan["sourceTurnId"], plan["eligible"],
                                      plan["reasonCode"], plan["reason"]),
                                     (thread_id, "turn-1", False, "CONTINUATION_NOT_INTERRUPTED",
                                      "来源回合不是可检查的中断状态。"), "续接资格投影")
            checked += _expect_value(isinstance(plan["warning"], str) and "额外费用" in plan["warning"],
                                     True, "续接风险提示")
            checked += _expect_error(
                lambda: service.on_turn_continuation_read({"threadId": thread_id}),
                "turn/continuation/read 参数无效", "续接参数集合")
            checked += _expect_error(
                lambda: service.on_turn_continuation_read({"threadId": thread_id,
                                                           "sourceTurnId": "bad id!"}),
                "sourceTurnId 格式无效", "续接来源格式")
            checked += _expect_error(
                lambda: service.on_turn_continuation_read({"threadId": thread_id,
                                                           "sourceTurnId": "x" * 129}),
                "sourceTurnId 必须是非空字符串（最多 128 字符）", "续接来源上限")
            checked += _expect_error(
                lambda: service.on_turn_continuation_read({"threadId": "000000000000",
                                                           "sourceTurnId": "turn-1"}),
                "会话不存在", "续接未知线程")
        finally:
            service.close()
    return checked


def _queue_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            empty = service.on_queue_list({"threadId": thread_id})
            checked += _expect_value(set(empty), {"items", "totalItems", "activeItems", "truncated",
                                                  "counts"}, "队列列表键")
            checked += _expect_value((empty["items"], empty["totalItems"], empty["activeItems"],
                                      empty["truncated"], empty["counts"]),
                                     ([], 0, 0, False, {"queued": 0, "delivering": 0, "paused": 0}),
                                     "空队列投影")
            service.sessions.append(thread_id, Entry(type="queue", payload={
                "id": "queue-1", "kind": "followUp", "status": "queued", "input": "排队消息"}))
            service.sessions.append(thread_id, Entry(type="queue", payload={
                "id": "queue-2", "kind": "steering", "status": "paused", "input": "插话消息"}))
            listed = service.on_queue_list({"threadId": thread_id})
            checked += _expect_value([(item["id"], item["kind"], item["status"], item["input"])
                                      for item in listed["items"]],
                                     [("queue-1", "followUp", "queued", "排队消息"),
                                      ("queue-2", "steering", "paused", "插话消息")], "队列条目投影")
            checked += _expect_value((listed["totalItems"], listed["activeItems"], listed["counts"]),
                                     (2, 2, {"queued": 1, "delivering": 0, "paused": 1}), "队列计数")
            item = service.on_queue_get({"threadId": thread_id, "queueId": "queue-1"})
            checked += _expect_value(set(item), {"queueItem"}, "队列项读取键")
            checked += _expect_value(item["queueItem"], {"id": "queue-1", "status": "queued",
                                                         "input": "排队消息", "kind": "followUp"},
                                     "队列项投影")
            checked += _expect_error(lambda: service.on_queue_get({"threadId": thread_id,
                                                                   "queueId": "nope"}),
                                     "队列项不存在", "未知队列项")
            checked += _expect_error(lambda: service.on_queue_list({}),
                                     "threadId 必须是非空字符串（最多 100000 字符）", "队列线程参数")
            checked += _expect_error(lambda: service.on_queue_get({"threadId": thread_id}),
                                     "queueId 必须是非空字符串（最多 100000 字符）", "队列项参数")
        finally:
            service.close()
    return checked


def _resume_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            resumed = service.on_thread_resume({"threadId": thread_id})
            checked += _expect_value(set(resumed), {"activeTurnId", "eventCursor", "items", "queue",
                                                    "queueActiveItems", "queueCounts", "queueTotalItems",
                                                    "queueTruncated", "thread", "turns"}, "恢复读取键")
            checked += _expect_value((resumed["thread"]["id"], resumed["thread"]["title"],
                                      resumed["turns"], resumed["items"], resumed["activeTurnId"]),
                                     (thread_id, "新会话", [], [], None), "恢复读取投影")
            read = service.on_thread_read({"threadId": thread_id})
            checked += _expect_value(resumed, read, "恢复与读取一致")
        finally:
            service.close()
    return checked


def _shutdown_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            checked += _expect_value(service.on_shutdown(None), {"stopped": True}, "关闭结果")
            checked += _expect_value(service._state, "stopped", "关闭状态")
            checked += _expect_value(service.on_shutdown(None), {"stopped": True}, "重复关闭幂等")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_continuation.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_continuation.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少续接检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_continuation_checks(), _queue_checks(), _resume_checks(), _shutdown_checks()))
    _check_documentation(structures, behaviors)
    print(f"续接与队列入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
