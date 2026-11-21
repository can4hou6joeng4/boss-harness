#!/usr/bin/env python3
"""核对技能 frontmatter 解析与列表投影的截断口径。

`SkillCatalog._fields` 只解析起始 `---` 与独立结束行之间的 `name` /
`description`：起始行允许 BOM 前缀并按 `strip()` 判定，结束线必须是整行
`---`（值中的三连字符不能提前结束），值去除包裹的引号。`_descriptor` 以
`fields.get` 提供缺省值（名称回退技能 id、描述为空串），超过 200 / 500
字符时截断并分别写 `nameTruncated` / `descriptionTruncated`，未超限不写
标记。这里按源码顺序固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

FIELDS_ORDER = (
    "def _fields(source: str) -> dict[str, str]:",
    "fields: dict[str, str] = {}",
    'lines = source.removeprefix("\ufeff").splitlines()',
    'if not lines or lines[0].strip() != "---":',
    "return fields",
    'closing = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)',
    "if closing is None:",
    "return fields",
    "for line in lines[1:closing]:",
    'match = re.match(r"^(name|description):\\s*(.+)$", line)',
    "if match:",
    'fields[match[1]] = match[2].strip("\\"\'")',
    "return fields",
)
DESCRIPTOR_ORDER = (
    "def _descriptor(cls, skill_id: str, fields: dict[str, str], digest: str, byte_length: int) -> dict:",
    'name = fields.get("name", skill_id)',
    'description = fields.get("description", "")',
    'descriptor: dict[str, Any] = {"id": skill_id, "name": name, "description": description,',
    '"digest": digest, "bytes": byte_length}',
    "if len(name) > cls.MAX_SKILL_NAME_CHARS:",
    'descriptor["name"] = name[:cls.MAX_SKILL_NAME_CHARS]',
    'descriptor["nameTruncated"] = True',
    "if len(description) > cls.MAX_SKILL_DESCRIPTION_CHARS:",
    'descriptor["description"] = description[:cls.MAX_SKILL_DESCRIPTION_CHARS]',
    'descriptor["descriptionTruncated"] = True',
    "return descriptor",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SkillCatalog":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SkillCatalog.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_skill_descriptor() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    fields = _method(tree, source, "_fields")
    descriptor = _method(tree, source, "_descriptor")
    checked = _ordered(FIELDS_ORDER, fields, RESOURCES)
    checked += _ordered(DESCRIPTOR_ORDER, descriptor, RESOURCES)
    # frontmatter：BOM、整行起始与结束、字段白名单、引号去除。
    if fields.count('source.removeprefix("﻿").splitlines()') != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 必须去除 BOM 后按行解析")
    checked += 1
    if fields.count('lines[0].strip() != "---"') != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 起始行必须按整行判定")
    checked += 1
    if fields.count('line.strip() == "---"') != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 结束行必须按整行判定")
    checked += 1
    if fields.count("lines[1:]") != 1 or fields.count("lines[1:closing]") != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 必须只解析起始与结束之间")
    checked += 1
    if fields.count('re.match(r"^(name|description):\\s*(.+)$", line)') != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 必须只提取两个字段")
    checked += 1
    if fields.count('match[2].strip("\\"\'")') != 1:
        raise ValueError(f"{RESOURCES} 的 frontmatter 值必须去除包裹引号")
    checked += 1
    # 投影：缺省值、基础字段、两处截断与标记。
    if descriptor.count('fields.get("name", skill_id)') != 1:
        raise ValueError(f"{RESOURCES} 的技能名必须回退到 id")
    checked += 1
    if descriptor.count('fields.get("description", "")') != 1:
        raise ValueError(f"{RESOURCES} 的技能描述必须允许缺省")
    checked += 1
    if descriptor.count('{"id": skill_id, "name": name, "description": description,') != 1:
        raise ValueError(f"{RESOURCES} 的技能投影必须包含基础字段")
    checked += 1
    if descriptor.count('"digest": digest, "bytes": byte_length}') != 1:
        raise ValueError(f"{RESOURCES} 的技能投影必须包含摘要与字节数")
    checked += 1
    if descriptor.count("if len(name) > cls.MAX_SKILL_NAME_CHARS:") != 1:
        raise ValueError(f"{RESOURCES} 的技能名必须按上限截断")
    checked += 1
    if descriptor.count("name[:cls.MAX_SKILL_NAME_CHARS]") != 1:
        raise ValueError(f"{RESOURCES} 的技能名截断长度必须取常量")
    checked += 1
    if descriptor.count('descriptor["nameTruncated"] = True') != 1:
        raise ValueError(f"{RESOURCES} 的技能名截断必须标记")
    checked += 1
    if descriptor.count("if len(description) > cls.MAX_SKILL_DESCRIPTION_CHARS:") != 1:
        raise ValueError(f"{RESOURCES} 的技能描述必须按上限截断")
    checked += 1
    if descriptor.count("description[:cls.MAX_SKILL_DESCRIPTION_CHARS]") != 1:
        raise ValueError(f"{RESOURCES} 的技能描述截断长度必须取常量")
    checked += 1
    if descriptor.count('descriptor["descriptionTruncated"] = True') != 1:
        raise ValueError(f"{RESOURCES} 的技能描述截断必须标记")
    checked += 1
    # 标记只在对应分支出现，且截断写回在标记之前。
    name_end = descriptor.index('descriptor["nameTruncated"] = True')
    if descriptor.index('descriptor["name"] = name[:cls.MAX_SKILL_NAME_CHARS]') > name_end:
        raise ValueError(f"{RESOURCES} 的技能名必须先截断再标记")
    checked += 1
    description_end = descriptor.index('descriptor["descriptionTruncated"] = True')
    if descriptor.index('descriptor["description"] = description[:cls.MAX_SKILL_DESCRIPTION_CHARS]') > description_end:
        raise ValueError(f"{RESOURCES} 的技能描述必须先截断再标记")
    checked += 1
    if descriptor.count("Truncated") != 2:
        raise ValueError(f"{RESOURCES} 的技能投影必须只有两个截断标记")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_skill_descriptor()
    except (ValueError, SyntaxError) as error:
        print(f"技能投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能投影一致：{checked} 项 frontmatter 与截断校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
