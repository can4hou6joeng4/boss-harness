#!/usr/bin/env python3
"""核对摘要面板菜单与来源展开状态只在当前一次展开内有效。

`summaryPanelVisit.ts` 把面板可见性与两个临时状态放在同一个对象里：可见性变化时开启
新一次访问并复位临时状态，同一可见性原样返回。结构侧固定 `RightPanel` 在渲染期同步
可见性、不再用两个独立的 `useState` 保存菜单和来源展开；行为侧由 Node 直接加载真实
模块核对关闭复位、返回不恢复、分别切换与幂等。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "apps/desktop/src/renderer/src/data/summaryPanelVisit.ts"
PANEL = "apps/desktop/src/renderer/src/shell/RightPanel.tsx"
DOCS = "docs/TECHNICAL_REFERENCE.md"

MODULE_FRAGMENTS = (
    " * `RightPanel` 在关闭时返回 `null` 但保持挂载；`menu` 与 `expanded` 因此会跨关闭",
    " * 残留，下次展开无需点击就出现菜单并抢走焦点。把可见性与临时状态放进同一个对象，",
    " * 可见性变化时开启新一次访问并复位临时状态；同一可见性原样返回，以便调用方在",
    " * 渲染期幂等同步。",
    "export interface SummaryPanelVisit {",
    "export function syncSummaryPanelVisit(visit: SummaryPanelVisit, open: boolean): SummaryPanelVisit {",
    "return visit.open === open ? visit : { open, menu: false, expanded: false };",
    "export function withSummaryPanelMenu(visit: SummaryPanelVisit, menu: boolean): SummaryPanelVisit {",
    "return visit.menu === menu ? visit : { ...visit, menu };",
    "export function withSummaryPanelExpanded(visit: SummaryPanelVisit, expanded: boolean): SummaryPanelVisit {",
    "return visit.expanded === expanded ? visit : { ...visit, expanded };",
)
PANEL_FRAGMENTS = (
    'import { syncSummaryPanelVisit, withSummaryPanelExpanded, withSummaryPanelMenu, type SummaryPanelVisit } from "../data/summaryPanelVisit";',
    "  // 面板关闭时只返回 null 但保持挂载；菜单与来源展开必须在渲染期随可见性复位，避免重新展开时自动弹出旧菜单。",
    "const [visit, setVisit] = useState<SummaryPanelVisit>(() => ({ open: isOpen, menu: false, expanded: false }));",
    "if (visit.open !== isOpen) setVisit(syncSummaryPanelVisit(visit, isOpen));",
    "const menu = visit.menu, expanded = visit.expanded;",
    "const setMenu = (next: boolean) => setVisit(current => withSummaryPanelMenu(current, next));",
    "const setExpanded = (next: boolean) => setVisit(current => withSummaryPanelExpanded(current, next));",
)
OLD_STATE = (
    "[expanded, setExpanded] = useState",
    "[menu, setMenu] = useState",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { syncSummaryPanelVisit, withSummaryPanelMenu, withSummaryPanelExpanded } = await import(pathToFileURL(process.argv[1]).href);
const opened = { open: true, menu: false, expanded: false };
const menuOpen = withSummaryPanelMenu(opened, true);
const both = withSummaryPanelExpanded(menuOpen, true);
const closed = syncSummaryPanelVisit(both, false);
const returned = syncSummaryPanelVisit(closed, true);
const results = [
  ["同一可见性保持引用", syncSummaryPanelVisit(opened, true) === opened],
  ["菜单打开写入标志", menuOpen.menu === true && menuOpen.open === true],
  ["菜单打开不改原对象", opened.menu === false && menuOpen !== opened],
  ["重复打开保持引用", withSummaryPanelMenu(menuOpen, true) === menuOpen],
  ["菜单关闭清空标志", withSummaryPanelMenu(menuOpen, false).menu === false],
  ["来源展开写入标志", both.expanded === true && both.menu === true],
  ["来源展开不改原对象", menuOpen.expanded === false && both !== menuOpen],
  ["重复展开保持引用", withSummaryPanelExpanded(both, true) === both],
  ["来源收起清空标志", withSummaryPanelExpanded(both, false).expanded === false],
  ["关闭面板复位两个标志", closed.open === false && closed.menu === false && closed.expanded === false],
  ["关闭不改已展开状态", both.menu === true && both.expanded === true],
  ["返回面板不恢复旧状态", returned.open === true && returned.menu === false && returned.expanded === false],
].map(([name, ok]) => ({ name, ok }));
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_BEHAVIORS = 12


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
        raise ValueError("Node 摘要面板状态试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 摘要面板状态试算失败，请核对 Node.js 24+ 与 summaryPanelVisit.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的摘要面板状态结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回摘要面板状态结果列表")
    return payload


def _check_behaviors() -> int:
    payload = _run_node()
    if len(payload) != EXPECTED_BEHAVIORS:
        raise ValueError(f"摘要面板状态用例数量变化：期望 {EXPECTED_BEHAVIORS}，实际 {len(payload)}")
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError(f"摘要面板状态第 {index + 1} 个用例格式不符")
        if item.get("ok") is not True:
            raise ValueError(f"摘要面板状态用例失败：{item['name']}")
    return len(payload)


def _check_structures() -> int:
    panel = _read(PANEL)
    checked = _expect(MODULE_FRAGMENTS, _read(MODULE), MODULE)
    checked += _expect(PANEL_FRAGMENTS, panel, PANEL)
    for fragment in OLD_STATE:
        if fragment in panel:
            raise ValueError(f"{PANEL} 仍用独立状态保存：{fragment}")
    return checked + len(OLD_STATE)


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(DOCS)
    if "`check_summary_panel_visit.py`" not in reference:
        raise ValueError(f"{DOCS} 缺少 check_summary_panel_visit.py 的索引")
    summary = f"共 {structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"{DOCS} 缺少摘要面板状态检查的计数：{summary}")


def main() -> int:
    try:
        structures = _check_structures()
        behaviors = _check_behaviors()
        _check_documentation(structures, behaviors)
    except (OSError, ValueError) as error:
        print(f"摘要面板状态规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"摘要面板状态规则一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
