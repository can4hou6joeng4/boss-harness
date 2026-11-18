"""内核搜索归一化使用的 Unicode 增量映射。

桌面 ``kernelSearchText`` 与内核搜索共用同一步骤：NFKC → casefold，但两边的
Unicode 数据源不同：桌面跟随 Node（Node 24 / ICU 78.3 为 Unicode 17.0），内核
跟随 Python（3.10 → 13.0、3.11 → 14.0、3.12 → 15.0、3.13 → 15.1、3.14 → 16.0）。
版本差异会让同一文本在两个入口得到不同的归一化结果，例如 Python ≤ 3.13 不折叠
Garay 大写字母，Python ≤ 3.11 不分解 Unicode 15 的西里尔修饰字母。

下面几张表只收录受支持 Python 相对桌面运行时缺少的映射：``_NFKC_EXTRA``
是 Unicode 17 新增的兼容分解，``_CANON_DECOMP_EXTRA`` / ``_COMPOSE_EXTRA``
是新增的规范分解与合成对，``_CASEFOLD_EXTRA`` 在 casefold 之前补齐差异。
运行时已应用映射时原码点不再出现，重复套用保持幂等；Unicode 的大小写映射与
已分配码点的分解一经分配即保持稳定。

映射以桌面运行时为准。升级 Node 的 Unicode 版本或调整最低 Python 版本后，对
全部码点逐一比较 ``search_normalize(chr(cp))`` 与桌面 ``kernelSearchText``，
按差异增删条目；半角假名、谚文组合等跨码点规则由 ``session._search_clusters``
负责，不在这两张表内。

``_GRAPHEME_EXTEND_EXTRA`` 与 ``_CCC_EXTRA`` 处理另一层差异：桌面按
Unicode 17 的字素属性合并组合记号，并按组合类做规范排序；受支持 Python
相对缺少部分码点与类别。含补表码点时先用 NFKD 全分解、按桌面组合类稳定重排
再逐对合成，避免运行时的旧组合类错误阻塞合成。
"""
from __future__ import annotations

import re
import unicodedata

_NFKC_EXTRA = str.maketrans({
    # Unicode 14 新增的拉丁修饰 / 上标字母兼容分解。
    0xA7F2: "C",
    0xA7F3: "F",
    0xA7F4: "Q",
    0x10781: "\u02d0",
    0x10782: "\u02d1",
    0x10783: "\u00e6",
    0x10784: "\u0299",
    0x10785: "\u0253",
    0x10787: "\u02a3",
    0x10788: "\uab66",
    0x10789: "\u02a5",
    0x1078A: "\u02a4",
    0x1078B: "\u0256",
    0x1078C: "\u0257",
    0x1078D: "\u1d91",
    0x1078E: "\u0258",
    0x1078F: "\u025e",
    0x10790: "\u02a9",
    0x10791: "\u0264",
    0x10792: "\u0262",
    0x10793: "\u0260",
    0x10794: "\u029b",
    0x10795: "\u0127",
    0x10796: "\u029c",
    0x10797: "\u0267",
    0x10798: "\u0284",
    0x10799: "\u02aa",
    0x1079A: "\u02ab",
    0x1079B: "\u026c",
    0x1079C: "\U0001df04",
    0x1079D: "\ua78e",
    0x1079E: "\u026e",
    0x1079F: "\U0001df05",
    0x107A0: "\u028e",
    0x107A1: "\U0001df06",
    0x107A2: "\u00f8",
    0x107A3: "\u0276",
    0x107A4: "\u0277",
    0x107A5: "q",
    0x107A6: "\u027a",
    0x107A7: "\U0001df08",
    0x107A8: "\u027d",
    0x107A9: "\u027e",
    0x107AA: "\u0280",
    0x107AB: "\u02a8",
    0x107AC: "\u02a6",
    0x107AD: "\uab67",
    0x107AE: "\u02a7",
    0x107AF: "\u0288",
    0x107B0: "\u2c71",
    0x107B2: "\u028f",
    0x107B3: "\u02a1",
    0x107B4: "\u02a2",
    0x107B5: "\u0298",
    0x107B6: "\u01c0",
    0x107B7: "\u01c1",
    0x107B8: "\u01c2",
    0x107B9: "\U0001df0a",
    0x107BA: "\U0001df1e",
    # Unicode 15 新增的西里尔修饰字母 U+1E030–U+1E06D。
    **{0x1E030 + offset: chr(0x430 + offset) for offset in range(0x9)},  # U+1E030–U+1E038
    **{0x1E03C + offset: chr(0x43E + offset) for offset in range(0xB)},  # U+1E03C–U+1E046
    **{0x1E051 + offset: chr(0x430 + offset) for offset in range(0x9)},  # U+1E051–U+1E059
    **{0x1E05F + offset: chr(0x443 + offset) for offset in range(0x6)},  # U+1E05F–U+1E064
    0x1E039: "\u043a",
    0x1E03A: "\u043b",
    0x1E03B: "\u043c",
    0x1E047: "\u044b",
    0x1E048: "\u044d",
    0x1E049: "\u044e",
    0x1E04A: "\ua689",
    0x1E04B: "\u04d9",
    0x1E04C: "\u0456",
    0x1E04D: "\u0458",
    0x1E04E: "\u04e9",
    0x1E04F: "\u04af",
    0x1E050: "\u04cf",
    0x1E05A: "\u043a",
    0x1E05B: "\u043b",
    0x1E05C: "\u043e",
    0x1E05D: "\u043f",
    0x1E05E: "\u0441",
    0x1E065: "\u044a",
    0x1E066: "\u044b",
    0x1E067: "\u0491",
    0x1E068: "\u0456",
    0x1E069: "\u0455",
    0x1E06A: "\u045f",
    0x1E06B: "\u04ab",
    0x1E06C: "\ua651",
    0x1E06D: "\u04b1",
    # Unicode 16 新增的 outlined 字母与数字 U+1CCD6–U+1CCF9，分解为 A–Z / 0–9。
    **{0x1CCD6 + offset: chr(0x41 + offset) for offset in range(0x1A)},  # U+1CCD6–U+1CCEF
    **{0x1CCF0 + offset: chr(0x30 + offset) for offset in range(0xA)},  # U+1CCF0–U+1CCF9
    # Unicode 17 新增的 modifier 大写 S，分解为 S。
    0xA7F1: "S",
})

