#!/usr/bin/env python3
"""核对技能上下文注入的数量、路径与摘要口径。

`SkillCatalog.load` 把用户选中的技能正文注入当前回合：`ids` 必须是最多 10 项
的字符串数组，去重保序；每次调用以 `list()` 重建目录映射；技能 id 必须存在，
路径固定为 `<root>/<id>/SKILL.md` 且不得越界；读取经 `_read_bounded` 受大小
限制，摘要必须与目录记录一致，否则提示重新选择；注入文本以
`<skill name={json.dumps(id)}>` 包装并以空行连接，返回的选中记录来自目录而
不是用户输入。这里按源码顺序固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

LOAD_ORDER = (
    "def load(self, ids: Any) -> tuple[str, list[dict]]:",
    "if ids is None:",
    'return "", []',
    "if not isinstance(ids, list) or len(ids) > 10 or any(not isinstance(i, str) for i in ids):",
    'raise ValueError("skillIds 必须是最多 10 项的字符串数组")',
    "if not ids:",
    'return "", []',
    'catalog = {skill["id"]: skill for skill in self.list()}',
    "selected, content = [], []",
    "for skill_id in dict.fromkeys(ids):",
    "if skill_id not in catalog:",
    'raise ValueError("技能不存在或不可读取")',
    'path = self.root / skill_id / "SKILL.md"',
    "if not path.parent.is_relative_to(self.root):",
    'raise ValueError("技能路径越界")',
    "loaded = self._read_bounded(path)",
    "if loaded is None:",
    'raise ValueError("技能文件不可读取或超过大小限制")',
    "source, _, digest = loaded",
    'if digest != catalog[skill_id]["digest"]:',
    'raise ValueError("技能文件已变化；请重新选择")',
    "selected.append(catalog[skill_id])",
    'content.append(f"<skill name={json.dumps(skill_id)}>\\n{source}\\n</skill>")',
    'return "\\n\\n".join(content), selected',
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


def check_skill_context() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    load = _method(tree, source, "load")
    checked = _ordered(LOAD_ORDER, load, RESOURCES)
    # 输入边界：最多 10 项、元素必须是字符串、去重保序。
    if load.count("len(ids) > 10") != 1:
        raise ValueError(f"{RESOURCES} 的技能 ids 必须限制为 10 项")
    checked += 1
    if load.count("any(not isinstance(i, str) for i in ids)") != 1:
        raise ValueError(f"{RESOURCES} 的技能 ids 必须全部是字符串")
    checked += 1
    if load.count("dict.fromkeys(ids)") != 1:
        raise ValueError(f"{RESOURCES} 的技能 ids 必须去重保序")
    checked += 1
    if load.count('return "", []') != 2:
        raise ValueError(f"{RESOURCES} 的技能上下文必须有两处空结果早退")
    checked += 1
    # 目录映射：每次调用重建，选中记录必须来自目录。
    if load.count('{skill["id"]: skill for skill in self.list()}') != 1:
        raise ValueError(f"{RESOURCES} 的技能目录必须在每次调用时重建")
    checked += 1
    if load.count("selected.append(catalog[skill_id])") != 1:
        raise ValueError(f"{RESOURCES} 的选中技能必须来自目录记录")
    checked += 1
    # 路径：固定 SKILL.md 且不得越界。
    if load.count('path = self.root / skill_id / "SKILL.md"') != 1:
        raise ValueError(f"{RESOURCES} 的技能路径必须固定为 SKILL.md")
    checked += 1
    if load.count("path.parent.is_relative_to(self.root)") != 1:
        raise ValueError(f"{RESOURCES} 的技能路径必须核对根目录")
    checked += 1
    # 读取：有界读取一次，摘要必须一致。
    if load.count("self._read_bounded(path)") != 1:
        raise ValueError(f"{RESOURCES} 的技能正文必须只读取一次")
    checked += 1
    if load.count('if digest != catalog[skill_id]["digest"]:') != 1:
        raise ValueError(f"{RESOURCES} 的技能摘要必须与目录一致")
    checked += 1
    if load.count('raise ValueError("技能文件已变化；请重新选择")') != 1:
        raise ValueError(f"{RESOURCES} 的技能变化必须有产品错误")
    checked += 1
    # 注入：名称 JSON 转义、固定包装、空行分隔。
    if load.count("json.dumps(skill_id)") != 1:
        raise ValueError(f"{RESOURCES} 的技能名必须 JSON 转义")
    checked += 1
    if load.count('f"<skill name={json.dumps(skill_id)}>') != 1:
        raise ValueError(f"{RESOURCES} 的技能正文必须有固定开始标签")
    checked += 1
    if load.count("</skill>") != 1:
        raise ValueError(f"{RESOURCES} 的技能正文必须有固定结束标签")
    checked += 1
    if load.count('return "\\n\\n".join(content), selected') != 1:
        raise ValueError(f"{RESOURCES} 的技能正文必须以空行分隔")
    checked += 1
    # 顺序：摘要校验通过后才记录选中与追加正文。
    digest_check = load.index('if digest != catalog[skill_id]["digest"]:')
    if load.index("selected.append(catalog[skill_id])") < digest_check:
        raise ValueError(f"{RESOURCES} 的选中技能必须在摘要校验之后记录")
    checked += 1
    if load.index("content.append(") < digest_check:
        raise ValueError(f"{RESOURCES} 的技能正文必须在摘要校验之后追加")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_skill_context()
    except (ValueError, SyntaxError) as error:
        print(f"技能上下文注入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能上下文注入一致：{checked} 项数量、路径与摘要校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
