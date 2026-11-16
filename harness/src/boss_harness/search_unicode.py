"""内核搜索归一化使用的 Unicode 增量映射。

桌面 ``kernelSearchText`` 与内核搜索共用同一步骤：NFKC → casefold，但两边的
Unicode 数据源不同：桌面跟随 Node（Node 24 / ICU 78.3 为 Unicode 17.0），内核
跟随 Python（3.10 → 13.0、3.11 → 14.0、3.12 → 15.0、3.13 → 15.1、3.14 → 16.0）。
版本差异会让同一文本在两个入口得到不同的归一化结果，例如 Python ≤ 3.13 不折叠
Garay 大写字母，Python ≤ 3.11 不分解 Unicode 15 的西里尔修饰字母。

下面两张表只收录受支持 Python 相对桌面运行时缺少的映射，逐码点补在对应步骤
之后：``_NFKC_EXTRA`` 在 NFKC 之后、casefold 之前，``_CASEFOLD_EXTRA`` 在
casefold 之后。运行时已应用映射时原码点不再出现，重复套用保持幂等；Unicode 的
大小写映射一经分配即保持稳定，NFKC 兼容分解对已有码点也不会改写。

映射以桌面运行时为准。升级 Node 的 Unicode 版本或调整最低 Python 版本后，对
全部码点逐一比较 ``search_normalize(chr(cp))`` 与桌面 ``kernelSearchText``，
按差异增删条目；半角假名、谚文组合等跨码点规则由 ``session._search_clusters``
负责，不在这两张表内。
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


def _extra_pattern() -> re.Pattern[str]:
    """合并两张表的源码点为字符类，用于快速判断文本是否可能命中补表。"""
    ranges: list[list[int]] = []
    for code in sorted({*_NFKC_EXTRA, *_CASEFOLD_EXTRA}):
        if ranges and code == ranges[-1][1] + 1:
            ranges[-1][1] = code
        else:
            ranges.append([code, code])
    body = "".join(
        re.escape(chr(low)) if low == high else f"{re.escape(chr(low))}-{re.escape(chr(high))}"
        for low, high in ranges)
    return re.compile(f"[{body}]")


_EXTRA_PATTERN = _extra_pattern()


def needs_extra(value: str) -> bool:
    """文本是否包含补表码点；不含时可直接走普通 NFKC + casefold。"""
    return _EXTRA_PATTERN.search(value) is not None


def search_normalize(value: str) -> str:
    """NFKC + casefold，并补齐运行时 Unicode 数据尚未覆盖的映射。

    补表后要再过一次 NFKC：新字母的兼容分解可能与紧随的组合记号重新合成
    （如 U+A7F1 + 组合锐音符 → ``ś``），只在替换后归一化才能与桌面一致。
    """
    normalized = unicodedata.normalize("NFKC", value)
    translated = normalized.translate(_NFKC_EXTRA)
    if translated != normalized:
        normalized = unicodedata.normalize("NFKC", translated)
    else:
        normalized = translated
    return normalized.casefold().translate(_CASEFOLD_EXTRA)
