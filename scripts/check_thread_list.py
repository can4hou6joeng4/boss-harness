#!/usr/bin/env python3
"""核对会话列表回执的逐项校验与去重。

侧栏把条目直接映射为会话：标识用于去重与操作目标，标题与时间用于展示，
`lastTurn` 会作为恢复目标。这里固定必填与可选字段的边界、角色与状态
白名单、失败码与恢复策略，以及重复 id 的拒绝，避免部分可疑列表被展示。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
THREADS = "apps/desktop/src/renderer/src/data/threadList.ts"

FRAGMENTS = (
    'import type { ThreadSummary } from "@boss-harness/protocol";',
    "const ID_LIMIT = 200;",
    "const TITLE_LIMIT = 500;",
    "const TIME_LIMIT = 64;",
    "const CODE_LIMIT = 120;",
    'const TURN_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "interrupted", "blocked", "error"]);',
    "function text(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    "function optionalText(value: unknown, limit: number): string | null | undefined {",
    "if (value === undefined || value === null) return null;",
    'return typeof value === "string" && value.length <= limit ? value : undefined;',
    "export function threadSummaryOf(value: unknown): ThreadSummary | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const raw = value as Record<string, unknown>;",
    "if (!text(raw.id, ID_LIMIT)) return null;",
    'if (typeof raw.title !== "string" || raw.title.length > TITLE_LIMIT) return null;',
    'if (typeof raw.updatedAt !== "string" || raw.updatedAt.length > TIME_LIMIT) return null;',
    'if (raw.archived !== undefined && typeof raw.archived !== "boolean") return null;',
    'if (raw.toolPolicy !== undefined && raw.toolPolicy !== "readOnly" && raw.toolPolicy !== "approval") return null;',
    "const provider = optionalText(raw.provider, ID_LIMIT);",
    "if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;",
    "if (!text(turn.turnId, ID_LIMIT)) return null;",
    'if (typeof turn.status !== "string" || !TURN_STATUSES.has(turn.status)) return null;',
    "if (optionalText(turn.failureCode, CODE_LIMIT) === undefined) return null;",
    "if (optionalText(turn.taskResumePolicy, CODE_LIMIT) === undefined) return null;",
    "return raw as unknown as ThreadSummary;",
    "export function uniqueThreadIds(items: { id: string }[]): boolean {",
    "return new Set(items.map(item => item.id)).size === items.length;",
)

ORDERED = (
    # 条目：对象判定 → 标识 → 标题与时间 → 归档与策略 → 可选文本 → 最近回合 → 放行。
    (
        "export function threadSummaryOf(value: unknown): ThreadSummary | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!text(raw.id, ID_LIMIT)) return null;",
        "raw.title.length > TITLE_LIMIT",
        "raw.updatedAt.length > TIME_LIMIT",
        "raw.archived !== undefined",
        "raw.toolPolicy !== undefined",
        "const provider = optionalText(raw.provider, ID_LIMIT);",
        "if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;",
        "if (!text(turn.turnId, ID_LIMIT)) return null;",
        "!TURN_STATUSES.has(turn.status)",
        "return raw as unknown as ThreadSummary;",
    ),
    # 去重：集合大小必须等于条目数。
    (
        "export function uniqueThreadIds(items: { id: string }[]): boolean {",
        "return new Set(items.map(item => item.id)).size === items.length;",
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


def check_thread_list() -> int:
    source = _read(THREADS)
    checked = 0
    checked += _expect(FRAGMENTS, source, THREADS)
    for group in ORDERED:
        checked += _ordered(group, source, THREADS)
    # 反向断言：可选字段的非法与缺省必须分开；重复 id 不得放行；必须校验三项可选文本。
    if "return typeof value === \"string\" ? value : null;" in source:
        raise ValueError(f"{THREADS} 的非法可选字段不能当作缺省")
    if "new Set(items.map(item => item.id)).size >= items.length" in source:
        raise ValueError(f"{THREADS} 的重复 id 必须拒绝")
    if "provider === undefined || model === undefined)" in source:
        raise ValueError(f"{THREADS} 必须同时校验 provider、model 与 reasoningEffort")
    return checked + 3


def main() -> int:
    try:
        checked = check_thread_list()
    except ValueError as error:
        print(f"会话列表核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话列表一致：{checked} 项校验、可选字段与去重")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
