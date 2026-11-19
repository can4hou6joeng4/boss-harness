#!/usr/bin/env python3
"""核对保留目标提示的接线：面板与设置页共用同一判定，文档同步。

提示本身不改变内核行为，但它是自动压缩静默无效时唯一的界面反馈；接线被删掉
不会触发构建失败，因此用静态检查固定判定边界、两个入口与各自的取值来源。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = "apps/desktop/src/renderer/src/data/compactionSettings.ts"
PANEL = "apps/desktop/src/renderer/src/components/ContextPanel.tsx"
DIALOG = "apps/desktop/src/renderer/src/components/SettingsDialog.tsx"
USER_GUIDE = "docs/USER_GUIDE.md"
DESKTOP_GUIDE = "docs/DESKTOP_GUIDE.md"

HELPER_FRAGMENTS = (
    "export function keepTargetReachesLimit(keepRecentTokens: number, limit: number): boolean {",
    "Number.isSafeInteger(keepRecentTokens) && keepRecentTokens >= 1",
    "Number.isSafeInteger(limit) && limit > 0",
    "keepRecentTokens >= limit;",
)
PANEL_FRAGMENTS = (
    'import { keepTargetReachesLimit } from "../data/compactionSettings";',
    "const autoKeep = Number(auto.draft.keepRecentTokens);",
    "{budget && keepTargetReachesLimit(autoKeep, budget.inputBudget) &&",
    "{budget && keepValid && keepTargetReachesLimit(keep, budget.inputBudget) &&",
)
DIALOG_FRAGMENTS = (
    "const [compactionWindow, setCompactionWindow] = useState<number | null>(null);",
    "// 窗口随每轮读取重新确认：断连、读取失败或读取期间不拿上一次的窗口当「当前模型」。",
    "setCompactionWindow(null);",
    "const window = config.modelCapabilities?.contextWindow;",
    'setCompactionWindow(typeof window === "number" && Number.isSafeInteger(window) && window > 0 ? window : null);',
    "keepTargetReachesLimit(Number(compaction.keepRecentTokens), compactionWindow)",
)
EARLY_RETURN = 'if (!isOpen || section !== "context" || !harnessUp) return;'
DOC_FRAGMENTS = (
    (USER_GUIDE, "保留目标不低于当前模型输入预算时"),
    (USER_GUIDE, "保留目标不低于当前模型上下文窗口时"),
    (DESKTOP_GUIDE, "保留目标不低于当前输入预算时"),
    (DESKTOP_GUIDE, "保留目标不低于该窗口时"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_context_keep() -> int:
    settings = _read(SETTINGS)
    checked = _expect(HELPER_FRAGMENTS, settings, SETTINGS)
    # 判定只在纯函数里定义一次：其他文件不得复制边界表达式。
    if "keepRecentTokens >= limit" in _read(PANEL) or "keepRecentTokens >= limit" in _read(DIALOG):
        raise ValueError("保留目标判定只能定义在 compactionSettings.ts")

    panel = _read(PANEL)
    checked += _expect(PANEL_FRAGMENTS, panel, PANEL)
    # 面板必须各自先确认预算已读取，再取值比较；缺失预算时不能引用 inputBudget。
    if panel.count("keepTargetReachesLimit(") != 2:
        raise ValueError(f"{PANEL} 的保留目标提示必须先确认预算存在")

    dialog = _read(DIALOG)
    checked += _expect(DIALOG_FRAGMENTS, dialog, DIALOG)
    # 窗口来自内核能力投影；字符串或非整数值不能进入比较。
    if "config.modelCapabilities?.contextWindow" not in dialog:
        raise ValueError(f"{DIALOG} 的保留目标提示必须使用内核返回的上下文窗口")
    # 清空必须发生在按连接状态提前退出之前，否则断连时仍会沿用上一轮的窗口。
    clear_index = dialog.find("setCompactionWindow(null);")
    early_return = dialog.find(EARLY_RETURN)
    if clear_index < 0 or early_return < 0 or clear_index > early_return:
        raise ValueError(f"{DIALOG} 必须先清空窗口状态再按连接状态提前退出")

    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 2


def main() -> int:
    try:
        checked = check_context_keep()
    except ValueError as error:
        print(f"上下文保留提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文保留提示一致：{checked} 项判定、入口与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
