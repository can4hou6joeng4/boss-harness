#!/usr/bin/env python3
"""核对会话行的归档过滤、关键词匹配与排序。

搜索弹窗与侧栏共用 `sessionRows`：默认排除已归档会话、按会话 id 去重、
把标题与项目名拼接后做整串 NFKC 小写、按空白拆分关键词逐词匹配，最后按
更新时间降序。这里固定过滤顺序与归一化口径，避免归档会话混入、重复行，
或过滤与高亮使用不同的关键词规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ROWS = "apps/desktop/src/renderer/src/data/sessionRows.ts"
ORDER = "apps/desktop/src/renderer/src/data/sessionOrder.ts"
SEARCH_TEXT = "apps/desktop/src/renderer/src/data/searchText.ts"

FRAGMENTS = (
    'import type { ProjectFolder, SessionItem } from "./mockData";',
    'import { sessionUpdatedAt } from "./sessionOrder";',
    'export function sessionRows(folders: ProjectFolder[], query = "", options: SessionRowOptions = {}): SessionRow[] {',
    'const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("zh-CN");',
    "const keywords = normalize(query).trim().split(/\\s+/).filter(Boolean);",
    "const seen = new Set<string>();",
    "return folders.flatMap(folder => folder.sessions.map(session => ({ session, project: folder.name })))",
    "if (row.session.archived === true && options.includeArchived !== true) return false;",
    "if (seen.has(row.session.id)) return false;",
    "seen.add(row.session.id);",
    "const text = normalize(`${row.session.title} ${row.project}`);",
    "return keywords.every(keyword => text.includes(keyword));",
    ".sort((a, b) => sessionUpdatedAt(b.session) - sessionUpdatedAt(a.session));",
)

ORDERED = (
    # 过滤顺序：先归档，后去重；去重键在任何匹配之前登记。
    (
        "if (row.session.archived === true && options.includeArchived !== true) return false;",
        "if (seen.has(row.session.id)) return false;",
        "seen.add(row.session.id);",
        "const text = normalize(`${row.session.title} ${row.project}`);",
        "return keywords.every(keyword => text.includes(keyword));",
    ),
    # 关键词先归一化整串再拆分，与高亮共用 NFKC 小写口径。
    (
        'const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("zh-CN");',
        "const keywords = normalize(query).trim().split(/\\s+/).filter(Boolean);",
    ),
    # 排序按更新时间降序，无效时间由 sessionUpdatedAt 回退 0。
    (
        "export function sessionUpdatedAt(session: SessionItem): number {",
        "return parseIsoDateTime(session.updatedAt)?.getTime() ?? 0;",
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


def check_search_rows() -> int:
    rows = _read(ROWS)
    checked = 0
    checked += _expect(FRAGMENTS, rows, ROWS)
    for group in ORDERED[:2]:
        checked += _ordered(group, rows, ROWS)
    checked += _ordered(ORDERED[2], _read(ORDER), ORDER)
    # 跨文件：高亮使用的 searchText 必须是同一 NFKC + zh-CN 小写口径。
    search_text = _read(SEARCH_TEXT)
    checked += _expect((
        'const LOCALE = "zh-CN";',
        'export const searchText = (value: string) => value.normalize("NFKC").toLocaleLowerCase(LOCALE);',
    ), search_text, SEARCH_TEXT)
    # 反向断言：归档默认不纳入；关键词必须全部命中（every），不能退回单个关键词。
    if re.search(r"includeArchived\s*=\s*true", rows):
        raise ValueError(f"{ROWS} 的 includeArchived 默认必须为假")
    if "keywords.some(" in rows:
        raise ValueError(f"{ROWS} 的关键词必须全部命中，不能使用 some")
    if "normalize(row.session.title).includes" in rows:
        raise ValueError(f"{ROWS} 必须把标题与项目名拼接后再匹配")
    return checked + 3


def main() -> int:
    try:
        checked = check_search_rows()
    except ValueError as error:
        print(f"会话行核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话行一致：{checked} 项归档过滤、关键词与排序")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
