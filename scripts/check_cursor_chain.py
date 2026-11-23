#!/usr/bin/env python3
"""核对分页游标链的环检测。

`cursorChain.ts` 在发出下一页请求前登记游标，重复即整体失败，避免异常内核的
环状游标反复请求同一批页。这里静态核对模块契约，并用 Node 直接加载真实模块，
覆盖首次登记、相邻重复、A → B → A、抛出后集合不变、标签拼接与集合隔离等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/cursorChain.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 分页游标链。",
    " * 只比较相邻游标会反复请求同一批页：列表重复渲染同一条目，会话恢复还会翻满",
    " * 页数上限。调用方在发出下一页请求前登记游标，重复即整体失败，不展示可疑数据。",
    "export function trackCursor(seen: Set<string>, next: string, label: string): void {",
    "if (seen.has(next)) throw new Error(`${label}分页未前进`);",
    "seen.add(next);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { trackCursor } = await import(pathToFileURL(process.argv[1]).href);
const capture = fn => {
  try {
    fn();
    return null;
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
};
const first = new Set();
const firstResult = capture(() => trackCursor(first, "A", "会话"));
const dupResult = capture(() => trackCursor(first, "A", "会话"));
const chain = new Set();
trackCursor(chain, "A", "会话");
trackCursor(chain, "B", "会话");
const loopResult = capture(() => trackCursor(chain, "A", "会话"));
const other = new Set();
const otherResult = capture(() => trackCursor(other, "A", "工具"));
const emptyLabel = capture(() => {
  const seen = new Set();
  trackCursor(seen, "x", "");
  trackCursor(seen, "x", "");
});
const numeric = new Set();
trackCursor(numeric, "01", "会话");
const numericResult = capture(() => trackCursor(numeric, "1", "会话"));
const spaced = capture(() => {
  const seen = new Set();
  trackCursor(seen, "x", "消息 列表");
  trackCursor(seen, "x", "消息 列表");
});
const result = {
  trace: [
    firstResult,
    dupResult,
    first.has("A"),
    loopResult,
    chain.size,
    otherResult,
    other.has("A") && chain.has("B"),
    emptyLabel,
    numericResult,
    spaced,
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED = (
    None,
    "会话分页未前进",
    True,
    "会话分页未前进",
    2,
    None,
    True,
    "分页未前进",
    None,
    "消息 列表分页未前进",
)
LABELS = {"trace": "游标"}


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
        raise ValueError("Node 分页游标试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 分页游标试算失败，请核对 Node.js 24+ 与 cursorChain.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的分页游标结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"分页游标{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"分页游标{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["trace"], EXPECTED, LABELS["trace"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_cursor_chain.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_cursor_chain.py")
    if "共 6 项结构、10 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_cursor_chain.py 检查 6 项结构、10 项行为")
    return 2


def check_cursor_chain() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_cursor_chain()
    except (OSError, ValueError) as error:
        print(f"分页游标规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分页游标规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
