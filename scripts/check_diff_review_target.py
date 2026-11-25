#!/usr/bin/env python3
"""核对变更审阅的临时状态与目标会话不会跨关闭或跨会话残留。

`diffReviewVisit.ts` 把弹窗可见性与文件下标、对比模式放在同一个状态对象里：可见性
变化时开启新一次审阅并复位；目标会话在打开时固定，背景会话切换后立即关闭。结构侧
固定 `UnifiedDiffModal` 的渲染期同步、`App` 的目标绑定与关闭复位；行为侧由 Node 直接
加载真实模块核对复位、幂等与目标可见性。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "apps/desktop/src/renderer/src/data/diffReviewVisit.ts"
MODAL = "apps/desktop/src/renderer/src/components/UnifiedDiffModal.tsx"
APP = "apps/desktop/src/renderer/src/App.tsx"
DOCS = "docs/TECHNICAL_REFERENCE.md"

MODULE_FRAGMENTS = (
    " * 变更审阅的临时状态与目标会话。",
    " * `UnifiedDiffModal` 关闭时只返回 `null`，组件实例仍挂载，文件下标与对比模式会跨",
    " * 关闭残留；可见性变化时开启新一次审阅并复位。目标会话则在打开时固定：背景会话",
    " * 切换后审阅必须立即关闭，否则弹窗内容会静默换成另一会话的变更。",
    'export type DiffReviewMode = "unified" | "split";',
    "export interface DiffReviewVisit {",
    "export function syncDiffReviewVisit(visit: DiffReviewVisit, open: boolean): DiffReviewVisit {",
    'return visit.open === open ? visit : { open, selected: 0, mode: "unified" };',
    "export function withDiffReviewFile(visit: DiffReviewVisit, selected: number): DiffReviewVisit {",
    "return visit.selected === selected ? visit : { ...visit, selected };",
    "export function withDiffReviewMode(visit: DiffReviewVisit, mode: DiffReviewMode): DiffReviewVisit {",
    "return visit.mode === mode ? visit : { ...visit, mode };",
    "export function diffReviewVisible(open: boolean, targetThreadId: string | null, activeThreadId: string | null): boolean {",
    "return open && targetThreadId !== null && targetThreadId === activeThreadId;",
)
MODAL_FRAGMENTS = (
    'import { syncDiffReviewVisit, withDiffReviewFile, withDiffReviewMode, type DiffReviewVisit, type DiffReviewMode } from "../data/diffReviewVisit";',
    "  // 弹窗关闭时只返回 null 但保持挂载；文件下标与模式随可见性复位，避免下次审阅从上次的选择开始。",
    'const [visit, setVisit] = useState<DiffReviewVisit>(() => ({ open: isOpen, selected: 0, mode: "unified" }));',
    "if (visit.open !== isOpen) setVisit(syncDiffReviewVisit(visit, isOpen));",
    "const selected = visit.selected, mode: DiffReviewMode = visit.mode;",
    "const setSelected = (next: number) => setVisit(current => withDiffReviewFile(current, next));",
    "const setMode = (next: DiffReviewMode) => setVisit(current => withDiffReviewMode(current, next));",
)
APP_FRAGMENTS = (
    'import { diffReviewVisible } from "./data/diffReviewVisit";',
    "const [diffThreadId, setDiffThreadId] = useState<string | null>(null);",
    "const diffVisible = diffReviewVisible(isDiffModalOpen, diffThreadId, activeSession?.id ?? null);",
    "if (isDiffModalOpen && !diffVisible) { setIsDiffModalOpen(false); setDiffThreadId(null); }",
    "onReviewDiff={() => { setDiffThreadId(activeSession?.id ?? null); setIsDiffModalOpen(true); }}",
    '<UnifiedDiffModal messages={messages} preview={preview} isOpen={diffVisible} onClose={() => { setIsDiffModalOpen(false); setDiffThreadId(null); }}',
)
OLD_PATTERNS = (
    (MODAL, "[selected, setSelected] = useState"),
    (MODAL, "[mode, setMode] = useState"),
    (APP, "<UnifiedDiffModal messages={messages} preview={preview} isOpen={isDiffModalOpen}"),
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { syncDiffReviewVisit, withDiffReviewFile, withDiffReviewMode, diffReviewVisible } = await import(pathToFileURL(process.argv[1]).href);
const opened = { open: true, selected: 0, mode: "unified" };
const picked = withDiffReviewFile(opened, 1);
const split = withDiffReviewMode(picked, "split");
const closed = syncDiffReviewVisit(split, false);
const returned = syncDiffReviewVisit(closed, true);
const results = [
  ["同一可见性保持引用", syncDiffReviewVisit(opened, true) === opened],
  ["选择文件写入下标", picked.selected === 1 && picked.mode === "unified"],
  ["选择文件不改原对象", opened.selected === 0 && picked !== opened],
  ["重复选择保持引用", withDiffReviewFile(picked, 1) === picked],
  ["切换模式写入模式", split.mode === "split" && split.selected === 1],
  ["切换模式不改原对象", picked.mode === "unified" && split !== picked],
  ["重复切换保持引用", withDiffReviewMode(split, "split") === split],
  ["关闭复位文件与模式", closed.open === false && closed.selected === 0 && closed.mode === "unified"],
  ["关闭不改已选中的状态", split.selected === 1 && split.mode === "split"],
  ["返回弹窗不恢复选择", returned.open === true && returned.selected === 0 && returned.mode === "unified"],
  ["未打开时不可见", diffReviewVisible(false, "s1", "s1") === false],
  ["目标缺失时不可见", diffReviewVisible(true, null, "s1") === false],
  ["目标匹配时可见", diffReviewVisible(true, "s1", "s1") === true],
  ["背景会话切换时关闭", diffReviewVisible(true, "s1", "s2") === false],
  ["没有活动会话时关闭", diffReviewVisible(true, "s1", null) === false],
].map(([name, ok]) => ({ name, ok }));
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_BEHAVIORS = 15


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _run_node() -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / MODULE)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 变更审阅状态试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 变更审阅状态试算失败，请核对 Node.js 24+ 与 diffReviewVisit.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的变更审阅状态结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回变更审阅状态结果列表")
    return payload


def _check_behaviors() -> int:
    payload = _run_node()
    if len(payload) != EXPECTED_BEHAVIORS:
        raise ValueError(f"变更审阅状态用例数量变化：期望 {EXPECTED_BEHAVIORS}，实际 {len(payload)}")
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError(f"变更审阅状态第 {index + 1} 个用例格式不符")
        if item.get("ok") is not True:
            raise ValueError(f"变更审阅状态用例失败：{item['name']}")
    return len(payload)


def _check_structures() -> int:
    checked = _expect(MODULE_FRAGMENTS, _read(MODULE), MODULE)
    checked += _expect(MODAL_FRAGMENTS, _read(MODAL), MODAL)
    app = _read(APP)
    checked += _expect(APP_FRAGMENTS, app, APP)
    for relative, pattern in OLD_PATTERNS:
        if pattern in _read(relative):
            raise ValueError(f"{relative} 仍保留旧写法：{pattern}")
    return checked + len(OLD_PATTERNS)


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(DOCS)
    if "`check_diff_review_target.py`" not in reference:
        raise ValueError(f"{DOCS} 缺少 check_diff_review_target.py 的索引")
    summary = f"共 {structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"{DOCS} 缺少变更审阅目标检查的计数：{summary}")


def main() -> int:
    try:
        structures = _check_structures()
        behaviors = _check_behaviors()
        _check_documentation(structures, behaviors)
    except (OSError, ValueError) as error:
        print(f"变更审阅目标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"变更审阅目标一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
