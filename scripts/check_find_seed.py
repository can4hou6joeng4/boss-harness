#!/usr/bin/env python3
"""核对会话内查找沿用选中文本的放行条件。

打开查找时只沿用适合当关键词的选择：焦点不在可编辑控件、单行、去掉首尾
空白后非空、长度按 Unicode 码点不超过 120。这里固定判定顺序与码点计数，
避免把 emoji 等非 BMP 字符按 UTF-16 码元误判超长，或让输入框里的残留选择
覆盖用户刚输入的关键词。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SEED = "apps/desktop/src/renderer/src/data/findSeed.ts"

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    "export const FIND_SEED_MAX_LENGTH = 120;",
    "editable?: boolean;",
    "const element = target as { tagName?: unknown; isContentEditable?: unknown } | null;",
    'if (!element || typeof element.tagName !== "string") return false;',
    "const tag = element.tagName.toLowerCase();",
    'return tag === "input" || tag === "textarea" || tag === "select" || element.isContentEditable === true;',
    "export function findSeedFromSelection(",
    "context: FindSeedContext = {},",
    ": string | null {",
    "if (context.editable) return null;",
    'if (typeof selection !== "string") return null;',
    "const text = selection.trim();",
    "if (!text) return null;",
    "if (/[\\r\\n]/.test(text)) return null;",
    "if (codePointLength(text) > FIND_SEED_MAX_LENGTH) return null;",
    "return text;",
)

ORDERED = (
    # 放行顺序：可编辑控件 → 非字符串 → 去空白 → 空选择 → 多行 → 码点上限 → 沿用。
    (
        "if (context.editable) return null;",
        'if (typeof selection !== "string") return null;',
        "const text = selection.trim();",
        "if (!text) return null;",
        "if (/[\\r\\n]/.test(text)) return null;",
        "if (codePointLength(text) > FIND_SEED_MAX_LENGTH) return null;",
        "return text;",
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


def check_find_seed() -> int:
    source = _read(SEED)
    checked = 0
    checked += _expect(FRAGMENTS, source, SEED)
    for group in ORDERED:
        checked += _ordered(group, source, SEED)
    # 反向断言：长度必须按码点判定；多行校验必须在 trim 之后。
    if "selection.length" in source or "text.length" in source:
        raise ValueError(f"{SEED} 的长度必须按 Unicode 码点计数，不能按 UTF-16 码元")
    if source.index("const text = selection.trim();") > source.index("if (/[\\r\\n]/.test(text)) return null;"):
        raise ValueError(f"{SEED} 必须先去掉首尾空白再判断多行")
    return checked + 2


def main() -> int:
    try:
        checked = check_find_seed()
    except ValueError as error:
        print(f"查找沿用核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找沿用一致：{checked} 项放行条件与码点计数")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