_CASEFOLD_EXTRA = str.maketrans({
    # Unicode 14 新增：格拉哥里大写 U+2C2F、拉丁大写 U+A7C0 / A7D0 / A7D6 / A7D8
    # 与 Vithkuqi 大写 U+10570–U+10595。
    **{0x10570 + offset: chr(0x10597 + offset) for offset in range(0xB)},  # U+10570–U+1057A
    **{0x1057C + offset: chr(0x105A3 + offset) for offset in range(0xF)},  # U+1057C–U+1058A
    **{0x1058C + offset: chr(0x105B3 + offset) for offset in range(0x7)},  # U+1058C–U+10592
    0x2C2F: "\u2c5f",
    0xA7C0: "\ua7c1",
    0xA7D0: "\ua7d1",
    0xA7D6: "\ua7d7",
    0xA7D8: "\ua7d9",
    0x10594: "\U000105bb",
    0x10595: "\U000105bc",
    # Unicode 16 新增：西里尔大写 U+1C89、拉丁大写 U+A7CB / A7CC / A7DA / A7DC
    # 与 Garay 大写 U+10D50–U+10D65。
    **{0x10D50 + offset: chr(0x10D70 + offset) for offset in range(0x16)},  # U+10D50–U+10D65
    0x1C89: "\u1c8a",
    0xA7CB: "\u0264",
    0xA7CC: "\ua7cd",
    0xA7DA: "\ua7db",
    0xA7DC: "\u019b",
    # Unicode 17 新增：拉丁大写 U+A7CE / A7D2 / A7D4 与 Beria Erfe 大写
    # U+16EA0–U+16EB8。
    **{0x16EA0 + offset: chr(0x16EBB + offset) for offset in range(0x19)},  # U+16EA0–U+16EB8
    0xA7CE: "\ua7cf",
    0xA7D2: "\ua7d3",
    0xA7D4: "\ua7d5",
})


# 桌面 Unicode 17 字素属性中可并入前一簇、但受支持 Python 未识别为组合记号
# (Extend / ZWJ / SpacingMark) 的码点；由 Node 24 的 Intl.Segmenter 与
# Unicode 17 GraphemeBreakProperty.txt 对齐生成。
_GRAPHEME_EXTEND_EXTRA = frozenset(
    code for group in (
        0x897,
        0xE33,
        0xEB3,
        range(0x1ACF, 0x1ADD + 1),
        range(0x1AE0, 0x1AEB + 1),
        range(0x200C, 0x200D + 1),
        range(0xFF9E, 0xFF9F + 1),
        range(0x10D69, 0x10D6D + 1),
        range(0x10EFA, 0x10EFC + 1),
        range(0x113B8, 0x113C0 + 1),
        0x113C2,
        0x113C5,
        range(0x113C7, 0x113CA + 1),
        range(0x113CC, 0x113D0 + 1),
        0x113D2,
        range(0x113E1, 0x113E2 + 1),
        range(0x11B60, 0x11B67 + 1),
        0x11F5A,
        range(0x1611E, 0x1612F + 1),
        range(0x1E5EE, 0x1E5EF + 1),
        0x1E6E3,
        0x1E6E6,
        range(0x1E6EE, 0x1E6EF + 1),
        0x1E6F5,
        range(0x1F3FB, 0x1F3FF + 1),
        range(0xE0020, 0xE007F + 1),
    ) for code in (group if isinstance(group, range) else (group,))
)

