#!/usr/bin/env python3
"""核对工具参数 schema 校验与注册表投影边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "harness/src/boss_harness/tool_schema.py"
BUNDLE = "harness/src/boss_harness/tool_bundle.py"
TYPES = "harness/src/boss_harness/models/types.py"
EXPECTED_CONSTANTS = {
    "_MAX_SCHEMA_BYTES": 128 * 1024,
    "_MAX_ARGUMENT_BYTES": 1024 * 1024,
    "_MAX_JSON_DEPTH": 64,
    "_MAX_JSON_NODES": 32768,
    "_MAX_SCHEMA_DEPTH": 32,
    "DEFAULT_MODEL_TOOL_RESULT_BYTES": 20 * 1024,
    "MIN_MODEL_TOOL_RESULT_BYTES": 8 * 1024,
    "MAX_MODEL_TOOL_RESULT_BYTES": 1024 * 1024,
}
EXPECTED_KEYWORDS = frozenset({
    "type", "properties", "required", "additionalProperties", "enum", "anyOf",
    "minimum", "maximum", "minLength", "maxLength", "pattern", "items", "minItems",
    "maxItems", "uniqueItems", "description", "title", "default",
})
EXPECTED_TYPES = frozenset({"string", "integer", "number", "boolean", "null", "object", "array"})
SCHEMA_FRAGMENTS = (
    "if depth > _MAX_SCHEMA_DEPTH or type(rule) is not dict or set(rule) - _KEYWORDS:",
    'if normalized.get("type") != "object":',
    "re.compile(rule[\"pattern\"])",
    "and rule[lower] > rule[upper]:",
    "if depth > _MAX_JSON_DEPTH or state[\"decoded_nodes\"] > _MAX_JSON_NODES:",
    "if state[\"visits\"] > _MAX_NORMALIZATION_VISITS:",
    'if not text.startswith(expected_prefix):',
    'parsed = json.loads(text, parse_constant=_reject_json_constant)',
    "expected_type = dict if kind == \"object\" else list",
    "return candidate if _matches(rule, candidate) else value",
    "copied = json.loads(_json_snapshot(arguments, maximum=_MAX_ARGUMENT_BYTES))",
    "validated = json.loads(_json_snapshot(normalized, maximum=_MAX_ARGUMENT_BYTES))",
    "if not _matches(schema, validated):",
)
BUNDLE_FRAGMENTS = (
    're.fullmatch(r"[A-Za-z0-9_-]{1,64}", name) is None',
    "not isinstance(description, str) or not description.strip()",
    "(execution_mode == \"parallel\" and requires_approval)",
    "or not MIN_MODEL_TOOL_RESULT_BYTES <= max_model_result_bytes <= MAX_MODEL_TOOL_RESULT_BYTES",
    "schema_json = canonical_schema(input_schema)",
    "validated_arguments(self._schema_json, arguments)",
    "if len({tool.name for tool in tools}) != len(tools):",
    "if type(read_only) is not bool:",
    "return frozenset(tool.name for tool in self.definitions if not read_only or not tool.requires_approval)",
    "raise ValueError(\"工具不在注册表中\")",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    values: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value
    return values


def _int_expression(node: ast.expr, values: dict[str, ast.expr],
                    seen: frozenset[str] = frozenset()) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_expression(node.left, values, seen) * _int_expression(node.right, values, seen)
    if isinstance(node, ast.Name) and node.id not in seen and node.id in values:
        return _int_expression(values[node.id], values, seen | {node.id})
    raise ValueError("工具 schema 常量必须是正整数乘积表达式")


def _literal_set(values: dict[str, ast.expr], name: str) -> frozenset[str]:
    if name not in values:
        raise ValueError(f"tool_schema.py 缺少 {name}")
    node = values[name]
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "frozenset":
        raise ValueError(f"{name} 必须是 frozenset 字面量")
    if not node.args or not isinstance(node.args[0], (ast.Set, ast.Tuple, ast.List)):
        raise ValueError(f"{name} 必须是 frozenset 字面量")
    items = frozenset(
        item.value for item in node.args[0].elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    )
    if len(items) != len(node.args[0].elts):
        raise ValueError(f"{name} 只能包含字符串字面量")
    return items


def check_tool_schema() -> tuple[int, int]:
    try:
        schema_tree = ast.parse(_read(SCHEMA))
        bundle_tree = ast.parse(_read(BUNDLE))
        types_tree = ast.parse(_read(TYPES))
    except SyntaxError:
        raise ValueError("无法解析工具 schema 源码") from None
    schema_values = _assigned(schema_tree)
    bundle_source = _read(BUNDLE)
    types_values = _assigned(types_tree)
    combined = {**schema_values, **types_values}
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in combined:
            raise ValueError(f"缺少工具 schema 常量 {name}")
        try:
            actual = _int_expression(combined[name], combined)
        except ValueError:
            raise ValueError(f"{name} 必须是正整数乘积表达式") from None
        if actual != expected:
            raise ValueError(f"{name} 必须是 {expected}，实际为 {actual}")
    if EXPECTED_CONSTANTS["_MAX_SCHEMA_BYTES"] > EXPECTED_CONSTANTS["_MAX_ARGUMENT_BYTES"]:
        raise ValueError("schema 字节上限不得大于参数字节上限")
    if EXPECTED_CONSTANTS["_MAX_SCHEMA_DEPTH"] >= EXPECTED_CONSTANTS["_MAX_JSON_DEPTH"]:
        raise ValueError("schema 深度上限必须小于 JSON 深度上限")
    if EXPECTED_CONSTANTS["MIN_MODEL_TOOL_RESULT_BYTES"] > EXPECTED_CONSTANTS["DEFAULT_MODEL_TOOL_RESULT_BYTES"]:
        raise ValueError("模型结果默认预算不得小于最小预算")
    if EXPECTED_CONSTANTS["DEFAULT_MODEL_TOOL_RESULT_BYTES"] > EXPECTED_CONSTANTS["MAX_MODEL_TOOL_RESULT_BYTES"]:
        raise ValueError("模型结果默认预算不得大于最大预算")
    keywords = _literal_set(schema_values, "_KEYWORDS")
    if keywords != EXPECTED_KEYWORDS:
        raise ValueError("tool_schema.py 的 _KEYWORDS 集合被改动")
    types = _literal_set(schema_values, "_TYPES")
    if types != EXPECTED_TYPES:
        raise ValueError("tool_schema.py 的 _TYPES 集合被改动")
    schema_source = _read(SCHEMA)
    missing = [fragment for fragment in SCHEMA_FRAGMENTS if fragment not in schema_source]
    if missing:
        raise ValueError("tool_schema.py 的校验边界缺少：" + "、".join(missing))
    missing = [fragment for fragment in BUNDLE_FRAGMENTS if fragment not in bundle_source]
    if missing:
        raise ValueError("tool_bundle.py 的注册表边界缺少：" + "、".join(missing))
    if "not isinstance(schema, Mapping)" not in schema_source:
        raise ValueError("canonical_schema 必须拒绝非 Mapping 根")
    if "except Exception:" not in schema_source or "raise ValueError(_ARGUMENT_ERROR)" not in schema_source:
        raise ValueError("参数校验失败必须统一转为受限参数错误")
    return len(EXPECTED_CONSTANTS) + 2, len(SCHEMA_FRAGMENTS) + len(BUNDLE_FRAGMENTS) + 2


def main() -> int:
    try:
        constants, guards = check_tool_schema()
    except ValueError as error:
        print(f"工具参数 schema 边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具参数边界一致：{constants} 个常量 / 集合、{guards} 项校验与投影防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
