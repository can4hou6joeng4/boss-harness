#!/usr/bin/env python3
"""核对 OpenAI Responses 流状态机的工具身份、终态集合与错误收敛。

`OpenAIResponsesProvider._stream_once` 把 SDK 的原始事件流映射成 StreamEvent：
输出项标识与 `call_id` 必须在起始、参数事件、完成项与终态响应之间保持一致；
终态响应是权威集合，流中出现但被撤回的块不能进入最终消息；参数以 `done` 事件
为准且只补发后缀；协议错误必须收敛成 `error` 事件，不能把异常抛给调用方。

这里用假的 `openai` 客户端驱动真实 `_stream_once`（不联网、不调用模型），
逐类验证身份校验、增量归属、参数缓冲、坏 JSON 收敛、撤回块过滤、终态原因与
错误事件文案；同时静态固定状态机的关键拒绝分支与收尾顺序。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import types
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/openai_responses.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.models import openai_responses  # noqa: E402
from boss_harness.models import ModelConfig  # noqa: E402
from boss_harness.models.secret import Secret  # noqa: E402
from boss_harness.models.types import ModelRequest, UserMessage  # noqa: E402

IDENTITY = (
    '            raw_item_id = getattr(item, "id", None)',
    "            identity = (",
    "            if not all(identity[1:]):",
    '                raise ValueError("工具调用缺少 call_id 或工具名")',
    "            if len(identity[1]) > 256 or len(identity[2]) > 256:",
    '                raise ValueError("工具调用标识或名称超过长度上限")',
)
REQUIRE_IDENTITY = (
    "            actual = function_call_identity(item)",
    "            expected = function_call_identities.get(index)",
    "            if expected is None or expected[1:] != actual[1:]:",
    '                raise ValueError("工具调用身份与初始输出项不一致")',
    "            if expected[0] and actual[0] and expected[0] != actual[0]:",
    '                raise ValueError("工具调用输出项标识不一致")',
    '                    raise ValueError("响应重复使用输出项标识")',
    "            function_call_identities[index] = identity",
)
REQUIRE_EVENT_ID = (
    '            event_item_id = getattr(event, "item_id", None)',
    "            if not isinstance(event_item_id, str) or not event_item_id:",
    '                raise ValueError("工具参数事件缺少输出项标识")',
    "            if identity is None or (identity[0] and event_item_id != identity[0]):",
    '                raise ValueError("工具参数事件的输出项标识不一致")',
    '                raise ValueError("工具参数事件重复使用输出项标识")',
)
ADDED = (
    '                    if kind == "response.output_item.added":',
    "                        if item_id:",
    "                            if item_id in item_ids:",
    '                                raise ValueError("响应重复使用输出项标识")',
    "                            if claimed is not None and claimed != item_type:",
    '                                raise ValueError("响应重复使用输出项索引")',
    "                            if index in closed_output_indexes:",
    '                                raise ValueError("输出项关闭后仍收到起始事件")',
)
FUNCTION_ADDED = (
    '                        elif item_type == "function_call":',
    "                            if index in started_function_calls:",
    '                                raise ValueError("响应重复使用工具调用索引")',
    '                                raise ValueError("工具调用初始项缺少 call_id 或工具名")',
    '                                raise ValueError("工具调用初始项标识或名称超过长度上限")',
    "                            if identity[1] in call_id_indexes:",
    '                                raise ValueError("响应重复使用工具调用 call_id")',
    '                                raise ValueError("工具调用初始参数不是文本")',
)
DELTA_GUARDS = (
    '                            if claimed not in (None, "reasoning") or index in closed_output_indexes:',
    '                                raise ValueError("思考增量没有对应的活动思考项")',
    '                            if claimed not in (None, "message") or index in closed_output_indexes:',
    '                                raise ValueError("文本增量没有对应的活动消息项")',
)
ARGUMENT_DELTA = (
    "                        if index not in started_function_calls or index in final_items_seen:",
    '                        raise ValueError("工具参数增量没有活动的工具调用")',
    '                            raise ValueError("工具调用参数终态之后仍收到增量")',
    '                            raise ValueError("工具调用参数增量不是文本")',
)
ARGUMENT_DONE = (
    "                        if index not in started_function_calls or index in arguments_done or index in final_items_seen:",
    '                        raise ValueError("工具参数终态没有对应的活动工具调用")',
    "                                delta=authoritative[len(previous):],",
)
ITEM_DONE = (
    '                                raise ValueError("响应输出项类型与起始事件不一致")',
    "                            if item_index in closed_output_indexes:",
    '                                raise ValueError("响应重复关闭输出项")',
    '                                raise ValueError("工具调用终态没有对应的唯一初始项")',
)
TERMINAL = (
    '                            raise ValueError("响应终态缺少 response 对象")',
    "                        if terminal_output is None:",
    '                            raise ValueError("响应终态缺少 output 集合")',
    '                                    raise ValueError("响应终态重复使用输出项标识")',
    '                                raise ValueError("响应终态重复使用输出项索引")',
    '                                raise ValueError("响应终态输出项类型与流事件不一致")',
    '                                raise ValueError("工具调用缺少完整的 output_item.done 事件")',
    '                                    raise ValueError("响应中的工具参数终态来源冲突")',
)
ENDING = (
    "                if started_function_calls != final_items_seen:",
    '                    raise ValueError("工具调用缺少完整的 output_item.done 事件")',
    "            blocks = {index: block for index, block in blocks.items() if index in terminal_indexes}",
    "        if not error_message and unfinished:",
    "            error_message = f\"工具调用参数不完整：{'、'.join(unfinished)}\"",
    '            _stop_reason(terminal, has_tool_calls=bool(calls)) if terminal is not None else ("error", "流在没有终态响应前结束")',
)
GUARD = (
    "        except Exception as exc:  # noqa: BLE001",
    '                error=f"模型流处理异常（{type(exc).__name__}）",',
)
PROBES = (
    ("function_call_identity", IDENTITY),
    ("require_function_call_identity", REQUIRE_IDENTITY),
    ("require_event_item_id", REQUIRE_EVENT_ID),
    ("added", ADDED),
    ("function_added", FUNCTION_ADDED),
    ("delta_guards", DELTA_GUARDS),
    ("argument_delta", ARGUMENT_DELTA),
    ("argument_done", ARGUMENT_DONE),
    ("item_done", ITEM_DONE),
    ("terminal", TERMINAL),
    ("ending", ENDING),
    ("guard", GUARD),
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
        if isinstance(node, ast.ClassDef) and node.name == "OpenAIResponsesProvider":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"openai_responses.py 缺少 OpenAIResponsesProvider.{name}")


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"OpenAI 流行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


class _FakeStream:
    def __init__(self, events: list) -> None:
        self.events = list(events)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


class _FakeResponses:
    def __init__(self, holder: dict) -> None:
        self.holder = holder

    async def create(self, **kwargs):
        return _FakeStream(self.holder["events"])


class _FakeClient:
    def __init__(self, holder: dict, **kwargs) -> None:
        self.responses = _FakeResponses(holder)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeOpenAI:
    holder: dict = {}

    def __new__(cls, **kwargs):
        return _FakeClient(cls.holder)


class _APIError(Exception):
    pass


class _APIStatusError(_APIError):
    pass


class _APIConnectionError(_APIError):
    pass


def _install_fake_sdk() -> None:
    openai_responses.openai = types.SimpleNamespace(
        AsyncOpenAI=_FakeOpenAI, APIError=_APIError,
        APIStatusError=_APIStatusError, APIConnectionError=_APIConnectionError)


def _run(events: list, *, abort: bool = False) -> list:
    _FakeOpenAI.holder["events"] = events
    provider = openai_responses.OpenAIResponsesProvider(
        ModelConfig(provider="openai", model="m1", api_key=Secret("k")))
    if abort:
        provider._abort_requested = True
    request = ModelRequest(model="m1", system="sys", messages=(UserMessage("hi"),))
    return list(provider._stream_once(request))


def _types(result: list) -> list[str]:
    return [event.type for event in result]


def _done(result: list):
    if not result or result[-1].type != "done":
        raise ValueError(f"OpenAI 流行为变化 缺少终态：{[event.type for event in result]}")
    return result[-1]


def _last_error(result: list):
    if not result or result[-1].type != "error":
        raise ValueError(f"OpenAI 流行为变化 缺少错误终态：{[event.type for event in result]}")
    return result[-1]


def _blocks(result: list) -> list[tuple]:
    message = _done(result).message
    return [(type(block).__name__,
             getattr(block, "text", None),
             getattr(block, "thinking", None),
             dict(block.arguments) if hasattr(block, "arguments") else None)
            for block in message.blocks]


def _message(item_id: str, text: str | None = None) -> SimpleNamespace:
    content = [] if text is None else [SimpleNamespace(text=text)]
    return SimpleNamespace(type="message", id=item_id, content=content)


def _reasoning(item_id: str, parts: tuple[str, ...] = ()) -> SimpleNamespace:
    return SimpleNamespace(type="reasoning", id=item_id, summary=[SimpleNamespace(text=part) for part in parts])


def _call(item_id: str, call_id: str, name: str, arguments: str = "") -> SimpleNamespace:
    return SimpleNamespace(type="function_call", id=item_id, call_id=call_id, name=name, arguments=arguments)


def _added(index: int, item) -> SimpleNamespace:
    return SimpleNamespace(type="response.output_item.added", output_index=index, item=item)


def _item_done(index: int, item) -> SimpleNamespace:
    return SimpleNamespace(type="response.output_item.done", output_index=index, item=item)


def _terminal(output: list, *, kind: str = "response.completed", status: str = "completed",
              usage=None, **extra) -> SimpleNamespace:
    response = SimpleNamespace(status=status, output=output, usage=usage, **extra)
    return SimpleNamespace(type=kind, response=response)


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
    for order in (
        ("def function_call_identity(", "def require_function_call_identity(", "def require_event_item_id("),
        ('kind == "response.output_item.added"', 'kind in _THINKING_DELTA_EVENTS',
         'kind in _TEXT_DELTA_EVENTS', 'kind == "response.function_call_arguments.delta"',
         'kind == "response.function_call_arguments.done"', 'kind == "response.output_item.done"',
         'kind in ("response.completed", "response.incomplete")'),
    ):
        position = -1
        for fragment in order:
            index = body.find(fragment, position + 1)
            if index < 0:
                raise ValueError(f"_stream_once 的事件顺序缺少：{fragment}")
            position = index
            checked += 1
    for fragment in ('_TEXT_DELTA_EVENTS = ("response.output_text.delta", "response.refusal.delta")',
                     '_THINKING_DELTA_EVENTS = ("response.reasoning_summary_text.delta", "response.reasoning_text.delta")'):
        if fragment not in source:
            raise ValueError(f"openai_responses.py 缺少事件白名单：{fragment}")
        checked += 1
    return checked


def _text_checks() -> int:
    checked = 0
    message = _message("m1", "你好")
    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="你好"),
                   _item_done(0, message),
                   _terminal([message])])
    types_seen = _types(result)
    checked += _expect_value(types_seen[0], "start", "文本流以 start 开始")
    checked += _expect_value("text_start" in types_seen and "text_delta" in types_seen, True, "文本流发出增量事件")
    checked += _expect_value(types_seen[-1], "done", "文本流以 done 结束")
    checked += _expect_value(_blocks(result), [("TextBlock", "你好", None, None)], "文本终态块")
    checked += _expect_value(_done(result).message.stop_reason, "stop", "文本终态原因")

    authoritative = _message("m1", "最终")
    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="旧"),
                   _item_done(0, authoritative),
                   _terminal([authoritative])])
    checked += _expect_value(_blocks(result), [("TextBlock", "最终", None, None)], "完成项文本优先于增量")

    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="a"),
                   _item_done(0, _message("m1", "a")),
                   _terminal([])])
    checked += _expect_value(_blocks(result), [], "撤回的块不进入终态")

    empty = _message("m1")
    result = _run([_added(0, empty), _item_done(0, empty), _terminal([empty])])
    checked += _expect_value(_blocks(result), [("TextBlock", "", None, None)], "空文本保留空块")
    checked += _expect_value(_types(result).count("text_delta"), 0, "空文本不发增量")

    refusal = SimpleNamespace(type="message", id="m1", content=[SimpleNamespace(refusal="拒绝")])
    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.refusal.delta", output_index=0, delta="拒绝"),
                   _item_done(0, refusal),
                   _terminal([refusal])])
    checked += _expect_value(_blocks(result), [("TextBlock", "拒绝", None, None)], "拒答文本按文本块")
    checked += _expect_value([event.delta for event in result if event.type == "text_delta"], ["拒绝"],
                             "拒答增量进入文本流")

    checked += _expect_value(_types(_run([SimpleNamespace(type="response.output_text.delta", output_index=1, delta="x")])),
                             ["start", "text_delta", "error"], "未知输出项的增量按活动项接受")
    return checked


def _thinking_checks() -> int:
    checked = 0
    partial = _reasoning("r1", ("第一段",))
    complete = _reasoning("r1", ("第一段", "第二段"))
    result = _run([_added(0, _reasoning("r1")),
                   SimpleNamespace(type="response.reasoning_summary_text.delta", output_index=0, delta="第一段"),
                   SimpleNamespace(type="response.reasoning_summary_part.done", output_index=0),
                   SimpleNamespace(type="response.reasoning_summary_text.delta", output_index=0, delta="第二段"),
                   _item_done(0, partial),
                   _terminal([complete])])
    checked += _expect_value(_blocks(result), [("ThinkingBlock", None, "第一段\n\n第二段", None)], "思考终态文本")
    checked += _expect_value([event.delta for event in result if event.type == "thinking_delta"],
                             ["第一段", "\n\n", "第二段"], "思考段落分隔延后")
    ends = [event.text for event in result if event.type == "thinking_end"]
    checked += _expect_value(ends[-1], "第一段\n\n第二段", "思考完成事件文本")
    return checked


def _call_checks() -> int:
    checked = 0
    final = _call("fc1", "call1", "boss_search", '{"keyword": "x"}')
    result = _run([_added(0, _call("fc1", "call1", "boss_search")),
                   SimpleNamespace(type="response.function_call_arguments.delta", output_index=0,
                                   item_id="fc1", delta='{"keyword"'),
                   SimpleNamespace(type="response.function_call_arguments.delta", output_index=0,
                                   item_id="fc1", delta=': "x"}'),
                   _item_done(0, final),
                   _terminal([final])])
    checked += _expect_value(_blocks(result), [("ToolCallBlock", None, None, {"keyword": "x"})], "工具调用终态块")
    checked += _expect_value(_done(result).message.stop_reason, "tool_use", "工具调用终态原因")
    checked += _expect_value([event.delta for event in result if event.type == "toolcall_delta"],
                             ['{"keyword"', ': "x"}'], "工具参数增量")
    checked += _expect_value(_done(result).message.tool_calls()[0].id, "call1", "工具调用使用 call_id")

    authoritative = _call("fc1", "c1", "n", '{"a": 1}')
    result = _run([_added(0, _call("fc1", "c1", "n")),
                   SimpleNamespace(type="response.function_call_arguments.delta", output_index=0,
                                   item_id="fc1", delta='{"a"'),
                   SimpleNamespace(type="response.function_call_arguments.done", output_index=0,
                                   item_id="fc1", arguments='{"a": 1}'),
                   _item_done(0, authoritative),
                   _terminal([authoritative])])
    checked += _expect_value([event.delta for event in result if event.type == "toolcall_delta"],
                             ['{"a"', ': 1}'], "参数终态只补新增后缀")
    checked += _expect_value(_blocks(result), [("ToolCallBlock", None, None, {"a": 1})], "参数终态权威")

    result = _run([_added(0, _call("fc1", "c1", "n")),
                   _item_done(0, _call("fc1", "c1", "n", '{"b": 2}')),
                   _terminal([_call("fc1", "c1", "n", '{"b": 2}')])])
    checked += _expect_value(_blocks(result), [("ToolCallBlock", None, None, {"b": 2})], "完成项参数作为来源")

    empty = _call("fc1", "c1", "n")
    result = _run([_added(0, _call("fc1", "c1", "n")), _item_done(0, empty), _terminal([empty])])
    checked += _expect_value(_blocks(result), [("ToolCallBlock", None, None, {})], "无参工具参数为空对象")

    broken = _call("fc1", "c1", "n", "{bad")
    result = _run([_added(0, _call("fc1", "c1", "n")),
                   SimpleNamespace(type="response.function_call_arguments.delta", output_index=0,
                                   item_id="fc1", delta="{bad"),
                   _item_done(0, broken),
                   _terminal([broken])])
    checked += _expect_value(_last_error(result).error, "工具调用参数不完整：n", "坏参数不产生终态消息")

    conflict = _call("fc1", "c1", "n", '{"b": 2}')
    result = _run([_added(0, _call("fc1", "c1", "n")),
                   SimpleNamespace(type="response.function_call_arguments.done", output_index=0,
                                   item_id="fc1", arguments='{"a": 1}'),
                   _item_done(0, conflict),
                   _terminal([conflict])])
    checked += _expect_value(_last_error(result).error, "工具调用参数不完整：n", "参数来源冲突不产生终态消息")
    return checked


def _terminal_checks() -> int:
    checked = 0
    message = _message("m1", "a")
    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="a"),
                   _terminal([message], kind="response.incomplete", status="incomplete",
                             incomplete_details=SimpleNamespace(reason="max_output_tokens"))])
    checked += _expect_value(_done(result).message.stop_reason, "length", "长度截断终态原因")
    checked += _expect_value(_blocks(result), [("TextBlock", "a", None, None)], "截断仍保留已收文本")

    usage = SimpleNamespace(input_tokens=5, output_tokens=2)
    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="a"),
                   _item_done(0, message),
                   _terminal([message], usage=usage)])
    checked += _expect_value((result[-1].message.usage.input, result[-1].message.usage.output),
                             (5, 2), "终态用量映射")

    result = _run([_added(0, _message("m1")),
                   SimpleNamespace(type="response.output_text.delta", output_index=0, delta="a")])
    checked += _expect_value(_last_error(result).error, "流在没有终态响应前结束", "缺终态收敛为错误")

    result = _run([], abort=True)
    checked += _expect_value((_last_error(result).reason, _last_error(result).error),
                             ("aborted", "请求已取消"), "中止收敛为错误")

    result = _run([SimpleNamespace(type="response.failed", response=SimpleNamespace(
        error=SimpleNamespace(code="server_error", type="service_unavailable_error", message="过载了")))])
    checked += _expect_value(_last_error(result).error, "接口错误 server_error：过载了", "流内失败事件")

    result = _run([SimpleNamespace(type="error", code="server_error", message="temporarily unavailable")])
    checked += _expect_value(_last_error(result).error, "接口错误 server_error：temporarily unavailable",
                             "流内错误事件")
    return checked


def _protocol_error_checks() -> int:
    checked = 0

    def fails(label: str, events: list) -> int:
        result = _run(events)
        error = _last_error(result)
        return _expect_value((error.error, "done" in _types(result)),
                             ("模型流处理异常（ValueError）", False), label)

    checked += fails("完成项身份不一致", [
        _added(0, _call("fc1", "c1", "n")),
        _item_done(0, _call("fc1", "c2", "n", "{}"))])
    checked += fails("重复输出项标识", [
        _added(0, _message("m1")), _added(1, _message("m1"))])
    checked += fails("重复输出项索引", [
        _added(0, _message("m1")), _added(0, _reasoning("r1"))])
    checked += fails("关闭后起始事件", [
        _added(0, _message("m1")), _item_done(0, _message("m1")), _added(0, _message("m2"))])
    checked += fails("思考增量错置", [
        _added(0, _message("m1")),
        SimpleNamespace(type="response.reasoning_summary_text.delta", output_index=0, delta="x")])
    checked += fails("参数增量无活动调用", [
        SimpleNamespace(type="response.function_call_arguments.delta", output_index=0, item_id="fc1", delta="x")])
    checked += fails("参数终态后增量", [
        _added(0, _call("fc1", "c1", "n")),
        SimpleNamespace(type="response.function_call_arguments.done", output_index=0, item_id="fc1", arguments="{}"),
        SimpleNamespace(type="response.function_call_arguments.delta", output_index=0, item_id="fc1", delta="x")])
    checked += fails("重复关闭输出项", [
        _added(0, _message("m1")), _item_done(0, _message("m1")), _item_done(0, _message("m1"))])
    checked += fails("重复 call_id", [
        _added(0, _call("fc1", "c1", "n")), _added(1, _call("fc2", "c1", "n"))])
    checked += fails("重复工具调用索引", [
        _added(0, _call("fc1", "c1", "n")), _added(0, _call("fc2", "c2", "n"))])
    checked += fails("终态缺少 response 对象", [
        SimpleNamespace(type="response.completed", response=None)])
    checked += fails("终态缺少 output 集合", [
        SimpleNamespace(type="response.completed", response=SimpleNamespace(status="completed", output=None))])
    checked += fails("终态之后仍收到事件", [
        _terminal([_message("m1", "a")]),
        SimpleNamespace(type="response.output_text.delta", output_index=0, delta="x")])
    checked += fails("终态输出项类型与流事件不一致", [
        _added(0, _reasoning("r1")),
        _terminal([_message("r1", "x")])])
    checked += fails("终态重复使用输出项标识", [
        _terminal([_message("m1", "a"), _message("m1", "b")])])
    checked += fails("工具调用缺少完成项", [
        _added(0, _call("fc1", "c1", "n")),
        _terminal([_call("fc1", "c1", "n", "{}")])])
    return checked


def _behavior_checks() -> int:
    _install_fake_sdk()
    checked = 0
    checked += _text_checks()
    checked += _thinking_checks()
    checked += _call_checks()
    checked += _terminal_checks()
    checked += _protocol_error_checks()
    return checked


def check_openai_stream() -> tuple[int, int]:
    return _check_structures(), _behavior_checks()


def main() -> int:
    try:
        structures, behaviors = check_openai_stream()
    except ValueError as error:
        print(f"OpenAI 流状态机核对失败，{error}", file=sys.stderr)
        return 2
    print(f"OpenAI 流状态机一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
