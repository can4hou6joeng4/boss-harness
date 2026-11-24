#!/usr/bin/env python3
"""核对 Anthropic Messages 流状态机的块索引、增量归属与错误收敛。

`AnthropicProvider._stream_once` 把官方 SDK 的事件流映射成 StreamEvent：
内容块索引在起始、增量与关闭之间必须唯一且一致；增量类型必须匹配活动块；
thinking 签名的初始值与增量覆盖共享同一份续接预算；工具调用的 id/名称在落库前
必须可用，参数分片或初始快照只能二选一；`message_stop` 是终态前提，之后出现
任何事件都算协议错误；取消、总时限与 SDK 错误一律收敛成 `error` 事件。

这里用假的 `anthropic` 客户端驱动真实 `_stream_once`（不联网、不调用模型），
逐类验证文本、思考签名、加密思考、工具调用、用量与停止原因、协议错误、
预算超限、错误分类、请求路径、提示缓存断点、中途取消与总时限；同时静态固定关键
拒绝分支、事件顺序与异常分层顺序。提示缓存断点只加在回合请求上，并且排在思考块
续接用的前缀摘要之后：摘要、连接检查与没有任务上下文的请求保持原形状。
"""

from __future__ import annotations

import ast
import asyncio
import os
from pathlib import Path
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/anthropic_provider.py"
sys.path.insert(0, str(ROOT / "harness/src"))

# Source build 在安装依赖前运行本脚本：模块级导入 SDK，这里注入最小占位模块
# 让真实模块可导入，行为对照随后用完整假 SDK 替换。
try:
    import anthropic  # noqa: F401
except ModuleNotFoundError:
    _sdk_stub = types.ModuleType("anthropic")
    for _name in ("APIError", "APIStatusError", "APIConnectionError", "RateLimitError"):
        setattr(_sdk_stub, _name, type(_name, (Exception,), {}))
    _sdk_stub.Anthropic = type("Anthropic", (), {})
    _sdk_stub.AsyncAnthropic = type("AsyncAnthropic", (), {})
    _sdk_stub.omit = object()
    sys.modules["anthropic"] = _sdk_stub

from boss_harness.models import anthropic_provider, ModelConfig  # noqa: E402
from boss_harness.models.continuation import anthropic_prefix_digest  # noqa: E402
from boss_harness.models.secret import Secret  # noqa: E402
from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    ModelRequest,
    ModelTaskContext,
    ThinkingBlock,
    ToolCallBlock,
    ToolResultItem,
    ToolResultsMessage,
    ToolSpec,
    UserMessage,
)

