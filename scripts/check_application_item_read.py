#!/usr/bin/env python3
"""核对条目读取入口：thread/item/result/read、thread/item/content/read。

工具结果与条目内容按引用分块读取：调用方必须带上条目引用里的 64 位摘要，过期摘要返回
`STALE_RESULT`（-32011）并附当前引用；分页用游标续读固定偏移。结果入口只接受
`threadId`、`itemId`、`sha256`、`cursor` 与 `limit`，拒绝文件路径或自由偏移；内容入口
另有 `part`（text / thinking）与可选的 32 位快照标识，并要求会话存在。这里在临时工作区
真实构造 `ApplicationService`（`provider=none`），写入工具调用与助手条目，用底层引用
函数算出真实摘要，逐项验证投影、分页、过期引用与拒绝分支；静态部分锁定两个 handler 的
参数校验与引用透传顺序。
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
from boss_harness.rpc import JsonRpcServer, RpcError  # noqa: E402
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
RESULT_READ = (
    '        params = params or {}',
    '        if set(params) - {"threadId", "itemId", "sha256", "cursor", "limit"}:',
    '            raise ValueError("工具结果读取包含未知参数；不接受文件路径或自由偏移")',
    '        thread_id, item_id = _text(params, "threadId"), _text(params, "itemId", maximum=128)',
    "        try:",
    "            item = self.sessions.read_item(thread_id, item_id)",
    "        except ItemLookupError as exc:",
    '            raise RpcError(-32010 if exc.code == "RESULT_HISTORY_LIMIT" else -32011,',
    '                           str(exc), {"code": exc.code, "itemId": item_id}) from None',
    "        if item is None:",
    '            raise ValueError("条目不属于该会话或不存在")',
    '        if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):',
    '            raise ValueError("该条目没有可读取的完整工具结果")',
    "        return read_result_chunk(thread_id, item,",
    '                                 sha256=_text(params, "sha256", maximum=64),',
    '                                 cursor=params.get("cursor"), limit=params.get("limit", 16_384))',
)
CONTENT_READ = (
    '        params = params or {}',
    '        allowed = {"threadId", "itemId", "part", "sha256", "snapshotId", "cursor", "limit"}',
    "        if set(params) - allowed:",
    '            raise ValueError("会话内容读取包含未知参数")',
    '        thread_id = _text(params, "threadId")',
    '        item_id = _text(params, "itemId", maximum=128)',
    '        part = params.get("part")',
    '        if not isinstance(part, str) or part not in {"text", "thinking"}:',
    '            raise ValueError("part 必须是 text 或 thinking")',
    '        snapshot_id = params.get("snapshotId")',
    "        if snapshot_id is not None and (not isinstance(snapshot_id, str)",
    '                or not re.fullmatch(r"[a-f0-9]{32}", snapshot_id)):',
    '            raise ValueError("snapshotId 格式无效")',
    "        self.sessions.require_thread(thread_id)",
    "        with self.events.lock:",
    "            if snapshot_id is None:",
    "                items = self.events.items(thread_id)",
    "        if snapshot_id is not None:",
    "            item = self.snapshots.item(snapshot_id, thread_id, item_id)",
    "        else:",
    '            item = next((value for value in items if value.get("id") == item_id), None)',
    "        if item is None:",
    '            raise ValueError("条目不属于该会话或不存在")',
    "        response = read_item_content(thread_id, item, part=part,",
    '            sha256=_text(params, "sha256", maximum=64), cursor=params.get("cursor"),',
    '            limit=params.get("limit", 16_384), snapshot_id=snapshot_id)',
    "        self._check_response_budget(response)",
    "        return response",
)
RESULT_KEYS = {"text", "offset", "resultRef", "nextCursor"}
CONTENT_KEYS = {"text", "offset", "nextCursor", "contentRef"}
REF_KEYS = {"threadId", "itemId", "encoding", "sha256", "byteLength", "characterLength"}
CONTENT_REF_KEYS = REF_KEYS | {"part"}
STALE = "工具结果已变化，请重新读取条目并确认新结果引用"
STALE_CONTENT = "会话内容已变化，请重新读取条目并确认新内容引用"


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
    for name, fragments in (("on_tool_result_read", RESULT_READ),
                            ("on_item_content_read", CONTENT_READ)):
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


def _seed(service: ApplicationService, thread_id: str) -> tuple[dict, dict]:
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "toolCall", "turnId": "turn-1", "tool": "boss_schema",
        "result": {"ok": True, "stdout": "结果正文" * 20}}))
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "agentMessage", "turnId": "turn-1",
        "text": "模型的文本回复" * 10, "thinking": "模型的思考内容" * 10}))
    items = service.on_items_list({"threadId": thread_id})["items"]
    tool = next(item for item in items if item.get("kind") == "toolCall")
    agent = next(item for item in items if item.get("kind") == "agentMessage")
    return tool, agent


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"条目读取行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"条目读取行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"条目读取行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_stale(call, message: str, data_code: str, label: str) -> int:
    try:
        call()
    except RpcError as error:
        data = error.data if isinstance(error.data, dict) else {}
        if (error.code, str(error), data.get("code")) != (-32011, message, data_code) \
                or not isinstance(data.get("currentRef"), dict):
            raise ValueError(f"条目读取行为变化 {label}：实际 {(error.code, str(error), data)!r}") from None
        return 1
    raise ValueError(f"条目读取行为变化 {label}：期望 RpcError，实际未抛出")


def _result_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            tool, agent = _seed(service, thread_id)
            digest = result_reference(thread_id, tool["id"],
                                      canonical_result_text(tool["result"]))["sha256"]
            full = service.on_tool_result_read(
                {"threadId": thread_id, "itemId": tool["id"], "sha256": digest})
            checked += _expect_value(set(full), RESULT_KEYS, "结果投影键")
            checked += _expect_value(set(full["resultRef"]), REF_KEYS, "结果引用键")
            checked += _expect_value((full["offset"], full["nextCursor"],
                                      "结果正文" in full["text"],
                                      full["resultRef"]["sha256"]), (0, None, True, digest),
                                     "结果全文投影")
            first = service.on_tool_result_read({"threadId": thread_id, "itemId": tool["id"],
                                                 "sha256": digest, "limit": 4})
            checked += _expect_value((len(first["text"]), first["offset"],
                                      isinstance(first["nextCursor"], str)), (4, 0, True), "结果首页")
            second = service.on_tool_result_read({"threadId": thread_id, "itemId": tool["id"],
                                                  "sha256": digest, "cursor": first["nextCursor"],
                                                  "limit": 8})
            checked += _expect_value((len(second["text"]), second["offset"]), (8, 4), "结果次页")
            checked += _expect_stale(lambda: service.on_tool_result_read(
                {"threadId": thread_id, "itemId": tool["id"], "sha256": "a" * 64}), STALE,
                "STALE_RESULT", "结果过期摘要")
            checked += _expect_error(lambda: service.on_tool_result_read(
                {"threadId": thread_id, "itemId": tool["id"], "path": "/etc/passwd"}),
                "工具结果读取包含未知参数；不接受文件路径或自由偏移", "结果未知参数")
            checked += _expect_error(lambda: service.on_tool_result_read(
                {"threadId": thread_id, "itemId": tool["id"]}),
                "sha256 必须是非空字符串（最多 64 字符）", "结果缺摘要")
            checked += _expect_error(lambda: service.on_tool_result_read(
                {"threadId": thread_id, "itemId": agent["id"], "sha256": digest}),
                "该条目没有可读取的完整工具结果", "结果非工具条目")
            checked += _expect_error(lambda: service.on_tool_result_read(
                {"threadId": thread_id, "itemId": "nope", "sha256": digest}),
                "条目不属于该会话或不存在", "结果未知条目")
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
            tool, agent = _seed(service, thread_id)
            text_digest = item_content_reference(thread_id, agent["id"], "text",
                                                 agent["text"], None)["sha256"]
            thinking_digest = item_content_reference(thread_id, agent["id"], "thinking",
                                                     agent["thinking"], None)["sha256"]
            text = service.on_item_content_read({"threadId": thread_id, "itemId": agent["id"],
                                                 "part": "text", "sha256": text_digest})
            checked += _expect_value(set(text), CONTENT_KEYS, "内容投影键")
            checked += _expect_value(set(text["contentRef"]), CONTENT_REF_KEYS, "内容引用键")
            checked += _expect_value((text["offset"], text["nextCursor"],
                                      text["text"], text["contentRef"]["part"]),
                                     (0, None, agent["text"], "text"), "内容全文投影")
            thinking = service.on_item_content_read({"threadId": thread_id, "itemId": agent["id"],
                                                     "part": "thinking", "sha256": thinking_digest})
            checked += _expect_value((thinking["text"], thinking["contentRef"]["part"]),
                                     (agent["thinking"], "thinking"), "内容思考投影")
            first = service.on_item_content_read({"threadId": thread_id, "itemId": agent["id"],
                                                  "part": "text", "sha256": text_digest, "limit": 2})
            checked += _expect_value((first["text"], first["offset"],
                                      isinstance(first["nextCursor"], str)),
                                     ("模型", 0, True), "内容首页")
            second = service.on_item_content_read({"threadId": thread_id, "itemId": agent["id"],
                                                   "part": "text", "sha256": text_digest,
                                                   "cursor": first["nextCursor"], "limit": 4})
            checked += _expect_value((second["text"], second["offset"]), ("的文本回", 2), "内容次页")
            checked += _expect_stale(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": agent["id"], "part": "text",
                 "sha256": "a" * 64}), STALE_CONTENT, "STALE_CONTENT", "内容过期摘要")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": agent["id"]}),
                "part 必须是 text 或 thinking", "内容缺 part")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": agent["id"], "part": "both"}),
                "part 必须是 text 或 thinking", "内容 part 非法")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": agent["id"], "part": "text",
                 "sha256": text_digest, "snapshotId": "bad"}), "snapshotId 格式无效", "内容快照格式")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": agent["id"], "part": "text", "extra": 1}),
                "会话内容读取包含未知参数", "内容未知参数")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": "000000000000", "itemId": agent["id"], "part": "text"}),
                "会话不存在", "内容未知线程")
            checked += _expect_error(lambda: service.on_item_content_read(
                {"threadId": thread_id, "itemId": tool["id"], "part": "text",
                 "sha256": text_digest}), "该条目没有可读取的文本或思考内容", "内容非助手条目")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_item_read.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_item_read.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少条目读取检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_result_checks(), _content_checks()))
    _check_documentation(structures, behaviors)
    print(f"条目读取入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
