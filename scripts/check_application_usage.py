#!/usr/bin/env python3
"""核对用量读取入口：thread/usage/read。

`thread/usage/read` 有两种视图：`log` 按完整日志聚合，包含被放弃分支的请求，并额外返回
`cacheWaste`；`branch` 只聚合当前分支，附 `branch` 叶子投影且不返回线性缓存估计。两者都
按页返回 `turns` 与 `nextCursor`，并带上 `summaryTasks`、逐任务 `summaryJobs` 与 `totals`。
视图参数走共享的 `_branch_view` 校验，非法值、多余键、未知线程与坏游标都在读取前拒绝。
这里在临时工作区真实构造 `ApplicationService`（`provider=none`），写入 `model_usage`
记录后跨分叉验证两种视图的回合集合、总量、分页与拒绝分支；静态部分锁定 handler 与
`_branch_view` 的校验顺序。
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
BRANCH_VIEW = (
    "def _branch_view(params: dict | None) -> bool:",
    '    view = (params or {}).get("view", "log")',
    '    if not isinstance(view, str) or view not in {"log", "branch"}:',
    '        raise ValueError("view 必须是 log 或 branch")',
    '    return view == "branch"',
)
USAGE_READ = (
    '        params = params or {}',
    '        if not set(params) <= {"threadId", "view", "cursor", "limit"}:',
    '            raise ValueError("thread/usage/read 只接受 threadId、view、cursor 与 limit")',
    '        thread_id = _text(params, "threadId")',
    "        with self.runtimes.lock:",
    "            entries = self.sessions.read_entries_snapshot(thread_id)",
    "            active_job_id = self.context.active_summary_job_id(thread_id, entries=entries)",
    "            result = self.sessions.usage_page(thread_id, branch=_branch_view(params),",
    '                                              cursor=params.get("cursor"), limit=params.get("limit", 50),',
    "                                              active_summary_job_id=active_job_id, entries=entries)",
    "        self._check_response_budget(result, usage=True)",
    "        return result",
)
TOTAL_KEYS = {"requests", "verifiedRequests", "unverifiedRequests", "unreportedRequests",
              "unverifiedReasons", "promptTokens", "uncachedInputTokens", "outputTokens",
              "cacheReadTokens", "cacheWriteTokens", "reasoningTokens", "costUsd", "costSource"}
LOG_KEYS = {"threadId", "view", "source", "costAvailable", "turnCount", "turns", "nextCursor",
            "summaryTasks", "totals", "summaryJobs", "summaryJobCount", "summaryJobsTruncated",
            "cacheWaste"}


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
    body = _method(tree, source, "on_thread_usage_read")
    position = -1
    for fragment in USAGE_READ:
        found = body.find(fragment, position + 1)
        if found < 0:
            raise ValueError(f"ApplicationService.on_thread_usage_read 的顺序缺少：{fragment}")
        position = found
        checked += 1
    position = -1
    for fragment in BRANCH_VIEW:
        found = source.find(fragment, position + 1)
        if found < 0:
            raise ValueError(f"_branch_view 的顺序缺少：{fragment}")
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


def _usage(service: ApplicationService, thread_id: str, turn_id: str, input_tokens: int,
           output_tokens: int, cache_read: int) -> None:
    service.sessions.append(thread_id, Entry(type="model_usage", payload={
        "turnId": turn_id, "provider": "openai", "model": "gpt-probe",
        "usage": {"input": input_tokens, "output": output_tokens,
                  "cache_read": cache_read, "cache_write": 0}}))


def _fork(service: ApplicationService, thread_id: str) -> None:
    """turn-1 之后把指针移回起点，再写入 turn-2：log 含两轮，branch 只有 turn-2。"""
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    _usage(service, thread_id, "turn-1", 100, 10, 50)
    service.on_thread_leaf_set({"threadId": thread_id, "turnId": None})
    service.sessions.record_turn(thread_id, "turn-2", "completed")
    _usage(service, thread_id, "turn-2", 200, 20, 100)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"用量读取行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"用量读取行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"用量读取行为变化 {label}：期望 ValueError，实际未抛出")


def _view_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            empty = service.on_thread_usage_read({"threadId": thread_id, "view": "log"})
            checked += _expect_value(set(empty), LOG_KEYS, "用量投影键")
            checked += _expect_value((empty["threadId"], empty["view"], empty["source"],
                                      empty["costAvailable"], empty["turnCount"], empty["turns"],
                                      empty["nextCursor"], empty["summaryJobs"],
                                      empty["summaryJobCount"], empty["summaryJobsTruncated"]),
                                     (thread_id, "log", "provider-usage", False, 0, [], None,
                                      [], 0, False), "用量空投影")
            checked += _expect_value((set(empty["totals"]), set(empty["summaryTasks"])),
                                     (TOTAL_KEYS, TOTAL_KEYS), "用量总量键")
            checked += _expect_value(empty["cacheWaste"], {"missCount": 0, "missedTokens": 0},
                                     "用量空缓存估计")
            checked += _expect_value(service.on_thread_usage_read({"threadId": thread_id}),
                                     empty, "用量默认视图")
            checked += _expect_error(lambda: service.on_thread_usage_read(
                {"threadId": thread_id, "extra": 1}),
                "thread/usage/read 只接受 threadId、view、cursor 与 limit", "用量多余键")
            checked += _expect_error(lambda: service.on_thread_usage_read(
                {"threadId": thread_id, "view": "both"}), "view 必须是 log 或 branch", "用量视图非法")
            checked += _expect_error(lambda: service.on_thread_usage_read(
                {"threadId": "000000000000"}), "会话不存在", "用量未知线程")
            checked += _expect_error(lambda: service.on_thread_usage_read(
                {"threadId": thread_id, "cursor": "bad"}), "分页游标无效", "用量坏游标")
            checked += _expect_error(lambda: service.on_thread_usage_read(
                {"threadId": thread_id, "limit": 0}), "limit 必须是 1 到 200 之间的整数", "用量上限")
        finally:
            service.close()
    return checked


def _aggregate_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _fork(service, thread_id)
            log = service.on_thread_usage_read({"threadId": thread_id, "view": "log"})
            checked += _expect_value((log["view"], log["turnCount"],
                                      [turn["turnId"] for turn in log["turns"]]),
                                     ("log", 2, ["turn-1", "turn-2"]), "用量日志回合")
            totals = log["totals"]
            checked += _expect_value((totals["requests"], totals["verifiedRequests"],
                                      totals["promptTokens"], totals["uncachedInputTokens"],
                                      totals["outputTokens"], totals["cacheReadTokens"]),
                                     (2, 2, 300, 150, 30, 150), "用量日志总量")
            checked += _expect_value(log["cacheWaste"], {"missCount": 0, "missedTokens": 0},
                                     "用量日志缓存估计")
            branch = service.on_thread_usage_read({"threadId": thread_id, "view": "branch"})
            checked += _expect_value(("cacheWaste" in branch, branch["view"], branch["turnCount"],
                                      [turn["turnId"] for turn in branch["turns"]]),
                                     (False, "branch", 1, ["turn-2"]), "用量分支回合")
            checked += _expect_value((branch["totals"]["requests"], branch["totals"]["promptTokens"],
                                      branch["totals"]["cacheReadTokens"]), (1, 200, 100),
                                     "用量分支总量")
            checked += _expect_value((branch["branch"]["leafTurnId"], branch["branch"]["branched"],
                                      branch["branch"]["activeTurnIds"]),
                                     ("turn-2", True, ["turn-2"]), "用量分支叶子")
            first = service.on_thread_usage_read({"threadId": thread_id, "view": "log", "limit": 1})
            checked += _expect_value(([turn["turnId"] for turn in first["turns"]],
                                      isinstance(first["nextCursor"], str)), (["turn-1"], True),
                                     "用量首页")
            second = service.on_thread_usage_read({"threadId": thread_id, "view": "log",
                                                   "cursor": first["nextCursor"], "limit": 1})
            checked += _expect_value(([turn["turnId"] for turn in second["turns"]],
                                      second["nextCursor"]), (["turn-2"], None), "用量次页")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_usage.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_usage.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少用量读取检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_view_checks(), _aggregate_checks()))
    _check_documentation(structures, behaviors)
    print(f"用量读取入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
