#!/usr/bin/env python3
"""核对用量范围单选组的方向键循环。

「会话用量」范围单选组按 WAI-ARIA 惯例支持左右与上下方向键并循环移动。
这里固定四个方向键的映射、其他按键返回 null、越界保护与非负取模，
避免上下键失效、负下标或未知视图被当成选项。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
KEYS = "apps/desktop/src/renderer/src/data/usageViewKeys.ts"

FRAGMENTS = (
    'import type { UsageView } from "./useThreadUsage";',
    'export const USAGE_VIEWS: readonly UsageView[] = ["log", "branch"];',
    "export function usageViewStep(view: UsageView, key: string): UsageView | null {",
    'const delta = key === "ArrowRight" || key === "ArrowDown" ? 1',
    ': key === "ArrowLeft" || key === "ArrowUp" ? -1 : 0;',
    "if (!delta) return null;",
    "const index = USAGE_VIEWS.indexOf(view);",
    "if (index < 0) return null;",
    "return USAGE_VIEWS[(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length]!;",
)

ORDERED = (
    # 映射：方向键 → 位移 → 非方向键退出 → 越界保护 → 非负取模循环。
    (
        "export function usageViewStep(view: UsageView, key: string): UsageView | null {",
        "const delta =",
        "if (!delta) return null;",
        "const index = USAGE_VIEWS.indexOf(view);",
        "if (index < 0) return null;",
        "return USAGE_VIEWS[(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length]!;",
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


def check_usage_view_keys() -> int:
    source = _read(KEYS)
    checked = 0
    checked += _expect(FRAGMENTS, source, KEYS)
    for group in ORDERED:
        checked += _ordered(group, source, KEYS)
    # 反向断言：上下键必须参与映射；取模前必须补齐长度；越界不得回退首项。
    if 'key === "ArrowDown"' not in source or 'key === "ArrowUp"' not in source:
        raise ValueError(f"{KEYS} 的方向键必须同时支持左右与上下")
    if "(index + delta) % USAGE_VIEWS.length" in source:
        raise ValueError(f"{KEYS} 的循环必须在取模前补齐非负")
    if "return USAGE_VIEWS[0]!;" in source:
        raise ValueError(f"{KEYS} 的未知视图必须返回 null")
    return checked + 3


def main() -> int:
    try:
        checked = check_usage_view_keys()
    except ValueError as error:
        print(f"用量视图按键核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量视图按键一致：{checked} 项方向键、越界与循环")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