RESET = (
    "        self._last_error_retryable = False",
    "        self._last_error_retry_after = None",
)
PRIVATE = (
    "        request_has_private = any(",
    "        def has_private() -> bool:",
    "        def private_error_info(info):",
)
ABORT = (
    "                if self._abort_requested:",
    '                    yield StreamEvent(type="error", reason="aborted", error="请求已取消")',
    "                    if self._abort_requested:",
)
MESSAGE_STOP = (
    "                    if saw_message_stop:",
    '                        raise ValueError("message_stop 之后收到额外模型流事件")',
)
START = (
    "                        if index in block_types:",
    '                            raise ValueError("响应重复使用内容块索引")',
)
SIGNATURE_START = (
    '                            initial_signature = getattr(event.content_block, "signature", None)',
    "                                if not isinstance(initial_signature, str):",
    '                                    raise ValueError("思考初始签名无效")',
    "                                if (size > MAX_ANTHROPIC_SIGNATURE_BYTES",
    "                                        or signature_bytes + size > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES):",
    '                                    raise ValueError("思考签名超过私有续接预算")',
    "                                signatures[index] = initial_signature",
)
REDACTED = (
    '                        elif block_type == "redacted_thinking":',
    "                            if not isinstance(data, str) or not data:",
    '                                raise ValueError("加密思考块无效")',
    "                            if (size > MAX_ANTHROPIC_SIGNATURE_BYTES",
    "                                    or signature_bytes + size > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES):",
    '                                raise ValueError("加密思考块超过私有续接预算")',
)
FALLBACK_BLOCK = (
    '                        elif block_type == "fallback":',
    '                            raise ValueError("当前内核不支持服务端 fallback 续接块")',
)
TOOL_START = (
    "                            if (not isinstance(call_id, str) or not call_id",
    "                                    or len(call_id) > 256 or call_id in tool_ids.values()):",
    '                                raise ValueError("工具调用标识无效或重复")',
    "                            if (not isinstance(call_name, str) or not call_name",
    "                                    or len(call_name) > 256):",
    '                                raise ValueError("工具调用名称无效")',
    "                            if initial not in (None, {}):",
    "                                if not isinstance(initial, dict):",
    '                                    raise ValueError("工具调用初始参数不是 JSON object")',
    "                                snapshot_only_tools.add(index)",
)
TEXT_DELTA = (
    '                            if block_types.get(index) != "text" or index in closed_blocks:',
    '                                raise ValueError("文本增量没有对应的活动文本块")',
    '                            yield StreamEvent(type="text_delta", content_index=index, delta=text)',
)
THINKING_DELTA = (
    '                            if block_types.get(index) != "thinking" or index in closed_blocks:',
    '                                raise ValueError("思考增量没有对应的活动思考块")',
    '                            yield StreamEvent(type="thinking_delta", content_index=index, delta=text)',
)
SIGNATURE_DELTA = (
    '                            if block_types.get(index) != "thinking" or index in closed_blocks:',
    '                                raise ValueError("思考签名增量没有唯一的活动 thinking block")',
    "                            if not isinstance(signature, str) or not signature:",
    '                                raise ValueError("思考签名增量无效")',
    "                            additional = max(0, size - signature_sizes.get(index, 0))",
    "                                    or signature_bytes + additional > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES):",
    "                            signature_sizes[index] = max(size, signature_sizes.get(index, 0))",
)
INPUT_DELTA = (
    "                            if index not in started_tools or index in closed_tool_blocks:",
    '                                raise ValueError("工具参数增量没有对应的活动工具块")',
    "                            if index in snapshot_only_tools:",
    '                                raise ValueError("工具调用初始参数与增量来源冲突")',
    '                                type="toolcall_delta",',
)
STOP = (
    "                        if index in closed_blocks:",
    '                            raise ValueError("响应重复关闭内容块")',
    '                                yield StreamEvent(type="thinking_end", content_index=index, text=joined)',
    '                                yield StreamEvent(type="text_end", content_index=index, text=joined)',
    '                                raise ValueError("内容块增量与块类型不一致")',
)
ENDING = (
    "                if not saw_message_stop:",
    '                    raise ValueError("模型流未正常结束")',
    "                if started_tools and any(",
    "                        index not in signatures or index not in closed_blocks",
    '                        for index, value in block_types.items() if value == "thinking"):',
    '                    raise ValueError("工具响应缺少完整的 thinking 签名")',
)
TOOL_FINISH = (
    "            if index not in closed_tool_blocks:",
    '                    error=self._redact(f"工具调用参数流未完整结束：{tool_names.get(index) or \'unknown\'}"),',
    '            parsed = {} if raw == "" else _parse_tool_arguments(raw)',
    "            if parsed is None:",
    '                name = tool_names.get(index, "")',
    '                    error=self._redact(f"工具调用参数不是完整 JSON object：{name or \'unknown\'}"),',
)
USAGE = (
    '            usage=(Usage(input=usage["input_tokens"], output=usage["output_tokens"],',
    '                   if {"input_tokens", "output_tokens"} <= usage_seen else None),',
    '        mapped_stop_reason = _STOP_REASONS.get(str(stop_reason or ""), "stop")',
    '        if str(stop_reason) == "refusal":',
    '            yield StreamEvent(type="error", reason="error", error="模型以安全原因拒绝")',
    '        yield StreamEvent(type="done", reason=mapped_stop_reason, message=message)',
)
DEADLINE = (
    "        except StreamDeadlineExceeded:",
    "                retryable = pump.worker_done",
    '                error=f"模型请求超过 {self._request_timeout_seconds} 秒总时限{detail}",',
    "        except StreamAborted:",
    "        except StreamPumpCapacityExceeded:",
)
ERRORS = (
    "        except anthropic.APIConnectionError as exc:",
    "        except SDK_TRANSPORT_ERRORS as exc:",
    "        except anthropic.RateLimitError as exc:",
    "        except anthropic.APIStatusError as exc:",
    '                source="stream_error" if exc.status_code == 200 else "http_error",',
    "        except OutputBudgetExceeded as exc:",
    "        except Exception as exc:  # noqa: BLE001",
    '                error=f"模型流处理异常（{type(exc).__name__}）",',
)
REQUEST_PATH = (
    "                    if self.server_side_fallback:",
    "                        stream = await client.beta.messages.create(",
    "                            betas=[_FALLBACK_BETA],",
    '                            fallbacks="default",',
    "                        stream = await client.messages.create(**kwargs, stream=True,",
    "                    headers = {name: anthropic.omit for name in client.default_headers",
    '                        if name.lower() not in self._request_header_names',
    '                        and not name.lower().startswith("x-stainless-")',
    '                        and name.lower() != "user-agent"}',
)
EVENT_BRANCHES = (
    'kind == "message_start"',
    'kind == "message_delta"',
    'kind == "message_stop"',
    'kind == "content_block_start"',
    'kind == "content_block_delta"',
    'kind == "content_block_stop"',
)
FINISH_ORDER = (
    "                if not saw_message_stop:",
    "                if started_tools and any(",
    "        tool_arguments: dict[int, dict[str, object]] = {}",
    "        blocks: list[object] = []",
    "        mapped_stop_reason = _STOP_REASONS.get(str(stop_reason or \"\"), \"stop\")",
    '        if str(stop_reason) == "refusal":',
    '        yield StreamEvent(type="done", reason=mapped_stop_reason, message=message)',
)
EXCEPTION_ORDER = (
    "        except StreamDeadlineExceeded:",
    "        except StreamAborted:",
    "        except StreamPumpCapacityExceeded:",
    "        except anthropic.APIConnectionError as exc:",
    "        except SDK_TRANSPORT_ERRORS as exc:",
    "        except anthropic.RateLimitError as exc:",
    "        except anthropic.APIStatusError as exc:",
    "        except OutputBudgetExceeded as exc:",
    "        except Exception as exc:  # noqa: BLE001",
)
# 四行既固定写法也固定先后：前缀摘要必须先于断点算完，断点只进入交给 SDK 的副本。
CACHE_ORDER = (
    '        prefix_digest = anthropic_prefix_digest(request.system, kwargs.get("tools"), kwargs["messages"])',
    "        task = request.task_context",
    '        if self.prompt_cache and task is not None and task.purpose == "turn":',
    "            kwargs = with_cache_breakpoints(kwargs)",
)
PROBES = (
    ("reset", RESET),
    ("private", PRIVATE),
    ("abort", ABORT),
    ("message_stop", MESSAGE_STOP),
    ("start", START),
    ("signature_start", SIGNATURE_START),
    ("redacted", REDACTED),
    ("fallback_block", FALLBACK_BLOCK),
    ("tool_start", TOOL_START),
    ("text_delta", TEXT_DELTA),
    ("thinking_delta", THINKING_DELTA),
    ("signature_delta", SIGNATURE_DELTA),
    ("input_delta", INPUT_DELTA),
    ("stop", STOP),
    ("ending", ENDING),
    ("tool_finish", TOOL_FINISH),
    ("usage", USAGE),
    ("deadline", DEADLINE),
    ("errors", ERRORS),
    ("request_path", REQUEST_PATH),
)
STOP_REASONS = (
    '    "end_turn": "stop",',
    '    "stop_sequence": "stop",',
    '    "tool_use": "tool_use",',
    '    "max_tokens": "length",',
    '    "pause_turn": "stop",',
    '    "refusal": "error",',
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
        if isinstance(node, ast.ClassDef) and node.name == "AnthropicProvider":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"anthropic_provider.py 缺少 AnthropicProvider.{name}")


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"Anthropic 流行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


