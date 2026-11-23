#!/usr/bin/env python3
"""核对折叠队列面板的可见项选择。

`queueSelection.ts` 在折叠状态下先保留最近的暂停项，再把名额分给最近待处理项，
最后才展示已结束项；返回顺序仍按持久化顺序。展开时原样返回。这里静态核对模块
结构，并用 Node 直接加载真实模块覆盖名额分配、状态分类与顺序保持。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueSelection.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { QueueItem } from "@boss-harness/protocol";',
    "/** 折叠状态下面板最多渲染的待处理项；展开后由内核投影上限约束。 */",
    "export const MAX_VISIBLE_QUEUE_ITEMS = 20;",
    'const isPending = (item: QueueItem) => item.status === "queued" || item.status === "delivering";',
    'const isTerminal = (item: QueueItem) => item.status === "delivered" || item.status === "cancelled";',
    " * 折叠时优先保留暂停项：它们不会自动投递，只能由用户重新排队或撤回；",
    " * 剩余名额给最近的排队 / 投递中项，名额允许时再显示最近的已结束项。",
    " * 返回顺序仍取持久化顺序，避免展示顺序与队列实际顺序不一致。",
    "export function selectVisibleQueueItems(items: QueueItem[], expanded: boolean): QueueItem[] {",
    "if (expanded) return items;",
    'const paused = items.filter(item => item.status === "paused").slice(-MAX_VISIBLE_QUEUE_ITEMS);',
    "const pendingRoom = Math.max(0, MAX_VISIBLE_QUEUE_ITEMS - paused.length);",
    "const pending = pendingRoom ? items.filter(isPending).slice(-pendingRoom) : [];",
    "const terminalRoom = Math.max(0, MAX_VISIBLE_QUEUE_ITEMS - paused.length - pending.length);",
    "const terminal = terminalRoom ? items.filter(isTerminal).slice(-terminalRoom) : [];",
    "const keep = new Set([...paused, ...pending, ...terminal].map(item => item.id));",
    "return items.filter(item => keep.has(item.id));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { selectVisibleQueueItems } = await import(pathToFileURL(process.argv[1]).href);
const item = (id, status) => ({ id, status, kind: "followUp", input: id });
const run = (specs, expanded = false) =>
  selectVisibleQueueItems(specs.map(([id, status]) => item(id, status)), expanded).map(entry => entry.id);
const seq = (prefix, count, status, start = 0) =>
  Array.from({ length: count }, (_, i) => [`${prefix}${start + i}`, status]);
const result = [
  run([["a", "queued"], ["b", "paused"], ["c", "delivered"]], true),
  run([]),
  run(seq("q", 5, "queued")),
  run(seq("q", 25, "queued")),
  run([...seq("p", 25, "paused"), ...seq("q", 5, "queued")]),
  run([...seq("p", 10, "paused"), ...seq("q", 15, "queued"), ...seq("t", 10, "delivered")]),
  run([...seq("p", 5, "paused"), ...seq("q", 10, "queued"), ...seq("t", 10, "delivered")]),
  run([...seq("p", 3, "paused"), ...seq("t", 25, "delivered")]),
  run([["a", "queued"], ["b", "weird"], ["c", "delivered"]]),
  run([["a", "queued"], ["b", "paused"], ["c", "delivered"]]),
  run([["a", "cancelled"], ["b", "delivered"]]),
  run([["a", "delivering"], ["b", "queued"]]),
  run(seq("q", 25, "queued"), true),
];
process.stdout.write(JSON.stringify(result));
"""


def seq(prefix: str, count: int, start: int = 0) -> list[str]:
    return [f"{prefix}{i}" for i in range(start, start + count)]


EXPECTED = (
    ["a", "b", "c"],
    [],
    seq("q", 5),
    seq("q", 20, 5),
    seq("p", 20, 5),
    seq("p", 10) + seq("q", 10, 5),
    seq("p", 5) + seq("q", 10) + seq("t", 5, 5),
    seq("p", 3) + seq("t", 17, 8),
    ["a", "c"],
    ["a", "b", "c"],
    ["a", "b"],
    ["a", "b"],
    seq("q", 25),
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
        raise ValueError("Node 可见队列项试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 可见队列项试算失败，请核对 Node.js 24+ 与 queueSelection.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的可见队列项结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回可见队列项列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"可见队列项用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"可见队列项第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_selection.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_selection.py")
    if "共 17 项结构、13 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_selection.py 检查 17 项结构、13 项行为")
    return 2


def check_queue_selection() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_selection()
    except (OSError, ValueError) as error:
        print(f"可见队列项核对失败，{error}", file=sys.stderr)
        return 2
    print(f"可见队列项一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
