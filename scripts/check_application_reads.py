#!/usr/bin/env python3
"""核对只读查询入口：线程、条目分页、事件、配置与能力投影。

握手完成后，桌面通过一组只读 handler 取列表、恢复会话与渲染配置页：
`thread/start` 校验标题、工具策略与模型线路并落 `thread/created` 事件；
`thread/read` 的 `excludeTurns` / `snapshot` 必须是布尔；`items/list` 与
`event/list` 各自校验游标并受页预算约束；`config/read` / `tool/list` /
`model/list` / `skills/list` 固定投影字段。这里在临时状态目录中真实构造
`ApplicationService`（`provider=none`，服务端输出重定向，不联网），逐项验证
参数拒绝与响应字段；静态部分锁定这些分支的源码顺序。
"""

from __future__ import annotations

import ast
import base64
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import re
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
THREAD_START = (
    '        title = params.get("title", "新会话")',
    '            raise ValueError("title 必须是最多 500 字符的字符串")',
    '        policy = params.get("toolPolicy", "approval")',
    '            raise ValueError("toolPolicy 必须是 readOnly 或 approval")',
    '        provider = self._canonical_provider(params.get("provider", self.config.provider))',
    "        config = self._configured_route(provider)",
    '        model = self._validate_model_id(params.get("model", config.model))',
    '            raise RpcError(-32013, "该 provider/model 不在本机配置目录中",',
    '            {"code": "MODEL_ROUTE_UNAVAILABLE", "provider": provider, "model": model})',
    "        thread = self.sessions.create(title, projectId=params.get(\"projectId\"),",
    '        self._emit_committed("thread/created", {"threadId": thread["id"], "thread": thread})',
    '        return {"thread": thread}',
)
THREAD_LIST = (
    '        return self.sessions.list_threads_page(cursor=params.get("cursor"), limit=params.get("limit", 50),',
    '                                               archived=params.get("archived", False), project_id=params.get("projectId"))',
)
THREAD_READ = (
    '        exclude = params.get("excludeTurns", False)',
    "        if type(exclude) is not bool:",
    '            raise ValueError("excludeTurns 必须是布尔值")',
    '        paged = params.get("snapshot", False)',
    "        if type(paged) is not bool:",
    '            raise ValueError("snapshot 必须是布尔值")',
    '        return self._snapshot(_text(params, "threadId"), exclude=exclude, paged=paged,',
    "                              branch=_branch_view(params))",
)
ITEMS_LIST = (
    '        limit = params.get("limit", 100)',
    "        if type(limit) is not int or not 1 <= limit <= 200:",
    '            raise ValueError("limit 必须是 1 到 200 的整数")',
    '        snapshot_id = params.get("snapshotId")',
    '            raise ValueError("snapshotId 格式无效")',
    '        scope_id = thread_id + (":" + snapshot_id if isinstance(snapshot_id, str) else "") + (":branch" if branch else "")',
    '                raise ValueError("条目分页游标无效") from None',
    '            raise ValueError("条目分页游标超出结果范围")',
    "            if wire_size(candidate_result) > MAX_PAGE_BYTES:",
    '                raise RpcError(-32010, "单个条目超过读取预算，无法在此页传输；原始记录仍保留",',
    '                                   {"code": "RESPONSE_TOO_LARGE", "itemId": item["id"]})',
)
EVENT_LIST = (
    '        source = self.sessions.events_after(params.get("cursor"), params.get("threadId"), params.get("limit", 100))',
    '        result = {"events": page, "nextCursor": params.get("cursor") or "0", "hasMore": source["hasMore"]}',
    '                raise RpcError(-32010, "单个事件超过读取预算；请读取会话快照恢复，事件游标未前移",',
    '                                   {"code": "RESPONSE_TOO_LARGE", "recoveryMethod": "thread/resume", "snapshot": True})',
)
CONFIG_READ = (
    '        unreadable = self.sessions.unreadable_thread_ids()',
    '        response = {"protocolVersion": PROTOCOL_VERSION, "workspace": str(self.workspace),',
    '"provider": self.config.provider, "model": self.config.model,',
    '"maxOutputTokens": self.config.max_tokens, "parallelThreads": self.runtimes.capacity,',
    '"maxRetainedTurns": self.runtimes.owner_capacity,',
    '"steeringMode": self.steering_mode,',
    '"modelCallsDisabled": self.model_calls_disabled,',
    '"maxAttachmentStorageBytes": self.attachment_limits.max_bytes,',
    '"maxAttachmentStorageObjects": self.attachment_limits.max_objects,',
    '"toolBundleId": self.tool_bundle.id,',
    '"autoCompaction": self.compaction_policy.describe(),',
    '"autoCompactionSource": self._auto_compaction_source,',
    '"approvalPolicy": "each-consequential-call", "approvalTimeoutSeconds": self.approval_timeout}',
    '        response["unreadableThreadCount"] = len(unreadable)',
    '        response["unreadableThreadIds"] = unreadable[:MAX_UNREADABLE_THREAD_IDS]',
)
TOOL_LIST = (
    '        return {"tools": self.registry.describe()}',
)
MODEL_LIST = (
    '            models.append({"id": model, "provider": provider, "configured": True, "available": available,',
    '                           "capabilities": self.model_catalog.resolve(provider, model).describe()})',
    '        return {"models": models,',
    '                "source": "local-config"}',
)


