#!/usr/bin/env python3
"""核对旧显示名称迁移的筛选、去重与上限。

旧版本只把「更改显示名称」写进本机偏好；启动后的迁移只能处理当前会话
列表中仍存在的会话，已删除会话的别名不写回内核。空白、非字符串或与内核
标题一致的别名只删除；名称按码点计数，超过 500 或单次已达 50 条时留给
下次启动。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ALIAS = "apps/desktop/src/renderer/src/data/aliasMigration.ts"

FRAGMENTS = (
    'import type { SessionItem } from "./mockData";',
    "export interface AliasMigration {",
    "session: SessionItem;",
    "name: string;",
    "export interface AliasMigrationPlan {",
    "rename: AliasMigration[];",
    "drop: string[];",
    "export const MAX_ALIAS_LENGTH = 500;",
    "export const MAX_ALIAS_MIGRATIONS = 50;",
    "export function planAliasMigrations(",
    "aliases: Record<string, string>,",
    "sessions: readonly SessionItem[],",
    "): AliasMigrationPlan {",
    "const plan: AliasMigrationPlan = { rename: [], drop: [] };",
    "const seen = new Set<string>();",
    "for (const session of sessions) {",
    "if (seen.has(session.id)) continue;",
    "seen.add(session.id);",
    "if (!Object.prototype.hasOwnProperty.call(aliases, session.id)) continue;",
    "const alias: unknown = aliases[session.id];",
    'if (typeof alias !== "string") { plan.drop.push(session.id); continue; }',
    "const name = alias.trim();",
    'const title = typeof session.title === "string" ? session.title.trim() : "";',
    "if (!name || name === title) { plan.drop.push(session.id); continue; }",
    "if (Array.from(name).length > MAX_ALIAS_LENGTH || plan.rename.length >= MAX_ALIAS_MIGRATIONS) continue;",
    "plan.rename.push({ session, name });",
    "return plan;",
)

ORDERED = (
    # 计划结构：迁移与删除两条出口。
    (
        "export interface AliasMigrationPlan {",
        "rename: AliasMigration[];",
        "drop: string[];",
    ),
    # 只遍历会话列表并去重，缺失别名直接跳过。
    (
        "const plan: AliasMigrationPlan = { rename: [], drop: [] };",
        "const seen = new Set<string>();",
        "for (const session of sessions) {",
        "if (seen.has(session.id)) continue;",
        "seen.add(session.id);",
        "if (!Object.prototype.hasOwnProperty.call(aliases, session.id)) continue;",
        "const alias: unknown = aliases[session.id];",
    ),
    # 非字符串、空白与同名先删除，再判码点上限与单次条数。
    (
        'if (typeof alias !== "string") { plan.drop.push(session.id); continue; }',
        "const name = alias.trim();",
        'const title = typeof session.title === "string" ? session.title.trim() : "";',
        "if (!name || name === title) { plan.drop.push(session.id); continue; }",
        "if (Array.from(name).length > MAX_ALIAS_LENGTH || plan.rename.length >= MAX_ALIAS_MIGRATIONS) continue;",
        "plan.rename.push({ session, name });",
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


def check_alias_migration() -> int:
    source = _read(ALIAS)
    checked = 0
    checked += _expect(FRAGMENTS, source, ALIAS)
    for group in ORDERED:
        checked += _ordered(group, source, ALIAS)
    # 反向断言：只能遍历会话列表；必须去重；长度必须按码点计数；
    # 空白或同名别名不得发起写入。
    if "Object.keys(aliases)" in source:
        raise ValueError(f"{ALIAS} 只能遍历当前会话列表，不能遍历别名键")
    if source.count("seen.add(session.id)") != 1:
        raise ValueError(f"{ALIAS} 的会话必须去重")
    if "name.length > MAX_ALIAS_LENGTH" in source:
        raise ValueError(f"{ALIAS} 的名称长度必须按码点计数")
    if "if (!name) { plan.drop" in source:
        raise ValueError(f"{ALIAS} 与内核标题一致的别名不得发起写入")
    return checked + 4


def main() -> int:
    try:
        checked = check_alias_migration()
    except ValueError as error:
        print(f"别名迁移核对失败，{error}", file=sys.stderr)
        return 2
    print(f"别名迁移一致：{checked} 项筛选、去重与上限")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
