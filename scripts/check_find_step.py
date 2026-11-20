#!/usr/bin/env python3
"""核对会话内查找的游标位点与循环跳转。

查找按「处」跳转：同一条消息内的思考块、工具块与最终答复可能命中同一个词，
游标要能逐处前进并在两端循环；每条匹配消息至少算一处，否则界面没渲染出
高亮区间的命中会变得不可达。这里固定位点数下限、游标夹取、跨消息循环与
全局序号的累加方式，避免状态行的「第 N / M 处」与实际跳转对不上。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STEP = "apps/desktop/src/renderer/src/data/findStep.ts"

FRAGMENTS = (
    "export interface FindCursor {",
    "message: number;",
    "offset: number;",
    "const EMPTY: FindCursor = { message: 0, offset: 0 };",
    "const whole = (value: number): number => (Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0);",
    "return counts.map(count => Math.max(1, whole(count)));",
    "return findSteps(counts).reduce((sum, steps) => sum + steps, 0);",
    "if (!counts.length) return EMPTY;",
    "const steps = findSteps(counts);",
    "const message = Math.min(whole(cursor.message), steps.length - 1);",
    "const offset = Math.min(whole(cursor.offset), (steps[message] ?? 1) - 1);",
    "return { message, offset };",
    "const current = clampFindCursor(cursor, counts);",
    "const next = current.offset + delta;",
    "if (next >= 0 && next < (steps[current.message] ?? 1)) return { message: current.message, offset: next };",
    "const length = steps.length;",
    "const message = (current.message + delta + length * length) % length;",
    "return { message, offset: delta > 0 ? 0 : (steps[message] ?? 1) - 1 };",
    "if (!counts.length) return 0;",
    "const safe = clampFindCursor(cursor, counts);",
    "let position = 0;",
    "for (let index = 0; index < safe.message; index += 1) position += steps[index] ?? 1;",
    "return position + safe.offset;",
)

ORDERED = (
    # 夹取：空列表回退 → 位点数 → 消息下标夹取 → 消息内位点夹取 → 返回。
    (
        "export function clampFindCursor(cursor: FindCursor, counts: readonly number[]): FindCursor {",
        "if (!counts.length) return EMPTY;",
        "const steps = findSteps(counts);",
        "const message = Math.min(whole(cursor.message), steps.length - 1);",
        "const offset = Math.min(whole(cursor.offset), (steps[message] ?? 1) - 1);",
        "return { message, offset };",
    ),
    # 步进：先收敛游标 → 段内前进 → 跨消息循环取模 → 按方向落在首尾。
    (
        "export function stepFindCursor(cursor: FindCursor, counts: readonly number[], delta: 1 | -1): FindCursor {",
        "const current = clampFindCursor(cursor, counts);",
        "const next = current.offset + delta;",
        "if (next >= 0 && next < (steps[current.message] ?? 1)) return { message: current.message, offset: next };",
        "const length = steps.length;",
        "const message = (current.message + delta + length * length) % length;",
        "return { message, offset: delta > 0 ? 0 : (steps[message] ?? 1) - 1 };",
    ),
    # 全局序号：空列表为 0 → 收敛游标 → 逐条累加前面的位数 → 加当前位点。
    (
        "export function findCursorPosition(cursor: FindCursor, counts: readonly number[]): number {",
        "if (!counts.length) return 0;",
        "const safe = clampFindCursor(cursor, counts);",
        "let position = 0;",
        "for (let index = 0; index < safe.message; index += 1) position += steps[index] ?? 1;",
        "return position + safe.offset;",
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


def check_find_step() -> int:
    source = _read(STEP)
    checked = 0
    checked += _expect(FRAGMENTS, source, STEP)
    for group in ORDERED:
        checked += _ordered(group, source, STEP)
    # 反向断言：数值取整必须向下取整；反向循环不得出现负模；序号必须逐条累加。
    if "Math.round(" in source:
        raise ValueError(f"{STEP} 的位点与游标必须向下取整")
    if "(current.message + delta) % length" in source:
        raise ValueError(f"{STEP} 的反向循环必须在取模前补齐非负")
    if "return safe.message + safe.offset;" in source:
        raise ValueError(f"{STEP} 的全局序号必须累加前面每条消息的位数")
    return checked + 3


def main() -> int:
    try:
        checked = check_find_step()
    except ValueError as error:
        print(f"查找游标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找游标一致：{checked} 项位点、夹取与循环跳转")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
