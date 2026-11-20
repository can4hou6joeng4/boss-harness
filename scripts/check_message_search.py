#!/usr/bin/env python3
"""核对消息搜索的批次失效与内核响应校验。

搜索弹窗的消息命中来自内核：批次记录发起时的查询与归档范围，输入或范围
变化后旧批次立即失效；响应形状不可信，非数组按空结果处理，逐项校验标识、
角色与片段，并按当前可见会话过滤。这里固定这些防护，避免旧结果继续可点开
或畸形条目进入渲染。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MESSAGE_SEARCH = "apps/desktop/src/renderer/src/data/messageSearch.ts"

FRAGMENTS = (
    'const SEARCH_ROLES: ReadonlySet<string> = new Set(["user", "agent", "tool"]);',
    'if (!value || typeof value !== "object") return false;',
    'return typeof match.threadId === "string" && match.threadId.length > 0',
    '&& typeof match.threadTitle === "string"',
    '&& typeof match.itemId === "string" && match.itemId.length > 0',
    '&& typeof match.role === "string" && SEARCH_ROLES.has(match.role)',
    '&& typeof match.snippet === "string";',
    "if (!batch || !needle || batch.query !== needle || batch.includeArchived !== includeArchived) {",
    "if (!Array.isArray(batch.matches)) return { matches: [], truncated: false };",
    "matches: batch.matches.filter(isThreadSearchMatch).filter(match => availableThreadIds.has(match.threadId)),",
    "truncated: batch.truncated === true,",
    "if (!enabled || codePointLength(needle) < MESSAGE_SEARCH_MIN_LENGTH) return state;",
    "if (codePointLength(needle) > MESSAGE_SEARCH_MAX_LENGTH) return state;",
    "if (settled && settled.query === needle && settled.includeArchived === includeArchived) return state;",
    'return "loading";',
)

ORDERED = (
    # 命中校验顺序：对象 → 会话与条目标识 → 标题与角色 → 片段。
    (
        'if (!value || typeof value !== "object") return false;',
        'return typeof match.threadId === "string" && match.threadId.length > 0',
        '&& typeof match.threadTitle === "string"',
        '&& typeof match.itemId === "string" && match.itemId.length > 0',
        '&& typeof match.role === "string" && SEARCH_ROLES.has(match.role)',
        '&& typeof match.snippet === "string";',
    ),
    # 可见命中：批次失效 → 非数组 → 逐项校验与可见会话过滤 → 截断标记。
    (
        "if (!batch || !needle || batch.query !== needle || batch.includeArchived !== includeArchived) {",
        "return { matches: [], truncated: false };",
        "if (!Array.isArray(batch.matches)) return { matches: [], truncated: false };",
        "matches: batch.matches.filter(isThreadSearchMatch).filter(match => availableThreadIds.has(match.threadId)),",
        "truncated: batch.truncated === true,",
    ),
    # 状态：未启用或过短保持组件状态 → 过长保持 → 批次对应当前输入保持 → 其余视为检索中。
    (
        "if (!enabled || codePointLength(needle) < MESSAGE_SEARCH_MIN_LENGTH) return state;",
        "if (codePointLength(needle) > MESSAGE_SEARCH_MAX_LENGTH) return state;",
        "if (settled && settled.query === needle && settled.includeArchived === includeArchived) return state;",
        'return "loading";',
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


def check_message_search() -> int:
    source = _read(MESSAGE_SEARCH)
    checked = 0
    checked += _expect(FRAGMENTS, source, MESSAGE_SEARCH)
    for group in ORDERED:
        checked += _ordered(group, source, MESSAGE_SEARCH)
    # 反向断言：命中必须逐项校验并过滤可见会话；截断只认布尔真；角色白名单必须覆盖工具命中。
    if "batch.matches.map(" in source:
        raise ValueError(f"{MESSAGE_SEARCH} 的批次命中必须过滤，不能直接映射")
    if re.search(r"truncated:\s*batch\.truncated\s*,", source):
        raise ValueError(f"{MESSAGE_SEARCH} 的截断标记必须以 === true 判定")
    if re.search(r"matches:\s*batch\.matches\s*,", source):
        raise ValueError(f"{MESSAGE_SEARCH} 不得把未校验的批次命中直接交给渲染")
    if '"tool"' not in source:
        raise ValueError(f"{MESSAGE_SEARCH} 的角色白名单必须包含 tool")
    return checked + 4


def main() -> int:
    try:
        checked = check_message_search()
    except ValueError as error:
        print(f"消息搜索核对失败，{error}", file=sys.stderr)
        return 2
    print(f"消息搜索一致：{checked} 项批次失效、响应校验与状态")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
