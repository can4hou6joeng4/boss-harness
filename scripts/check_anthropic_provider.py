#!/usr/bin/env python3
"""核对 Anthropic Messages 适配器的流式、续接与凭据边界。

`models/anthropic_provider.py` 负责消息翻译、thinking 签名与加密块的续接预算、
工具调用参数装配、用量上报与错误分类。这里固定停止原因映射、可重试状态、
凭据去空白与请求头过滤、流内事件顺序校验、签名总量上限、工具标识上限、
「已产出内容后不再重试」以及错误文本不回显私有载荷等边界。
`with_cache_breakpoints` 为回合请求加提示缓存断点：只在系统提示与最后一条 user
消息的末块各放一处，返回副本而不改入参，不标记工具定义、更早的消息与空白内容，
也不使用顶层缓存字段或更长的保留时间。
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/anthropic_provider.py"

sys.path.insert(0, str(ROOT / "harness/src"))

try:
    import anthropic  # noqa: F401
except ModuleNotFoundError as error:
    if error.name != "anthropic":
        raise
    # Source build 不安装第三方 SDK：纯辅助函数在导入期不使用 SDK 运行时属性。
    stub = types.ModuleType("anthropic")
    for name in ("APIStatusError", "RateLimitError", "APIConnectionError", "APIError"):
        setattr(stub, name, type(name, (Exception,), {}))
    stub.Anthropic = type("Anthropic", (), {})
    stub.AsyncAnthropic = type("AsyncAnthropic", (), {})
    stub.omit = object()
    sys.modules["anthropic"] = stub

from boss_harness.models.anthropic_provider import (  # noqa: E402
    _parse_tool_arguments,
    _status_retryable,
    to_sdk_messages,
    tool_result_payload,
    with_cache_breakpoints,
)
from boss_harness.models.continuation import anthropic_prefix_digest  # noqa: E402
from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    ModelErrorInfo,
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
    ToolResultItem,
    ToolResultsMessage,
    UserMessage,
)

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
TRANSFORM_FRAGMENTS = (
    "def _parse_tool_arguments(raw: str) -> dict[str, object] | None:",
    'if blocks:\n                out.append({"role": "assistant", "content": blocks})',
    "if (prefix_digest is not None and block.prefix_digest is not None",
    "if block.redacted_data is not None:",
    "elif block.signature is not None:",
)
CACHE_FRAGMENTS = (
    "def with_cache_breakpoints(kwargs: Mapping[str, object]) -> dict[str, object]:",
    "return isinstance(value, str) and bool(value.strip())",
    "marked = dict(kwargs)",
    'marked["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]',
    "if not isinstance(messages, list) or not messages:\n        return marked",
    'if not isinstance(last, dict) or last.get("role") != "user":\n        return marked',
    'blocks: list[object] = [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]',
    'and content[-1].get("type") == "tool_result" and _has_text(content[-1].get("content"))):',
    'blocks = [*content[:-1], {**content[-1], "cache_control": {"type": "ephemeral"}}]',
    'marked["messages"] = [*messages[:-1], {**last, "content": blocks}]',
    "self.prompt_cache = config.prompt_cache",
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


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}：期望 {expected!r}，实际 {actual!r}")


def _behavior_checks() -> int:
    checked = 0
    # 参数解析：空串与 None 不是合法对象，纯空白、非对象、非法常量与深嵌套都归为 None。
    for raw, expected in (
        ('{"a": 1}', {"a": 1}),
        ('  {"a": 1}  ', {"a": 1}),
        ("", None),
        (None, None),
        ("[]", None),
        ("null", None),
        ('"s"', None),
        ('{"a": 1', None),
        ("NaN", None),
        ('{"a": NaN}', None),
        ("[" * 20000 + "]" * 20000, None),
    ):
        _expect_value(_parse_tool_arguments(raw), expected, f"参数解析 {raw!r}")
        checked += 1
    # 状态重试：结构化结论优先；流内 200 只认明确可重试，HTTP 错误看状态码集合。
    def info(**kwargs: object) -> ModelErrorInfo:
        return ModelErrorInfo(provider="anthropic", source="http_error", **kwargs)

    for error_info, status, expected in (
        (None, 429, False),
        (None, 200, False),
        (info(code="CONTEXT_OVERFLOW", retryable=True), 200, False),
        (info(retryable=False), 503, False),
        (info(retryable=True), 200, True),
        (info(retryable=None), 200, False),
        (info(retryable=True), 400, False),
        (info(retryable=None), 429, True),
        (info(retryable=None), 529, True),
        (info(retryable=None), 408, True),
        (info(retryable=None), 400, False),
        (info(retryable=None), "429", False),
    ):
        _expect_value(_status_retryable(error_info, status), expected, f"状态重试 {error_info} {status!r}")
        checked += 1
    # 工具结果：JSON 保持中文，序列化失败回退字符串，统一按字符截断到 20000。
    class LongText:
        def __str__(self) -> str:
            return "y" * 30000

    for result, expected in (
        ({"ok": True}, '{"ok": true}'),
        ({"text": "你好"}, '{"text": "你好"}'),
        ("x", '"x"'),
        ([1, 2], "[1, 2]"),
        ({1}, "{1}"),
        ("x" * 25000, '"' + "x" * 19999),
        (LongText(), "y" * 20000),
    ):
        _expect_value(tool_result_payload(result), expected, f"工具结果 {result!r}")
        checked += 1
    # 消息翻译：工具结果合并为一条 user；空 assistant 不产出；思考块按签名与加密状态保留。
    for messages, expected in (
        ([UserMessage("hi")], [{"role": "user", "content": "hi"}]),
        (
            [ToolResultsMessage((ToolResultItem("t1", "ok"), ToolResultItem("t2", "bad", True)))],
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                        {"type": "tool_result", "tool_use_id": "t2", "content": "bad", "is_error": True},
                    ],
                }
            ],
        ),
        (
            [AssistantMessage((TextBlock("a"), TextBlock("b")))],
            [{"role": "assistant", "content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}],
        ),
        (
            [AssistantMessage((ToolCallBlock("t1", "boss_hr_greet", {"a": 1}),))],
            [{"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "boss_hr_greet", "input": {"a": 1}}]}],
        ),
        (
            [AssistantMessage((ThinkingBlock(thinking="x", signature="sig"),))],
            [{"role": "assistant", "content": [{"type": "thinking", "thinking": "x", "signature": "sig"}]}],
        ),
        (
            [AssistantMessage((ThinkingBlock(thinking="x", signature="sig", redacted_data="enc"),))],
            [{"role": "assistant", "content": [{"type": "redacted_thinking", "data": "enc"}]}],
        ),
        ([AssistantMessage((ThinkingBlock(thinking="x"),))], []),
        ([AssistantMessage(())], []),
        ([UserMessage("a"), AssistantMessage(()), UserMessage("b")], [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]),
    ):
        _expect_value(to_sdk_messages(messages), expected, f"消息翻译 {messages!r}")
        checked += 1
    # 前缀摘要：匹配才回放思考；无系统提示不计算摘要，因而不过滤。
    prefix = anthropic_prefix_digest("sys", [], [{"role": "user", "content": "hi"}])
    base = [UserMessage("hi")]
    _expect_value(
        to_sdk_messages(
            base + [AssistantMessage((ThinkingBlock(thinking="t", signature="s", prefix_digest=prefix),))], system="sys"
        ),
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "t", "signature": "s"}]},
        ],
        "前缀匹配保留思考",
    )
    checked += 1
    _expect_value(
        to_sdk_messages(
            base + [AssistantMessage((ThinkingBlock(thinking="t", signature="s", prefix_digest="0" * 64),))], system="sys"
        ),
        [{"role": "user", "content": "hi"}],
        "前缀不符丢弃思考",
    )
    checked += 1
    _expect_value(
        to_sdk_messages(
            base + [AssistantMessage((ThinkingBlock(thinking="t", signature="s", prefix_digest="0" * 64),))], system=None
        ),
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "t", "signature": "s"}]},
        ],
        "无系统提示不过滤",
    )
    checked += 1
    _expect_value(
        to_sdk_messages(
            base
            + [
                AssistantMessage(
                    (
                        ThinkingBlock(thinking="t", redacted_data="enc", prefix_digest="0" * 64),
                        TextBlock("answer"),
                    )
                )
            ],
            system="sys",
        ),
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": [{"type": "text", "text": "answer"}]}],
        "前缀不符只丢思考",
    )
    checked += 1
    return checked


_EPHEMERAL = {"type": "ephemeral"}


def _cache_checks() -> int:
    checked = 0

    def expect(kwargs: dict, expected: dict, label: str) -> None:
        nonlocal checked
        try:
            actual = with_cache_breakpoints(kwargs)
        except Exception as error:  # noqa: BLE001 - 调用点在流开始之前，任何输入形状都不应抛出
            raise ValueError(f"缓存断点 {label}：抛出 {type(error).__name__}") from None
        _expect_value(actual, expected, f"缓存断点 {label}")
        checked += 1

    def user(content: object) -> dict:
        return {"role": "user", "content": content}

    def result(call_id: str, content: object, **extra: object) -> dict:
        return {"type": "tool_result", "tool_use_id": call_id, "content": content, **extra}

    system_block = [{"type": "text", "text": "sys", "cache_control": _EPHEMERAL}]
    hi_block = [{"type": "text", "text": "hi", "cache_control": _EPHEMERAL}]
    assistant = {"role": "assistant", "content": [{"type": "text", "text": "a"}]}
    # 系统提示与字符串 user 正文：非空白字符串各转成带断点的单文本块，两处互不依赖。
    expect({"system": "sys", "messages": []}, {"system": system_block, "messages": []},
           "系统提示转成带断点的文本块")
    expect({"system": "sys", "messages": [user("hi")]},
           {"system": system_block, "messages": [user(hi_block)]}, "系统提示与字符串正文各带一处断点")
    # 空白、缺失与已是块列表的系统提示保持原样，消息上的断点不受影响。
    for blank in ("", "  \n"):
        expect({"system": blank, "messages": [user("hi")]},
               {"system": blank, "messages": [user(hi_block)]}, f"空白系统提示保持原样 {blank!r}")
    expect({"messages": [user("hi")]}, {"messages": [user(hi_block)]}, "缺少系统提示时不新增")
    listed = [{"type": "text", "text": "sys"}]
    expect({"system": listed, "messages": []}, {"system": listed, "messages": []},
           "已是块列表的系统提示不再包裹")
    # 空白正文不能带断点。
    for blank in ("", " \n "):
        expect({"system": "sys", "messages": [user(blank)]},
               {"system": system_block, "messages": [user(blank)]}, f"空白正文不标记 {blank!r}")
    # 工具结果列表：只标记末块，保留错误标记，前面的块不带断点。
    expect({"system": "sys", "messages": [user([result("t1", "ok"), result("t2", "bad", is_error=True)])]},
           {"system": system_block,
            "messages": [user([result("t1", "ok"),
                               result("t2", "bad", is_error=True, cache_control=_EPHEMERAL)])]},
           "工具结果只标记末块")
    for label, content in (("内容为空", ""), ("内容为空白", " \n"),
                           ("内容不是字符串", [{"type": "text", "text": "x"}])):
        blocks = [result("t1", "ok"), result("t2", content)]
        expect({"system": "sys", "messages": [user(blocks)]},
               {"system": system_block, "messages": [user(blocks)]}, f"工具结果{label}时不标记")
    for label, block in (("文本块", {"type": "text", "text": "x"}),
                         ("其他带内容的块", {"type": "mcp_tool_result", "tool_use_id": "t9", "content": "x"})):
        blocks = [result("t1", "ok"), block]
        expect({"system": "sys", "messages": [user(blocks)]},
               {"system": system_block, "messages": [user(blocks)]}, f"末块是{label}时不标记")
    expect({"system": "sys", "messages": [user([])]},
           {"system": system_block, "messages": [user([])]}, "空内容列表不标记")
    # 位置：只看最后一条消息；末条不是 user 时不回头标记更早的 user 消息。
    expect({"system": "sys", "messages": [user("a"), assistant, user("hi")]},
           {"system": system_block, "messages": [user("a"), assistant, user(hi_block)]},
           "只标记最后一条 user 消息")
    # 末条用字符串正文：只有角色判断能拦住它，换成块列表会被形状判断顺带拦下。
    reply = {"role": "assistant", "content": "a"}
    expect({"system": "sys", "messages": [user("hi"), reply]},
           {"system": system_block, "messages": [user("hi"), reply]}, "末条是 assistant 时不标记消息")
    # 其余参数原样保留，工具定义不带断点；返回副本，入参与其中的消息、内容块都不被修改，
    # 调用方先算好的前缀摘要因此仍然对应入参。
    tools = [{"name": "boss_search", "description": "搜索", "input_schema": {"type": "object"}}]
    full = {"model": "m1", "max_tokens": 64, "system": "sys", "tools": tools,
            "thinking": {"type": "adaptive"}, "output_config": {"effort": "high"},
            "messages": [user("a"), assistant, user([result("t1", "ok")])]}
    snapshot = copy.deepcopy(full)
    marked = with_cache_breakpoints(full)
    rest = ("model", "max_tokens", "thinking", "output_config")
    _expect_value({key: marked.get(key) for key in rest}, {key: snapshot[key] for key in rest},
                  "缓存断点 其余参数原样保留")
    checked += 1
    _expect_value(marked.get("tools"), snapshot["tools"], "缓存断点 工具定义不带断点")
    checked += 1
    _expect_value(full, snapshot, "缓存断点 工具结果的入参不被修改")
    checked += 1
    text_only = {"system": "sys", "messages": [user("hi")]}
    text_snapshot = copy.deepcopy(text_only)
    with_cache_breakpoints(text_only)
    _expect_value(text_only, text_snapshot, "缓存断点 字符串正文的入参不被修改")
    checked += 1
    return checked


def check_anthropic_provider() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, STATUS_FRAGMENTS, MESSAGE_FRAGMENTS,
                      TRANSFORM_FRAGMENTS, CACHE_FRAGMENTS, CREDENTIAL_FRAGMENTS, REQUEST_FRAGMENTS,
                      STREAM_ONCE_FRAGMENTS):
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
    # 顶层缓存字段在部分平台被拒；更长的保留时间会提高写入成本，不能悄悄启用。
    if 'kwargs["cache_control"]' in module or 'marked["cache_control"]' in module:
        raise ValueError(f"{MODULE} 不得使用顶层缓存字段")
    if '"ttl"' in module:
        raise ValueError(f"{MODULE} 不得设置缓存保留时间")
    checked += _behavior_checks()
    checked += _cache_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_anthropic_provider()
    except ValueError as error:
        print(f"Anthropic 适配器核对失败，{error}", file=sys.stderr)
        return 2
    print(f"Anthropic 适配器一致：{checked} 项续接、重试、凭据、翻译与缓存断点防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
