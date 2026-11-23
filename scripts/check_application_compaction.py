#!/usr/bin/env python3
"""核对上下文压缩入口：context/compact、context/compact/plan、context/compact/start、
context/compact/abort、context/compact/read。

同步提交先校验线程存在与空闲状态，成功时返回上下文读取投影并带检查点；重复提交以
「没有新增可压缩内容」拒绝。计划入口返回 18 项投影，拒绝未知回合与越界保留量。后台
摘要入口校验模型格式（`-32602`）与并发上限，任务读取 / 中止对未知标识返回
`COMPACTION_JOB_NOT_FOUND`。这里在临时工作区与状态目录中真实构造 `ApplicationService`
（`provider=none`），验证拒绝分支与同步提交回执；静态部分锁定五个 handler 的校验顺序。
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
COMPACT = (
    '        thread_id = _text(params, "threadId")',
    "        committed = False",
    "            with self.runtimes.lock:",
    "                self.sessions.require_thread(thread_id)",
    "                self._idle(thread_id)",
    "                source_digest = self._source_digest(params or {})",
    '                self.context.compact(thread_id, _text(params, "summary", maximum=32_000),',
    '                                     _text(params, "throughTurnId"), source_digest, _on_committed=published)',
    '                result = self.on_context_read({"threadId": thread_id})',
    '            self.events.emit("context/compacted", {"threadId": thread_id})',
    "            return result",
    "        except (CheckpointCommittedError, CheckpointCommitUncertain) as exc:",
    '            raise RpcError(-32012, str(exc), {"code": exc.code, "threadId": thread_id,',
    '                           "checkpointCommitted": True if isinstance(exc, CheckpointCommittedError) else None}) from None',
    "            if committed:",
    '                raise RpcError(-32012, "摘要已提交并生效，但状态刷新或通知失败；请重新读取上下文，不要重复提交。",',
    '                           {"code": "COMPACTION_COMMITTED_REFRESH_FAILED", "threadId": thread_id,',
)
COMPACT_GUARD = (
    '        if "keepRecentTokens" in params and (type(keep) is not int or not 1 <= keep <= 1_000_000):',
    '            raise ValueError("keepRecentTokens 必须是 1 到 1000000 之间的整数")',
)
COMPACT_PLAN = (
    "        with self.runtimes.lock:",
    "            return self._compaction_plan(params or {})",
)
COMPACT_START = (
    '        thread_id = _text(params, "threadId")',
    '        model_override = None',
    '        if "model" in params:',
    "                model_override = self._validate_model_id(params[\"model\"])",
    "                raise RpcError(-32602, str(exc)) from None",
    '        source_digest = self._source_digest(params)',
    "        with self.runtimes.lock:",
    "            if self.runtimes.closed:",
    '                raise RpcError(-32003, "内核正在关闭")',
    "            self._idle(thread_id)",
    "            if thread_id in self._compaction_by_thread:",
    '                raise RpcError(-32004, "该会话已经有摘要任务在运行")',
    '            plan = self._compaction_plan(params)',
    "            config = self._model_config(self.sessions.get_thread(thread_id), {})",
    "            config = self._compaction_model_config(self.compaction_policy, config,",
    "                                                   model_override=model_override)",
    "            if active_manual >= self.runtimes.capacity:",
    '                raise RpcError(-32005, "已达到后台摘要并发上限",',
    '                               {"code": "COMPACTION_CONCURRENCY_LIMIT", "limit": self.runtimes.capacity})',
    '                raise RpcError(-32005, "模型供应商实例正在被其他任务使用，无法安全隔离摘要请求")',
    '            self._emit_committed("context/compactionStarted", self._compaction_public(job))',
    "        return self._compaction_public(job)",
)
COMPACT_ABORT = (
    '        job_id = _text(params, "jobId", maximum=128)',
    "        with self.runtimes.lock:",
    "            job = self._compaction_jobs.get(job_id)",
    "            if job is None:",
    "                raise self._missing_compaction_job()",
    '            if job["status"] != "running":',
    '                return {"aborted": False, **self._compaction_public(job)}',
    "            aborts = [self._claim_compaction_abort_locked(job)]",
    '            result = {"aborted": True, **self._compaction_public(job)}',
    "        for abort in aborts:",
    "            abort.start()",
    "        return result",
)
COMPACT_READ = (
    '        job_id = _text(params, "jobId", maximum=128)',
    "        with self.runtimes.lock:",
    "            job = self._compaction_jobs.get(job_id)",
    "            if job is None:",
    "                raise self._missing_compaction_job()",
    "            public = self._compaction_public(job)",
    '            if (public["status"] != "running"',
    '                    and self._compaction_by_thread.get(job["threadId"]) == job["jobId"]):',
    '                public["status"] = "running"',
    "            return public",
)
PLAN_KEYS = {"threadId", "throughTurnId", "sourceItemIds", "digestVersion", "sourceDigest",
             "sourceItemCount", "firstItemId", "lastItemId", "selection", "keepRecentTokens",
             "retainedItemCount", "retainedTurnIds", "firstKeptItemId", "estimatedRetainedTokens",
             "retentionEstimateMethod", "retentionUsageApplied", "retentionUsageAnchorCount",
             "checkpointDigest"}


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
    methods = (("on_context_compact", COMPACT), ("on_context_compact_plan", COMPACT_PLAN),
               ("on_context_compact_start", COMPACT_START), ("on_context_compact_abort", COMPACT_ABORT),
               ("on_context_compact_read", COMPACT_READ), ("_compaction_plan", COMPACT_GUARD))
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


def _seed(service: ApplicationService, thread_id: str) -> None:
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "userMessage", "text": "你好", "turnId": "turn-1"}))


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"压缩入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"压缩入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"压缩入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if (error.code, str(error), error.data) != (code, message, data):
            raise ValueError(f"压缩入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                             f"实际 ({error.code}, {str(error)!r}, {error.data!r})") from None
        return 1
    raise ValueError(f"压缩入口行为变化 {label}：期望 RpcError，实际未抛出")


def _plan_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            checked += _expect_error(lambda: service.on_context_compact_plan({}),
                                     "threadId 必须是非空字符串（最多 100000 字符）", "计划缺线程")
            checked += _expect_error(lambda: service.on_context_compact_plan(
                {"threadId": "000000000000"}), "会话不存在", "计划未知线程")
            checked += _expect_error(lambda: service.on_context_compact_plan(
                {"threadId": thread_id, "throughTurnId": "nope"}), "回合不存在", "计划未知回合")
            checked += _expect_error(lambda: service.on_context_compact_plan(
                {"threadId": thread_id, "keepRecentTokens": 0}),
                "keepRecentTokens 必须是 1 到 1000000 之间的整数", "计划保留量")
            checked += _expect_error(lambda: service.on_context_compact_plan(
                {"threadId": thread_id}), "保留近期完整回合后，没有更早的可压缩内容", "计划无可压缩")
            plan = service.on_context_compact_plan({"threadId": thread_id, "throughTurnId": "turn-1"})
            checked += _expect_value(set(plan), PLAN_KEYS, "计划投影键")
            checked += _expect_value((plan["threadId"], plan["throughTurnId"], plan["selection"],
                                      plan["sourceItemCount"], plan["retainedItemCount"],
                                      plan["digestVersion"]),
                                     (thread_id, "turn-1", "explicit", 1, 0, 2), "计划投影值")
            checked += _expect_value(isinstance(plan["sourceDigest"], str) and len(plan["sourceDigest"]) == 64,
                                     True, "计划摘要长度")
            checked += _expect_value(plan["sourceItemIds"], [plan["firstItemId"]], "计划来源条目")
            checked += _expect_value(plan["lastItemId"], plan["firstItemId"], "计划末条目")
            checked += _expect_value((plan["checkpointDigest"], plan["retainedTurnIds"], plan["firstKeptItemId"]),
                                     (None, [], None), "计划空检查点")
        finally:
            service.close()
    return checked


def _start_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            checked += _expect_error(lambda: service.on_context_compact_start({}),
                                     "threadId 必须是非空字符串（最多 100000 字符）", "启动缺线程")
            checked += _expect_rpc(lambda: service.on_context_compact_start(
                {"threadId": thread_id, "model": 5}), -32602, "model 格式无效", None, "启动模型格式")
            checked += _expect_error(lambda: service.on_context_compact_start(
                {"threadId": "000000000000"}), "会话不存在", "启动未知线程")
            checked += _expect_error(lambda: service.on_context_compact_start({"threadId": thread_id}),
                                     "保留近期完整回合后，没有更早的可压缩内容", "启动无可压缩")
            checked += _expect_error(lambda: service.on_context_compact_start(
                {"threadId": thread_id, "throughTurnId": "nope"}), "回合不存在", "启动未知回合")
        finally:
            service.close()
    return checked


def _job_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            checked += _expect_error(lambda: service.on_context_compact_abort({}),
                                     "jobId 必须是非空字符串（最多 128 字符）", "中止缺标识")
            checked += _expect_error(lambda: service.on_context_compact_abort({"jobId": "x" * 129}),
                                     "jobId 必须是非空字符串（最多 128 字符）", "中止标识上限")
            checked += _expect_rpc(lambda: service.on_context_compact_abort({"jobId": "nope"}),
                                   -32011, "摘要任务不存在或已过期",
                                   {"code": "COMPACTION_JOB_NOT_FOUND"}, "中止未知任务")
            checked += _expect_error(lambda: service.on_context_compact_read({}),
                                     "jobId 必须是非空字符串（最多 128 字符）", "读取缺标识")
            checked += _expect_rpc(lambda: service.on_context_compact_read({"jobId": "nope"}),
                                   -32011, "摘要任务不存在或已过期",
                                   {"code": "COMPACTION_JOB_NOT_FOUND"}, "读取未知任务")
        finally:
            service.close()
    return checked


def _compact_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            checked += _expect_error(lambda: service.on_context_compact({"threadId": thread_id}),
                                     "summary 必须是非空字符串（最多 32000 字符）", "提交缺摘要")
            checked += _expect_error(lambda: service.on_context_compact(
                {"threadId": thread_id, "summary": "", "throughTurnId": "turn-1"}),
                "summary 必须是非空字符串（最多 32000 字符）", "提交空摘要")
            checked += _expect_error(lambda: service.on_context_compact(
                {"threadId": "000000000000", "summary": "摘要正文", "throughTurnId": "turn-1"}),
                "会话不存在", "提交未知线程")
            checked += _expect_error(lambda: service.on_context_compact(
                {"threadId": thread_id, "summary": "摘要正文", "throughTurnId": "nope"}),
                "回合不存在", "提交未知回合")
            workspace.take()
            result = service.on_context_compact({"threadId": thread_id, "summary": "摘要正文",
                                                 "throughTurnId": "turn-1"})
            checked += _expect_value(len(result), 27, "提交上下文键数")
            checked += _expect_value((result["threadId"], result["checkpoint"]),
                                     (thread_id, {"summary": "摘要正文", "throughTurnId": "turn-1",
                                                  "sourceDigest": result["checkpoint"]["sourceDigest"],
                                                  "origin": "user", "digestVersion": 2,
                                                  "sourceItemIds": result["checkpoint"]["sourceItemIds"]}),
                                     "提交检查点投影")
            checked += _expect_value(result["provider"], "none", "提交线路")
            events = workspace.take()
            checked += _expect_value(any(event.get("method") == "context/compacted"
                                         and event.get("params", {}).get("threadId") == thread_id
                                         for event in events), True, "提交广播")
            checked += _expect_error(lambda: service.on_context_compact(
                {"threadId": thread_id, "summary": "摘要正文", "throughTurnId": "turn-1"}),
                "没有新增可压缩内容", "重复提交")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_compaction.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_compaction.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少压缩检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_plan_checks(), _start_checks(), _job_checks(), _compact_checks()))
    _check_documentation(structures, behaviors)
    print(f"上下文压缩入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
