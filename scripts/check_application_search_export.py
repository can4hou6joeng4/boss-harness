#!/usr/bin/env python3
"""核对搜索与导出读取入口：thread/search、thread/export。

`thread/search` 是跨会话的只读搜索：默认排除归档会话，`includeArchived` 必须是布尔，
`query` 上限 200 字符，命中只返回有界摘要与来源标题。`thread/export` 把一次会话渲染为
有界、脱敏的文档：`format` 只接受 markdown / json / html，`includeToolResults` 必须是
布尔，`maxBytes` 限定范围，视图走共享的 `_branch_view`；响应带 `content` 与 `bytes`。
这里在临时工作区真实构造 `ApplicationService`（`provider=none`），写入正文后验证命中、
归档过滤、三种导出格式的内容与错误分支，并核对导出文档不含工作区绝对路径；静态部分
锁定两个 handler 的参数校验与快照读取顺序。
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
SEARCH = (
    '        params = params or {}',
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
EXPORT = (
    "        from boss_harness.session_export import DEFAULT_EXPORT_BYTES, export_thread",
    '        params = params or {}',
    '        if not set(params) <= {"threadId", "view", "format", "includeToolResults", "maxBytes"}:',
    '            raise ValueError("thread/export 只接受 threadId、view、format、includeToolResults 与 maxBytes")',
    "        secrets = [config.api_key.get() for config in (self.config, *self._model_configs.values())",
    "                   if config.api_key]",
    '        thread_id = _text(params, "threadId")',
    "        with self.runtimes.lock:",
    "            entries = self.sessions.read_entries_snapshot(thread_id)",
    "            active_job_id = self.context.active_summary_job_id(thread_id, entries=entries)",
    "            result = export_thread(self.sessions, thread_id, branch=_branch_view(params),",
    '                                   fmt=params.get("format", "markdown"),',
    '                                   include_tool_results=params.get("includeToolResults", False),',
    '                                   max_bytes=params.get("maxBytes", DEFAULT_EXPORT_BYTES),',
    "                                   server_version=__version__, secrets=secrets,",
    "                                   paths=(self.workspace, self.sessions.root.parent),",
    "                                   active_summary_job_id=active_job_id, entries=entries)",
    "        self._check_response_budget(result)",
    "        return result",
)
MATCH_KEYS = {"itemId", "role", "snippet", "threadId", "threadTitle"}
SEARCH_KEYS = {"query", "matches", "truncated"}
EXPORT_KEYS = {"threadId", "view", "format", "mediaType", "suggestedFileName", "bytes",
               "maxBytes", "truncated", "turnCount", "exportedTurnCount", "toolResults",
               "redactions", "content"}
REDACTION_KEYS = {"secrets", "environment", "paths", "personalInfo"}


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
    for name, fragments in (("on_thread_search", SEARCH), ("on_thread_export", EXPORT)):
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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"搜索导出行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"搜索导出行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"搜索导出行为变化 {label}：期望 ValueError，实际未抛出")


def _search_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id, "turn-1", "招聘岗位的缓存命中测试")
            found = service.on_thread_search({"query": "缓存命中"})
            checked += _expect_value(set(found), SEARCH_KEYS, "搜索投影键")
            checked += _expect_value((found["query"], found["truncated"], len(found["matches"])),
                                     ("缓存命中", False, 1), "搜索投影值")
            match = found["matches"][0]
            checked += _expect_value(set(match), MATCH_KEYS, "搜索命中键")
            checked += _expect_value((match["threadId"], match["role"], match["snippet"],
                                      match["threadTitle"]),
                                     (thread_id, "user", "招聘岗位的缓存命中测试", "新会话"), "搜索命中值")
            checked += _expect_value(service.on_thread_search({"query": "不存在的词"})["matches"], [],
                                     "搜索空结果")
            checked += _expect_error(lambda: service.on_thread_search({}),
                                     "query 必须是非空字符串（最多 200 字符）", "搜索缺查询")
            checked += _expect_error(lambda: service.on_thread_search({"query": ""}),
                                     "query 必须是非空字符串（最多 200 字符）", "搜索空查询")
            checked += _expect_error(lambda: service.on_thread_search({"query": "长" * 201}),
                                     "query 必须是非空字符串（最多 200 字符）", "搜索超长查询")
            checked += _expect_error(lambda: service.on_thread_search({"query": "x", "extra": 1}),
                                     "thread/search 只接受 query、limit 与 includeArchived", "搜索多余键")
            checked += _expect_error(lambda: service.on_thread_search(
                {"query": "x", "includeArchived": "yes"}), "includeArchived 必须是布尔值", "搜索归档类型")
            checked += _expect_error(lambda: service.on_thread_search({"query": "x", "limit": 0}),
                                     "limit 必须是 1–50 的整数", "搜索上限")
            service.on_thread_archive({"threadId": thread_id})
            checked += _expect_value(service.on_thread_search({"query": "缓存命中"})["matches"], [],
                                     "搜索默认排除归档")
            included = service.on_thread_search({"query": "缓存命中", "includeArchived": True})
            checked += _expect_value([match["threadId"] for match in included["matches"]],
                                     [thread_id], "搜索包含归档")
        finally:
            service.close()
    return checked


def _export_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id, "turn-1", "导出正文")
            markdown = service.on_thread_export({"threadId": thread_id})
            checked += _expect_value(set(markdown), EXPORT_KEYS, "导出投影键")
            checked += _expect_value((markdown["threadId"], markdown["view"], markdown["format"],
                                      markdown["mediaType"], markdown["suggestedFileName"],
                                      markdown["maxBytes"], markdown["truncated"],
                                      markdown["turnCount"], markdown["exportedTurnCount"],
                                      markdown["toolResults"]),
                                     (thread_id, "log", "markdown", "text/markdown",
                                      f"boss-harness-session-{thread_id}-log.md", 524288, False,
                                      1, 1, "omitted"), "导出元数据")
            checked += _expect_value(set(markdown["redactions"]), REDACTION_KEYS, "导出脱敏键")
            checked += _expect_value(markdown["content"].startswith("# BOSS Harness 会话导出"), True,
                                     "导出 Markdown 标题")
            checked += _expect_value(markdown["content"].count("导出正文") >= 1, True, "导出正文")
            checked += _expect_value(markdown["bytes"] > 0, True, "导出字节数")
            exported = service.on_thread_export({"threadId": thread_id, "format": "json"})
            document = json.loads(exported["content"])
            checked += _expect_value((document["schema"], document["threadId"], document["view"],
                                      exported["mediaType"]), ("boss-harness-session-export/1",
                                                               thread_id, "log", "application/json"),
                                     "导出 JSON")
            html = service.on_thread_export({"threadId": thread_id, "format": "html"})
            checked += _expect_value((html["content"].startswith("<!doctype html>"),
                                      "Content-Security-Policy" in html["content"]),
                                     (True, True), "导出 HTML")
            checked += _expect_error(lambda: service.on_thread_export(
                {"threadId": thread_id, "format": "pdf"}), "format 必须是 markdown、json 或 html",
                "导出格式")
            checked += _expect_error(lambda: service.on_thread_export(
                {"threadId": thread_id, "includeToolResults": "yes"}),
                "includeToolResults 必须是布尔值", "导出工具结果类型")
            checked += _expect_error(lambda: service.on_thread_export(
                {"threadId": thread_id, "maxBytes": 1}), "maxBytes 必须是 65536 到 786432 的整数",
                "导出大小上限")
            checked += _expect_error(lambda: service.on_thread_export(
                {"threadId": thread_id, "view": "both"}), "view 必须是 log 或 branch", "导出视图")
            checked += _expect_error(lambda: service.on_thread_export({"threadId": "000000000000"}),
                                     "会话不存在", "导出未知线程")
            checked += _expect_error(lambda: service.on_thread_export(
                {"threadId": thread_id, "extra": 1}),
                "thread/export 只接受 threadId、view、format、includeToolResults 与 maxBytes",
                "导出多余键")
        finally:
            service.close()
    return checked


def _redaction_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id, "turn-1", f"工作区路径 {workspace.workspace} 结束")
            for fmt in ("markdown", "json"):
                exported = service.on_thread_export({"threadId": thread_id, "format": fmt})
                checked += _expect_value(str(workspace.workspace) in exported["content"], False,
                                         f"导出脱敏路径 {fmt}")
                checked += _expect_value(exported["redactions"]["paths"] >= 1, True,
                                         f"导出脱敏计数 {fmt}")
                checked += _expect_value("工作区路径" in exported["content"], True,
                                         f"导出保留正文 {fmt}")
            branch = service.on_thread_export({"threadId": thread_id, "view": "branch"})
            checked += _expect_value("视图：当前分支" in branch["content"], True, "导出分支视图")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_search_export.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_search_export.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少搜索导出检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_search_checks(), _export_checks(), _redaction_checks()))
    _check_documentation(structures, behaviors)
    print(f"搜索导出入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
