#!/usr/bin/env python3
"""核对剪贴板写入结果与迟到回执的失效。

界面只有在真正写入成功后才显示「已复制」；失败原因只用于提示，不能
包含被复制的正文。连续点击时用版本令牌丢弃迟到回执，重置或卸载后清除
计时器，避免旧提示重新出现或卸载后继续更新状态。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CLIPBOARD = "apps/desktop/src/renderer/src/data/clipboardCopy.ts"

FRAGMENTS = (
    'import { useCallback, useEffect, useRef, useState } from "react";',
    'import { safeSlice } from "@boss-harness/shared";',
    "export type CopyResult = { ok: true } | { ok: false; reason: string };",
    "const MAX_REASON_LENGTH = 80;",
    "export async function copyText(text: string): Promise<CopyResult> {",
    "const clipboard = typeof navigator === \"undefined\" ? undefined : navigator.clipboard;",
    "if (!clipboard || typeof clipboard.writeText !== \"function\") return { ok: false, reason: \"当前环境不支持剪贴板写入\" };",
    "await clipboard.writeText(text);",
    "return { ok: true };",
    "const message = error instanceof Error ? error.message : typeof error === \"string\" ? error : \"\";",
    "return { ok: false, reason: safeSlice(message.trim(), MAX_REASON_LENGTH) || \"系统拒绝了剪贴板写入\" };",
    "export interface CopyFeedback {",
    "key: string;",
    "ok: boolean;",
    "reason?: string;",
    "export function useClipboardCopy(resetMs = 2000) {",
    "const [feedback, setFeedback] = useState<CopyFeedback | null>(null);",
    "const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);",
    "const version = useRef(0);",
    "const clear = useCallback(() => {",
    "if (timer.current !== undefined) clearTimeout(timer.current);",
    "timer.current = undefined;",
    "useEffect(() => () => { version.current += 1; clear(); }, [clear]);",
    "const mine = ++version.current;",
    "clear();",
    "setFeedback(null);",
    "const result = await copyText(text);",
    "if (version.current !== mine) return result;",
    "setFeedback(result.ok ? { key, ok: true } : { key, ok: false, reason: result.reason });",
    "timer.current = setTimeout(() => {",
    "if (version.current !== mine) return;",
    "timer.current = undefined;",
    "}, resetMs);",
    "return result;",
    "const reset = useCallback(() => { version.current += 1; clear(); setFeedback(null); }, [clear]);",
    "return { feedback, copy, reset };",
)

ORDERED = (
    # 写入：环境守卫、系统写入、成功回执。
    (
        "export async function copyText(text: string): Promise<CopyResult> {",
        "const clipboard = typeof navigator === \"undefined\" ? undefined : navigator.clipboard;",
        "if (!clipboard || typeof clipboard.writeText !== \"function\")",
        "await clipboard.writeText(text);",
        "return { ok: true };",
    ),
    # 失败：只取错误消息并截断，为空时回退固定文案。
    (
        "try {",
        "const message = error instanceof Error ? error.message : typeof error === \"string\" ? error : \"\";",
        "return { ok: false, reason: safeSlice(message.trim(), MAX_REASON_LENGTH) || \"系统拒绝了剪贴板写入\" };",
    ),
    # 清理：先取消计时器再清空引用。
    (
        "const clear = useCallback(() => {",
        "if (timer.current !== undefined) clearTimeout(timer.current);",
        "timer.current = undefined;",
    ),
    # 复制：领取新版本、清空旧提示、写入后按版本决定是否反馈。
    (
        "const mine = ++version.current;",
        "clear();",
        "setFeedback(null);",
        "const result = await copyText(text);",
        "if (version.current !== mine) return result;",
        "setFeedback(result.ok ? { key, ok: true } : { key, ok: false, reason: result.reason });",
        "timer.current = setTimeout(() => {",
        "if (version.current !== mine) return;",
        "timer.current = undefined;",
        "}, resetMs);",
        "return result;",
    ),
    # 重置：推进版本并清空提示。
    (
        "const reset = useCallback(() => { version.current += 1; clear(); setFeedback(null); }, [clear]);",
        "return { feedback, copy, reset };",
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


def check_clipboard_copy() -> int:
    source = _read(CLIPBOARD)
    checked = 0
    checked += _expect(FRAGMENTS, source, CLIPBOARD)
    for group in ORDERED:
        checked += _ordered(group, source, CLIPBOARD)
    # 反向断言：失败原因不得拼接正文；迟到回执不得恢复提示；
    # 版本令牌必须在卸载与重置时推进。
    if "safeSlice(text" in source:
        raise ValueError(f"{CLIPBOARD} 的失败原因不得包含被复制正文")
    if "version.current === mine" in source:
        raise ValueError(f"{CLIPBOARD} 的迟到回执必须丢弃")
    if source.count("version.current += 1") != 2:
        raise ValueError(f"{CLIPBOARD} 的版本令牌必须在卸载与重置时推进")
    if source.count("setFeedback(null)") != 3:
        raise ValueError(f"{CLIPBOARD} 的清空必须覆盖开始、计时器与重置")
    return checked + 4


def main() -> int:
    try:
        checked = check_clipboard_copy()
    except ValueError as error:
        print(f"剪贴板写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"剪贴板写入一致：{checked} 项写入结果与迟到回执")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
