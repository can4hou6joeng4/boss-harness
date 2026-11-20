#!/usr/bin/env python3
"""核对主题偏好的三态解析、深色合成与写回。

主题偏好只有 `system` / `light` / `dark` 三态：解析先折叠空白与大小写，
无法识别的值一律回退 `system`；合成时 `dark` 为真、`light` 为假，其余
跟随系统外观；写回只保留 `light` / `dark`，其他值规范化为 `system`。
这里固定这三条语义，避免脏值被当作固定外观或原样写回。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
THEME = "apps/desktop/src/renderer/src/data/themePreference.ts"

FRAGMENTS = (
    'export type ThemePreference = "system" | "light" | "dark";',
    "export function parseThemePreference(raw: string | null | undefined): ThemePreference {",
    'if (typeof raw !== "string") return "system";',
    "const value = raw.trim().toLowerCase();",
    'return value === "light" || value === "dark" ? value : "system";',
    "export function resolveDarkTheme(preference: ThemePreference, systemPrefersDark: boolean): boolean {",
    'if (preference === "dark") return true;',
    'if (preference === "light") return false;',
    "return systemPrefersDark;",
    "export function serializeThemePreference(preference: ThemePreference): ThemePreference {",
    'return preference === "light" || preference === "dark" ? preference : "system";',
)

ORDERED = (
    # 解析：非字符串先回退，再折叠空白与大小写，最后判定固定外观。
    (
        "export function parseThemePreference(raw: string | null | undefined): ThemePreference {",
        'if (typeof raw !== "string") return "system";',
        "const value = raw.trim().toLowerCase();",
        'return value === "light" || value === "dark" ? value : "system";',
    ),
    # 合成：深色、浅色、跟随系统的顺序。
    (
        "export function resolveDarkTheme(preference: ThemePreference, systemPrefersDark: boolean): boolean {",
        'if (preference === "dark") return true;',
        'if (preference === "light") return false;',
        "return systemPrefersDark;",
    ),
    # 写回：只保留黑白两态，其余规范化为跟随系统。
    (
        "export function serializeThemePreference(preference: ThemePreference): ThemePreference {",
        'return preference === "light" || preference === "dark" ? preference : "system";',
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


def check_theme_preference() -> int:
    source = _read(THEME)
    checked = 0
    checked += _expect(FRAGMENTS, source, THEME)
    for group in ORDERED:
        checked += _ordered(group, source, THEME)
    # 反向断言：不得跳过空白折叠；写回不得原样保留；回退不得落到固定外观。
    if "raw.toLowerCase()" in source:
        raise ValueError(f"{THEME} 的解析必须先折叠空白再转小写")
    if "return preference;" in source:
        raise ValueError(f"{THEME} 的写回不得原样保留未知值")
    if '? preference : "light"' in source or '? preference : "dark"' in source:
        raise ValueError(f"{THEME} 的写回回退必须是跟随系统")
    return checked + 3


def main() -> int:
    try:
        checked = check_theme_preference()
    except ValueError as error:
        print(f"主题偏好核对失败，{error}", file=sys.stderr)
        return 2
    print(f"主题偏好一致：{checked} 项解析、合成与写回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
