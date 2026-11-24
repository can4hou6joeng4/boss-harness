#!/usr/bin/env python3
"""核对界面偏好的旧命名空间迁移。

旧键只做一次性补齐、不删除；新键已存在说明新版写过偏好，旧值不能反过来
覆盖。结构侧固定先收集旧键再写入、命名空间替换、跳过已存在的新键与异常
回退；行为侧把真实模块复制到临时目录，以可控 `localStorage` 桩由 Node
加载，驱动补齐、不覆盖、旧键保留、空值、多键与存储异常。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"

EXPECTED = 14

NODE_SCRIPT = """\
import {
  LEGACY_UI_STORAGE_PREFIX,
  UI_STORAGE_PREFIX,
  migrateLegacyUiStorage,
} from "./uiStorage.ts";

type Values = Record<string, string | null>;

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

let store: Values = {};
let failOn: string | null = null;
const stub = {
  get length() { return Object.keys(store).length; },
  key(index: number) { return Object.keys(store)[index] ?? null; },
  getItem(key: string) { return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null; },
  setItem(key: string, value: string) {
    if (failOn === key) throw new Error("quota");
    store[key] = value;
  },
};
Object.defineProperty(globalThis, "localStorage", { value: stub, configurable: true, writable: true });
const restore = (): void => {
  Object.defineProperty(globalThis, "localStorage", { value: stub, configurable: true, writable: true });
};
const reset = (entries: Values): void => { store = { ...entries }; failOn = null; };

expect("前缀常量固定", UI_STORAGE_PREFIX === "boss-harness.ui." && LEGACY_UI_STORAGE_PREFIX === "boss-cli.ui.");

reset({ "boss-cli.ui.theme": "dark", "boss-harness.ui.other": "1" });
migrateLegacyUiStorage();
expect("旧键补齐新键", store["boss-harness.ui.theme"] === "dark");
expect("旧键保留不删除", store["boss-cli.ui.theme"] === "dark");
expect("无关键不动", store["boss-harness.ui.other"] === "1" && Object.keys(store).length === 3);

reset({ "boss-cli.ui.theme": "old", "boss-harness.ui.theme": "new" });
migrateLegacyUiStorage();
expect("已有新键不被覆盖", store["boss-harness.ui.theme"] === "new" && store["boss-cli.ui.theme"] === "old");

reset({ "boss-ui.theme": "x", "other": "y" });
migrateLegacyUiStorage();
expect("非旧前缀不迁移", Object.keys(store).length === 2 && !("boss-harness.ui.theme" in store));

reset({ "boss-cli.ui.": "" });
migrateLegacyUiStorage();
expect("空前缀键照常补齐", store["boss-harness.ui."] === "");

reset({ "boss-cli.ui.a": "1", "boss-cli.ui.b": "2", "boss-cli.ui.c": "3" });
migrateLegacyUiStorage();
expect(
  "多键一次补齐",
  store["boss-harness.ui.a"] === "1" && store["boss-harness.ui.b"] === "2" && store["boss-harness.ui.c"] === "3",
);
expect("迁移不重复写入", Object.keys(store).length === 6);

reset({});
migrateLegacyUiStorage();
expect("无旧键不写入", Object.keys(store).length === 0);

reset({ "boss-cli.ui.theme": null });
migrateLegacyUiStorage();
expect("空值不写入新键", !("boss-harness.ui.theme" in store));

reset({ "boss-cli.ui.theme": "dark" });
failOn = "boss-harness.ui.theme";
let threw = false;
try { migrateLegacyUiStorage(); } catch { threw = true; }
expect("写入失败被吞掉", threw === false && !("boss-harness.ui.theme" in store));

reset({ "boss-cli.ui.theme": "dark" });
Object.defineProperty(globalThis, "localStorage", {
  get() { throw new Error("blocked"); },
  configurable: true,
});
threw = false;
try { migrateLegacyUiStorage(); } catch { threw = true; }
expect("存储不可用被吞掉", threw === false);
restore();

reset({ "boss-cli.ui.theme": "dark" });
migrateLegacyUiStorage();
migrateLegacyUiStorage();
expect("重复迁移保持幂等", store["boss-harness.ui.theme"] === "dark" && Object.keys(store).length === 2);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'export const UI_STORAGE_PREFIX = "boss-harness.ui.";',
    'export const LEGACY_UI_STORAGE_PREFIX = "boss-cli.ui.";',
    "export function migrateLegacyUiStorage(): void {",
    "const legacyKeys: string[] = [];",
    "for (let index = 0; index < localStorage.length; index += 1) {",
    "const key = localStorage.key(index);",
    "if (key?.startsWith(LEGACY_UI_STORAGE_PREFIX)) legacyKeys.push(key);",
    "const next = UI_STORAGE_PREFIX + key.slice(LEGACY_UI_STORAGE_PREFIX.length);",
    "if (localStorage.getItem(next) !== null) continue;",
    "const value = localStorage.getItem(key);",
    "if (value !== null) localStorage.setItem(next, value);",
)

ORDERED = (
    # 迁移：先收集旧键 → 再逐个替换命名空间 → 新键存在则跳过 → 值非空才写入。
    (
        "export function migrateLegacyUiStorage(): void {",
        "const legacyKeys: string[] = [];",
        "for (let index = 0; index < localStorage.length; index += 1) {",
        "for (const key of legacyKeys) {",
        "const next = UI_STORAGE_PREFIX + key.slice(LEGACY_UI_STORAGE_PREFIX.length);",
        "if (localStorage.getItem(next) !== null) continue;",
        "const value = localStorage.getItem(key);",
        "if (value !== null) localStorage.setItem(next, value);",
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
    checked += _expect(FRAGMENTS, source, STORAGE)
    for group in ORDERED:
        checked += _ordered(group, source, STORAGE)
    # 反向断言：旧键不得删除；不得让旧值覆盖新键；迁移必须捕获异常。
    if "localStorage.removeItem(key)" in source:
        raise ValueError(f"{STORAGE} 的旧键只做补齐，不得删除")
    if "if (localStorage.getItem(next) === null) continue;" in source:
        raise ValueError(f"{STORAGE} 必须在新键已存在时跳过，不能覆盖")
    if source.count("catch {") != 1:
        raise ValueError(f"{STORAGE} 的迁移必须整体捕获存储异常")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(STORAGE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "uiStorage.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("界面存储迁移行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"界面存储迁移行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_ui_storage.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_ui_storage.py")
    if "共 22 项结构、14 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_ui_storage.py 检查 22 项结构、12 项行为")
    return 2


def check_ui_storage() -> tuple[int, int]:
    source = _read(STORAGE)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_ui_storage()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"界面存储迁移核对失败，{error}", file=sys.stderr)
        return 2
    print(f"界面存储迁移一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
