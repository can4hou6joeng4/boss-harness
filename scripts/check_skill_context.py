#!/usr/bin/env python3
"""核对技能上下文注入的数量、路径与摘要口径。

`SkillCatalog.load` 把用户选中的技能正文注入当前回合：`ids` 必须是最多 10 项
的字符串数组，去重保序；每次调用以 `list()` 重建目录映射；技能 id 必须存在，
路径固定为 `<root>/<id>/SKILL.md` 且不得越界；读取经 `_read_bounded` 受大小
限制，摘要必须与目录记录一致，否则提示重新选择；注入文本以
`<skill name={json.dumps(id)}>` 包装并以空行连接，返回的选中记录来自目录而
不是用户输入。`session.bounded_skill_ids` 则把持久记录还原为注入集合：非列表
返回空，非法项先跳过再计数、去重保序、最多 10 项且单个最多 200 字符。
除源码顺序外，本脚本在临时目录构造 `SkillCatalog` 并直接调用两个函数对照
这些边界；不启动子进程、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.resources import SkillCatalog  # noqa: E402
from boss_harness.session import (  # noqa: E402
    MAX_SKILL_ID_LENGTH,
    MAX_SKILL_IDS,
    bounded_skill_ids,
)

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"技能注入行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"技能注入行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"技能注入行为变化 {label}：期望 ValueError")


def _write_skill(root: Path, skill_id: str, name: str, body: str = "正文") -> None:
    directory = root / skill_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} 的说明\n---\n{body}",
        encoding="utf-8")


class _StaleDigestCatalog(SkillCatalog):
    def list(self) -> list[dict]:
        return [{**entry, "digest": "0" * 64} for entry in super().list()]


class _EscapedIdCatalog(SkillCatalog):
    def list(self) -> list[dict]:
        return [{**entry, "id": "/escape"} for entry in super().list()]


def _behavior_checks() -> int:
    checked = 0
    ids_message = "skillIds 必须是最多 10 项的字符串数组"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "skills"
        _write_skill(root, "skill-a", "甲")
        _write_skill(root, "skill-b", "乙")
        for index in range(2, 10):
            _write_skill(root, f"skill-{index:02d}", f"技能 {index}")
        catalog = SkillCatalog(root)
        checked += _expect_value(catalog.load(None), ("", []), "None 输入")
        checked += _expect_value(catalog.load([]), ("", []), "空列表")
        for label, ids in (
            ("非列表", "skill-a"),
            ("11 项", [f"s{index}" for index in range(11)]),
            ("重复 12 项", [f"s{index}" for index in range(6)] * 2),
            ("非字符串元素", ["skill-a", 3]),
        ):
            checked += _expect_error(lambda ids=ids: catalog.load(ids), ids_message, label)
        checked += _expect_error(lambda: catalog.load([""]), "技能不存在或不可读取", "空 id")
        checked += _expect_error(
            lambda: catalog.load(["missing"]), "技能不存在或不可读取", "未知 id")
        ten_ids = ["skill-a", "skill-b"] + [f"skill-{index:02d}" for index in range(2, 10)]
        checked += _expect_value(len(catalog.load(ten_ids)[1]), MAX_SKILL_IDS, "恰好 10 项")
        content, selected = catalog.load(["skill-b", "skill-a", "skill-b"])
        checked += _expect_value(
            [item["id"] for item in selected], ["skill-b", "skill-a"], "去重保序")
        checked += _expect_value(
            content.count('<skill name="skill-b">'), 1, "重复 id 只注入一次")
        checked += _expect_value(
            catalog.load(["skill-a"])[0],
            '<skill name="skill-a">\n---\nname: 甲\ndescription: 甲 的说明\n---\n正文\n</skill>',
            "固定包装")
        joined = catalog.load(["skill-a", "skill-b"])[0]
        checked += _expect_value(
            joined.count("</skill>\n\n<skill name="), 1, "空行分隔")
        checked += _expect_value(
            [item["name"] for item in selected], ["乙", "甲"], "选中记录来自目录")
        stale = _StaleDigestCatalog(root)
        checked += _expect_error(
            lambda: stale.load(["skill-a"]), "技能文件已变化；请重新选择", "摘要变化")
        escaped = _EscapedIdCatalog(root)
        checked += _expect_error(
            lambda: escaped.load(["/escape"]), "技能路径越界", "路径越界")

        checked += _expect_value(bounded_skill_ids(None), [], "持久 id 非列表")
        checked += _expect_value(bounded_skill_ids("skill-a"), [], "持久 id 字符串")
        checked += _expect_value(
            bounded_skill_ids([3, "", "a", "a", "b" * (MAX_SKILL_ID_LENGTH + 1),
                               "b" * MAX_SKILL_ID_LENGTH]),
            ["a", "b" * MAX_SKILL_ID_LENGTH], "持久 id 过滤去重")
        checked += _expect_value(
            bounded_skill_ids([f"s{index}" for index in range(MAX_SKILL_IDS + 2)]),
            [f"s{index}" for index in range(MAX_SKILL_IDS)], "持久 id 上限")
        checked += _expect_value(
            bounded_skill_ids([None] + [f"s{index}" for index in range(MAX_SKILL_IDS)]),
            [f"s{index}" for index in range(MAX_SKILL_IDS)], "非法项不占名额")
        checked += _expect_value(bounded_skill_ids(["b", "a", "b"]), ["b", "a"], "持久 id 顺序")
    return checked


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
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_skill_context()
    except (ValueError, SyntaxError) as error:
        print(f"技能上下文注入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能上下文注入一致：{checked} 项数量、路径、摘要与持久 id 校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
