#!/usr/bin/env python3
"""核对侧栏提示的序号重播与清空语义。

连续两次复制同一内容时文案相同；若状态只存字符串，React 不会重排计时器，
`role="status"` 也不会重新播报。这里固定每次回执自增 `seq`、清空只清文案、
空态返回原对象，以及组件按 `seq` 作 key 并保留状态角色。行为侧把真实
`sidebarNotice.ts` 复制到临时目录，由 Node 直接加载驱动回执、清空与边界
输入，避免相同文案被复用、序号被重置或清空原地改写输入。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
NOTICE = "apps/desktop/src/renderer/src/data/sidebarNotice.ts"
SIDEBAR = "apps/desktop/src/renderer/src/shell/ProjectSidebar.tsx"

EXPECTED = 16

NODE_SCRIPT = """\
import {
  EMPTY_SIDEBAR_NOTICE,
  SIDEBAR_NOTICE_TIMEOUT_MS,
  clearSidebarNotice,
  nextSidebarNotice,
} from "./sidebarNotice.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);

expect("空态形状", same(EMPTY_SIDEBAR_NOTICE, { text: "", seq: 0 }));
expect("停留时长", SIDEBAR_NOTICE_TIMEOUT_MS === 2600);
expect(
  "首次回执",
  same(nextSidebarNotice(EMPTY_SIDEBAR_NOTICE, "已复制路径"), { text: "已复制路径", seq: 1 }),
);
const first = nextSidebarNotice(EMPTY_SIDEBAR_NOTICE, "已复制路径");
const second = nextSidebarNotice(first, "已复制路径");
expect("相同文案也自增", second.seq === 2 && second.text === "已复制路径");
expect("相同文案返回新对象", first !== second);
const third = nextSidebarNotice(second, "已复制编号");
expect("不同文案递增", third.seq === 3 && third.text === "已复制编号");
expect("以当前序号为基递增", nextSidebarNotice({ text: "", seq: 7 }, "x").seq === 8);
const origin = { text: "旧提示", seq: 4 };
nextSidebarNotice(origin, "新提示");
expect("回执不修改输入", same(origin, { text: "旧提示", seq: 4 }));
const cleared = clearSidebarNotice(third);
expect("清空只清文案", same(cleared, { text: "", seq: 3 }));
expect("清空返回新对象且不改输入", cleared !== third && third.text === "已复制编号");
expect("已空返回原对象", clearSidebarNotice(EMPTY_SIDEBAR_NOTICE) === EMPTY_SIDEBAR_NOTICE);
const emptyCustom = { text: "", seq: 5 };
expect("空文案状态返回原引用", clearSidebarNotice(emptyCustom) === emptyCustom);
expect("清空后回执继续递增", nextSidebarNotice(cleared, "再次复制").seq === 4);
const blank = nextSidebarNotice(EMPTY_SIDEBAR_NOTICE, "");
expect("空文案回执也自增", blank.seq === 1 && blank !== EMPTY_SIDEBAR_NOTICE);
const multi = nextSidebarNotice(EMPTY_SIDEBAR_NOTICE, " 第一行\\n第二行 ");
expect("多行文本原样保留", multi.text === " 第一行\\n第二行 ");
let running = EMPTY_SIDEBAR_NOTICE;
const seqs: number[] = [];
for (const text of ["a", "a", "b"]) {
  running = nextSidebarNotice(running, text);
  seqs.push(running.seq);
}
expect("连续回执单调递增", same(seqs, [1, 2, 3]));

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export type SidebarNotice = { text: string; seq: number };",
    'export const EMPTY_SIDEBAR_NOTICE: SidebarNotice = { text: "", seq: 0 };',
    "export const SIDEBAR_NOTICE_TIMEOUT_MS = 2600;",
    "export function nextSidebarNotice(current: SidebarNotice, text: string): SidebarNotice {",
    "return { text, seq: current.seq + 1 };",
    "export function clearSidebarNotice(current: SidebarNotice): SidebarNotice {",
    'return current.text ? { ...current, text: "" } : current;',
)

SIDEBAR_FRAGMENTS = (
    'import { clearSidebarNotice, EMPTY_SIDEBAR_NOTICE, nextSidebarNotice, SIDEBAR_NOTICE_TIMEOUT_MS, type SidebarNotice } from "../data/sidebarNotice";',
    "const timer = setTimeout(() => setNotice(clearSidebarNotice), SIDEBAR_NOTICE_TIMEOUT_MS);",
    '<div key={notice.seq} className="sidebar-feedback" role="status">{notice.text}</div>',
)

ORDERED = (
    # 回执：每次新建记录并自增序号。
    (
        "export function nextSidebarNotice(current: SidebarNotice, text: string): SidebarNotice {",
        "return { text, seq: current.seq + 1 };",
    ),
    # 清空：只清文案并保留原对象语义。
    (
        "export function clearSidebarNotice(current: SidebarNotice): SidebarNotice {",
        'return current.text ? { ...current, text: "" } : current;',
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


def _check_structure(source: str, sidebar: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, NOTICE)
    checked += _expect(SIDEBAR_FRAGMENTS, sidebar, SIDEBAR)
    for group in ORDERED:
        checked += _ordered(group, source, NOTICE)
    # 反向断言：文案相同时也要自增；清空不得重置序号；组件不得改用文案作 key。
    if "current.text === text" in source:
        raise ValueError(f"{NOTICE} 相同文案也必须生成新回执并自增序号")
    if source.count('{ text: "", seq: 0 }') != 1:
        raise ValueError(f"{NOTICE} 的清空路径不得重置序号")
    if "key={notice.text}" in sidebar:
        raise ValueError(f"{SIDEBAR} 的提示节点必须按序号重建，不能按文案")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(NOTICE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "sidebarNotice.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("侧栏提示行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"侧栏提示行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_sidebar_notice.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_sidebar_notice.py")
    if "共 17 项结构、16 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_sidebar_notice.py 检查 17 项结构、16 项行为")
    return 2


def check_sidebar_notice() -> tuple[int, int]:
    source = _read(NOTICE)
    sidebar = _read(SIDEBAR)
    structure = _check_structure(source, sidebar)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_sidebar_notice()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"侧栏提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"侧栏提示一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
