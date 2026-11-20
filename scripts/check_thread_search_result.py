#!/usr/bin/env python3
"""核对搜索回执的形状校验与上限。

`thread/search` 的命中条目直接进入搜索弹窗：标识拼进选项 key，片段交给
关键词高亮，角色决定显示成你、助手还是工具。这里固定对象与数组判定、
标识与文本上限、角色白名单、回执级上限与「任一命中非法即整体拒绝」，
避免把内核异常传成渲染期抛错或把损坏响应当成完整结果。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESULT = "apps/desktop/src/renderer/src/data/threadSearchResult.ts"

FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const TITLE_LIMIT = 4096;",
    "const SNIPPET_LIMIT = 4096;",
    "export const SEARCH_MATCH_LIMIT = 200;",
    'const ROLES: ReadonlySet<string> = new Set(["user", "agent", "tool"]);',
    "function boundedText(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const raw = value as Record<string, unknown>;",
    "if (!boundedText(raw.threadId, ID_LIMIT)) return null;",
    'if (typeof raw.threadTitle !== "string" || raw.threadTitle.length > TITLE_LIMIT) return null;',
    "if (!boundedText(raw.itemId, ID_LIMIT)) return null;",
    'if (typeof raw.role !== "string" || !ROLES.has(raw.role)) return null;',
    'if (typeof raw.snippet !== "string" || raw.snippet.length > SNIPPET_LIMIT) return null;',
    'role: raw.role as ThreadSearchMatch["role"],',
    "if (!Array.isArray(raw.matches) || raw.matches.length > SEARCH_MATCH_LIMIT) return null;",
    'if (raw.truncated !== undefined && typeof raw.truncated !== "boolean") return null;',
    "const matches: ThreadSearchMatch[] = [];",
    "const match = threadSearchMatchOf(item);",
    "if (!match) return null;",
    "matches.push(match);",
    "return { matches, truncated: raw.truncated === true };",
)

ORDERED = (
    # 单条命中：对象判定 → 标识 → 标题 → 角色 → 片段 → 返回带类型的对象。
    (
        "export function threadSearchMatchOf(value: unknown): ThreadSearchMatch | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!boundedText(raw.threadId, ID_LIMIT)) return null;",
        'if (typeof raw.threadTitle !== "string" || raw.threadTitle.length > TITLE_LIMIT) return null;',
        "if (!boundedText(raw.itemId, ID_LIMIT)) return null;",
        'if (typeof raw.role !== "string" || !ROLES.has(raw.role)) return null;',
        'if (typeof raw.snippet !== "string" || raw.snippet.length > SNIPPET_LIMIT) return null;',
        'role: raw.role as ThreadSearchMatch["role"],',
    ),
    # 整体回执：对象判定 → 上限 → 截断标记类型 → 逐条校验 → 拒绝整包。
    (
        "export function threadSearchResultOf(value: unknown): ThreadSearchResult | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!Array.isArray(raw.matches) || raw.matches.length > SEARCH_MATCH_LIMIT) return null;",
        'if (raw.truncated !== undefined && typeof raw.truncated !== "boolean") return null;',
        "for (const item of raw.matches) {",
        "if (!match) return null;",
        "matches.push(match);",
        "return { matches, truncated: raw.truncated === true };",
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


def check_thread_search_result() -> int:
    source = _read(RESULT)
    checked = 0
    checked += _expect(FRAGMENTS, source, RESULT)
    for group in ORDERED:
        checked += _ordered(group, source, RESULT)
    # 反向断言：角色必须先过白名单再断言类型；截断标记只取 true；单条非法必须整体拒绝。
    if source.index("ROLES.has(raw.role)") > source.index('raw.role as ThreadSearchMatch["role"]'):
        raise ValueError(f"{RESULT} 的角色必须先过白名单再断言类型")
    if "truncated: raw.truncated }" in source:
        raise ValueError(f"{RESULT} 的截断标记只能取显式 true")
    if "if (!match) continue;" in source:
        raise ValueError(f"{RESULT} 的单条命中非法时必须拒绝整包回执")
    return checked + 3


def main() -> int:
    try:
        checked = check_thread_search_result()
    except ValueError as error:
        print(f"搜索回执核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索回执一致：{checked} 项形状校验与上限")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
