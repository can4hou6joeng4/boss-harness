#!/usr/bin/env python3
"""核对会话内查找状态行的计数单位与分支。

状态行按「处命中」计数，与游标的跳转单位一致；只有正文零命中时才提示
「含详情可命中 N 条消息」，高亮超过上限时才补「仅前 N 处高亮」。这里固定
分支顺序、位次的 1 起始显示与夹取、高亮上限的缺省来源，避免状态行误报
截断或把可停靠数当成真实命中数。行为侧把真实 `findStatus.ts` 复制到临时
目录、改写导入，并从真实 `findHighlight.ts` 抽取常量生成最小依赖，由 Node
直接加载驱动计数、夹取、截断与详情分支。
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
STATUS = "apps/desktop/src/renderer/src/data/findStatus.ts"
HIGHLIGHT = "apps/desktop/src/renderer/src/data/findHighlight.ts"

EXPECTED = 24

NODE_SCRIPT = """\
import { findStatusText } from "./findStatus.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);

expect("空查询", findStatusText({ query: "", total: 3, position: 0 }) === "输入关键词");
expect("纯空白查询", findStatusText({ query: "   ", total: 3, position: 0 }) === "输入关键词");
expect(
  "首位显示从一开始",
  findStatusText({ query: "q", total: 3, position: 0 }) === "第 1 / 3 处命中",
);
expect("位次递增", findStatusText({ query: "q", total: 3, position: 2 }) === "第 3 / 3 处命中");
expect("位次越界夹取", findStatusText({ query: "q", total: 3, position: 99 }) === "第 3 / 3 处命中");
expect("负位次收敛", findStatusText({ query: "q", total: 3, position: -5 }) === "第 1 / 3 处命中");
expect(
  "小数位次向下取整",
  findStatusText({ query: "q", total: 3, position: 1.9 }) === "第 2 / 3 处命中",
);
expect(
  "小数总数向下取整",
  findStatusText({ query: "q", total: 2.9, position: 0 }) === "第 1 / 2 处命中",
);
expect(
  "非有限总数按零",
  findStatusText({ query: "q", total: Number.NaN, position: 0 }) === "无匹配消息",
);
expect(
  "默认上限取常量",
  findStatusText({ query: "q", total: 300, position: 0, capped: true })
    === "第 1 / 300 处命中 · 仅前 200 处高亮",
);
expect(
  "自定义上限",
  findStatusText({ query: "q", total: 10, position: 0, capped: true, highlightLimit: 50 })
    === "第 1 / 10 处命中 · 仅前 50 处高亮",
);
expect(
  "上限小数向下取整",
  findStatusText({ query: "q", total: 10, position: 0, capped: true, highlightLimit: 49.9 })
    === "第 1 / 10 处命中 · 仅前 49 处高亮",
);
expect(
  "未截断不提示上限",
  findStatusText({ query: "q", total: 10, position: 0, capped: false }) === "第 1 / 10 处命中",
);
expect(
  "仅严格 true 视为截断",
  findStatusText({ query: "q", total: 10, position: 0, capped: "true" as any }) === "第 1 / 10 处命中",
);
expect(
  "详情提示",
  findStatusText({ query: "q", total: 0, position: 0, detailHits: 5 })
    === "正文无匹配 · 含详情可命中 5 条消息",
);
expect(
  "详情零不提示",
  findStatusText({ query: "q", total: 0, position: 0, detailHits: 0 }) === "无匹配消息",
);
expect(
  "详情缺省不提示",
  findStatusText({ query: "q", total: 0, position: 0 }) === "无匹配消息",
);
expect(
  "详情小数向下取整",
  findStatusText({ query: "q", total: 0, position: 0, detailHits: 3.9 })
    === "正文无匹配 · 含详情可命中 3 条消息",
);
expect(
  "详情非有限按零",
  findStatusText({ query: "q", total: 0, position: 0, detailHits: Number.POSITIVE_INFINITY })
    === "无匹配消息",
);
expect(
  "零命中优先于截断",
  findStatusText({ query: "q", total: 0, position: 0, capped: true }) === "无匹配消息",
);
expect(
  "有命中不提示详情",
  !findStatusText({ query: "q", total: 2, position: 0, detailHits: 5 }).includes("含详情"),
);
const statusInput = { query: "q", total: 3, position: 1, detailHits: 7, capped: true, highlightLimit: 9 };
findStatusText(statusInput);
expect(
  "输入不被修改",
  same(statusInput, { query: "q", total: 3, position: 1, detailHits: 7, capped: true, highlightLimit: 9 }),
);
expect(
  "查询首尾空白不影响判定",
  findStatusText({ query: "  q  ", total: 1, position: 0 }) === "第 1 / 1 处命中",
);
expect(
  "上限为零照实报告",
  findStatusText({ query: "q", total: 5, position: 0, capped: true, highlightLimit: 0 })
    === "第 1 / 5 处命中 · 仅前 0 处高亮",
);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { FIND_HIGHLIGHT_LIMIT } from "./findHighlight";',
    "query: string;",
    "total: number;",
    "position: number;",
    "detailHits?: number;",
    "capped?: boolean;",
    "highlightLimit?: number;",
    'if (!input.query.trim()) return "输入关键词";',
    "const whole = (value: number): number => Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;",
    "const total = whole(input.total);",
    "if (total > 0) {",
    "const position = Math.min(whole(input.position), total - 1);",
    "const limit = whole(input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT);",
    "return input.capped === true",
    "? `第 ${position + 1} / ${total} 处命中 · 仅前 ${limit} 处高亮`",
    ": `第 ${position + 1} / ${total} 处命中`;",
    "const detailHits = whole(input.detailHits ?? 0);",
    "if (detailHits > 0) return `正文无匹配 · 含详情可命中 ${detailHits} 条消息`;",
    'return "无匹配消息";',
)