class _FakeStream:
    def __init__(self, events: list, gate, gate_after: int) -> None:
        self.events = list(events)
        self.gate = gate
        self.gate_after = gate_after
        self.sent = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.gate is not None and self.sent >= self.gate_after:
            await self.gate.wait()
        if not self.events:
            raise StopAsyncIteration
        value = self.events.pop(0)
        self.sent += 1
        if isinstance(value, BaseException):
            raise value
        return value


class _FakeMessages:
    def __init__(self, holder: dict, label: str) -> None:
        self.holder = holder
        self.label = label

    async def create(self, **kwargs):
        self.holder["path"] = self.label
        self.holder["kwargs"] = kwargs
        return _FakeStream(self.holder["events"], self.holder.get("gate"),
                           int(self.holder.get("gate_after", 0)))


class _FakeBeta:
    def __init__(self, holder: dict) -> None:
        self.messages = _FakeMessages(holder, "beta")


class _FakeAsyncAnthropic:
    holder: dict = {}

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.default_headers = {"x-api-key": "secret-header", "user-agent": "ua",
                                "x-stainless-arch": "arm64", "anthropic-version": "2023-06-01"}
        self.messages = _FakeMessages(type(self).holder, "messages")
        self.beta = _FakeBeta(type(self).holder)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeAnthropic:
    def __init__(self, **kwargs) -> None:
        self.base_url = "https://api.test"
        self.api_key = kwargs.get("api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""
        self.auth_token = kwargs.get("auth_token") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or ""
        self.credentials = None
        self.default_headers = {"x-api-key": "secret-header", "user-agent": "ua",
                                "x-stainless-arch": "arm64", "anthropic-version": "2023-06-01"}
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _ApiError(Exception):
    pass


class _ApiStatusError(_ApiError):
    def __init__(self, message: str, *, status_code: int = 500, body=None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.response = None


class _RateLimitError(_ApiError):
    def __init__(self, message: str, *, body=None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = 429
        self.body = body
        self.response = None


class _ApiConnectionError(_ApiError):
    pass


def _install_fake_sdk() -> None:
    anthropic_provider.anthropic = types.SimpleNamespace(
        Anthropic=_FakeAnthropic, AsyncAnthropic=_FakeAsyncAnthropic,
        APIStatusError=_ApiStatusError, RateLimitError=_RateLimitError,
        APIConnectionError=_ApiConnectionError, APIError=_ApiError, omit=object())


def _request(**overrides) -> ModelRequest:
    values = {"model": "m1", "system": "sys", "messages": (UserMessage("hi"),)}
    values.update(overrides)
    return ModelRequest(**values)


def _run(events: list, *, fallback: bool = False, abort: bool = False,
         gate=None, gate_after: int = 0, timeout: int = 120,
         request: ModelRequest | None = None, cache: bool | None = None) -> tuple:
    _FakeAsyncAnthropic.holder.clear()
    _FakeAsyncAnthropic.holder.update(events=events, gate=gate, gate_after=gate_after)
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"}, clear=False):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        # 缺省不传开关，沿用配置默认值；只有显式关闭的用例才传。
        options = {} if cache is None else {"prompt_cache": cache}
        provider = anthropic_provider.AnthropicProvider(
            ModelConfig(provider="anthropic", model="m1", api_key=Secret("k"),
                        server_side_fallback=fallback, request_timeout_seconds=timeout, **options))
        if abort:
            provider._abort_requested = True
        result = list(provider._stream_once(request or _request()))
    return provider, result


def _types(result: list) -> list[str]:
    return [event.type for event in result]


def _done(result: list):
    if not result or result[-1].type != "done":
        raise ValueError(f"Anthropic 流行为变化 缺少终态：{[event.type for event in result]}")
    return result[-1]


def _last_error(result: list):
    if not result or result[-1].type != "error":
        raise ValueError(f"Anthropic 流行为变化 缺少错误终态：{[event.type for event in result]}")
    return result[-1]


def _blocks(result: list) -> list[tuple]:
    return [(type(block).__name__,
             getattr(block, "text", None),
             getattr(block, "thinking", None),
             getattr(block, "signature", None),
             getattr(block, "redacted_data", None),
             dict(block.arguments) if hasattr(block, "arguments") else None)
            for block in _done(result).message.blocks]


def _message_start(input_tokens=None, output_tokens=None) -> SimpleNamespace:
    usage = (None if input_tokens is None and output_tokens is None else
             SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens))
    return SimpleNamespace(type="message_start", message=SimpleNamespace(usage=usage))


def _message_delta(stop_reason=None, input_tokens=None, output_tokens=None) -> SimpleNamespace:
    usage = (None if input_tokens is None and output_tokens is None else
             SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens))
    return SimpleNamespace(type="message_delta",
                           delta=SimpleNamespace(stop_reason=stop_reason), usage=usage)


def _block(index: int, block) -> SimpleNamespace:
    return SimpleNamespace(type="content_block_start", index=index, content_block=block)


def _delta(index: int, delta) -> SimpleNamespace:
    return SimpleNamespace(type="content_block_delta", index=index, delta=delta)


def _block_stop(index: int) -> SimpleNamespace:
    return SimpleNamespace(type="content_block_stop", index=index)


def _message_stop() -> SimpleNamespace:
    return SimpleNamespace(type="message_stop")


def _text(value: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="text", text=value)


def _thinking(value: str = "", signature=None) -> SimpleNamespace:
    return SimpleNamespace(type="thinking", thinking=value, signature=signature)


def _tool(call_id="c1", name="boss_search", initial=None) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=call_id, name=name, input=initial)


