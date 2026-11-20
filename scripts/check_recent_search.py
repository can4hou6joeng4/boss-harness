#!/usr/bin/env python3
"""核对最近搜索的阈值来源、去重与本地存储回退。

搜索弹窗的最近搜索存在渲染层本地存储：存储可能损坏、被禁用或写入失败，
阈值与消息搜索共用同一组常量。这里固定解析、去重、限长与回退行为，
避免把损坏数据带进渲染，或让两个阈值各自漂移。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RECENT = "apps/desktop/src/renderer/src/data/recentSearches.ts"

FRAGMENTS = (
    'import { MESSAGE_SEARCH_MAX_LENGTH, MESSAGE_SEARCH_MIN_LENGTH } from "./searchStatus";',
    'export const RECENT_SEARCH_KEY = UI_STORAGE_PREFIX + "recentSearches";',
    "export const RECENT_SEARCH_MIN_LENGTH = MESSAGE_SEARCH_MIN_LENGTH;",
    "export const RECENT_SEARCH_LIMIT = 5;",
    'const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("zh-CN");',
    'if (typeof value !== "string") continue;',
    "const query = value.trim();",
    "if (codePointLength(query) < RECENT_SEARCH_MIN_LENGTH || codePointLength(query) > MESSAGE_SEARCH_MAX_LENGTH) continue;",
    "const key = normalize(query);",
    "if (seen.has(key)) continue;",
    "result.push(query);",
    "if (result.length >= limit) break;",
    "if (!raw) return [];",
    "parsed = JSON.parse(raw);",
    "return Array.isArray(parsed) ? sanitize(parsed, limit) : [];",
    "if (!query.trim()) return sanitize(list, limit);",
    "return sanitize([query, ...list], limit);",
    "const next = mergeRecentSearch(readRecentSearches(), query);",
    "localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(next));",
    "return next;",
    "localStorage.removeItem(RECENT_SEARCH_KEY);",
)

ORDERED = (
    # 读取：存储不可用时回退 null，不抛出。
    (
        "function readRaw(): string | null {",
        "    return localStorage.getItem(RECENT_SEARCH_KEY);",
        "  } catch {",
        "    // 隐私模式或存储被禁用：搜索照常可用，只是不保留历史。",
        "    return null;",
    ),
    # 解析：损坏 JSON 与非数组都回退为空。
    (
        "export function parseRecentSearches(raw: string | null, limit = RECENT_SEARCH_LIMIT): string[] {",
        "if (!raw) return [];",
        "  try {",
        "    parsed = JSON.parse(raw);",
        "  } catch {",
        "    return [];",
        "  return Array.isArray(parsed) ? sanitize(parsed, limit) : [];",
    ),
    # 写入：先合并再写，写入失败仍返回当前列表。
    (
        "export function rememberRecentSearch(query: string): string[] {",
        "const next = mergeRecentSearch(readRecentSearches(), query);",
        "  try {\n    localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(next));",
        "  } catch {",
        "  return next;",
    ),
    # 清除：存储不可用时没有需要清理的数据。
    (
        "export function clearRecentSearches(): void {",
        "  try {\n    localStorage.removeItem(RECENT_SEARCH_KEY);",
        "  } catch {",
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


def check_recent_search() -> int:
    recent = _read(RECENT)
    checked = 0
    checked += _expect(FRAGMENTS, recent, RECENT)
    for group in ORDERED:
        checked += _ordered(group, recent, RECENT)
    # 反向断言：阈值只能引用消息搜索常量，不得重新写死数字。
    if re.search(r"RECENT_SEARCH_MIN_LENGTH\s*=\s*\d", recent):
        raise ValueError(f"{RECENT} 的最短长度必须引用 MESSAGE_SEARCH_MIN_LENGTH，不得写死数字")
    # 去重键必须先归一化，不得直接用原始大小写判断。
    if re.search(r"seen\.has\(query\)", recent):
        raise ValueError(f"{RECENT} 的去重必须使用 NFKC 小写归一化后的键")
    return checked + 2


def main() -> int:
    try:
        checked = check_recent_search()
    except ValueError as error:
        print(f"最近搜索核对失败，{error}", file=sys.stderr)
        return 2
    print(f"最近搜索一致：{checked} 项阈值来源、去重与存储回退")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
