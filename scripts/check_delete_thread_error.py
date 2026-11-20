#!/usr/bin/env python3
"""核对删除会话失败的原因码映射与未确认措辞。

`incomplete` 表示会话已从列表消失（内核已隐藏、稍后继续清理），`failed`
表示内核明确拒绝删除，`unknown` 表示结果未确认。这里固定原因码只在
`rpcError === true` 且 `data.code` 为字符串时读取，三种已知原因各有归属，
其他原因不得臆断为已删除或删除失败。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DELETE = "apps/desktop/src/renderer/src/data/deleteThreadError.ts"

FRAGMENTS = (
    'import { harnessErrorText } from "./harnessBridge";',
    'export type DeleteThreadFailure = { status: "incomplete" | "failed" | "unknown"; message: string };',
    "export function deleteThreadFailure(error: unknown): DeleteThreadFailure {",
    "const value = error && typeof error === \"object\"",
    "? error as { rpcError?: unknown; data?: unknown } : null;",
    "const data = value?.data && typeof value.data === \"object\" ? value.data as Record<string, unknown> : null;",
    'const code = value?.rpcError === true && typeof data?.code === "string" ? data.code : "";',
    "switch (code) {",
    'case "THREAD_BUSY":',
    'return { status: "failed", message: "该聊天仍有运行中的回合或排队消息，无法删除。请先停止当前回合并清空队列，再重试。" };',
    'case "THREAD_DELETE_INCOMPLETE":',
    'return { status: "incomplete", message: "聊天已从列表移除，但本机数据尚未清理完；内核重启后会继续清理。" };',
    'case "THREAD_NOT_FOUND":',
    'return { status: "incomplete", message: "该聊天已不存在，已从列表移除。" };',
    "default:",
    'return { status: "unknown", message: `删除结果尚未确认：${harnessErrorText(error)}。请刷新会话列表核对；若该聊天已消失，无需重试。` };',
)

ORDERED = (
    # 原因码读取：对象、数据、rpcError 与字符串 code 依次收紧。
    (
        "const value = error && typeof error === \"object\"",
        "? error as { rpcError?: unknown; data?: unknown } : null;",
        "const data = value?.data && typeof value.data === \"object\" ? value.data as Record<string, unknown> : null;",
        'const code = value?.rpcError === true && typeof data?.code === "string" ? data.code : "";',
    ),
    # 三种已知原因在前，未知原因兜底。
    (
        "switch (code) {",
        'case "THREAD_BUSY":',
        'case "THREAD_DELETE_INCOMPLETE":',
        'case "THREAD_NOT_FOUND":',
        "default:",
        'return { status: "unknown"',
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


def check_delete_thread_error() -> int:
    source = _read(DELETE)
    checked = 0
    checked += _expect(FRAGMENTS, source, DELETE)
    for group in ORDERED:
        checked += _ordered(group, source, DELETE)
    # 反向断言：原因码只允许三种；不得臆断删除结果；未知原因必须带原始错误文本。
    if source.count('case "') != 3:
        raise ValueError(f"{DELETE} 的原因码只允许三种")
    if 'status: "deleted"' in source:
        raise ValueError(f"{DELETE} 不得把删除结果说成已删除")
    if source.count("harnessErrorText(") != 1:
        raise ValueError(f"{DELETE} 的未知原因必须带原始错误文本")
    return checked + 3


def main() -> int:
    try:
        checked = check_delete_thread_error()
    except ValueError as error:
        print(f"删除失败展示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除失败展示一致：{checked} 项原因码与未确认措辞")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
