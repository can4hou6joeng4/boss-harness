#!/usr/bin/env python3
"""对照内核搜索归一化入口的索引映射与 identity 判定。

`SessionStore._search_normalized` 把文本按组合簇归一化，并在需要时返回
每个归一化字符对应的原文起止索引：ASCII 直接小写；非 ASCII 逐簇归一化，
所有簇都是单码点且折叠后仍是单字符时不保留索引，否则用 `array('I')`
紧凑存放两列索引。`search_messages` 依赖该索引把命中映射回原文片段。
本脚本直接导入内核函数做行为对照，并扫描 `session.py` 的快速路径、
identity 判定与两次聚类遍历；它不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.search_unicode import search_normalize  # noqa: E402
from boss_harness.session import SessionStore, _search_clusters  # noqa: E402

NORMALIZED = SessionStore._search_normalized

CASES = (
    ("", ("", None, None)),
    ("abc", ("abc", None, None)),
    ("ABC", ("abc", None, None)),
    ("é", ("é", None, None)),
    ("é", ("é", (0,), (2,))),
    ("á̧", ("á̧", (0, 0), (3, 3))),
    ("Ａ", ("a", None, None)),
    ("ß", ("ss", (0, 0), (1, 1))),
    ("İ", ("i̇", (0, 0), (1, 1))),
    ("ㄱㅏ", ("가", (0,), (2,))),
    ("각", ("각", (0,), (2,))),
    ("ｶﾞ", ("ガ", (0,), (2,))),
    ("カﾞ", ("ガ", (0,), (2,))),
    ("각ᄀ", ("각ᄀ", (0, 0), (2, 2))),
    ("ꟲ", ("c", None, None)),
    ("Aꟲ", ("ac", None, None)),
    ("ꟲé", ("cé", (0, 1), (1, 3))),
    ("İß", ("i̇ss", (0, 0, 1, 1), (1, 1, 2, 2))),
    ("Ａé", ("aé", (0, 1), (1, 3))),
    ("\ud800", ("\ud800", None, None)),
)
MIXED = (
    "aé가나ｶﾞé",
    "ㄱㅏ각각ᄀ",
    "ＡßｶﾞA",
    "ȩ́İ",
    "ꟲé",
)
NORMALIZED_ORDER = (
    "def _search_normalized(value: str) -> tuple[str, array.array | None, array.array | None]:",
    "if value.isascii():",
    "return value.lower(), None, None",
    "normalize = search_normalize if needs_extra(value) else None",
    "parts = io.StringIO()",
    "identity = True",
    "for index, end, part in _search_clusters(value, normalize):",
    "if not part:",
    "parts.write(part)",
    "identity = False",
    "normalized = parts.getvalue()",
    "if identity:",
    "return normalized, None, None",
    'starts = array.array("I")',
    'ends = array.array("I")',
    "starts.extend([index] * len(part))",
    "ends.extend([end] * len(part))",
    "return normalized, starts, ends",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_search_index() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    normalized = _method(tree, source, "SessionStore", "_search_normalized")
    checked = _ordered(NORMALIZED_ORDER, normalized, SESSION)
    # ASCII 快速路径是唯一小写出口，且不保留索引。
    if normalized.count("value.isascii()") != 1:
        raise ValueError(f"{SESSION} 的 ASCII 快速路径必须唯一")
    checked += 1
    if normalized.count("None, None") != 2:
        raise ValueError(f"{SESSION} 的 identity 与 ASCII 出口必须返回空索引")
    checked += 1
    # identity 只在一个位置置假，判定必须同时看码点数与折叠长度。
    if "if end - index != 1 or len(part) != 1:\n                identity = False" not in normalized:
        raise ValueError(f"{SESSION} 的 identity 判定必须覆盖码点数与折叠长度")
    checked += 1
    if normalized.count("identity = False") != 1 or normalized.count("if identity:") != 1:
        raise ValueError(f"{SESSION} 的 identity 必须单点置假且只判一次")
    checked += 1
    # 空片段跳过，两轮遍历共用同一聚类调用。
    if normalized.count("if not part:") != 1:
        raise ValueError(f"{SESSION} 的归一化必须跳过空片段")
    checked += 1
    if normalized.count("for index, end, part in _search_clusters(value, normalize):") != 2:
        raise ValueError(f"{SESSION} 的归一化必须两轮聚类遍历")
    checked += 1
    if normalized.rindex("for index, end, part in _search_clusters(value, normalize):") < normalized.index('ends = array.array("I")'):
        raise ValueError(f"{SESSION} 的索引必须在 identity 判定后重建")
    checked += 1
    # 索引用紧凑数组，长度按折叠结果展开。
    if normalized.count('array.array("I")') != 2:
        raise ValueError(f"{SESSION} 的索引必须用两个紧凑数组")
    checked += 1
    if "starts = [" in normalized or "ends = [" in normalized:
        raise ValueError(f"{SESSION} 的索引不得退化为 Python 列表")
    checked += 1
    if normalized.count("len(part)") != 3:
        raise ValueError(f"{SESSION} 的索引必须按折叠长度展开")
    checked += 1
    # 补表只在含补表码点时启用，且不绕过聚类归一化。
    if normalized.count("normalize = search_normalize if needs_extra(value) else None") != 1:
        raise ValueError(f"{SESSION} 的补表归一化必须只在一处启用")
    checked += 1
    if "unicodedata" in normalized:
        raise ValueError(f"{SESSION} 的归一化不得绕过聚类默认分支")
    checked += 1
    # 定义与调用点唯一：查询与正文各一次。
    if source.count("def _search_normalized(") != 1:
        raise ValueError(f"{SESSION} 必须只定义一处归一化入口")
    checked += 1
    if source.count("self._search_normalized(") != 2:
        raise ValueError(f"{SESSION} 的归一化入口必须被查询与正文各调用一次")
    checked += 1
    # 行为对照：完整三元组逐用例比较。
    for value, expected in CASES:
        actual = NORMALIZED(value)
        starts = None if actual[1] is None else tuple(actual[1])
        ends = None if actual[2] is None else tuple(actual[2])
        if (actual[0], starts, ends) != expected:
            raise ValueError(f"{SESSION} 的归一化结果变化：{value!r} → {actual!r}")
        checked += 1
    # 非 identity 文本：索引与逐簇重建一致、单调且覆盖原文。
    for value in MIXED:
        text, starts, ends = NORMALIZED(value)
        if starts is None or ends is None:
            raise ValueError(f"{SESSION} 的跨簇文本必须保留索引：{value!r}")
        if len(starts) != len(text) or len(ends) != len(text):
            raise ValueError(f"{SESSION} 的索引长度必须等于折叠长度：{value!r}")
        rebuilt_starts: list[int] = []
        rebuilt_ends: list[int] = []
        for index, end, part in _search_clusters(value, search_normalize):
            rebuilt_starts.extend([index] * len(part))
            rebuilt_ends.extend([end] * len(part))
        if list(starts) != rebuilt_starts or list(ends) != rebuilt_ends:
            raise ValueError(f"{SESSION} 的索引必须与逐簇重建一致：{value!r}")
        checked += 1
        position = 0
        for start, end in zip(starts, ends):
            if start < position or end < start or end > len(value):
                raise ValueError(f"{SESSION} 的索引必须单调且覆盖原文：{value!r}")
            position = start
        checked += 1
        # 折叠文本与补表逐簇拼接一致；无补表时也与默认分支一致。
        rebuilt = "".join(part for _, _, part in _search_clusters(value, search_normalize))
        if text != rebuilt:
            raise ValueError(f"{SESSION} 的折叠文本必须与逐簇拼接一致：{value!r}")
        checked += 1
        if "ꟲ" not in value:
            plain = "".join(part for _, _, part in _search_clusters(value))
            if text != plain:
                raise ValueError(f"{SESSION} 的无补表文本必须与默认分支一致：{value!r}")
            checked += 1
    return checked


def main() -> int:
    try:
        checked = check_search_index()
    except (ValueError, SyntaxError) as error:
        print(f"搜索索引核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索索引一致：{checked} 项归一化、索引与补表校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
