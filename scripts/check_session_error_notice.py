#!/usr/bin/env python3
"""核对 session/error 通知的形状校验与单行摘要。

提示条把正文直接渲染为 React 子节点：对象或数组会让整屏落入错误边界，
非字符串的会话标识会污染错误缓存。这里固定会话标识上限、正文的空白
折叠与码点截断、缺省正文的通用文案，以及无法识别时整条丢弃。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NOTICE = "apps/desktop/src/renderer/src/data/sessionErrorNotice.ts"

FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    "const ID_LIMIT = 200;",
    "const MESSAGE_LIMIT = 600;",
    'export const SESSION_ERROR_FALLBACK = "任务遇到错误，请检查后重试。";',
    "export interface SessionErrorNotice {",
    "threadId: string;",
    "message: string;",
    "function compact(value: string): string {",
    'const collapsed = value.replace(/\\s+/g, " ").trim();',
    "if (collapsed.length <= MESSAGE_LIMIT) return collapsed;",
    "return `${safeSlice(collapsed, MESSAGE_LIMIT - 1).trimEnd()}…`;",
    "export function sessionErrorNoticeOf(params: unknown): SessionErrorNotice | null {",
    "if (!params || typeof params !== \"object\" || Array.isArray(params)) return null;",
    "const raw = params as Record<string, unknown>;",
    "if (typeof raw.threadId !== \"string\" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT) return null;",
    "if (raw.message !== undefined && raw.message !== null && typeof raw.message !== \"string\") return null;",
    'const message = typeof raw.message === "string" ? compact(raw.message) : "";',
    "return { threadId: raw.threadId, message: message || SESSION_ERROR_FALLBACK };",
)

ORDERED = (
    # 摘要：折叠空白、判上限、按码点截断并补省略号。
    (
        "function compact(value: string): string {",
        'const collapsed = value.replace(/\\s+/g, " ").trim();',
        "if (collapsed.length <= MESSAGE_LIMIT) return collapsed;",
        "return `${safeSlice(collapsed, MESSAGE_LIMIT - 1).trimEnd()}…`;",
    ),
    # 校验：参数形状、会话标识、正文类型，最后回退通用文案。
    (
        "export function sessionErrorNoticeOf(params: unknown): SessionErrorNotice | null {",
        "if (!params || typeof params !== \"object\" || Array.isArray(params)) return null;",
        "const raw = params as Record<string, unknown>;",
        "if (typeof raw.threadId !== \"string\" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT) return null;",
        "if (raw.message !== undefined && raw.message !== null && typeof raw.message !== \"string\") return null;",
        'const message = typeof raw.message === "string" ? compact(raw.message) : "";',
        "return { threadId: raw.threadId, message: message || SESSION_ERROR_FALLBACK };",
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


def check_session_error_notice() -> int:
    source = _read(NOTICE)
    checked = 0
    checked += _expect(FRAGMENTS, source, NOTICE)
    for group in ORDERED:
        checked += _ordered(group, source, NOTICE)
    # 反向断言：不得直接按 UTF-16 码元切正文；空白正文必须回退通用文案；
    # 多余字段不得进入结果。
    if "collapsed.slice(" in source:
        raise ValueError(f"{NOTICE} 的正文必须用 safeSlice 按码点截断")
    if 'message: message || ""' in source:
        raise ValueError(f"{NOTICE} 的空白正文必须回退通用文案")
    if "..." in source:
        raise ValueError(f"{NOTICE} 的结果不得夹带多余字段")
    if source.count("SESSION_ERROR_FALLBACK") != 2:
        raise ValueError(f"{NOTICE} 的通用文案只在定义与兜底各出现一次")
    return checked + 4


def main() -> int:
    try:
        checked = check_session_error_notice()
    except ValueError as error:
        print(f"会话错误提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话错误提示一致：{checked} 项形状校验与单行摘要")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