def _text_delta(value: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="text_delta", text=value)


def _thinking_delta(value: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="thinking_delta", thinking=value)


def _signature_delta(value: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="signature_delta", signature=value)


def _input_delta(value: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="input_json_delta", partial_json=value)


def _check_structures() -> int:
    source = _read(MODULE)
    tree = _tree(MODULE)
    body = _method(tree, source, "_stream_once")
    checked = 0
    for name, fragments in PROBES:
        for fragment in fragments:
            if fragment not in body:
                raise ValueError(f"_stream_once 的 {name} 分支缺少：{fragment}")
            checked += 1
    for order in (CACHE_ORDER, EVENT_BRANCHES, FINISH_ORDER, EXCEPTION_ORDER):
        position = -1
        for fragment in order:
            index = body.find(fragment, position + 1)
            if index < 0:
                raise ValueError(f"_stream_once 的顺序缺少：{fragment}")
            position = index
            checked += 1
    for fragment in STOP_REASONS:
        if fragment not in source:
            raise ValueError(f"anthropic_provider.py 的停止原因映射缺少：{fragment}")
        checked += 1
    return checked


def _text_checks() -> int:
    checked = 0
    result = _run([_message_start(5), _block(0, _text("你")), _delta(0, _text_delta("好")),
                   _block_stop(0), _message_delta("end_turn", output_tokens=2), _message_stop()])[1]
    checked += _expect_value(_types(result),
                             ["start", "text_start", "text_delta", "text_delta", "text_end", "done"],
                             "文本流事件顺序")
    checked += _expect_value([event.delta for event in result if event.type == "text_delta"],
                             ["你", "好"], "初始文本与增量")
    checked += _expect_value([event.text for event in result if event.type == "text_end"],
                             ["你好"], "文本完成事件")
    checked += _expect_value(_blocks(result), [("TextBlock", "你好", None, None, None, None)],
                             "文本终态块")
    checked += _expect_value(_done(result).message.stop_reason, "stop", "文本终态原因")
    checked += _expect_value((_done(result).message.usage.input, _done(result).message.usage.output),
                             (5, 2), "两次上报的用量合并")

    for reason, expected in (("max_tokens", "length"), ("pause_turn", "stop"),
                             ("stop_sequence", "stop"), ("future_reason", "stop")):
        result = _run([_message_start(1), _message_delta(reason), _message_stop()])[1]
        checked += _expect_value(_done(result).message.stop_reason, expected, f"停止原因 {reason}")

    result = _run([_message_start(), _block(0, _text("a")), _delta(0, _text_delta("b")),
                   _block_stop(0), _message_delta("end_turn"), _message_stop()])[1]
    checked += _expect_value(_done(result).message.usage, None, "未上报用量不伪造零")

    result = _run([_message_start(3), _block(0, _text("")), _block_stop(0),
                   _message_delta("end_turn"), _message_stop()])[1]
    checked += _expect_value(_blocks(result), [("TextBlock", "", None, None, None, None)],
                             "空文本块保留")
    checked += _expect_value(_types(result).count("text_end"), 0, "空文本不发完成事件")
    checked += _expect_value(_done(result).message.usage, None, "只上报输入时不产生用量")
    return checked


