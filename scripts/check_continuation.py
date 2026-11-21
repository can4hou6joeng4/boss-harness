#!/usr/bin/env python3
"""核对 Anthropic 私有续接元数据的预算、构造与恢复校验。

continuation.py 只保存签名块的描述而不是重复正文：请求前缀 digest 绑定模型可见
前缀，构造与恢复都必须拒绝超限签名、重复引用、跨回合批次与被编辑的助手消息。
任一放宽都会让未验证的签名进入下一次请求，或让损坏记录反复阻断分支，因此静态固定，
并直接构造消息与持久条目核对构造、恢复与降级结果。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/continuation.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.continuation import (  # noqa: E402
    ANTHROPIC_CONTINUATION_FIELD,
    MAX_ANTHROPIC_CONTINUATION_BYTES,
    MAX_ANTHROPIC_SIGNATURE_BYTES,
    MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES,
    anthropic_continuation,
    anthropic_prefix_digest,
    assistant_from_tool_batch,
)
from boss_harness.models.types import (  # noqa: E402
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
)

CONSTANT_FRAGMENTS = (
    'ANTHROPIC_CONTINUATION_FIELD = "_anthropicContinuation"\n',
    "MAX_ANTHROPIC_SIGNATURE_BYTES = 16 * 1024\n",
    "MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES = 96 * 1024\n",
    "MAX_ANTHROPIC_CONTINUATION_BYTES = 128 * 1024\n",
    "MAX_ANTHROPIC_CONTINUATION_CHARS = 1024 * 1024\n",
)
DIGEST_FRAGMENTS = (
    "def anthropic_prefix_digest(system: str, tools: object, messages: object) -> str:",
    'value = {"system": system, "tools": tools or [], "messages": messages}',
    'json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")',
    "hashlib.sha256(encoded).hexdigest()",
)
BUILD_FRAGMENTS = (
    "calls = [block for block in message.blocks if isinstance(block, ToolCallBlock)]",
    "has_continuation = any(",
    "isinstance(block, ThinkingBlock) and (block.signature is not None or block.redacted_data is not None)",
    "if not calls or not has_continuation:",
    "return None",
    '"version": 1,',
    '"provider": "anthropic",',
    '"assistantItemId": assistant_item_id,',
    '"toolCallIds": [block.id for block in calls],',
    "block.prefix_digest for block in message.blocks",
    "total_signature_bytes = 0",
    'descriptors.append({"type": "text", "length": len(block.text),',
    '"sha256": hashlib.sha256(block.text.encode("utf-8")).hexdigest()})',
    'raise ValueError("Anthropic thinking blocks do not share a request prefix")',
    "if block.redacted_data is not None:",
    "if block.signature is not None or block.thinking:",
    'raise ValueError("Anthropic redacted thinking block is invalid")',
    'raise ValueError("Anthropic redacted thinking exceeds its private storage limit")',
    "total_signature_bytes += size",
    'descriptors.append({"type": "redactedThinking", "data": block.redacted_data})',
    'raise ValueError("Anthropic thinking signature exceeds its private storage limit")',
    'descriptors.append({"type": "thinking", "length": len(block.thinking),',
    '"signature": signature,',
    'elif isinstance(block, ToolCallBlock):',
    'descriptors.append({"type": "toolCall", "id": block.id})',
    "if (total_signature_bytes > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES",
    "or len(descriptors) > 4096):",
    'raise ValueError("Anthropic thinking signatures exceed their private storage limit")',
    'payload["blocks"] = descriptors',
    'if len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_ANTHROPIC_CONTINUATION_BYTES:',
    'raise ValueError("Anthropic tool continuation exceeds its private storage limit")',
)
BATCH_FRAGMENTS = (
    "def _tool_arguments(item: dict[str, Any]) -> dict[str, Any]:",
    'value = item.get("toolArguments")',
    "return value if isinstance(value, dict) else {}",
    "def assistant_from_tool_batch(items: list[dict], pending: list[dict]) -> AssistantMessage:",
    'id=str(item.get("toolCallId") or item["id"]),',
    'name=str(item.get("toolName", "")),',
    "if len(assistant_ids) > 1:",
    'raise ValueError("Tool batch assistant reference is duplicated")',
    'if linked_assistant is not None and linked_assistant.get("kind") != "agentMessage":',
    "return _plain_batch(None, tool_calls)",
    'isinstance(item.get("status"), str) and item.get("status") in {"completed", "failed"}',
    '"completed", "failed", "not_executed", "not_approved"',
    'raise ValueError("Tool batch assistant item is missing or inconsistent")',
    "continuations = [item[ANTHROPIC_CONTINUATION_FIELD] for item in pending",
    "except UnicodeEncodeError:",
    "return _plain_batch(linked_assistant, tool_calls)",
)
PLAIN_FRAGMENTS = (
    "def _plain_batch(linked_assistant: dict | None, tool_calls: tuple[ToolCallBlock, ...]) -> AssistantMessage:",
    "blocks = ((TextBlock(text=wire_text(text)),) if isinstance(text, str) and text else ()) + tool_calls",
)
RESTORE_FRAGMENTS = (
    "def _restore_continuation(items: list[dict], pending: list[dict],",
    "if len(continuations) != 1 or ANTHROPIC_CONTINUATION_FIELD not in pending[0]:",
    'raise ValueError("Anthropic continuation metadata is duplicated")',
    'set(payload) != {"version", "provider", "assistantItemId", "toolCallIds", "requestPrefix", "blocks"}',
    'type(payload.get("version")) is not int or payload["version"] != 1',
    'payload.get("provider") != "anthropic"',
    'raise ValueError("Anthropic continuation metadata is invalid")',
    're.fullmatch(r"[a-f0-9]{64}", prefix_digest) is None',
    'raise ValueError("Anthropic continuation request prefix is invalid")',
    "if (not isinstance(intended_call_ids, list) or not intended_call_ids",
    "or len(set(intended_call_ids)) != len(intended_call_ids)",
    "or intended_call_ids[:len(call_ids)] != call_ids):",
    'raise ValueError("Anthropic continuation no longer matches its tool batch")',
    "if linked_assistant_id is not None and assistant_item_id != linked_assistant_id:",
    'raise ValueError("Anthropic continuation assistant reference does not match its batch")',
    'raise ValueError("Anthropic continuation assistant item is missing")',
    'raise ValueError("Anthropic continuation assistant belongs to another turn")',
    'raise ValueError("Anthropic continuation tools belong to different turns")',
    "if not isinstance(blocks, list) or len(blocks) > 4096:",
    'raise ValueError("Anthropic continuation block list is invalid")',
    'if assistant_item is not None and assistant_item.get("contextEdit"):',
    'raise ValueError("Signed Anthropic assistant responses cannot be context edited")',
    "if missing_call_seen:",
    'raise ValueError("Anthropic continuation has content after an unpersisted tool call")',
    'if set(block) != ({"type", "length", "sha256"} if kind == "text"',
    'else {"type", "length", "sha256", "signature"}):',
    'raise ValueError("Anthropic continuation content descriptor is invalid")',
    're.fullmatch(r"[a-f0-9]{64}", content_digest) is None',
    'raise ValueError("Anthropic continuation content digest is invalid")',
    "if type(length) is not int or not 0 <= length <= MAX_ANTHROPIC_CONTINUATION_CHARS:",
    'raise ValueError("Anthropic continuation content length is invalid")',
    'if hashlib.sha256(value.encode("utf-8")).hexdigest() != content_digest:',
    'raise ValueError("Anthropic continuation text has changed")',
    'raise ValueError("Anthropic continuation thinking has changed")',
    'if set(block) != {"type", "data"} or not isinstance(block.get("data"), str) or not block["data"]:',
    'raise ValueError("Anthropic redacted thinking block is invalid")',
    'if set(block) != {"type", "id"} or not isinstance(block.get("id"), str):',
    'raise ValueError("Anthropic continuation tool descriptor is invalid")',
    'raise ValueError("Anthropic continuation block type is unsupported")',
    "if (text_length > MAX_ANTHROPIC_CONTINUATION_CHARS",
    "or thinking_length > MAX_ANTHROPIC_CONTINUATION_CHARS",
    "or signature_bytes > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES",
    "or described_calls != intended_call_ids",
    "or (assistant_item is None and (text_length or thinking_length))",
    "and (text_offset != len(text_value) or thinking_offset != len(thinking_value)))):",
    'raise ValueError("Anthropic continuation does not match its assistant response")',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "Anthropic 的私有续接元数据只保存签名块描述：请求前缀 digest、块顺序、长度与内容 SHA-256；单个签名最多 16 KiB，签名合计最多 96 KiB，续接载荷最多 128 KiB，正文 / 思考各最多 1 048 576 字符且块最多 4096 个"),
    (TECHNICAL_REFERENCE, "恢复时逐块校验 digest、调用 ID、回合归属与助手引用；编码失败的签名元数据降级为普通工具批次，其余字段错配按固定说明拒绝"),
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


PREFIX = "a" * 64


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"续接元数据行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"续接元数据行为变化 {label}：错误消息 {str(error)!r}") from None
        return 1
    raise ValueError(f"续接元数据行为变化 {label}：未抛出 ValueError")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_payload(text: str = "hello", thinking: str = "think",
                   assistant_id: str | None = "a1") -> dict:
    message = AssistantMessage(blocks=(
        TextBlock(text=text),
        ThinkingBlock(thinking=thinking, signature="sig", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="tool", arguments={"a": 1}),
    ))
    return anthropic_continuation(message, assistant_id)


def _pending(payload) -> list[dict]:
    return [{"id": "t1", "toolCallId": "c1", "toolName": "tool", "toolArguments": {"a": 1},
             "turnId": "turn", "toolBatchId": "batch", "toolBatchAssistantItemId": "a1",
             ANTHROPIC_CONTINUATION_FIELD: payload}]


def _assistant(text: str = "hello", thinking: str = "think", *,
               assistant_id: str = "a1", turn: str = "turn", edit: bool = False,
               kind: str = "agentMessage") -> dict:
    item = {"id": assistant_id, "kind": kind, "turnId": turn, "toolBatchId": "batch",
            "status": "completed", "text": text, "thinking": thinking}
    if edit:
        item["contextEdit"] = True
    return item


def _unlinked(payload) -> list[dict]:
    item = _pending(payload)[0]
    item.pop("toolBatchAssistantItemId")
    return [item]


def _behavior_checks() -> int:
    checked = 0
    # 前缀 digest：空工具归一、排序与分隔符固定、非 ASCII 不转义。
    system = "你是助手"
    messages = [{"role": "user", "text": "你好"}]
    digest = anthropic_prefix_digest(system, None, messages)
    checked += _expect_value(anthropic_prefix_digest(system, [], messages), digest, "空工具归一")
    checked += _expect_value(len(digest), 64, "摘要长度")
    checked += _expect_value(all(char in "0123456789abcdef" for char in digest), True,
                             "小写十六进制")
    expected = json.dumps({"system": system, "tools": [], "messages": messages},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    checked += _expect_value(digest, hashlib.sha256(expected.encode("utf-8")).hexdigest(),
                             "非 ASCII 与紧凑排序")
    checked += _expect_value(
        anthropic_prefix_digest("x", None, messages) != digest, True, "系统差异")

    # 构造：仅在有工具调用且存在签名 / 隐藏思考时生成描述，字段与顺序固定。
    payload = _build_payload()
    checked += _expect_value(
        (payload["version"], payload["provider"], payload["assistantItemId"],
         payload["toolCallIds"], payload["requestPrefix"]),
        (1, "anthropic", "a1", ["c1"], PREFIX), "构造字段")
    checked += _expect_value(
        payload["blocks"],
        [{"type": "text", "length": 5, "sha256": _sha("hello")},
         {"type": "thinking", "length": 5, "signature": "sig", "sha256": _sha("think")},
         {"type": "toolCall", "id": "c1"}], "块描述")
    checked += _expect_value(anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", signature="s", prefix_digest=PREFIX),)), None), None,
        "没有调用")
    checked += _expect_value(anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None), None, "没有签名")
    unsigned = anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", prefix_digest=PREFIX),
        ThinkingBlock(thinking="u", signature="s", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None)
    checked += _expect_value(unsigned["blocks"][0]["signature"], None, "无签名描述")
    redacted = anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(redacted_data="opaque", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), "a1")
    checked += _expect_value(redacted["blocks"][0],
                             {"type": "redactedThinking", "data": "opaque"}, "隐藏思考描述")

    # 构造拒绝：前缀不一致、隐藏块夹带字段、空与超限签名、合计 / 描述 / 载荷上限。
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", signature="s", prefix_digest=PREFIX),
        ThinkingBlock(thinking="u", signature="s", prefix_digest="b" * 64),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic thinking blocks do not share a request prefix", "前缀不一致")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", signature="s", redacted_data="r", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic redacted thinking block is invalid", "隐藏块带签名")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", redacted_data="r", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic redacted thinking block is invalid", "隐藏块带正文")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(redacted_data="", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic redacted thinking exceeds its private storage limit", "空隐藏块")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", signature="", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic thinking signature exceeds its private storage limit", "空签名")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(thinking="t", signature="x" * (MAX_ANTHROPIC_SIGNATURE_BYTES + 1),
                      prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic thinking signature exceeds its private storage limit", "单签名超限")
    six = tuple(ThinkingBlock(thinking="t", signature="x" * MAX_ANTHROPIC_SIGNATURE_BYTES,
                              prefix_digest=PREFIX) for _ in range(6))
    checked += _expect_value(len(anthropic_continuation(AssistantMessage(
        blocks=six + (ToolCallBlock(id="c1", name="x"),)), None)["blocks"]), 7, "签名合计边界")
    seven = tuple(ThinkingBlock(thinking="t", signature="x" * MAX_ANTHROPIC_SIGNATURE_BYTES,
                                prefix_digest=PREFIX) for _ in range(7))
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(
        blocks=seven + (ToolCallBlock(id="c1", name="x"),)), None),
        "Anthropic thinking signatures exceed their private storage limit", "签名合计超限")
    many = tuple(TextBlock(text="") for _ in range(4096)) + (
        ThinkingBlock(thinking="t", signature="s", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=many), None),
                             "Anthropic thinking signatures exceed their private storage limit",
                             "描述块上限")
    big_calls = tuple(ToolCallBlock(id="x" * 100, name="n") for _ in range(4000)) + (
        ThinkingBlock(thinking="t", signature="s", prefix_digest=PREFIX),)
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=big_calls), None),
                             "Anthropic tool continuation exceeds its private storage limit",
                             "载荷上限")
    checked += _expect_error(lambda: anthropic_continuation(AssistantMessage(blocks=(
        ThinkingBlock(redacted_data="汉" * 6000, prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="x"))), None),
        "Anthropic redacted thinking exceeds its private storage limit", "多字节隐藏块")

    # 普通批次：调用 ID 优先 toolCallId，非对象参数归空，引用缺失 / 类型不符降级。
    plain = assistant_from_tool_batch([], [
        {"id": "t1", "toolCallId": "tc1", "toolName": "lookup",
         "toolArguments": {"q": "x"}, "turnId": "turn"},
        {"id": "t2", "toolArguments": [1], "turnId": "turn"},
    ])
    checked += _expect_value(
        [(block.id, block.name, dict(block.arguments)) for block in plain.blocks],
        [("tc1", "lookup", {"q": "x"}), ("t2", "", {})], "普通批次")
    linked_items = [_assistant()]
    linked_pending = [{"id": "t1", "toolName": "tool", "turnId": "turn",
                       "toolBatchId": "batch", "toolBatchAssistantItemId": "a1"}]
    checked += _expect_value(assistant_from_tool_batch(linked_items, linked_pending).text(),
                             "hello", "普通批次正文")
    checked += _expect_error(lambda: assistant_from_tool_batch([], [
        {"id": "t1", "toolBatchAssistantItemId": "a1"},
        {"id": "t2", "toolBatchAssistantItemId": "a2"}]),
        "Tool batch assistant reference is duplicated", "重复助手引用")
    degraded = assistant_from_tool_batch(
        [_assistant(kind="toolResult")],
        [{"id": "t1", "turnId": "turn", "toolBatchAssistantItemId": "a1"}])
    checked += _expect_value((degraded.text(), len(degraded.blocks)), ("", 1), "引用类型降级")
    missing = assistant_from_tool_batch(
        [], [{"id": "t1", "turnId": "turn", "toolBatchAssistantItemId": "a1"}])
    checked += _expect_value((missing.text(), len(missing.blocks)), ("", 1), "缺失引用降级")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant(turn="other")],
        [{"id": "t1", "turnId": "turn", "toolBatchId": "batch",
          "toolBatchAssistantItemId": "a1"}]),
        "Tool batch assistant item is missing or inconsistent", "引用不一致")
    failed_items = [_assistant()]
    failed_items[0]["status"] = "failed"
    settled = [{"id": "t1", "turnId": "turn", "toolBatchId": "batch",
                "toolBatchAssistantItemId": "a1", "status": "completed",
                "executionState": "failed"}]
    checked += _expect_value(assistant_from_tool_batch(failed_items, settled).text(),
                             "hello", "失败批次已结算")
    unsettled = [dict(settled[0], status="pending")]
    checked += _expect_error(lambda: assistant_from_tool_batch(failed_items, unsettled),
                             "Tool batch assistant item is missing or inconsistent",
                             "失败批次未结算")

    # 恢复成功：正文、思考与工具调用按描述顺序还原；空前缀保留。
    restored = assistant_from_tool_batch([_assistant()], _pending(payload))
    checked += _expect_value([type(block).__name__ for block in restored.blocks],
                             ["TextBlock", "ThinkingBlock", "ToolCallBlock"], "恢复块顺序")
    checked += _expect_value(
        (restored.blocks[0].text, restored.blocks[1].thinking, restored.blocks[1].signature,
         restored.blocks[1].prefix_digest), ("hello", "think", "sig", PREFIX), "恢复块字段")
    redacted_items = [{"id": "a1", "kind": "agentMessage", "turnId": "turn",
                       "toolBatchId": "batch", "status": "completed"}]
    restored_redacted = assistant_from_tool_batch(redacted_items, _pending(redacted))
    checked += _expect_value(
        (type(restored_redacted.blocks[0]).__name__,
         restored_redacted.blocks[0].redacted_data),
        ("ThinkingBlock", "opaque"), "恢复隐藏思考")
    no_prefix = copy.deepcopy(payload)
    no_prefix["requestPrefix"] = None
    checked += _expect_value(
        assistant_from_tool_batch([_assistant()], _pending(no_prefix)).blocks[1].prefix_digest,
        None, "恢复空前缀")

    # 后缀缺失：持久条目只保留连续前缀，未出现的调用允许缺席。
    two_calls = AssistantMessage(blocks=(
        ThinkingBlock(thinking="", signature="s", prefix_digest=PREFIX),
        ToolCallBlock(id="c1", name="a"), ToolCallBlock(id="c2", name="b")))
    suffix_payload = anthropic_continuation(two_calls, None)
    suffix_pending = [{"id": "t1", "toolCallId": "c1", "toolName": "a", "turnId": "turn",
                       ANTHROPIC_CONTINUATION_FIELD: suffix_payload}]
    suffix = assistant_from_tool_batch([], suffix_pending)
    checked += _expect_value([type(block).__name__ for block in suffix.blocks],
                             ["ThinkingBlock", "ToolCallBlock"], "缺席调用放行")

    # 恢复拒绝：重复元数据、字段错配、调用 ID、助手引用与回合归属。
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(payload) + _pending(payload)),
        "Anthropic continuation metadata is duplicated", "重复续接")
    without = _pending(payload)[0]
    without.pop(ANTHROPIC_CONTINUATION_FIELD)
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], [without, _pending(payload)[0]]),
        "Anthropic continuation metadata is duplicated", "字段不在首项")
    for label, value, message in (
        ("载荷非对象", "x", "Anthropic continuation metadata is invalid"),
        ("版本不符", {**payload, "version": 2}, "Anthropic continuation metadata is invalid"),
        ("provider 不符", {**payload, "provider": "openai"},
         "Anthropic continuation metadata is invalid"),
        ("字段缺失", {key: value for key, value in payload.items() if key != "blocks"},
         "Anthropic continuation metadata is invalid"),
        ("字段多余", {**payload, "extra": 1}, "Anthropic continuation metadata is invalid"),
        ("前缀非法", {**payload, "requestPrefix": "XYZ"},
         "Anthropic continuation request prefix is invalid"),
        ("调用为空", {**payload, "toolCallIds": []},
         "Anthropic continuation no longer matches its tool batch"),
        ("调用非字符串", {**payload, "toolCallIds": [1]},
         "Anthropic continuation no longer matches its tool batch"),
        ("调用重复", {**payload, "toolCallIds": ["c1", "c1"]},
         "Anthropic continuation no longer matches its tool batch"),
        ("调用顺序", {**payload, "toolCallIds": ["c2"]},
         "Anthropic continuation no longer matches its tool batch"),
        ("助手引用不符", {**payload, "assistantItemId": "other"},
         "Anthropic continuation assistant reference does not match its batch"),
    ):
        checked += _expect_error(
            lambda value=value: assistant_from_tool_batch(
                [_assistant(assistant_id="a2")],
                [dict(_pending(value)[0], toolBatchAssistantItemId="a2")]),
            message, label)
    wrong_kind_items = [{"id": "a1", "kind": "toolResult", "turnId": "turn",
                         "toolBatchId": "batch", "status": "completed"}]
    checked += _expect_error(lambda: assistant_from_tool_batch(
        wrong_kind_items, _unlinked(payload)),
        "Anthropic continuation assistant item is missing", "助手类型不符")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [], _unlinked(payload)),
        "Anthropic continuation assistant item is missing", "助手缺失")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant(turn="other")], _unlinked(payload)),
        "Anthropic continuation assistant belongs to another turn", "助手回合不符")
    pair = [
        {"id": "t1", "toolCallId": "c1", "toolName": "a", "turnId": "turn-a"},
        {"id": "t2", "toolCallId": "c2", "toolName": "b", "turnId": "turn-b"},
    ]
    pair[0][ANTHROPIC_CONTINUATION_FIELD] = suffix_payload
    checked += _expect_error(lambda: assistant_from_tool_batch([], pair),
                             "Anthropic continuation tools belong to different turns",
                             "工具跨回合")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant(edit=True)], _pending(payload)),
        "Signed Anthropic assistant responses cannot be context edited", "编辑后的助手")

    # 恢复拒绝：块结构、digest、长度、签名与隐藏块上限。
    def broken(**changes) -> dict:
        value = copy.deepcopy(payload)
        value.update(changes)
        return value

    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(broken(blocks="x"))),
        "Anthropic continuation block list is invalid", "块列表类型")
    unsupported = copy.deepcopy(payload)
    unsupported["blocks"].append({"type": "image"})
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(unsupported)),
        "Anthropic continuation block type is unsupported", "未知块类型")
    descriptor = copy.deepcopy(payload)
    descriptor["blocks"][0] = {"type": "text", "length": 5}
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(descriptor)),
        "Anthropic continuation content descriptor is invalid", "描述字段缺失")
    bad_digest = copy.deepcopy(payload)
    bad_digest["blocks"][0]["sha256"] = "xyz"
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(bad_digest)),
        "Anthropic continuation content digest is invalid", "摘要格式")
    negative = copy.deepcopy(payload)
    negative["blocks"][0]["length"] = -1
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(negative)),
        "Anthropic continuation content length is invalid", "负长度")
    boolean = copy.deepcopy(payload)
    boolean["blocks"][0]["length"] = True
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(boolean)),
        "Anthropic continuation content length is invalid", "布尔长度")
    text_changed = copy.deepcopy(payload)
    text_changed["blocks"][0]["sha256"] = _sha("HELLO")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(text_changed)),
        "Anthropic continuation text has changed", "正文变化")
    thinking_changed = copy.deepcopy(payload)
    thinking_changed["blocks"][1]["sha256"] = _sha("THINK")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(thinking_changed)),
        "Anthropic continuation thinking has changed", "思考变化")
    empty_signature = copy.deepcopy(payload)
    empty_signature["blocks"][1]["signature"] = ""
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(empty_signature)),
        "Anthropic continuation signature is invalid", "恢复空签名")
    big_signature = copy.deepcopy(payload)
    big_signature["blocks"][1]["signature"] = "x" * (MAX_ANTHROPIC_SIGNATURE_BYTES + 1)
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(big_signature)),
        "Anthropic continuation signature exceeds its limit", "恢复超限签名")
    empty_redacted = copy.deepcopy(payload)
    empty_redacted["blocks"].append({"type": "redactedThinking", "data": ""})
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(empty_redacted)),
        "Anthropic redacted thinking block is invalid", "恢复空隐藏块")
    big_redacted = copy.deepcopy(payload)
    big_redacted["blocks"].append({"type": "redactedThinking", "data": "汉" * 6000})
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(big_redacted)),
        "Anthropic redacted thinking exceeds its limit", "恢复超限隐藏块")
    bad_tool = copy.deepcopy(payload)
    bad_tool["blocks"][2] = {"type": "toolCall", "id": "c1", "extra": 1}
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant()], _pending(bad_tool)),
        "Anthropic continuation tool descriptor is invalid", "调用描述字段")

    # 恢复拒绝：不可持久调用之后出现内容、正文截断与缺失助手时的内容。
    after = copy.deepcopy(suffix_payload)
    after["blocks"] = [
        {"type": "toolCall", "id": "c1"},
        {"type": "toolCall", "id": "c2"},
        {"type": "text", "length": 5, "sha256": _sha("hello")},
    ]
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [], [{"id": "t1", "toolCallId": "c1", "turnId": "turn",
              ANTHROPIC_CONTINUATION_FIELD: after}]),
        "Anthropic continuation has content after an unpersisted tool call", "缺调用后内容")
    checked += _expect_error(lambda: assistant_from_tool_batch(
        [_assistant(text="hello!")], _pending(payload)),
        "Anthropic continuation does not match its assistant response", "正文截断")
    no_assistant = copy.deepcopy(payload)
    no_assistant["assistantItemId"] = None
    no_assistant["blocks"][0] = {"type": "text", "length": 1, "sha256": _sha("")}
    no_assistant["blocks"][1] = {"type": "thinking", "length": 1, "sha256": _sha(""),
                                 "signature": "sig"}
    checked += _expect_error(lambda: assistant_from_tool_batch([], _unlinked(no_assistant)),
                             "Anthropic continuation does not match its assistant response",
                             "缺失助手带内容")

    # 编码失败：签名元数据无法按 UTF-8 校验时降级为普通批次，工具调用保留。
    surrogate = assistant_from_tool_batch([_assistant(thinking="\ud800")], _pending(payload))
    checked += _expect_value([type(block).__name__ for block in surrogate.blocks],
                             ["TextBlock", "ToolCallBlock"], "编码失败降级")
    return checked


def check_continuation() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(DIGEST_FRAGMENTS, module, MODULE)
    checked += _expect(BUILD_FRAGMENTS, module, MODULE)
    checked += _expect(BATCH_FRAGMENTS, module, MODULE)
    checked += _expect(PLAIN_FRAGMENTS, module, MODULE)
    checked += _expect(RESTORE_FRAGMENTS, module, MODULE)
    # 构造：先收集调用与签名块 → 逐块描述 → 合计上限 → 末尾载荷上限。
    checked += _ordered(
        (
            "calls = [block for block in message.blocks if isinstance(block, ToolCallBlock)]",
            "has_continuation = any(",
            "total_signature_bytes = 0",
            "if (total_signature_bytes > MAX_ANTHROPIC_SIGNATURE_TOTAL_BYTES",
            'payload["blocks"] = descriptors',
        ),
        module,
        MODULE,
    )
    # 恢复：字段集合 → 版本与 provider → 前缀 digest → 调用 ID 连续前缀。
    checked += _ordered(
        (
            'set(payload) != {"version", "provider", "assistantItemId", "toolCallIds", "requestPrefix", "blocks"}',
            'payload.get("provider") != "anthropic"',
            're.fullmatch(r"[a-f0-9]{64}", prefix_digest) is None',
            "or intended_call_ids[:len(call_ids)] != call_ids):",
        ),
        module,
        MODULE,
    )
    # 逐块恢复：不可持久调用之后禁止内容 → 正文 / 思考 digest → 末尾总量核对。
    checked += _ordered(
        (
            "if missing_call_seen:",
            'if hashlib.sha256(value.encode("utf-8")).hexdigest() != content_digest:',
            "or described_calls != intended_call_ids",
        ),
        module,
        MODULE,
    )
    # 降级边界：编码失败只降级为普通批次，不得跳过一致性错误。
    if "except UnicodeEncodeError:\n        #" not in module:
        raise ValueError(f"{MODULE} 的编码失败降级必须限定在元数据恢复")
    if "ensure_ascii=True" in module:
        raise ValueError(f"{MODULE} 的摘要与载荷编码必须保留非 ASCII")
    if "hashlib.md5" in module or "hashlib.sha1" in module:
        raise ValueError(f"{MODULE} 的内容摘要必须使用 SHA-256")
    if 'sorted(payload) ==' in module:
        raise ValueError(f"{MODULE} 的续接字段必须精确匹配")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_continuation()
    except (ValueError, OSError) as error:
        print(f"续接元数据核对失败，{error}", file=sys.stderr)
        return 2
    print(f"续接元数据一致：{checked} 项预算、构造与恢复校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
