#!/usr/bin/env python3
"""核对上下文读取与导出入口：context/read、说明读取与 thread/export。

`context/read` 在无运行回合时构造预览请求并返回预算投影；带 `input` / `model` /
`skillIds` / `attachmentIds` 时标记 `requestSource=preview` 且只影响该次预览。
`context/instructions/read` 只读有界正文、空工作区返回 `empty`。`thread/export`
支持 markdown / json / html，默认省略工具结果明文，按凭据、环境变量、路径与个人信息
四类计数脱敏。这里在临时工作区与状态目录中真实构造 `ApplicationService`
（`provider=none`），写入说明、回合与带凭据的消息，逐项验证投影、脱敏与拒绝分支；
静态部分锁定这些 handler 的源码顺序。
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
from boss_harness.models.secret import Secret  # noqa: E402
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
CONTEXT_READ = (
    '        preview = any(key in params for key in ("input", "model", "skillIds", "attachmentIds"))',
    "        workspace_instructions = self.workspace_instructions.describe()",
    "        with self.runtimes.lock:",
    "            if job is not None and preview:",
    '                raise RpcError(-32004, "回合运行中只能读取已准备请求的预算；预览请等待回合结束")',
    "                config = self._model_config(thread, params)",
    '                sections = self._system_prompt_sections(thread.get("toolPolicy") == "readOnly", skill_text)',
    "            messages = list(self.context.history(thread_id, entries=entries))",
    "            result = self.context.read(thread_id, request=request,",
    '            return {**result, "provider": config.provider, "requestSource": "active" if job else "preview" if preview else "default",',
    '                    "summaryAvailable": self._summary_available(policy, config.provider),',
    '                    "compactionJob": self._compaction_reference(thread_id),',
    '                    "systemPromptInfo": prompt_info,',
    '                    "workspaceInstructions": workspace_instructions}',
)
INSTRUCTIONS_READ = (
    "        if params:",
    '            raise ValueError("context/instructions/read 不接受参数")',
    "        return self.workspace_instructions.read_text()",
)
EXPORT = (
    '        if not set(params) <= {"threadId", "view", "format", "includeToolResults", "maxBytes"}:',
    '            raise ValueError("thread/export 只接受 threadId、view、format、includeToolResults 与 maxBytes")',
    "        secrets = [config.api_key.get() for config in (self.config, *self._model_configs.values())",
    "            result = export_thread(self.sessions, thread_id, branch=_branch_view(params),",
    '                                   fmt=params.get("format", "markdown"),',
    '                                   include_tool_results=params.get("includeToolResults", False),',
    '                                   max_bytes=params.get("maxBytes", DEFAULT_EXPORT_BYTES),',
    "                                   server_version=__version__, secrets=secrets,",
    "                                   paths=(self.workspace, self.sessions.root.parent),",
    "        self._check_response_budget(result)",
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
    for name, fragments in (("on_context_read", CONTEXT_READ),
                            ("on_context_instructions_read", INSTRUCTIONS_READ),
                            ("on_thread_export", EXPORT)):
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

    def service(self, config: ModelConfig | None = None, **kwargs) -> ApplicationService:
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, self.state,
                                     config or ModelConfig(provider="none", model="none"),
                                     None, workspace=self.workspace, **kwargs)
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                               "protocolVersion": "0.2.0"})
        service.on_initialized(None)
        self.server = server
        return service


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"上下文入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"上下文入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"上下文入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data: dict, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message or error.data != data:
            raise ValueError(
                f"上下文入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, "
                f"{str(error)!r}, {getattr(error, 'data', None)!r})") from None
        return 1
    raise ValueError(f"上下文入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _seed(service: ApplicationService, thread_id: str) -> None:
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    service.sessions.append(thread_id, Entry(type="item", payload={"kind": "userMessage",
                                                                   "text": "你好，令牌 sk-ant-abc1234567890 与 probe-secret-value",
                                                                   "turnId": "turn-1"}))
    service.sessions.append(thread_id, Entry(type="item", payload={"kind": "agentMessage", "text": "收到",
                                                                   "status": "completed", "turnId": "turn-1"}))
    service.sessions.append(thread_id, Entry(type="item", payload={"kind": "toolCall", "name": "boss_hr_greet",
                                                                   "status": "completed", "input": {"greeting": "x"},
                                                                   "result": {"ok": True}, "turnId": "turn-1"}))


def _instructions_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            empty = service.on_context_instructions_read(None)
            checked += _expect_value(set(empty), {"path", "pathPreferred", "content", "status",
                                                  "limitBytes", "bytes"}, "空说明键")
            checked += _expect_value((empty["path"], empty["pathPreferred"], empty["content"],
                                      empty["status"], empty["limitBytes"], empty["bytes"]),
                                     (".boss-harness/CONTEXT.md", ".boss-harness/CONTEXT.md", "",
                                      "empty", 8192, None), "空说明投影")
            checked += _expect_error(lambda: service.on_context_instructions_read({"extra": 1}),
                                     "context/instructions/read 不接受参数", "说明读取参数")
            written = service.on_context_instructions_write({"content": "招聘助手说明"})
            checked += _expect_value(written, {"path": ".boss-harness/CONTEXT.md", "bytes": 18,
                                               "status": "loaded", "limitBytes": 8192}, "说明写入")
            read = service.on_context_instructions_read({})
            checked += _expect_value((read["content"], read["status"], read["bytes"]),
                                     ("招聘助手说明", "loaded", 18), "说明回读")
        finally:
            service.close()
    return checked


def _context_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            base = service.on_context_read({"threadId": thread_id})
            checked += _expect_value(set(base), {"breakdown", "capabilitySource", "capacityIsEstimate",
                                                 "checkpoint", "compactionJob", "contextWindow", "estimateMethod",
                                                 "estimatedInputTokens", "inputBudget", "lastBudget",
                                                 "messageCount", "model", "modelMaxOutputTokens",
                                                 "outputReserve", "provider", "reasoningEffort",
                                                 "requestFingerprint", "requestSource", "requestedOutputTokens",
                                                 "summaryAvailable", "summaryUsage", "systemPromptInfo",
                                                 "threadId", "usage", "usageApplied", "withinBudget",
                                                 "workspaceInstructions"}, "上下文读取键")
            checked += _expect_value((base["threadId"], base["model"], base["provider"], base["requestSource"],
                                      base["contextWindow"], base["withinBudget"], base["messageCount"],
                                      base["usageApplied"], base["capabilitySource"]),
                                     (thread_id, "none", "none", "default", 200000, True, 4, False,
                                      "legacy-default"), "上下文读取投影")
            checked += _expect_value(set(base["breakdown"]), {"system", "messages", "tools", "options"},
                                     "预算分解键")
            checked += _expect_value((base["lastBudget"], base["summaryUsage"], base["checkpoint"], base["usage"]),
                                     (None, None, None, None), "空摘要与用量")
            checked += _expect_value(base["workspaceInstructions"], None, "空说明投影")
            preview = service.on_context_read({"threadId": thread_id, "input": "写一条招呼"})
            checked += _expect_value((preview["requestSource"], preview["messageCount"]), ("preview", 5),
                                     "预览请求")
            checked += _expect_error(lambda: service.on_context_read({"threadId": "000000000000"}),
                                     "会话不存在", "未知线程")
        finally:
            service.close()
    return checked


def _export_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service(ModelConfig(provider="none", model="none",
                                                api_key=Secret("probe-secret-value")))
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _seed(service, thread_id)
            markdown = service.on_thread_export({"threadId": thread_id})
            checked += _expect_value(set(markdown), {"bytes", "content", "exportedTurnCount", "format", "maxBytes",
                                                     "mediaType", "redactions", "suggestedFileName", "threadId",
                                                     "toolResults", "truncated", "turnCount", "view"}, "导出键")
            checked += _expect_value((markdown["threadId"], markdown["format"], markdown["view"],
                                      markdown["mediaType"], markdown["suggestedFileName"], markdown["maxBytes"],
                                      markdown["turnCount"], markdown["exportedTurnCount"],
                                      markdown["toolResults"], markdown["truncated"]),
                                     (thread_id, "markdown", "log", "text/markdown",
                                      f"boss-harness-session-{thread_id}-log.md", 524288, 1, 1,
                                      "omitted", False), "Markdown 元数据")
            checked += _expect_value(markdown["redactions"], {"secrets": 2, "environment": 0, "paths": 0,
                                                              "personalInfo": 0}, "脱敏计数")
            checked += _expect_value(("[已脱敏:凭据]" in markdown["content"],
                                      "sk-ant-abc1234567890" in markdown["content"],
                                      "probe-secret-value" in markdown["content"]), (True, False, False),
                                     "凭据脱敏")
            checked += _expect_value(markdown["bytes"], len(markdown["content"].encode("utf-8")), "导出字节数")
            payload = json.loads(service.on_thread_export({"threadId": thread_id, "format": "json"})["content"])
            checked += _expect_value(("schema" in payload, payload["threadId"], payload["title"]),
                                     (True, thread_id, "新会话"), "JSON 导出")
            checked += _expect_value(service.on_thread_export({"threadId": thread_id,
                                                               "format": "json"})["mediaType"],
                                     "application/json", "JSON 媒体类型")
            html = service.on_thread_export({"threadId": thread_id, "format": "html"})
            checked += _expect_value((html["mediaType"], html["content"].startswith("<!doctype html>")),
                                     ("text/html", True), "HTML 导出")
            with_tools = service.on_thread_export({"threadId": thread_id, "includeToolResults": True})
            checked += _expect_value((with_tools["toolResults"], with_tools["bytes"] > markdown["bytes"]),
                                     ("included", True), "包含工具结果")
            checked += _expect_value(service.on_thread_export({"threadId": thread_id,
                                                               "view": "branch"})["view"], "branch", "分支视图")
            checked += _expect_error(lambda: service.on_thread_export({"threadId": thread_id, "format": "xml"}),
                                     "format 必须是 markdown、json 或 html", "导出格式")
            checked += _expect_error(lambda: service.on_thread_export({"threadId": thread_id, "maxBytes": 0}),
                                     "maxBytes 必须是 65536 到 786432 的整数", "导出上限")
            checked += _expect_error(lambda: service.on_thread_export({"threadId": thread_id, "extra": 1}),
                                     "thread/export 只接受 threadId、view、format、includeToolResults 与 maxBytes",
                                     "导出参数集合")
            checked += _expect_error(lambda: service.on_thread_export({"threadId": "000000000000"}),
                                     "会话不存在", "导出未知线程")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_context.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_context.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少上下文检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_instructions_checks(), _context_checks(), _export_checks()))
    _check_documentation(structures, behaviors)
    print(f"上下文与导出入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
