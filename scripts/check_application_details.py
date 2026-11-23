#!/usr/bin/env python3
"""核对会话详情读取入口：用量、搜索、推理档位、分支、回合、任务与内容分页。

`thread/usage/read` 只报当前视图的聚合与预算；`thread/search` 有界跨会话搜索并默认
跳过归档；`thread/reasoning/read|set` 投影推理档位并拒绝未声明的档位；`thread/branches/list`
与 `thread/branchSummary/read` 枚举端点与读取被放弃分支摘要；`turn/list|read` 返回回合
与条目投影；`task/read` 把回合、队列与摘要任务收敛到同一 locator；`item/content/read`
与 `tool/result/read` 按摘要分页读取正文与工具结果。这里在临时工作区与状态目录中真实
构造 `ApplicationService`（`provider=none`）并写入已完成回合与三类条目，逐项验证投影、
拒绝分支与摘要校验；静态部分锁定这些 handler 的源码顺序。
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
from boss_harness.item_content import item_content_reference  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402
from boss_harness.session import Entry  # noqa: E402
from boss_harness.tool_results import canonical_result_text, result_reference  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
USAGE = (
    '        if not set(params) <= {"threadId", "view", "cursor", "limit"}:',
    '            raise ValueError("thread/usage/read 只接受 threadId、view、cursor 与 limit")',
    '        thread_id = _text(params, "threadId")',
    "        with self.runtimes.lock:",
    "            entries = self.sessions.read_entries_snapshot(thread_id)",
    "            active_job_id = self.context.active_summary_job_id(thread_id, entries=entries)",
    "            result = self.sessions.usage_page(thread_id, branch=_branch_view(params),",
    "        self._check_response_budget(result, usage=True)",
    "        return result",
)
SEARCH = (
    '        if not set(params) <= {"query", "limit", "includeArchived"}:',
    '            raise ValueError("thread/search 只接受 query、limit 与 includeArchived")',
    '        include_archived = params.get("includeArchived", False)',
    "        if type(include_archived) is not bool:",
    '            raise ValueError("includeArchived 必须是布尔值")',
    '        result = self.sessions.search_messages(_text(params, "query", maximum=200),',
    '                                               limit=params.get("limit", 30),',
    "                                               include_archived=include_archived)",
    "        self._check_response_budget(result)",
    "        return result",
)
REASONING_READ = (
    '        if set(params) != {"threadId"}:',
    '            raise ValueError("thread/reasoning/read 只接受 threadId")',
    "            config, available, summary_active = self._reasoning_scope(thread_id, thread)",
    "            capabilities = self.model_catalog.resolve(config.provider, config.model)",
    '            return {"threadId": thread_id, "model": config.model, "effort": effort,',
)
REASONING_SET = (
    '        if set(params) != {"threadId", "effort"}:',
    '            raise ValueError("thread/reasoning/set 只接受 threadId 和 effort")',
    "        if effort is not None and (not isinstance(effort, str) or not effort):",
    '            raise ValueError("effort 必须是推理档位字符串或 null")',
    '            if thread.get("archived"):',
    '                raise ValueError("请先恢复归档会话")',
    "            config, available, _ = self._reasoning_scope(thread_id, thread)",
    "            if effort is not None:",
    "                if effort not in available:",
    '                    raise RpcError(-32012, "会话或当前运行模型未声明支持该推理档位",',
    '                                   {"code": "REASONING_EFFORT_UNSUPPORTED", "model": config.model,',
    '                                    "available": available})',
    '            if thread.get("reasoningEffort") == effort:',
    '                return {"thread": thread}',
    "            updated = self.sessions.update_thread(thread_id, reasoningEffort=effort)",
    '        self._emit_committed("thread/reasoning/updated", {"threadId": thread_id, "effort": effort})',
)
BRANCHES = (
    '        if not set(params) <= {"threadId", "cursor", "limit"}:',
    '            raise ValueError("thread/branches/list 只接受 threadId、cursor 与 limit")',
    '        result = self.sessions.list_branches(_text(params, "threadId"), cursor=params.get("cursor"),',
    '                                             limit=params.get("limit", 50))',
    "        self._check_response_budget(result)",
)
SUMMARY = (
    '        if set(params) != {"threadId", "entryId"}:',
    '            raise ValueError("thread/branchSummary/read 只接受 threadId 与 entryId")',
    '        entry_id = _text(params, "entryId", maximum=128)',
    "        listed = next((summary for summary in self.context._branch_summaries(thread_id, entries)",
    "        if listed is None:",
    '            raise RpcError(-32011, "被放弃分支摘要不存在，或不在当前分支上",',
    '                           {"code": "BRANCH_SUMMARY_NOT_FOUND", "threadId": thread_id, "entryId": entry_id})',
    '                  "summary": payload["summary"].strip(), "origin": "model",',
)
TURN_READ = (
    '        thread_id = _text(params, "threadId")',
    '        turn = self.sessions.get_turn(thread_id, _text(params, "turnId"))',
    '        result = {"turn": {**turn, "items": [project_item(thread_id, item) for item in turn["items"]]}}',
    "        self._check_response_budget(result)",
    "        return result",
)
TURN_LIST = (
    "        if _branch_view(params):",
    "            result = self.sessions.list_branch_turns(thread_id, cursor=params.get(\"cursor\"),",
    '            return {"turns": result["turns"], "nextCursor": result["nextCursor"],',
    '        return self.sessions.list_turns(_text(params, "threadId"), cursor=params.get("cursor"), limit=params.get("limit", 50))',
)
TASK = (
    '        if set(params) != {"threadId", "kind", "id"}:',
    '            raise ValueError("task/read 参数无效")',
    '        kind, task_id = params.get("kind"), _text(params, "id", maximum=128)',
    '        if not isinstance(kind, str) or kind not in {"turn", "queue", "compaction"}:',
    '            raise ValueError("kind 必须是 turn、queue 或 compaction")',
    '        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", task_id):',
    '            raise ValueError("id 格式无效")',
    "        with self._task_read_snapshot(thread_id) as snapshot:",
    "                    raise self._missing_task()",
)
ITEM_CONTENT = (
    '        allowed = {"threadId", "itemId", "part", "sha256", "snapshotId", "cursor", "limit"}',
    "        if set(params) - allowed:",
    '            raise ValueError("会话内容读取包含未知参数")',
    '        item_id = _text(params, "itemId", maximum=128)',
    '        if not isinstance(part, str) or part not in {"text", "thinking"}:',
    '            raise ValueError("part 必须是 text 或 thinking")',
    "        if snapshot_id is not None and (not isinstance(snapshot_id, str)",
    '            raise ValueError("snapshotId 格式无效")',
    "        self.sessions.require_thread(thread_id)",
    '            raise ValueError("条目不属于该会话或不存在")',
    "        response = read_item_content(thread_id, item, part=part,",
    "        self._check_response_budget(response)",
)
TOOL_RESULT = (
    '        if set(params) - {"threadId", "itemId", "sha256", "cursor", "limit"}:',
    '            raise ValueError("工具结果读取包含未知参数；不接受文件路径或自由偏移")',
    "            item = self.sessions.read_item(thread_id, item_id)",
    "        except ItemLookupError as exc:",
    '            raise RpcError(-32010 if exc.code == "RESULT_HISTORY_LIMIT" else -32011,',
    '                           str(exc), {"code": exc.code, "itemId": item_id}) from None',
    '        if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):',
    '            raise ValueError("该条目没有可读取的完整工具结果")',
    "        return read_result_chunk(thread_id, item,",
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
    for name, fragments in (("on_thread_usage_read", USAGE), ("on_thread_search", SEARCH),
                            ("on_thread_reasoning_read", REASONING_READ),
                            ("on_thread_reasoning_set", REASONING_SET),
                            ("on_thread_branches_list", BRANCHES),
                            ("on_thread_branch_summary_read", SUMMARY),
                            ("on_turn_read", TURN_READ), ("on_turn_list", TURN_LIST),
                            ("on_task_read", TASK), ("on_item_content_read", ITEM_CONTENT),
                            ("on_tool_result_read", TOOL_RESULT)):
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


def _take(workspace: _Workspace) -> list[str]:
    server = workspace.server
    assert server is not None
    text = server._out.getvalue()
    server._out = io.StringIO()
    methods = []
    for line in text.splitlines():
        try:
            methods.append(json.loads(line)["method"])
        except (ValueError, KeyError):
            raise ValueError(f"通知行无法解析：{line[:80]}") from None
    return methods


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"详情读取入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"详情读取入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"详情读取入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data: dict, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message or error.data != data:
            raise ValueError(
                f"详情读取入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, "
                f"{str(error)!r}, {getattr(error, 'data', None)!r})") from None
        return 1
    raise ValueError(f"详情读取入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _seed(service: ApplicationService, thread_id: str) -> dict[str, str]:
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    ids = {}
    for key, payload in (
        ("user", {"kind": "userMessage", "text": "你好，帮我看看", "turnId": "turn-1"}),
        ("agent", {"kind": "agentMessage", "text": "收到", "status": "completed", "turnId": "turn-1"}),
        ("tool", {"kind": "toolCall", "name": "boss_hr_greet", "status": "completed",
                  "input": {"greeting": "x"}, "result": {"ok": True, "data": {"id": 1}},
                  "turnId": "turn-1"}),
    ):
        ids[key] = service.sessions.append(thread_id, Entry(type="item", payload=payload)).id
    return ids


def _usage_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            empty = service.on_thread_usage_read({"threadId": thread_id})
            checked += _expect_value(set(empty), {"threadId", "view", "source", "costAvailable", "turnCount",
                                                  "turns", "nextCursor", "summaryTasks", "totals",
                                                  "summaryJobs", "summaryJobCount", "summaryJobsTruncated",
                                                  "cacheWaste"}, "用量键")
            checked += _expect_value((empty["threadId"], empty["view"], empty["source"], empty["costAvailable"],
                                      empty["turnCount"], empty["turns"], empty["nextCursor"],
                                      empty["summaryJobCount"], empty["cacheWaste"]),
                                     (thread_id, "log", "provider-usage", False, 0, [], None, 0,
                                      {"missedTokens": 0, "missCount": 0}), "空用量投影")
            checked += _expect_value(set(empty["totals"]), {"requests", "verifiedRequests", "unverifiedRequests",
                                                            "unreportedRequests", "unverifiedReasons",
                                                            "promptTokens", "uncachedInputTokens",
                                                            "outputTokens", "cacheReadTokens", "cacheWriteTokens",
                                                            "reasoningTokens", "costUsd", "costSource"},
                                     "用量合计键")
            branch = service.on_thread_usage_read({"threadId": thread_id, "view": "branch"})
            checked += _expect_value((branch["view"], "cacheWaste" in branch), ("branch", False), "分支用量视图")
            checked += _expect_error(
                lambda: service.on_thread_usage_read({"threadId": thread_id, "extra": 1}),
                "thread/usage/read 只接受 threadId、view、cursor 与 limit", "用量参数集合")
            checked += _expect_error(
                lambda: service.on_thread_usage_read({"threadId": thread_id, "view": "all"}),
                "view 必须是 log 或 branch", "用量视图")
            checked += _expect_error(
                lambda: service.on_thread_usage_read({"threadId": thread_id, "limit": 0}),
                "limit 必须是 1 到 200 之间的整数", "用量上限")
        finally:
            service.close()
    return checked


def _search_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            ids = _seed(service, thread_id)
            found = service.on_thread_search({"query": "看看"})
            checked += _expect_value(set(found), {"query", "matches", "truncated"}, "搜索结果键")
            checked += _expect_value((found["query"], found["truncated"], len(found["matches"])),
                                     ("看看", False, 1), "搜索命中")
            checked += _expect_value({key: found["matches"][0][key] for key in
                                      ("threadId", "threadTitle", "itemId", "role", "snippet")},
                                     {"threadId": thread_id, "threadTitle": "新会话", "itemId": ids["user"],
                                      "role": "user", "snippet": "你好，帮我看看"}, "命中投影")
            checked += _expect_value(service.on_thread_search({"query": "不存在"})["matches"], [],
                                     "无命中")
            service.on_thread_archive({"threadId": thread_id})
            checked += _expect_value(service.on_thread_search({"query": "看看"})["matches"], [],
                                     "默认跳过归档")
            checked += _expect_value(len(service.on_thread_search({"query": "看看",
                                                                   "includeArchived": True})["matches"]), 1,
                                     "包含归档命中")
            checked += _expect_error(
                lambda: service.on_thread_search({"query": "看看", "includeArchived": "yes"}),
                "includeArchived 必须是布尔值", "归档开关")
            checked += _expect_error(lambda: service.on_thread_search({"query": "看看", "limit": 0}),
                                     "limit 必须是 1–50 的整数", "搜索上限")
            checked += _expect_error(lambda: service.on_thread_search({"query": "   "}),
                                     "query 必须是非空字符串（最多 200 字符）", "空白查询")
            checked += _expect_error(lambda: service.on_thread_search({"query": "看看", "extra": 1}),
                                     "thread/search 只接受 query、limit 与 includeArchived", "搜索参数集合")
        finally:
            service.close()
    return checked


def _reasoning_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            read = service.on_thread_reasoning_read({"threadId": thread_id})
            checked += _expect_value(set(read), {"threadId", "model", "effort", "configuredEffort", "supported",
                                                 "availableEfforts", "summaryActive", "capabilitySource",
                                                 "capabilityIsEstimate"}, "推理读取键")
            checked += _expect_value((read["threadId"], read["model"], read["effort"], read["configuredEffort"],
                                      read["supported"], read["availableEfforts"], read["summaryActive"],
                                      read["capabilitySource"], read["capabilityIsEstimate"]),
                                     (thread_id, "none", None, None, True, [], False,
                                      "legacy-default", True), "推理读取投影")
            checked += _expect_error(lambda: service.on_thread_reasoning_read({}),
                                     "thread/reasoning/read 只接受 threadId", "推理读取参数")
            checked += _expect_error(lambda: service.on_thread_reasoning_set({"threadId": thread_id}),
                                     "thread/reasoning/set 只接受 threadId 和 effort", "推理设置参数")
            checked += _expect_error(lambda: service.on_thread_reasoning_set({"threadId": thread_id,
                                                                              "effort": ""}),
                                     "effort 必须是推理档位字符串或 null", "档位类型")
            checked += _expect_rpc(
                lambda: service.on_thread_reasoning_set({"threadId": thread_id, "effort": "high"}),
                -32012, "会话或当前运行模型未声明支持该推理档位",
                {"code": "REASONING_EFFORT_UNSUPPORTED", "model": "none", "available": []}, "档位不支持")
            same = service.on_thread_reasoning_set({"threadId": thread_id, "effort": None})
            checked += _expect_value(same["thread"]["id"], thread_id, "同值返回")
            checked += _expect_value(_take(workspace), [], "同值不通知")
            service.on_thread_archive({"threadId": thread_id})
            checked += _expect_error(
                lambda: service.on_thread_reasoning_set({"threadId": thread_id, "effort": None}),
                "请先恢复归档会话", "归档拒绝")
        finally:
            service.close()
    return checked


def _branch_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            listed = service.on_thread_branches_list({"threadId": thread_id})
            checked += _expect_value(set(listed), {"threadId", "branched", "leafTurnId", "turnCount",
                                                   "endpoints", "nextCursor"}, "分支列表键")
            checked += _expect_value((listed["threadId"], listed["branched"], listed["leafTurnId"],
                                      listed["turnCount"], listed["endpoints"], listed["nextCursor"]),
                                     (thread_id, False, None, 0, [], None), "空分支投影")
            checked += _expect_error(lambda: service.on_thread_branches_list({"threadId": thread_id, "view": "x"}),
                                     "thread/branches/list 只接受 threadId、cursor 与 limit", "分支列表参数")
            checked += _expect_error(lambda: service.on_thread_branches_list({"threadId": thread_id, "limit": 0}),
                                     "limit 必须是 1 到 200 之间的整数", "分支列表上限")
            checked += _expect_error(lambda: service.on_thread_branch_summary_read({"threadId": thread_id}),
                                     "thread/branchSummary/read 只接受 threadId 与 entryId", "摘要读取参数")
            checked += _expect_rpc(
                lambda: service.on_thread_branch_summary_read({"threadId": thread_id, "entryId": "00000000"}),
                -32011, "被放弃分支摘要不存在，或不在当前分支上",
                {"code": "BRANCH_SUMMARY_NOT_FOUND", "threadId": thread_id, "entryId": "00000000"},
                "摘要不存在")
            checked += _expect_error(
                lambda: service.on_thread_branch_summary_read({"threadId": thread_id, "entryId": "x" * 129}),
                "entryId 必须是非空字符串（最多 128 字符）", "摘要条目标识")
        finally:
            service.close()
    return checked


def _turn_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            ids = _seed(service, thread_id)
            listed = service.on_turn_list({"threadId": thread_id})
            checked += _expect_value(set(listed), {"turns", "nextCursor"}, "回合列表键")
            turn = listed["turns"][0]
            checked += _expect_value((turn["turnId"], turn["threadId"], turn["status"]),
                                     ("turn-1", thread_id, "completed"), "回合投影")
            read = service.on_turn_read({"threadId": thread_id, "turnId": "turn-1"})
            checked += _expect_value(set(read), {"turn"}, "回合读取键")
            items = read["turn"]["items"]
            checked += _expect_value([(item["kind"], item["id"]) for item in items],
                                     [("userMessage", ids["user"]), ("agentMessage", ids["agent"]),
                                      ("toolCall", ids["tool"])], "回合条目")
            checked += _expect_value((items[0]["text"], items[2]["result"]),
                                     ("你好，帮我看看", {"ok": True, "data": {"id": 1}}), "条目内容")
            checked += _expect_error(lambda: service.on_turn_read({"threadId": thread_id, "turnId": "turn-9"}),
                                     "回合不存在", "未知回合")
            checked += _expect_error(lambda: service.on_turn_read({"threadId": thread_id}),
                                     "turnId 必须是非空字符串（最多 100000 字符）", "回合读取参数")
            checked += _expect_error(lambda: service.on_turn_list({"threadId": thread_id, "limit": 0}),
                                     "limit 必须是 1 到 200 之间的整数", "回合列表上限")
        finally:
            service.close()
    return checked


def _task_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            task = service.on_task_read({"threadId": thread_id, "kind": "turn", "id": "turn-1"})
            checked += _expect_value(set(task), {"task"}, "任务读取键")
            checked += _expect_value(set(task["task"]), {"locator", "threadId", "status", "ownership",
                                                         "runtimeOwned", "recoveryPolicy", "relations",
                                                         "historyWindow"}, "任务投影键")
            checked += _expect_value((task["task"]["locator"], task["task"]["threadId"], task["task"]["status"],
                                      task["task"]["ownership"], task["task"]["runtimeOwned"],
                                      task["task"]["recoveryPolicy"], task["task"]["relations"],
                                      task["task"]["historyWindow"]),
                                     ({"kind": "turn", "id": "turn-1"}, thread_id, "completed", "root",
                                      False, "closed", [], {"terminalCompactions": 64,
                                                            "checkpointRelations": "durable"}), "任务投影")
            checked += _expect_rpc(
                lambda: service.on_task_read({"threadId": thread_id, "kind": "queue", "id": "queue-1"}),
                -32012, "任务不存在或不属于此会话", {"code": "TASK_NOT_FOUND"}, "未知任务")
            checked += _expect_error(lambda: service.on_task_read({"threadId": thread_id, "kind": "other",
                                                                   "id": "turn-1"}),
                                     "kind 必须是 turn、queue 或 compaction", "任务类型")
            checked += _expect_error(lambda: service.on_task_read({"threadId": thread_id, "kind": "turn",
                                                                   "id": "bad id!"}),
                                     "id 格式无效", "任务标识")
            checked += _expect_error(lambda: service.on_task_read({"threadId": thread_id, "kind": "turn"}),
                                     "task/read 参数无效", "任务参数集合")
        finally:
            service.close()
    return checked


def _content_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            ids = _seed(service, thread_id)
            reference = item_content_reference(thread_id, ids["agent"], "text", "收到")
            content = service.on_item_content_read({"threadId": thread_id, "itemId": ids["agent"],
                                                    "part": "text", "sha256": reference["sha256"]})
            checked += _expect_value(set(content), {"text", "offset", "nextCursor", "contentRef"}, "内容读取键")
            checked += _expect_value((content["text"], content["offset"], content["nextCursor"],
                                      content["contentRef"]),
                                     ("收到", 0, None, reference), "内容读取投影")
            checked += _expect_error(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": ids["agent"],
                                                      "part": "all", "sha256": reference["sha256"]}),
                "part 必须是 text 或 thinking", "内容分区")
            checked += _expect_error(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": ids["agent"],
                                                      "part": "text", "sha256": "bad"}),
                "sha256 必须是内容引用中的 64 位小写十六进制摘要", "内容摘要格式")
            checked += _expect_rpc(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": ids["agent"],
                                                      "part": "text", "sha256": "0" * 64}),
                -32011, "会话内容已变化，请重新读取条目并确认新内容引用",
                {"code": "STALE_CONTENT", "currentRef": reference}, "内容摘要不一致")
            checked += _expect_error(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": ids["user"],
                                                      "part": "text", "sha256": reference["sha256"]}),
                "该条目没有可读取的文本或思考内容", "非助手文本")
            checked += _expect_error(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": "00000000",
                                                      "part": "text", "sha256": reference["sha256"]}),
                "条目不属于该会话或不存在", "未知条目")
            checked += _expect_error(
                lambda: service.on_item_content_read({"threadId": thread_id, "itemId": ids["agent"],
                                                      "part": "text", "sha256": reference["sha256"],
                                                      "offset": 1}),
                "会话内容读取包含未知参数", "内容参数集合")
        finally:
            service.close()
    return checked


def _result_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            ids = _seed(service, thread_id)
            result = {"ok": True, "data": {"id": 1}}
            reference = result_reference(thread_id, ids["tool"], canonical_result_text(result))
            read = service.on_tool_result_read({"threadId": thread_id, "itemId": ids["tool"],
                                                "sha256": reference["sha256"]})
            checked += _expect_value(set(read), {"text", "offset", "resultRef", "nextCursor"}, "结果读取键")
            checked += _expect_value((read["text"], read["offset"], read["nextCursor"], read["resultRef"]),
                                     (canonical_result_text(result), 0, None, reference), "结果读取投影")
            checked += _expect_rpc(
                lambda: service.on_tool_result_read({"threadId": thread_id, "itemId": ids["tool"],
                                                     "sha256": "0" * 64}),
                -32011, "工具结果已变化，请重新读取条目并确认新结果引用",
                {"code": "STALE_RESULT", "currentRef": reference}, "结果摘要不一致")
            checked += _expect_error(
                lambda: service.on_tool_result_read({"threadId": thread_id, "itemId": ids["user"],
                                                     "sha256": reference["sha256"]}),
                "该条目没有可读取的完整工具结果", "非工具条目")
            checked += _expect_error(
                lambda: service.on_tool_result_read({"threadId": thread_id, "itemId": "00000000",
                                                     "sha256": reference["sha256"]}),
                "条目不属于该会话或不存在", "未知结果条目")
            checked += _expect_error(
                lambda: service.on_tool_result_read({"threadId": thread_id, "itemId": ids["tool"],
                                                     "sha256": reference["sha256"], "path": "/tmp/x"}),
                "工具结果读取包含未知参数；不接受文件路径或自由偏移", "结果参数集合")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_details.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_details.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少详情检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((
        _usage_checks(), _search_checks(), _reasoning_checks(), _branch_checks(),
        _turn_checks(), _task_checks(), _content_checks(), _result_checks(),
    ))
    _check_documentation(structures, behaviors)
    print(f"会话详情读取入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
