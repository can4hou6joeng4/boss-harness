#!/usr/bin/env python3
"""核对弹窗初始焦点的选择顺序。

`modalFocus.ts` 先找单行输入，再找多行文本域，最后回退到第一个控件；这保证文本域
弹窗的键盘输入直接落在正文上。这里静态核对模块契约，并用 Node 直接加载真实模块
覆盖优先级、同优先级首次命中与空列表边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/modalFocus.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 弹窗初始焦点的选择顺序。",
    " * 单行输入优先（搜索、新建技能等沿用原有行为），其次多行文本域，最后才回退到",
    " * 弹窗里第一个可聚焦控件。文本域弹窗（编辑排队消息、编辑技能）此前被跳过，",
    " * 焦点只能落在标题栏的关闭按钮上：直接键入不进入正文，误按 Enter 还会关闭弹窗。",
    "export function pickFocusTarget<T extends { tagName: string }>(items: readonly T[]): T | undefined {",
    'return items.find(item => item.tagName === "INPUT")',
    '?? items.find(item => item.tagName === "TEXTAREA")',
    "?? items[0];",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { pickFocusTarget } = await import(pathToFileURL(process.argv[1]).href);
const pick = tags => {
  const items = tags.map((tagName, index) => ({ tagName, index }));
  const found = pickFocusTarget(items);
  return found ? found.index : -1;
};
const result = [
  pick([]),
  pick(["BUTTON"]),
  pick(["TEXTAREA"]),
  pick(["INPUT"]),
  pick(["BUTTON", "TEXTAREA"]),
  pick(["BUTTON", "TEXTAREA", "INPUT"]),
  pick(["TEXTAREA", "INPUT"]),
  pick(["INPUT", "INPUT"]),
  pick(["TEXTAREA", "TEXTAREA"]),
  pick(["input"]),
  pick(["BUTTON", "SELECT"]),
];
process.stdout.write(JSON.stringify(result));
"""

EXPECTED = (-1, 0, 0, 0, 1, 2, 1, 0, 0, 0, 0)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _run_node(target: Path) -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 焦点选择试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 焦点选择试算失败，请核对 Node.js 24+ 与 modalFocus.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的焦点选择结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回焦点选择列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"焦点选择用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"焦点选择第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_run_node(ROOT / TARGET), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_modal_focus.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_modal_focus.py")
    if "共 8 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_modal_focus.py 检查 8 项结构、11 项行为")
    return 2


def check_modal_focus() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_modal_focus()
    except (OSError, ValueError) as error:
        print(f"弹窗焦点规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"弹窗焦点规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
