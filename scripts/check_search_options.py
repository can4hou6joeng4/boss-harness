#!/usr/bin/env python3
"""核对搜索结果的顺序、去重与命中定位意图。

搜索弹窗把内核命中排在会话标题结果之前，消息按会话与条目去重，找不到
对应会话行的命中直接丢弃；打开工具命中时要先展开工具块，否则搜索片段
与会话里可见的文本对不上。这里固定这些顺序与意图，避免键盘顺序与屏幕
不一致或定位到看不见的文字。行为侧把真实 `searchOptions.ts` 复制到临时
目录、删去类型导入，由 Node 直接加载驱动顺序、去重、角色标签与定位意图。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
OPTIONS = "apps/desktop/src/renderer/src/data/searchOptions.ts"

EXPECTED = 22

NODE_SCRIPT = """\
import { buildSearchOptions, searchHitFocus, searchRoleLabel } from "./searchOptions.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const rowOf = (id: string): any => ({ session: { id }, title: `T-${id}` });
const rowA = rowOf("s1");
const rowB = rowOf("s2");
const rows = [rowA, rowB];
const rowsById = new Map<string, any>([["s1", rowA], ["s2", rowB]]);
const hitOf = (threadId: string, itemId: string, role = "user"): any => ({ threadId, itemId, role });

const hitA = hitOf("s1", "i1");
const hitB = hitOf("s1", "i2");
const options = buildSearchOptions(rows, [hitA, hitB], rowsById);
expect(
  "消息命中在前",
  options.length === 4 && options[0].kind === "message" && options[1].kind === "message",
);
expect(
  "会话结果在后且顺序",
  options[2].kind === "session" && options[2].row === rowA
    && options[3].kind === "session" && options[3].row === rowB,
);
expect(
  "命中键格式",
  options[0].key === "message:s1:i1" && options[1].key === "message:s1:i2",
);
expect("会话键格式", options[2].key === "session:s1" && options[3].key === "session:s2");
expect("命中携带 hit 与 row", options[0].hit === hitA && options[0].row === rowA);
expect("会话结果携带 row", options[3].row === rowB);

const skipped = buildSearchOptions(rows, [hitOf("missing", "i1"), hitA], rowsById);
expect(
  "缺行命中被跳过且不中断",
  skipped.length === 3 && skipped[0].kind === "message" && skipped[0].key === "message:s1:i1",
);

const dedup = buildSearchOptions(rows, [hitA, hitOf("s1", "i1"), hitB], rowsById);
expect("重复命中去重", dedup.filter(option => option.kind === "message").length === 2);

const dupSessions = buildSearchOptions(
  [rowA, rowOf("s1"), rowB],
  [],
  new Map<string, any>([["s1", rowA], ["s2", rowB]]),
);
expect(
  "同一会话只入列一次",
  dupSessions.length === 2 && dupSessions[0].row === rowA && dupSessions[1].row === rowB,
);

expect("空输入返回空列表", buildSearchOptions([], [], new Map()).length === 0);
const noRows = buildSearchOptions(rows, [hitOf("missing", "x")], rowsById);
expect(
  "全部缺行仍返回会话",
  noRows.length === 2 && noRows.every(option => option.kind === "session"),
);

expect("角色标签用户", searchRoleLabel("user") === "你");
expect("角色标签工具", searchRoleLabel("tool") === "工具");
expect("角色标签助手", searchRoleLabel("assistant") === "助手");
expect("角色标签未知回退助手", searchRoleLabel("system" as any) === "助手");

const toolFocus = searchHitFocus({ itemId: "i9", role: "tool" }, " 关键词 ");
expect(
  "工具命中展开工具块",
  toolFocus.revealToolBlock === true && toolFocus.itemId === "i9",
);
expect("定位关键词去首尾空白", toolFocus.query === "关键词");
expect("用户命中保持折叠", searchHitFocus({ itemId: "i1", role: "user" }, "q").revealToolBlock === false);
expect(
  "助手命中保持折叠",
  searchHitFocus({ itemId: "i2", role: "assistant" }, "q").revealToolBlock === false,
);
expect("默认查询为空", searchHitFocus({ itemId: "i3", role: "user" }).query === "");
expect("内部空白保留", searchHitFocus({ itemId: "i4", role: "user" }, " a b ").query === "a b");
const focusInput = { itemId: "i5", role: "tool" as const };
searchHitFocus(focusInput, " x ");
expect("定位不修改输入", focusInput.itemId === "i5" && focusInput.role === "tool");

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import type { SessionRow } from "./sessionRows";',
    "export type SearchOption =",
    '| { kind: "message"; key: string; hit: ThreadSearchMatch; row: SessionRow }',
    '| { kind: "session"; key: string; row: SessionRow };',
    "const options: SearchOption[] = [];",
    "const seen = new Set<string>();",
    "for (const hit of hits) {",
    "const row = rowsById.get(hit.threadId);",
    "if (!row) continue;",
    "const key = `message:${hit.threadId}:${hit.itemId}`;",
    "if (seen.has(key)) continue;",
    "seen.add(key);",
    'options.push({ kind: "message", key, hit, row });',
    "for (const row of rows) {",
    "const key = `session:${row.session.id}`;",
    'options.push({ kind: "session", key, row });',
    "return options;",
    'return role === "user" ? "你" : role === "tool" ? "工具" : "助手";',
    'return { itemId: hit.itemId, revealToolBlock: hit.role === "tool", query: query.trim() };',
)

ORDERED = (
    # 消息命中先于会话结果：逐条查行、去重、入列，再遍历会话行。
    (
        "const options: SearchOption[] = [];",
        "const seen = new Set<string>();",
        "for (const hit of hits) {",
        "const row = rowsById.get(hit.threadId);",
        "if (!row) continue;",
        "const key = `message:${hit.threadId}:${hit.itemId}`;",
        "if (seen.has(key)) continue;",
        "seen.add(key);",
        'options.push({ kind: "message", key, hit, row });',
        "for (const row of rows) {",
        "const key = `session:${row.session.id}`;",
        'options.push({ kind: "session", key, row });',
        "return options;",
    ),
    # 角色标签三分支：用户、工具、其余按助手。
    (
        'return role === "user" ? "你"',
        'role === "tool" ? "工具"',
        ': "助手";',
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
    rewritten = "".join(
        line for line in source.splitlines(keepends=True) if not line.startswith("import type ")
    )
    if "import type" in rewritten:
        raise ValueError(f"{OPTIONS} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, OPTIONS)
    for group in ORDERED:
        checked += _ordered(group, source, OPTIONS)
    # 反向断言：缺行必须跳过；只有工具命中展开工具块；关键词必须去掉首尾空白。
    if "if (!row) return" in source:
        raise ValueError(f"{OPTIONS} 找不到会话行的命中必须跳过，不能中断整个列表")
    if "revealToolBlock: true" in source:
        raise ValueError(f"{OPTIONS} 只有工具命中可以展开工具块")
    if 'revealToolBlock: hit.role === "tool"' not in source:
        raise ValueError(f"{OPTIONS} 的展开意图必须由命中角色决定")
    if "query: query.trim()" not in source:
        raise ValueError(f"{OPTIONS} 的定位关键词必须去掉首尾空白")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(OPTIONS)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "searchOptions.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("搜索结果行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"搜索结果行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_search_options.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_search_options.py")
    if "共 39 项结构、22 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_search_options.py 检查 39 项结构、22 项行为")
    return 2


def check_search_options() -> tuple[int, int]:
    source = _read(OPTIONS)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_search_options()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"搜索结果核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索结果一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
