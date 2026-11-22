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
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.model_tools import (  # noqa: E402
    MODEL_RESULT_READ_SPEC,
    MODEL_RESULT_READ_TOOL,
    model_tool_specs,
    validate_model_result_read,
)
from boss_harness.models.types import ToolSpec  # noqa: E402
from boss_harness.tool_results import MODEL_RESULT_READ_CHARS  # noqa: E402

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


ARGUMENT_ERROR = "工具参数不符合已注册的 schema"
UNPASSABLE_ERROR = "工具参数包含无法作为命令行参数传递的字符（如空字符或孤立代理项），请去掉后重试"


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型结果读取工具行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"模型结果读取工具行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"模型结果读取工具行为变化 {label}：期望错误 {message!r}，实际未抛出")


def _spec(name: str) -> ToolSpec:
    return ToolSpec(name=name, description="说明", input_schema={"type": "object"})


def _behavior_checks() -> int:
    checked = 0
    existing = (_spec("boss_hr_greet"), _spec("boss_schema"))
    combined = model_tool_specs(existing)
    checked += _expect_value(combined[:2], existing, "保留既有工具")
    checked += _expect_value(combined[2] is MODEL_RESULT_READ_SPEC, True, "追加只读工具")
    checked += _expect_value(model_tool_specs(()), (MODEL_RESULT_READ_SPEC,), "空清单追加")
    try:
        model_tool_specs((_spec(MODEL_RESULT_READ_TOOL),))
    except ValueError as error:
        checked += _expect_value(str(error), "工具名称与 Harness 内核工具冲突", "重名拒绝")
    else:
        raise ValueError("模型结果读取工具行为变化 重名冲突：期望 ValueError，实际未抛出")

    valid = {"itemId": "item-1", "sha256": "a" * 64}
    arguments = validate_model_result_read(valid)
    checked += _expect_value(arguments, valid, "合法参数")
    checked += _expect_value(arguments is valid, False, "独立副本")
    arguments["itemId"] = "改动"
    checked += _expect_value(valid["itemId"], "item-1", "副本不修改输入")
    bounded = {"itemId": "i" * 128, "sha256": "0" * 64, "cursor": "c" * 2048,
               "limit": MODEL_RESULT_READ_CHARS}
    checked += _expect_value(validate_model_result_read(bounded), bounded, "边界参数")
    checked += _expect_value(validate_model_result_read(
        {"itemId": "i" * 128, "sha256": "0" * 64, "limit": 1}),
        {"itemId": "i" * 128, "sha256": "0" * 64, "limit": 1}, "最小分段")

    for label, payload in (
        ("缺少摘要", {"itemId": "item-1"}),
        ("缺少条目", {"sha256": "a" * 64}),
        ("空条目", {"itemId": "", "sha256": "a" * 64}),
        ("条目过长", {"itemId": "i" * 129, "sha256": "a" * 64}),
        ("摘要大写", {"itemId": "item-1", "sha256": "A" * 64}),
        ("摘要过短", {"itemId": "item-1", "sha256": "a" * 63}),
        ("游标过长", {"itemId": "item-1", "sha256": "a" * 64, "cursor": "c" * 2049}),
        ("分段为零", {"itemId": "item-1", "sha256": "a" * 64, "limit": 0}),
        ("分段超限", {"itemId": "item-1", "sha256": "a" * 64,
                      "limit": MODEL_RESULT_READ_CHARS + 1}),
        ("分段浮点", {"itemId": "item-1", "sha256": "a" * 64, "limit": 1.0}),
        ("分段布尔", {"itemId": "item-1", "sha256": "a" * 64, "limit": True}),
        ("额外字段", {"itemId": "item-1", "sha256": "a" * 64, "extra": 1}),
        ("非对象参数", ["item-1"]),
    ):
        checked += _expect_error(lambda payload=payload: validate_model_result_read(payload),
                                 ARGUMENT_ERROR, label)
    checked += _expect_error(
        lambda: validate_model_result_read({"itemId": "a\x00", "sha256": "a" * 64}),
        UNPASSABLE_ERROR, "空字符条目")

    checked += _expect_value(MODEL_RESULT_READ_SPEC.name, MODEL_RESULT_READ_TOOL, "工具名称")
    checked += _expect_value(MODEL_RESULT_READ_SPEC.max_model_result_bytes, 64 * 1024,
                             "结果字节上限")
    schema = MODEL_RESULT_READ_SPEC.input_schema
    checked += _expect_value(schema["additionalProperties"], False, "禁止额外字段")
    checked += _expect_value(schema["required"], ["itemId", "sha256"], "必填字段")
    checked += _expect_value(schema["properties"]["limit"]["maximum"], MODEL_RESULT_READ_CHARS,
                             "分段上限")
    checked += _expect_value(MODEL_RESULT_READ_CHARS, 8_192, "字符常量")
    checked += _expect_value("8192 个 Unicode 字符" in MODEL_RESULT_READ_SPEC.description, True,
                             "描述上限")
    checked += _expect_value("不调用招聘平台" in MODEL_RESULT_READ_SPEC.description, True,
                             "描述只读")
    return checked


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
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"模型结果读取工具核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型结果读取工具一致：{checked} 项模式、预算与错误映射防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