def _thinking_checks() -> int:
    checked = 0
    result = _run([_message_start(1), _block(0, _thinking("想", "s1")),
                   _delta(0, _thinking_delta("更多")), _delta(0, _signature_delta("s1s2")),
                   _block_stop(0), _message_delta("end_turn", output_tokens=4), _message_stop()])[1]
    blocks = _blocks(result)
    checked += _expect_value(blocks[0][0], "ThinkingBlock", "思考终态块类型")
    checked += _expect_value(blocks[0][2], "想更多", "思考文本拼接")
    checked += _expect_value(blocks[0][3], "s1s2", "签名增量覆盖初始签名")
    checked += _expect_value([event.delta for event in result if event.type == "thinking_delta"],
                             ["想", "更多"], "思考增量事件")
    checked += _expect_value([event.text for event in result if event.type == "thinking_end"],
                             ["想更多"], "思考完成事件")
    checked += _expect_value(_done(result).message.blocks[0].prefix_digest is not None, True,
                             "思考块携带续接前缀摘要")

    result = _run([_message_start(1), _block(0, SimpleNamespace(type="redacted_thinking", data="cmVk")),
                   _block_stop(0), _message_delta("end_turn"), _message_stop()])[1]
    checked += _expect_value(_blocks(result),
                             [("ThinkingBlock", None, "", None, "cmVk", None)], "加密思考块")
    checked += _expect_value(_done(result).message.blocks[0].prefix_digest is not None, True,
                             "加密思考块携带续接前缀摘要")

    # 六个 16 KiB 签名正好用满 96 KiB 总量：同块重复上报同一签名只按差分计费，
    # 若把增量当绝对值，第六块的重复上报会越界。
    full = "x" * (16 * 1024)
    events = [_message_start(1)]
    for index in range(6):
        events.append(_block(index, _thinking("", full)))
        if index == 5:
            events.append(_delta(5, _signature_delta(full)))
        events.append(_block_stop(index))
    events += [_message_delta("end_turn"), _message_stop()]
    result = _run(events)[1]
    checked += _expect_value((_types(result)[-1], len(_done(result).message.blocks)),
                             ("done", 6), "签名总量按差分计费")
    return checked


def _call_checks() -> int:
    checked = 0
    result = _run([_message_start(1), _block(0, _tool()),
                   _delta(0, _input_delta('{"keyword"')), _delta(0, _input_delta(': "x"}')),
                   _block_stop(0), _message_delta("tool_use", output_tokens=6), _message_stop()])[1]
    checked += _expect_value([event.type for event in result],
                             ["start", "toolcall_start", "toolcall_delta", "toolcall_delta",
                              "toolcall_end", "done"], "工具调用事件顺序")
    checked += _expect_value([event.delta for event in result if event.type == "toolcall_delta"],
                             ['{"keyword"', ': "x"}'], "工具参数增量")
    checked += _expect_value(_blocks(result),
                             [("ToolCallBlock", None, None, None, None, {"keyword": "x"})],
                             "工具参数装配")
    checked += _expect_value(_done(result).message.stop_reason, "tool_use", "工具调用终态原因")
    end = [event for event in result if event.type == "toolcall_end"]
    checked += _expect_value((end[0].tool_call.id, end[0].tool_call.name), ("c1", "boss_search"),
                             "工具调用完成事件")

    result = _run([_message_start(1), _block(0, _tool(initial={"a": 1})), _block_stop(0),
                   _message_delta("tool_use"), _message_stop()])[1]
    checked += _expect_value(_blocks(result),
                             [("ToolCallBlock", None, None, None, None, {"a": 1})], "初始参数快照")
    checked += _expect_value(_types(result).count("toolcall_delta"), 0, "快照不产生参数增量")

    result = _run([_message_start(1), _block(0, _tool()), _block_stop(0),
                   _message_delta("tool_use"), _message_stop()])[1]
    checked += _expect_value(_blocks(result),
                             [("ToolCallBlock", None, None, None, None, {})], "无参数工具为空对象")

    result = _run([_message_start(1), _block(0, _tool()), _delta(0, _input_delta("{bad")),
                   _block_stop(0), _message_stop()])[1]
    checked += _expect_value(_last_error(result).error, "工具调用参数不是完整 JSON object：boss_search",
                             "坏参数不产生终态消息")

    result = _run([_message_start(1), _block(0, _tool()), _message_stop()])[1]
    checked += _expect_value(_last_error(result).error, "工具调用参数流未完整结束：boss_search",
                             "未关闭的工具不产生终态消息")
    return checked


