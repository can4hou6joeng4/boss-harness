#!/usr/bin/env python3
"""核对用量范围单选组的方向键循环。

「会话用量」范围单选组按 WAI-ARIA 惯例支持左右与上下方向键并循环移动。
结构侧固定四个方向键的映射、其他按键返回 null、越界保护与非负取模；行为
侧把真实 `usageViewKeys.ts` 复制到临时目录、改写类型导入，由 Node 驱动两个
视图与四个方向键的映射、首尾环绕、未知视图回退与重复调用稳定性，避免
上下键失效、负下标或未知视图被当成选项。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
KEYS = "apps/desktop/src/renderer/src/data/usageViewKeys.ts"

EXPECTED = 14

NODE_SCRIPT = """\
import { USAGE_VIEWS, usageViewStep } from "./usageViewKeys.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);

expect("选项顺序", same([...USAGE_VIEWS], ["log", "branch"]));
expect("右进", usageViewStep("log", "ArrowRight") === "branch");
expect("下进", usageViewStep("log", "ArrowDown") === "branch");
expect("左退", usageViewStep("branch", "ArrowLeft") === "log");
expect("上退", usageViewStep("branch", "ArrowUp") === "log");
expect("右进环绕", usageViewStep("branch", "ArrowRight") === "log");
expect("下进环绕", usageViewStep("branch", "ArrowDown") === "log");
expect("左退环绕", usageViewStep("log", "ArrowLeft") === "branch");
expect("上退环绕", usageViewStep("log", "ArrowUp") === "branch");
expect(
  "其他键返回 null",
  usageViewStep("log", "Enter") === null
    && usageViewStep("log", "") === null
    && usageViewStep("branch", "Tab") === null,
);
expect("大小写敏感", usageViewStep("log", "arrowright") === null);
expect(
  "未知视图返回 null",
  usageViewStep("usage" as any, "ArrowRight") === null
    && usageViewStep("" as any, "ArrowLeft") === null,
);
expect(
  "重复调用稳定",
  usageViewStep("log", "ArrowRight") === "branch"
    && usageViewStep("log", "ArrowRight") === "branch",
);
expect(
  "选项只读不被改动",
  USAGE_VIEWS.length === 2 && USAGE_VIEWS[0] === "log" && USAGE_VIEWS[1] === "branch",
);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import type { UsageView } from "./useThreadUsage";',
    'export const USAGE_VIEWS: readonly UsageView[] = ["log", "branch"];',
    "export function usageViewStep(view: UsageView, key: string): UsageView | null {",
    'const delta = key === "ArrowRight" || key === "ArrowDown" ? 1',
    ': key === "ArrowLeft" || key === "ArrowUp" ? -1 : 0;',
    "if (!delta) return null;",
    "const index = USAGE_VIEWS.indexOf(view);",
    "if (index < 0) return null;",
    "return USAGE_VIEWS[(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length]!;",
)

ORDERED = (
    # 映射：方向键 → 位移 → 非方向键退出 → 越界保护 → 非负取模循环。
    (
        "export function usageViewStep(view: UsageView, key: string): UsageView | null {",
        "const delta =",
        "if (!delta) return null;",
        "const index = USAGE_VIEWS.indexOf(view);",
        "if (index < 0) return null;",
        "return USAGE_VIEWS[(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length]!;",
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
    rewritten = source.replace('import type { UsageView } from "./useThreadUsage";\n', "")
    if "useThreadUsage" in rewritten:
        raise ValueError(f"{KEYS} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, KEYS)
    for group in ORDERED:
        checked += _ordered(group, source, KEYS)
    # 反向断言：上下键必须参与映射；取模前必须补齐长度；越界不得回退首项。
    if 'key === "ArrowDown"' not in source or 'key === "ArrowUp"' not in source:
        raise ValueError(f"{KEYS} 的方向键必须同时支持左右与上下")
    if "(index + delta) % USAGE_VIEWS.length" in source:
        raise ValueError(f"{KEYS} 的循环必须在取模前补齐非负")
    if "return USAGE_VIEWS[0]!;" in source:
        raise ValueError(f"{KEYS} 的未知视图必须返回 null")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(KEYS)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "usageViewKeys.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("用量视图按键行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"用量视图按键行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_usage_view_keys.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_usage_view_keys.py")
    if "共 18 项结构、14 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_usage_view_keys.py 检查 18 项结构、14 项行为")
    return 2


def check_usage_view_keys() -> tuple[int, int]:
    source = _read(KEYS)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_usage_view_keys()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"用量视图按键核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量视图按键一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
