#!/usr/bin/env python3
"""核对搜索状态行与空态只描述已完成的搜索范围。

状态行与空态分别实现，但必须遵守同一条规则：消息搜索失败、未启用、
查询过短或过长时不能宣称「没有找到相关聊天或消息」；零命中且截断时
两者使用同一说法。这里固定各分支文案与阈值引用，避免重新引入已修过
的误报，或把最短字符数写死在提示里。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STATUS = "apps/desktop/src/renderer/src/data/searchStatus.ts"

FRAGMENTS = (
    'if (!query.trim()) return "最近聊天";',
    'if (messageState === "ready") {',
    "? `找到 ${chatCount} 个聊天、${messageCount} 条消息（仅显示部分结果）`",
    ": `找到 ${chatCount} 个聊天；消息搜索不完整`",
    "return `找到 ${chatCount} 个聊天、${messageCount} 条消息`;",
    'if (messageState === "tooLong") return `找到 ${chatCount} 个聊天；搜索词超过 ${MESSAGE_SEARCH_MAX_LENGTH} 字符，未搜索消息`;',
    'if (messageState === "error") return `找到 ${chatCount} 个聊天；消息搜索失败`;',
    "return `找到 ${chatCount} 个聊天`;",
    'if (!query.trim()) return { title: "还没有聊天", hint: "创建聊天后，可以在这里快速找到它" };',
    "if (!searchMessages) {",
    'hint: "当前内核只按标题与项目搜索；升级内核后可搜索消息内容",',
    'if (messageState === "error") {',
    'title: "标题中没有匹配的聊天",',
    'hint: "消息搜索失败，暂时无法确认消息内容是否有命中；可稍后重试或换个关键词",',
    'if (messageState === "tooLong") {',
    "hint: `标题中没有匹配；消息搜索需要 ${MESSAGE_SEARCH_MAX_LENGTH} 个字符以内，可缩短搜索词后重试`,",
    "if (codePointLength(query.trim()) < MESSAGE_SEARCH_MIN_LENGTH) {",
    "hint: `标题中没有匹配；输入至少 ${MESSAGE_SEARCH_MIN_LENGTH} 个字符可同时搜索消息内容`,",
    'if (messageState !== "ready") {',
    'title: "正在搜索消息…",',
    'hint: "标题结果已更新；消息内容仍在检索中",',
    'return { title: "没有找到相关聊天或消息", hint: "试试其他关键词、项目名称或消息内容" };',
)

ORDERED = (
    # 状态行：空查询 → 完成（含截断）→ 过长 → 失败 → 其他。
    (
        'if (!query.trim()) return "最近聊天";',
        'if (messageState === "ready") {',
        'if (messageState === "tooLong") return',
        'if (messageState === "error") return',
        "return `找到 ${chatCount} 个聊天`;",
    ),
    # 空态：空查询 → 未启用 → 失败 → 过长 → 过短 → 未完成 → 完整。
    (
        'if (!query.trim()) return { title: "还没有聊天"',
        "if (!searchMessages) {",
        'if (messageState === "error") {',
        'if (messageState === "tooLong") {',
        "if (codePointLength(query.trim()) < MESSAGE_SEARCH_MIN_LENGTH) {",
        'if (messageState !== "ready") {',
        'return { title: "没有找到相关聊天或消息"',
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


def check_search_status() -> int:
    source = _read(STATUS)
    checked = 0
    checked += _expect(FRAGMENTS, source, STATUS)
    for group in ORDERED:
        checked += _ordered(group, source, STATUS)
    # 反向断言：完整结论只在最后分支出现一次；最短字符数不得写死。
    if re.search(r"至少 \d+ 个字符", source):
        raise ValueError(f"{STATUS} 的空态提示必须引用 MESSAGE_SEARCH_MIN_LENGTH，不得写死数字")
    if source.count('title: "没有找到相关聊天或消息"') != 1:
        raise ValueError(f"{STATUS} 的完整结论只能出现在所有未完成分支之后")
    if source.index('title: "没有找到相关聊天或消息"') < source.index('if (messageState !== "ready") {'):
        raise ValueError(f"{STATUS} 的完整结论不得先于未完成分支出现")
    if source.count("MESSAGE_SEARCH_MIN_LENGTH") < 2:
        raise ValueError(f"{STATUS} 的最短字符数必须同时用于触发条件与提示文案")
    return checked + 4


def main() -> int:
    try:
        checked = check_search_status()
    except ValueError as error:
        print(f"搜索状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索状态一致：{checked} 项状态行、空态与阈值引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
