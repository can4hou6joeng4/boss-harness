#!/usr/bin/env python3
"""核对 OpenAI Responses 适配器的流式边界。

`models/openai_responses.py` 把内部消息翻译成 Responses 的 input 条目、把上游
事件映射成 StreamEvent 与 Usage，并决定哪些失败可以自动重试。这里固定
终态原因映射、增量事件集合、可重试状态与流内错误判定、工具调用身份与
参数解析、用量不伪造、以及「已向调用方产出内容后不再重试」的门槛。
"""

from __future__ import annotations

from pathlib import Path
import sys
import types
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

try:
    import openai  # noqa: F401
except ModuleNotFoundError as error:
    if error.name != "openai":
        raise
    # Source build 不安装第三方 SDK：解析辅助函数在导入期不使用 SDK 运行时属性。
    stub = types.ModuleType("openai")
    stub.APIStatusError = type("APIStatusError", (Exception,), {})
    stub.AsyncOpenAI = type("AsyncOpenAI", (), {})
    sys.modules["openai"] = stub

from boss_harness.models.openai_responses import (  # noqa: E402
    _error_message,
    _message_text,
    _parse_arguments,
    _reasoning_text,
    _stop_reason,
    _stream_error_retryable,
    _usage_from_response,
)
from boss_harness.models.output_budget import ResponseTextBudget  # noqa: E402
from boss_harness.models.types import ModelErrorInfo, Usage  # noqa: E402

MODULE = "harness/src/boss_harness/models/openai_responses.py"

