#!/usr/bin/env python3
"""核对会话标题的项目前缀剥离与码点截断。

首页、快速提问、侧栏与分支标签都依赖 `sessionTitleFromPrompt` 与
`compactTitle`：先剥离「招聘项目：…」前缀，再折叠空白、按 Unicode 码点
截断，空内容回退「新会话」。这里固定这些顺序与上限，避免把项目前缀带进
标题、切开代理对，或在本未超限时加上省略号。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TITLE = "apps/desktop/src/renderer/src/data/sessionTitle.ts"
HARNESS_SESSION = "harness/src/boss_harness/session.py"

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    "export const SESSION_TITLE_LIMIT = 32;",
    'export const SESSION_TITLE_FALLBACK = "新会话";',
    "const PROJECT_PREFIX = /^\\s*招聘项目：[^\\n]*\\n\\n/;",
    'return prompt.replace(PROJECT_PREFIX, "");',
    'return Array.from(text).slice(0, limit).join("");',
    'const collapsed = stripProjectPrefix(prompt).replace(/\\s+/g, " ").trim();',
    "return (codePointLength(collapsed) > limit ? sliceCodePoints(collapsed, limit) : collapsed) || SESSION_TITLE_FALLBACK;",
    'const collapsed = (text ?? "").replace(/\\s+/g, " ").trim();',
    "if (!collapsed || limit <= 0) return fallback;",
    'return codePointLength(collapsed) > limit ? `${sliceCodePoints(collapsed, limit).trimEnd()}…` : collapsed;',
)

ORDERED = (
    # 前缀剥离只替换固定格式，不匹配时原样返回。
    (
        "export function stripProjectPrefix(prompt: string): string {",
        'return prompt.replace(PROJECT_PREFIX, "");',
    ),
    # 截断按码点展开，不直接切 UTF-16 码元。
    (
        "function sliceCodePoints(text: string, limit: number): string {",
        'return Array.from(text).slice(0, limit).join("");',
    ),
    # 生成顺序：前缀 → 折叠空白 → trim → 码点判定 → 截断 → 回退。
    (
        'const collapsed = stripProjectPrefix(prompt).replace(/\\s+/g, " ").trim();',
        "return (codePointLength(collapsed) > limit ? sliceCodePoints(collapsed, limit) : collapsed) || SESSION_TITLE_FALLBACK;",
    ),
    # 紧凑标题：空值或非正上限回退，超限才截断并保留省略号。
    (
        "if (!collapsed || limit <= 0) return fallback;",
        'return codePointLength(collapsed) > limit ? `${sliceCodePoints(collapsed, limit).trimEnd()}…` : collapsed;',
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


def check_session_title() -> int:
    title = _read(TITLE)
    checked = 0
    checked += _expect(FRAGMENTS, title, TITLE)
    for group in ORDERED:
        checked += _ordered(group, title, TITLE)
    # 反向断言：不得回到直接按码元截断，不得在未超限时补省略号。
    for forbidden in ("prompt.slice(", "prompt.substring(", "collapsed.slice(", "collapsed.substring("):
        if forbidden in title:
            raise ValueError(f"{TITLE} 必须按 Unicode 码点截断，不得使用 {forbidden}")
    if re.search(r"codePointLength\(collapsed\)\s*>=\s*limit", title):
        raise ValueError(f"{TITLE} 的超限判断必须严格大于 limit，避免未超限时截断")
    # 桌面默认标题上限必须落在内核的标题上限内，避免合法标题被拒绝。
    harness = _read(HARNESS_SESSION)
    match = re.search(r"MAX_THREAD_TITLE_CHARS = (\d+)", harness)
    if not match:
        raise ValueError(f"{HARNESS_SESSION} 缺少 MAX_THREAD_TITLE_CHARS")
    limit = int(re.search(r"SESSION_TITLE_LIMIT = (\d+)", title).group(1))
    if not 1 <= limit <= int(match.group(1)):
        raise ValueError(f"{TITLE} 的 SESSION_TITLE_LIMIT 必须在 1 与内核上限 {match.group(1)} 之间")
    return checked + 3


def main() -> int:
    try:
        checked = check_session_title()
    except ValueError as error:
        print(f"会话标题核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话标题一致：{checked} 项前缀剥离、码点截断与上限关系")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