# 上述码点中 Unicode 17 仍带非零组合类的部分；其余按 ccc=0 处理。
# Python NFKC 对未知码点不作规范排序，补表后需要按此类别重排。
_CCC_EXTRA = {
    0x897: 230, 0x1ACF: 230, 0x1AD0: 230, 0x1AD1: 230, 0x1AD2: 230, 0x1AD3: 230, 0x1AD4: 230, 0x1AD5: 230, 0x1AD6: 230, 0x1AD7: 230, 0x1AD8: 230, 0x1AD9: 230, 0x1ADA: 230, 0x1ADB: 230, 0x1ADC: 230, 0x1ADD: 220, 0x1AE0: 230, 0x1AE1: 230, 0x1AE2: 230, 0x1AE3: 230, 0x1AE4: 230, 0x1AE5: 230, 0x1AE6: 220, 0x1AE7: 230, 0x1AE8: 230, 0x1AE9: 230, 0x1AEA: 230, 0x1AEB: 234, 0x10D69: 230, 0x10D6A: 230, 0x10D6B: 230, 0x10D6C: 230, 0x10D6D: 230, 0x10EFA: 220, 0x10EFB: 220, 0x113CE: 9, 0x113CF: 9, 0x113D0: 9, 0x1612F: 9, 0x1E5EE: 230, 0x1E5EF: 220, 0x1E6E3: 230, 0x1E6E6: 230, 0x1E6EE: 230, 0x1E6EF: 230, 0x1E6F5: 230,
}


# Unicode 17 已把这些旧版记号移出 Extend/SpacingMark；内核不应再按 Python
# 运行时的旧类别把它们并入前一簇，否则桌面会把它们当独立字素，命中映射不同。
_GRAPHEME_EXTEND_RETIRED = frozenset((
    code for group in (
        0x102B, 0x102C, 0x1038,
        range(0x1062, 0x1064 + 1),
        range(0x1067, 0x106D + 1),
        0x1083,
        range(0x1087, 0x108C + 1),
        0x108F,
        range(0x109A, 0x109C + 1),
        range(0x11720, 0x11721 + 1),
        0x1A61, 0x1A63, 0x1A64, 0xAA7B, 0xAA7D,
    ) for code in (group if isinstance(group, range) else (group,))
))


def is_grapheme_extend(code: int) -> bool:
    """该码点是否应按桌面字素规则并入前一簇。"""
    if code in _GRAPHEME_EXTEND_RETIRED:
        return False
    codepoint = chr(code)
    return (bool(unicodedata.combining(codepoint))
            or unicodedata.category(codepoint) in {"Mn", "Mc", "Me"}
            or code in _GRAPHEME_EXTEND_EXTRA)


def extra_combining_class(code: int) -> int:
    """桌面 Unicode 17 的组合类；运行时已有数据时以运行时为准。"""
    return unicodedata.combining(chr(code)) or _CCC_EXTRA.get(code, 0)


def _extra_pattern() -> re.Pattern[str]:
    """合并所有补表码点；规范分解键与部件也要触发慢路径。"""
    canon_codes = set(_CANON_DECOMP_EXTRA)
    for parts in _CANON_DECOMP_EXTRA.values():
        canon_codes.update(parts)
    ranges: list[list[int]] = []
    for code in sorted({*_NFKC_EXTRA, *_CASEFOLD_EXTRA, *_GRAPHEME_EXTEND_EXTRA, *canon_codes}):
        if ranges and code == ranges[-1][1] + 1:
            ranges[-1][1] = code
        else:
            ranges.append([code, code])
    body = "".join(
        re.escape(chr(low)) if low == high else f"{re.escape(chr(low))}-{re.escape(chr(high))}"
        for low, high in ranges)
    return re.compile(f"[{body}]")


