#!/usr/bin/env python3
"""核对技能编辑器关闭请求的意图判定。

`skillEditorClose.ts` 用三枚布尔量决定关闭请求是忽略、先确认还是直接关闭：
请求进行中不能关，未保存内容首次关闭只提示。这里静态核对模块契约，并用 Node
直接加载真实模块覆盖三枚输入的全部八种组合。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/skillEditorClose.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "/**",
    " * 技能对话框的关闭意图。",
    " * 保存 / 删除进行中不能关闭：请求已经发出，关闭只会让界面与磁盘状态分叉。",
    " * 有未保存内容时第一次关闭只提示，第二次才真正丢弃，避免误按 Esc 或点遮罩丢掉长正文。",
    'export type SkillDialogCloseIntent = "ignore" | "confirm" | "close";',
    "export function skillDialogCloseIntent(busy: boolean, dirty: boolean, confirmed: boolean): SkillDialogCloseIntent {",
    'if (busy) return "ignore";',
    'if (dirty && !confirmed) return "confirm";',
    'return "close";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { skillDialogCloseIntent } = await import(pathToFileURL(process.argv[1]).href);
const result = [];
for (const busy of [false, true]) {
  for (const dirty of [false, true]) {
    for (const confirmed of [false, true]) {
      result.push(skillDialogCloseIntent(busy, dirty, confirmed));
    }
  }
}
process.stdout.write(JSON.stringify(result));
"""

EXPECTED = (
    "close", "close", "confirm", "close",
    "ignore", "ignore", "ignore", "ignore",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 关闭意图试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 关闭意图试算失败，请核对 Node.js 24+ 与 skillEditorClose.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的关闭意图结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回关闭意图列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"关闭意图用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"关闭意图第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_editor_close.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_editor_close.py")
    if "共 9 项结构、8 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_editor_close.py 检查 9 项结构、8 项行为")
    return 2


def check_skill_editor_close() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_editor_close()
    except (OSError, ValueError) as error:
        print(f"技能编辑器关闭意图核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能编辑器关闭意图一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
