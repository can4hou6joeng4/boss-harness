#!/usr/bin/env python3
"""对照内核搜索的跨码点聚类与归一化行为。

`session._search_clusters` 把基字符与组合记号、谚文 jamo、半角假名浊音符号、
`GRAPHEME_V_EXTRA` 相邻码点并入同一簇，返回原文起止索引与
`NFKC + casefold`（或补表的 `search_normalize`）片段。调用方依赖索引在
片段与查询之间建立映射。本脚本直接导入内核函数做行为对照，并扫描
`session.py` 固定合并条件与两处调用点；它不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import _search_clusters  # noqa: E402

CASES = (
    ("", []),
    ("abc", [(0, 1, "a"), (1, 2, "b"), (2, 3, "c")]),
    ("A", [(0, 1, "a")]),
    ("é", [(0, 2, "é")]),
    ("á̧", [(0, 3, "á̧")]),
    ("Ａ", [(0, 1, "a")]),
    ("ß", [(0, 1, "ss")]),
    ("가", [(0, 2, "가")]),
    ("ㄱㅏ", [(0, 2, "가")]),
    ("각", [(0, 2, "각")]),
    ("가나", [(0, 1, "가"), (1, 2, "나")]),
    ("ｶﾞ", [(0, 2, "ガ")]),
    ("カﾞ", [(0, 2, "ガ")]),
    ("ｶ", [(0, 1, "カ")]),
    ("ﾞ", [(0, 1, "゙")]),
    ("각ᄀ", [(0, 2, "각ᄀ")]),
)
MIXED = ("aé가나ｶﾞé", "ㄱㅏ각각ᄀ", "ＡßｶﾞA")
CLUSTER_ORDER = (
    "def _search_clusters(value: str, normalize: Callable[[str], str] | None = None",
    "index = 0",
    "length = len(value)",
    "while index < length:",
    "end = index + 1",
    "hangul = _is_hangul_letter(value[index]) or _is_hangul_syllable(value[index])",
    "while end < length and (",
    "is_grapheme_extend(ord(value[end]))",
    "or (hangul and _is_hangul_letter(value[end]))",
    "or value[end] in _HALFWIDTH_VOICED_MARKS",
    "or (ord(value[end - 1]) in GRAPHEME_V_EXTRA and ord(value[end]) in GRAPHEME_V_EXTRA)",
    "part = value[index:end]",
    'yield index, end, (unicodedata.normalize("NFKC", part).casefold()',
    "if normalize is None else normalize(part))",
    "index = end",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_search_clusters() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    cluster = _function(tree, source, "_search_clusters")
    checked = _ordered(CLUSTER_ORDER, cluster, SESSION)
    # 每簇至少一个码点，且索引在循环末尾前移。
    if cluster.count("end = index + 1") != 1:
        raise ValueError(f"{SESSION} 的聚类每簇至少一个码点")
    checked += 1
    if cluster.count("index = end") != 1 or "index = end +" in cluster:
        raise ValueError(f"{SESSION} 的聚类必须从上一簇末尾继续")
    checked += 1
    # 四类合并条件各一处，缺一都会漏掉跨码点命中。
    if cluster.count("is_grapheme_extend(ord(value[end]))") != 1:
        raise ValueError(f"{SESSION} 的聚类必须并入组合记号")
    checked += 1
    if cluster.count("hangul and _is_hangul_letter(value[end])") != 1:
        raise ValueError(f"{SESSION} 的聚类必须并入谚文 jamo")
    checked += 1
    if cluster.count("_HALFWIDTH_VOICED_MARKS") != 1:
        raise ValueError(f"{SESSION} 的聚类必须并入半角浊音符号")
    checked += 1
    if cluster.count("ord(value[end - 1]) in GRAPHEME_V_EXTRA and ord(value[end]) in GRAPHEME_V_EXTRA") != 1:
        raise ValueError(f"{SESSION} 的聚类必须并入相邻扩展 V 码点")
    checked += 1
    # 归一化：默认 NFKC + casefold，只有传入 normalize 时替换。
    if cluster.count('unicodedata.normalize("NFKC", part).casefold()') != 1:
        raise ValueError(f"{SESSION} 的聚类默认必须 NFKC + casefold")
    checked += 1
    if cluster.count("if normalize is None else normalize(part)") != 1:
        raise ValueError(f"{SESSION} 的聚类必须支持补表归一化")
    checked += 1
    # 调用方必须使用返回的原文区间。
    if source.count("for index, end, part in _search_clusters(value, normalize):") != 2:
        raise ValueError(f"{SESSION} 必须有两处按区间消费聚类")
    checked += 1
    # 行为对照：逐用例比较完整输出。
    for value, expected in CASES:
        actual = list(_search_clusters(value))
        if actual != expected:
            raise ValueError(f"{SESSION} 的聚类结果变化：{value!r} → {actual!r}")
        checked += 1
    # 区间首尾相接、覆盖全文、严格递增。
    for value in MIXED:
        clusters = list(_search_clusters(value))
        position = 0
        for start, end, part in clusters:
            if start != position or end <= start or not part:
                raise ValueError(f"{SESSION} 的聚类区间不连续：{value!r} → {clusters!r}")
            position = end
        if position != len(value):
            raise ValueError(f"{SESSION} 的聚类必须覆盖全文：{value!r}")
        checked += 1
    # 补表归一化逐簇调用，参数是原文片段。
    calls: list[str] = []

    def normalize(part: str) -> str:
        calls.append(part)
        return "<" + part + ">"

    value = "ｶﾞé"
    clusters = list(_search_clusters(value, normalize))
    if calls != ["ｶﾞ", "é"] or [part for _, _, part in clusters] != ["<ｶﾞ>", "<é>"]:
        raise ValueError(f"{SESSION} 的补表归一化必须逐簇调用：{calls!r}")
    checked += 1
    # 归一化结果再聚类保持稳定。
    for value in MIXED:
        once = "".join(part for _, _, part in _search_clusters(value))
        twice = "".join(part for _, _, part in _search_clusters(once))
        if once != twice:
            raise ValueError(f"{SESSION} 的聚类归一化不幂等：{value!r}")
        checked += 1
    # 普通路径与 NFKC + casefold 逐簇一致。
    for value in MIXED:
        for start, end, part in _search_clusters(value):
            expected = unicodedata.normalize("NFKC", value[start:end]).casefold()
            if part != expected:
                raise ValueError(f"{SESSION} 的聚类片段与 NFKC 不一致：{value!r}")
        checked += 1
    return checked


def main() -> int:
    try:
        checked = check_search_clusters()
    except (ValueError, SyntaxError) as error:
        print(f"搜索聚类核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索聚类一致：{checked} 项行为与结构校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
