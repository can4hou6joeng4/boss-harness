#!/usr/bin/env python3
"""核对上下文规模估算、请求指纹、成功用量校准与消息组装口径。

`_message_size` 逐类型累加正文、思考签名、脱敏数据、工具调用与工具结果，
并为每条消息加固定开销；`estimate_tokens` 以字符数的一半作为保守估算。
`_usage_input_tokens` 只接受当前 provider 的非负整数字段，并受单请求上限
约束；`request_fingerprint` 覆盖模型、系统提示、消息、工具、输出预算、
推理档位与思考配置；`_retained_usage_estimate` 只用已验证前缀的成功用量
校准逐条估算；`messages_from_items` 把持久条目还原为模型请求，过滤未完成、
空正文与续接来源的助手消息，按 `toolBatchId` 分组工具调用并降级孤立代理项。
这里既按源码顺序固定这些边界，也直接调用上述函数核对计数、指纹、组装与
校准结果。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = "harness/src/boss_harness/context.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.context import (  # noqa: E402
    _json_size,
    _message_fingerprint_payload,
    _message_size,
    _retained_usage_estimate,
    _usage_input_tokens,
    estimate_tokens,
    messages_from_items,
    request_fingerprint,
)
from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    ModelRequest,
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
    ToolResultItem,
    ToolResultsMessage,
    ToolSpec,
    UserMessage,
)
from boss_harness.usage import MAX_REQUEST_TOKENS  # noqa: E402

JSON_ORDER = (
    "def _json_size(value: Any) -> int:",
    "return len(json.dumps(value, ensure_ascii=False))",
)
MESSAGE_ORDER = (
    "def _message_size(messages: tuple[ChatMessage, ...] | list[ChatMessage]) -> int:",
    "size = 0",
    "for message in messages:",
    "if isinstance(message, UserMessage):",
    "size += len(message.text)",
    "elif isinstance(message, AssistantMessage):",
    "for block in message.blocks:",
    "if isinstance(block, TextBlock):",
    "elif isinstance(block, ThinkingBlock):",
    "size += len(block.thinking)",
    "if block.signature is not None:",
    "size += len(block.signature)",
    "if block.redacted_data is not None:",
    "size += len(block.redacted_data)",
    "elif isinstance(block, ToolCallBlock):",
    "size += len(block.id) + len(block.name) + _json_size(dict(block.arguments))",
    "else:",
    "size += sum(len(result.content) + len(result.tool_call_id) for result in message.results)",
    "size += 32",
)
MESSAGES_ORDER = (
    "def messages_from_items(items: list[dict],",
    'write_tools: frozenset[str] = frozenset({"boss_hr_greet"})) -> tuple[ChatMessage, ...]:',
    "marker = item.get(ANTHROPIC_CONTINUATION_FIELD)",
    'batch_assistant_id = item.get("toolBatchAssistantItemId")',
    "content=wire_text(model_result_for_item(p, write_tools=write_tools)),",
    'is_error=p.get("status") == "failed") for p in pending)))',
    'if kind != "toolCall" or (pending and item.get("toolBatchId") != batch):',
    'if isinstance(item.get("text"), str):',
    'and not _is_one_of(item.get("id"), continuation_agent_ids)):',
    'elif kind == "toolCall" and item.get("status") != "running":',
)
ESTIMATE_ORDER = (
    'def estimate_tokens(messages: tuple[ChatMessage, ...] | list[ChatMessage], system: str = "") -> int:',
    "A conservative character estimate, not a vendor tokenizer or billing value.",
    "size = len(system) + _message_size(messages)",
    "return (size + 1) // 2",
)
USAGE_ORDER = (
    "def _usage_input_tokens(provider: str, usage: Any) -> int | None:",
    "if not isinstance(usage, dict):",
    "return None",
    'names = ("input",) if provider == "openai" else ("input", "cache_read", "cache_write") if provider == "anthropic" else ()',
    "if not names:",
    "values = [usage.get(name) for name in names]",
    "if any(type(value) is not int or value < 0 for value in values):",
    "total = sum(values)",
    "return total if 0 < total <= MAX_REQUEST_TOKENS else None",
)
FINGERPRINT_ORDER = (
    "def request_fingerprint(provider: str, request: ModelRequest) -> str:",
    'payload = {"provider": provider, "model": request.model, "system": request.system,',
    '"messages": [_message_fingerprint_payload(message) for message in request.messages],',
    '"tools": [{"name": tool.name, "description": tool.description,',
    '"inputSchema": dict(tool.input_schema)} for tool in request.tools],',
    '"maxTokens": request.max_tokens, "effort": request.effort,',
    '"thinking": dict(request.thinking) if request.thinking is not None else None}',
    "encoded = _canonical_json_bytes(payload)",
    "return hashlib.sha256(encoded).hexdigest()",
)
PAYLOAD_ORDER = (
    "def _message_fingerprint_payload(message: ChatMessage) -> dict[str, Any]:",
    'return {"role": "user", "text": message.text}',
    "if isinstance(message, AssistantMessage):",
    "blocks = []",
    'blocks.append({"type": "text", "text": block.text})',
    'blocks.append({"type": "thinking", "text": block.thinking})',
    'blocks[-1]["signature"] = block.signature',
    'blocks[-1]["redactedData"] = block.redacted_data',
    'blocks[-1]["prefixDigest"] = block.prefix_digest',
    'blocks.append({"type": "toolCall", "id": block.id, "name": block.name,',
    '"arguments": dict(block.arguments)})',
    'return {"role": "assistant", "blocks": blocks}',
    'return {"role": "toolResults", "results": [',
    '{"toolCallId": result.tool_call_id, "content": result.content, "isError": result.is_error}',
)
RETAINED_ORDER = (
    "def _retained_usage_estimate(provider: str, request: ModelRequest, entries: list[dict], *,",
    "messages: list[ChatMessage], owners: list[str | None]",
    ") -> tuple[dict[int, int], list[tuple[int, int]]]:",
    "fallback = {index: (_message_size([message]) + 1) // 2",
    "if len(owners) != len(messages):",
    "return fallback, []",
    'if entry.get("type") != "model_usage":',
    'anchor = entry.get("payload")',
    'if (not isinstance(anchor, dict) or anchor.get("provider") != provider',
    'or anchor.get("model") != request.model or anchor.get("eligible") is not True):',
    'count = anchor.get("messageCount")',
    'fingerprint = anchor.get("requestFingerprint")',
    "if type(count) is not int or not 0 <= count <= len(messages) or count > len(request.messages) \\",
    "or not isinstance(fingerprint, str):",
    "if tuple(request.messages[:count]) != tuple(messages[:count]):",
    "prefix = replace(request, messages=request.messages[:count])",
    "if request_fingerprint(provider, prefix) != fingerprint:",
    'usage = _usage_input_tokens(provider, anchor.get("usage"))',
    "if usage is None:",
    "if count in anchors and anchors[count] != usage:",
    "conflicts = True",
    "break",
    "anchors.clear()",
    "ordered = sorted(anchors.items())",
    "if len(ordered) < 2 or any(right[1] <= left[1] for left, right in zip(ordered, ordered[1:])):",
    "ordered = []",
    "calibrated = dict(fallback)",
    "applied_intervals: list[tuple[int, int]] = []",
    "for (start, previous_usage), (end, usage) in zip(ordered, ordered[1:]):",
    "indexes = list(range(start, end))",
    "if not indexes or any(not isinstance(owners[index], str) or not owners[index] for index in indexes):",
    "local = [fallback[index] for index in indexes]",
    "total_local, total_usage = sum(local), usage - previous_usage",
    "if total_local <= 0 or total_usage <= 0:",
    "cumulative = 0",
    "previous_rounded = 0",
    "for index, estimate in zip(indexes, local):",
    "cumulative += estimate",
    "rounded = (cumulative * total_usage + total_local // 2) // total_local",
    "calibrated[index] = rounded - previous_rounded",
    "previous_rounded = rounded",
    "applied_intervals.append((start, end))",
    "return calibrated, applied_intervals",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


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
        raise ValueError(
            f"上下文规模估算行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"上下文规模估算行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"上下文规模估算行为变化 {label}：期望 ValueError")


def _request(messages, *, model: str = "m", system: str = "", tools: tuple = (),
             max_tokens: int = 100, effort=None, thinking=None) -> ModelRequest:
    return ModelRequest(model=model, system=system, messages=tuple(messages),
                        tools=tuple(tools), max_tokens=max_tokens,
                        effort=effort, thinking=thinking)


def _anchor(provider: str, request: ModelRequest, count, usage, *, eligible=True) -> dict:
    prefix = replace(request, messages=request.messages[:count])
    return {"type": "model_usage", "payload": {
        "provider": provider, "model": request.model, "eligible": eligible,
        "messageCount": count,
        "requestFingerprint": request_fingerprint(provider, prefix),
        "usage": usage}}


def _retained(request: ModelRequest, entries: list[dict], owners: list):
    return _retained_usage_estimate(
        "openai", request, entries, messages=list(request.messages), owners=owners)


def _behavior_checks() -> int:
    checked = 0

    checked += _expect_value(_json_size({}), 2, "空对象规模")
    checked += _expect_value(_json_size({"a": 1}), 8, "对象规模")
    checked += _expect_value(_json_size({"a": "汉"}), 10, "非 ASCII 规模")
    checked += _expect_value(_json_size({"a": 1, "b": 2}), 16, "多字段规模")

    checked += _expect_value(_message_size([UserMessage("abc")]), 35, "用户消息规模")
    checked += _expect_value(
        _message_size((UserMessage("a"), AssistantMessage((TextBlock("bc"),)))), 67,
        "混合消息规模")
    checked += _expect_value(
        _message_size([AssistantMessage((ThinkingBlock(
            "th", signature="sig", redacted_data="red", prefix_digest="p"),))]),
        40, "思考块规模")
    checked += _expect_value(
        _message_size([AssistantMessage((ToolCallBlock("id", "read", {"a": 1}),))]),
        46, "工具调用规模")
    checked += _expect_value(
        _message_size([ToolResultsMessage((ToolResultItem("c1", "ok"),
                                            ToolResultItem("c2", "no", True)))]),
        40, "工具结果规模")
    checked += _expect_value(
        _message_size([UserMessage("x"), ToolResultsMessage((ToolResultItem("c", "y"),))]),
        33 + 34, "结果与正文规模")

    checked += _expect_value(estimate_tokens([], ""), 0, "空估算")
    checked += _expect_value(estimate_tokens([], "ab"), 1, "系统提示估算")
    checked += _expect_value(estimate_tokens([UserMessage("a")]), 17, "单消息估算")
    checked += _expect_value(estimate_tokens([UserMessage("a")], "bc"), 18, "系统加消息估算")

    checked += _expect_value(_usage_input_tokens("openai", None), None, "用量非对象")
    checked += _expect_value(_usage_input_tokens("openai", []), None, "用量列表")
    checked += _expect_value(_usage_input_tokens("openai", {"input": 5}), 5, "OpenAI 输入")
    checked += _expect_value(
        _usage_input_tokens("openai", {"input": 5, "cache_read": 1000, "cache_write": 1000}),
        5, "OpenAI 只计输入")
    checked += _expect_value(_usage_input_tokens("openai", {"input": True}), None, "OpenAI 布尔")
    checked += _expect_value(_usage_input_tokens("openai", {"input": -1}), None, "OpenAI 负数")
    checked += _expect_value(_usage_input_tokens("openai", {"input": 1.0}), None, "OpenAI 浮点")
    checked += _expect_value(_usage_input_tokens("openai", {}), None, "OpenAI 缺字段")
    checked += _expect_value(
        _usage_input_tokens("anthropic", {"input": 5, "cache_read": 2, "cache_write": 3}),
        10, "Anthropic 合计")
    checked += _expect_value(
        _usage_input_tokens("anthropic", {"input": 5, "cache_read": 2}), None,
        "Anthropic 缺缓存写")
    checked += _expect_value(
        _usage_input_tokens("anthropic", {"input": 5, "cache_read": 2, "cache_write": 0}),
        7, "Anthropic 缓存读")
    checked += _expect_value(
        _usage_input_tokens("anthropic", {"input": 5, "cache_read": True, "cache_write": 0}),
        None, "Anthropic 布尔")
    checked += _expect_value(_usage_input_tokens("none", {"input": 5}), None, "空线路")
    checked += _expect_value(_usage_input_tokens("google", {"input": 5}), None, "未知线路")
    checked += _expect_value(_usage_input_tokens("openai", {"input": 0}), None, "零用量")
    checked += _expect_value(
        _usage_input_tokens("openai", {"input": MAX_REQUEST_TOKENS}), MAX_REQUEST_TOKENS,
        "用量上限边界")
    checked += _expect_value(
        _usage_input_tokens("openai", {"input": MAX_REQUEST_TOKENS + 1}), None, "用量超限")
    checked += _expect_value(
        _usage_input_tokens("anthropic", {"input": MAX_REQUEST_TOKENS,
                                          "cache_read": 0, "cache_write": 1}), None,
        "Anthropic 合计超限")

    base = _request([UserMessage("hello")])
    digest = request_fingerprint("openai", base)
    checked += _expect_value(
        (len(digest), set(digest) <= set("0123456789abcdef")), (64, True), "指纹形态")
    checked += _expect_value(request_fingerprint("openai", base), digest, "指纹确定")
    checked += _expect_value(
        request_fingerprint("anthropic", base) != digest, True, "指纹线路")
    checked += _expect_value(
        request_fingerprint("openai", _request([UserMessage("hello")], model="m2")) != digest,
        True, "指纹模型")
    checked += _expect_value(
        request_fingerprint("openai", _request([UserMessage("hello")], system="sys")) != digest,
        True, "指纹系统提示")
    checked += _expect_value(
        request_fingerprint("openai", _request([UserMessage("other")])) != digest, True,
        "指纹消息")
    checked += _expect_value(
        request_fingerprint("openai", _request(
            [UserMessage("hello")],
            tools=(ToolSpec("read", "desc", {"type": "object"}),))) != digest, True,
        "指纹工具")
    checked += _expect_value(
        request_fingerprint("openai", _request([UserMessage("hello")], max_tokens=200)) != digest,
        True, "指纹输出预算")
    checked += _expect_value(
        request_fingerprint("openai", _request([UserMessage("hello")], effort="low")) != digest,
        True, "指纹推理档位")
    checked += _expect_value(
        request_fingerprint("openai", _request(
            [UserMessage("hello")], thinking={"type": "enabled"})) != digest, True,
        "指纹思考配置")
    checked += _expect_value(
        request_fingerprint("openai", _request(
            [UserMessage("hello")], thinking={"a": 1, "b": 2})),
        request_fingerprint("openai", _request(
            [UserMessage("hello")], thinking={"b": 2, "a": 1})), "指纹思考键序")

    checked += _expect_value(
        _message_fingerprint_payload(UserMessage("hi")), {"role": "user", "text": "hi"},
        "用户负载")
    checked += _expect_value(
        _message_fingerprint_payload(AssistantMessage((
            TextBlock("t"), ThinkingBlock("th", signature="sig", redacted_data="red"),
            ThinkingBlock("x"), ToolCallBlock("id", "read", {"a": 1})))),
        {"role": "assistant", "blocks": [
            {"type": "text", "text": "t"},
            {"type": "thinking", "text": "th", "signature": "sig", "redactedData": "red"},
            {"type": "thinking", "text": "x"},
            {"type": "toolCall", "id": "id", "name": "read", "arguments": {"a": 1}}]},
        "助手负载")
    checked += _expect_value(
        _message_fingerprint_payload(AssistantMessage((
            ThinkingBlock("th", prefix_digest="p"),))),
        {"role": "assistant", "blocks": [
            {"type": "thinking", "text": "th", "prefixDigest": "p"}]}, "前缀摘要负载")
    checked += _expect_value(
        _message_fingerprint_payload(ToolResultsMessage((
            ToolResultItem("c", "x", True),))),
        {"role": "toolResults", "results": [
            {"toolCallId": "c", "content": "x", "isError": True}]}, "结果负载")

    messages = [UserMessage("a"), UserMessage("bb"), UserMessage("ccc")]
    request = _request(messages)
    fallback = {0: 17, 1: 17, 2: 18}
    checked += _expect_value(_retained(request, [], ["t", "t", "t"]), (fallback, []), "无锚点回退")
    checked += _expect_value(_retained(request, [], ["t", "t"]), (fallback, []), "归属长度不符")
    low = _anchor("openai", request, 1, {"input": 10})
    high = _anchor("openai", request, 3, {"input": 40})
    checked += _expect_value(
        _retained(request, [low, high], ["t", "t", "t"]),
        ({0: 17, 1: 15, 2: 15}, [(1, 3)]), "区间校准")
    start = _anchor("openai", request, 0, {"input": 5})
    checked += _expect_value(
        _retained(request, [start, high], ["t", "t", "t"]),
        ({0: 11, 1: 12, 2: 12}, [(0, 3)]), "从零校准")
    checked += _expect_value(
        _retained(request, [low, high], ["t", None, "t"]), (fallback, []), "归属缺失跳过")
    checked += _expect_value(
        _retained(request, [low, high], ["t", "", "t"]), (fallback, []), "归属空串跳过")
    flat = _anchor("openai", request, 3, {"input": 10})
    checked += _expect_value(
        _retained(request, [low, flat], ["t", "t", "t"]), (fallback, []), "非递增回退")
    checked += _expect_value(_retained(request, [low], ["t", "t", "t"]), (fallback, []), "单锚点回退")
    conflict = _anchor("openai", request, 1, {"input": 11})
    checked += _expect_value(
        _retained(request, [low, conflict, high], ["t", "t", "t"]), (fallback, []), "冲突清空")
    checked += _expect_value(
        _retained(request, [low, low, high], ["t", "t", "t"]),
        ({0: 17, 1: 15, 2: 15}, [(1, 3)]), "重复一致锚点")
    checked += _expect_value(
        _retained(request, [_anchor("anthropic", request, 1, {"input": 10}),
                            _anchor("anthropic", request, 3, {"input": 40})],
                  ["t", "t", "t"]), (fallback, []), "线路不符跳过")
    other = _request(messages, model="other")
    checked += _expect_value(
        _retained(request, [_anchor("openai", other, 1, {"input": 10}),
                            _anchor("openai", other, 3, {"input": 40})],
                  ["t", "t", "t"]), (fallback, []), "模型不符跳过")
    ineligible = _anchor("openai", request, 1, {"input": 10}, eligible=False)
    checked += _expect_value(
        _retained(request, [ineligible, high], ["t", "t", "t"]), (fallback, []),
        "未标记合格跳过")
    boolean_count = _anchor("openai", request, True, {"input": 10})
    checked += _expect_value(
        _retained(request, [boolean_count, high], ["t", "t", "t"]), (fallback, []),
        "布尔计入跳过")
    over_count = _anchor("openai", request, 4, {"input": 10})
    checked += _expect_value(
        _retained(request, [over_count, high], ["t", "t", "t"]), (fallback, []),
        "超长计入跳过")
    bad_fingerprint = _anchor("openai", request, 1, {"input": 10})
    bad_fingerprint["payload"]["requestFingerprint"] = "0" * 64
    checked += _expect_value(
        _retained(request, [bad_fingerprint, high], ["t", "t", "t"]), (fallback, []),
        "指纹不符跳过")
    foreign = _request([UserMessage("a"), UserMessage("zz"), UserMessage("ccc")])
    checked += _expect_value(
        _retained(request, [_anchor("openai", foreign, 2, {"input": 20}), high],
                  ["t", "t", "t"]), (fallback, []), "前缀消息不符跳过")
    checked += _expect_value(
        _retained(request, [_anchor("openai", request, 1, {"input": 0}), high],
                  ["t", "t", "t"]), (fallback, []), "零用量跳过")
    checked += _expect_value(
        _retained(request, [_anchor("openai", request, 1, {"input": True}), high],
                  ["t", "t", "t"]), (fallback, []), "无效用量跳过")
    checked += _expect_value(
        _retained(request, [{"type": "message", "payload": {"provider": "openai"}}, high],
                  ["t", "t", "t"]), (fallback, []), "非用量条目跳过")
    checked += _expect_value(
        _retained(request, [{"type": "model_usage", "payload": None}, high],
                  ["t", "t", "t"]), (fallback, []), "空载荷跳过")

    user = {"kind": "userMessage", "id": "u1", "text": "你好"}
    agent = {"kind": "agentMessage", "id": "a1", "text": "回复", "status": "completed"}
    checked += _expect_value(messages_from_items([]), (), "空条目")
    checked += _expect_value(
        messages_from_items([user, agent]),
        (UserMessage("你好"), AssistantMessage(blocks=(TextBlock(text="回复"),))),
        "用户与助手")
    for label, item in (
        ("运行中助手", {"kind": "agentMessage", "id": "a2", "text": "运行", "status": "running"}),
        ("失败助手", {"kind": "agentMessage", "id": "a3", "text": "失败", "status": "failed"}),
        ("空正文助手", {"kind": "agentMessage", "id": "a4", "text": "", "status": "completed"}),
        ("非字符串用户", {"kind": "userMessage", "id": "u2", "text": 3}),
    ):
        checked += _expect_value(messages_from_items([item]), (), label)
    checked += _expect_value(
        messages_from_items([
            {"kind": "userMessage", "id": "u3", "text": "坏\ud800字"},
            {"kind": "agentMessage", "id": "a5", "text": "也\udc00坏",
             "status": "completed"}]),
        (UserMessage("坏�字"), AssistantMessage(blocks=(TextBlock(text="也�坏"),))),
        "孤立代理项降级")

    tool_a = {"kind": "toolCall", "id": "t1", "toolCallId": "c1", "toolName": "boss_list_jobs",
              "toolArguments": {"page": 1}, "toolBatchId": "b1", "status": "completed",
              "result": {"ok": True}}
    tool_b = {"kind": "toolCall", "id": "t2", "toolCallId": "c2", "toolName": "boss_list_jobs",
              "toolArguments": {}, "toolBatchId": "b1", "status": "completed",
              "result": {"ok": False}}
    checked += _expect_value(
        messages_from_items([tool_a]),
        (AssistantMessage(blocks=(ToolCallBlock(id="c1", name="boss_list_jobs",
                                                arguments={"page": 1}),)),
         ToolResultsMessage(results=(ToolResultItem(
             tool_call_id="c1", content='{"ok": true}', is_error=False),))),
        "单工具批次")
    checked += _expect_value(
        messages_from_items([tool_a, tool_b]),
        (AssistantMessage(blocks=(ToolCallBlock(id="c1", name="boss_list_jobs",
                                                arguments={"page": 1}),
                                  ToolCallBlock(id="c2", name="boss_list_jobs",
                                                arguments={}))),
         ToolResultsMessage(results=(
             ToolResultItem(tool_call_id="c1", content='{"ok": true}', is_error=False),
             ToolResultItem(tool_call_id="c2", content='{"ok": false}', is_error=False)))),
        "同批合并")
    checked += _expect_value(
        len(messages_from_items([tool_a, dict(tool_b, toolBatchId="b2")])), 4, "批次拆分")
    interrupted = messages_from_items([tool_a, user, tool_a])
    checked += _expect_value(
        [type(message).__name__ for message in interrupted],
        ["AssistantMessage", "ToolResultsMessage", "UserMessage",
         "AssistantMessage", "ToolResultsMessage"], "用户消息打断批次")
    checked += _expect_value(
        messages_from_items([dict(tool_a, status="running")]), (), "运行中工具跳过")
    fallback = messages_from_items([{
        "kind": "toolCall", "id": "t9", "toolName": "boss_list_jobs",
        "toolArguments": {}, "toolBatchId": "b1", "status": "completed",
        "result": {}}])[1]
    checked += _expect_value(fallback.results[0].tool_call_id, "t9", "缺少调用 id 回退")
    failed = messages_from_items([{
        "kind": "toolCall", "id": "t3", "toolCallId": "c3",
        "toolName": "boss_list_jobs", "toolArguments": {},
        "toolBatchId": "b1", "status": "failed", "resultSummary": "命令失败"}])[1]
    checked += _expect_value(
        (failed.results[0].is_error, "resultUnavailable" in failed.results[0].content),
        (True, True), "失败工具标记")
    checked += _expect_value(
        messages_from_items([
            {"kind": "agentMessage", "id": "a6", "text": "带签名", "status": "completed",
             "_anthropicContinuation": {"assistantItemId": "a6"}}, user]),
        (UserMessage("你好"),), "续接标识过滤")
    checked += _expect_error(
        lambda: messages_from_items([dict(tool_a, toolBatchAssistantItemId="x"),
                                     dict(tool_b, toolBatchAssistantItemId="y")]),
        "Tool batch assistant reference is duplicated", "重复批次引用")
    surrogate_result = messages_from_items([{
        "kind": "toolCall", "id": "t4", "toolCallId": "c4",
        "toolName": "boss_list_jobs", "toolArguments": {},
        "toolBatchId": "b1", "status": "completed",
        "result": {"text": "坏\ud800"}}])[1]
    checked += _expect_value(
        ("�" in surrogate_result.results[0].content,
         "\ud800" in surrogate_result.results[0].content), (True, False), "工具结果降级")
    return checked


def check_context_estimate() -> int:
    source = _read(CONTEXT)
    tree = ast.parse(source)
    json_size = _function(tree, source, "_json_size")
    message_size = _function(tree, source, "_message_size")
    estimate = _function(tree, source, "estimate_tokens")
    usage = _function(tree, source, "_usage_input_tokens")
    fingerprint = _function(tree, source, "request_fingerprint")
    payload = _function(tree, source, "_message_fingerprint_payload")
    retained = _function(tree, source, "_retained_usage_estimate")
    messages = _function(tree, source, "messages_from_items")
    checked = _ordered(JSON_ORDER, json_size, CONTEXT)
    checked += _ordered(MESSAGE_ORDER, message_size, CONTEXT)
    checked += _ordered(MESSAGES_ORDER, messages, CONTEXT)
    checked += _ordered(ESTIMATE_ORDER, estimate, CONTEXT)
    checked += _ordered(USAGE_ORDER, usage, CONTEXT)
    checked += _ordered(FINGERPRINT_ORDER, fingerprint, CONTEXT)
    checked += _ordered(PAYLOAD_ORDER, payload, CONTEXT)
    checked += _ordered(RETAINED_ORDER, retained, CONTEXT)
    # 规模估算必须逐条加固定开销，且思考签名与脱敏数据各自计数一次。
    if message_size.count("size += 32") != 1:
        raise ValueError(f"{CONTEXT} 的规模估算必须为每条消息加固定开销")
    checked += 1
    if message_size.count("size += len(block.signature)") != 1:
        raise ValueError(f"{CONTEXT} 的规模估算必须计入思考签名")
    checked += 1
    if message_size.count("size += len(block.redacted_data)") != 1:
        raise ValueError(f"{CONTEXT} 的规模估算必须计入脱敏数据")
    checked += 1
    # 工具参数必须复制后序列化，避免估算路径持有可变引用。
    if message_size.count("_json_size(dict(block.arguments))") != 1:
        raise ValueError(f"{CONTEXT} 的规模估算必须复制工具参数")
    checked += 1
    # 字符估算以向上取整的一半为界，不引入厂商分词器。
    if estimate.count("(size + 1) // 2") != 1 or "len(system) + _message_size(messages)" not in estimate:
        raise ValueError(f"{CONTEXT} 的 token 估算必须包含系统提示并向上取整")
    checked += 1
    if "import tiktoken" in source or "import tokenizers" in source:
        raise ValueError(f"{CONTEXT} 的 token 估算不得依赖厂商分词器")
    checked += 1
    # provider 用量字段固定，且总量受单请求上限约束。
    if '"cache_read", "cache_write"' not in usage or '"input",)' not in usage:
        raise ValueError(f"{CONTEXT} 的用量字段必须按 provider 固定")
    checked += 1
    if usage.count("MAX_REQUEST_TOKENS") != 1:
        raise ValueError(f"{CONTEXT} 的用量必须受单请求上限约束")
    checked += 1
    if usage.count("type(value) is not int or value < 0") != 1:
        raise ValueError(f"{CONTEXT} 的用量必须是精确非负整数")
    checked += 1
    # 请求指纹必须覆盖思考配置并只输出 SHA-256 十六进制摘要。
    if '"thinking": dict(request.thinking)' not in fingerprint:
        raise ValueError(f"{CONTEXT} 的请求指纹必须包含思考配置")
    checked += 1
    if fingerprint.count("hashlib.sha256(encoded).hexdigest()") != 1:
        raise ValueError(f"{CONTEXT} 的请求指纹必须使用 SHA-256")
    checked += 1
    # 消息负载只含约定字段，角色名固定。
    if payload.count('{"role": "user"') != 1 or payload.count('{"role": "assistant"') != 1 \
            or payload.count('{"role": "toolResults"') != 1:
        raise ValueError(f"{CONTEXT} 的消息负载角色必须固定")
    checked += 1
    for field in ('"signature"', '"redactedData"', '"prefixDigest"', '"isError"'):
        if payload.count(field) != 1:
            raise ValueError(f"{CONTEXT} 的消息负载必须包含 {field}")
        checked += 1
    # 校准：冲突锚点必须清空，用量必须严格递增。
    if retained.count("anchors.clear()") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须清空冲突锚点")
    checked += 1
    if retained.count("right[1] <= left[1]") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须要求严格递增")
    checked += 1
    if retained.count("len(ordered) < 2") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准至少需要两个锚点")
    checked += 1
    # 校准区间必须校验 owners，且只用已验证前缀。
    if retained.count("not isinstance(owners[index], str) or not owners[index]") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须校验消息归属")
    checked += 1
    if retained.count("if request_fingerprint(provider, prefix) != fingerprint:") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须复核前缀指纹")
    checked += 1
    # 四舍五入到整条消息，且累计差值不回退。
    if retained.count("(cumulative * total_usage + total_local // 2) // total_local") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须按累计值四舍五入")
    checked += 1
    if retained.count("calibrated[index] = rounded - previous_rounded") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须换算为单条增量")
    checked += 1
    if retained.count("applied_intervals.append((start, end))") != 1:
        raise ValueError(f"{CONTEXT} 的用量校准必须记录已应用区间")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_context_estimate()
    except (ValueError, SyntaxError) as error:
        print(f"上下文规模估算核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文规模估算一致：{checked} 项结构、组装、行为与校准校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