CONSTANT_FRAGMENTS = (
    "_STOP_REASONS = {",
    '"completed": "stop",',
    '"in_progress": "stop",',
    '"queued": "stop",',
    '"incomplete": "length",',
    '"failed": "error",',
    '"cancelled": "error",',
    '_TEXT_DELTA_EVENTS = ("response.output_text.delta", "response.refusal.delta")',
    '_THINKING_DELTA_EVENTS = ("response.reasoning_summary_text.delta", "response.reasoning_text.delta")',
    "_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})",
    '_TRANSIENT_ERROR_MARKERS = ("service_unavailable", "server_error", "overloaded", "temporarily")',
    'raise ValueError(f"非法 JSON 常量: {value}")',
    'haystack = f"{code} {detail}".lower()',
    "return any(marker in haystack for marker in _TRANSIENT_ERROR_MARKERS)",
    "if error_info is not None:",
    'if error_info.code == "CONTEXT_OVERFLOW":\n            return False',
    "if error_info.retryable is not None:\n            return error_info.retryable is True",
    "return _looks_transient(code, detail)",
)
INPUT_FRAGMENTS = (
    "if isinstance(message, ToolResultsMessage):",
    '"type": "function_call_output",',
    '"call_id": result.tool_call_id,',
    '"output": result.content,',
    '{"role": "assistant", "content": [{"type": "output_text", "text": block.text}]}',
    '"type": "function_call",',
    '"call_id": block.id,',
    '"name": block.name,',
    '"arguments": json.dumps(dict(block.arguments), ensure_ascii=False),',
    "# ThinkingBlock 不回放：没有可回传的 encrypted_content。",
    'items.append({"role": "user", "content": message.text})',
)
USAGE_FRAGMENTS = (
    'usage = getattr(response, "usage", None)',
    "if usage is None:\n        return None",
    "if input_tokens is None or output_tokens is None:\n        return None",
    'cache_read=(token_count(getattr(details, "cached_tokens", None)) or 0) if details is not None else 0,',
    'cache_write=(token_count(getattr(details, "cache_write_tokens", None)) or 0) if details is not None else 0,',
    '(token_count(getattr(output_details, "reasoning_tokens", None)) or 0)',
    "if output_details is not None\n        else None,",
)
STOP_ORDER = (
    'status == "completed"',
    '("tool_use" if has_tool_calls else "stop"), ""',
    'status == "incomplete"',
    'reason == "max_output_tokens"',
    'return "length", ""',
    'return "error", f"响应未完成（{reason or \'原因未知\'}）"',
    'status in ("failed", "cancelled")',
    'message = str(getattr(error, "message", "") or "") or f"响应状态 {status}"',
    'status in ("in_progress", "queued")',
)
REQUEST_FRAGMENTS = (
    'id = "openai"',
    'raise ValueError("openai provider 需要 bearer 凭据（~/.codex/config.toml 或 BOSS_HARNESS_OPENAI_API_KEY）")',
    "self._max_attempts, self._retry_base_delay = retry_settings()",
    '"store": False,',
    '"max_output_tokens": request.max_tokens,',
    '"type": "function",',
    'kwargs["tool_choice"] = "auto"',
    'kwargs["parallel_tool_calls"] = True',
    'kwargs["reasoning"] = {"effort": request.effort}',
    "self._abort_requested = True",
    "self._abort_event.set()",
    "stop = cancel if callable(cancel) else close",
    "if callable(stop):",
    "return with_retry_outcome(self._normalized_stream(request))",
    'if event.type == "error" and self._abort_requested:',
    'event = StreamEvent(type="error", reason="aborted", error="请求已取消")',
    "finally:\n            events.close()",
    "self._abort_requested = False",
    "self._abort_event.clear()",
    "for attempt in range(1, attempts + 1):",
    "if retryable and not emitted and attempt < attempts:",
    "emitted = True",
    "if isinstance(active, AsyncStreamPump) and not active.worker_done:",
    "；后台清理未确认，已停止自动重试",
    "request.recovery_budget.reserve_retry(self._abort_event)",
    "；共享模型恢复次数已用尽，已停止自动重试",
    "yield retry_start_event(attempt + 1, attempts, delay, self._redact(retry_message or \"\"))",
    "if self._abort_event.wait(delay):",
    "yield retry_aborted_before_attempt_event(attempt + 1)",
    "finally:\n            self._active_stream = None",
    "async with openai.AsyncOpenAI(api_key=self._secret, base_url=self.base_url,",
    "timeout=30.0, max_retries=0",
    "stream = await client.responses.create(**kwargs, stream=True)",
    "pump = AsyncStreamPump(produce, timeout=self._request_timeout_seconds,",
    'name="openai-response-stream"',
    "if not all(identity[1:]):",
    'raise ValueError("工具调用缺少 call_id 或工具名")',
    'if len(identity[1]) > 256 or len(identity[2]) > 256:\n                raise ValueError("工具调用标识或名称超过长度上限")',
    'if len(identity[1]) > 256 or len(identity[2]) > 256:\n                                raise ValueError("工具调用初始项标识或名称超过长度上限")',
    'raise ValueError("工具调用标识或名称超过长度上限")',
    "if expected is None or expected[1:] != actual[1:]:",
    'raise ValueError("工具调用身份与初始输出项不一致")',
    'raise ValueError("工具参数事件缺少输出项标识")',
    "terminal_indexes: set[int] | None = None",
)
PARSE_FRAGMENTS = (
    'if raw is None or raw == "":\n        return {}',
    "text = raw.strip()\n    if not text:\n        return None",
    "parsed = json.loads(text, parse_constant=_reject_json_constant)",
    "except (TypeError, ValueError, RecursionError):\n        return None",
    "return parsed if isinstance(parsed, dict) else None",
    'error = body.get("error")',
    'if isinstance(error, dict) and error.get("message"):\n            return str(error["message"])',
    'return str(getattr(exc, "message", "") or exc)',
)
TEXT_FRAGMENTS = (
    'summary = getattr(item, "summary", None) or []',
    'size += budget.size(text, MAX_RESPONSE_TEXT_BYTES - size)',
    'budget.ensure_size(("thinking", index), size + (2 * max(0, len(parts))))',
    'return budget.reconcile_parts(("thinking", index), parts, separator="\\n\\n") if budget else "\\n\\n".join(parts)',
    'text = getattr(part, "text", None)',
    'text = getattr(part, "refusal", None)',
    'size += budget.size(str(text), MAX_RESPONSE_TEXT_BYTES - size)',
    'budget.ensure_size(("text", index), size)',
    'return budget.reconcile_parts(("text", index), parts) if budget else "".join(parts)',
)
BRANCH_FRAGMENTS = (
    'input_tokens = token_count(getattr(usage, "input_tokens", None))',
    'output_tokens = token_count(getattr(usage, "output_tokens", None))',
    'if not parts:\n        for part in getattr(item, "content", None) or []:',
    'if text is None:\n            text = getattr(part, "refusal", None)',
    "if isinstance(body, dict):",
    'if body.get("message"):\n            return str(body["message"])',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}：期望 {expected!r}，实际 {actual!r}")


def _model_error(**kwargs: object) -> ModelErrorInfo:
    return ModelErrorInfo(provider="openai", source="stream_error", **kwargs)


