#!/usr/bin/env python3
"""核对运行状态面板的分区标识与键盘导航。

`cockpitTabs.ts` 固定四个分区、生成标签与内容区的 ARIA id，并实现水平 tablist
的 ← / → / Home / End 导航。这里静态核对模块契约，并用 Node 直接加载真实模块，
覆盖循环移动、首末跳转、未知按键、越界与非整数索引等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/cockpitTabs.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 运行状态面板的分区标识与 WAI-ARIA Tabs 导航。",
    " * 标签与内容区共用同一组 id 构造函数，避免 aria-controls 与实际节点漂移。",
    'export const COCKPIT_TAB_KEYS = ["overview", "turns", "approvals", "catalog"] as const;',
    "export type CockpitTab = typeof COCKPIT_TAB_KEYS[number];",
    "return `cockpit-tab-${tab}`;",
    "return `cockpit-panel-${tab}`;",
    " * 水平 tablist 的键盘导航：← / → 循环移动，Home / End 跳到首末。",
    " * 返回目标索引；其他按键、越界索引或非整数返回 null，交回浏览器默认行为。",
    "export function cockpitTabIndexForKey(index: number, length: number, key: string): number | null {",
    "if (!Number.isInteger(index) || index < 0 || index >= length) return null;",
    'if (key === "ArrowRight") return (index + 1) % length;',
    'if (key === "ArrowLeft") return (index - 1 + length) % length;',
    'if (key === "Home") return 0;',
    'if (key === "End") return length - 1;',
    "return null;\n}",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { COCKPIT_TAB_KEYS, cockpitTabId, cockpitTabPanelId, cockpitTabIndexForKey } = await import(pathToFileURL(process.argv[1]).href);
const nav = [
  [0, 4, "ArrowRight"],
  [3, 4, "ArrowRight"],
  [0, 4, "ArrowLeft"],
  [1, 4, "ArrowLeft"],
  [2, 4, "Home"],
  [2, 4, "End"],
  [0, 4, "Enter"],
  [0, 4, "ArrowUp"],
  [0, 4, ""],
  [-1, 4, "ArrowRight"],
  [4, 4, "ArrowRight"],
  [1.5, 4, "ArrowRight"],
  [NaN, 4, "ArrowRight"],
  [0, 0, "ArrowRight"],
  [0, 1, "ArrowRight"],
  [0, 1, "ArrowLeft"],
  [0, 4, "End"],
  [3, 4, "Home"],
];
const result = {
  keys: [COCKPIT_TAB_KEYS.join(",")],
  ids: COCKPIT_TAB_KEYS.map(tab => [cockpitTabId(tab), cockpitTabPanelId(tab)]),
  nav: nav.map(([index, length, key]) => cockpitTabIndexForKey(index, length, key)),
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_KEYS = ("overview,turns,approvals,catalog",)
EXPECTED_IDS = (
    ["cockpit-tab-overview", "cockpit-panel-overview"],
    ["cockpit-tab-turns", "cockpit-panel-turns"],
    ["cockpit-tab-approvals", "cockpit-panel-approvals"],
    ["cockpit-tab-catalog", "cockpit-panel-catalog"],
)
EXPECTED_NAV = (1, 0, 3, 0, 0, 3, None, None, None, None, None, None, None, None, 0, 0, 3, 0)
LABELS = {"keys": "分区", "ids": "标识", "nav": "导航"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 运行状态面板试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 运行状态面板试算失败，请核对 Node.js 24+ 与 cockpitTabs.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的运行状态面板结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"运行状态面板{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"运行状态面板{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["keys"], EXPECTED_KEYS, LABELS["keys"])
            + _compare(payload["ids"], EXPECTED_IDS, LABELS["ids"])
            + _compare(payload["nav"], EXPECTED_NAV, LABELS["nav"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_cockpit_tabs.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_cockpit_tabs.py")
    if "共 15 项结构、23 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_cockpit_tabs.py 检查 15 项结构、23 项行为")
    return 2


def check_cockpit_tabs() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_cockpit_tabs()
    except (OSError, ValueError) as error:
        print(f"运行状态面板规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"运行状态面板规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