ORDERED = (
    # 状态行：空查询 → 总数 → 有命中分支（位次夹取、上限、截断说明）→ 详情提示 → 无匹配。
    (
        'if (!input.query.trim()) return "输入关键词";',
        "const total = whole(input.total);",
        "if (total > 0) {",
        "const position = Math.min(whole(input.position), total - 1);",
        "const limit = whole(input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT);",
        "return input.capped === true",
        ": `第 ${position + 1} / ${total} 处命中`;",
        "const detailHits = whole(input.detailHits ?? 0);",
        "if (detailHits > 0) return `正文无匹配 · 含详情可命中 ${detailHits} 条消息`;",
        'return "无匹配消息";',
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
    rewritten = source.replace('from "./findHighlight";', 'from "./findHighlight.ts";')
    if 'from "./findHighlight";' in rewritten:
        raise ValueError(f"{STATUS} 的导入结构已变化，需要更新改写")
    return rewritten


def _highlight_constant(source: str) -> str:
    match = re.search(r"export const FIND_HIGHLIGHT_LIMIT = \d+;", source)
    if not match:
        raise ValueError(f"{HIGHLIGHT} 缺少 FIND_HIGHLIGHT_LIMIT 常量")
    return match.group(0)


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, STATUS)
    for group in ORDERED:
        checked += _ordered(group, source, STATUS)
    # 反向断言：数值向下取整；详情提示只在零命中分支出现一次；上限不得写死。
    if "Math.round(" in source:
        raise ValueError(f"{STATUS} 的位次与上限必须向下取整")
    if source.count("正文无匹配") != 1:
        raise ValueError(f"{STATUS} 的详情提示只能在正文零命中时出现一次")
    if source.index("正文无匹配") < source.index("return input.capped === true"):
        raise ValueError(f"{STATUS} 的详情提示不得先于有命中分支出现")
    if "?? 200" in source:
        raise ValueError(f"{STATUS} 的高亮上限必须引用 FIND_HIGHLIGHT_LIMIT")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(STATUS)
    highlight = _read(HIGHLIGHT)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "findStatus.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "findHighlight.ts").write_text(_highlight_constant(highlight), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("查找状态行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"查找状态行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_find_status.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_find_status.py")
    if "共 33 项结构、24 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_find_status.py 检查 33 项结构、24 项行为")
    return 2


def check_find_status() -> tuple[int, int]:
    source = _read(STATUS)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_find_status()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"查找状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找状态一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
