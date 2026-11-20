#!/usr/bin/env python3
"""核对会话内查找状态行的计数单位与分支。

状态行按「处命中」计数，与游标的跳转单位一致；只有正文零命中时才提示
「含详情可命中 N 条消息」，高亮超过上限时才补「仅前 N 处高亮」。这里固定
分支顺序、位次的 1 起始显示与夹取、高亮上限的缺省来源，避免状态行误报
截断或把可停靠数当成真实命中数。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STATUS = "apps/desktop/src/renderer/src/data/findStatus.ts"

FRAGMENTS = (
    'import { FIND_HIGHLIGHT_LIMIT } from "./findHighlight";',
    "query: string;",
    "total: number;",
    "position: number;",
    "detailHits?: number;",
    "capped?: boolean;",
    "highlightLimit?: number;",
    'if (!input.query.trim()) return "输入关键词";',
    "const whole = (value: number): number => Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;",
    "const total = whole(input.total);",
    "if (total > 0) {",
    "const position = Math.min(whole(input.position), total - 1);",
    "const limit = whole(input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT);",
    "return input.capped === true",
    "? `第 ${position + 1} / ${total} 处命中 · 仅前 ${limit} 处高亮`",
    ": `第 ${position + 1} / ${total} 处命中`;",
    "const detailHits = whole(input.detailHits ?? 0);",
    "if (detailHits > 0) return `正文无匹配 · 含详情可命中 ${detailHits} 条消息`;",
    'return "无匹配消息";',
)

ORDERED = (
    # 状态行：空查询 → 总数 → 有命中分支（位次夹取、上限、截断说明）→ 详情提示 → 无匹配。
    (
        'if (!input.query.trim()) return "输入关键词";',
        "const total = whole(input.total);",
        "if (total > 0) {",
        "const position = Math.min(whole(input.position), total - 1);",
        "const limit = whole(input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT);",
        "return input.capped === true",
        ": `第 ${position + 1} / ${total} 处命中`;",
        "const detailHits = whole(input.detailHits ?? 0);",
        "if (detailHits > 0) return `正文无匹配 · 含详情可命中 ${detailHits} 条消息`;",
        'return "无匹配消息";',
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


def check_find_status() -> int:
    source = _read(STATUS)
    checked = 0
    checked += _expect(FRAGMENTS, source, STATUS)
    for group in ORDERED:
        checked += _ordered(group, source, STATUS)
    # 反向断言：数值向下取整；详情提示只在零命中分支出现一次；上限不得写死。
    if "Math.round(" in source:
        raise ValueError(f"{STATUS} 的位次与上限必须向下取整")
    if source.count("正文无匹配") != 1:
        raise ValueError(f"{STATUS} 的详情提示只能在正文零命中时出现一次")
    if source.index("正文无匹配") < source.index("return input.capped === true"):
        raise ValueError(f"{STATUS} 的详情提示不得先于有命中分支出现")
    if "?? 200" in source:
        raise ValueError(f"{STATUS} 的高亮上限必须引用 FIND_HIGHLIGHT_LIMIT")
    return checked + 4


def main() -> int:
    try:
        checked = check_find_status()
    except ValueError as error:
        print(f"查找状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找状态一致：{checked} 项计数单位、分支与上限引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
