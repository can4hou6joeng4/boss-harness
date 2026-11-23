#!/usr/bin/env python3
"""核对审批结论文案、期限 ISO 转换与复制行拼装。

`approvalCopy.ts` 只接受三种已知审批结论，未知字符串按尚无结论处理，不把原始值
抄进文本；期限只接受有限正数 epoch 毫秒且不超过 Date 可表示上限，整秒时省略
`.000` 毫秒；复制行按工具名、说明、结论或期限（互斥）拼装，空白字段跳过，
参数原文与审批内部 id 不进入文本。这里用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COPY = "apps/desktop/src/renderer/src/data/approvalCopy.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

COPY_FRAGMENTS = (
    "const DECISION_TEXT: Record<string, string> = {",
    'approve: "已批准",',
    'deny: "已拒绝",',
    'expired: "审批已失效，已按未批准处理",',
    "const MAX_DATE_MS = 8.64e15;",
    'return typeof value === "string" && value.trim() ? value : null;',
    "export function approvalDecisionText(value: unknown): string | null {",
    "Object.prototype.hasOwnProperty.call(DECISION_TEXT, value)",
    "? DECISION_TEXT[value] ?? null",
    "export function approvalDeadlineText(value: unknown): string | null {",
    'if (typeof value !== "number" || !Number.isFinite(value) || value <= 0 || value > MAX_DATE_MS) return null;',
    "const iso = new Date(value).toISOString();",
    'return iso.endsWith(".000Z") ? `${iso.slice(0, -5)}Z` : iso;',
    "export function approvalCopyLine(",
    "if (!approval) return null;",
    "const toolName = options.includeToolName ? text(approval.toolName) : null;",
    "if (toolName) lines.push(`审批工具：${toolName}`);",
    "const description = text(approval.description);",
    "if (description) lines.push(`审批说明：${description}`);",
    "if (decision) {",
    "lines.push(`审批：${decision}`);",
    "const deadline = approvalDeadlineText(approval.deadline);",
    "if (deadline) lines.push(`审批期限：${deadline}`);",
    'return lines.length ? lines.join("\\n\\n") : null;',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { approvalDecisionText, approvalDeadlineText, approvalCopyLine } =
  await import(pathToFileURL(process.argv[1]).href);
const results = {
  decision: [
    ["approve", "deny", "expired"].map(approvalDecisionText),
    ["pending", "", "constructor", "__proto__", "toString"].map(approvalDecisionText),
    [0, true, {}, null].map(approvalDecisionText),
  ],
  deadline: [
    [0, -1, Number.NaN, Number.POSITIVE_INFINITY].map(approvalDeadlineText),
    [approvalDeadlineText(8.64e15), approvalDeadlineText(8.64e15 + 1)],
    [approvalDeadlineText(1700000000000), approvalDeadlineText(1700000000123)],
    ["1700000000000", null, undefined].map(approvalDeadlineText),
  ],
  line: [
    approvalCopyLine(undefined),
    approvalCopyLine({}),
    [
      approvalCopyLine({ toolName: "boss_hr_greet", description: "打招呼", decision: "approve" }),
      approvalCopyLine({ toolName: "boss_hr_greet", description: "打招呼", decision: "approve" }, { includeToolName: true }),
    ],
    approvalCopyLine({ toolName: "  ", description: " ", decision: "deny" }, { includeToolName: true }),
    approvalCopyLine({ description: "说明" }),
    approvalCopyLine({ decision: "approve", deadline: 1700000000000 }),
    approvalCopyLine({ decision: "pending", deadline: 1700000000000 }),
    approvalCopyLine({ decision: "pending", deadline: -1 }),
    approvalCopyLine({ deadline: 1700000000123 }),
    approvalCopyLine({ decision: "expired" }),
    approvalCopyLine({ description: "  " }),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_DECISION = (
    ["已批准", "已拒绝", "审批已失效，已按未批准处理"],
    [None, None, None, None, None],
    [None, None, None, None],
)
EXPECTED_DEADLINE = (
    [None, None, None, None],
    ["+275760-09-13T00:00:00Z", None],
    ["2023-11-14T22:13:20Z", "2023-11-14T22:13:20.123Z"],
    [None, None, None],
)
EXPECTED_LINE = (
    None,
    None,
    ["审批说明：打招呼\n\n审批：已批准", "审批工具：boss_hr_greet\n\n审批说明：打招呼\n\n审批：已批准"],
    "审批：已拒绝",
    "审批说明：说明",
    "审批：已批准",
    "审批期限：2023-11-14T22:13:20Z",
    None,
    "审批期限：2023-11-14T22:13:20.123Z",
    "审批：审批已失效，已按未批准处理",
    None,
)


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / COPY)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 审批复制试算失败，请核对 Node.js 24+ 与 approvalCopy.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的审批复制结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回审批复制矩阵")
    for key in ("decision", "deadline", "line"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"审批复制{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"审批复制{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["decision"], EXPECTED_DECISION, "结论")
    checked += _compare(payload["deadline"], EXPECTED_DEADLINE, "期限")
    checked += _compare(payload["line"], EXPECTED_LINE, "拼装")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_approval_copy.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_approval_copy.py")
    if "共 24 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_approval_copy.py 检查 24 项结构、18 项行为")
    return 2


def check_approval_copy() -> tuple[int, int]:
    structure = _expect(COPY_FRAGMENTS, _read(COPY), COPY)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_approval_copy()
    except (OSError, ValueError) as error:
        print(f"审批复制规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批复制规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
