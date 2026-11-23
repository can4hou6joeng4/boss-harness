#!/usr/bin/env python3
"""核对分支指针入口：thread/leaf/read、thread/leaf/set。

读取返回六项投影（线程、是否分叉、叶子回合、活动回合数与列表、截断标记）；写入严格
限定 threadId、turnId（字符串或 null）与可选 summarize（布尔），并在移动前检查运行中
回合、工具结果围栏、后续任务、请求回执、队列投递与归档，全部拒绝都发生在指针移动
之前。带 summarize 时先做摘要预检：provider=none 返回 -32013 且分支保持不动。指针
真正移动才广播 thread/leafChanged；目标与当前一致时 changed 为 false 且不发事件。
这里在临时工作区与状态目录中真实构造 `ApplicationService`（provider=none），逐项
验证投影、拒绝分支与广播语义；静态部分锁定两个 handler 的校验顺序。
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
LEAF_READ = (
    '        params = params or {}',
    '        if set(params) != {"threadId"}:',
    '            raise ValueError("thread/leaf/read 只接受 threadId")',
    '        return self.sessions.read_leaf(_text(params, "threadId"))',
)
LEAF_SET = (
    '        params = params or {}',
    '        if not {"threadId", "turnId"} <= set(params) <= {"threadId", "turnId", "summarize"}:',
    '            raise ValueError("thread/leaf/set 只接受 threadId、turnId（可为 null）与可选 summarize")',
    '        thread_id = _text(params, "threadId")',
    '        turn_id = params["turnId"]',
    "        if turn_id is not None and not isinstance(turn_id, str):",
    '            raise ValueError("turnId 必须是字符串或 null")',
    '        summarize = params.get("summarize", False)',
    "        if type(summarize) is not bool:",
    '            raise ValueError("summarize 必须是布尔值")',
    "        job: dict[str, Any] | None = None",
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    "            self._idle(thread_id)",
    "            if thread_id in self._tool_persistence_fences:",
    '                raise RpcError(-32004, "工具结果持久化状态需要人工核对，暂不能切换分支")',
    "            if any(owner == thread_id for owner in self._follow_up_worker_threads.values()):",
    '                raise RpcError(-32004, "该会话仍有后续任务正在收尾")',
    '            if any(notice.get("threadId") == thread_id for notice in self._receipt_notices.values()):',
    '                raise RpcError(-32004, "该会话请求回执仍在收尾")',
    "            with self.queue.lock:",
    '                if any(item.get("status") == "delivering" for item in self.queue.list(thread_id)):',
    '                    raise RpcError(-32004, "队列中仍有投递状态未核对的请求")',
    '                if self.sessions.get_thread(thread_id).get("archived"):',
    '                    raise RpcError(-32004, "请先恢复会话，再切换分支")',
    "                prepared = self._prepare_branch_summary(thread_id, turn_id) if summarize else None",
    "                result = self.sessions.set_leaf(thread_id, turn_id, _with_entry_id=True)",
    '                leaf_entry_id = result.pop("_leafEntryId", None)',
    '                if result.get("changed"):',
    "                    self.snapshots.invalidate_branch(thread_id, leaf_entry_id)",
    "                if prepared is not None and leaf_entry_id is not None:",
    "                    job = self._register_branch_summary(thread_id, leaf_entry_id, *prepared)",
    '        if result.get("changed"):',
    '            self._emit_committed("thread/leafChanged", {"threadId": thread_id, "leafTurnId": result["leafTurnId"]})',
    "        if job is not None:",
    '            result["summaryJob"] = self._launch_branch_summary(job)',
)
READ_KEYS = {"threadId", "branched", "leafTurnId", "activeTurnCount", "activeTurnIds",
             "activeTurnIdsTruncated"}


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
    for name, fragments in (("on_thread_leaf_read", LEAF_READ), ("on_thread_leaf_set", LEAF_SET)):
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


def _seed(service: ApplicationService, thread_id: str, turn_id: str, status: str) -> None:
    service.sessions.record_turn(thread_id, turn_id, status)
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "userMessage", "text": turn_id, "turnId": turn_id}))


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"分支指针行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"分支指针行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"分支指针行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        actual = (error.code, str(error), error.data)
        if actual != (code, message, data):
            raise ValueError(f"分支指针行为变化 {label}：期望 {(code, message, data)!r}，"
                             f"实际 {actual!r}") from None
        return 1
    raise ValueError(f"分支指针行为变化 {label}：期望 RpcError，实际未抛出")


def _read_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_error(lambda: service.on_thread_leaf_read({}),
                                     "thread/leaf/read 只接受 threadId", "读取缺键")
            checked += _expect_error(lambda: service.on_thread_leaf_read(
                {"threadId": thread_id, "extra": 1}), "thread/leaf/read 只接受 threadId", "读取多余键")
            checked += _expect_error(lambda: service.on_thread_leaf_read({"threadId": "000000000000"}),
                                     "会话不存在", "读取未知线程")
            empty = service.on_thread_leaf_read({"threadId": thread_id})
            checked += _expect_value(set(empty), READ_KEYS, "读取投影键")
            checked += _expect_value((empty["threadId"], empty["branched"], empty["leafTurnId"],
                                      empty["activeTurnCount"], empty["activeTurnIds"],
                                      empty["activeTurnIdsTruncated"]),
                                     (thread_id, False, None, 0, [], False), "读取空线程投影")
            _seed(service, thread_id, "turn-1", "completed")
            _seed(service, thread_id, "turn-2", "completed")
            loaded = service.on_thread_leaf_read({"threadId": thread_id})
            checked += _expect_value((loaded["branched"], loaded["leafTurnId"],
                                      loaded["activeTurnCount"], loaded["activeTurnIds"]),
                                     (False, "turn-2", 2, ["turn-1", "turn-2"]), "读取两回合投影")
        finally:
            service.close()
    return checked


def _moved_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id, "turn-1", "completed")
            _seed(service, thread_id, "turn-2", "completed")
            checked += _expect_error(lambda: service.on_thread_leaf_set({"threadId": thread_id}),
                                     "thread/leaf/set 只接受 threadId、turnId（可为 null）与可选 summarize",
                                     "写入缺键")
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": None, "extra": 1}),
                "thread/leaf/set 只接受 threadId、turnId（可为 null）与可选 summarize", "写入多余键")
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": 5}), "turnId 必须是字符串或 null", "写入回合类型")
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": None, "summarize": 1}),
                "summarize 必须是布尔值", "写入摘要开关类型")
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": "000000000000", "turnId": None}), "会话不存在", "写入未知线程")
            workspace.take()
            moved = service.on_thread_leaf_set({"threadId": thread_id, "turnId": "turn-1"})
            checked += _expect_value(set(moved), READ_KEYS | {"changed"}, "移动返回键")
            checked += _expect_value((moved["changed"], moved["branched"], moved["leafTurnId"],
                                      moved["activeTurnCount"], moved["activeTurnIds"]),
                                     (True, True, "turn-1", 1, ["turn-1"]), "移动投影")
            events = [event for event in workspace.take()
                      if event.get("method") == "thread/leafChanged"]
            checked += _expect_value(len(events), 1, "移动广播次数")
            checked += _expect_value(events[0].get("params", {}).get("leafTurnId"), "turn-1",
                                     "移动广播载荷")
            checked += _expect_value(service.on_thread_leaf_read({"threadId": thread_id}),
                                     {key: moved[key] for key in READ_KEYS}, "移动回读一致")
            again = service.on_thread_leaf_set({"threadId": thread_id, "turnId": "turn-1"})
            checked += _expect_value((again["changed"], again["leafTurnId"]), (False, "turn-1"),
                                     "移动幂等")
            checked += _expect_value(workspace.take(), [], "移动幂等不广播")
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": "turn-9"}),
                "仅可把分支指针移到已经结束的回合", "移动未知回合")
            checked += _expect_rpc(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": None, "summarize": True}), -32013,
                "被放弃分支摘要需要可用模型线路（当前 provider=none）；分支未切换，可不带 summarize 重试",
                {"code": "BRANCH_SUMMARY_MODEL_UNAVAILABLE", "provider": "none"}, "摘要预检失败")
            checked += _expect_value(service.on_thread_leaf_read({"threadId": thread_id}),
                                     {key: moved[key] for key in READ_KEYS}, "摘要预检不改指针")
            checked += _expect_value(workspace.take(), [], "摘要预检不广播")
            rewound = service.on_thread_leaf_set({"threadId": thread_id, "turnId": None})
            checked += _expect_value((rewound["changed"], rewound["leafTurnId"],
                                      rewound["activeTurnCount"], rewound["branched"]),
                                     (True, None, 0, True), "回到起点投影")
            events = [event for event in workspace.take()
                      if event.get("method") == "thread/leafChanged"]
            checked += _expect_value((len(events), events[0].get("params", {}).get("leafTurnId")),
                                     (1, None), "回起点广播载荷")
            checked += _expect_value(service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": None})["changed"], False, "回起点幂等")
            archived = service.on_thread_start({})["thread"]["id"]
            service.on_thread_archive({"threadId": archived})
            checked += _expect_rpc(lambda: service.on_thread_leaf_set(
                {"threadId": archived, "turnId": None}), -32004, "请先恢复会话，再切换分支",
                None, "写入归档会话")
        finally:
            service.close()
    return checked


def _running_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id, "turn-1", "completed")
            _seed(service, thread_id, "turn-2", "running")
            workspace.take()
            checked += _expect_error(lambda: service.on_thread_leaf_set(
                {"threadId": thread_id, "turnId": "turn-1"}),
                "会话仍有未结束的回合，不能切换分支", "未结束回合拒绝")
            checked += _expect_value(workspace.take(), [], "未结束回合不广播")
            checked += _expect_value(service.on_thread_leaf_read({"threadId": thread_id})["branched"],
                                     False, "未结束回合保持未分叉")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_leaf.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_leaf.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少分支指针检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_read_checks(), _moved_checks(), _running_checks()))
    _check_documentation(structures, behaviors)
    print(f"分支指针入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
