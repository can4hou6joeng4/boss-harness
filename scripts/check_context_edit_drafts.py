#!/usr/bin/env python3
"""核对上下文编辑草稿缓存的隔离与清除规则。

`contextEditDrafts.ts` 在应用生命周期内按「会话 + 消息」保留未提交的替换正文。
这里静态核对模块契约，并用 Node 直接加载真实模块，覆盖覆盖写入、空串与 `null`
区分、会话 / 消息隔离、清除范围与拼接碰撞等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/contextEditDrafts.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 消息上下文编辑的未保存替换文本按「会话 + 消息」保留在应用生命周期内。",
    " * 用户尚未提交的正文。同一会话的不同消息各存各的，不互相覆盖。",
    "const drafts = new Map<string, string>();",
    "const keyOf = (threadId: string, itemId: string) => `${threadId}\\u0000${itemId}`;",
    "export function readContextEditDraft(threadId: string, itemId: string): string | null {",
    "return drafts.get(keyOf(threadId, itemId)) ?? null;",
    "export function writeContextEditDraft(threadId: string, itemId: string, draft: string): void {",
    "drafts.set(keyOf(threadId, itemId), draft);",
    "export function clearContextEditDraft(threadId: string, itemId: string): void {",
    "drafts.delete(keyOf(threadId, itemId));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { readContextEditDraft, writeContextEditDraft, clearContextEditDraft } = await import(pathToFileURL(process.argv[1]).href);
const read = (threadId, itemId) => readContextEditDraft(threadId, itemId);
const trace = [];
trace.push(read("t1", "i1"));
writeContextEditDraft("t1", "i1", "hello");
trace.push(read("t1", "i1"));
writeContextEditDraft("t1", "i1", "hello2");
trace.push(read("t1", "i1"));
trace.push(read("t1", "i2"));
writeContextEditDraft("t1", "i2", "second");
trace.push(read("t1", "i2"));
trace.push(read("t2", "i1"));
writeContextEditDraft("t2", "i1", "other");
trace.push(read("t2", "i1"));
trace.push(read("t1", "i1"));
clearContextEditDraft("t1", "i1");
trace.push(read("t1", "i1"));
trace.push(read("t1", "i2"));
writeContextEditDraft("t1", "i1", "🙂\n  ");
trace.push(read("t1", "i1"));
writeContextEditDraft("t1", "i1", "");
trace.push(read("t1", "i1"));
clearContextEditDraft("t1", "i1");
writeContextEditDraft("t1", "i1", "again");
trace.push(read("t1", "i1"));
clearContextEditDraft("missing", "none");
writeContextEditDraft("a-b", "c", "dash");
writeContextEditDraft("a", "b-c", "nested");
trace.push(read("a-b", "c"));
trace.push(read("a", "b-c"));
writeContextEditDraft("a b", "c", "space");
writeContextEditDraft("a", "b c", "spaced");
trace.push(read("a b", "c"));
trace.push(read("a", "b c"));
writeContextEditDraft("ab", "c", "joined-left");
writeContextEditDraft("a", "bc", "joined-right");
trace.push(read("ab", "c"));
trace.push(read("a", "bc"));
process.stdout.write(JSON.stringify({ trace }));
"""

EXPECTED = (
    None,
    "hello",
    "hello2",
    None,
    "second",
    None,
    "other",
    "hello2",
    None,
    "second",
    "🙂\n  ",
    "",
    "again",
    "dash",
    "nested",
    "space",
    "spaced",
    "joined-left",
    "joined-right",
)
LABELS = {"trace": "草稿"}


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
        raise ValueError("Node 上下文编辑草稿试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 上下文编辑草稿试算失败，请核对 Node.js 24+ 与 contextEditDrafts.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的上下文编辑草稿结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"上下文编辑{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"上下文编辑{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["trace"], EXPECTED, LABELS["trace"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_edit_drafts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_edit_drafts.py")
    if "共 10 项结构、19 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_edit_drafts.py 检查 10 项结构、19 项行为")
    return 2


def check_context_edit_drafts() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_edit_drafts()
    except (OSError, ValueError) as error:
        print(f"上下文编辑草稿规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文编辑草稿规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
