#!/usr/bin/env python3
"""核对生命周期 hook 的超时、上下文冻结与策略拒绝边界。

hooks.py 是宿主注入策略的唯一入口：事件观察有界且脱敏，策略检查收到完整
JSON 快照并 fail closed，超时与关闭期限不会让迟到结果改写回合。检查固定源码
结构，并在临时合成数据上执行上下文复制、边界与拒绝码场景。
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
import threading
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/hooks.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.hooks import (  # noqa: E402
    MAX_POLICY_CONTEXT_BYTES,
    MAX_POLICY_CONTEXT_DEPTH,
    MAX_POLICY_CONTEXT_NODES,
    HookCancellationSignal,
    LifecycleHooks,
    _signal_mode,
    freeze_context,
    freeze_policy_context,
)

CONSTANT_FRAGMENTS = (
    "MAX_HOOK_TIMEOUT_SECONDS = 30.0\n",
    "DEFAULT_HOOK_TIMEOUT_SECONDS = 0.25\n",
    "MAX_PENDING_EVENTS = 256\n",
    "MAX_ACTIVE_HOOK_CALLBACKS = 16\n",
    "HOOK_BUSY_DIAGNOSTIC_INTERVAL_SECONDS = 1.0\n",
    "MAX_CONTEXT_STRING = 16_384\n",
    "MAX_CONTEXT_KEYS = 64\n",
    "MAX_CONTEXT_ITEMS = 128\n",
    "MAX_CONTEXT_DEPTH = 6\n",
    "MAX_POLICY_CONTEXT_BYTES = 1_052_672\n",
    "MAX_POLICY_CONTEXT_NODES = 32_784\n",
    "MAX_POLICY_CONTEXT_DEPTH = 66\n",
    "MAX_CONTEXT_UNITS = 512\n",
    # 内部哨兵必须各自独立：混淆会让拒绝被当成允许。
    "_HOOK_FAILED = object()",
    "_HOOK_BUSY = object()",
    "_HOOK_CONTEXT_TOO_LARGE = object()",
    "_HOOK_CONTEXT_INVALID = object()",
    "_HOOK_CANCELLED = object()",
    "_HOOK_CLOSED = object()",
)
DECISION_FRAGMENTS = (
    "if type(self.allow) is not bool:",
    'raise ValueError("HookDecision.allow 必须是布尔值")',
    're.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.code) is None',
    'raise ValueError("HookDecision.code 无效")',
    'raise ValueError("HookDecision.message 无效")',
    "if len(values) > MAX_CONTEXT_UNITS or any(type(item) is not int or item < 0 for item in values):",
    'object.__setattr__(self, "drop_units", tuple(sorted(set(values))))',
)
SAFE_FRAGMENTS = (
    "if depth >= MAX_CONTEXT_DEPTH:",
    'return "<omitted:depth>"',
    "return redact_secrets(value[:MAX_CONTEXT_STRING])",
    "if isinstance(value, float) and not math.isfinite(value):",
    'return "<omitted:number>"',
    "if index >= MAX_CONTEXT_KEYS:",
    'result["<omitted:keys>"] = f"{len(value) - MAX_CONTEXT_KEYS} more"',
    "result[key[:128]] = _safe_value(item, depth=depth + 1)",
    "for item in value[:MAX_CONTEXT_ITEMS]",
    'result.append(f"<omitted:items:{len(value) - MAX_CONTEXT_ITEMS}>")',
    "return redact_secrets(str(value)[:MAX_CONTEXT_STRING])",
)
FREEZE_FRAGMENTS = (
    "return MappingProxyType({key: freeze(value) for key, value in item.items()})",
    "return tuple(freeze(value) for value in item)",
    # 观察上下文先做有界、脱敏副本，再冻结为只读视图。
    "return freeze(_safe_value(dict(value)))",
)
POLICY_FRAGMENTS = (
    "if size > MAX_POLICY_CONTEXT_BYTES:",
    'raise _PolicyContextError("HOOK_CONTEXT_TOO_LARGE")',
    'raise _PolicyContextError("HOOK_CONTEXT_INVALID")',
    "if 0xD800 <= codepoint <= 0xDFFF:",
    "if depth > MAX_POLICY_CONTEXT_DEPTH or nodes > MAX_POLICY_CONTEXT_NODES:",
    "if not math.isfinite(item):",
    # 环引用必须拒绝，否则完整复制会无限递归。
    "if marker in active:",
    "active.add(marker)",
    "active.remove(marker)",
    "if not isinstance(value, Mapping):",
)
LIFECYCLE_FRAGMENTS = (
    "if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= MAX_HOOK_TIMEOUT_SECONDS:",
    'raise ValueError("hook timeout 必须大于 0 且不超过 30 秒")',
    'raise ValueError("lifecycle_hooks 必须是可迭代对象") from None',
    'raise ValueError("expose_tool_results 必须是布尔值")',
    'raise ValueError("生命周期 hook 至少提供一种受支持的回调")',
    "self._event_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue(MAX_PENDING_EVENTS)",
    '"on_event", "before_tool_call", "before_request", "transform_context",',
    '"after_tool_call", "close"',
)
EVENT_FRAGMENTS = (
    # 事件观察只投影白名单字段，正文、思考与工具参数不进入 hook 上下文。
    'visible = {"threadId", "turnId", "itemId", "queueId", "jobId", "status", "code",',
    '"reason", "origin", "kind", "toolName", "model", "provider", "effort",',
    '"state", "aborted", "active", "eventCursor", "eventId", "recoveryAction",',
    '"outputObserved", "requestRejected"}',
    "projected = {key: source[key] for key in visible if key in source}",
    'return {"phase": "event", "event": method, "params": _safe_value(projected)}',
    "except queue.Full:",
    "self._dropped_events += 1",
)
INVOKE_FRAGMENTS = (
    'policy = method in {"before_tool_call", "before_request", "transform_context"}',
    # 取消先于关闭与容量判定：已取消的回合不再启动策略回调。
    "if policy and cancel_event is not None and cancel_event.is_set():",
    "return _HOOK_CANCELLED",
    "if policy and (self._closing or self._closed):",
    "return _HOOK_CLOSED",
    "callback_context = (freeze_policy_context(context or {}) if method in {",
    '"before_tool_call", "before_request", "transform_context", "after_tool_call"}',
    'else freeze_context(context or {}) if method == "on_event" else None)',
    "if self._active >= MAX_ACTIVE_HOOK_CALLBACKS:",
    'self._busy_events += 1',
    '"HOOK_BUSY", "生命周期 hook 在途回调已达到内核上限"',
    '"HOOK_TIMEOUT", "生命周期 hook 超时", timed_out=True',
    "finished.wait(min(0.025, remaining))",
    "return result[0] if result else None",
)
SIGNAL_FRAGMENTS = (
    # 只有可解析签名的回调才可能收到信令；无签名时按旧式单参数调用。
    "def _signal_mode(callback: Callable[..., Any]) -> str | None:",
    "parameters = inspect.signature(callback).parameters",
    "except (TypeError, ValueError):\n        return None",
    'signal = parameters.get("signal")',
    'if signal.kind == inspect.Parameter.POSITIONAL_ONLY:\n            return "positional"',
    'if signal.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):\n            return "keyword"',
    'return "keyword" if any(item.kind == inspect.Parameter.VAR_KEYWORD for item in parameters.values()) else None',
)
DISPATCH_FRAGMENTS = (
    # 仅在策略 / 观察阶段且确有信令对象时分类；close 与事件观察保持单参数。
    'signal_mode = (_signal_mode(callback)\n                       if method in {"before_tool_call", "before_request", "transform_context", "after_tool_call"}\n                       and signal is not None else None)',
    'elif signal_mode == "positional":\n                    result.append(callback(callback_context, signal))',
    'elif signal_mode == "keyword":\n                    result.append(callback(callback_context, signal=signal))',
    "result.append(callback(callback_context))",
)
POLICY_RESULT_FRAGMENTS = (
    'return HookDecision(False, "HOOK_CLOSED", "内核策略 hook 正在关闭或已关闭；工具调用已暂停")',
    'return HookDecision(False, "HOOK_CONTEXT_TOO_LARGE", "策略输入超过内核上限；为保证策略检查完整，工具调用已暂停")',
    'return HookDecision(False, "HOOK_CONTEXT_INVALID", "策略输入不是受支持的 JSON；为保证策略检查完整，工具调用已暂停")',
    'return HookDecision(False, "HOOK_BUSY", "内核策略 hook 已达到在途回调上限；工具调用已暂停")',
    'return HookDecision(False, "HOOK_ERROR", "内核策略 hook 未能完成；为避免执行未核对的工具，当前回合已暂停")',
    'return HookDecision(False, "HOOK_RESULT_INVALID", "内核策略 hook 返回了无效结果；当前回合已暂停")',
    "if not result.allow:",
    "return result",
)
REQUEST_RESULT_FRAGMENTS = (
    'return HookDecision(False, "HOOK_CLOSED", "内核策略 hook 正在关闭或已关闭；模型请求已拒绝")',
    'return HookDecision(False, "HOOK_CONTEXT_TOO_LARGE", "策略输入超过内核上限；模型请求已拒绝")',
    'return HookDecision(False, "HOOK_BUSY", "内核策略 hook 已达到在途回调上限；模型请求已拒绝")',
    'return HookDecision(False, "HOOK_ERROR", "内核策略 hook 未能完成；模型请求已拒绝")',
    'return HookDecision(False, "HOOK_RESULT_INVALID", "内核策略 hook 返回了无效结果；模型请求已拒绝")',
)
TRANSFORM_FRAGMENTS = (
    "or any(index >= unit_count - 1 for index in result.drop_units)):",
    '"transform_context 必须返回 ContextTransform 或 None，且不能省略当前输入单元"',
    "dropped.update(result.drop_units)",
    "return tuple(sorted(dropped))",
)
AFTER_FRAGMENTS = (
    "if self.expose_tool_results:",
    'payload["result"] = dict(result)',
    "internal_results = (_HOOK_CANCELLED, _HOOK_FAILED, _HOOK_BUSY, _HOOK_CONTEXT_TOO_LARGE,",
    "if returned is not None and not any(returned is value for value in internal_results):",
    '"after_tool_call 仅用于观察，不能返回改写结果"',
)
CLOSE_FRAGMENTS = (
    "self._closing = True",
    "while (self._active or not self._event_queue.empty()) and time.monotonic() < end:",
    'self._invoke(hook, "close", None, event="kernel/shutdown", deadline=end)',
    "self._closed = True",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "队列容量为 256，拥塞会记录 `kernel/hookError`"),
    (TECHNICAL_REFERENCE, "合计最多 16 个在途 worker"),
    (TECHNICAL_REFERENCE, "总量上限为 1,052,672 字节，另受 32,784 个节点、深度 66 限制"),
    (TECHNICAL_REFERENCE, "默认限时 250ms，宿主可传入 `hook_timeout`（最大 30 秒）"),
    (TECHNICAL_REFERENCE, "取消优先于拒绝"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"生命周期 hook 行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_rejected(value, code: str, label: str) -> int:
    try:
        freeze_policy_context(value)
    except ValueError as error:
        actual = getattr(error, "code", None)
        if actual != code:
            raise ValueError(f"生命周期 hook 拒绝码变化 {label}：期望 {code!r}，实际 {actual!r}") from None
    else:
        raise ValueError(f"生命周期 hook 应拒绝 {label}")
    return 1


def _nested(levels: int) -> dict[str, object]:
    root: dict[str, object] = {}
    current = root
    for _ in range(levels):
        child: dict[str, object] = {}
        current["next"] = child
        current = child
    current["leaf"] = 1
    return root


def _behavior_checks() -> int:
    secret = "sk-demo-secret-123456"
    source = {
        "tool": "boss_hr_greet",
        "args": {"text": secret, "count": 2, "flag": True, "none": None, "ratio": 0.5},
        "items": [1, "二", secret],
    }
    frozen = freeze_policy_context(source)
    checked = _expect_value(frozen["args"]["text"], secret, "策略副本不脱敏")
    checked += _expect_value(type(frozen), MappingProxyType, "顶层只读")
    checked += _expect_value(type(frozen["args"]), MappingProxyType, "嵌套映射只读")
    checked += _expect_value(type(frozen["items"]), tuple, "数组转为元组")
    checked += _expect_value(frozen["args"] is source["args"], False, "嵌套副本独立")
    try:
        frozen["tool"] = "改写"
    except TypeError:
        checked += 1
    else:
        raise ValueError("生命周期 hook 策略副本必须只读")

    observed = freeze_context({"args": {"text": secret}})
    checked += _expect_value(observed["args"]["text"], "<redacted>", "观察副本脱敏")
    long_text = "a" * 16_385
    checked += _expect_value(freeze_context({"text": long_text})["text"], "a" * 16_384, "观察字符串截断")
    deep = {"leaf": 1}
    for _ in range(6):
        deep = {"next": deep}
    node = freeze_context(deep)
    for _ in range(6):
        node = node["next"]
    checked += _expect_value(node, "<omitted:depth>", "观察深度省略")
    many_keys = freeze_context({f"k{index}": index for index in range(70)})
    checked += _expect_value(len(many_keys), 65, "观察键上限")
    checked += _expect_value(many_keys["<omitted:keys>"], "6 more", "观察键省略标注")
    many_items = freeze_context({"items": list(range(140))})
    checked += _expect_value(len(many_items["items"]), 129, "观察数组上限")
    checked += _expect_value(many_items["items"][-1], "<omitted:items:12>", "观察数组省略标注")

    edge = MAX_POLICY_CONTEXT_BYTES - 8
    checked += _expect_value(len(freeze_policy_context({"k": "a" * edge})["k"]), edge, "字节上限接受")
    checked += _expect_rejected({"k": "a" * (edge + 1)}, "HOOK_CONTEXT_TOO_LARGE", "字节上限拒绝")
    values = MAX_POLICY_CONTEXT_NODES - 1
    checked += _expect_value(
        type(freeze_policy_context({f"k{index:05d}": 1 for index in range(values)})), MappingProxyType, "节点上限接受"
    )
    checked += _expect_rejected(
        {f"k{index:05d}": 1 for index in range(values + 1)}, "HOOK_CONTEXT_TOO_LARGE", "节点上限拒绝"
    )
    checked += _expect_value(
        type(freeze_policy_context(_nested(MAX_POLICY_CONTEXT_DEPTH - 1))), MappingProxyType, "深度上限接受"
    )
    checked += _expect_rejected(_nested(MAX_POLICY_CONTEXT_DEPTH), "HOOK_CONTEXT_TOO_LARGE", "深度上限拒绝")

    cycle_list: list = []
    cycle_list.append(cycle_list)
    checked += _expect_rejected({"items": cycle_list}, "HOOK_CONTEXT_INVALID", "环引用数组")
    cycle_dict: dict = {}
    cycle_dict["self"] = cycle_dict
    checked += _expect_rejected({"node": cycle_dict}, "HOOK_CONTEXT_INVALID", "环引用对象")
    checked += _expect_rejected({"k": {1: "x"}}, "HOOK_CONTEXT_INVALID", "非字符串键")
    checked += _expect_rejected({"k": "\ud800"}, "HOOK_CONTEXT_INVALID", "代理项")
    checked += _expect_rejected({"k": math.nan}, "HOOK_CONTEXT_INVALID", "NaN")
    checked += _expect_rejected({"k": math.inf}, "HOOK_CONTEXT_INVALID", "无穷")
    checked += _expect_rejected({"k": (1, 2)}, "HOOK_CONTEXT_INVALID", "元组")
    checked += _expect_rejected({"k": {1, 2}}, "HOOK_CONTEXT_INVALID", "集合")
    checked += _expect_rejected({"k": b"bytes"}, "HOOK_CONTEXT_INVALID", "字节串")
    checked += _expect_rejected({"k": object()}, "HOOK_CONTEXT_INVALID", "自定义对象")
    checked += _expect_rejected([1], "HOOK_CONTEXT_INVALID", "数组顶层")
    checked += _expect_rejected("text", "HOOK_CONTEXT_INVALID", "字符串顶层")
    checked += _expect_rejected(None, "HOOK_CONTEXT_INVALID", "空值顶层")
    return checked


def _plain_callback(context):
    return None


def _keyword_callback(context, signal):
    return None


def _keyword_only_callback(context, *, signal):
    return None


def _positional_callback(context, signal, /):
    return None


def _var_kwargs_callback(context, **kwargs):
    return None


def _var_args_callback(context, *args):
    return None


def _named_var_params_callback(context, *signal):
    return None


def _named_var_kwargs_callback(context, **signal):
    return None


class _PlainHook:
    def __init__(self) -> None:
        self.contexts: list[dict] = []

    def before_tool_call(self, context):
        self.contexts.append(dict(context))


class _KeywordHook:
    def __init__(self) -> None:
        self.signals: list[object] = []

    def before_tool_call(self, context, *, signal=None):
        self.signals.append(signal)


class _PositionalHook:
    def __init__(self) -> None:
        self.signals: list[object] = []

    def before_tool_call(self, context, signal, /):
        self.signals.append(signal)


class _VarKwargsHook:
    def __init__(self) -> None:
        self.kwargs: list[dict] = []

    def before_tool_call(self, context, **kwargs):
        self.kwargs.append(dict(kwargs))


class _BareSignalHook:
    def __init__(self) -> None:
        self.called = 0

    def before_tool_call(self, **signal):
        self.called += 1


class _AfterHook:
    def __init__(self) -> None:
        self.signals: list[object] = []

    def after_tool_call(self, context, *, signal=None):
        self.signals.append(signal)


class _CallableInstance:
    def __call__(self, context, signal):
        return None


def _signal_checks() -> int:
    # 信令分类只依赖参数名与参数种类：仅位置按位置传，普通 / 仅关键字 / 可变关键字
    # 按关键字传；名为 signal 的可变参数与无可解析签名都回退为单参数调用。
    checked = _expect_value(_signal_mode(_plain_callback), None, "单参数回调")
    checked += _expect_value(_signal_mode(lambda context: None), None, "匿名回调")
    checked += _expect_value(_signal_mode(_keyword_callback), "keyword", "普通信令参数")
    checked += _expect_value(_signal_mode(_keyword_only_callback), "keyword", "仅关键字信令")
    checked += _expect_value(_signal_mode(_positional_callback), "positional", "仅位置信令")
    checked += _expect_value(_signal_mode(_var_kwargs_callback), "keyword", "可变关键字兜底")
    checked += _expect_value(_signal_mode(_var_args_callback), None, "可变位置参数不接收信令")
    checked += _expect_value(_signal_mode(_named_var_params_callback), None, "名为 signal 的可变位置参数")
    checked += _expect_value(_signal_mode(_named_var_kwargs_callback), None, "名为 signal 的可变关键字参数")
    checked += _expect_value(_signal_mode(_CallableInstance()), "keyword", "可调用对象")
    checked += _expect_value(_signal_mode(type), None, "无可解析签名")

    event = threading.Event()
    positional = _PositionalHook()
    hooks = LifecycleHooks([positional], timeout=1.0)
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}, cancel_event=event), None,
                             "仅位置回调放行")
    checked += _expect_value(len(positional.signals), 1, "仅位置回调执行一次")
    signal = positional.signals[0]
    checked += _expect_value(type(signal), HookCancellationSignal, "仅位置回调收到信令")
    checked += _expect_value(signal.aborted, False, "信令初始未中止")
    event.set()
    checked += _expect_value(signal.aborted, True, "信令跟随取消事件")
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}, cancel_event=event), None,
                             "已取消不回退为拒绝")
    checked += _expect_value(len(positional.signals), 1, "已取消不再启动回调")

    keyword = _KeywordHook()
    hooks = LifecycleHooks([keyword], timeout=1.0)
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}), None, "无取消事件放行")
    checked += _expect_value(keyword.signals, [None], "无取消事件信令为空")
    event = threading.Event()
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}, cancel_event=event), None,
                             "关键字回调放行")
    checked += _expect_value(type(keyword.signals[-1]), HookCancellationSignal, "关键字回调收到信令")

    var_kwargs = _VarKwargsHook()
    hooks = LifecycleHooks([var_kwargs], timeout=1.0)
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}), None, "可变关键字回调放行")
    checked += _expect_value(var_kwargs.kwargs, [{}], "无取消事件不注入信令关键字")
    event = threading.Event()
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}, cancel_event=event), None,
                             "可变关键字回调带信令放行")
    checked += _expect_value(type(var_kwargs.kwargs[-1].get("signal")), HookCancellationSignal,
                             "可变关键字回调收到信令")

    plain = _PlainHook()
    hooks = LifecycleHooks([plain], timeout=1.0)
    checked += _expect_value(hooks.before_tool_call({"tool": "boss_status"}), None, "单参数回调放行")
    checked += _expect_value(plain.contexts[0].get("phase"), "before_tool_call", "单参数回调收到上下文")

    after = _AfterHook()
    hooks = LifecycleHooks([after], timeout=1.0)
    hooks.after_tool_call({"tool": "boss_status"}, {})
    checked += _expect_value(type(after.signals[-1]), HookCancellationSignal, "观察阶段始终提供信令")

    bare = _BareSignalHook()
    hooks = LifecycleHooks([bare], timeout=1.0)
    decision = hooks.before_tool_call({"tool": "boss_status"}, cancel_event=threading.Event())
    checked += _expect_value((decision.allow, decision.code), (False, "HOOK_ERROR"),
                             "仅可变关键字回调失败关闭")
    checked += _expect_value(bare.called, 0, "仅可变关键字回调未执行")

    positional_bare = _PositionalHook()
    hooks = LifecycleHooks([positional_bare], timeout=1.0)
    decision = hooks.before_tool_call({"tool": "boss_status"})
    checked += _expect_value((decision.allow, decision.code), (False, "HOOK_ERROR"),
                             "无取消事件的仅位置回调失败关闭")
    checked += _expect_value(positional_bare.signals, [], "无信令时不调用仅位置回调")
    return checked


def check_hooks() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(DECISION_FRAGMENTS, module, MODULE)
    checked += _expect(SAFE_FRAGMENTS, module, MODULE)
    checked += _expect(FREEZE_FRAGMENTS, module, MODULE)
    checked += _expect(POLICY_FRAGMENTS, module, MODULE)
    checked += _expect(LIFECYCLE_FRAGMENTS, module, MODULE)
    checked += _expect(EVENT_FRAGMENTS, module, MODULE)
    checked += _expect(INVOKE_FRAGMENTS, module, MODULE)
    checked += _expect(SIGNAL_FRAGMENTS, module, MODULE)
    checked += _expect(DISPATCH_FRAGMENTS, module, MODULE)
    checked += _expect(POLICY_RESULT_FRAGMENTS, module, MODULE)
    checked += _expect(REQUEST_RESULT_FRAGMENTS, module, MODULE)
    checked += _expect(TRANSFORM_FRAGMENTS, module, MODULE)
    checked += _expect(AFTER_FRAGMENTS, module, MODULE)
    checked += _expect(CLOSE_FRAGMENTS, module, MODULE)
    # 取消检查必须先于关闭与容量分支：取消中的回合不得启动新的策略回调。
    cancelled = module.find("if policy and cancel_event is not None and cancel_event.is_set():")
    closed = module.find("if policy and (self._closing or self._closed):")
    if cancelled < 0 or closed < 0 or cancelled > closed:
        raise ValueError(f"{MODULE} 必须先检查取消再检查关闭")
    # 策略上下文必须完整复制：不得经观察用脱敏/截断路径，否则策略看到残缺输入。
    if "freeze_policy_context(_safe_value" in module:
        raise ValueError(f"{MODULE} 的策略上下文不得走观察脱敏路径")
    # 事件观察不得把原始 params 直接交给回调。
    if "_safe_value(dict(params" in module:
        raise ValueError(f"{MODULE} 的事件投影必须先按白名单过滤")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_hooks()
        scenarios = _behavior_checks() + _signal_checks()
    except (ValueError, OSError) as error:
        print(f"生命周期 hook 核对失败，{error}", file=sys.stderr)
        return 2
    print(f"生命周期 hook 一致：{checked} 项上限、脱敏与拒绝防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
