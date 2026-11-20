#!/usr/bin/env python3
"""核对界面偏好的旧命名空间迁移。

旧键只做一次性补齐、不删除；新键已存在说明新版写过偏好，旧值不能反过来
覆盖。这里固定先收集旧键再写入、命名空间替换、跳过已存在的新键与异常回退，
避免升级后旧偏好盖掉新版选择，或回退旧版时丢失偏好。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"

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


def check_ui_storage() -> int:
    source = _read(STORAGE)
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


def main() -> int:
    try:
        checked = check_ui_storage()
    except ValueError as error:
        print(f"界面存储迁移核对失败，{error}", file=sys.stderr)
        return 2
    print(f"界面存储迁移一致：{checked} 项前缀、跳过与回退")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
