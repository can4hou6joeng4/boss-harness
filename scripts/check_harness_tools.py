#!/usr/bin/env python3
"""核对内核默认工具允许清单的静态边界。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS_SOURCE = ROOT / "harness/src/boss_harness/tools/boss_cli.py"
CONTEXT_SOURCE = ROOT / "harness/src/boss_harness/context.py"
TOOL_RESULTS_SOURCE = ROOT / "harness/src/boss_harness/tool_results.py"
BUNDLE_SOURCE = ROOT / "harness/src/boss_harness/tools/bundle.py"
HARNESS_PACKAGE = ROOT / "harness/src/boss_harness"
SHELL_APIS = (
    ("shell=True", "不得以 shell=True 启动子进程"),
    ("create_subprocess_shell(", "不得使用 create_subprocess_shell"),
    ("os.system(", "不得使用 os.system"),
    ("os.popen(", "不得使用 os.popen"),
)
BUNDLE_FRAGMENTS = (
    "handlers = tool_handlers()",
    "approval_required = approval_required_tools()",
    'name=spec["name"]',
    'description=spec["description"]',
    'input_schema=spec["input_schema"]',
    'requires_approval=spec["name"] in approval_required',
    "for spec in TOOLS",
)
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


def _frozenset_literal(node: ast.AST, where: str) -> set[str]:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Name)
        or node.func.id != "frozenset"
        or len(node.args) != 1
        or node.keywords
    ):
        raise ValueError(f"{where} 必须是 frozenset 字面量")
    items = node.args[0]
    if not isinstance(items, (ast.Set, ast.List, ast.Tuple)):
        raise ValueError(f"{where} 必须是 frozenset 字面量")
    values: set[str] = set()
    for item in items.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise ValueError(f"{where} 只能包含字符串字面量")
        values.add(item.value)
    return values


def _assigned_frozenset(path: Path, name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            continue
        return _frozenset_literal(node.value, f"{path.name} 的 {name}")
    raise ValueError(f"{path.name} 缺少 {name}")


def _write_tools_default(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        positional = node.args.posonlyargs + node.args.args
        defaults = node.args.defaults
        if not defaults:
            continue
        for argument, default in zip(positional[-len(defaults):], defaults):
            if argument.arg == "write_tools":
                return _frozenset_literal(
                    default, f"{path.name} 的 write_tools 默认值"
                )
    raise ValueError(f"{path.name} 缺少 write_tools 默认值")


def check_harness_tools() -> tuple[int, int, int, int, int]:
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
    write_sets = (
        ("context.py 的 _WRITE_TOOLS", _assigned_frozenset(CONTEXT_SOURCE, "_WRITE_TOOLS")),
        ("context.py 的 write_tools 默认值", _write_tools_default(CONTEXT_SOURCE)),
        (
            "tool_results.py 的 LEGACY_WRITE_TOOLS",
            _assigned_frozenset(TOOL_RESULTS_SOURCE, "LEGACY_WRITE_TOOLS"),
        ),
    )
    for label, values in write_sets:
        if values != WRITE_TOOLS:
            raise ValueError(
                f"{label} 应恰为 boss_hr_greet，实际为："
                + ("、".join(sorted(values)) or "无")
            )
    bundle_text = BUNDLE_SOURCE.read_text(encoding="utf-8")
    missing = [fragment for fragment in BUNDLE_FRAGMENTS if fragment not in bundle_text]
    if missing:
        raise ValueError(
            "bundle.py 的工具组合必须沿用 TOOLS 与审批标记："
            + "、".join(missing)
        )
    for path in sorted(HARNESS_PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token, message in SHELL_APIS:
            if token in text:
                raise ValueError(
                    f"{message}：{path.relative_to(ROOT).as_posix()}"
                )
    if "shell=False" not in TOOLS_SOURCE.read_text(encoding="utf-8"):
        raise ValueError("boss_cli.py 的 subprocess.Popen 必须显式设置 shell=False")
    return (
        len(names),
        len(names) - len(approval),
        len(write_sets),
        len(BUNDLE_FRAGMENTS),
        len(SHELL_APIS) + 1,
    )


def main() -> int:
    try:
        total, read_only, write_sets, bundle, shell = check_harness_tools()
    except (OSError, SyntaxError, ValueError) as error:
        print(f"内核工具允许清单核对失败，{error}", file=sys.stderr)
        return 2
    print(
        f"内核工具允许清单一致：{total} 个工具"
        f"（{read_only} 个只读、{total - read_only} 个需批准）、"
        f"schema 边界完整、{write_sets} 处写工具集合一致、"
        f"bundle 保留 {bundle} 项审批投影、工具子进程 {shell} 项 shell 边界完整"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