class _Source:
    def __init__(self) -> None:
        self.checked = 0

    def method(self, body: str, name: str, fragments: tuple[str, ...]) -> None:
        for fragment in fragments:
            if fragment not in body:
                raise ValueError(f"ApplicationService.{name} 缺少：{fragment}")
            self.checked += 1

    def order(self, body: str, name: str, fragments: tuple[str, ...]) -> None:
        position = -1
        for fragment in fragments:
            found = body.find(fragment, position + 1)
            if found < 0:
                raise ValueError(f"ApplicationService.{name} 的顺序缺少：{fragment}")
            position = found
            self.checked += 1


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
    checks = _Source()
    checks.order(_method(tree, source, "on_thread_start"), "on_thread_start", THREAD_START)
    checks.method(_method(tree, source, "on_thread_list"), "on_thread_list", THREAD_LIST)
    checks.order(_method(tree, source, "on_thread_read"), "on_thread_read", THREAD_READ)
    checks.order(_method(tree, source, "on_items_list"), "on_items_list", ITEMS_LIST)
    checks.order(_method(tree, source, "on_event_list"), "on_event_list", EVENT_LIST)
    checks.order(_method(tree, source, "on_config_read"), "on_config_read", CONFIG_READ)
    checks.method(_method(tree, source, "on_tool_list"), "on_tool_list", TOOL_LIST)
    checks.method(_method(tree, source, "on_model_list"), "on_model_list", MODEL_LIST)
    return checks.checked


@contextmanager
def _clean_environment():
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        yield


