#!/usr/bin/env python3
"""核对模型请求策略的拒绝投影与脱敏边界。

策略拒绝必须与 provider 错误区分，拒绝原因不得把凭据或原文写入会话；投影
字段、脱敏与 model_error 记录被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/request_policy.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.hooks import HookDecision  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.models.secret import Secret  # noqa: E402
from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    ModelRequest,
    TextBlock,
    ToolCallBlock,
    ToolResultItem,
    ToolResultsMessage,
    UserMessage,
)
from boss_harness.request_policy import (  # noqa: E402
    ModelRequestRejected,
    _unit_view,
    check_model_request,
    history_units,
    record_model_rejection,
    transform_request_context,
)
from boss_harness.session import SessionStore  # noqa: E402

PAYLOAD_FRAGMENTS = (
    "MAX_UNIT_PREVIEW_CHARS = 1_000",
    '("purpose", "provider", "model", "requestIndex", "threadId", "turnId", "jobId")',
    '"errorInfo": {"source": "request_policy", "code": self.code}',
    '"outputObserved": False',
    '"contextRecoveryEligible": False',
    '"requestRejected": True',
)
PREVIEW_FRAGMENTS = (
    '"userText": redact_secrets(text[:MAX_UNIT_PREVIEW_CHARS])',
    '"toolNames": tool_names[:64]',
    "for message in messages if isinstance(message, AssistantMessage)",
    "for message in messages if isinstance(message, ToolResultsMessage)",
)
TRANSFORM_FRAGMENTS = (
    "if len(units) < 2:",
    "offset = max(0, len(units) - MAX_CONTEXT_UNITS)",
    "if outcome is None or (cancel_event is not None and cancel_event.is_set()):",
    "dropped = set(outcome)",
    "return replace(request, messages=messages)",
)
IDENTITY_FRAGMENTS = (
    "request = replace(request, task_context=task)",
    "if hooks is None or (cancel_event is not None and cancel_event.is_set()):",
    'if task.purpose == "turn" and hooks.transforms_context:',
    "decision = hooks.before_request(context, cancel_event=cancel_event)",
    "if decision is not None and not decision.allow:",
)
RECORD_FRAGMENTS = (
    "if not error.recorded:",
    'sessions.append(thread_id, Entry(type="model_error", payload=error.payload()))',
    "error.recorded = True",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "`requestRejected=true` 区分策略拒绝"),
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
        raise ValueError(f"请求策略行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


class _FakeHooks:
    def __init__(self, *, transform=None, decision=None) -> None:
        self.transforms_context = transform is not None
        self._transform = transform
        self._decision = decision
        self.transform_calls: list[dict] = []
        self.before_calls: list[dict] = []

    def transform_context(self, context, *, unit_count, cancel_event=None):
        self.transform_calls.append(dict(context))
        return self._transform(context, unit_count) if self._transform else None

    def before_request(self, context, *, cancel_event=None):
        self.before_calls.append(dict(context))
        return self._decision


def _request(messages) -> ModelRequest:
    return ModelRequest(model="gpt-x", system="s", messages=tuple(messages))


def check_request_policy() -> int:
    module = _read(MODULE)
    checked = _expect(PAYLOAD_FRAGMENTS, module, MODULE)
    checked += _expect(PREVIEW_FRAGMENTS, module, MODULE)
    checked += _expect(TRANSFORM_FRAGMENTS, module, MODULE)
    checked += _expect(IDENTITY_FRAGMENTS, module, MODULE)
    checked += _expect(RECORD_FRAGMENTS, module, MODULE)
    # 两条拒绝路径都必须先脱敏再抛出；直接使用原始消息会让凭据进入会话。
    rejects = module.count("raise ModelRequestRejected(")
    redacted = module.count("redact_secrets(outcome.message") + module.count("redact_secrets(decision.message")
    if rejects != 2 or redacted != 2:
        raise ValueError(f"{MODULE} 的两处策略拒绝必须各自经过 redact_secrets")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    # 行为：历史单元从用户输入切分，无用户消息时整段一个单元。
    assistant = AssistantMessage(blocks=(TextBlock(text="abc"),))
    tool_results = ToolResultsMessage(results=(ToolResultItem(tool_call_id="c1", content="abcd"),))
    checked += _expect_value(history_units(()), [], "空历史")
    checked += _expect_value(history_units((assistant, tool_results)), [(0, 2)], "无用户消息")
    checked += _expect_value(
        history_units((UserMessage(text="u1"), assistant, UserMessage(text="u2"), assistant)),
        [(0, 2), (2, 4)], "用户消息切分")
    checked += _expect_value(history_units((assistant, UserMessage(text="u1"), assistant)),
                             [(0, 1), (1, 3)], "中途用户消息")
    # 行为：单元摘要截断与脱敏，工具名最多 64 条但计数完整。
    calls = tuple(ToolCallBlock(id=f"c{i}", name=f"tool{i}") for i in range(65))
    view = _unit_view(2, (UserMessage(text="x" * 1005),
                          AssistantMessage(blocks=(TextBlock(text="abc"), *calls)), tool_results))
    checked += _expect_value(
        (view["index"], view["messageCount"], view["userTextChars"], len(view["userText"]),
         len(view["toolNames"]), view["toolCallCount"], view["assistantTextChars"],
         view["toolResultChars"]),
        (2, 3, 1005, 1000, 64, 65, 3, 4), "单元摘要")
    checked += _expect_value(_unit_view(0, (UserMessage(text="key sk-abcdef123456"),))["userText"],
                             "key <redacted>", "单元脱敏")
    # 行为：变换在单元不足或取消时放行，按结果丢弃整段历史。
    first, second = UserMessage(text="u1"), UserMessage(text="u2")
    request = _request((first, assistant, second))
    config = ModelConfig(provider="openai", model="gpt-x")
    single = _request((first,))
    hooks = _FakeHooks(transform=lambda context, unit_count: (0,))
    checked += _expect_value(
        transform_request_context(hooks, config, single, {}, None) is single, True, "单元不足")
    checked += _expect_value(hooks.transform_calls, [], "单元不足不调用")
    hooks = _FakeHooks(transform=lambda context, unit_count: None)
    checked += _expect_value(transform_request_context(hooks, config, request, {}, None) is request,
                             True, "变换无结果")
    hooks = _FakeHooks(transform=lambda context, unit_count: ())
    checked += _expect_value(transform_request_context(hooks, config, request, {}, None) is request,
                             True, "空丢弃")
    cancel = threading.Event()
    cancel.set()
    hooks = _FakeHooks(transform=lambda context, unit_count: (0,))
    checked += _expect_value(transform_request_context(hooks, config, request, {}, cancel) is request,
                             True, "变换取消")
    hooks = _FakeHooks(transform=lambda context, unit_count: (0,))
    transformed = transform_request_context(hooks, config, request, {"purpose": "turn"}, None)
    checked += _expect_value(transformed.messages, (second,), "丢弃单元")
    checked += _expect_value(
        (hooks.transform_calls[0]["unitCount"], hooks.transform_calls[0]["unitOffset"],
         len(hooks.transform_calls[0]["units"])), (2, 0, 2), "变换上下文")
    # 行为：变换拒绝抛出脱敏的策略拒绝。
    secret = Secret("sk-secret123456")
    secret_config = ModelConfig(provider="openai", model="gpt-x", api_key=secret)
    hooks = _FakeHooks(transform=lambda context, unit_count: HookDecision(
        False, "DENIED", "密钥 sk-secret123456 被拒绝"))
    try:
        transform_request_context(hooks, secret_config, request, {"purpose": "turn"}, None)
    except ModelRequestRejected as error:
        checked += _expect_value((error.code, "sk-secret123456" in str(error),
                                  "<redacted>" in str(error)), ("DENIED", False, True),
                                 "变换拒绝脱敏")
    else:
        raise ValueError("变换拒绝必须抛出 ModelRequestRejected")
    # 行为：请求检查总是重写归属，取消时短路，只有回合请求先变换。
    result = check_model_request(None, config, request, {"tokens": 1}, purpose="turn",
                                 request_index=3, thread_id="thread-1", turn_id="turn-1")
    task = result.task_context
    checked += _expect_value(
        (getattr(task, "purpose", None), getattr(task, "request_index", None),
         getattr(task, "thread_id", None), getattr(task, "turn_id", None)),
        ("turn", 3, "thread-1", "turn-1"), "归属重写")
    checked += _expect_value(result is request, False, "归属新请求")
    hooks = _FakeHooks(decision=None)
    result = check_model_request(hooks, config, request, {}, purpose="turn", request_index=0,
                                 cancel_event=cancel)
    checked += _expect_value((getattr(result.task_context, "purpose", None),
                              hooks.before_calls), ("turn", []), "请求取消短路")
    hooks = _FakeHooks(transform=lambda context, unit_count: (0,))
    check_model_request(hooks, config, request, {}, purpose="compaction", request_index=1)
    checked += _expect_value(hooks.transform_calls, [], "非回合不变换")
    hooks = _FakeHooks(transform=lambda context, unit_count: (0,))
    result = check_model_request(hooks, config, request, {}, purpose="turn", request_index=2)
    checked += _expect_value(result.messages, (second,), "回合变换")
    checked += _expect_value(hooks.before_calls[0]["messageCount"], 1, "变换后消息数")
    # 行为：before_request 拒绝抛出脱敏拒绝，上下文只含已知身份。
    hooks = _FakeHooks(decision=HookDecision(False, "HOOK_DENIED", "含 sk-secret123456"))
    try:
        check_model_request(hooks, secret_config, request, {"budget": 1}, purpose="turn",
                            request_index=0, thread_id="thread-1", turn_id="turn-1",
                            job_id="job-1", max_model_requests=9)
    except ModelRequestRejected as error:
        payload = error.payload()
        checked += _expect_value(
            (error.code, "sk-secret123456" in payload["message"], payload["threadId"],
             payload["turnId"], payload["jobId"], "maxModelRequests" in payload),
            ("HOOK_DENIED", False, "thread-1", "turn-1", "job-1", False), "请求拒绝")
    else:
        raise ValueError("before_request 拒绝必须抛出 ModelRequestRejected")
    hooks = _FakeHooks(decision=HookDecision(True))
    result = check_model_request(hooks, config, request, {}, purpose="turn", request_index=0)
    checked += _expect_value(getattr(result.task_context, "request_index", None), 0, "允许请求")
    hooks = _FakeHooks(decision=None)
    check_model_request(hooks, config, request, {"tokens": 2}, purpose="compaction",
                        request_index=4)
    context = hooks.before_calls[0]
    checked += _expect_value(
        ("threadId" in context, "turnId" in context, "jobId" in context,
         "maxModelRequests" in context), (False, False, False, False), "请求上下文省略")
    hooks = _FakeHooks(decision=None)
    check_model_request(hooks, config, request, {}, purpose="turn", request_index=4)
    context = hooks.before_calls[0]
    checked += _expect_value((context["threadId"], context["turnId"]), (None, None),
                             "回合身份占位")
    # 行为：拒绝载荷只保留白名单身份与固定字段。
    error = ModelRequestRejected("CODE_X", "msg sk-abcdef123456",
                                 {"purpose": "turn", "provider": "openai", "threadId": "t",
                                  "extra": 1})
    payload = error.payload()
    checked += _expect_value(
        (sorted(payload), payload["code"], payload["errorInfo"], payload["requestRejected"],
         payload["outputObserved"], payload["contextRecoveryEligible"]),
        (sorted(("purpose", "provider", "threadId", "code", "message", "errorInfo",
                 "outputObserved", "contextRecoveryEligible", "requestRejected")),
         "CODE_X", {"source": "request_policy", "code": "CODE_X"}, True, False, False),
        "拒绝载荷")
    checked += _expect_value("extra" in payload, False, "拒绝白名单")
    # 行为：策略拒绝每个错误只记录一条 model_error。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("策略拒绝")["id"]
            error = ModelRequestRejected("CODE_X", "msg", {"purpose": "turn"})
            record_model_rejection(store, thread_id, error)
            first_entries = [entry for entry in store.read_entries(thread_id)
                             if entry.get("type") == "model_error"]
            checked += _expect_value(len(first_entries), 1, "拒绝记录")
            checked += _expect_value(
                (error.recorded, first_entries[0]["payload"]["code"],
                 first_entries[0]["payload"]["requestRejected"]), (True, "CODE_X", True),
                "拒绝记录内容")
            record_model_rejection(store, thread_id, error)
            second_entries = [entry for entry in store.read_entries(thread_id)
                              if entry.get("type") == "model_error"]
            checked += _expect_value(len(second_entries), 1, "拒绝记录幂等")
        finally:
            store.close()
    return checked + 1


def main() -> int:
    try:
        checked = check_request_policy()
    except ValueError as error:
        print(f"请求策略核对失败，{error}", file=sys.stderr)
        return 2
    print(f"请求策略一致：{checked} 项投影、脱敏与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
