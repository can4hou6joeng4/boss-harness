#!/usr/bin/env python3
"""核对界面偏好导出文件的白名单、逐键校验与旧作用域兼容。

导出文件只包含允许迁移的界面偏好，导入时任一如名键非法就整体拒绝；旧
`boss-cli.ui` 作用域按旧前缀读取，未知键忽略，别名与项目名永远不写入
导出。这里固定上下限、枚举、分支顺序与白名单，避免隐私文本外泄或同一份
文件在新旧版本给出不同结果。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFERENCES = "apps/desktop/src/renderer/src/data/preferencesFile.ts"

FRAGMENTS = (
    'import { LEGACY_UI_STORAGE_PREFIX, UI_STORAGE_PREFIX } from "./uiStorage";',
    'import type { ThemePreference } from "./themePreference";',
    'export type Density = "compact" | "comfortable";',
    'export type Motion = "reduced" | "full";',
    "export const PREFERENCE_FONT_SIZES = [12, 13, 14, 15, 16] as const;",
    "export const PREFERENCE_FILE_MAX_BYTES = 64 * 1024;",
    "const PREFERENCE_FILE_VERSION = 1;",
    'const PREFERENCE_FILE_SCOPE = "boss-harness.ui";',
    'const LEGACY_PREFERENCE_FILE_SCOPE = "boss-cli.ui";',
    "function isRecord(value: unknown): value is Record<string, unknown> {",
    'return typeof value === "object" && value !== null && !Array.isArray(value);',
    'if (typeof text !== "string" || !text.trim()) return { ok: false, reason: "文件为空" };',
    'if (new TextEncoder().encode(text).byteLength > PREFERENCE_FILE_MAX_BYTES) return { ok: false, reason: "文件超过 64 KiB" };',
    "parsed = JSON.parse(text);",
    'return { ok: false, reason: "不是有效的 JSON 文件" };',
    'if (!isRecord(parsed)) return { ok: false, reason: "文件结构无效" };',
    'if (parsed.version !== PREFERENCE_FILE_VERSION) return { ok: false, reason: "不支持的版本，请使用当前版本导出的文件" };',
    "if (parsed.scope !== PREFERENCE_FILE_SCOPE && parsed.scope !== LEGACY_PREFERENCE_FILE_SCOPE) {",
    'return { ok: false, reason: "不是本应用的界面偏好文件" };',
    'if (!isRecord(parsed.preferences)) return { ok: false, reason: "缺少界面偏好内容" };',
    "const preferences = parsed.preferences;",
    "const prefix = parsed.scope === LEGACY_PREFERENCE_FILE_SCOPE ? LEGACY_UI_STORAGE_PREFIX : UI_STORAGE_PREFIX;",
    "const readKey = (name: string): string => `${prefix}${name}`;",
    "const values: PreferencesFileValues = {};",
    "let fields = 0;",
    'const fontSizeRaw = preferences[readKey("fontSize")];',
    'const size = typeof fontSizeRaw === "string" ? Number(fontSizeRaw) : Number.NaN;',
    'if (!PREFERENCE_FONT_SIZES.some((candidate) => candidate === size)) return { ok: false, reason: "字体大小无效" };',
    'const densityRaw = preferences[readKey("density")];',
    'if (densityRaw !== "compact" && densityRaw !== "comfortable") return { ok: false, reason: "会话密度无效" };',
    'const motionRaw = preferences[readKey("motion")];',
    'if (motionRaw !== "reduced" && motionRaw !== "full") return { ok: false, reason: "动态效果设置无效" };',
    'const approvalSoundRaw = preferences[readKey("approvalSound")];',
    'if (approvalSoundRaw !== "true" && approvalSoundRaw !== "false") return { ok: false, reason: "审批提示音设置无效" };',
    'values.approvalSound = approvalSoundRaw === "true";',
    'const themeRaw = preferences[readKey("theme")];',
    'if (themeRaw !== "system" && themeRaw !== "light" && themeRaw !== "dark") return { ok: false, reason: "主题设置无效" };',
    'if (fields === 0) return { ok: false, reason: "文件不包含可导入的界面偏好" };',
    "return { ok: true, values, fields };",
    "// 工作区别名与项目名可能包含隐私文本，即使同处界面前缀也不能导出；这里只允许白名单键。",
    '[knownKey("fontSize")]: String(preferences.fontSize),',
    '[knownKey("density")]: preferences.density,',
    '[knownKey("motion")]: preferences.motion,',
    '[knownKey("approvalSound")]: String(preferences.approvalSound),',
    '[knownKey("theme")]: theme,',
    "return JSON.stringify({ version: PREFERENCE_FILE_VERSION, scope: PREFERENCE_FILE_SCOPE, preferences: exported }, null, 2);",
)

ORDERED = (
    # 空文本与字节上限先于 JSON 解析。
    (
        'if (typeof text !== "string" || !text.trim()) return { ok: false, reason: "文件为空" };',
        'if (new TextEncoder().encode(text).byteLength > PREFERENCE_FILE_MAX_BYTES) return { ok: false, reason: "文件超过 64 KiB" };',
        "parsed = JSON.parse(text);",
    ),
    # 结构、版本、作用域与偏好内容依次校验。
    (
        'if (!isRecord(parsed)) return { ok: false, reason: "文件结构无效" };',
        'if (parsed.version !== PREFERENCE_FILE_VERSION)',
        "if (parsed.scope !== PREFERENCE_FILE_SCOPE && parsed.scope !== LEGACY_PREFERENCE_FILE_SCOPE) {",
        'if (!isRecord(parsed.preferences)) return { ok: false, reason: "缺少界面偏好内容" };',
        "const preferences = parsed.preferences;",
    ),
    # 作用域决定读取前缀，再生成读取函数。
    (
        "const prefix = parsed.scope === LEGACY_PREFERENCE_FILE_SCOPE ? LEGACY_UI_STORAGE_PREFIX : UI_STORAGE_PREFIX;",
        "const readKey = (name: string): string => `${prefix}${name}`;",
    ),
    # 字体大小先解析再对照白名单，最后写入结果。
    (
        'const fontSizeRaw = preferences[readKey("fontSize")];',
        'const size = typeof fontSizeRaw === "string" ? Number(fontSizeRaw) : Number.NaN;',
        "if (!PREFERENCE_FONT_SIZES.some((candidate) => candidate === size))",
        "values.fontSize = size;",
    ),
    # 四个枚举键依次读取、校验、计数。
    (
        'const densityRaw = preferences[readKey("density")];',
        'if (densityRaw !== "compact" && densityRaw !== "comfortable")',
        'const motionRaw = preferences[readKey("motion")];',
        'if (motionRaw !== "reduced" && motionRaw !== "full")',
        'const approvalSoundRaw = preferences[readKey("approvalSound")];',
        'if (approvalSoundRaw !== "true" && approvalSoundRaw !== "false")',
        'values.approvalSound = approvalSoundRaw === "true";',
        'const themeRaw = preferences[readKey("theme")];',
        'if (themeRaw !== "system" && themeRaw !== "light" && themeRaw !== "dark")',
    ),
    # 没有任何已知键时拒绝，否则返回计数字段。
    (
        'if (fields === 0) return { ok: false, reason: "文件不包含可导入的界面偏好" };',
        "return { ok: true, values, fields };",
    ),
    # 导出按白名单顺序写入，最后序列化为带版本与作用域的文件。
    (
        '[knownKey("fontSize")]: String(preferences.fontSize),',
        '[knownKey("density")]: preferences.density,',
        '[knownKey("motion")]: preferences.motion,',
        '[knownKey("approvalSound")]: String(preferences.approvalSound),',
        '[knownKey("theme")]: theme,',
        "return JSON.stringify({ version: PREFERENCE_FILE_VERSION, scope: PREFERENCE_FILE_SCOPE, preferences: exported }, null, 2);",
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


def check_preferences_file() -> int:
    source = _read(PREFERENCES)
    checked = 0
    checked += _expect(FRAGMENTS, source, PREFERENCES)
    for group in ORDERED:
        checked += _ordered(group, source, PREFERENCES)
    # 反向断言：导出不得包含别名与项目名；旧作用域不得按新前缀读取；
    # 非法已知键不得跳过；导出键只能逐个白名单写入，不能展开偏好对象。
    if "alias" in source or "projectName" in source:
        raise ValueError(f"{PREFERENCES} 的导出不得包含别名或项目名")
    if "LEGACY_PREFERENCE_FILE_SCOPE ? UI_STORAGE_PREFIX" in source:
        raise ValueError(f"{PREFERENCES} 的旧作用域必须按旧前缀读取")
    if "continue" in source:
        raise ValueError(f"{PREFERENCES} 的非法已知键必须整体拒绝，不能跳过")
    if "..." in source:
        raise ValueError(f"{PREFERENCES} 的导出只能逐个白名单键写入，不能展开偏好对象")
    if source.count("knownKey(") != 6:
        raise ValueError(f"{PREFERENCES} 的导出键数量必须保持 5 个白名单键")
    return checked + 5


def main() -> int:
    try:
        checked = check_preferences_file()
    except ValueError as error:
        print(f"界面偏好文件核对失败，{error}", file=sys.stderr)
        return 2
    print(f"界面偏好文件一致：{checked} 项白名单、逐键校验与旧作用域")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
