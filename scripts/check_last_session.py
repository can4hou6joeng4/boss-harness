#!/usr/bin/env python3
"""核对最近打开会话的存储解析与回退。

启动时据本地存储的会话 id 回到上次会话；损坏记录、超长 id 与存储不可用
都必须退回首页，不能把异常拖到启动阶段。这里固定严格解析、命名空间键、
异常回退与清空语义，避免带首尾空白的记录或空 id 被当成可恢复会话。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LAST = "apps/desktop/src/renderer/src/data/lastSession.ts"
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"

FRAGMENTS = (
    'import { UI_STORAGE_PREFIX } from "./uiStorage";',
    'export const LAST_SESSION_KEY = UI_STORAGE_PREFIX + "lastSession";',
    "const MAX_SESSION_ID_LENGTH = 200;",
    "export function parseLastSessionId(raw: string | null): string | null {",
    'if (typeof raw !== "string") return null;',
    "const id = raw.trim();",
    "if (!id || id.length > MAX_SESSION_ID_LENGTH || id !== raw) return null;",
    "return id;",
    "export function readLastSessionId(): string | null {",
    "return parseLastSessionId(localStorage.getItem(LAST_SESSION_KEY));",
    "export function rememberLastSessionId(id: string | null): void {",
    "if (id) localStorage.setItem(LAST_SESSION_KEY, id);",
    "else localStorage.removeItem(LAST_SESSION_KEY);",
)

STORAGE_FRAGMENTS = (
    'export const UI_STORAGE_PREFIX = "boss-harness.ui.";',
)

ORDERED = (
    # 解析：类型 → 去空白 → 严格判定 → 返回。
    (
        "export function parseLastSessionId(raw: string | null): string | null {",
        'if (typeof raw !== "string") return null;',
        "const id = raw.trim();",
        "if (!id || id.length > MAX_SESSION_ID_LENGTH || id !== raw) return null;",
        "return id;",
    ),
    # 记录：有 id 写入，没有则删除键。
    (
        "export function rememberLastSessionId(id: string | null): void {",
        "if (id) localStorage.setItem(LAST_SESSION_KEY, id);",
        "else localStorage.removeItem(LAST_SESSION_KEY);",
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


def check_last_session() -> int:
    source = _read(LAST)
    storage = _read(STORAGE)
    checked = 0
    checked += _expect(FRAGMENTS, source, LAST)
    checked += _expect(STORAGE_FRAGMENTS, storage, STORAGE)
    for group in ORDERED:
        checked += _ordered(group, source, LAST)
    # 反向断言：损坏记录不得恢复；读写都要有异常回退；清空不得写入空字符串。
    if "id !== raw" not in source:
        raise ValueError(f"{LAST} 带首尾空白的记录必须视为损坏")
    if source.count("catch {") != 2:
        raise ValueError(f"{LAST} 读写本地存储都必须捕获异常并退回首页")
    if 'setItem(LAST_SESSION_KEY, "")' in source:
        raise ValueError(f"{LAST} 清空必须删除键，不能写入空字符串")
    return checked + 3


def main() -> int:
    try:
        checked = check_last_session()
    except ValueError as error:
        print(f"最近会话核对失败，{error}", file=sys.stderr)
        return 2
    print(f"最近会话一致：{checked} 项解析、回退与清空")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
