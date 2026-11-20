#!/usr/bin/env python3
"""核对搜索结果的顺序、去重与命中定位意图。

搜索弹窗把内核命中排在会话标题结果之前，消息按会话与条目去重，找不到
对应会话行的命中直接丢弃；打开工具命中时要先展开工具块，否则搜索片段
与会话里可见的文本对不上。这里固定这些顺序与意图，避免键盘顺序与屏幕
不一致或定位到看不见的文字。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = "apps/desktop/src/renderer/src/data/searchOptions.ts"

FRAGMENTS = (
    'import type { SessionRow } from "./sessionRows";',
    "export type SearchOption =",
    '| { kind: "message"; key: string; hit: ThreadSearchMatch; row: SessionRow }',
    '| { kind: "session"; key: string; row: SessionRow };',
    "const options: SearchOption[] = [];",
    "const seen = new Set<string>();",
    "for (const hit of hits) {",
    "const row = rowsById.get(hit.threadId);",
    "if (!row) continue;",
    "const key = `message:${hit.threadId}:${hit.itemId}`;",
    "if (seen.has(key)) continue;",
    "seen.add(key);",
    'options.push({ kind: "message", key, hit, row });',
    "for (const row of rows) {",
    "const key = `session:${row.session.id}`;",
    'options.push({ kind: "session", key, row });',
    "return options;",
    'return role === "user" ? "你" : role === "tool" ? "工具" : "助手";',
    'return { itemId: hit.itemId, revealToolBlock: hit.role === "tool", query: query.trim() };',
)

ORDERED = (
    # 消息命中先于会话结果：逐条查行、去重、入列，再遍历会话行。
    (
        "const options: SearchOption[] = [];",
        "const seen = new Set<string>();",
        "for (const hit of hits) {",
        "const row = rowsById.get(hit.threadId);",
        "if (!row) continue;",
        "const key = `message:${hit.threadId}:${hit.itemId}`;",
        "if (seen.has(key)) continue;",
        "seen.add(key);",
        'options.push({ kind: "message", key, hit, row });',
        "for (const row of rows) {",
        "const key = `session:${row.session.id}`;",
        'options.push({ kind: "session", key, row });',
        "return options;",
    ),
    # 角色标签三分支：用户、工具、其余按助手。
    (
        'return role === "user" ? "你"',
        'role === "tool" ? "工具"',
        ': "助手";',
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


def check_search_options() -> int:
    source = _read(OPTIONS)
    checked = 0
    checked += _expect(FRAGMENTS, source, OPTIONS)
    for group in ORDERED:
        checked += _ordered(group, source, OPTIONS)
    # 反向断言：缺行必须跳过；只有工具命中展开工具块；关键词必须去掉首尾空白。
    if "if (!row) return" in source:
        raise ValueError(f"{OPTIONS} 找不到会话行的命中必须跳过，不能中断整个列表")
    if "revealToolBlock: true" in source:
        raise ValueError(f"{OPTIONS} 只有工具命中可以展开工具块")
    if "revealToolBlock: hit.role === \"tool\"" not in source:
        raise ValueError(f"{OPTIONS} 的展开意图必须由命中角色决定")
    if "query: query.trim()" not in source:
        raise ValueError(f"{OPTIONS} 的定位关键词必须去掉首尾空白")
    return checked + 4


def main() -> int:
    try:
        checked = check_search_options()
    except ValueError as error:
        print(f"搜索结果核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索结果一致：{checked} 项顺序、去重与定位意图")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
