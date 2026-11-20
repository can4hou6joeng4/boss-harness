#!/usr/bin/env python3
"""核对会话索引健康度的读数与状态文案。

内核会跳过无法解析的会话日志，只在这里暴露；缺失或形状不可信必须显示
「未报告」，不能渲染成告警或正常。这里固定数值校验、零计数与列出 id 的
矛盾判定、id 去重与截断，以及设置页文案的三态，避免把损坏响应当成健康。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HEALTH = "apps/desktop/src/renderer/src/data/sessionIndexHealth.ts"

FRAGMENTS = (
    "export interface SessionIndexHealth {",
    "count: number;",
    "ids: string[];",
    "export const SESSION_INDEX_MAX_IDS = 20;",
    "const MAX_THREAD_ID_LENGTH = 64;",
    "function isRecord(value: unknown): value is Record<string, unknown> {",
    'return typeof value === "object" && value !== null && !Array.isArray(value);',
    "export function readSessionIndexHealth(config: unknown): SessionIndexHealth | null {",
    "if (!isRecord(config)) return null;",
    "const count = config.unreadableThreadCount;",
    'if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) return null;',
    "const ids: string[] = [];",
    "const raw = config.unreadableThreadIds;",
    "if (count === 0) {",
    "const listed = Array.isArray(raw) && raw.some(value =>",
    'typeof value === "string" && value.length > 0 && value.length <= MAX_THREAD_ID_LENGTH);',
    "return listed ? null : { count, ids };",
    "if (Array.isArray(raw)) {",
    "if (ids.length >= SESSION_INDEX_MAX_IDS) break;",
    'if (typeof value !== "string" || value.length === 0 || value.length > MAX_THREAD_ID_LENGTH) continue;',
    "if (!ids.includes(value)) ids.push(value);",
    "return { count, ids };",
    "export function sessionIndexHealthLabel(health: SessionIndexHealth | null): string {",
    'if (!health) return "未报告";',
    'return health.count > 0 ? `${health.count} 个无法读取` : "正常";',
)

ORDERED = (
    # 读数：对象判定 → 计数校验 → 零计数的矛盾判定 → 有计数时逐条去重截断。
    (
        "export function readSessionIndexHealth(config: unknown): SessionIndexHealth | null {",
        "if (!isRecord(config)) return null;",
        "const count = config.unreadableThreadCount;",
        'if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) return null;',
        "const raw = config.unreadableThreadIds;",
        "if (count === 0) {",
        "return listed ? null : { count, ids };",
        "if (Array.isArray(raw)) {",
        "if (ids.length >= SESSION_INDEX_MAX_IDS) break;",
        "if (!ids.includes(value)) ids.push(value);",
        "return { count, ids };",
    ),
    # 文案：未报告 → 有计数 → 正常。
    (
        "export function sessionIndexHealthLabel(health: SessionIndexHealth | null): string {",
        'if (!health) return "未报告";',
        'return health.count > 0 ? `${health.count} 个无法读取` : "正常";',
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


def check_session_index_health() -> int:
    source = _read(HEALTH)
    checked = 0
    checked += _expect(FRAGMENTS, source, HEALTH)
    for group in ORDERED:
        checked += _ordered(group, source, HEALTH)
    # 反向断言：未报告不能写成正常；去重必须先查再入列；计数不得用浮点校验。
    if 'if (!health) return "正常";' in source:
        raise ValueError(f"{HEALTH} 的未报告状态不能写成正常")
    if "ids.push(value);\n      if (!ids.includes(value))" in source:
        raise ValueError(f"{HEALTH} 的 id 必须先查重再入列")
    if "Number.isInteger(count)" in source:
        raise ValueError(f"{HEALTH} 的计数必须用安全整数校验")
    return checked + 3


def main() -> int:
    try:
        checked = check_session_index_health()
    except ValueError as error:
        print(f"会话索引健康核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话索引健康一致：{checked} 项读数、去重与文案")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
