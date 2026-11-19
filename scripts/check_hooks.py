#!/usr/bin/env python3
"""核对生命周期 hook 的超时、上下文冻结与策略拒绝边界。

hooks.py 是宿主注入策略的唯一入口：事件观察有界且脱敏，策略检查收到完整
JSON 快照并 fail closed，超时与关闭期限不会让迟到结果改写回合。任一上限、
脱敏或拒绝映射被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/hooks.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

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
    except ValueError as error:
        print(f"生命周期 hook 核对失败，{error}", file=sys.stderr)
        return 2
    print(f"生命周期 hook 一致：{checked} 项上限、脱敏与拒绝防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
