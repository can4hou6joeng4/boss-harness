#!/usr/bin/env python3
"""核对主题偏好的三态解析、深色合成与写回。

主题偏好只有 `system` / `light` / `dark` 三态：解析先折叠空白与大小写，
无法识别的值一律回退 `system`；合成时 `dark` 为真、`light` 为假，其余
跟随系统外观；写回只保留 `light` / `dark`，其他值规范化为 `system`。
结构侧固定这三条语义；行为侧把真实 `themePreference.ts` 复制到临时目录，
由 Node 直接加载驱动解析、合成与写回，避免脏值被当作固定外观或原样写回。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
THEME = "apps/desktop/src/renderer/src/data/themePreference.ts"

EXPECTED = 20

NODE_SCRIPT = """\
import {
  parseThemePreference,
  resolveDarkTheme,
  serializeThemePreference,
} from "./themePreference.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

expect("跟随系统", parseThemePreference("system") === "system");
expect("浅色", parseThemePreference("light") === "light");
expect("深色", parseThemePreference("dark") === "dark");
expect(
  "空白与大小写折叠",
  parseThemePreference(" LIGHT ") === "light" && parseThemePreference("Dark") === "dark",
);
expect(
  "未知值回退系统",
  parseThemePreference("auto") === "system" && parseThemePreference("sepia") === "system",
);
expect(
  "空白回退系统",
  parseThemePreference("") === "system" && parseThemePreference("   ") === "system",
);
expect(
  "非字符串回退系统",
  parseThemePreference(null) === "system"
    && parseThemePreference(undefined) === "system"
    && parseThemePreference(123 as any) === "system"
    && parseThemePreference({} as any) === "system",
);
expect("内部空白不折叠", parseThemePreference("li ght") === "system");

expect("深色固定为真", resolveDarkTheme("dark", false) === true);
expect("浅色固定为假", resolveDarkTheme("light", true) === false);
expect("跟随系统深色", resolveDarkTheme("system", true) === true);
expect("跟随系统浅色", resolveDarkTheme("system", false) === false);

expect("浅色写回", serializeThemePreference("light") === "light");
expect("深色写回", serializeThemePreference("dark") === "dark");
expect("系统写回", serializeThemePreference("system") === "system");
expect("未知写回回退系统", serializeThemePreference("sepia" as any) === "system");
expect("空白写回回退系统", serializeThemePreference(" light " as any) === "system");
expect(
  "非字符串写回回退系统",
  serializeThemePreference(null as any) === "system"
    && serializeThemePreference(undefined as any) === "system",
);
expect("写回不修剪大小写", serializeThemePreference("Light" as any) === "system");
expect(
  "解析写回往返",
  ["system", "light", "dark"].every(
    value => serializeThemePreference(parseThemePreference(value) as any) === value,
  ),
);

console.log(`PASS ${passed}`);
"""

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


def _check_structure(source: str) -> int:
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


def _check_behaviors() -> int:
    source = _read(THEME)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "themePreference.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("主题偏好行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"主题偏好行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_theme_preference.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_theme_preference.py")
    if "共 24 项结构、20 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_theme_preference.py 检查 24 项结构、20 项行为")
    return 2


def check_theme_preference() -> tuple[int, int]:
    source = _read(THEME)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_theme_preference()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"主题偏好核对失败，{error}", file=sys.stderr)
        return 2
    print(f"主题偏好一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
