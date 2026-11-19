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

ROOT = Path(__file__).resolve().parents[1]
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


def check_openai_responses() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, INPUT_FRAGMENTS, USAGE_FRAGMENTS, REQUEST_FRAGMENTS, PARSE_FRAGMENTS, TEXT_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 终态映射必须按 completed → incomplete → failed/cancelled → in_progress/queued 收敛。
    checked += _ordered(STOP_ORDER, module, MODULE)
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
    print(f"OpenAI Responses 适配器一致：{checked} 项映射、重试与身份防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
