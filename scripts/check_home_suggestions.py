#!/usr/bin/env python3
"""核对首页建议卡填充前的判定。

`homeSuggestions.ts` 决定点击建议卡时是否直接改写输入框：当前输入为空，或与建议
（双方去除首尾空白后）完全相同时直接填充，其余情况先向用户确认。这里静态核对
模块契约，并由 Node 直接加载真实模块执行空白、碰撞与大小写用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/homeSuggestions.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 首页建议卡填充前的判断。",
    " * 建议卡一次点击就会改写整个输入框；已有未发送正文时先确认，",
    " * 避免把用户正在写或刚从草稿恢复的内容直接覆盖。空白草稿与相同内容无需确认。",
    'export type SuggestionFillIntent = "apply" | "confirm";',
    "export function suggestionFillIntent(current: string, suggestion: string): SuggestionFillIntent {",
    "const existing = current.trim();",
    'if (!existing || existing === suggestion.trim()) return "apply";',
    'return "confirm";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { suggestionFillIntent } = await import(pathToFileURL(process.argv[1]).href);
const pairs = [
  ["", "hi"],
  ["   ", "hi"],
  ["\n\t", "x"],
  ["hello", "hello"],
  [" hello ", "hello"],
  ["hello", " hello "],
  ["", ""],
  ["hello", "world"],
  ["h", "hello"],
  ["hello world", "hello"],
  ["Hello", "hello"],
  ["hello", "Hello"],
];
const result = { cases: pairs.map(([current, suggestion]) => suggestionFillIntent(current, suggestion)) };
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_CASES = (
    "apply", "apply", "apply", "apply", "apply", "apply", "apply",
    "confirm", "confirm", "confirm", "confirm", "confirm",
)
LABELS = {"cases": "判定"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "homeSuggestions.ts"
        target.write_text(_read(TARGET), encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 首页建议卡试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 首页建议卡试算失败，请核对 Node.js 24+ 与 homeSuggestions.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的首页建议卡结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"首页建议卡{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"首页建议卡{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_home_suggestions.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_home_suggestions.py")
    if "共 8 项结构、12 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_home_suggestions.py 检查 8 项结构、12 项行为")
    return 2


def check_home_suggestions() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_home_suggestions()
    except (OSError, ValueError) as error:
        print(f"首页建议卡填充判定核对失败，{error}", file=sys.stderr)
        return 2
    print(f"首页建议卡填充判定一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
