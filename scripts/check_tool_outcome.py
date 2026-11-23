#!/usr/bin/env python3
"""核对工具卡结果徽标的判定规则。

`toolOutcome.ts` 决定工具卡是否显示结果徽标与文案：只标注需要用户决策的状态，
成功与未回报保持安静。这里静态核对模块契约，并用 Node 直接加载真实模块，覆盖
九个明确状态、成功不打扰、显式状态优先与旧条目兜底等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/toolOutcome.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ThreadItem } from "@boss-harness/protocol";',
    'export type ToolOutcomeTone = "uncertain" | "failed" | "notExecuted" | "pending";',
    "export interface ToolOutcomeBadge {",
    "tone: ToolOutcomeTone;",
    "label: string;",
    " * 只标注需要用户决策的状态：成功与未回报不打扰。尤其不能把「未执行」「结果未确认」",
    " * 显示成成功——写操作（如打招呼）若被当成已生效，用户可能重复触达。",
    "export function toolOutcomeBadge(",
    'case "outcome_unknown":',
    'case "approved":',
    'case "executing":',
    'case "completed":\n      return null;',
    'if (errorCode === "SESSION_INTERRUPTED") return { tone: "uncertain", label: "结果未确认" };',
    'if (status === "failed") return { tone: "failed", label: "执行失败" };',
    'if (status === "running") return { tone: "pending", label: "执行中" };',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { toolOutcomeBadge } = await import(pathToFileURL(process.argv[1]).href);
const shape = badge => badge === null ? null : [badge.tone, badge.label];
const result = {
  cases: [
    shape(toolOutcomeBadge("outcome_unknown", "completed")),
    shape(toolOutcomeBadge("not_executed", "completed")),
    shape(toolOutcomeBadge("not_approved", "completed")),
    shape(toolOutcomeBadge("failed", "failed")),
    shape(toolOutcomeBadge("pending_approval", "running")),
    shape(toolOutcomeBadge("queued", "running")),
    shape(toolOutcomeBadge("approved", "running")),
    shape(toolOutcomeBadge("executing", "running")),
    shape(toolOutcomeBadge("completed", "completed")),
    shape(toolOutcomeBadge("completed", "failed", "SESSION_INTERRUPTED")),
    shape(toolOutcomeBadge("approved", "completed", "SESSION_INTERRUPTED")),
    shape(toolOutcomeBadge(undefined, "completed")),
    shape(toolOutcomeBadge(undefined, "failed")),
    shape(toolOutcomeBadge(undefined, "running")),
    shape(toolOutcomeBadge(undefined, "completed", "SESSION_INTERRUPTED")),
    shape(toolOutcomeBadge(undefined, "failed", "OTHER")),
    shape(toolOutcomeBadge(undefined, "running", "SESSION_INTERRUPTED")),
    shape(toolOutcomeBadge(undefined, "completed", "OTHER")),
    shape(toolOutcomeBadge(undefined, "completed", "session_interrupted")),
    shape(toolOutcomeBadge("mystery", "failed")),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED = (
    ["uncertain", "结果未确认"],
    ["notExecuted", "未执行"],
    ["notExecuted", "未获批准"],
    ["failed", "执行失败"],
    ["pending", "等待审批"],
    ["pending", "排队中"],
    ["pending", "执行中"],
    ["pending", "执行中"],
    None,
    None,
    ["pending", "执行中"],
    None,
    ["failed", "执行失败"],
    ["pending", "执行中"],
    ["uncertain", "结果未确认"],
    ["failed", "执行失败"],
    ["uncertain", "结果未确认"],
    None,
    None,
    ["failed", "执行失败"],
)
LABELS = {"cases": "徽标"}


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
        raise ValueError("Node 工具结果徽标试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 工具结果徽标试算失败，请核对 Node.js 24+ 与 toolOutcome.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的工具结果徽标结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"工具结果{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"工具结果{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_tool_outcome.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_tool_outcome.py")
    if "共 15 项结构、20 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_tool_outcome.py 检查 15 项结构、20 项行为")
    return 2


def check_tool_outcome() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_tool_outcome()
    except (OSError, ValueError) as error:
        print(f"工具结果徽标规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具结果徽标规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
