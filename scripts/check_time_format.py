#!/usr/bin/env python3
"""核对界面时间格式与会话排序键的严格解析。

界面时间固定为简体中文并按本机时区补零，不能跟随系统区域；会话排序键只接受
完整 ISO 时间，缺失或可疑值按 0 落到列表末尾。这里固定补零、非法时间的空串
回退、ISO 包装与排序键的零回退，避免区域差异或 NaN 打乱界面与顺序。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TIME = "apps/desktop/src/renderer/src/data/timeFormat.ts"
ORDER = "apps/desktop/src/renderer/src/data/sessionOrder.ts"

FRAGMENTS = (
    'import { formatLocalDate, parseIsoDateTime } from "@boss-harness/shared";',
    "export { parseIsoDateTime };",
    'const pad = (part: number) => String(part).padStart(2, "0");',
    "export function formatLocalDateTime(at: Date): string {",
    'if (Number.isNaN(at.getTime())) return "";',
    "return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;",
    "export function formatLocalClock(at: Date): string {",
    "return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;",
    "export function formatIsoDateTime(value: unknown): string {",
    "export function formatIsoClock(value: unknown): string {",
    "return at ? formatLocalDateTime(at) : \"\";",
    "return at ? formatLocalClock(at) : \"\";",
)

ORDER_FRAGMENTS = (
    'import { parseIsoDateTime } from "./timeFormat";',
    "export function sessionUpdatedAt(session: SessionItem): number {",
    "return parseIsoDateTime(session.updatedAt)?.getTime() ?? 0;",
)

ORDERED = (
    # 日期时间：先判非法，再补零输出。
    (
        "export function formatLocalDateTime(at: Date): string {",
        'if (Number.isNaN(at.getTime())) return "";',
        "return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;",
    ),
    # 时刻：先判非法，再补零输出。
    (
        "export function formatLocalClock(at: Date): string {",
        'if (Number.isNaN(at.getTime())) return "";',
        "return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;",
    ),
    # ISO 包装：严格解析 → 格式化或空串。
    (
        "export function formatIsoDateTime(value: unknown): string {",
        "const at = parseIsoDateTime(value);",
        "return at ? formatLocalDateTime(at) : \"\";",
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


def check_time_format() -> int:
    source = _read(TIME)
    order = _read(ORDER)
    checked = 0
    checked += _expect(FRAGMENTS, source, TIME)
    checked += _expect(ORDER_FRAGMENTS, order, ORDER)
    for group in ORDERED:
        checked += _ordered(group, source, TIME)
    # 反向断言：不得跟随系统区域；排序键不得用宽松解析；两个格式化函数都要判 NaN。
    if ".toLocaleString(" in source or ".toLocaleDateString(" in source:
        raise ValueError(f"{TIME} 的时间不得跟随系统区域")
    if "Date.parse(" in order:
        raise ValueError(f"{ORDER} 的排序键必须使用严格 ISO 解析")
    if source.count("Number.isNaN(at.getTime())") != 2:
        raise ValueError(f"{TIME} 的两个格式化函数都必须先判非法时间")
    return checked + 3


def main() -> int:
    try:
        checked = check_time_format()
    except ValueError as error:
        print(f"时间格式核对失败，{error}", file=sys.stderr)
        return 2
    print(f"时间格式一致：{checked} 项补零、解析与排序键")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