# 桌面 Unicode 17 字素规则中的 Kirat Rai V：相邻的 V 必须与前面的 V/L/V
# 留在同一簇，否则逐簇归一化无法合成 U+16D68 / U+16D69 / U+16D6A。
GRAPHEME_V_EXTRA = frozenset((0x16D63, 0x16D67, 0x16D68, 0x16D69, 0x16D6A))


_CANON_DECOMP_EXTRA = {
    0x105C9: (0x105D2, 0x0307), 0x105E4: (0x105DA, 0x0307),
    0x11383: (0x11382, 0x113C9), 0x11385: (0x11384, 0x113BB),
    0x1138E: (0x1138B, 0x113C2), 0x11391: (0x11390, 0x113C9),
    0x113C5: (0x113C2, 0x113C2), 0x113C7: (0x113C2, 0x113B8),
    0x113C8: (0x113C2, 0x113C9),
    0x16121: (0x1611E, 0x1611E), 0x16122: (0x1611E, 0x16129),
    0x16123: (0x1611E, 0x1611F), 0x16124: (0x16129, 0x1611F),
    0x16125: (0x1611E, 0x16120), 0x16126: (0x16121, 0x1611F),
    0x16127: (0x16122, 0x1611F), 0x16128: (0x16121, 0x16120),
    0x16D68: (0x16D67, 0x16D67), 0x16D69: (0x16D63, 0x16D67),
    0x16D6A: (0x16D69, 0x16D67),
}
_COMPOSE_EXTRA = {parts: chr(code) for code, parts in _CANON_DECOMP_EXTRA.items()}

_EXTRA_PATTERN = _extra_pattern()
_RECURSION_LIMIT = 16


def needs_extra(value: str) -> bool:
    """文本是否包含补表码点；不含时可直接走普通 NFKC + casefold。"""
    return _EXTRA_PATTERN.search(value) is not None


def _expand_canonical(code: int, seen: frozenset[int] = frozenset()) -> str:
    """递归展开运行时未收录的 Unicode 17 规范分解。"""
    parts = _CANON_DECOMP_EXTRA.get(code)
    if parts is None or code in seen:
        return chr(code)
    return "".join(_expand_canonical(part, seen | {code}) for part in parts)


def _canonical_order(chars: list[str]) -> list[str]:
    """按桌面 Unicode 17 的组合类稳定合并记号，不改变 starter 的相对位置。"""
    if len(chars) < 2:
        return list(chars)
    result: list[str] = []
    pending: list[tuple[int, str]] = []
    for char in chars:
        value = extra_combining_class(ord(char))
        if value == 0:
            if pending:
                result.extend(item[1] for item in sorted(pending, key=lambda item: item[0]))
                pending.clear()
            result.append(char)
        else:
            pending.append((value, char))
    if pending:
        result.extend(item[1] for item in sorted(pending, key=lambda item: item[0]))
    return result


def _compose_pair(first: str, second: str, cache: dict[tuple[str, str], str | None]) -> str | None:
    """按桌面规则合成一对 NFKD 稳定的字符。"""
    key = (first, second)
    if key in cache:
        return cache[key]
    target = _COMPOSE_EXTRA.get((ord(first), ord(second)))
    if target is None:
        candidate = unicodedata.normalize("NFC", first + second)
        target = candidate if len(candidate) == 1 else None
    cache[key] = target
    return target


def _canonical_compose(chars: list[str]) -> str:
    """按桌面 Unicode 17 的组合类与合成表单遍合成。"""
    result: list[str] = []
    starter = -1
    last_class = 0
    cache: dict[tuple[str, str], str | None] = {}
    for char in chars:
        canonical_class = extra_combining_class(ord(char))
        composed = None
        if starter >= 0 and (len(result) == starter + 1
                             or (canonical_class and last_class < canonical_class)):
            composed = _compose_pair(result[starter], char, cache)
        if composed is not None:
            result[starter] = composed
            continue
        if canonical_class == 0:
            starter = len(result)
        result.append(char)
        last_class = canonical_class
    return "".join(result)


def search_normalize(value: str) -> str:
    """按桌面字素簇的 NFKC + casefold 规则归一化补齐运行时 Unicode 数据。"""
    if not needs_extra(value):
        return unicodedata.normalize("NFKC", value).casefold()
    decomposed = unicodedata.normalize("NFKD", value).translate(_NFKC_EXTRA)
    expanded = "".join(_expand_canonical(ord(char)) for char in decomposed)
    decomposed = unicodedata.normalize("NFKD", expanded)
    composed = _canonical_compose(_canonical_order(list(decomposed)))
    return composed.casefold().translate(_CASEFOLD_EXTRA)
