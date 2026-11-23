#!/usr/bin/env python3
"""核对输入区 ↑ / ↓ 历史调取规则。

`composerHistory.ts` 决定输入区如何从本会话已有消息中调取历史：只收本会话
用户消息、跳过空白与超长条目、最多保留最近 50 条；进入历史时记住草稿，
非空输入按前缀过滤（与聊天内查找共用 NFKC + 大小写归一化），无匹配回退
逐条浏览；历史缩短后游标收敛回草稿；方向判定只在单行或无选区的空闲 ↑
进入历史，多行编辑与 ⇧ / ⌥ / ⌘ / Ctrl 组合保留原生行为。这里用 Node 在
临时目录加载真实模块，逐项核对上述规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HISTORY = "apps/desktop/src/renderer/src/data/composerHistory.ts"
SEARCH = "apps/desktop/src/renderer/src/data/searchText.ts"
CASE_FOLD = "apps/desktop/src/renderer/src/data/caseFold.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

HISTORY_FRAGMENTS = (
    "export const MAX_RECALL_PROMPTS = 50;",
    "export const MAX_RECALL_CHARS = 20_000;",
    "export function recallablePrompts(messages: readonly RecallMessage[]): string[] {",
    "for (let cursor = messages.length - 1; cursor >= 0 && prompts.length < MAX_RECALL_PROMPTS; cursor -= 1) {",
    'if (message?.role !== "user" || typeof message.content !== "string") continue;',
    "const text = message.content.trim();",
    "if (!text || text.length > MAX_RECALL_CHARS) continue;",
    "return prompts.reverse();",
    "export function recallOlder(prompts: readonly string[], state: PromptRecallState, value: string): PromptRecallResult {",
    "if (state.index >= count) return { state: { index: -1, draft: state.draft }, text: value };",
    "const prefix = searchText(value.trim());",
    "return { state: { index: count - 1, draft: value }, text: prompts[count - 1] ?? value };",
    "export function recallNewer(prompts: readonly string[], state: PromptRecallState, value: string): PromptRecallResult {",
    "? { state: { index: -1, draft: state.draft }, text: state.draft }",
    "function findMatchingPrompt(prompts: readonly string[], prefix: string, from: number, step: 1 | -1): number {",
    "if (prompt !== undefined && searchText(prompt).startsWith(prefix)) return index;",
    "export function recallAfterValueChange(state: PromptRecallState, value: string, owned: string): PromptRecallState {",
    "if (state.index === -1 || value === owned) return state;",
    'export function recallKeyDirection(event: RecallKeyEvent, browsing: boolean): "older" | "newer" | null {',
    "if (event.shiftKey || event.altKey || event.metaKey || event.ctrlKey) return null;",
    "(collapsed && (event.selectionStart === 0 || event.singleLine))",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { recallablePrompts, recallOlder, recallNewer, recallAfterValueChange, recallKeyDirection } =
  await import(pathToFileURL(process.argv[1]).href);
const ev = (key, extra = {}) => ({
  key, selectionStart: 0, selectionEnd: 0, singleLine: true,
  shiftKey: false, altKey: false, metaKey: false, ctrlKey: false, ...extra,
});
const stateOf = (state) => ({ index: state.index, draft: state.draft, prefix: state.prefix ?? "none" });
const long = (length) => "x".repeat(length);
const many = Array.from({ length: 60 }, (_, index) => ({ role: "user", content: `m${index}` }));
const results = {
  recallable: [
    recallablePrompts([
      { role: "user", content: "A" },
      { role: "agent", content: "X" },
      { role: "user", content: "B" },
    ]),
    recallablePrompts([
      { role: "user", content: "  hi  " },
      { role: "user", content: "   " },
      { role: "user" },
      { role: "user", content: "" },
    ]),
    (() => {
      const prompts = recallablePrompts([
        { role: "user", content: long(20000) },
        { role: "user", content: long(20001) },
      ]);
      return [prompts.length === 1, prompts[0] === long(20000)];
    })(),
    (() => {
      const prompts = recallablePrompts(many);
      return [prompts.length, prompts[0], prompts[prompts.length - 1]];
    })(),
  ],
  older: [
    (() => {
      const state = { index: -1, draft: "d" };
      const result = recallOlder([], state, "v");
      return { same: result.state === state, text: result.text };
    })(),
    (() => {
      const result = recallOlder(["a", "b"], { index: -1, draft: "" }, "");
      return stateOf(result.state);
    })(),
    (() => {
      const result = recallOlder(["alpha", "beta", "alpha two"], { index: -1, draft: "" }, "  ALPHA ");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallOlder(["alpha", "beta"], { index: -1, draft: "" }, "zzz");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallOlder(["alpha", "beta", "alpha two"], { index: 2, draft: "", prefix: "alpha" }, "alpha two");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const state = { index: 0, draft: "d" };
      const result = recallOlder(["a", "b"], state, "v");
      return { same: result.state === state, text: result.text };
    })(),
    (() => {
      const result = recallOlder(["a", "b"], { index: 5, draft: "d" }, "v");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallOlder(["a", "b", "c"], { index: 2, draft: "d" }, "v");
      return { ...stateOf(result.state), text: result.text };
    })(),
  ],
  newer: [
    (() => {
      const state = { index: -1, draft: "d" };
      const result = recallNewer(["a"], state, "v");
      return { same: result.state === state, text: result.text };
    })(),
    (() => {
      const result = recallNewer(["a", "b"], { index: 1, draft: "draft" }, "b");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallNewer(["a", "b"], { index: 0, draft: "d" }, "a");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallNewer(["alpha", "beta", "alpha two"], { index: 0, draft: "d", prefix: "alpha" }, "alpha");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallNewer(["alpha", "beta", "alpha two"], { index: 2, draft: "d", prefix: "alpha" }, "alpha two");
      return { ...stateOf(result.state), text: result.text };
    })(),
    (() => {
      const result = recallNewer(["a"], { index: 5, draft: "d" }, "v");
      return { ...stateOf(result.state), text: result.text };
    })(),
  ],
  changed: [
    (() => {
      const state = { index: -1, draft: "d" };
      return recallAfterValueChange(state, "x", "y") === state;
    })(),
    (() => {
      const state = { index: 2, draft: "d" };
      return recallAfterValueChange(state, "a", "a") === state;
    })(),
    (() => {
      const state = recallAfterValueChange({ index: 2, draft: "d" }, "new", "old");
      return { index: state.index, draft: state.draft };
    })(),
  ],
  keys: [
    [
      recallKeyDirection(ev("ArrowUp", { shiftKey: true }), false),
      recallKeyDirection(ev("ArrowUp", { altKey: true }), false),
      recallKeyDirection(ev("ArrowUp", { metaKey: true }), false),
      recallKeyDirection(ev("ArrowDown", { ctrlKey: true }), true),
    ],
    recallKeyDirection(ev("ArrowUp"), false),
    recallKeyDirection(ev("ArrowUp", { selectionStart: 3, selectionEnd: 3, singleLine: true }), false),
    recallKeyDirection(ev("ArrowUp", { selectionStart: 3, selectionEnd: 3, singleLine: false }), false),
    recallKeyDirection(ev("ArrowDown"), false),
    recallKeyDirection(ev("ArrowUp", { selectionStart: 0, selectionEnd: 2 }), false),
    recallKeyDirection(ev("ArrowDown", { selectionStart: 2, selectionEnd: 2, singleLine: false }), true),
    recallKeyDirection(ev("ArrowUp", { selectionStart: 1, selectionEnd: 3, singleLine: false }), true),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_RECALLABLE = (
    ["A", "B"],
    ["hi"],
    [True, True],
    [50, "m10", "m59"],
)
EXPECTED_OLDER = (
    {"same": True, "text": "v"},
    {"index": 1, "draft": "", "prefix": "none"},
    {"index": 2, "draft": "  ALPHA ", "prefix": "alpha", "text": "alpha two"},
    {"index": 1, "draft": "zzz", "prefix": "none", "text": "beta"},
    {"index": 0, "draft": "", "prefix": "alpha", "text": "alpha"},
    {"same": True, "text": "v"},
    {"index": -1, "draft": "d", "prefix": "none", "text": "v"},
    {"index": 1, "draft": "d", "prefix": "none", "text": "b"},
)
EXPECTED_NEWER = (
    {"same": True, "text": "v"},
    {"index": -1, "draft": "draft", "prefix": "none", "text": "draft"},
    {"index": 1, "draft": "d", "prefix": "none", "text": "b"},
    {"index": 2, "draft": "d", "prefix": "alpha", "text": "alpha two"},
    {"index": -1, "draft": "d", "prefix": "none", "text": "d"},
    {"index": -1, "draft": "d", "prefix": "none", "text": "v"},
)
EXPECTED_CHANGED = (True, True, {"index": -1, "draft": ""})
EXPECTED_KEYS = (
    [None, None, None, None],
    "older",
    "older",
    None,
    None,
    None,
    "newer",
    "older",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # composerHistory 经 searchText 再导入 caseFold，都是无扩展名相对路径；
    # Node 的类型剥离只解析显式扩展名，所以把三个文件复制到临时目录并改写导入，
    # 不改动仓库源文件。
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base / "caseFold.ts").write_text(_read(CASE_FOLD), encoding="utf-8")
        (base / "searchText.ts").write_text(
            _read(SEARCH).replace('from "./caseFold"', 'from "./caseFold.ts"'), encoding="utf-8")
        history = base / "composerHistory.ts"
        history.write_text(
            _read(HISTORY).replace('from "./searchText"', 'from "./searchText.ts"'), encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(history)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 输入历史试算失败，请核对 Node.js 24+ 与 composerHistory.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的输入历史结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回输入历史矩阵")
    for key in ("recallable", "older", "newer", "changed", "keys"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"输入历史{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"输入历史{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["recallable"], EXPECTED_RECALLABLE, "收集")
    checked += _compare(payload["older"], EXPECTED_OLDER, "上翻")
    checked += _compare(payload["newer"], EXPECTED_NEWER, "下翻")
    checked += _compare(payload["changed"], EXPECTED_CHANGED, "收敛")
    checked += _compare(payload["keys"], EXPECTED_KEYS, "方向")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_composer_history.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_composer_history.py")
    if "共 21 项结构、29 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_composer_history.py 检查 21 项结构、29 项行为")
    return 2


def check_composer_history() -> tuple[int, int]:
    structure = _expect(HISTORY_FRAGMENTS, _read(HISTORY), HISTORY)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_composer_history()
    except (OSError, ValueError) as error:
        print(f"输入历史规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"输入历史规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
