#!/usr/bin/env python3
"""核对通知分组标题的拼接与截断。

通知标题优先「项目 · 会话」，缺失会话时用线程 id 前 8 位回退，归档会话补
「 · 已归档」。这里固定空白折叠、去重、后缀保留与按码点截断，避免标题重复、
截断后丢掉归档标记，或把非 BMP 字符切成半个码点。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LABELS = "apps/desktop/src/renderer/src/data/notificationLabels.ts"

FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    'import type { SessionItem } from "./mockData";',
    "export const NOTIFICATION_LABEL_LIMIT = 120;",
    'const ARCHIVED_SUFFIX = " · 已归档";',
    "const FALLBACK_ID_LIMIT = 8;",
    "function compact(value: unknown): string {",
    'return typeof value === "string" ? value.replace(/\\s+/g, " ").trim() : "";',
    "export function notificationGroupLabel(source: NotificationGroupSource): string {",
    "const threadId = compact(source.threadId);",
    'const fallback = `会话 ${threadId.slice(0, FALLBACK_ID_LIMIT) || "未知"}`;',
    "const title = compact(source.session?.title) || fallback;",
    "const project = compact(source.project);",
    "const base = project && project !== title ? `${project} · ${title}` : title;",
    'const suffix = source.session?.archived === true ? ARCHIVED_SUFFIX : "";',
    "if (base.length + suffix.length <= NOTIFICATION_LABEL_LIMIT) return `${base}${suffix}`;",
    "const room = Math.max(1, NOTIFICATION_LABEL_LIMIT - suffix.length - 1);",
    "return `${safeSlice(base, room)}…${suffix}`;",
)

ORDERED = (
    # 拼接：折叠空白 → 回退 → 标题 → 项目去重 → 后缀 → 放行 → 截断。
    (
        "export function notificationGroupLabel(source: NotificationGroupSource): string {",
        "const threadId = compact(source.threadId);",
        "const fallback =",
        "const title = compact(source.session?.title) || fallback;",
        "const project = compact(source.project);",
        "const base = project && project !== title",
        'const suffix = source.session?.archived === true ? ARCHIVED_SUFFIX : "";',
        "if (base.length + suffix.length <= NOTIFICATION_LABEL_LIMIT) return `${base}${suffix}`;",
        "const room = Math.max(1, NOTIFICATION_LABEL_LIMIT - suffix.length - 1);",
        "return `${safeSlice(base, room)}…${suffix}`;",
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


def check_notification_labels() -> int:
    source = _read(LABELS)
    checked = 0
    checked += _expect(FRAGMENTS, source, LABELS)
    for group in ORDERED:
        checked += _ordered(group, source, LABELS)
    # 反向断言：截断必须按码点；长度判断必须计入后缀；放行路径也带后缀。
    if "base.slice(" in source:
        raise ValueError(f"{LABELS} 的截断必须按 Unicode 码点，不能按 UTF-16 码元")
    if "if (base.length <= NOTIFICATION_LABEL_LIMIT)" in source:
        raise ValueError(f"{LABELS} 的长度判断必须计入归档后缀")
    return checked + 2


def main() -> int:
    try:
        checked = check_notification_labels()
    except ValueError as error:
        print(f"通知标题核对失败，{error}", file=sys.stderr)
        return 2
    print(f"通知标题一致：{checked} 项拼接、去重与截断")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
