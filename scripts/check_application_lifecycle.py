#!/usr/bin/env python3
"""核对会话生命周期写入入口：归档、重命名、模型切换、分支、删除与叶读取。

`thread/archive` 归档后暂停队列并广播、重复归档保持幂等；`thread/unarchive` 恢复；
`thread/name/set` 只收非空且不超过 500 字符的标题；`thread/model/set` 校验参数集合、
线路与模型目录，归档会话拒绝切换，同值切换不重复广播；`thread/fork` 只接受已结束的
回合；`thread/delete` 先按忙因拒绝，成功后广播 `thread/deleted` 并写入事件；
`thread/leaf/read` 投影分支位置。这里在临时工作区与状态目录中真实构造
`ApplicationService`（`provider=none`），逐项验证结果、通知与事件落库；静态部分
锁定这些分支的源码顺序。
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

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
ARCHIVE = (
    "        with self._follow_up_admission_lock, self.runtimes.lock:",
    "            self._idle(thread_id)",
    "            paused_queue_ids = self.queue.pause(thread_id, reason=PAUSE_REASON_THREAD_ARCHIVED)",
    "            self._forget_capacity_waiter_locked(thread_id)",
    "            thread = self.sessions.archive_thread(thread_id)",
    "        for queue_id in paused_queue_ids:",
    "            self._emit_queue_updated(thread_id, queue_id)",
    '        self._emit_committed("thread/archived", {"threadId": thread_id})',
    '        return {"thread": thread}',
)
DELETE = (
    "        with self._thread_admission.hold(thread_id), self._follow_up_admission_lock, self.runtimes.lock:",
    "            if thread_id in self.runtimes.active:",
    '                reason = "turn"',
    '            elif any(job.get("threadId") == thread_id for job in self.runtimes.jobs.values()):',
    '                reason = "cleanup"',
    "            elif thread_id in self._compaction_by_thread:",
    '                reason = "compaction"',
    "            elif thread_id in self._follow_up_dispatches:",
    '                reason = "dispatch"',
    "            elif thread_id in self._follow_up_worker_threads.values():",
    '                reason = "cleanup"',
    '            elif any(notice.get("threadId") == thread_id for notice in self._receipt_notices.values()):',
    '                reason = "cleanup"',
    "            if reason is not None:",
    '                raise RpcError(-32004, "会话仍由运行任务持有，暂不能删除",',
    '                               {"code": "THREAD_BUSY", "threadId": thread_id, "reason": reason})',
    "                notify_deleted = (self.sessions.has_pending_deletion(thread_id)",
    "                                  or self.sessions.path_for(thread_id).exists())",
    "                    event = self.sessions.delete_thread(thread_id, _on_committed=mark_deletion_committed)",
    "                except ThreadNotFound:",
    '                    raise RpcError(-32011, "会话不存在",',
    '                                   {"code": "THREAD_NOT_FOUND", "threadId": thread_id}) from None',
    "                    if pending_deletion:",
    '                        raise RpcError(-32012, "会话删除尚未完成；该会话已隐藏，内核重启后会继续清理",',
    '                                       {"code": "THREAD_DELETE_INCOMPLETE", "threadId": thread_id}) from None',
    "                if notify_deleted:",
    "                    self.events.publish_persisted(event)",
    '        return {"threadId": thread_id, "deleted": True}',
)
UNARCHIVE = (
    "        thread = self.sessions.unarchive_thread(thread_id)",
    '        self._emit_committed("thread/unarchived", {"threadId": thread_id})',
    '        return {"thread": thread}',
)
NAME = (
    '        thread = self.sessions.update_thread(thread_id, title=_text(params, "name", maximum=500))',
    '        self._emit_committed("thread/renamed", {"threadId": thread_id, "thread": thread})',
    '        return {"thread": thread}',
)
MODEL_SET = (
    '        if set(params) != {"threadId", "provider", "model"}:',
    '            raise ValueError("thread/model/set 只接受 threadId、provider 和 model")',
    '        provider = self._canonical_provider(params["provider"])',
    '        model = self._validate_model_id(params["model"])',
    "        config = self._configured_route(provider)",
    "        if model != config.model:",
    '            raise RpcError(-32013, "该 provider/model 不在本机配置目录中",',
    '                           {"code": "MODEL_ROUTE_UNAVAILABLE", "provider": provider, "model": model})',
    '            if thread.get("archived"):',
    '                raise ValueError("请先恢复归档会话")',
    "            self._idle(thread_id)",
    "                pending = [item for item in self.queue.list(thread_id)",
    '                           if item.get("status") in {"queued", "delivering"}]',
    "            if pending:",
    '                raise RpcError(-32004, "会话仍有排队消息，请先处理队列再切换模型线路",',
    '                               {"code": "MODEL_SWITCH_QUEUE_PENDING", "pending": len(pending)})',
    '            if (thread.get("provider") == provider and thread.get("model") == model',
    '                    and thread.get("reasoningEffort") is None):',
    '                return {"thread": thread}',
    '            updated = self.sessions.update_thread(thread_id, provider=provider, model=model, reasoningEffort=None)',
    '        self._emit_committed("thread/model/updated", {"threadId": thread_id, "provider": provider,',
    '                                                      "model": model, "thread": updated})',
    '        return {"thread": updated}',
)
FORK = (
    '        thread = self.sessions.fork_thread(_text(params, "threadId"), turn_id=params.get("turnId"), title=params.get("title"))',
    '        self._emit_committed("thread/created", {"threadId": thread["id"], "thread": thread})',
    '        return {"thread": thread}',
)
LEAF_READ = (
    '        if set(params) != {"threadId"}:',
    '            raise ValueError("thread/leaf/read 只接受 threadId")',
    '        return self.sessions.read_leaf(_text(params, "threadId"))',
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
    for name, fragments in (("on_thread_archive", ARCHIVE), ("on_thread_delete", DELETE),
                            ("on_thread_unarchive", UNARCHIVE), ("on_thread_name", NAME),
                            ("on_thread_model_set", MODEL_SET), ("on_thread_fork", FORK),
                            ("on_thread_leaf_read", LEAF_READ)):
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
    """取出已发布的通知方法名并清空输出缓冲。"""
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
        raise ValueError(f"生命周期入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"生命周期入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"生命周期入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data: dict, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message or error.data != data:
            raise ValueError(
                f"生命周期入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, "
                f"{str(error)!r}, {getattr(error, 'data', None)!r})") from None
        return 1
    raise ValueError(f"生命周期入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _archive_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            first = service.on_thread_start({})["thread"]["id"]
            second = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            archived = service.on_thread_archive({"threadId": first})
            checked += _expect_value(set(archived), {"thread"}, "归档结果键")
            checked += _expect_value(archived["thread"]["archived"], True, "归档标记")
            checked += _expect_value(_take(workspace), ["thread/archived"], "归档通知")
            again = service.on_thread_archive({"threadId": first})
            checked += _expect_value(again["thread"]["archived"], True, "归档幂等")
            checked += _expect_value(_take(workspace), ["thread/archived"], "重复归档通知")
            listed = {item["id"] for item in service.on_thread_list({})["threads"]}
            checked += _expect_value((first in listed, second in listed), (False, True), "默认列表排除归档")
            archived_list = {item["id"] for item in service.on_thread_list({"archived": True})["threads"]}
            checked += _expect_value(archived_list, {first}, "归档列表")
            restored = service.on_thread_unarchive({"threadId": first})
            checked += _expect_value(restored["thread"]["archived"], False, "恢复标记")
            checked += _expect_value(_take(workspace), ["thread/unarchived"], "恢复通知")
            listed = {item["id"] for item in service.on_thread_list({})["threads"]}
            checked += _expect_value(listed, {first, second}, "恢复后列表")
        finally:
            service.close()
    return checked


def _name_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            renamed = service.on_thread_name({"threadId": thread_id, "name": "招聘助手"})
            checked += _expect_value(set(renamed), {"thread"}, "重命名结果键")
            checked += _expect_value(renamed["thread"]["title"], "招聘助手", "重命名标题")
            checked += _expect_value(_take(workspace), ["thread/renamed"], "重命名通知")
            for params, label in (
                ({"threadId": thread_id, "name": "   "}, "空白标题"),
                ({"threadId": thread_id, "name": "x" * 501}, "超长标题"),
                ({"threadId": thread_id}, "缺失标题"),
            ):
                checked += _expect_error(
                    lambda params=params: service.on_thread_name(params),
                    "name 必须是非空字符串（最多 500 字符）", label)
        finally:
            service.close()
    return checked


def _model_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            checked += _expect_error(
                lambda: service.on_thread_model_set({"threadId": thread_id, "provider": "none"}),
                "thread/model/set 只接受 threadId、provider 和 model", "参数集合")
            checked += _expect_rpc(
                lambda: service.on_thread_model_set({"threadId": thread_id, "provider": "anthropic",
                                                     "model": "x"}),
                -32013, "本机没有可用的该模型线路配置",
                {"code": "MODEL_PROVIDER_UNAVAILABLE", "provider": "anthropic"}, "线路不可用")
            checked += _expect_rpc(
                lambda: service.on_thread_model_set({"threadId": thread_id, "provider": "none",
                                                     "model": "other"}),
                -32013, "该 provider/model 不在本机配置目录中",
                {"code": "MODEL_ROUTE_UNAVAILABLE", "provider": "none", "model": "other"}, "模型不在目录")
            service.sessions.update_thread(thread_id, provider="none", model="legacy")
            updated = service.on_thread_model_set({"threadId": thread_id, "provider": "none", "model": "none"})
            checked += _expect_value(set(updated), {"thread"}, "切换结果键")
            checked += _expect_value((updated["thread"]["provider"], updated["thread"]["model"],
                                      updated["thread"]["reasoningEffort"]),
                                     ("none", "none", None), "切换结果")
            checked += _expect_value(_take(workspace), ["thread/model/updated"], "切换通知")
            same = service.on_thread_model_set({"threadId": thread_id, "provider": "none", "model": "none"})
            checked += _expect_value(same["thread"]["model"], "none", "同值返回")
            checked += _expect_value(_take(workspace), [], "同值不通知")
            service.on_thread_archive({"threadId": thread_id})
            _take(workspace)
            checked += _expect_error(
                lambda: service.on_thread_model_set({"threadId": thread_id, "provider": "none",
                                                     "model": "none"}),
                "请先恢复归档会话", "归档拒绝")
        finally:
            service.close()
    return checked


def _fork_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            source = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            checked += _expect_error(lambda: service.on_thread_fork({"threadId": source}),
                                     "仅可从已经结束的回合创建分支", "无结束回合")
            service.sessions.record_turn(source, "turn-1", "completed")
            forked = service.on_thread_fork({"threadId": source, "turnId": "turn-1"})
            thread = forked["thread"]
            checked += _expect_value(set(forked), {"thread"}, "分支结果键")
            checked += _expect_value((thread["id"] != source, len(thread["id"])), (True, 12), "分支标识")
            checked += _expect_value((thread["title"], thread["provider"], thread["model"]),
                                     ("新会话", "none", "none"), "分支默认值")
            checked += _expect_value(_take(workspace), ["thread/created"], "分支通知")
            titled = service.on_thread_fork({"threadId": source, "title": "分支名"})
            checked += _expect_value(titled["thread"]["title"], "分支名", "分支标题")
        finally:
            service.close()
    return checked


def _delete_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            checked += _expect_rpc(
                lambda: service.on_thread_delete({"threadId": "000000000000"}), -32011, "会话不存在",
                {"code": "THREAD_NOT_FOUND", "threadId": "000000000000"}, "删除不存在")
            thread_id = service.on_thread_start({})["thread"]["id"]
            _take(workspace)
            deleted = service.on_thread_delete({"threadId": thread_id})
            checked += _expect_value(deleted, {"threadId": thread_id, "deleted": True}, "删除结果")
            checked += _expect_value(service.on_thread_list({})["threads"], [], "删除后列表")
            checked += _expect_error(lambda: service.on_thread_read({"threadId": thread_id}),
                                     "会话不存在", "删除后读取")
            checked += _expect_value(_take(workspace), ["thread/deleted"], "删除通知")
            methods = [item["method"] for item in service.on_event_list({})["events"]]
            checked += _expect_value("thread/deleted" in methods, True, "删除事件落库")
        finally:
            service.close()
    return checked


def _leaf_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            checked += _expect_error(lambda: service.on_thread_leaf_read({}),
                                     "thread/leaf/read 只接受 threadId", "叶读取参数")
            initial = service.on_thread_leaf_read({"threadId": thread_id})
            checked += _expect_value(set(initial), {"threadId", "branched", "leafTurnId", "activeTurnCount",
                                                    "activeTurnIds", "activeTurnIdsTruncated"}, "叶读取键")
            checked += _expect_value((initial["threadId"], initial["branched"], initial["leafTurnId"],
                                      initial["activeTurnCount"], initial["activeTurnIds"],
                                      initial["activeTurnIdsTruncated"]),
                                     (thread_id, False, None, 0, [], False), "初始叶")
            service.sessions.record_turn(thread_id, "turn-1", "completed")
            current = service.on_thread_leaf_read({"threadId": thread_id})
            checked += _expect_value((current["leafTurnId"], current["activeTurnCount"],
                                      current["activeTurnIds"]),
                                     ("turn-1", 1, ["turn-1"]), "回合后叶")
            checked += _expect_error(lambda: service.on_thread_leaf_read({"threadId": "000000000000"}),
                                     "会话不存在", "叶读取未知线程")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_application_lifecycle.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_application_lifecycle.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少生命周期检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = sum((
        _archive_checks(), _name_checks(), _model_checks(),
        _fork_checks(), _delete_checks(), _leaf_checks(),
    ))
    _check_documentation(structures, behaviors)
    print(f"会话生命周期入口检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