@contextmanager
def _service():
    with TemporaryDirectory() as directory, _clean_environment():
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, Path(directory), ModelConfig(provider="none", model="none"),
                                     None)
        try:
            service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                                   "protocolVersion": "0.2.0"})
            service.on_initialized(None)
            yield service
        finally:
            if service._state != "stopped":
                service.close()


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"只读入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"只读入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"只读入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message:
            raise ValueError(
                f"只读入口行为变化 {label}：期望 RpcError({code}, {message!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, {str(error)!r})") from None
        return 1
    raise ValueError(f"只读入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _threads(service: ApplicationService, count: int) -> list[str]:
    ids = []
    for index in range(count):
        ids.append(service.on_thread_start({"title": f"会话{index}"})["thread"]["id"])
    return ids


def _append_messages(service: ApplicationService, thread_id: str, count: int) -> None:
    for index in range(count):
        service.sessions.append(thread_id, Entry(type="item",
                                                 payload={"kind": "userMessage", "text": f"消息{index}"}))


def _thread_checks() -> int:
    checked = 0
    with _service() as service:
        thread = service.on_thread_start({})["thread"]
        checked += _expect_value({key: thread[key] for key in ("title", "provider", "model",
                                                              "toolPolicy", "archived", "cwd")},
                                 {"title": "新会话", "provider": "none", "model": "none",
                                  "toolPolicy": "approval", "archived": False,
                                  "cwd": str(service.workspace)}, "默认线程投影")
        checked += _expect_value(re.fullmatch(r"[a-f0-9]{12}", thread["id"]) is not None, True,
                                 "线程标识格式")
        checked += _expect_value(service.on_thread_start({"toolPolicy": "readOnly"})["thread"]["toolPolicy"],
                                 "readOnly", "只读策略")
        for title in (1, "x" * 501):
            checked += _expect_error(lambda title=title: service.on_thread_start({"title": title}),
                                     "title 必须是最多 500 字符的字符串", f"标题 {title!r}")
        checked += _expect_error(lambda: service.on_thread_start({"toolPolicy": "open"}),
                                 "toolPolicy 必须是 readOnly 或 approval", "工具策略拒绝")
        checked += _expect_rpc(lambda: service.on_thread_start({"provider": "anthropic"}),
                               -32013, "本机没有可用的该模型线路配置", "线路不可用")
        checked += _expect_rpc(lambda: service.on_thread_start({"model": "other"}),
                               -32013, "该 provider/model 不在本机配置目录中", "模型不在目录")
        events = service.on_event_list({})
        created = [event for event in events["events"] if event["method"] == "thread/created"]
        checked += _expect_value(len(created), 2, "创建事件数量")
        checked += _expect_value(set(created[0]["params"]),
                                 {"eventId", "eventCursor", "threadId", "thread"}, "创建事件字段")
        checked += _expect_value(created[0]["params"]["threadId"], thread["id"], "创建事件线程")
    return checked


def _list_checks() -> int:
    checked = 0
    with _service() as service:
        first, second = _threads(service, 2)
        listed = service.on_thread_list({})
        checked += _expect_value(set(listed), {"threads", "nextCursor"}, "列表键")
        checked += _expect_value(len(listed["threads"]), 2, "默认列表数量")
        checked += _expect_value(service.on_thread_list({"archived": True})["threads"], [], "默认排除归档")
        service.on_thread_archive({"threadId": second})
        active = service.on_thread_list({})
        archived = service.on_thread_list({"archived": True})
        checked += _expect_value([item["id"] for item in active["threads"]], [first], "归档后活动列表")
        checked += _expect_value([item["id"] for item in archived["threads"]], [second], "归档列表")
    return checked


def _read_checks() -> int:
    checked = 0
    with _service() as service:
        thread_id = _threads(service, 1)[0]
        _append_messages(service, thread_id, 3)
        read = service.on_thread_read({"threadId": thread_id})
        checked += _expect_value(set(read), {"thread", "turns", "items", "eventCursor", "activeTurnId",
                                             "queue", "queueActiveItems", "queueCounts",
                                             "queueTotalItems", "queueTruncated"}, "读取键")
        checked += _expect_value(len(read["items"]), 3, "读取条目数量")
        checked += _expect_value(read["thread"]["id"], thread_id, "读取线程标识")
        excluded = service.on_thread_read({"threadId": thread_id, "excludeTurns": True})
        checked += _expect_value((excluded["turns"], excluded["items"]), (None, []), "排除回合")
        paged = service.on_thread_read({"threadId": thread_id, "snapshot": True})
        checked += _expect_value(set(paged), {"thread", "turns", "items", "itemCount", "snapshotId",
                                              "eventCursor", "activeTurnId", "queue", "queueActiveItems",
                                              "queueCounts", "queueTotalItems", "queueTruncated"},
                                 "快照键")
        checked += _expect_value(re.fullmatch(r"[a-f0-9]{32}", paged["snapshotId"]) is not None, True,
                                 "快照标识")
        checked += _expect_value((paged["items"], paged["itemCount"]), ([], 3), "快照分页内容")
        checked += _expect_error(lambda: service.on_thread_read({"threadId": thread_id, "excludeTurns": 1}),
                                 "excludeTurns 必须是布尔值", "排除参数类型")
        checked += _expect_error(lambda: service.on_thread_read({"threadId": thread_id, "snapshot": "yes"}),
                                 "snapshot 必须是布尔值", "快照参数类型")
        checked += _expect_error(lambda: service.on_thread_read({"threadId": "000000000000"}),
                                 "会话不存在", "未知线程")
        checked += _expect_error(lambda: service.on_items_list({"threadId": "short"}),
                                 "threadId 格式无效", "线程标识格式")
    return checked


def _items_checks() -> int:
    checked = 0
    with _service() as service:
        thread_id = _threads(service, 1)[0]
        empty = service.on_items_list({"threadId": thread_id})
        checked += _expect_value(empty, {"items": [], "nextCursor": None}, "空条目页")
        for limit in (0, 201, True, "50"):
            checked += _expect_error(
                lambda limit=limit: service.on_items_list({"threadId": thread_id, "limit": limit}),
                "limit 必须是 1 到 200 的整数", f"条目上限 {limit!r}")
        checked += _expect_error(
            lambda: service.on_items_list({"threadId": thread_id, "snapshotId": "xyz"}),
            "snapshotId 格式无效", "快照标识格式")
        checked += _expect_error(
            lambda: service.on_items_list({"threadId": thread_id, "cursor": "!!"}),
            "条目分页游标无效", "游标解码")
        beyond = base64.urlsafe_b64encode(json.dumps([thread_id, 5]).encode()).decode()
        checked += _expect_error(
            lambda: service.on_items_list({"threadId": thread_id, "cursor": beyond}),
            "条目分页游标超出结果范围", "游标越界")
        _append_messages(service, thread_id, 3)
        first = service.on_items_list({"threadId": thread_id, "limit": 2})
        checked += _expect_value((len(first["items"]), first["nextCursor"] is not None),
                                 (2, True), "首页")
        second = service.on_items_list({"threadId": thread_id, "limit": 2, "cursor": first["nextCursor"]})
        checked += _expect_value((len(second["items"]), second["nextCursor"]), (1, None), "次页")
        checked += _expect_value([item["kind"] for item in first["items"] + second["items"]],
                                 ["userMessage"] * 3, "条目投影")
        snapshot = service.on_thread_read({"threadId": thread_id, "snapshot": True})
        paged = service.on_items_list({"threadId": thread_id, "snapshotId": snapshot["snapshotId"],
                                       "limit": 2})
        checked += _expect_value((len(paged["items"]), paged["nextCursor"] is not None),
                                 (2, True), "快照首页")
        rest = service.on_items_list({"threadId": thread_id, "snapshotId": snapshot["snapshotId"],
                                      "limit": 2, "cursor": paged["nextCursor"]})
        checked += _expect_value((len(rest["items"]), rest["nextCursor"]), (1, None), "快照次页")
    return checked


def _event_checks() -> int:
    checked = 0
    with _service() as service:
        first, second = _threads(service, 2)
        service.on_thread_start({"title": "第三条"})
        page = service.on_event_list({"limit": 2})
        checked += _expect_value((len(page["events"]), page["hasMore"]), (2, True), "事件首页")
        rest = service.on_event_list({"cursor": page["nextCursor"]})
        checked += _expect_value((len(rest["events"]), rest["hasMore"]), (1, False), "事件次页")
        filtered = service.on_event_list({"threadId": first})
        checked += _expect_value([event["params"]["threadId"] for event in filtered["events"]],
                                 [first], "事件线程过滤")
        checked += _expect_error(lambda: service.on_event_list({"threadId": "000000000000"}),
                                 "会话不存在", "未知线程事件")
        checked += _expect_value(service.on_event_list({"threadId": second})["events"][0]["params"]["threadId"],
                                 second, "第二线程事件")
        checked += _expect_value(set(page["events"][0]), {"method", "params"}, "事件条目键")
    return checked


def _config_checks() -> int:
    checked = 0
    with _service() as service:
        config = service.on_config_read({})
        checked += _expect_value(set(config), {
            "protocolVersion", "workspace", "provider", "model", "maxOutputTokens",
            "parallelThreads", "maxRetainedTurns", "maxModelRequests", "steeringMode",
            "modelCallsDisabled", "maxAttachmentStorageBytes", "maxAttachmentStorageObjects",
            "modelCapabilities", "toolBundleId", "autoCompaction", "autoCompactionSource",
            "approvalPolicy", "approvalTimeoutSeconds", "unreadableThreadCount",
            "unreadableThreadIds"}, "配置键")
        checked += _expect_value({key: config[key] for key in (
            "protocolVersion", "provider", "model", "maxOutputTokens", "parallelThreads",
            "maxRetainedTurns", "maxModelRequests", "steeringMode", "modelCallsDisabled",
            "maxAttachmentStorageBytes", "maxAttachmentStorageObjects", "toolBundleId",
            "autoCompactionSource", "approvalPolicy", "approvalTimeoutSeconds",
            "unreadableThreadCount", "unreadableThreadIds")}, {
            "protocolVersion": "0.2.0", "provider": "none", "model": "none",
            "maxOutputTokens": 64000, "parallelThreads": 8, "maxRetainedTurns": 16,
            "maxModelRequests": 6, "steeringMode": "all", "modelCallsDisabled": False,
            "maxAttachmentStorageBytes": 512 * 1024 * 1024, "maxAttachmentStorageObjects": 4096,
            "toolBundleId": "boss", "autoCompactionSource": "default",
            "approvalPolicy": "each-consequential-call", "approvalTimeoutSeconds": 300.0,
            "unreadableThreadCount": 0, "unreadableThreadIds": []}, "配置取值")
        checked += _expect_value(config["workspace"], str(service.workspace), "工作区路径")
        checked += _expect_value(config["autoCompaction"], {
            "enabled": True, "triggerPercent": 80, "keepRecentTokens": 20000,
            "provider": None, "model": None, "effort": None}, "压缩策略投影")
        checked += _expect_value(config["modelCapabilities"], {
            "contextWindow": 200000, "maxOutputTokens": 64000,
            "capabilitySource": "legacy-default", "capacityIsEstimate": True,
            "reasoningEfforts": []}, "模型能力投影")
    return checked


def _tool_checks() -> int:
    checked = 0
    with _service() as service:
        tools = service.on_tool_list({})["tools"]
        checked += _expect_value(len(tools), 14, "工具数量")
        checked += _expect_value(set(tools[0]), {"name", "description", "inputSchema",
                                                 "maxModelResultBytes", "readOnly",
                                                 "requiresApproval", "executionMode"}, "工具条目键")
        names = {tool["name"] for tool in tools}
        checked += _expect_value("boss_hr_greet" in names, True, "审批工具在列")
        greet = next(tool for tool in tools if tool["name"] == "boss_hr_greet")
        checked += _expect_value((greet["readOnly"], greet["requiresApproval"]), (False, True),
                                 "审批工具标记")
        readonly = [tool for tool in tools if tool["readOnly"]]
        checked += _expect_value(len(readonly), 13, "只读工具数量")
    return checked


def _model_checks() -> int:
    checked = 0
    with _service() as service:
        listing = service.on_model_list({})
        checked += _expect_value(set(listing), {"models", "source"}, "模型列表键")
        checked += _expect_value(listing["source"], "local-config", "模型来源")
        checked += _expect_value(len(listing["models"]), 1, "线路数量")
        model = listing["models"][0]
        checked += _expect_value(set(model), {"id", "provider", "configured", "available",
                                              "capabilities"}, "线路条目键")
        checked += _expect_value({key: model[key] for key in ("id", "provider", "configured",
                                                              "available")},
                                 {"id": "none", "provider": "none", "configured": True,
                                  "available": True}, "none 线路")
        checked += _expect_value(model["capabilities"]["capabilitySource"], "legacy-default",
                                 "能力来源")
    return checked


def _skills_checks() -> int:
    checked = 0
    with _service() as service:
        listing = service.on_skills_list({})
        checked += _expect_value(listing, {"skills": [], "problems": [],
                                           "root": ".boss-harness/skills"}, "空技能目录")
        checked += _expect_error(lambda: service.on_skills_read({"name": "missing"}),
                                 "skills/read 只接受 id", "技能读取参数")
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _thread_checks()
    checked += _list_checks()
    checked += _read_checks()
    checked += _items_checks()
    checked += _event_checks()
    checked += _config_checks()
    checked += _tool_checks()
    checked += _model_checks()
    checked += _skills_checks()
    return checked


def check_reads() -> int:
    reference = _read(TECHNICAL_REFERENCE)
    for marker in ("check_application_reads.py", "### `check_application_reads.py`",
                   "只读查询入口"):
        if marker not in reference:
            raise ValueError(f"技术参考缺少只读入口检查说明：{marker}")
    structural = _check_structures()
    behavioral = _behavior_checks()
    return structural, behavioral


def main() -> int:
    try:
        structural, behavioral = check_reads()
    except ValueError as error:
        print(error)
        return 1
    print(f"只读查询入口一致：{structural} 项结构、{behavioral} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
