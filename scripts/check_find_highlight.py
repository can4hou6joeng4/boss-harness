#!/usr/bin/env python3
"""核对会话内查找的高亮区间与折叠块语义。

查找把归一化文本的命中偏移映射回原文，合并同一次字素展开产生的重叠区间，
并按上限收束；关闭的 `<details>` 内文字不参与统计与高亮。这里固定这些规则，
避免高亮标错位置、计数大于可见命中，或长会话挂载过多区间。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HIGHLIGHT = "apps/desktop/src/renderer/src/data/findHighlight.ts"

FRAGMENTS = (
    "export const FIND_HIGHLIGHT_LIMIT = 200;",
    "const { normalized, starts, ends } = mapped;",
    "const index = normalized.indexOf(needle, from);",
    "const start = starts[index];",
    "const end = ends[index + needle.length - 1];",
    "if (start === undefined || end === undefined) break;",
    "if (previous && start < previous.end) previous.end = Math.max(previous.end, end);",
    "else ranges.push({ start, end });",
    "from = index + needle.length;",
    "if (start < cursor) continue;",
    'if (start > cursor) segments.push({ text: text.slice(cursor, start), match: false });',
    'segments.push({ text: text.slice(start, end), match: true });',
    'if (cursor < text.length) segments.push({ text: text.slice(cursor), match: false });',
    "if (element instanceof HTMLDetailsElement && !element.open) {",
    'const summary = element.querySelector(":scope > summary");',
    "if (!summary || !summary.contains(node)) return true;",
    "if (!text.data || (!includeFolded && foldedAway(text, root))) continue;",
    "if (end < combined.length) {",
    "range.setEnd(last, last.data.length);",
    "const needle = searchText(query).trim();",
    "const needle = kernelSearchText(query.trim());",
    "return scanRanges(searchTextWithMap(text), needle, limit);",
    "return scanRanges(kernelSearchTextWithMap(text), needle, limit);",
)

ORDERED = (
    # 扫描：归一化文本找命中 → 映射回原文 → 重叠合并 → 从命中末尾继续。
    (
        "const { normalized, starts, ends } = mapped;",
        "const index = normalized.indexOf(needle, from);",
        "const start = starts[index];",
        "const end = ends[index + needle.length - 1];",
        "if (start === undefined || end === undefined) break;",
        "if (previous && start < previous.end) previous.end = Math.max(previous.end, end);",
        "from = index + needle.length;",
    ),
    # 拆分：按区间顺序输出未命中 / 命中片段，末尾补剩余原文。
    (
        "if (start < cursor) continue;",
        "if (start > cursor) segments.push({ text: text.slice(cursor, start), match: false });",
        "segments.push({ text: text.slice(start, end), match: true });",
        "if (cursor < text.length) segments.push({ text: text.slice(cursor), match: false });",
    ),
    # 折叠块：从节点向上找最近一层未展开的 details，summary 例外。
    (
        "if (element instanceof HTMLDetailsElement && !element.open) {",
        'const summary = element.querySelector(":scope > summary");',
        "if (!summary || !summary.contains(node)) return true;",
    ),
    # 收集：跳过折叠内容（可配置）→ 合并文本 → 映射区间 → 末尾收束。
    (
        "if (!text.data || (!includeFolded && foldedAway(text, root))) continue;",
        "const combined = parts.join(\"\");",
        "if (end < combined.length) {",
        "range.setEnd(last, last.data.length);",
    ),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_find_highlight() -> int:
    source = _read(HIGHLIGHT)
    checked = 0
    checked += _expect(FRAGMENTS, source, HIGHLIGHT)
    for group in ORDERED:
        checked += _ordered(group, source, HIGHLIGHT)
    # 反向断言：不得直接对原文扫描，不得省略重叠合并或折叠块排除。
    if re.search(r"text\.indexOf\(needle", source):
        raise ValueError(f"{HIGHLIGHT} 必须先归一化再扫描，不得直接对原文使用 indexOf")
    if "previous.end = end;" in source:
        raise ValueError(f"{HIGHLIGHT} 的重叠区间必须取最大结束位置")
    if "foldedAway(text, root)" not in source:
        raise ValueError(f"{HIGHLIGHT} 必须保留关闭折叠块的排除")
    if "FIND_HIGHLIGHT_LIMIT = 200" not in source:
        raise ValueError(f"{HIGHLIGHT} 的高亮区间上限必须保持 200")
    return checked + 4


def main() -> int:
    try:
        checked = check_find_highlight()
    except ValueError as error:
        print(f"查找高亮核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找高亮一致：{checked} 项区间映射、合并与折叠块语义")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