def _terminal_checks() -> int:
    checked = 0
    result = _run([_message_start(1), _message_delta("refusal"), _message_stop()])[1]
    checked += _expect_value((_last_error(result).reason, _last_error(result).error),
                             ("error", "模型以安全原因拒绝"), "安全拒绝收敛为错误")
    checked += _expect_value("done" in _types(result), False, "安全拒绝不产生终态消息")

    result = _run([_message_start(1)], abort=True)[1]
    checked += _expect_value((_last_error(result).reason, _last_error(result).error),
                             ("aborted", "请求已取消"), "开始前取消")

    gate = asyncio.Event()
    _FakeAsyncAnthropic.holder.clear()
    _FakeAsyncAnthropic.holder.update(
        events=[_message_start(1), _block(0, _text()), _delta(0, _text_delta("a"))],
        gate=gate, gate_after=3)
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"}, clear=False):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        provider = anthropic_provider.AnthropicProvider(
            ModelConfig(provider="anthropic", model="m1", api_key=Secret("k")))
        seen = []
        for event in provider._stream_once(_request()):
            seen.append(event)
            if event.type == "text_delta":
                provider.request_abort()
                gate.set()
    checked += _expect_value((seen[-1].reason, seen[-1].error),
                             ("aborted", "请求已取消"), "中途取消")
    checked += _expect_value("done" in _types(seen), False, "中途取消不产生终态消息")

    started_provider, result = _run([_message_start(1)], gate=asyncio.Event(), gate_after=0,
                                    timeout=1)
    del started_provider
    checked += _expect_value(_last_error(result).reason, "error", "总时限错误原因")
    checked += _expect_value(_last_error(result).error.startswith("模型请求超过 1 秒总时限"), True,
                             "总时限错误文案")

    provider, _ = _run([_ApiStatusError("过载", status_code=529,
                                        body={"type": "error", "error": {"type": "overloaded_error",
                                                                          "message": "过载"}})])
    checked += _expect_value(provider._last_error_retryable, True, "可重试状态标记")
    provider, _ = _run([_message_start(1), _message_stop()])
    checked += _expect_value(provider._last_error_retryable, False, "每次尝试重置重试标记")
    return checked


def _error_checks() -> int:
    checked = 0
    result = _run([_ApiStatusError("过载", status_code=529,
                                   body={"type": "error", "error": {"type": "overloaded_error",
                                                                     "message": "过载"}})])[1]
    error = _last_error(result)
    checked += _expect_value(error.error, "接口错误 529：过载", "529 错误文案")
    checked += _expect_value((error.error_info.provider_code, error.error_info.retryable),
                             ("overloaded_error", True), "529 诊断信息")
    checked += _expect_value(_types(result), ["start", "error"], "状态错误终止流")

    result = _run([_ApiStatusError("坏了", status_code=400,
                                   body={"type": "error", "error": {"type": "invalid_request_error",
                                                                     "message": "坏了"}})])[1]
    checked += _expect_value(_last_error(result).error_info.retryable, False, "400 不可重试")

    result = _run([_RateLimitError("慢点", body={"type": "error",
                                                 "error": {"type": "rate_limit_error",
                                                           "message": "慢点"}})])[1]
    checked += _expect_value(_last_error(result).error, "被限流：慢点", "限流错误文案")
    checked += _expect_value(_last_error(result).error_info.retryable, True, "限流可重试")

    result = _run([_ApiConnectionError("断线")])[1]
    checked += _expect_value(_last_error(result).error, "连接失败：断线", "连接错误文案")
    checked += _expect_value(_last_error(result).error_info.source, "transport_error",
                             "连接错误来源")

    result = _run([RuntimeError("随便")])[1]
    checked += _expect_value(_last_error(result).error, "模型流处理异常（RuntimeError）",
                             "未知异常收敛")

    result = _run([_message_start(1), _block(0, _text()),
                   _delta(0, _text_delta("x" * (1024 * 1024 + 1))), _block_stop(0),
                   _message_stop()])[1]
    checked += _expect_value(_last_error(result).error,
                             "模型文本与思考输出超过本地 UTF-8 字节上限", "文本预算超限")

    result = _run([_message_start(1), _block(0, _tool()),
                   _delta(0, _input_delta("x" * (1024 * 1024 + 1))), _block_stop(0),
                   _message_stop()])[1]
    checked += _expect_value(_last_error(result).error, "工具参数超过本地字节上限", "工具预算超限")
    return checked


