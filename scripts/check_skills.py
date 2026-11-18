#!/usr/bin/env python3
"""核对工作区技能加载的读取、枚举与列表投影边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
RPC = "harness/src/boss_harness/rpc.py"
CONSTANTS = (
    "MAX_SKILL_BYTES",
    "MAX_SKILL_DESCRIPTORS",
    "MAX_EXISTING_SKILL_ID",
    "MAX_SKILL_NAME_CHARS",
    "MAX_SKILL_DESCRIPTION_CHARS",
    "MAX_SKILL_SCAN_ENTRIES",
)
READ_FRAGMENTS = (
    'getattr(os, "O_NOFOLLOW", 0)',
    "os.O_NONBLOCK",
    "opened.st_dev != observed.st_dev",
    "opened.st_ino != observed.st_ino",
    "handle.read(cls.MAX_SKILL_BYTES + 1)",
)
SCAN_FRAGMENTS = (
    "os.scandir(self.root)",
    "entry.is_dir(follow_symlinks=False)",
    'path = self.root / entry.name / "SKILL.md"',
    "with entries:",
    "if self._root_is_symlink:",
    "技能目录不能是符号链接；请改为工作区内的普通目录",
    "limit = min(limit * 2, self.MAX_SKILL_SCAN_ENTRIES)",
)
PROJECTION_FRAGMENTS = (
    'descriptor["name"] = name[:cls.MAX_SKILL_NAME_CHARS]',
    'descriptor["description"] = description[:cls.MAX_SKILL_DESCRIPTION_CHARS]',
    "problems[:self.MAX_SKILL_DESCRIPTORS]",
)
FORBIDDEN_ENUMERATION = re.compile(r"\.(?:glob|rglob|iterdir)\(")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _parse(relative: str) -> ast.Module:
    try:
        return ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


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
        return (_int_expression(node.left, values, seen)
                * _int_expression(node.right, values, seen))
    if isinstance(node, ast.Name) and node.id not in seen and node.id in values:
        return _int_expression(values[node.id], values, seen | {node.id})
    raise ValueError("技能常量必须是正整数表达式")


def check_skills() -> tuple[int, int, int]:
    text = _read(RESOURCES)
    values = _assigned(_parse(RESOURCES))
    constants: dict[str, int] = {}
    for name in CONSTANTS:
        if name not in values:
            raise ValueError(f"resources.py 缺少技能常量 {name}")
        try:
            constants[name] = _int_expression(values[name], values)
        except ValueError:
            raise ValueError(f"resources.py 的 {name} 必须是正整数表达式") from None
    rpc_values = _assigned(_parse(RPC))
    if "MAX_FRAME_BYTES" not in rpc_values:
        raise ValueError("rpc.py 缺少 MAX_FRAME_BYTES")
    frame = _int_expression(rpc_values["MAX_FRAME_BYTES"], rpc_values)
    if constants["MAX_SKILL_SCAN_ENTRIES"] < constants["MAX_SKILL_DESCRIPTORS"]:
        raise ValueError("MAX_SKILL_SCAN_ENTRIES 不得小于 MAX_SKILL_DESCRIPTORS")
    if constants["MAX_SKILL_BYTES"] > frame:
        raise ValueError("MAX_SKILL_BYTES 不得超过内核 MAX_FRAME_BYTES")
    for fragment in READ_FRAGMENTS:
        if fragment not in text:
            raise ValueError(f"resources.py 的技能读取缺少：{fragment}")
    for fragment in SCAN_FRAGMENTS:
        if fragment not in text:
            raise ValueError(f"resources.py 的技能枚举缺少：{fragment}")
    for fragment in PROJECTION_FRAGMENTS:
        if fragment not in text:
            raise ValueError(f"resources.py 的技能投影缺少：{fragment}")
    start = text.find("class SkillCatalog:")
    if start < 0:
        raise ValueError("resources.py 缺少 SkillCatalog")
    end = text.find("\nclass ", start + 1)
    catalog = text[start:] if end < 0 else text[start:end]
    match = FORBIDDEN_ENUMERATION.search(catalog)
    if match is not None:
        raise ValueError(f"SkillCatalog 不得使用 {match.group(0)} 枚举技能目录")
    return (len(constants), len(READ_FRAGMENTS) + len(SCAN_FRAGMENTS),
            len(PROJECTION_FRAGMENTS))


def main() -> int:
    try:
        constants, guards, projections = check_skills()
    except ValueError as error:
        print(f"工作区技能边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工作区技能边界一致：{constants} 个常量、{guards} 项读取 / 枚举防护、"
          f"{projections} 项投影上限")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
