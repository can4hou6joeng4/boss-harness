#!/usr/bin/env python3
"""核对分支读取入口：thread/branches/list、thread/branchSummary/read。

分支列表按回合树枚举端点：被放弃端点 `containsLeaf` / `isLeaf` 为 false 但可选中，
当前端点两者为 true；分页用 `(位置, 回合)` 游标续读。被放弃分支摘要只在切换分支时
由摘要任务写入，读取按当前分支扫描并返回 15 项投影；未知条目与普通条目都返回
`BRANCH_SUMMARY_NOT_FOUND`（-32011），避免把日志中的任意条目当成摘要正文。这里在
临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），用分支指针
移动与 `append_branch_summary` 构造真实分叉，逐项验证投影、分页与拒绝分支；静态
部分锁定两个 handler 的参数校验与返回路径。
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
BRANCHES = (
    '        params = params or {}',
    '        if not set(params) <= {"threadId", "cursor", "limit"}:',
    '            raise ValueError("thread/branches/list 只接受 threadId、cursor 与 limit")',
    '        result = self.sessions.list_branches(_text(params, "threadId"), cursor=params.get("cursor"),',
    '                                             limit=params.get("limit", 50))',
    "        self._check_response_budget(result)",
    "        return result",
)
SUMMARY_READ = (
    '        params = params or {}',
    '        if set(params) != {"threadId", "entryId"}:',
    '            raise ValueError("thread/branchSummary/read 只接受 threadId 与 entryId")',
    '        thread_id = _text(params, "threadId")',
    '        entry_id = _text(params, "entryId", maximum=128)',
    "        entries = self.sessions.read_active_entries(thread_id)",
    "        listed = next((summary for summary in self.context._branch_summaries(thread_id, entries)",
    '                       if summary["entryId"] == entry_id), None)',
    "        if listed is None:",
    '            raise RpcError(-32011, "被放弃分支摘要不存在，或不在当前分支上",',
    '                           {"code": "BRANCH_SUMMARY_NOT_FOUND", "threadId": thread_id, "entryId": entry_id})',
    '        payload = listed["payload"]',
    '        result = {"threadId": thread_id, "entryId": entry_id,',
    '                  **{key: listed[key] for key in ("targetTurnId", "fromTurnId", "abandonedTurnIds",',
    '                                                  "summaryJobId", "characters")},',
    '                  "summary": payload["summary"].strip(), "origin": "model",',
    '                  "label": "模型生成的被放弃分支摘要",',
    '                  "commonTurnId": payload.get("commonTurnId"),',
    '                  "summaryProvider": payload.get("summaryProvider"), "summaryModel": payload.get("summaryModel"),',
    '                  "sourceTextDigest": payload.get("sourceTextDigest"), "createdAt": listed.get("createdAt")}',
    "        self._check_response_budget(result)",
    "        return result",
)
LIST_KEYS = {"threadId", "branched", "leafTurnId", "turnCount", "endpoints", "nextCursor"}
ENDPOINT_KEYS = {"turnId", "status", "startedAt", "updatedAt", "completedAt", "depth", "forkTurnId",
                 "branchTurnId", "branchInputPreview", "inputPreview", "containsLeaf", "isLeaf",
                 "selectable"}
SUMMARY_KEYS = {"threadId", "entryId", "targetTurnId", "fromTurnId", "abandonedTurnIds",
                "summaryJobId", "characters", "summary", "origin", "label", "commonTurnId",
                "summaryProvider", "summaryModel", "sourceTextDigest", "createdAt"}


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
    for name, fragments in (("on_thread_branches_list", BRANCHES),
                            ("on_thread_branch_summary_read", SUMMARY_READ)):
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


def _seed(service: ApplicationService, thread_id: str, turn_id: str, text: str) -> None:
    service.sessions.record_turn(thread_id, turn_id, "completed")
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "userMessage", "text": text, "turnId": turn_id}))


def _fork(service: ApplicationService, thread_id: str) -> tuple[str, str]:
    """两个回合后把指针移回第一轮，再追加第三轮，并写入真实的分支摘要记录。"""
    _seed(service, thread_id, "turn-1", "第一轮")
    _seed(service, thread_id, "turn-2", "第二轮的探索")
    service.on_thread_leaf_set({"threadId": thread_id, "turnId": "turn-1"})
    entries = service.sessions.read_entries(thread_id)
    leaf_id = next(entry["id"] for entry in reversed(entries) if entry.get("type") == "leaf")
    summary = service.sessions.append_branch_summary(thread_id, leaf_id, {
        "summary": "探索了第二轮的方案，但最终放弃。",
        "targetTurnId": "turn-1", "fromTurnId": "turn-2",
        "abandonedTurnIds": ["turn-2"], "commonTurnId": "turn-1",
        "summaryJobId": "job-branch-1", "summaryProvider": "none", "summaryModel": "none",
        "sourceTextDigest": "a" * 64})
    _seed(service, thread_id, "turn-3", "第三轮继续")
    return summary.id, leaf_id


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"分支读取行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"分支读取行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"分支读取行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        actual = (error.code, str(error), error.data)
        if actual != (code, message, data):
            raise ValueError(f"分支读取行为变化 {label}：期望 {(code, message, data)!r}，"
                             f"实际 {actual!r}") from None
        return 1
    raise ValueError(f"分支读取行为变化 {label}：期望 RpcError，实际未抛出")


def _list_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            empty = service.on_thread_branches_list({"threadId": thread_id})
            checked += _expect_value(set(empty), LIST_KEYS, "列表投影键")
            checked += _expect_value((empty["threadId"], empty["branched"], empty["leafTurnId"],
                                      empty["turnCount"], empty["endpoints"], empty["nextCursor"]),
                                     (thread_id, False, None, 0, [], None), "列表空投影")
            _fork(service, thread_id)
            listed = service.on_thread_branches_list({"threadId": thread_id})
            checked += _expect_value((listed["branched"], listed["leafTurnId"], listed["turnCount"],
                                      [endpoint["turnId"] for endpoint in listed["endpoints"]]),
                                     (True, "turn-3", 3, ["turn-2", "turn-3"]), "列表分叉投影")
            checked += _expect_value([set(endpoint) for endpoint in listed["endpoints"]],
                                     [ENDPOINT_KEYS, ENDPOINT_KEYS], "列表端点键")
            checked += _expect_value([(endpoint["isLeaf"], endpoint["containsLeaf"],
                                       endpoint["forkTurnId"], endpoint["branchTurnId"],
                                       endpoint["selectable"])
                                      for endpoint in listed["endpoints"]],
                                     [(False, False, "turn-1", "turn-2", True),
                                      (True, True, "turn-1", "turn-3", True)], "列表端点投影")
            checked += _expect_value([endpoint["inputPreview"] for endpoint in listed["endpoints"]],
                                     ["第二轮的探索", "第三轮继续"], "列表输入预览")
            first = service.on_thread_branches_list({"threadId": thread_id, "limit": 1})
            checked += _expect_value(([endpoint["turnId"] for endpoint in first["endpoints"]],
                                      isinstance(first["nextCursor"], str)), (["turn-2"], True),
                                     "列表首页")
            second = service.on_thread_branches_list({"threadId": thread_id,
                                                      "cursor": first["nextCursor"], "limit": 1})
            checked += _expect_value(([endpoint["turnId"] for endpoint in second["endpoints"]],
                                      second["nextCursor"]), (["turn-3"], None), "列表次页")
            checked += _expect_error(lambda: service.on_thread_branches_list(
                {"threadId": thread_id, "extra": 1}),
                "thread/branches/list 只接受 threadId、cursor 与 limit", "列表参数")
            checked += _expect_error(lambda: service.on_thread_branches_list(
                {"threadId": thread_id, "cursor": "bad"}), "分页游标无效", "列表游标")
            checked += _expect_error(lambda: service.on_thread_branches_list(
                {"threadId": thread_id, "limit": 0}), "limit 必须是 1 到 200 之间的整数", "列表上限")
            checked += _expect_error(lambda: service.on_thread_branches_list(
                {"threadId": "000000000000"}), "会话不存在", "列表未知线程")
        finally:
            service.close()
    return checked


def _summary_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            summary_id, leaf_id = _fork(service, thread_id)
            summary = service.on_thread_branch_summary_read({"threadId": thread_id,
                                                             "entryId": summary_id})
            checked += _expect_value(set(summary), SUMMARY_KEYS, "摘要投影键")
            checked += _expect_value((summary["threadId"], summary["entryId"], summary["targetTurnId"],
                                      summary["fromTurnId"], summary["abandonedTurnIds"],
                                      summary["summaryJobId"], summary["characters"]),
                                     (thread_id, summary_id, "turn-1", "turn-2", ["turn-2"],
                                      "job-branch-1", 16), "摘要投影值")
            checked += _expect_value((summary["summary"], summary["origin"], summary["label"],
                                      summary["commonTurnId"], summary["summaryProvider"],
                                      summary["summaryModel"], summary["sourceTextDigest"]),
                                     ("探索了第二轮的方案，但最终放弃。", "model",
                                      "模型生成的被放弃分支摘要", "turn-1", "none", "none", "a" * 64),
                                     "摘要正文与来源")
            checked += _expect_value(isinstance(summary["createdAt"], str), True, "摘要时间")
            checked += _expect_error(lambda: service.on_thread_branch_summary_read(
                {"threadId": thread_id}),
                "thread/branchSummary/read 只接受 threadId 与 entryId", "摘要参数")
            checked += _expect_error(lambda: service.on_thread_branch_summary_read(
                {"threadId": thread_id, "entryId": summary_id, "extra": 1}),
                "thread/branchSummary/read 只接受 threadId 与 entryId", "摘要多余键")
            checked += _expect_error(lambda: service.on_thread_branch_summary_read(
                {"threadId": "000000000000", "entryId": summary_id}), "会话不存在", "摘要未知线程")
            for label, entry_id in (("摘要未知条目", "nope"), ("摘要普通条目", leaf_id)):
                checked += _expect_rpc(lambda entry_id=entry_id: service.on_thread_branch_summary_read(
                    {"threadId": thread_id, "entryId": entry_id}), -32011,
                    "被放弃分支摘要不存在，或不在当前分支上",
                    {"code": "BRANCH_SUMMARY_NOT_FOUND", "threadId": thread_id,
                     "entryId": entry_id}, label)
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_branches.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_branches.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少分支读取检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_list_checks(), _summary_checks()))
    _check_documentation(structures, behaviors)
    print(f"分支读取入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
