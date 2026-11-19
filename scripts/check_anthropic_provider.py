#!/usr/bin/env python3
"""核对 Anthropic Messages 适配器的流式、续接与凭据边界。

`models/anthropic_provider.py` 负责消息翻译、thinking 签名与加密块的续接预算、
工具调用参数装配、用量上报与错误分类。这里固定停止原因映射、可重试状态、
凭据去空白与请求头过滤、流内事件顺序校验、签名总量上限、工具标识上限、
「已产出内容后不再重试」以及错误文本不回显私有载荷等边界。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/anthropic_provider.py"

CONSTANT_FRAGMENTS = (
    '_FALLBACK_BETA = "server-side-fallback-2026-07-01"',
    "_STOP_REASONS = {",
    '"end_turn": "stop",',
    '"stop_sequence": "stop",',
    '"tool_use": "tool_use",',
    '"max_tokens": "length",',
    '"pause_turn": "stop",',
    '"refusal": "error",',
    "_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504, 529})",
    'raise ValueError(f"非法 JSON 常量: {value}")',
    "parsed = json.loads(raw, parse_constant=_reject_json_constant)",
    "except (TypeError, ValueError, RecursionError):\n        return None",
    "return parsed if isinstance(parsed, dict) else None",
)
STATUS_FRAGMENTS = (
    "def _status_retryable(error_info, status_code: object) -> bool:",
    'if error_info is None or error_info.code == "CONTEXT_OVERFLOW" or error_info.retryable is False:\n        return False',
    "if status_code == 200:\n        return error_info.retryable is True",
    "return status_code in _RETRYABLE_STATUS",
    "def tool_result_payload(result: object) -> str:",
    'return json.dumps(result, ensure_ascii=False)[:20000]',
    "except TypeError:\n        return str(result)[:20000]",
)
MESSAGE_FRAGMENTS = (
    "def to_sdk_messages(messages: Sequence[ChatMessage], *, system: str | None = None,",
    '"type": "tool_result",',
    '"tool_use_id": item.tool_call_id,',
    '"content": item.content,',
    '**({"is_error": True} if item.is_error else {}),',
    'blocks.append({"type": "text", "text": block.text})',
    'blocks.append({"type": "redacted_thinking", "data": block.redacted_data})',
    'blocks.append({"type": "thinking", "thinking": block.thinking,',
    '"signature": block.signature})',
    '{"type": "tool_use", "id": block.id, "name": block.name, "input": dict(block.arguments)}',
    'out.append({"role": "user", "content": message.text})',
    "prefix_digest = anthropic_prefix_digest(system, tools, out) if system is not None else None",
    "and block.prefix_digest != prefix_digest):\n                        continue",
)
CREDENTIAL_FRAGMENTS = (
    'id = "anthropic"',
    'env_api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()',
    'env_auth_token = (os.environ.get("ANTHROPIC_AUTH_TOKEN") or "").strip()',
    "if env_api_key:\n            credential_options[\"api_key\"] = env_api_key",
    'elif env_auth_token:\n            credential_options["auth_token"] = env_auth_token',
    "snapshot = anthropic.Anthropic(timeout=30.0, max_retries=0, **credential_options)",
    'if len(self._client_options) == 1:\n                raise ValueError("Anthropic 线路未配置可用凭据")',
    'if not name.lower().startswith("x-stainless-") and name.lower() != "user-agent"}',
    "self._credential_secrets = tuple(value for value in",
    "return bounded_error(\"\", redact_secrets(str(text), extra=self._credential_secrets))",
)
REQUEST_FRAGMENTS = (
    "self._last_pump: AsyncStreamPump | None = None",
    'return with_retry_outcome(self._normalized_stream(request))',
    'if event.type == "error" and self._abort_requested:',
    'event = StreamEvent(type="error", reason="aborted", error="请求已取消")',
    "finally:\n            events.close()",
    '"messages": to_sdk_messages(request.messages, system=request.system, tools=tools),',
    'kwargs["thinking"] = dict(request.thinking)',
    'kwargs["output_config"] = {"effort": request.effort}',
    "self._abort_requested = False",
    "self._abort_event.clear()",
    "for attempt in range(1, attempts + 1):",
    "if retryable and not emitted and attempt < attempts:",
    "emitted = True",
    "if pump is not None and not pump.worker_done:",
    "；后台清理未确认，已停止自动重试",
    "；共享模型恢复次数已用尽，已停止自动重试",
    "yield retry_start_event(attempt + 1, attempts, delay, self._redact(retry_message or \"\"))",
    "if self._abort_event.wait(delay):",
    "def _final_retry_error(self, event: StreamEvent, suffix: str) -> StreamEvent:",
    "info = replace(event.error_info, retryable=False) if event.error_info is not None else None",
    "return replace(event, error=self._redact((event.error or \"模型请求失败\") + suffix), error_info=info)",
)
STREAM_ONCE_FRAGMENTS = (
    'usage = {"input_tokens": 0, "output_tokens": 0,',
    "usage_seen: set[str] = set()",
    "def private_error_info(info):",
    "return replace(info, provider_code=None) if has_private() else info",
    "async with anthropic.AsyncAnthropic(timeout=30.0, max_retries=0,",
    'headers = {name: anthropic.omit for name in client.default_headers',
    "if self.server_side_fallback:",
    'betas=[_FALLBACK_BETA],',
    'fallbacks="default",',
    'pump = AsyncStreamPump(produce, timeout=self._request_timeout_seconds,',
    'name="anthropic-message-stream"',
    'if self._abort_requested:\n                    yield StreamEvent(type="error", reason="aborted", error="请求已取消")',
    'raise ValueError("message_stop 之后收到额外模型流事件")',
    'raise ValueError("响应重复使用内容块索引")',
    'raise ValueError("思考初始签名无效")',
    'raise ValueError("思考签名超过私有续接预算")',
    'raise ValueError("加密思考块超过私有续接预算")',
    'raise ValueError("当前内核不支持服务端 fallback 续接块")',
    'raise ValueError("工具调用标识无效或重复")',
    "or len(call_id) > 256 or call_id in tool_ids.values()):",
    "if (size > MAX_ANTHROPIC_SIGNATURE_BYTES\n                                        or signature_bytes + size > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES):\n                                    raise ValueError(\"思考签名超过私有续接预算\")",
    'raise ValueError("工具调用名称无效")',
    'raise ValueError("工具调用初始参数不是 JSON object")',
    'raise ValueError("文本增量没有对应的活动文本块")',
    'raise ValueError("思考增量没有对应的活动思考块")',
    'raise ValueError("思考签名增量没有唯一的活动 thinking block")',
    'raise ValueError("工具参数增量没有对应的活动工具块")',
    'raise ValueError("工具调用初始参数与增量来源冲突")',
    'raise ValueError("响应重复关闭内容块")',
    'raise ValueError("内容块增量与块类型不一致")',
    'raise ValueError("模型流未正常结束")',
    'raise ValueError("工具响应缺少完整的 thinking 签名")',
    "self._last_error_retryable = True",
    'message = "模型连接失败" if has_private() else f"连接失败：{exc}"',
    "except anthropic.RateLimitError as exc:",
    "self._last_error_retry_after = retry_after_seconds(exc)",
    'message = "模型请求被限流" if has_private() else f"被限流：{exc}"',
    'source="stream_error" if exc.status_code == 200 else "http_error",',
    "except OutputBudgetExceeded as exc:",
    'error=f"模型流处理异常（{type(exc).__name__}）",',
    "finally:\n            self._active_stream = None",
    "parsed = {} if raw == \"\" else _parse_tool_arguments(raw)",
    'error=self._redact(f"工具调用参数不是完整 JSON object：{name or \'unknown\'}"),',
    'mapped_stop_reason = _STOP_REASONS.get(str(stop_reason or ""), "stop")',
    'if {"input_tokens", "output_tokens"} <= usage_seen else None),',
    'if str(stop_reason) == "refusal":',
    'yield StreamEvent(type="error", reason="error", error="模型以安全原因拒绝")',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_anthropic_provider() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, STATUS_FRAGMENTS, MESSAGE_FRAGMENTS,
                      CREDENTIAL_FRAGMENTS, REQUEST_FRAGMENTS, STREAM_ONCE_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 签名预算必须同时限制单块与总量。
    if "MAX_ANTHROPIC_SIGNATURE_BYTES" not in module or "MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES" not in module:
        raise ValueError(f"{MODULE} 必须保留思考签名预算")
    # 反向断言：不得把加密思考内容写进错误文本，也不得让错误回显原始载荷。
    if 'error=f"模型流处理异常（{exc}）"' in module:
        raise ValueError(f"{MODULE} 的通用异常不得回显原始载荷")
    if "except Exception:\n                pass" not in module:
        raise ValueError(f"{MODULE} 的中断兜底不得把异常抛给调用方")
    if "json.loads(raw)" in module:
        raise ValueError(f"{MODULE} 的参数解析必须拒绝非法常量")
    return checked + 1


def main() -> int:
    try:
        checked = check_anthropic_provider()
    except ValueError as error:
        print(f"Anthropic 适配器核对失败，{error}", file=sys.stderr)
        return 2
    print(f"Anthropic 适配器一致：{checked} 项续接、重试与凭据防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
