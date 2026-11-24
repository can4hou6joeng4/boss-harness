#!/usr/bin/env python3
"""核对界面偏好导出文件的白名单、逐键校验与旧作用域兼容。

导出文件只包含允许迁移的界面偏好，导入时任一如名键非法就整体拒绝；旧
`boss-cli.ui` 作用域按旧前缀读取，未知键忽略，别名与项目名永远不写入
导出。结构侧固定上下限、枚举、分支顺序与白名单；行为侧把真实模块复制到
临时目录、改写相对导入，由 Node 加载 `parsePreferencesFile` 与
`buildPreferencesFile` 驱动解析与导出往返。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
PREFERENCES = "apps/desktop/src/renderer/src/data/preferencesFile.ts"
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"

EXPECTED = 33

NODE_SCRIPT = """\
import {
  PREFERENCE_FILE_MAX_BYTES,
  buildPreferencesFile,
  parsePreferencesFile,
} from "./preferencesFile.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const P = "boss-harness.ui.";
const L = "boss-cli.ui.";
const wrap = (preferences: unknown, scope = "boss-harness.ui", version = 1): string =>
  JSON.stringify({ version, scope, preferences });
const ok = (result: any): boolean => result.ok === true;
const bad = (result: any, text: string): boolean => result.ok === false && result.reason === text;
const parse = (text: unknown): any => parsePreferencesFile(text as string);

expect("空文本被拒绝", bad(parse(""), "文件为空"));
expect("空白文本被拒绝", bad(parse("  \\n "), "文件为空"));
expect("非字符串被拒绝", bad(parse(undefined), "文件为空"));
expect("超限被拒绝", bad(parse("x".repeat(PREFERENCE_FILE_MAX_BYTES + 1)), "文件超过 64 KiB"));
expect("非法 JSON 被拒绝", bad(parse("{"), "不是有效的 JSON 文件"));
expect("数组结构被拒绝", bad(parse("[]"), "文件结构无效"));
expect("版本不匹配被拒绝", bad(parse(wrap({}, "boss-harness.ui", 2)), "不支持的版本，请使用当前版本导出的文件"));
expect("未知作用域被拒绝", bad(parse(wrap({}, "other.ui")), "不是本应用的界面偏好文件"));
expect("缺少偏好内容被拒绝", bad(parse(JSON.stringify({ version: 1, scope: "boss-harness.ui" })), "缺少界面偏好内容"));
expect("偏好内容非对象被拒绝", bad(parse(wrap([])), "缺少界面偏好内容"));

let result = parse(wrap({ [`${P}fontSize`]: "14" }));
expect("字体大小读取", ok(result) && result.values.fontSize === 14 && result.fields === 1);
expect("字体大小越界被拒绝", bad(parse(wrap({ [`${P}fontSize`]: "17" })), "字体大小无效"));
expect("字体大小必须为字符串", bad(parse(wrap({ [`${P}fontSize`]: 14 })), "字体大小无效"));
result = parse(wrap({ [`${P}density`]: "compact" }));
expect("密度读取", ok(result) && result.values.density === "compact");
expect("密度非法被拒绝", bad(parse(wrap({ [`${P}density`]: "wide" })), "会话密度无效"));
result = parse(wrap({ [`${P}motion`]: "reduced" }));
expect("动效读取", ok(result) && result.values.motion === "reduced");
expect("动效非法被拒绝", bad(parse(wrap({ [`${P}motion`]: "fast" })), "动态效果设置无效"));
result = parse(wrap({ [`${P}approvalSound`]: "true" }));
expect("提示音开读取", ok(result) && result.values.approvalSound === true);
result = parse(wrap({ [`${P}approvalSound`]: "false" }));
expect("提示音关读取", ok(result) && result.values.approvalSound === false);
expect("提示音非法被拒绝", bad(parse(wrap({ [`${P}approvalSound`]: "yes" })), "审批提示音设置无效"));
result = parse(wrap({ [`${P}theme`]: "dark" }));
expect("主题读取", ok(result) && result.values.theme === "dark");
expect("主题非法被拒绝", bad(parse(wrap({ [`${P}theme`]: "blue" })), "主题设置无效"));
result = parse(wrap({
  [`${P}theme`]: "light",
  [`${P}fontSize`]: "13",
  [`${P}density`]: "comfortable",
  [`${P}motion`]: "full",
  [`${P}approvalSound`]: "false",
}));
expect(
  "全部键读取",
  ok(result) && result.fields === 5 && result.values.fontSize === 13 && result.values.density === "comfortable"
    && result.values.motion === "full" && result.values.approvalSound === false && result.values.theme === "light",
);
expect("未知键被忽略", bad(parse(wrap({ [`${P}unknown`]: "x" })), "文件不包含可导入的界面偏好"));
result = parse(wrap({ [`${L}theme`]: "dark" }, "boss-cli.ui"));
expect("旧作用域按旧前缀读取", ok(result) && result.values.theme === "dark");
expect("旧作用域忽略新前缀", bad(parse(wrap({ [`${P}theme`]: "dark" }, "boss-cli.ui")), "文件不包含可导入的界面偏好"));
expect("新作用域忽略旧前缀", bad(parse(wrap({ [`${L}theme`]: "dark" })), "文件不包含可导入的界面偏好"));
expect("任一非法键整体拒绝", bad(parse(wrap({ [`${P}theme`]: "dark", [`${P}fontSize`]: "99" })), "字体大小无效"));

const built = buildPreferencesFile({ fontSize: 14, density: "compact", motion: "reduced", approvalSound: true }, "dark");
const payload = JSON.parse(built);
expect("导出带版本与作用域", payload.version === 1 && payload.scope === "boss-harness.ui");
const keys = Object.keys(payload.preferences).sort();
expect("导出只含白名单键", keys.length === 5 && keys.every(key => key.startsWith(P)));
expect(
  "导出值正确",
  payload.preferences[`${P}fontSize`] === "14"
    && payload.preferences[`${P}approvalSound`] === "true"
    && payload.preferences[`${P}theme`] === "dark",
);
expect("导出为缩进排版", built.includes("\\n  "));
const round = parse(built);
expect(
  "导出可回读",
  ok(round) && round.fields === 5 && round.values.fontSize === 14
    && round.values.approvalSound === true && round.values.theme === "dark",
);

console.log(`PASS ${passed}`);
"""

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


def _rewrite(source: str) -> str:
    rewritten = source.replace('from "./uiStorage"', 'from "./uiStorage.ts"')
    rewritten = rewritten.replace(
        'import type { ThemePreference } from "./themePreference";',
        'type ThemePreference = "system" | "light" | "dark";',
    )
    if 'from "./uiStorage.ts"' not in rewritten or "type ThemePreference" not in rewritten:
        raise ValueError(f"{PREFERENCES} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
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


def _check_behaviors() -> int:
    source = _read(PREFERENCES)
    storage = _read(STORAGE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "preferencesFile.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "uiStorage.ts").write_text(storage, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("界面偏好文件行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"界面偏好文件行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_preferences_file.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_preferences_file.py")
    if "共 82 项结构、33 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_preferences_file.py 检查 82 项结构、33 项行为")
    return 2


def check_preferences_file() -> tuple[int, int]:
    source = _read(PREFERENCES)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_preferences_file()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"界面偏好文件核对失败，{error}", file=sys.stderr)
        return 2
    print(f"界面偏好文件一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
