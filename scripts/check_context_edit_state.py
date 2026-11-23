#!/usr/bin/env python3
"""核对上下文编辑弹窗的提交闸门与正文上限。

`contextEditState.ts` 决定「后续模型上下文」对话框能否提交，并按 Unicode 码点限制
替换文本长度。这里静态核对模块契约，并在临时目录改写共享包导入后加载真实模块，
覆盖闸门组合、码点上限、表情计数与旧快照提示等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/contextEditState.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    " * 「后续模型上下文」对话框的提交闸门。",
    " * 在重新读取成功前不能再基于它提交编辑。",
    "export interface ContextEditGate {",
    "loading: boolean;",
    "saving: boolean;",
    "stale: boolean;",
    "export function contextEditSubmitBlocked(gate: ContextEditGate): boolean {",
    "return gate.loading || gate.saving || gate.stale;",
    "export const CONTEXT_EDIT_MAX_TEXT_LENGTH = 32_000;",
    "/** 替换文本是否超过上限；`null` 表示排除消息，不受正文上限约束。 */",
    "export function contextEditTextTooLong(text: string | null): boolean {",
    "return text !== null && codePointLength(text) > CONTEXT_EDIT_MAX_TEXT_LENGTH;",
    'export const CONTEXT_EDIT_STALE_NOTICE = "下方是上次成功读取的上下文快照，可能已过期；重新读取成功前不会提交新的编辑。";',
    " * 的「最多 32000 字符」一致。界面不能直接用 HTML `maxLength`，它按 UTF-16 码元计数。",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { contextEditSubmitBlocked, contextEditTextTooLong, CONTEXT_EDIT_MAX_TEXT_LENGTH, CONTEXT_EDIT_STALE_NOTICE } = await import(pathToFileURL(process.argv[1]).href);
const gates = [
  [false, false, false],
  [true, false, false],
  [false, true, false],
  [false, false, true],
  [true, true, false],
  [true, false, true],
  [false, true, true],
  [true, true, true],
];
const result = {
  limit: [CONTEXT_EDIT_MAX_TEXT_LENGTH],
  gates: gates.map(([loading, saving, stale]) => contextEditSubmitBlocked({ loading, saving, stale })),
  texts: [
    contextEditTextTooLong(null),
    contextEditTextTooLong(""),
    contextEditTextTooLong("x".repeat(32_000)),
    contextEditTextTooLong("x".repeat(32_001)),
    contextEditTextTooLong("🙂".repeat(32_000)),
    contextEditTextTooLong("🙂".repeat(32_001)),
  ],
  notice: [CONTEXT_EDIT_STALE_NOTICE],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_LIMIT = (32_000,)
EXPECTED_GATES = (False, True, True, True, True, True, True, True)
EXPECTED_TEXTS = (False, False, False, True, False, True)
EXPECTED_NOTICE = ("下方是上次成功读取的上下文快照，可能已过期；重新读取成功前不会提交新的编辑。",)
LABELS = {"limit": "上限", "gates": "闸门", "texts": "正文", "notice": "提示"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "contextEditState.ts"
        target.write_text(
            _read(TARGET).replace('from "@boss-harness/shared"', f'from "{(ROOT / SHARED).as_uri()}"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 上下文编辑状态试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 上下文编辑状态试算失败，请核对 Node.js 24+ 与 contextEditState.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的上下文编辑状态结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"上下文编辑状态{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"上下文编辑状态{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["limit"], EXPECTED_LIMIT, LABELS["limit"])
            + _compare(payload["gates"], EXPECTED_GATES, LABELS["gates"])
            + _compare(payload["texts"], EXPECTED_TEXTS, LABELS["texts"])
            + _compare(payload["notice"], EXPECTED_NOTICE, LABELS["notice"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_edit_state.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_edit_state.py")
    if "共 15 项结构、16 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_edit_state.py 检查 15 项结构、16 项行为")
    return 2


def check_context_edit_state() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_edit_state()
    except (OSError, ValueError) as error:
        print(f"上下文编辑状态规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文编辑状态规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
