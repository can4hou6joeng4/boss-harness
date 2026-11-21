#!/usr/bin/env python3
"""核对上下文规模估算、请求指纹与成功用量校准口径。

`_message_size` 逐类型累加正文、思考签名、脱敏数据、工具调用与工具结果，
并为每条消息加固定开销；`estimate_tokens` 以字符数的一半作为保守估算。
`_usage_input_tokens` 只接受当前 provider 的非负整数字段，并受单请求上限
约束；`request_fingerprint` 覆盖模型、系统提示、消息、工具、输出预算、
推理档位与思考配置；`_retained_usage_estimate` 只用已验证前缀的成功用量
校准逐条估算。这里按源码顺序固定这些边界，避免预算被低估或校准被污染。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = "harness/src/boss_harness/context.py"

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
    checked = _ordered(JSON_ORDER, json_size, CONTEXT)
    checked += _ordered(MESSAGE_ORDER, message_size, CONTEXT)
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
    return checked


def main() -> int:
    try:
        checked = check_context_estimate()
    except (ValueError, SyntaxError) as error:
        print(f"上下文规模估算核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文规模估算一致：{checked} 项规模、指纹与用量校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
