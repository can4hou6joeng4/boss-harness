#!/usr/bin/env python3
"""核对上下文条目编辑入口：context/edit/read、context/edit。

读取返回八项投影（线程、条目、来源摘要、原文、当前文本、排除标记、可编辑与原因）；
归档会话把 `canEdit` 置为 false 并给出原因。编辑严格限定四项参数，`replacementText`
只接受字符串或 null，`sourceDigest` 必须是 64 位十六进制并以乐观并发方式比对：过期摘要
返回「会话消息或编辑状态已变化」；`null` 表示恢复原文（当前文本为 null、`excluded` 为
true）。这里在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），
写入条目后逐项验证投影与拒绝分支；静态部分锁定两个 handler 的校验顺序。
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
EDIT_READ = (
    '        params = params or {}',
    '        if set(params) != {"threadId", "itemId"}:',
    '            raise ValueError("context/edit/read 参数无效")',
    '        thread_id, item_id = _text(params, "threadId"), _text(params, "itemId")',
    "        with self.runtimes.lock:",
    "            result = self.context.context_edit_read(thread_id, item_id)",
    "            thread = self.sessions.get_thread(thread_id)",
    '            if thread.get("archived"):',
    '                result.update(canEdit=False, reason="归档会话不可编辑。")',
    "            elif thread_id in self.runtimes.active or thread_id in self._compaction_by_thread:",
    '                result.update(canEdit=False, reason="会话正在运行或整理摘要；请等待结束后再编辑。")',
    "            self._check_response_budget(result)",
    "            return result",
)
EDIT = (
    '        params = params or {}',
    '        if set(params) != {"threadId", "itemId", "sourceDigest", "replacementText"}:',
    '            raise ValueError("context/edit 参数无效")',
    '        thread_id, item_id = _text(params, "threadId"), _text(params, "itemId")',
    '        replacement = params.get("replacementText")',
    "        if replacement is not None and not isinstance(replacement, str):",
    '            raise ValueError("replacementText 必须是字符串或 null")',
    "        with self.runtimes.lock:",
    "            thread = self.sessions.get_thread(thread_id)",
    '            if thread.get("archived"):',
    '                raise ValueError("归档会话不可编辑")',
    "            if thread_id in self.runtimes.active or thread_id in self._compaction_by_thread:",
    '                raise RpcError(-32004, "会话正在运行或整理摘要；请等待结束后再编辑")',
    "            result = self.context.context_edit(thread_id, item_id, replacement,",
    '                                               params.get("sourceDigest"),',
    "                                               validate_response=self._check_response_budget)",
    '            self._emit_committed("context/edited", {"threadId": thread_id, "itemId": item_id,',
    '                                                     "sourceDigest": result["sourceDigest"]})',
    "            return result",
)
READ_KEYS = {"threadId", "itemId", "sourceDigest", "originalText", "currentText",
             "excluded", "canEdit", "reason"}


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
    for name, fragments in (("on_context_edit_read", EDIT_READ), ("on_context_edit", EDIT)):
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


def _seed(service: ApplicationService, thread_id: str, text: str = "原始正文") -> str:
    service.sessions.record_turn(thread_id, "turn-1", "completed")
    service.sessions.append(thread_id, Entry(type="item", payload={
        "kind": "userMessage", "text": text, "turnId": "turn-1"}))
    return service.on_items_list({"threadId": thread_id})["items"][0]["id"]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"编辑入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"编辑入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"编辑入口行为变化 {label}：期望 ValueError，实际未抛出")


def _read_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            item_id = _seed(service, thread_id)
            checked += _expect_error(lambda: service.on_context_edit_read({"threadId": thread_id}),
                                     "context/edit/read 参数无效", "读取缺键")
            checked += _expect_error(lambda: service.on_context_edit_read(
                {"threadId": thread_id, "itemId": item_id, "extra": 1}),
                "context/edit/read 参数无效", "读取多余键")
            checked += _expect_error(lambda: service.on_context_edit_read(
                {"threadId": "000000000000", "itemId": item_id}), "会话不存在", "读取未知线程")
            checked += _expect_error(lambda: service.on_context_edit_read(
                {"threadId": thread_id, "itemId": "nope"}), "会话消息不存在", "读取未知条目")
            read = service.on_context_edit_read({"threadId": thread_id, "itemId": item_id})
            checked += _expect_value(set(read), READ_KEYS, "读取投影键")
            checked += _expect_value((read["threadId"], read["itemId"], read["originalText"],
                                      read["currentText"], read["excluded"], read["canEdit"],
                                      read["reason"]),
                                     (thread_id, item_id, "原始正文", "原始正文", False, True, None),
                                     "读取投影值")
            checked += _expect_value(isinstance(read["sourceDigest"], str)
                                     and len(read["sourceDigest"]) == 64, True, "读取摘要长度")
            archived = service.on_thread_start({})["thread"]["id"]
            service.on_thread_archive({"threadId": archived})
            archived_item = _seed(service, archived, "归档正文")
            archived_read = service.on_context_edit_read({"threadId": archived,
                                                          "itemId": archived_item})
            checked += _expect_value((archived_read["canEdit"], archived_read["reason"]),
                                     (False, "归档会话不可编辑。"), "读取归档投影")
        finally:
            service.close()
    return checked


def _edit_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            item_id = _seed(service, thread_id)
            checked += _expect_error(lambda: service.on_context_edit({"threadId": thread_id}),
                                     "context/edit 参数无效", "编辑缺键")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": thread_id, "itemId": item_id, "sourceDigest": None,
                 "replacementText": "x", "extra": 1}), "context/edit 参数无效", "编辑多余键")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": thread_id, "itemId": item_id, "sourceDigest": None,
                 "replacementText": 5}), "replacementText 必须是字符串或 null", "编辑替换类型")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": "000000000000", "itemId": item_id, "sourceDigest": None,
                 "replacementText": "x"}), "会话不存在", "编辑未知线程")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": thread_id, "itemId": item_id, "sourceDigest": None,
                 "replacementText": "x"}), "sourceDigest 格式无效", "编辑空摘要")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": thread_id, "itemId": item_id, "sourceDigest": "x" * 64,
                 "replacementText": "x"}), "sourceDigest 格式无效", "编辑摘要格式")
            read = service.on_context_edit_read({"threadId": thread_id, "itemId": item_id})
            digest = read["sourceDigest"]
            workspace.take()
            edited = service.on_context_edit({"threadId": thread_id, "itemId": item_id,
                                              "sourceDigest": digest,
                                              "replacementText": "新正文"})
            checked += _expect_value(set(edited), READ_KEYS, "编辑返回键")
            checked += _expect_value((edited["itemId"], edited["originalText"],
                                      edited["currentText"], edited["excluded"], edited["canEdit"]),
                                     (item_id, "原始正文", "新正文", False, True), "编辑投影")
            checked += _expect_value(edited["sourceDigest"] != digest, True, "编辑摘要变化")
            checked += _expect_value(service.on_context_edit_read({"threadId": thread_id,
                                                                   "itemId": item_id}),
                                     edited, "编辑回读一致")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": thread_id, "itemId": item_id, "sourceDigest": digest,
                 "replacementText": "再改"}),
                "会话消息或编辑状态已变化，请重新读取后再提交", "编辑旧摘要重放")
            restored = service.on_context_edit({"threadId": thread_id, "itemId": item_id,
                                                "sourceDigest": edited["sourceDigest"],
                                                "replacementText": None})
            checked += _expect_value((restored["currentText"], restored["excluded"]),
                                     (None, True), "编辑恢复原文")
            events = workspace.take()
            edited_events = [event for event in events if event.get("method") == "context/edited"]
            checked += _expect_value(len(edited_events), 2, "编辑广播次数")
            checked += _expect_value([event.get("params", {}).get("itemId") for event in edited_events],
                                     [item_id, item_id], "编辑广播载荷")
            archived = service.on_thread_start({})["thread"]["id"]
            service.on_thread_archive({"threadId": archived})
            archived_item = _seed(service, archived, "归档正文")
            checked += _expect_error(lambda: service.on_context_edit(
                {"threadId": archived, "itemId": archived_item, "sourceDigest": None,
                 "replacementText": "x"}), "归档会话不可编辑", "编辑归档会话")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_edit.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_edit.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少编辑检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_read_checks(), _edit_checks()))
    _check_documentation(structures, behaviors)
    print(f"上下文编辑入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
