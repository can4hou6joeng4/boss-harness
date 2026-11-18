#!/usr/bin/env python3
"""核对搜索片段与桌面高亮的边界一致性，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
HIGHLIGHT = "apps/desktop/src/renderer/src/data/findHighlight.ts"
DIALOG = "apps/desktop/src/renderer/src/components/SearchDialog.tsx"
SNIPPET_FRAGMENTS = (
    "_SEARCH_SNIPPET_BYTES = 200",
    "def _search_snippet(text: str, start: int, end: int) -> str:",
    "left, right = max(0, start - 40), min(len(text), end + 40)",
    'before = re.sub(r"\\s+", " ", text[left:start]).lstrip()',
    "hit = text[start:end]",
    'after = re.sub(r"\\s+", " ", text[end:right]).rstrip()',
    "room = _SEARCH_SNIPPET_BYTES - len(hit)",
    "if len(before) + len(after) > room:",
    "keep_left = min(len(before), max(0, room) // 2)",
    "keep_right = min(len(after), max(0, room) - keep_left)",
    "keep_left = min(len(before), max(0, room) - keep_right)",
    "trimmed_before, trimmed_after = keep_left < len(before), keep_right < len(after)",
    'before = before[len(before) - keep_left:] if keep_left else ""',
    "after = after[:keep_right]",
    'return (("…" if left or trimmed_before else "") + f"{before}{hit}{after}".strip()',
    '+ ("…" if right < len(text) or trimmed_after else ""))',
)
HIGHLIGHT_FRAGMENTS = (
    "export function findKernelTextRanges(text: string, query: string, limit = FIND_HIGHLIGHT_LIMIT): TextRange[] {",
    "const needle = kernelSearchText(query.trim());",
    "return scanRanges(kernelSearchTextWithMap(text), needle, limit);",
    "export function splitKernelHighlight(text: string, query: string, limit = 50): TextSegment[] {",
    "return splitByRanges(text, findKernelTextRanges(text, query, limit));",
    "findKernelTextRanges(text, query, count)",
)
DIALOG_FRAGMENTS = (
    "<Highlighted text={hit.snippet} query={query} kernel />",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"session.py 缺少 {name}")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_search_snippet() -> tuple[int, int]:
    session = _read(SESSION)
    tree = ast.parse(session)
    snippet = _function(tree, session, "_search_snippet")
    checked = 0
    for fragment in SNIPPET_FRAGMENTS[1:]:
        if fragment not in snippet:
            raise ValueError(f"_search_snippet 缺少：{fragment}")
        checked += 1
    budget = SNIPPET_FRAGMENTS[0]
    if budget not in session or budget.split(" = ")[1] != "200":
        raise ValueError("_SEARCH_SNIPPET_BYTES 必须为 200")
    checked += 1
    # Hit text must be copied verbatim: no whitespace collapsing on the match itself.
    collapse_hit = snippet.count('re.sub(r"\\s+", " ",')
    if collapse_hit != 2:
        raise ValueError("空白折叠只能作用于命中两侧上下文")
    checked += 1
    checked += _expect(HIGHLIGHT_FRAGMENTS, _read(HIGHLIGHT), "findHighlight.ts")
    checked += _expect(DIALOG_FRAGMENTS, _read(DIALOG), "SearchDialog.tsx")
    return 3, checked


def main() -> int:
    try:
        modules, guards = check_search_snippet()
    except (ValueError, SyntaxError) as error:
        print(f"搜索片段边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索片段边界一致：{modules} 个模块、{guards} 项命中保留与高亮防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