def _request_checks() -> int:
    checked = 0
    _, result = _run([_message_start(1), _message_delta("end_turn"), _message_stop()])
    checked += _expect_value(result[-1].type, "done", "默认路径完成")
    holder = _FakeAsyncAnthropic.holder
    checked += _expect_value(holder["path"], "messages", "默认走 messages.create")
    kwargs = holder["kwargs"]
    checked += _expect_value((kwargs["model"], kwargs["system"], kwargs["stream"]),
                             ("m1", "sys", True), "请求基本字段")
    checked += _expect_value(kwargs["messages"], [{"role": "user", "content": "hi"}],
                             "消息翻译")
    headers = kwargs["extra_headers"]
    checked += _expect_value(("x-api-key" in headers, "x-stainless-arch" in headers,
                              "user-agent" in headers),
                             (True, False, False), "请求头过滤")

    _, result = _run([_message_start(1), _message_delta("end_turn"), _message_stop()],
                     fallback=True)
    checked += _expect_value(result[-1].type, "done", "fallback 路径完成")
    kwargs = _FakeAsyncAnthropic.holder["kwargs"]
    checked += _expect_value(_FakeAsyncAnthropic.holder["path"], "beta", "fallback 走 beta 接口")
    checked += _expect_value((kwargs["betas"], kwargs["fallbacks"]),
                             (["server-side-fallback-2026-07-01"], "default"), "fallback 参数")

    _, result = _run([_message_start(1), _message_delta("end_turn"), _message_stop()],
                     request=_request(tools=(ToolSpec(name="boss_search", description="搜索",
                                                      input_schema={"type": "object"}),),
                                      thinking={"type": "enabled", "budget_tokens": 1024},
                                      effort="high"))
    kwargs = _FakeAsyncAnthropic.holder["kwargs"]
    checked += _expect_value(result[-1].type, "done", "带工具请求完成")
    checked += _expect_value(kwargs["tools"][0]["name"], "boss_search", "工具定义传递")
    checked += _expect_value(kwargs["thinking"], {"type": "enabled", "budget_tokens": 1024},
                             "思考配置传递")
    checked += _expect_value(kwargs["output_config"], {"effort": "high"}, "effort 传递")
    return checked


def _cache_checks() -> int:
    checked = 0
    ephemeral = {"type": "ephemeral"}
    turn = ModelTaskContext(purpose="turn", request_index=0)
    plain = ("sys", [{"role": "user", "content": "hi"}])
    marked = ([{"type": "text", "text": "sys", "cache_control": ephemeral}],
              [{"role": "user", "content": [{"type": "text", "text": "hi", "cache_control": ephemeral}]}])

    def captured(request: ModelRequest, events: list | None = None, **options) -> tuple:
        _, result = _run(events or [_message_start(1), _message_delta("end_turn"), _message_stop()],
                         request=request, **options)
        return dict(_FakeAsyncAnthropic.holder["kwargs"]), _done(result).message

    # 只有回合请求带断点：系统提示与末条 user 消息各一处；其余用途与关闭开关时保持原形状。
    turn_kwargs, _ = captured(_request(task_context=turn))
    checked += _expect_value((turn_kwargs["system"], turn_kwargs["messages"]), marked,
                             "回合请求在系统提示与末条消息各带一处断点")
    for label, purpose in (("摘要", "compaction"), ("连接检查", "connection_check")):
        kwargs, _ = captured(_request(task_context=ModelTaskContext(purpose=purpose, request_index=0)))
        checked += _expect_value((kwargs["system"], kwargs["messages"]), plain, f"{label}请求不带断点")
    kwargs, _ = captured(_request())
    checked += _expect_value((kwargs["system"], kwargs["messages"]), plain, "无任务上下文的请求不带断点")
    # 断点只写在内容块里：带断点的请求与不带断点的请求有同一组顶层参数。
    checked += _expect_value(sorted(turn_kwargs), sorted(kwargs), "断点不新增顶层参数")
    kwargs, _ = captured(_request(task_context=turn), cache=False)
    checked += _expect_value((kwargs["system"], kwargs["messages"]), plain, "关闭开关后回合请求不带断点")
    kwargs, _ = captured(_request(task_context=turn), fallback=True)
    checked += _expect_value(
        (_FakeAsyncAnthropic.holder["path"], kwargs["system"], kwargs["messages"]),
        ("beta", *marked), "beta 路径同样带断点")

    # 工具回合：断点落在最后一个工具结果上；更早的消息、工具定义与回放的思考块保持原样。
    tools = [{"name": "boss_search", "description": "搜索", "input_schema": {"type": "object"}}]
    replayed = ThinkingBlock(thinking="t", signature="s",
                             prefix_digest=anthropic_prefix_digest("sys", tools, plain[1]))
    history = (UserMessage("hi"),
               AssistantMessage((replayed, ToolCallBlock("c1", "boss_search", {"q": 1}),
                                 ToolCallBlock("c2", "boss_search", {"q": 2}))),
               ToolResultsMessage((ToolResultItem("c1", "ok"), ToolResultItem("c2", "bad", True))))
    earlier = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "t", "signature": "s"},
            {"type": "tool_use", "id": "c1", "name": "boss_search", "input": {"q": 1}},
            {"type": "tool_use", "id": "c2", "name": "boss_search", "input": {"q": 2}}]},
    ]
    first_result = {"type": "tool_result", "tool_use_id": "c1", "content": "ok"}
    last_result = {"type": "tool_result", "tool_use_id": "c2", "content": "bad", "is_error": True}
    request = _request(messages=history, task_context=turn,
                       tools=(ToolSpec(name="boss_search", description="搜索",
                                       input_schema={"type": "object"}),))
    thinking_events = [_message_start(1), _block(0, _thinking("想", "s1")), _block_stop(0),
                       _message_delta("end_turn"), _message_stop()]
    kwargs, message = captured(request, list(thinking_events))
    checked += _expect_value(
        kwargs["messages"],
        earlier + [{"role": "user", "content": [first_result, {**last_result, "cache_control": ephemeral}]}],
        "工具回合只标记最后一个工具结果")
    checked += _expect_value(kwargs["tools"], tools, "工具定义不带断点")
    # 续接：新思考块绑定的是不带断点的前缀，开关开闭得到同一个摘要，下一次请求才能回放。
    expected = anthropic_prefix_digest(
        "sys", tools, earlier + [{"role": "user", "content": [first_result, last_result]}])
    _, without = captured(request, list(thinking_events), cache=False)
    checked += _expect_value((message.blocks[0].prefix_digest, without.blocks[0].prefix_digest),
                             (expected, expected), "断点不进入思考块的前缀摘要")
    return checked


