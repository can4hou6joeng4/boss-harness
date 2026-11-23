#!/usr/bin/env python3
"""核对连接检查的只读报告、登录校验与关停边界。

`ConnectionChecks` 是内核与模型 / 招聘平台之间的检查服务：它只在用户触发时
访问网络，报告不得携带上游消息或账号细节；扫码登录只接受官方 Cookie 的格式
与大小校验后的数据；`is_idle` 决定退出前能否关闭共享资源，`prepare_close` /
`close` 必须取消全部活动检查并在锁外等待，非协作 worker 超时后保留所有权。

这里先按源码固定未被子结构脚本覆盖的契约（`is_idle`、`read` 深拷贝与禁用覆盖、
`_error` 公开码白名单、`_new_bridge` 身份校验、`model_calls_disabled` 约束、空闲
通知在锁外、模型检查的成功判定与准备顺序），再用假桥与假 provider 实际构造
`ConnectionChecks` 执行报告、登录、平台检查、模型检查与关停；不访问网络、不调用
真实模型。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/connections.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.bridge_lifecycle import BridgeLifecycle  # noqa: E402
from boss_harness.connections import ConnectionChecks  # noqa: E402
from boss_harness.models import ModelConfig  # noqa: E402
from boss_harness.models.types import AssistantMessage, StreamEvent, TextBlock, ToolCallBlock  # noqa: E402
from boss_harness.request_policy import ModelRequestRejected  # noqa: E402
from boss_harness.rpc import RpcError  # noqa: E402

IS_IDLE = (
    "def is_idle(self) -> bool:",
    "        with self.lock:",
    "            return not self.active",
)
READ = (
    "            report = deepcopy(self.report)",
    "            if self.bridge_factory is None:",
    '                report["cli"].update(_disabled())',
    '                report["platform"].update(_disabled())',
)
ERROR = (
    '        raw = (result.error or {}).get("code", "CONNECTION_FAILED")',
    "        # Do not expose upstream messages/hints, which can contain account details.",
    '        code = raw if isinstance(raw, str) and raw in PUBLIC_CHECK_CODES else "CONNECTION_FAILED"',
    "        blocked = should_pause(result)",
    '        summary = "平台要求恢复登录或处理验证；已停止访问，请在官方页面处理后手动重新检查" if blocked else "检查失败，请核对本机配置或网络后重试"',
    '        return {"state": "blocked" if blocked else "failed", "code": code, "summary": summary}',
)
NEW_BRIDGE = (
    "        bridge = self.bridge_factory()",
    "        try:",
    "            weakref.ref(bridge)",
    "        except TypeError:",
    "            self.bridge_lifecycle.close(bridge)",
    '            raise ValueError("工具桥实例必须支持独立身份跟踪") from None',
    "        return bridge",
)
DISABLED_GUARD = (
    "        if type(model_calls_disabled) is not bool:",
    '            raise ValueError("model_calls_disabled 必须是布尔值")',
    '        if model_calls_disabled and config.provider != "none":',
    '            raise ValueError("model_calls_disabled 只能用于 none 默认线路")',
)
DISABLED_CODE = (
    "        if model_calls_disabled:",
    '            self.report["model"]["code"] = _MODEL_CALLS_DISABLED_CODE',
)
NOTIFY_IDLE = (
    "def _notify_idle(self) -> None:",
    "        if self.on_idle is not None:",
    "            self.on_idle()",
)
CLOSE_DEADLINE = (
    "        deadline = time.monotonic() + 2 if deadline is None else deadline",
)
START_FAILED_START = (
    "            result = self.read()",
    "        if failed_start:",
    "            self._notify_idle()",
    "        return result",
)
LOGIN_FAILED_START = (
    "        result = self.read_login()",
    "        # The application's idle callback acquires other lifecycle locks.",
    "        if failed_start:",
    "            self._notify_idle()",
    "        return result",
)
MODEL_REJECTED = (
    "        except ModelRequestRejected as exc:",
    "            with self.lock:",
    "                active = self.active.get(key)",
    "                if active is not None and active[1] is cancel and not cancel.is_set():",
    '                    self._set(key, state="failed", code=exc.code, summary=str(exc),',
    "                              requestRejected=True, checkedAt=_now())",
)
MODEL_SUCCESS = (
    '                        success = message.stop_reason == "stop" and bool(message.text().strip()) and not message.tool_calls()',
    '                outcome = {"state": "ready", "summary": "真实模型已完成一次小请求"} if success else {',
    '                    "state": "failed", "code": "MODEL_CHECK_FAILED", "summary": "模型未完成有效响应，请核对供应商、模型与网络"}',
)
MODEL_ORDER = (
    "                    request = self.request_preparer(request)",
    "                budget = self.request_budget(request) if self.request_budget is not None else {}",
    "                request = check_model_request(self.lifecycle_hooks, config, request, budget,",
    '                    purpose="connection_check", request_index=0, cancel_event=cancel)',
)
PROBES = (
    ("is_idle", IS_IDLE),
    ("read", READ),
    ("_error", ERROR),
    ("_new_bridge", NEW_BRIDGE),
    ("_notify_idle", NOTIFY_IDLE),
    ("start", START_FAILED_START),
    ("complete_login", LOGIN_FAILED_START),
    ("_run", MODEL_REJECTED),
    ("_run", MODEL_SUCCESS),
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
        if isinstance(node, ast.ClassDef) and node.name == "ConnectionChecks":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"connections.py 缺少 ConnectionChecks.{name}")


def _init_body(tree: ast.Module, source: str) -> str:
    return _method(tree, source, "__init__")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"连接行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_call(call, label: str) -> int:
    try:
        call()
    except BaseException:
        return 1
    raise ValueError(f"连接行为变化 {label}：期望抛出但正常返回")


def _expect_message(call, message: str, label: str) -> int:
    try:
        call()
    except Exception as error:
        if message not in str(error):
            raise ValueError(f"连接行为变化 {label}：期望包含 {message!r}，实际 {str(error)!r}")
        return 1
    raise ValueError(f"连接行为变化 {label}：期望抛出但正常返回")


def _expect_rpc(call, code: int, data_code: str, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if error.code != code or (error.data or {}).get("code") != data_code:
            raise ValueError(f"连接行为变化 {label}：期望 {code}/{data_code}，实际 {error.code}/{error.data!r}")
        return 1
    raise ValueError(f"连接行为变化 {label}：期望 RpcError")


def _settle(checks: ConnectionChecks, label: str) -> None:
    deadline = time.monotonic() + 5
    while not checks.is_idle() and time.monotonic() < deadline:
        time.sleep(0.005)
    if not checks.is_idle():
        raise ValueError(f"连接行为变化 {label}：后台检查未在超时内结束")


class FakeResult:
    def __init__(self, ok: bool = True, data: object = None, error: dict | None = None) -> None:
        self.ok, self.data, self.error = ok, data, error


class FakeBridge:
    source = "fake-boss"

    def __init__(self, status: dict | None = None, available: bool = True) -> None:
        self.status = {"logged_in": True, "auth_state": "complete"} if status is None else status
        self.available_value = available
        self.calls: list[tuple[str, tuple]] = []
        self.cancel_event: threading.Event | None = None

    def available(self) -> bool:
        return self.available_value

    def call(self, name: str, *args, **kwargs) -> FakeResult:
        self.calls.append((name, args))
        if name == "login":
            return FakeResult()
        if name == "status":
            return FakeResult(data=dict(self.status))
        return FakeResult()


class FakeProvider:
    id = "fake"

    def __init__(self, events: tuple[StreamEvent, ...] = ()) -> None:
        self.events = events
        self.requests: list[object] = []
        self.aborted = False

    def stream(self, request):
        self.requests.append(request)
        for event in self.events:
            yield event

    def request_abort(self) -> None:
        self.aborted = True


class BlockingProvider(FakeProvider):
    def __init__(self, gate: threading.Event) -> None:
        super().__init__()
        self.gate = gate

    def stream(self, request):
        self.requests.append(request)
        self.gate.wait(5)
        yield StreamEvent(type="done", message=AssistantMessage(blocks=(TextBlock(text="OK"),)))


def _ok_message() -> AssistantMessage:
    return AssistantMessage(blocks=(TextBlock(text="OK"),))


def _check_structures() -> int:
    source = _read(MODULE)
    tree = _tree(MODULE)
    checked = 0
    checked += _ordered(("PUBLIC_CHECK_CODES = PAUSE_CODES | {", '"CONNECTION_FAILED",'),
                        source, "公开检查码白名单")
    for name, fragments in PROBES:
        body = _method(tree, source, name)
        for fragment in fragments:
            if fragment not in body:
                raise ValueError(f"ConnectionChecks.{name} 缺少：{fragment}")
            checked += 1
    for fragment in DISABLED_GUARD + DISABLED_CODE:
        if fragment not in _init_body(tree, source):
            raise ValueError(f"ConnectionChecks.__init__ 缺少：{fragment}")
        checked += 1
    close = _method(tree, source, "close")
    for fragment in CLOSE_DEADLINE:
        if fragment not in close:
            raise ValueError(f"ConnectionChecks.close 缺少：{fragment}")
        checked += 1
    checked += _ordered(MODEL_ORDER, _method(tree, source, "_run"), "模型检查准备顺序")
    return checked


def _disabled_report_checks() -> int:
    checked = 0
    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    checked += _expect_value(checks.is_idle(), True, "禁用实例初始空闲")
    report = checks.read()
    for target in ("cli", "platform"):
        checked += _expect_value(
            (report[target]["state"], report[target]["code"], report[target]["summary"]),
            ("disabled", "NOT_SUPPORTED", "当前工具组合未启用平台连接与登录"), f"禁用 {target} 报告")
    checked += _expect_value(checks.read_login(),
                             {"state": "disabled", "code": "NOT_SUPPORTED", "summary": "当前工具组合未启用平台连接与登录"},
                             "禁用登录报告")
    checked += _expect_value(checks.start("local")["cli"]["state"], "disabled", "禁用实例拒绝本地检查")
    checked += _expect_value(dict(checks.active), {}, "禁用实例不启动活动检查")
    mutable = checks.read()
    mutable["model"]["summary"] = "篡改"
    checked += _expect_value(checks.read()["model"]["summary"], "默认模型线路不调用模型", "报告深拷贝隔离")
    checks.report["cli"] = {"state": "ready"}
    checked += _expect_value(checks.read()["cli"]["state"], "disabled", "禁用时强制覆盖活动报告")
    checked += _expect_value(checks.report["model"]["summary"], "默认模型线路不调用模型", "禁用模型中性文案")
    checked += _expect_call(lambda: checks.start("bogus"),
                            "非法检查目标")
    checked += _expect_message(lambda: checks.start(7), "target 必须是 local、model 或 platform",
                              "非法目标类型")
    return checked


def _model_disable_checks() -> int:
    checked = 0
    for value in (1, "yes", None):
        checked += _expect_message(
            lambda value=value: ConnectionChecks(ModelConfig(provider="none"), model_calls_disabled=value),
            "model_calls_disabled 必须是布尔值", f"非布尔开关 {value!r}")
    checked += _expect_message(
        lambda: ConnectionChecks(ModelConfig(provider="openai"), model_calls_disabled=True),
        "model_calls_disabled 只能用于 none 默认线路", "显式禁用限于 none 线路")
    without_bridge = ConnectionChecks(ModelConfig(provider="none"), model_calls_disabled=True, bridge_factory=None)
    checked += _expect_value((without_bridge.report["model"]["code"], without_bridge.report["model"]["summary"]),
                             ("MODEL_DISABLED", "已显式禁用模型调用，需要模型时改用具体 provider 重新启动"),
                             "显式禁用无平台文案")
    with_bridge = ConnectionChecks(ModelConfig(provider="none"), model_calls_disabled=True,
                                   bridge_factory=FakeBridge)
    checked += _expect_value(
        (with_bridge.report["model"]["code"], with_bridge.report["model"]["summary"]),
        ("MODEL_DISABLED", "已显式禁用模型调用，需要模型时改用具体 provider 重新启动；招聘 CLI 仍可运行并可能访问平台"),
        "显式禁用保留平台能力文案")
    policy = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None, browser_source_policy="chromium")
    checked += _expect_value((policy.read()["cli"].get("browserSourcePolicy"),
                              policy.read()["platform"].get("browserSourcePolicy")),
                             ("chromium", "chromium"), "浏览器来源策略进入报告")
    plain = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    checked += _expect_value("browserSourcePolicy" in plain.read()["cli"], False, "未设置时不伪造来源策略")
    return checked


def _bridge_identity_checks() -> int:
    checked = 0

    class Unweak:
        __slots__ = ()

        def available(self) -> bool:
            return True

        def call(self, *args, **kwargs) -> FakeResult:
            return FakeResult()

    closed: list[object] = []

    class RecordingLifecycle(BridgeLifecycle):
        def close(self, bridge=None):
            closed.append(bridge)
            return super().close(bridge)

    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=Unweak,
                              bridge_lifecycle=RecordingLifecycle())
    checked += _expect_message(checks.begin_login, "工具桥实例必须支持独立身份跟踪", "工具桥身份校验")
    checked += _expect_value(len(closed), 1, "身份校验失败仍释放工具桥")
    return checked


def _error_checks() -> int:
    checked = 0

    def result(error, ok: bool = False) -> FakeResult:
        return FakeResult(ok=ok, error=error)

    blocked = ConnectionChecks._error(result({"code": "AUTH_REQUIRED"}))
    checked += _expect_value((blocked["state"], blocked["code"]), ("blocked", "AUTH_REQUIRED"), "暂停码阻断")
    checked += _expect_value(blocked["summary"],
                             "平台要求恢复登录或处理验证；已停止访问，请在官方页面处理后手动重新检查",
                             "暂停码恢复文案")
    contract = ConnectionChecks._error(result({"code": "CLI_CONTRACT_ERROR"}))
    checked += _expect_value((contract["state"], contract["code"]), ("blocked", "CLI_CONTRACT_ERROR"),
                             "契约错误阻断并保留公开码")
    failed = ConnectionChecks._error(result({"code": "CLI_ERROR"}))
    checked += _expect_value((failed["state"], failed["code"], failed["summary"]),
                             ("failed", "CLI_ERROR", "检查失败，请核对本机配置或网络后重试"),
                             "公开码保留")
    for error in ({"code": "LOGIN_REQUIRED"}, {"code": 5}, {"code": ""}, None, {}):
        checked += _expect_value(ConnectionChecks._error(result(error))["code"], "CONNECTION_FAILED",
                                 f"未公开码归一 {error!r}")
    leak = ConnectionChecks._error(result({"code": "AUTH_REQUIRED", "message": "账号 13800000000 异常",
                                           "hint": "联系客服"}))
    checked += _expect_value("13800000000" in repr(leak) or "联系客服" in repr(leak), False, "不泄露上游消息")
    return checked


def _login_checks() -> int:
    checked = 0
    disabled = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    checked += _expect_rpc(disabled.begin_login, -32006, "NOT_SUPPORTED", "禁用实例拒绝登录")
    unavailable = ConnectionChecks(ModelConfig(provider="none"),
                                   bridge_factory=lambda: FakeBridge(available=False))
    checked += _expect_value(unavailable.begin_login(),
                             {"state": "failed", "code": "CLI_UNAVAILABLE", "summary": "上游 CLI 不可用，请先检查本机连接"},
                             "上游不可用拒绝登录")
    bridge = FakeBridge()
    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=lambda: bridge)
    started = checks.begin_login()
    first_id = started["id"]
    checked += _expect_value((started["state"], len(first_id)), ("waiting", 32), "登录等待标识")
    checked += _expect_value(checks.begin_login()["id"], first_id, "等待中重复登录复用标识")
    checked += _expect_value(checks.cancel_login("unknown")["state"], "waiting", "未知标识不取消登录")
    cancelled = checks.cancel_login(first_id)
    checked += _expect_value((cancelled["state"], cancelled["summary"]),
                             ("cancelled", "已取消扫码登录"), "取消扫码登录")

    busy = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=FakeBridge)
    busy.active["cli"] = (threading.Thread(), threading.Event())
    checked += _expect_value(busy.begin_login(),
                             {"state": "failed", "code": "CHECK_BUSY", "summary": "请等待当前平台检查结束后再登录"},
                             "检查中拒绝登录")
    busy.active.pop("cli", None)

    formats = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=FakeBridge)
    login_id = formats.begin_login()["id"]
    invalid = (
        ("非对象 Cookie", [], "ua"),
        ("空 Cookie", {}, "ua"),
        ("超量 Cookie", {f"k{index}": "v" for index in range(201)}, "ua"),
        ("非法 Cookie 名", {"bad name": "v", "wt2": "x"}, "ua"),
        ("Cookie 值含分号", {"wt2": "a;b"}, "ua"),
        ("Cookie 值含控制符", {"wt2": "a\x01b"}, "ua"),
        ("缺少 wt2", {"other": "x"}, "ua"),
        ("User-Agent 超长", {"wt2": "x"}, "u" * 513),
        ("User-Agent 含控制符", {"wt2": "x"}, "u\x01"),
    )
    for label, cookies, agent in invalid:
        checked += _expect_message(
            lambda cookies=cookies, agent=agent: formats.complete_login(
                {"id": login_id, "cookies": cookies, "userAgent": agent}),
            "官方登录态格式无效", label)
    checked += _expect_message(
        lambda: formats.complete_login({"id": login_id, "cookies": {"wt2": "x" * (70 * 1024)}, "userAgent": "ua"}),
        "官方登录态超过大小限制", "登录态超过 64KB")
    checked += _expect_message(
        lambda: formats.complete_login({"id": "wrong", "cookies": {"wt2": "x"}, "userAgent": "ua"}),
        "扫码登录已结束，请重新打开官方登录窗口", "过期的登录标识")
    return checked


def _login_save_checks() -> int:
    checked = 0
    idle: list[int] = []
    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=FakeBridge)
    checks.on_idle = lambda: idle.append(1)
    login_id = checks.begin_login()["id"]
    saving = checks.complete_login({"id": login_id, "cookies": {"wt2": "x"}, "userAgent": "ua"})
    checked += _expect_value((saving["state"], saving["summary"]),
                             ("saving", "已检测到扫码登录，正在通过上游验证并保存…"), "登录保存开始")
    _settle(checks, "登录保存")
    checked += _expect_value((checks.report["platform"]["state"], checks.report["platform"]["authState"],
                              checks.report["platform"]["summary"]),
                             ("ready", "complete", "官方账号验证通过，登录态已保存；可用功能取决于账号身份"),
                             "登录保存成功")
    checked += _expect_value(checks.login["state"], "succeeded", "登录状态成功")
    checked += _expect_value(len(idle) >= 1, True, "登录结束通知空闲回收")

    readback = ConnectionChecks(ModelConfig(provider="none"),
                                bridge_factory=lambda: FakeBridge({"logged_in": False, "auth_state": "complete"}))
    login_id = readback.begin_login()["id"]
    readback.complete_login({"id": login_id, "cookies": {"wt2": "x"}, "userAgent": "ua"})
    _settle(readback, "登录读回失败")
    checked += _expect_value((readback.report["platform"]["state"], readback.report["platform"]["code"]),
                             ("failed", "LOGIN_READBACK_FAILED"), "登录读回失败")
    checked += _expect_value(readback.login["state"], "failed", "登录读回失败状态")

    partial = ConnectionChecks(ModelConfig(provider="none"),
                               bridge_factory=lambda: FakeBridge({"logged_in": True, "auth_state": "partial"}))
    login_id = partial.begin_login()["id"]
    partial.complete_login({"id": login_id, "cookies": {"wt2": "x"}, "userAgent": "ua"})
    _settle(partial, "登录态不完整")
    checked += _expect_value((partial.report["platform"]["state"], partial.report["platform"]["code"],
                              partial.report["platform"]["authState"]),
                             ("unchecked", "LOGIN_INCOMPLETE", "partial"), "登录态不完整")
    checked += _expect_value(partial.login["state"], "failed", "登录态不完整状态")

    gate = threading.Event()

    class BlockingBridge(FakeBridge):
        def call(self, name, *args, **kwargs):
            gate.wait(5)
            return super().call(name, *args, **kwargs)

    stopping = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=BlockingBridge)
    login_id = stopping.begin_login()["id"]
    stopping.complete_login({"id": login_id, "cookies": {"wt2": "x"}, "userAgent": "ua"})
    stopped = stopping.cancel_login(login_id)
    checked += _expect_value((stopped["state"], stopped["summary"]),
                             ("cancelled", "保存已停止，登录态可能已更新，请手动检查"), "保存中取消登录")
    checked += _expect_value((stopping.report["platform"]["state"], stopping.report["platform"]["summary"]),
                             ("unchecked", "登录保存已取消，请手动核对登录态"), "保存中取消平台报告")
    gate.set()
    _settle(stopping, "保存取消")
    checked += _expect_value((stopping.login["state"], stopping.report["platform"]["state"]),
                             ("cancelled", "unchecked"), "取消后不覆盖结果")
    return checked


def _platform_checks() -> int:
    checked = 0

    def run(status: dict, available: bool = True) -> tuple[ConnectionChecks, FakeBridge]:
        bridge = FakeBridge(status, available=available)
        checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=lambda: bridge)
        checks.start("platform")
        _settle(checks, f"平台检查 {status!r}")
        return checks, bridge

    risk, _ = run({"logged_in": True, "auth_state": "complete", "cdp_risk_lock": {"locked": True}})
    checked += _expect_value((risk.report["platform"]["state"], risk.report["platform"]["code"],
                              risk.report["platform"]["authState"]),
                             ("blocked", "ENVIRONMENT_RISK_LOCKED", "complete"), "平台风险锁")
    group, _ = run({"logged_in": True, "auth_state": "complete", "cdp_risk_lock": {"group_locked": True}})
    checked += _expect_value(group.report["platform"]["code"], "ENVIRONMENT_RISK_LOCKED", "平台分组风险锁")
    broken, _ = run({"logged_in": True, "auth_state": "broken"})
    checked += _expect_value((broken.report["platform"]["state"], broken.report["platform"]["code"],
                              broken.report["platform"]["authState"]),
                             ("blocked", "AUTH_REQUIRED", "broken"), "登录态损坏阻断")
    anonymous, _ = run({"logged_in": False, "auth_state": "complete"})
    checked += _expect_value((anonymous.report["platform"]["state"], anonymous.report["platform"]["code"]),
                             ("blocked", "AUTH_REQUIRED"), "未登录阻断")
    ready, bridge = run({"logged_in": True, "auth_state": "complete"})
    checked += _expect_value((ready.report["platform"]["state"], ready.report["platform"]["summary"]),
                             ("ready", "已完成一次平台只读在线验证"), "平台在线检查成功")
    checked += _expect_value([name for name, _ in bridge.calls], ["status", "status"], "平台检查先本地后在线")
    checked += _expect_value("--live" in bridge.calls[1][1], True, "在线验证使用 live 状态")
    unchecked, _ = run({"logged_in": True, "auth_state": "complete"}, available=False)
    checked += _expect_value((unchecked.report["platform"]["state"], unchecked.report["platform"]["code"]),
                             ("failed", "CLI_UNAVAILABLE"), "平台桥不可用")
    return checked


def _cli_checks() -> int:
    checked = 0
    bridge = FakeBridge()
    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=lambda: bridge)
    checks.start("local")
    _settle(checks, "本地检查")
    checked += _expect_value((checks.report["cli"]["state"], checks.report["cli"]["summary"],
                              checks.report["cli"]["binarySource"]),
                             ("ready", "CLI 可执行，v1 JSON 契约有效", "fake-boss"), "本地契约检查")
    checked += _expect_value([name for name, _ in bridge.calls], ["schema", "status"], "本地检查同时读取登录态")
    checked += _expect_value(checks.report["platform"]["authState"], "complete", "本地检查记录登录态")

    risk_bridge = FakeBridge({"logged_in": True, "auth_state": "complete", "cdp_risk_lock": {"locked": True}})
    risk = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=lambda: risk_bridge)
    risk.start("local")
    _settle(risk, "本地风险检查")
    checked += _expect_value((risk.report["cli"]["state"], risk.report["platform"]["state"]),
                             ("ready", "blocked"), "本地风险锁不推翻 CLI 结果")

    class FailingBridge(FakeBridge):
        def call(self, name, *args, **kwargs):
            self.calls.append((name, args))
            if name == "schema":
                return FakeResult(ok=False, error={"code": "CLI_CONTRACT_ERROR", "message": "内部细节"})
            return super().call(name, *args, **kwargs)

    failing = FailingBridge()
    failed = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=lambda: failing)
    failed.start("local")
    _settle(failed, "本地契约失败")
    checked += _expect_value((failed.report["cli"]["state"], failed.report["cli"]["code"],
                              "内部细节" in repr(failed.read())),
                             ("blocked", "CLI_CONTRACT_ERROR", False), "本地契约失败与脱敏")
    return checked


def _close_checks() -> int:
    checked = 0
    checks = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    login_cancel = threading.Event()
    checks.login_cancel = login_cancel
    cancel = threading.Event()
    checks.active["cli"] = (threading.Thread(), cancel)
    checks.prepare_close()
    checked += _expect_value((checks.closed, cancel.is_set(), login_cancel.is_set()),
                             (True, True, True), "关闭准备取消全部活动")
    checks.active.pop("cli", None)

    model = ConnectionChecks(ModelConfig(provider="openai", model="m1"),
                             provider_factory=lambda config: BlockingProvider(threading.Event()))
    model.start("model")
    model.prepare_close()
    checked += _expect_value((model.report["model"]["state"], model.report["model"]["code"],
                              model.report["model"]["summary"]),
                             ("failed", "CANCELLED", "模型检查已停止"), "关闭准备取消模型检查")
    model.active.clear()

    idle = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    idle.active["cli"] = (threading.Thread(), threading.Event())
    checked += _expect_value(idle.is_idle(), False, "活动记录使实例非空闲")
    idle.active.pop("cli")
    checked += _expect_value(idle.is_idle(), True, "活动清空后恢复空闲")
    idle.prepare_close()
    checked += _expect_value(idle.start("platform")["platform"]["state"], "disabled", "关闭后不再启动检查")

    worker_cancel = threading.Event()
    slow = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    worker = threading.Thread(target=time.sleep, args=(2,), daemon=True)
    worker.start()
    slow.active["cli"] = (worker, worker_cancel)
    started = time.monotonic()
    slow.close(deadline=time.monotonic() + 0.05)
    elapsed = time.monotonic() - started
    checked += _expect_value(elapsed >= 0.01 and elapsed < 1.0, True, "关闭按截止时间返回")
    checked += _expect_value((worker_cancel.is_set(), slow.closed), (True, True), "关闭取消非协作检查")
    checked += _expect_value("cli" in slow.active, True, "非协作检查保留所有权")
    slow.active.pop("cli", None)
    worker.join()

    empty = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    empty.close()
    checked += _expect_value(empty.closed, True, "无活动时关闭立即完成")
    return checked


def _model_checks() -> int:
    checked = 0
    disabled = ConnectionChecks(ModelConfig(provider="none"), bridge_factory=None)
    checked += _expect_value(disabled.start("model")["model"]["state"], "disabled", "禁用线路不启动模型检查")
    checked += _expect_value(dict(disabled.active), {}, "禁用线路不产生活动记录")

    def run(provider, **kwargs) -> ConnectionChecks:
        checks = ConnectionChecks(ModelConfig(provider="openai", model="m1"),
                                  provider_factory=lambda config: provider, **kwargs)
        checks.start("model")
        _settle(checks, "模型检查")
        return checks

    ready = run(FakeProvider((StreamEvent(type="done", message=_ok_message()),)))
    checked += _expect_value((ready.report["model"]["state"], ready.report["model"]["summary"]),
                             ("ready", "真实模型已完成一次小请求"), "模型检查成功")
    empty = run(FakeProvider((StreamEvent(type="done", message=AssistantMessage(blocks=(TextBlock(text="  "),))),)))
    checked += _expect_value((empty.report["model"]["state"], empty.report["model"]["code"]),
                             ("failed", "MODEL_CHECK_FAILED"), "空响应不是有效回答")
    tool = run(FakeProvider((StreamEvent(type="done", message=AssistantMessage(
        blocks=(ToolCallBlock(id="t1", name="boss_search"),))),)))
    checked += _expect_value(tool.report["model"]["code"], "MODEL_CHECK_FAILED", "工具调用不是有效回答")
    absent = run(None)
    checked += _expect_value((absent.report["model"]["state"], absent.report["model"]["code"]),
                             ("failed", "CHECK_FAILED"), "缺少 provider")
    errored = run(FakeProvider((StreamEvent(type="error", reason="network"),)))
    checked += _expect_value(errored.report["model"]["code"], "MODEL_CHECK_FAILED", "错误事件中断检查")

    class RejectingProvider(FakeProvider):
        def stream(self, request):
            self.requests.append(request)
            raise ModelRequestRejected("MODEL_REQUEST_BUDGET", "请求预算已用尽", {"purpose": "connection_check"})
            yield

    rejected = run(RejectingProvider())
    checked += _expect_value((rejected.report["model"]["state"], rejected.report["model"]["code"],
                              rejected.report["model"]["summary"], rejected.report["model"]["requestRejected"]),
                             ("failed", "MODEL_REQUEST_BUDGET", "请求预算已用尽", True), "模型请求被拒绝")

    order: list[str] = []
    received: list[object] = []
    provider = FakeProvider((StreamEvent(type="done", message=_ok_message()),))
    prepared = ConnectionChecks(
        ModelConfig(provider="openai", model="m1"),
        provider_factory=lambda config: received.append(config) or provider,
        request_preparer=lambda request: order.append("preparer") or request,
        request_budget=lambda request: order.append("budget") or {"max": 1})
    prepared.start("model")
    _settle(prepared, "模型准备顺序")
    checked += _expect_value(order, ["preparer", "budget"], "模型检查准备顺序")
    checked += _expect_value((received[0].max_tokens, received[0].effort), (512, "low"), "模型检查请求约束")
    request = provider.requests[0]
    checked += _expect_value((request.model, request.max_tokens, request.effort,
                              request.system, len(request.messages)),
                             ("m1", 512, "low", "Connection check. Reply OK only.", 1), "模型检查请求内容")

    gate = threading.Event()
    slow_provider = BlockingProvider(gate)
    busy = ConnectionChecks(ModelConfig(provider="openai", model="m1"),
                            provider_factory=lambda config: slow_provider)
    busy.start("model")
    active = busy.active.get("model")
    repeat = busy.start("model")
    checked += _expect_value((repeat["model"]["state"], busy.active.get("model") is active),
                             ("checking", True), "检查中重复启动被忽略")
    gate.set()
    _settle(busy, "检查中重复启动")
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _disabled_report_checks()
    checked += _model_disable_checks()
    checked += _bridge_identity_checks()
    checked += _error_checks()
    checked += _login_checks()
    checked += _login_save_checks()
    checked += _platform_checks()
    checked += _cli_checks()
    checked += _close_checks()
    checked += _model_checks()
    return checked


def check_connections() -> tuple[int, int]:
    return _check_structures(), _behavior_checks()


def main() -> int:
    try:
        structures, behaviors = check_connections()
    except ValueError as error:
        print(f"连接检查边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"连接检查边界一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
