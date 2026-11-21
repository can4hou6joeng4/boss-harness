#!/usr/bin/env python3
"""核对工具参数 schema 校验与注册表投影边界，成功时输出核对项数量。

静态部分固定常量、关键字集合与源码顺序；行为部分直接调用 `canonical_schema`
与 `validated_arguments`，覆盖受限方言注册、类型精确匹配、结构化字符串解码、
不可传递字符的错误文案与参数快照边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "harness/src/boss_harness/tool_schema.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.tool_schema import canonical_schema, validated_arguments  # noqa: E402
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


SCHEMA_ERROR = "工具参数 schema 无效或包含不支持的规则"
ARGUMENT_ERROR = "工具参数不符合已注册的 schema"
UNPASSABLE_ERROR = "工具参数包含无法作为命令行参数传递的字符（如空字符或孤立代理项），请去掉后重试"


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"工具参数行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"工具参数行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"工具参数行为变化 {label}：期望 ValueError")


def _behavior_checks() -> int:
    checked = 0
    # 注册：根必须是 Mapping 且规范化为对象；未知关键字与非法规则整体拒绝。
    checked += _expect_error(
        lambda: canonical_schema({"type": "array"}), SCHEMA_ERROR, "根必须是对象")
    checked += _expect_error(
        lambda: canonical_schema([("type", "object")]), SCHEMA_ERROR, "非 Mapping 根")
    checked += _expect_error(
        lambda: canonical_schema({"type": "object", "$ref": "x"}), SCHEMA_ERROR, "未知关键字")
    checked += _expect_value(
        canonical_schema({"type": "object", "properties": {"名": {"type": "string"}}}),
        '{"properties":{"名":{"type":"string"}},"type":"object"}', "规范化输出")
    checked += _expect_value(
        canonical_schema(types.MappingProxyType({"type": "object"})),
        '{"type":"object"}', "Mapping 根")
    invalid = (
        ("properties 非对象", {"type": "object", "properties": []}),
        ("required 重复", {"type": "object", "required": ["a", "a"]}),
        ("required 非字符串", {"type": "object", "required": [1]}),
        ("additionalProperties 非布尔", {"type": "object", "additionalProperties": 1}),
        ("enum 为空", {"type": "object", "properties": {"a": {"enum": []}}}),
        ("enum 重复", {"type": "object", "properties": {"a": {"enum": [1, 1.0]}}}),
        ("anyOf 为空", {"type": "object", "properties": {"a": {"anyOf": []}}}),
        ("长度下界为负", {"type": "object", "properties": {"a": {
            "type": "string", "minLength": -1}}}),
        ("长度上下界倒置", {"type": "object", "properties": {"a": {
            "type": "string", "minLength": 2, "maxLength": 1}}}),
        ("非法正则", {"type": "object", "properties": {"a": {
            "type": "string", "pattern": "("}}}),
        ("items 非对象", {"type": "object", "properties": {"a": {
            "type": "array", "items": 1}}}),
        ("边界非数字", {"type": "object", "properties": {"a": {
            "type": "number", "minimum": "0"}}}),
    )
    for label, schema in invalid:
        checked += _expect_error(lambda schema=schema: canonical_schema(schema), SCHEMA_ERROR, label)
    deep = {"type": "string"}
    for _ in range(34):
        deep = {"type": "object", "properties": {"a": deep}}
    checked += _expect_error(lambda: canonical_schema(deep), SCHEMA_ERROR, "schema 超深")
    # 参数校验：类型精确匹配、必填、额外属性、长度、正则与枚举。
    person = {"type": "object", "properties": {"name": {"type": "string"}},
              "required": ["name"]}
    person_json = canonical_schema(person)
    checked += _expect_value(
        validated_arguments(person_json, {"name": "x"}), {"name": "x"}, "基本参数")
    checked += _expect_value(
        validated_arguments(person_json, {"name": "x", "extra": 1}),
        {"name": "x", "extra": 1}, "额外键默认允许")
    checked += _expect_error(
        lambda: validated_arguments(
            canonical_schema({**person, "additionalProperties": False}),
            {"name": "x", "extra": 1}),
        ARGUMENT_ERROR, "额外键被拒绝")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {}), ARGUMENT_ERROR, "必填缺失")
    integer_json = canonical_schema(
        {"type": "object", "properties": {"n": {"type": "integer"}}})
    number_json = canonical_schema(
        {"type": "object", "properties": {"n": {"type": "number"}}})
    checked += _expect_value(
        validated_arguments(integer_json, {"n": 1}), {"n": 1}, "整数接受")
    checked += _expect_error(
        lambda: validated_arguments(integer_json, {"n": True}), ARGUMENT_ERROR, "整数拒绝布尔")
    checked += _expect_error(
        lambda: validated_arguments(integer_json, {"n": 1.0}), ARGUMENT_ERROR, "整数拒绝浮点")
    checked += _expect_value(
        validated_arguments(number_json, {"n": 1}), {"n": 1}, "数值接受整数")
    checked += _expect_value(
        validated_arguments(number_json, {"n": 1.5}), {"n": 1.5}, "数值接受浮点")
    checked += _expect_error(
        lambda: validated_arguments(number_json, {"n": True}), ARGUMENT_ERROR, "数值拒绝布尔")
    text_json = canonical_schema(
        {"type": "object", "properties": {"s": {
            "type": "string", "minLength": 2, "maxLength": 3}}})
    checked += _expect_value(
        validated_arguments(text_json, {"s": "ab"}), {"s": "ab"}, "长度下界通过")
    checked += _expect_error(
        lambda: validated_arguments(text_json, {"s": "a"}), ARGUMENT_ERROR, "长度下界拒绝")
    checked += _expect_error(
        lambda: validated_arguments(text_json, {"s": "abcd"}), ARGUMENT_ERROR, "长度上界拒绝")
    search_json = canonical_schema(
        {"type": "object", "properties": {"s": {"type": "string", "pattern": "b"}}})
    checked += _expect_value(
        validated_arguments(search_json, {"s": "abc"}), {"s": "abc"}, "正则子串匹配")
    checked += _expect_error(
        lambda: validated_arguments(
            canonical_schema({"type": "object", "properties": {
                "s": {"type": "string", "pattern": "^b"}}}), {"s": "abc"}),
        ARGUMENT_ERROR, "正则锚点拒绝")
    enum_json = canonical_schema(
        {"type": "object", "properties": {"v": {"type": "number", "enum": [1, 2]}}})
    checked += _expect_value(
        validated_arguments(enum_json, {"v": 1.0}), {"v": 1.0}, "枚举数值等价")
    checked += _expect_error(
        lambda: validated_arguments(enum_json, {"v": True}), ARGUMENT_ERROR, "枚举拒绝布尔")
    any_json = canonical_schema(
        {"type": "object", "properties": {"v": {
            "anyOf": [{"type": "string"}, {"type": "integer"}]}}})
    checked += _expect_value(
        validated_arguments(any_json, {"v": "x"}), {"v": "x"}, "anyOf 字符串")
    checked += _expect_value(
        validated_arguments(any_json, {"v": 3}), {"v": 3}, "anyOf 整数")
    checked += _expect_error(
        lambda: validated_arguments(any_json, {"v": 1.5}), ARGUMENT_ERROR, "anyOf 拒绝")
    array_json = canonical_schema(
        {"type": "object", "properties": {"xs": {
            "type": "array", "items": {"type": "integer"},
            "minItems": 1, "maxItems": 2, "uniqueItems": True}}})
    checked += _expect_value(
        validated_arguments(array_json, {"xs": [1, 2]}), {"xs": [1, 2]}, "数组通过")
    checked += _expect_error(
        lambda: validated_arguments(array_json, {"xs": []}), ARGUMENT_ERROR, "数组下界拒绝")
    checked += _expect_error(
        lambda: validated_arguments(array_json, {"xs": [1, 2, 3]}), ARGUMENT_ERROR, "数组上界拒绝")
    checked += _expect_error(
        lambda: validated_arguments(array_json, {"xs": [1, 1]}), ARGUMENT_ERROR, "数组重复拒绝")
    unique_json = canonical_schema(
        {"type": "object", "properties": {"xs": {
            "type": "array", "uniqueItems": True}}})
    checked += _expect_error(
        lambda: validated_arguments(unique_json, {"xs": [1, 1.0]}), ARGUMENT_ERROR, "数组数值等价重复")
    checked += _expect_value(
        validated_arguments(unique_json, {"xs": [1, True]}), {"xs": [1, True]}, "数组布尔不重复")
    # 结构化字符串：只按 schema 选中的对象 / 数组解码，失败保留原文。
    nested = {"type": "object", "properties": {"a": {
        "type": "object", "properties": {"b": {"type": "integer"}},
        "required": ["b"]}}}
    nested_json = canonical_schema(nested)
    checked += _expect_value(
        validated_arguments(nested_json, {"a": '{"b": 2}'}),
        {"a": {"b": 2}}, "对象结构化解码")
    checked += _expect_value(
        validated_arguments(
            canonical_schema({"type": "object", "properties": {
                "xs": {"type": "array", "items": {"type": "integer"}}}}),
            {"xs": "[1,2]"}), {"xs": [1, 2]}, "数组结构化解码")
    checked += _expect_value(
        validated_arguments(
            canonical_schema({"type": "object", "properties": {
                "s": {"type": "string"}}}),
            {"s": '{"b": 1}'}), {"s": '{"b": 1}'}, "字符串字段不解码")
    checked += _expect_error(
        lambda: validated_arguments(nested_json, {"a": '{"c": 2}'}),
        ARGUMENT_ERROR, "解码不符子 schema 拒绝")
    checked += _expect_error(
        lambda: validated_arguments(nested_json, {"a": "[1]"}),
        ARGUMENT_ERROR, "前缀类型不符拒绝")
    # 参数快照：不可传递字符单独点名；非 JSON、循环、超深与非字符串键统一拒绝。
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x\x00y"}),
        UNPASSABLE_ERROR, "空字符不可传递")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x\ud800y"}),
        UNPASSABLE_ERROR, "孤立代理项不可传递")
    checked += _expect_error(
        lambda: validated_arguments(person_json, []), ARGUMENT_ERROR, "非对象参数")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", "bad": float("nan")}),
        ARGUMENT_ERROR, "NaN 参数")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", "bad": (1, 2)}),
        ARGUMENT_ERROR, "元组参数")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", "bad": b"x"}),
        ARGUMENT_ERROR, "字节参数")
    cycle: dict = {}
    cycle["self"] = cycle
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", "bad": cycle}),
        ARGUMENT_ERROR, "循环参数")
    deep_args: list = []
    for _ in range(70):
        deep_args = [deep_args]
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", "bad": deep_args}),
        ARGUMENT_ERROR, "超深参数")
    checked += _expect_error(
        lambda: validated_arguments(person_json, {"name": "x", 1: "y"}),
        ARGUMENT_ERROR, "非字符串键")
    checked += _expect_error(
        lambda: validated_arguments("{", {"name": "x"}), ARGUMENT_ERROR, "非法 schema JSON")
    # 返回独立副本：顶层与嵌套对象都不共享，输入不被修改。
    arguments = {"name": "x", "meta": {"k": 1}}
    result = validated_arguments(
        canonical_schema({"type": "object", "properties": {
            "name": {"type": "string"}, "meta": {"type": "object"}}}), arguments)
    checked += _expect_value(result is arguments, False, "返回独立副本")
    checked += _expect_value(result["meta"] is arguments["meta"], False, "嵌套副本独立")
    structured = {"a": '{"b": 2}'}
    validated_arguments(nested_json, structured)
    checked += _expect_value(structured, {"a": '{"b": 2}'}, "输入不被修改")
    return checked


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
    return (len(EXPECTED_CONSTANTS) + 2,
            len(SCHEMA_FRAGMENTS) + len(BUNDLE_FRAGMENTS) + 2 + _behavior_checks())


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
