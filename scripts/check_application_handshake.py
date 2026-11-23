#!/usr/bin/env python3
"""核对内核握手状态机：顺序、协议协商、能力声明与桥接投影。

`ApplicationService` 以 `_check_ready` 把连接限制在 cold → initializing →
ready 的顺序里：`initialize` 校验 `clientInfo`、协议版本与客户端能力，按协议
版本决定单步就绪还是等待 `initialized`，并一次性投影工具桥、模型线路、审批与
事件游标。这里在临时状态目录中真实构造服务（`provider=none`，不联网、不调用
上游），逐类验证拒绝分支与投影字段；静态部分锁定这些分支的源码顺序。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.compaction import CompactionPolicy  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer, RpcError  # noqa: E402
from boss_harness.settings import save_auto_compaction  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
CAPABILITY_KEYS = (
    "bidirectionalRequests", "eventReplay", "pagination", "parallelThreads",
    "durableApprovals", "explicitTurnContinuation", "sessionLeaf",
    "sessionBranchViews", "sessionBranchTree", "sessionBranchSummary",
    "sessionBranchSnapshots", "sessionBranchSummaryRead", "threadUsage",
    "sessionModelSelection", "threadExport", "threadSearch",
    "threadSearchArchived", "workspaceInstructionsEdit", "skillsRead",
    "skillsCreate", "skillsWrite", "skillsDelete", "queueUpdate", "queueSteer",
    "attachmentReadPaging", "autoCompactionConfig",
)
READY = (
    '        if method == "initialize" or method == "shutdown":',
    "            return",
    '        if method == "initialized" and self._state == "initializing":',
    "            return",
    '        if self._state != "ready":',
    '            raise RpcError(-32002, "先完成 initialize → initialized 握手")',
)
INIT_ENTRY = (
    '        if self._state != "cold":',
    '            raise RpcError(-32600, "连接已经初始化")',
    "        params = params or {}",
    '        info = params.get("clientInfo")',
    "        if not isinstance(info, dict):",
    '            raise ValueError("clientInfo 必须包含 name 和 version")',
    '        _text(info, "name", maximum=200)',
    '        _text(info, "version", maximum=100)',
)
INIT_PROTOCOL = (
    '        protocol = params.get("protocolVersion", "0.1.0")',
    "        if not isinstance(protocol, str):",
    '            raise ValueError("protocolVersion 必须是字符串")',
    '        if protocol not in {"0.1.0", PROTOCOL_VERSION}:',
    '            raise RpcError(-32000, "协议版本不兼容", {"supported": ["0.1.0", PROTOCOL_VERSION]})',
)
INIT_CAPS = (
    '        capabilities = params.get("capabilities")',
    "        if capabilities is None:",
    "            capabilities = {}",
    "        if not isinstance(capabilities, dict):",
    '            raise ValueError("capabilities 必须是对象或 null")',
    '        bidirectional = capabilities.get("bidirectionalRequests", False)',
    '        opt_out = capabilities.get("optOutNotificationMethods", [])',
    "        if type(bidirectional) is not bool or not isinstance(opt_out, list) or len(opt_out) > 128 or any(",
    "                not isinstance(name, str) or len(name) > 200 for name in opt_out):",
    '            raise ValueError("客户端能力声明无效")',
)
INIT_STATE = (
    "        bridge_description = self._bridge_description()",
    "        self._bidirectional = bidirectional and protocol == PROTOCOL_VERSION",
    "        self._protocol = protocol",
    "        self.server.opt_out_notifications = frozenset(opt_out)",
    '        self._state = "initializing" if protocol == PROTOCOL_VERSION else "ready"',
    '        anthropic = self.config.provider == "anthropic"',
)
INIT_RESULT = (
    '        return {"serverName": "boss-harness", "serverVersion": __version__, "protocolVersion": protocol,',
    '            "capabilities": {"bidirectionalRequests": True, "eventReplay": True,',
    '                             "pagination": True, "parallelThreads": True,',
    '                             "durableApprovals": True, "explicitTurnContinuation": True,',
    '                             "sessionLeaf": True, "sessionBranchViews": True,',
    '                             "sessionBranchTree": True, "sessionBranchSummary": True,',
    '                             "sessionBranchSnapshots": True, "sessionBranchSummaryRead": True,',
    '                             "threadUsage": True, "sessionModelSelection": True, "threadExport": True,',
    '                             "threadSearch": True, "threadSearchArchived": True,',
    '                             "workspaceInstructionsEdit": True, "skillsRead": True,',
    '                             "skillsCreate": True, "skillsWrite": True,',
    '                             "skillsDelete": True, "queueUpdate": True,',
    '                             "queueSteer": True,',
    '                           "attachmentReadPaging": True,',
    '                             "autoCompactionConfig": self._auto_compaction_source in {"stored", "default"}},',
    '            "toolBridge": {**bridge_description, "tools": self.runner.tool_names,',
    '                           "bundleId": self.tool_bundle.id},',
    '            "modelBridge": {"provider": self.config.provider, "model": self.config.model,',
    '                "driven": self.provider is not None, "modelCallsDisabled": self.model_calls_disabled,',
    '                "thinking": dict(self.config.thinking) if anthropic and self.config.thinking else None,',
    '                "serverSideFallback": anthropic and self.config.server_side_fallback},',
    '            "approval": {"requiredTools": sorted(self.approval_required), "timeoutSeconds": self.approval_timeout},',
    '            "eventCursor": self.sessions.latest_event_cursor()}',
)
INITIALIZED = (
    '        if self._state != "initializing":',
    '            raise RpcError(-32600, "连接不在初始化阶段")',
    '        self._state = "ready"',
    '        return {"ready": True}',
)
BRIDGE = (
    "            metadata = self.tool_bundle.describe_bridge(self.tools)",
    "        except Exception:",
    '            raise ValueError("工具桥描述回调失败") from None',
    '        if not isinstance(metadata, dict) or type(metadata.get("available")) is not bool:',
    '            raise ValueError("工具桥描述必须包含布尔 available")',
    "            encoded = json.dumps(metadata, ensure_ascii=False, allow_nan=False)",
    "            if len(encoded.encode()) > 16 * 1024:",
    "            return json.loads(encoded)",
    "        except (TypeError, ValueError, RecursionError):",
    '            raise ValueError("工具桥描述必须是有界 JSON 元数据") from None',
)
REGISTER = (
    '"initialize": self.on_initialize, "initialized": self.on_initialized,',
)
DISPATCH = ("server.before_dispatch = self._check_ready",)


class _Source:
    """按顺序保存片段，便于逐段定位缺失位置。"""

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
    checks.order(_method(tree, source, "_check_ready"), "_check_ready", READY)
    initialize = _method(tree, source, "on_initialize")
    checks.method(initialize, "on_initialize", INIT_ENTRY)
    checks.order(initialize, "on_initialize", INIT_PROTOCOL)
    checks.order(initialize, "on_initialize", INIT_CAPS)
    checks.order(initialize, "on_initialize", INIT_STATE)
    checks.method(initialize, "on_initialize", INIT_RESULT)
    checks.method(_method(tree, source, "on_initialized"), "on_initialized", INITIALIZED)
    checks.method(_method(tree, source, "_bridge_description"), "_bridge_description", BRIDGE)
    checks.method(_method(tree, source, "_register"), "_register", REGISTER)
    checks.method(_method(tree, source, "__init__"), "__init__", DISPATCH)
    return checks.checked


@contextmanager
def _clean_environment(overrides: dict[str, str] | None = None):
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        if overrides:
            os.environ.update(overrides)
        yield


@contextmanager
def _service(*, settings: dict | None = None, environment: dict[str, str] | None = None,
             config: ModelConfig | None = None, **kwargs):
    with TemporaryDirectory() as directory, _clean_environment(environment):
        root = Path(directory)
        if settings is not None:
            save_auto_compaction(root, settings)
        server = JsonRpcServer()
        service = ApplicationService(server, root, config or ModelConfig(provider="none", model="none"),
                                     None, **kwargs)
        try:
            yield server, service
        finally:
            if service._state != "stopped":
                service.close()


def _params(**overrides) -> dict:
    params = {"clientInfo": {"name": "probe", "version": "1.0"}, "protocolVersion": "0.2.0"}
    params.update(overrides)
    return params


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"握手行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_rpc(call, code: int, message: str, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if error.code != code or str(error) != message:
            raise ValueError(
                f"握手行为变化 {label}：期望 ({code}, {message!r})，实际 ({error.code}, {str(error)!r})") from None
        return 1
    raise ValueError(f"握手行为变化 {label}：期望 RpcError({code})，实际未抛出")


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"握手行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"握手行为变化 {label}：期望 ValueError，实际未抛出")


def _state_checks() -> int:
    checked = 0
    with _service() as (server, service):
        checked += _expect_value(service._state, "cold", "初始状态")
        checked += _expect_value((service._protocol, service._bidirectional), ("0.1.0", False), "初始协议")
        for method in ("initialize", "shutdown"):
            service._check_ready(method)
            checked += 1
        checked += _expect_rpc(lambda: service._check_ready("thread/read"), -32002,
                               "先完成 initialize → initialized 握手", "冷启动拒绝")
        checked += _expect_rpc(lambda: service.on_initialized(None), -32600,
                               "连接不在初始化阶段", "冷启动 initialized")
        result = service.on_initialize(_params())
        checked += _expect_value(service._state, "initializing", "0.2.0 初始化阶段")
        service._check_ready("initialized")
        checked += 1
        checked += _expect_rpc(lambda: service._check_ready("thread/read"), -32002,
                               "先完成 initialize → initialized 握手", "初始化阶段拒绝")
        checked += _expect_rpc(lambda: service.on_initialize(_params()), -32600,
                               "连接已经初始化", "重复 initialize")
        checked += _expect_value(service.on_initialized(None), {"ready": True}, "initialized 返回")
        checked += _expect_value(service._state, "ready", "就绪状态")
        service._check_ready("thread/read")
        checked += 1
        checked += _expect_value(service.on_shutdown(None), {"stopped": True}, "shutdown 返回")
        checked += _expect_value(service._state, "stopped", "停止状态")
        checked += _expect_value(result["protocolVersion"], "0.2.0", "回报协议版本")
    return checked


def _legacy_checks() -> int:
    checked = 0
    with _service() as (server, service):
        result = service.on_initialize(_params(protocolVersion="0.1.0"))
        checked += _expect_value(service._state, "ready", "0.1.0 单步就绪")
        checked += _expect_value(service._bidirectional, False, "0.1.0 不启用双向")
        checked += _expect_value(result["protocolVersion"], "0.1.0", "0.1.0 回报版本")
        checked += _expect_rpc(lambda: service.on_initialized(None), -32600,
                               "连接不在初始化阶段", "0.1.0 已就绪")
    with _service() as (server, service):
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"}})
        checked += _expect_value(service._state, "ready", "缺省版本按 0.1.0")
        checked += _expect_value(service._protocol, "0.1.0", "缺省协议")
    return checked


def _client_checks() -> int:
    checked = 0
    cases = (
        ({}, "clientInfo 必须包含 name 和 version"),
        ({"clientInfo": []}, "clientInfo 必须包含 name 和 version"),
        ({"clientInfo": None}, "clientInfo 必须包含 name 和 version"),
        ({"clientInfo": "probe"}, "clientInfo 必须包含 name 和 version"),
        ({"clientInfo": {"version": "1.0"}}, "name 必须是非空字符串（最多 200 字符）"),
        ({"clientInfo": {"name": "   ", "version": "1.0"}}, "name 必须是非空字符串（最多 200 字符）"),
        ({"clientInfo": {"name": "p" * 201, "version": "1.0"}}, "name 必须是非空字符串（最多 200 字符）"),
        ({"clientInfo": {"name": "probe"}}, "version 必须是非空字符串（最多 100 字符）"),
        ({"clientInfo": {"name": "probe", "version": "v" * 101}}, "version 必须是非空字符串（最多 100 字符）"),
    )
    with _service() as (server, service):
        for params, message in cases:
            checked += _expect_error(lambda params=params: service.on_initialize(params), message, f"clientInfo {params!r}")
        checked += _expect_value(service._state, "cold", "非法 clientInfo 不改变状态")
    return checked


def _protocol_checks() -> int:
    checked = 0
    with _service() as (server, service):
        for value in ([], {}, None, 1, True, 0.2):
            checked += _expect_error(
                lambda value=value: service.on_initialize(_params(protocolVersion=value)),
                "protocolVersion 必须是字符串", f"版本 {value!r}")
        try:
            service.on_initialize(_params(protocolVersion="9.9.9"))
        except RpcError as error:
            checked += _expect_value((error.code, str(error), error.data),
                                     (-32000, "协议版本不兼容", {"supported": ["0.1.0", "0.2.0"]}),
                                     "不兼容版本")
        else:
            raise ValueError("握手行为变化 不兼容版本：期望 RpcError(-32000)，实际未抛出")
        checked += _expect_value(service._state, "cold", "非法版本不改变状态")
    return checked


def _capability_checks() -> int:
    checked = 0
    with _service() as (server, service):
        for value in ([], "probe", 1):
            checked += _expect_error(
                lambda value=value: service.on_initialize(_params(capabilities=value)),
                "capabilities 必须是对象或 null", f"能力 {value!r}")
        for value in (1, 0, "true", None, []):
            checked += _expect_error(
                lambda value=value: service.on_initialize(
                    _params(capabilities={"bidirectionalRequests": value})),
                "客户端能力声明无效", f"双向 {value!r}")
        for value in ({}, "probe", 1, None):
            checked += _expect_error(
                lambda value=value: service.on_initialize(
                    _params(capabilities={"optOutNotificationMethods": value})),
                "客户端能力声明无效", f"退订 {value!r}")
        checked += _expect_error(
            lambda: service.on_initialize(_params(capabilities={"optOutNotificationMethods": ["x"] * 129})),
            "客户端能力声明无效", "退订数量上限")
        checked += _expect_error(
            lambda: service.on_initialize(_params(capabilities={"optOutNotificationMethods": [1]})),
            "客户端能力声明无效", "退订元素类型")
        checked += _expect_error(
            lambda: service.on_initialize(_params(capabilities={"optOutNotificationMethods": ["n" * 201]})),
            "客户端能力声明无效", "退订元素长度")
        checked += _expect_value(service._state, "cold", "非法能力不改变状态")
        service.on_initialize(_params(capabilities={
            "bidirectionalRequests": True, "optOutNotificationMethods": ["a", "b", "a"]}))
        checked += _expect_value(service._bidirectional, True, "0.2.0 双向生效")
        checked += _expect_value(server.opt_out_notifications, frozenset({"a", "b"}), "退订集去重")
    with _service() as (server, service):
        service.on_initialize(_params(capabilities={"bidirectionalRequests": False}))
        checked += _expect_value(service._bidirectional, False, "显式关闭双向")
        checked += _expect_value(server.opt_out_notifications, frozenset(), "缺省退订为空")
    with _service() as (server, service):
        service.on_initialize(_params(protocolVersion="0.1.0",
                                      capabilities={"bidirectionalRequests": True}))
        checked += _expect_value(service._bidirectional, False, "0.1.0 忽略双向声明")
    with _service() as (server, service):
        service.on_initialize(_params(capabilities=None))
        checked += _expect_value((service._state, service._bidirectional), ("initializing", False),
                                 "显式空能力")
    return checked


def _result_checks() -> int:
    checked = 0
    with _service() as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(set(result), {"serverName", "serverVersion", "protocolVersion",
                                               "capabilities", "toolBridge", "modelBridge",
                                               "approval", "eventCursor"}, "握手结果键")
        checked += _expect_value(result["serverName"], "boss-harness", "服务名")
        checked += _expect_value(isinstance(result["serverVersion"], str) and bool(result["serverVersion"]),
                                 True, "服务版本为非空字符串")
        checked += _expect_value(result["capabilities"], {key: True for key in CAPABILITY_KEYS},
                                 "能力投影")
        bridge = result["toolBridge"]
        checked += _expect_value(set(bridge), {"available", "binary", "binarySource", "tools", "bundleId"},
                                 "工具桥键")
        checked += _expect_value(type(bridge["available"]) is bool, True, "工具桥可用性为布尔")
        checked += _expect_value(bridge["bundleId"], "boss", "工具组合标识")
        checked += _expect_value(len(bridge["tools"]), 14, "工具数量")
        checked += _expect_value("boss_hr_greet" in bridge["tools"], True, "审批工具在列")
        checked += _expect_value(result["modelBridge"], {
            "provider": "none", "model": "none", "driven": False, "modelCallsDisabled": False,
            "thinking": None, "serverSideFallback": False}, "模型桥投影")
        checked += _expect_value(result["approval"], {"requiredTools": ["boss_hr_greet"],
                                                      "timeoutSeconds": 300.0}, "审批投影")
        checked += _expect_value(result["eventCursor"], service.sessions.latest_event_cursor(),
                                 "事件游标")
        checked += _expect_value(result["eventCursor"], "0", "空会话事件游标")
        checked += _expect_value(type(result["eventCursor"]) is str, True, "事件游标为字符串")
    return checked


def _source_checks() -> int:
    checked = 0
    with _service() as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(service._auto_compaction_source, "default", "默认来源")
        checked += _expect_value(result["capabilities"]["autoCompactionConfig"], True, "默认来源可配置")
    with _service(settings={"enabled": False, "triggerPercent": 80,
                            "keepRecentTokens": 20_000}) as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(service._auto_compaction_source, "stored", "持久来源")
        checked += _expect_value(service.compaction_policy.enabled, False, "持久策略生效")
        checked += _expect_value(result["capabilities"]["autoCompactionConfig"], True, "持久来源可配置")
    with _service(environment={"BOSS_HARNESS_COMPACTION": '{"enabled": false}'}) as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(service._auto_compaction_source, "environment", "环境来源")
        checked += _expect_value(service.compaction_policy.enabled, False, "环境策略生效")
        checked += _expect_value(result["capabilities"]["autoCompactionConfig"], False, "环境来源不可改")
    with _service(compaction_policy=CompactionPolicy(enabled=False)) as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(service._auto_compaction_source, "explicit", "显式来源")
        checked += _expect_value(result["capabilities"]["autoCompactionConfig"], False, "显式来源不可改")
    return checked


def _disabled_checks() -> int:
    checked = 0
    with _service(model_calls_disabled=True) as (server, service):
        result = service.on_initialize(_params())
        checked += _expect_value(service.model_calls_disabled, True, "禁用模型调用")
        checked += _expect_value(result["modelBridge"]["modelCallsDisabled"], True, "模型桥禁用标记")
        checked += _expect_value(result["modelBridge"]["driven"], False, "禁用后无驱动线路")
    return checked


def _bridge_checks() -> int:
    checked = 0
    cases = (
        (lambda tools: 1 / 0, "工具桥描述回调失败", "回调异常"),
        (lambda tools: [], "工具桥描述必须包含布尔 available", "非对象"),
        (lambda tools: {"available": 1}, "工具桥描述必须包含布尔 available", "可用性非布尔"),
        (lambda tools: {"available": None}, "工具桥描述必须包含布尔 available", "可用性为空"),
        (lambda tools: {"available": True, "extra": {1, 2}}, "工具桥描述必须是有界 JSON 元数据", "不可序列化"),
        (lambda tools: {"available": True, "n": float("nan")}, "工具桥描述必须是有界 JSON 元数据", "NaN"),
        (lambda tools: {"available": True, "pad": "x" * (17 * 1024)}, "工具桥描述必须是有界 JSON 元数据", "超过 16 KiB"),
    )
    with _service() as (server, service):
        original = service.tool_bundle
        try:
            for callback, message, label in cases:
                service.tool_bundle = SimpleNamespace(describe_bridge=callback)
                checked += _expect_error(service._bridge_description, message, label)
            recursive = {"available": True}
            recursive["self"] = recursive
            service.tool_bundle = SimpleNamespace(describe_bridge=lambda tools: recursive)
            checked += _expect_error(service._bridge_description, "工具桥描述必须是有界 JSON 元数据",
                                     "循环引用")
            metadata = {"available": True, "binary": "/tmp/boss", "binarySource": "explicit"}
            service.tool_bundle = SimpleNamespace(describe_bridge=lambda tools: metadata)
            copied = service._bridge_description()
            checked += _expect_value(copied, metadata, "合法描述")
            checked += _expect_value(copied is metadata, False, "描述为深拷贝")
            copied["binary"] = "changed"
            checked += _expect_value(metadata["binary"], "/tmp/boss", "修改副本不影响原对象")
        finally:
            service.tool_bundle = original
        result = service.on_initialize(_params())
        checked += _expect_value(set(result["toolBridge"]), {"available", "binary", "binarySource",
                                                             "tools", "bundleId"}, "恢复后握手可用")
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _state_checks()
    checked += _legacy_checks()
    checked += _client_checks()
    checked += _protocol_checks()
    checked += _capability_checks()
    checked += _result_checks()
    checked += _source_checks()
    checked += _disabled_checks()
    checked += _bridge_checks()
    return checked


def check_handshake() -> int:
    reference = _read(TECHNICAL_REFERENCE)
    for marker in ("check_application_handshake.py", "### `check_application_handshake.py`",
                   "握手状态机"):
        if marker not in reference:
            raise ValueError(f"技术参考缺少握手检查说明：{marker}")
    structural = _check_structures()
    behavioral = _behavior_checks()
    return structural, behavioral


def main() -> int:
    try:
        structural, behavioral = check_handshake()
    except ValueError as error:
        print(error)
        return 1
    print(f"应用握手一致：{structural} 项结构、{behavioral} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