def _behavior_checks() -> int:
    checked = 0
    # 参数解析：空串与 None 是空对象；只有纯空白、非法常量与截断内容归为 None。
    for raw, expected in (
        (None, {}),
        ("", {}),
        ("   ", None),
        (' {"a": 1} ', {"a": 1}),
        ("[]", None),
        ("null", None),
        ("true", None),
        ("12", None),
        ('"s"', None),
        ('{"a": 1', None),
        ("NaN", None),
        ('{"a": NaN}', None),
        ("[" * 20000 + "]" * 20000, None),
    ):
        _expect_value(_parse_arguments(raw), expected, f"参数解析 {raw!r}")
        checked += 1
    # 终态原因：工具调用覆盖 completed/in_progress，incomplete 只有长度上限算 length。
    for response, has_tool_calls, expected in (
        (SimpleNamespace(status="completed"), False, ("stop", "")),
        (SimpleNamespace(status="completed"), True, ("tool_use", "")),
        (SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="max_output_tokens")), True, ("length", "")),
        (SimpleNamespace(status="incomplete", incomplete_details=SimpleNamespace(reason="content_filter")), False, ("error", "响应未完成（content_filter）")),
        (SimpleNamespace(status="incomplete"), False, ("error", "响应未完成（原因未知）")),
        (SimpleNamespace(status="failed", error=SimpleNamespace(message="upstream down")), False, ("error", "upstream down")),
        (SimpleNamespace(status="failed"), False, ("error", "响应状态 failed")),
        (SimpleNamespace(status="cancelled", error=SimpleNamespace(message="cancelled by upstream")), False, ("error", "cancelled by upstream")),
        (SimpleNamespace(status="in_progress"), True, ("tool_use", "")),
        (SimpleNamespace(status="queued"), False, ("stop", "")),
        (SimpleNamespace(status="weird"), True, ("tool_use", "")),
        (object(), False, ("stop", "")),
    ):
        _expect_value(_stop_reason(response, has_tool_calls), expected, f"终态原因 {response!r}")
        checked += 1
    # 用量：缺失或不完整的计数不伪造全零；明细缺失时缓存为 0、思考为 None。
    for response, expected in (
        (SimpleNamespace(), None),
        (SimpleNamespace(usage=None), None),
        (SimpleNamespace(usage=SimpleNamespace(input_tokens=5)), None),
        (SimpleNamespace(usage=SimpleNamespace(input_tokens=True, output_tokens=2)), None),
        (SimpleNamespace(usage=SimpleNamespace(input_tokens=5, output_tokens=2)), Usage(input=5, output=2)),
        (
            SimpleNamespace(usage=SimpleNamespace(input_tokens="12", output_tokens=" 3 ", input_tokens_details=None, output_tokens_details=None)),
            Usage(input=12, output=3),
        ),
        (
            SimpleNamespace(
                usage=SimpleNamespace(
                    input_tokens=5,
                    output_tokens=2,
                    input_tokens_details=SimpleNamespace(cached_tokens=3, cache_write_tokens=1),
                    output_tokens_details=SimpleNamespace(reasoning_tokens=7),
                )
            ),
            Usage(input=5, output=2, cache_read=3, cache_write=1, reasoning=7),
        ),
        (
            SimpleNamespace(
                usage=SimpleNamespace(
                    input_tokens=5,
                    output_tokens=2,
                    input_tokens_details=SimpleNamespace(),
                    output_tokens_details=SimpleNamespace(),
                )
            ),
            Usage(input=5, output=2, reasoning=0),
        ),
    ):
        _expect_value(_usage_from_response(response), expected, f"用量映射 {response!r}")
        checked += 1
    # 流内错误：上下文溢出与结构化结论优先，只有没有结论时才回退文本标记。
    for error_info, code, detail, expected in (
        (None, "server_error", "", True),
        (None, "", "SERVICE_UNAVAILABLE", True),
        (None, "", "temporarily unavailable", True),
        (None, "bad_request", "invalid", False),
        (_model_error(code="CONTEXT_OVERFLOW", retryable=True), "server_error", "overloaded", False),
        (_model_error(retryable=True), "", "bad", True),
        (_model_error(retryable=False), "server_error", "overloaded", False),
        (_model_error(retryable=None), "", "overloaded", True),
    ):
        _expect_value(_stream_error_retryable(error_info, code, detail), expected, f"重试判定 {code} {detail}")
        checked += 1
    # 思考文本：summary 优先，全部为空时才回退 content，片段以空行分隔。
    for item, expected in (
        (SimpleNamespace(summary=[SimpleNamespace(text="先想"), SimpleNamespace(text="再想")]), "先想\n\n再想"),
        (SimpleNamespace(summary=[SimpleNamespace(text=""), SimpleNamespace(text="有")]), "有"),
        (SimpleNamespace(summary=[], content=[SimpleNamespace(text="a"), SimpleNamespace(text="b")]), "a\n\nb"),
        (SimpleNamespace(summary=[SimpleNamespace(text="")], content=[SimpleNamespace(text="fallback")]), "fallback"),
        (SimpleNamespace(), ""),
        (SimpleNamespace(summary=[SimpleNamespace(text=None)]), ""),
    ):
        _expect_value(_reasoning_text(item), expected, f"思考文本 {item!r}")
        checked += 1
    budget = ResponseTextBudget()
    _expect_value(
        _reasoning_text(SimpleNamespace(summary=[SimpleNamespace(text="你好"), SimpleNamespace(text="世界")]), budget, 2),
        "你好\n\n世界",
        "思考文本预算拼接",
    )
    _expect_value((budget._item_bytes[("thinking", 2)], budget._response_bytes), (14, 14), "思考文本预算计量")
    checked += 2
    # 消息文本：output_text 优先，仅当 text 缺失时才用 refusal，片段直接相连。
    for item, expected in (
        (SimpleNamespace(content=[SimpleNamespace(text="foo"), SimpleNamespace(text="bar")]), "foobar"),
        (SimpleNamespace(content=[SimpleNamespace(text=None, refusal="拒绝")]), "拒绝"),
        (SimpleNamespace(content=[SimpleNamespace(text="", refusal="拒绝")]), ""),
        (SimpleNamespace(content=[SimpleNamespace(refusal="拒绝")]), "拒绝"),
        (SimpleNamespace(), ""),
    ):
        _expect_value(_message_text(item), expected, f"消息文本 {item!r}")
        checked += 1
    budget = ResponseTextBudget()
    _expect_value(
        _message_text(SimpleNamespace(content=[SimpleNamespace(text="你好"), SimpleNamespace(text="世界")]), budget, 1),
        "你好世界",
        "消息文本预算拼接",
    )
    _expect_value((budget._item_bytes[("text", 1)], budget._response_bytes), (12, 12), "消息文本预算计量")
    checked += 2
    # 错误消息：body.error.message → body.message → 异常 message → 异常字符串。
    missing = SimpleNamespace(body=None)
    for exc, expected in (
        (SimpleNamespace(body={"error": {"message": "boom"}}, message="fallback"), "boom"),
        (SimpleNamespace(body={"message": "plain"}, message="fallback"), "plain"),
        (SimpleNamespace(body={"error": {"code": "x"}}, message="fallback"), "fallback"),
        (SimpleNamespace(body={"error": {"message": ""}, "message": "outer"}, message="fallback"), "outer"),
        (SimpleNamespace(body="oops", message="fallback"), "fallback"),
        (missing, str(missing)),
    ):
        _expect_value(_error_message(exc), expected, f"错误消息 {exc!r}")
        checked += 1
    return checked


def check_openai_responses() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, INPUT_FRAGMENTS, USAGE_FRAGMENTS, REQUEST_FRAGMENTS, PARSE_FRAGMENTS, TEXT_FRAGMENTS, BRANCH_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 终态映射必须按 completed → incomplete → failed/cancelled → in_progress/queued 收敛。
    checked += _ordered(STOP_ORDER, module, MODULE)
    checked += _behavior_checks()
    # 反向断言：流内错误必须先看结构化结论，不得整体吞掉异常。
    if "except Exception:" in module.split("def to_input_items")[0]:
        raise ValueError(f"{MODULE} 的流内错误判定不得吞掉全部异常")
    if "json.loads(raw" in module:
        raise ValueError(f"{MODULE} 的参数解析必须按空白与非法常量收敛")
    if '"encrypted_content":' in module:
        raise ValueError(f"{MODULE} 不得回放思考块的加密内容")
    return checked + 1


def main() -> int:
    try:
        checked = check_openai_responses()
    except ValueError as error:
        print(f"OpenAI Responses 适配器核对失败，{error}", file=sys.stderr)
        return 2
    print(f"OpenAI Responses 适配器一致：{checked} 项映射、重试、身份与解析防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
