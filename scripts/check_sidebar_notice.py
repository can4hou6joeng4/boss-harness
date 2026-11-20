#!/usr/bin/env python3
"""核对侧栏提示的序号重播与清空语义。

连续两次复制同一内容时文案相同；若状态只存字符串，React 不会重排计时器，
`role="status"` 也不会重新播报。这里固定每次回执自增 `seq`、清空只清文案、
空态返回原对象，以及组件按 `seq` 作 key 并保留状态角色。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NOTICE = "apps/desktop/src/renderer/src/data/sidebarNotice.ts"
SIDEBAR = "apps/desktop/src/renderer/src/shell/ProjectSidebar.tsx"

FRAGMENTS = (
    "export type SidebarNotice = { text: string; seq: number };",
    'export const EMPTY_SIDEBAR_NOTICE: SidebarNotice = { text: "", seq: 0 };',
    "export const SIDEBAR_NOTICE_TIMEOUT_MS = 2600;",
    "export function nextSidebarNotice(current: SidebarNotice, text: string): SidebarNotice {",
    "return { text, seq: current.seq + 1 };",
    "export function clearSidebarNotice(current: SidebarNotice): SidebarNotice {",
    'return current.text ? { ...current, text: "" } : current;',
)

SIDEBAR_FRAGMENTS = (
    'import { clearSidebarNotice, EMPTY_SIDEBAR_NOTICE, nextSidebarNotice, SIDEBAR_NOTICE_TIMEOUT_MS, type SidebarNotice } from "../data/sidebarNotice";',
    "const timer = setTimeout(() => setNotice(clearSidebarNotice), SIDEBAR_NOTICE_TIMEOUT_MS);",
    '<div key={notice.seq} className="sidebar-feedback" role="status">{notice.text}</div>',
)

ORDERED = (
    # 回执：每次新建记录并自增序号。
    (
        "export function nextSidebarNotice(current: SidebarNotice, text: string): SidebarNotice {",
        "return { text, seq: current.seq + 1 };",
    ),
    # 清空：只清文案并保留原对象语义。
    (
        "export function clearSidebarNotice(current: SidebarNotice): SidebarNotice {",
        'return current.text ? { ...current, text: "" } : current;',
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


def check_sidebar_notice() -> int:
    source = _read(NOTICE)
    sidebar = _read(SIDEBAR)
    checked = 0
    checked += _expect(FRAGMENTS, source, NOTICE)
    checked += _expect(SIDEBAR_FRAGMENTS, sidebar, SIDEBAR)
    for group in ORDERED:
        checked += _ordered(group, source, NOTICE)
    # 反向断言：文案相同时也要自增；清空不得重置序号；组件不得改用文案作 key。
    if "current.text === text" in source:
        raise ValueError(f"{NOTICE} 相同文案也必须生成新回执并自增序号")
    if source.count('{ text: "", seq: 0 }') != 1:
        raise ValueError(f"{NOTICE} 的清空路径不得重置序号")
    if "key={notice.text}" in sidebar:
        raise ValueError(f"{SIDEBAR} 的提示节点必须按序号重建，不能按文案")
    return checked + 3


def main() -> int:
    try:
        checked = check_sidebar_notice()
    except ValueError as error:
        print(f"侧栏提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"侧栏提示一致：{checked} 项序号、清空与状态角色")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