def _protocol_error_checks() -> int:
    checked = 0

    def fails(label: str, events: list) -> int:
        result = _run(events)[1]
        error = _last_error(result)
        return _expect_value((error.error, "done" in _types(result)),
                             ("模型流处理异常（ValueError）", False), label)

    checked += fails("重复内容块索引", [_message_start(1), _block(0, _text()), _block(0, _text()),
                                        _block_stop(0), _message_stop()])
    checked += fails("重复关闭内容块", [_message_start(1), _block(0, _text()),
                                        _block_stop(0), _block_stop(0), _message_stop()])
    checked += fails("文本增量错置到思考块", [_message_start(1), _block(0, _thinking()),
                                              _delta(0, _text_delta("x")), _block_stop(0),
                                              _message_stop()])
    checked += fails("无活动文本块", [_message_start(1), _delta(0, _text_delta("x")),
                                      _message_stop()])
    checked += fails("思考增量错置到文本块", [_message_start(1), _block(0, _text()),
                                              _delta(0, _thinking_delta("x")), _block_stop(0),
                                              _message_stop()])
    checked += fails("签名增量无活动思考块", [_message_start(1), _block(0, _text()),
                                              _delta(0, _signature_delta("s")), _block_stop(0),
                                              _message_stop()])
    checked += fails("空签名增量", [_message_start(1), _block(0, _thinking()),
                                    _delta(0, _signature_delta("")), _block_stop(0),
                                    _message_stop()])
    checked += fails("参数增量无活动工具块", [_message_start(1), _delta(0, _input_delta("x")),
                                              _message_stop()])
    checked += fails("快照与增量冲突", [_message_start(1), _block(0, _tool(initial={"a": 1})),
                                        _delta(0, _input_delta('{"a": 2}')), _block_stop(0),
                                        _message_stop()])
    checked += fails("加密思考块为空", [_message_start(1),
                                        _block(0, SimpleNamespace(type="redacted_thinking", data="")),
                                        _block_stop(0), _message_stop()])
    checked += fails("服务端 fallback 块", [_message_start(1),
                                            _block(0, SimpleNamespace(type="fallback")),
                                            _block_stop(0), _message_stop()])
    checked += fails("工具标识为空", [_message_start(1), _block(0, _tool(call_id="")),
                                      _block_stop(0), _message_stop()])
    checked += fails("工具标识重复", [_message_start(1), _block(0, _tool(call_id="c1")),
                                      _block_stop(0), _block(1, _tool(call_id="c1")),
                                      _block_stop(1), _message_stop()])
    checked += fails("工具名称为空", [_message_start(1), _block(0, _tool(name="")),
                                      _block_stop(0), _message_stop()])
    checked += fails("初始参数不是对象", [_message_start(1), _block(0, _tool(initial=[1, 2])),
                                          _block_stop(0), _message_stop()])
    checked += fails("初始签名超过预算",
                     [_message_start(1), _block(0, _thinking("", "x" * (16 * 1024 + 1))),
                      _block_stop(0), _message_stop()])
    checked += fails("加密思考块超过预算",
                     [_message_start(1), _block(0, SimpleNamespace(type="redacted_thinking",
                                                                   data="x" * (16 * 1024 + 1))),
                      _block_stop(0), _message_stop()])
    checked += fails("message_stop 之后仍有事件", [_message_start(1), _message_stop(),
                                                   _message_stop()])
    checked += fails("缺少 message_stop", [_message_start(1), _block(0, _text()),
                                            _delta(0, _text_delta("x")), _block_stop(0)])
    checked += fails("工具响应缺少思考签名",
                     [_message_start(1), _block(0, _thinking("想")), _block_stop(0),
                      _block(1, _tool(initial={})), _block_stop(1), _message_stop()])
    return checked


def _behavior_checks() -> int:
    _install_fake_sdk()
    checked = 0
    checked += _text_checks()
    checked += _thinking_checks()
    checked += _call_checks()
    checked += _terminal_checks()
    checked += _error_checks()
    # 排在请求路径之前：断点用途判定出错时由这里的用例报告，而不是由基本字段的用例顺带发现。
    checked += _cache_checks()
    checked += _request_checks()
    checked += _protocol_error_checks()
    return checked


def check_anthropic_stream() -> tuple[int, int]:
    return _check_structures(), _behavior_checks()


def main() -> int:
    try:
        structures, behaviors = check_anthropic_stream()
    except ValueError as error:
        print(f"Anthropic 流状态机核对失败，{error}", file=sys.stderr)
        return 2
    print(f"Anthropic 流状态机一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
