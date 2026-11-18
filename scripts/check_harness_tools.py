#!/usr/bin/env python3
"""核对内核默认工具允许清单的静态边界。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS_SOURCE = ROOT / "harness/src/boss_harness/tools/boss_cli.py"
EXPECTED_TOOLS = frozenset({
    "boss_search",
    "boss_detail",
    "boss_recommend",
    "boss_chat",
    "boss_status",
    "boss_stats",
    "boss_hr_jobs",
    "boss_hr_jobs_detail",
    "boss_hr_recommendations",
    "boss_hr_candidates",
    "boss_hr_chat",
    "boss_hr_resume",
    "boss_hr_greet",
    "boss_list_tools",
})
WRITE_TOOLS = frozenset({"boss_hr_greet"})


def _literal_dict(node: ast.AST, where: str) -> dict[str, ast.AST]:
    if not isinstance(node, ast.Dict):
        raise ValueError(f"{where} 必须是字典字面量")
    fields: dict[str, ast.AST] = {}
    for key, value in zip(node.keys, node.values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ValueError(f"{where} 的键必须是字符串字面量")
        fields[key.value] = value
    return fields


def _string(fields: dict[str, ast.AST], key: str, where: str) -> str:
    node = fields.get(key)
    if (
        not isinstance(node, ast.Constant)
        or not isinstance(node.value, str)
        or not node.value.strip()
    ):
        raise ValueError(f"{where} 缺少非空字符串 {key}")
    return node.value


def _bool(fields: dict[str, ast.AST], key: str, where: str) -> bool:
    node = fields.get(key)
    if not isinstance(node, ast.Constant) or not isinstance(node.value, bool):
        raise ValueError(f"{where} 缺少布尔值 {key}")
    return node.value


def _tools_tuple(tree: ast.Module) -> ast.Tuple:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "TOOLS"
            for target in targets
        ):
            continue
        if not isinstance(node.value, ast.Tuple):
            raise ValueError("TOOLS 必须是元组字面量")
        return node.value
    raise ValueError("harness/src/boss_harness/tools/boss_cli.py 缺少 TOOLS 元组")


def _check_schema(node: ast.AST, where: str) -> None:
    fields = _literal_dict(node, f"{where} 的 input_schema")
    schema_type = fields.get("type")
    if (
        not isinstance(schema_type, ast.Constant)
        or schema_type.value != "object"
    ):
        raise ValueError(f"{where} 的 input_schema.type 必须是 object")
    properties = fields.get("properties")
    if not isinstance(properties, ast.Dict):
        raise ValueError(f"{where} 的 input_schema.properties 必须是字典字面量")
    declared: set[str] = set()
    for key in properties.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise ValueError(f"{where} 的 input_schema.properties 键必须是字符串字面量")
        declared.add(key.value)
    required_node = fields.get("required")
    if not isinstance(required_node, ast.List):
        raise ValueError(f"{where} 的 input_schema.required 必须是列表字面量")
    required: list[str] = []
    for item in required_node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise ValueError(f"{where} 的 input_schema.required 只能包含字符串字面量")
        required.append(item.value)
    if len(set(required)) != len(required):
        raise ValueError(f"{where} 的 input_schema.required 不得重复")
    unknown = sorted(set(required) - declared)
    if unknown:
        raise ValueError(
            f"{where} 的 input_schema.required 含未声明属性：" + "、".join(unknown)
        )
    additional = fields.get("additionalProperties")
    if not isinstance(additional, ast.Constant) or additional.value is not False:
        raise ValueError(f"{where} 的 input_schema.additionalProperties 必须是 False")


def check_harness_tools() -> tuple[int, int]:
    tree = ast.parse(
        TOOLS_SOURCE.read_text(encoding="utf-8"), filename=str(TOOLS_SOURCE)
    )
    tools = _tools_tuple(tree)
    names: list[str] = []
    approval: set[str] = set()
    for index, element in enumerate(tools.elts, start=1):
        where = f"TOOLS 的第 {index} 项"
        fields = _literal_dict(element, where)
        name = _string(fields, "name", where)
        _string(fields, "description", where)
        if "handler" not in fields:
            raise ValueError(f"{where} 缺少 handler")
        if _bool(fields, "requires_approval", where):
            approval.add(name)
        schema = fields.get("input_schema")
        if schema is None:
            raise ValueError(f"{where} 缺少 input_schema")
        _check_schema(schema, where)
        names.append(name)
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError("TOOLS 工具名重复：" + "、".join(duplicates))
    if set(names) != EXPECTED_TOOLS:
        missing = sorted(EXPECTED_TOOLS - set(names))
        extra = sorted(set(names) - EXPECTED_TOOLS)
        raise ValueError(
            "TOOLS 工具名与允许清单不一致：缺少 " + ("、".join(missing) or "无")
            + "；多出 " + ("、".join(extra) or "无")
        )
    if approval != WRITE_TOOLS:
        raise ValueError(
            "TOOLS 的需批准工具应恰为 boss_hr_greet，实际为："
            + ("、".join(sorted(approval)) or "无")
        )
    return len(names), len(names) - len(approval)


def main() -> int:
    try:
        total, read_only = check_harness_tools()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"内核工具允许清单核对失败，{error}", file=sys.stderr)
        return 2
    print(
        f"内核工具允许清单一致：{total} 个工具"
        f"（{read_only} 个只读、{total - read_only} 个需批准）、schema 边界完整"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
