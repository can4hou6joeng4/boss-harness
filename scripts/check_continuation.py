#!/usr/bin/env python3
"""核对 Anthropic 私有续接元数据的预算、构造与恢复校验。

continuation.py 只保存签名块的描述而不是重复正文：请求前缀 digest 绑定模型可见
前缀，构造与恢复都必须拒绝超限签名、重复引用、跨回合批次与被编辑的助手消息。
任一放宽都会让未验证的签名进入下一次请求，或让损坏记录反复阻断分支，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/continuation.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

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
    return checked + 1


def main() -> int:
    try:
        checked = check_continuation()
    except ValueError as error:
        print(f"续接元数据核对失败，{error}", file=sys.stderr)
        return 2
    print(f"续接元数据一致：{checked} 项预算、构造与恢复防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
