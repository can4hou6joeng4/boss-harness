#!/usr/bin/env python3
"""核对附件与运行资源入口：attachment/add、attachment/read、runtime/resources/read、approval/list。

`attachment/add` 只接受工作区内的支持文本文件并映射配额错误；`attachment/read` 默认整份
返回小附件，显式给出 `cursor` / `limit` / `sha256` 时走摘要分块，整份超预算以带恢复建议
的 `-32010` 拒绝；`runtime/resources/read` 在锁内投影回合容量、所有者与等待者；
`approval/list` 按线程过滤待决审批并返回计数。这里在临时工作区与状态目录中真实构造
`ApplicationService`（`provider=none`），写入工作区文件并逐项验证投影与拒绝分支；
静态部分锁定这些 handler 的源码顺序。
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

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
ATTACHMENT_ADD = (
    '            attachment = self.attachments.add(_text(params, "threadId"), _text(params, "path", maximum=4096))',
    "        except AttachmentQuotaExceeded as exc:",
    "            raise RpcError(-32005, str(exc), exc.data) from None",
    '        return {"attachment": attachment}',
)
ATTACHMENT_READ = (
    '        if set(params) - {"threadId", "attachmentId", "cursor", "limit", "sha256"}:',
    '            raise ValueError("附件读取包含未知参数")',
    '        attachment_id = _text(params, "attachmentId", maximum=128)',
    '        if "cursor" in params or "limit" in params or "sha256" in params:',
    "            return self.attachments.read_chunk(",
    "        attachment = self.attachments.read(thread_id, attachment_id)",
    '        result = {"attachment": attachment}',
    "        if wire_size(result) > MAX_PAGE_BYTES:",
    '            raise RpcError(-32010, "附件正文超过单页读取预算，请分段读取",',
    '                           {"code": "RESPONSE_TOO_LARGE", "recoveryMethod": "attachment/read",',
    "        return result",
)
RUNTIME = (
    "        if params not in (None, {}):",
    '            raise ValueError("runtime/resources/read 不接受参数")',
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    "            owners = []",
    "            return {",
    '                "turnCapacity": self.runtimes.capacity,',
    '                "activeTurnCount": len(self.runtimes.active),',
    '                "owners": owners[:MAX_RUNTIME_RESOURCE_OWNERS],',
    '                "ownersTruncated": len(owners) > MAX_RUNTIME_RESOURCE_OWNERS,',
    '                "waiterCount": len(self._capacity_waiters), "waiters": waiters,',
    '                "waitersTruncated": len(self._capacity_waiters) > MAX_RUNTIME_RESOURCE_WAITERS,',
)
APPROVAL = (
    "        if params is not None and not isinstance(params, dict):",
    '            raise ValueError("审批查询参数必须是对象")',
    '        if set(params) - {"threadId", "limit"}:',
    '            raise ValueError("审批查询只接受 threadId 和 limit")',
    '            thread_id = _text(params, "threadId", maximum=64)',
    "        if type(limit) is not int or not 1 <= limit <= 200:",
    '            raise ValueError("limit 必须是 1 到 200 之间的整数")',
    "        approvals, truncated = self.sessions.pending_approvals(thread_id, limit=limit)",
    '        return {"approvals": approvals, "truncated": truncated,',
    '                "threadCounts": self.sessions.pending_approval_counts(thread_id)}',
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
    for name, fragments in (("on_attachment_add", ATTACHMENT_ADD),
                            ("on_attachment_read", ATTACHMENT_READ),
                            ("on_runtime_resources_read", RUNTIME),
                            ("on_approval_list", APPROVAL)):
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
        raise ValueError(f"附件入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"附件入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"附件入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data: dict, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message or error.data != data:
            raise ValueError(
                f"附件入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, "
                f"{str(error)!r}, {getattr(error, 'data', None)!r})") from None
        return 1
    raise ValueError(f"附件入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _attachment_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        (workspace.workspace / "notes.txt").write_text("招聘附件正文", encoding="utf-8")
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            added = service.on_attachment_add({"threadId": thread_id, "path": "notes.txt"})
            checked += _expect_value(set(added), {"attachment"}, "添加结果键")
            attachment = added["attachment"]
            checked += _expect_value(set(attachment), {"id", "name", "digest", "bytes", "mediaType"},
                                     "附件投影键")
            checked += _expect_value((attachment["name"], attachment["bytes"],
                                      attachment["mediaType"], len(attachment["id"]),
                                      len(attachment["digest"])),
                                     ("notes.txt", 18, "text/plain; charset=utf-8", 32, 64),
                                     "附件投影")
            read = service.on_attachment_read({"threadId": thread_id, "attachmentId": attachment["id"]})
            checked += _expect_value(set(read), {"attachment"}, "整份读取键")
            checked += _expect_value((read["attachment"]["content"], read["attachment"]["bytes"]),
                                     ("招聘附件正文", 18), "整份读取投影")
            chunk = service.on_attachment_read({"threadId": thread_id, "attachmentId": attachment["id"],
                                                "sha256": attachment["digest"]})
            checked += _expect_value(set(chunk), {"text", "offset", "nextCursor", "contentRef"},
                                     "分块读取键")
            checked += _expect_value((chunk["text"], chunk["offset"], chunk["nextCursor"],
                                      chunk["contentRef"]["sha256"]),
                                     ("招聘附件正文", 0, None, attachment["digest"]), "分块读取投影")
            checked += _expect_error(
                lambda: service.on_attachment_add({"threadId": thread_id, "path": "../escape.txt"}),
                "附件必须是工作区内支持的文本文件", "工作区外路径")
            checked += _expect_error(
                lambda: service.on_attachment_add({"threadId": thread_id, "path": "missing.txt"}),
                "附件必须是工作区内可读取的普通文本文件", "不存在文件")
            checked += _expect_error(lambda: service.on_attachment_add({"threadId": thread_id}),
                                     "path 必须是非空字符串（最多 4096 字符）", "缺失路径")
            checked += _expect_error(lambda: service.on_attachment_add({"threadId": thread_id,
                                                                        "path": "x" * 5000}),
                                     "path 必须是非空字符串（最多 4096 字符）", "路径上限")
            checked += _expect_error(
                lambda: service.on_attachment_read({"threadId": thread_id, "attachmentId": "nope"}),
                "附件不属于该会话", "未知附件")
            checked += _expect_error(
                lambda: service.on_attachment_read({"threadId": thread_id, "attachmentId": attachment["id"],
                                                    "sha256": "bad"}),
                "sha256 必须是附件内容引用中的 64 位小写十六进制摘要", "摘要格式")
            checked += _expect_error(
                lambda: service.on_attachment_read({"threadId": thread_id, "attachmentId": attachment["id"],
                                                    "limit": 0}),
                "limit 必须是 1 到 32768 的整数", "分块上限")
            checked += _expect_error(
                lambda: service.on_attachment_read({"threadId": thread_id, "attachmentId": attachment["id"],
                                                    "offset": 1}),
                "附件读取包含未知参数", "读取参数集合")
        finally:
            service.close()
    return checked


def _runtime_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            resources = service.on_runtime_resources_read(None)
            checked += _expect_value(set(resources), {"turnCapacity", "activeTurnCount", "maxRetainedTurns",
                                                      "retainedTurnCount", "ownerCount", "owners",
                                                      "ownersTruncated", "waiterCount", "waiters",
                                                      "waitersTruncated"}, "资源投影键")
            checked += _expect_value((resources["turnCapacity"], resources["activeTurnCount"],
                                      resources["maxRetainedTurns"], resources["retainedTurnCount"],
                                      resources["ownerCount"], resources["owners"],
                                      resources["ownersTruncated"], resources["waiterCount"],
                                      resources["waiters"], resources["waitersTruncated"]),
                                     (8, 0, 16, 0, 0, [], False, 0, [], False), "空资源投影")
            checked += _expect_error(lambda: service.on_runtime_resources_read({"extra": 1}),
                                     "runtime/resources/read 不接受参数", "资源参数")
        finally:
            service.close()
    return checked


def _approval_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            listed = service.on_approval_list(None)
            checked += _expect_value(set(listed), {"approvals", "truncated", "threadCounts"}, "审批列表键")
            checked += _expect_value((listed["approvals"], listed["truncated"], listed["threadCounts"]),
                                     ([], False, {}), "空审批投影")
            checked += _expect_value(service.on_approval_list({"threadId": thread_id}),
                                     {"approvals": [], "truncated": False, "threadCounts": {}}, "线程过滤")
            checked += _expect_error(lambda: service.on_approval_list("thread"),
                                     "审批查询参数必须是对象", "非对象参数")
            checked += _expect_error(lambda: service.on_approval_list({"extra": 1}),
                                     "审批查询只接受 threadId 和 limit", "参数集合")
            checked += _expect_error(lambda: service.on_approval_list({"threadId": "x" * 65}),
                                     "threadId 必须是非空字符串（最多 64 字符）", "线程标识上限")
            checked += _expect_error(lambda: service.on_approval_list({"limit": 0}),
                                     "limit 必须是 1 到 200 之间的整数", "上限")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_attachments.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_attachments.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少附件检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((_attachment_checks(), _runtime_checks(), _approval_checks()))
    _check_documentation(structures, behaviors)
    print(f"附件与运行资源入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
