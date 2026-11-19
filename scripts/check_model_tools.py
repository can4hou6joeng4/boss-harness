#!/usr/bin/env python3
"""核对模型可见结果读取工具的模式、预算与错误映射边界。

model_tools.py 向模型暴露唯一的只读内核工具：模式只接受 itemId、sha256、
cursor 与有界 limit，读取只返回当前会话已保存结果的有界分段并携带摘要绑定，
大结果不得整份回灌；错误统一为固定码，陈旧引用透传 currentRef。任一放宽都会
让模型读到越权数据或把完整大结果反复注入上下文，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/model_tools.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

SPEC_FRAGMENTS = (
    'MODEL_RESULT_READ_TOOL = "read_session_tool_result"\n',
    "    MODEL_RESULT_READ_CHARS, canonical_result_text, read_result_text_chunk,",
    "_RESULT_READ_SCHEMA = canonical_schema({",
    '"itemId": {"type": "string", "minLength": 1, "maxLength": 128},',
    '"sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},',
    '"cursor": {"type": "string", "maxLength": 2048},',
    '"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},',
    '"required": ["itemId", "sha256"],',
    '"additionalProperties": False,',
    "MODEL_RESULT_READ_SPEC = ToolSpec(",
    "name=MODEL_RESULT_READ_TOOL,",
    "读取当前会话中大工具结果的精确 JSON 分段",
    "每次最多 {MODEL_RESULT_READ_CHARS} 个 Unicode 字符",
    "此操作只读已保存记录，不调用招聘平台",
    "max_model_result_bytes=64 * 1024,",
)
FUNCTION_FRAGMENTS = (
    "def model_tool_specs(tools: tuple[ToolSpec, ...]) -> tuple[ToolSpec, ...]:",
    "if any(tool.name == MODEL_RESULT_READ_TOOL for tool in tools):",
    'raise ValueError("工具名称与 Harness 内核工具冲突")',
    "return (*tools, MODEL_RESULT_READ_SPEC)",
    "def validate_model_result_read(arguments: dict[str, Any]) -> dict[str, Any]:",
    "return validated_arguments(_RESULT_READ_SCHEMA, arguments)",
    "def read_model_tool_result(sessions: SessionStore, thread_id: str, arguments: dict[str, Any]) -> ToolResult:",
    "arguments = validate_model_result_read(arguments)",
    'item_id = arguments["itemId"]',
    "item = sessions.read_item(thread_id, item_id)",
    "if item is None:",
    'error={"code": "INVALID_RESULT_REFERENCE", "message": "结果不存在或不属于当前会话"})',
    'if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):',
    'raise ValueError("该条目没有可读取的完整工具结果")',
    'text = canonical_result_text(item["result"])',
    "chunk = read_result_text_chunk(thread_id, item_id, text, sha256=arguments[\"sha256\"],",
    "cursor=arguments.get(\"cursor\"),",
    "limit=arguments.get(\"limit\", MODEL_RESULT_READ_CHARS))",
    "except ItemLookupError as exc:",
    'error={"code": exc.code, "message": str(exc)})',
    "except RpcError as exc:",
    'code = exc.data.get("code") if isinstance(exc.data, dict) else None',
    'error = {"code": code if isinstance(code, str) else "RESULT_READ_FAILED",',
    '"message": str(exc)}',
    'current_ref = exc.data.get("currentRef") if isinstance(exc.data, dict) else None',
    "if isinstance(current_ref, dict):",
    'error["currentRef"] = current_ref',
    "except ValueError as exc:",
    "return ToolResult(ok=True, command=MODEL_RESULT_READ_TOOL, data=chunk)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "模型可按 item ID、摘要和游标每次读取至多 8,192 个 Unicode 字符"),
    (TECHNICAL_REFERENCE, "读取只访问当前会话已保存的数据，不重新调用招聘工具"),
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


def check_model_tools() -> int:
    module = _read(MODULE)
    checked = _expect(SPEC_FRAGMENTS, module, MODULE)
    checked += _expect(FUNCTION_FRAGMENTS, module, MODULE)
    # 模式：四字段按顺序 → 必需字段 → 禁止额外字段。
    checked += _ordered(
        (
            '"itemId": {"type": "string", "minLength": 1, "maxLength": 128},',
            '"sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},',
            '"cursor": {"type": "string", "maxLength": 2048},',
            '"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},',
            '"required": ["itemId", "sha256"],',
            '"additionalProperties": False,',
        ),
        module,
        MODULE,
    )
    # 读取：校验 → 会话查找 → 缺失拒绝 → 条目形状 → 规范化正文 → 有界分段。
    checked += _ordered(
        (
            "arguments = validate_model_result_read(arguments)",
            "item = sessions.read_item(thread_id, item_id)",
            "if item is None:",
            'if item.get("kind") != "toolCall"',
            'text = canonical_result_text(item["result"])',
            "chunk = read_result_text_chunk(",
        ),
        module,
        MODULE,
    )
    # 错误映射：条目查找 → RpcError → 数值校验。
    checked += _ordered(
        (
            "except ItemLookupError as exc:",
            "except RpcError as exc:",
            "except ValueError as exc:",
        ),
        module,
        MODULE,
    )
    # 反向断言：不得整份回灌、不得复制字符常量、必须禁止额外字段。
    if "data=item" in module or "data=text" in module:
        raise ValueError(f"{MODULE} 的读取结果不得整份回灌模型")
    if "MODEL_RESULT_READ_CHARS = 8_192" in module:
        raise ValueError(f"{MODULE} 的读取字符上限必须沿用工具结果常量")
    if '"maximum": 8192' in module or '"maximum": 8_192' in module:
        raise ValueError(f"{MODULE} 的模式必须引用共享常量")
    if '"additionalProperties": True' in module:
        raise ValueError(f"{MODULE} 的模式不得允许额外字段")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_model_tools()
    except ValueError as error:
        print(f"模型结果读取工具核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型结果读取工具一致：{checked} 项模式、预算与错误映射防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
