#!/usr/bin/env python3
"""核对消息工具栏可复制的文本。

`messageCopy.ts` 优先取气泡段落，其次正文与计划正文，最后按工具卡可见字段拼装：
工具名、结果徽标、耗时、审批行、输入、来源编号、查询时间、错误码、恢复建议与输出。
思考过程不算正文。依赖链复制到临时目录并统一改写相对导入与共享包导入后，由 Node
直接加载真实模块执行用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/messageCopy.ts"
DATA = "apps/desktop/src/renderer/src/data"
DEPENDENCIES = (
    "mockData.ts",
    "approvalCopy.ts",
    "toolOutcome.ts",
    "toolSource.ts",
    "toolTiming.ts",
    "turnTiming.ts",
    "timeFormat.ts",
)
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"
RELATIVE = re.compile(r'''(?m)^(import [^"']*from |export [^"']*from )"\./([A-Za-z0-9_]+)"''')

FRAGMENTS = (
    'import type { MessageItem } from "./mockData";',
    'import { approvalCopyLine } from "./approvalCopy";',
    'import { toolOutcomeBadge } from "./toolOutcome";',
    'import { toolQueriedAtText } from "./toolSource";',
    'import { toolCompletedTimingLabel } from "./toolTiming";',
    "export function messageCopyText(item: CopySource): string {",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { messageCopyText } = await import(pathToFileURL(process.argv[1]).href);
const full = {
  name: "boss_hr_greet",
  executionState: "failed",
  status: "failed",
  errorCode: "E1",
  durationMs: 1500,
  input: "in",
  source: { ref: "R1", tool: "t", queriedAt: "2026-11-24T10:30:00Z" },
  recoveryAction: "检查网络",
  output: "out",
};
const fullText = messageCopyText({ toolUse: full });
const order = ["工具：boss_hr_greet", "状态：执行失败", "耗时 2 秒", "in",
  "来源编号：R1", "查询于：2026-11-24T10:30:00Z", "错误码：E1", "恢复建议：检查网络", "out"];
const positions = order.map((part) => fullText.indexOf(part));
const duplicated = messageCopyText({
  toolUse: { name: "t", input: "x" },
  approval: { toolName: "boss_hr_greet", description: "d" },
});
const cases = [
  messageCopyText({ paragraphs: ["a", "b"], content: "c" }) === "a\n\nb",
  messageCopyText({ paragraphs: ["a", "  ", "b"], content: "c" }) === "a\n\nb",
  messageCopyText({ content: " hi " }) === " hi ",
  messageCopyText({}) === "",
  messageCopyText({ plan: { content: "计划" } }) === "计划",
  messageCopyText({ content: "正文", plan: { content: "计划" } }) === "正文",
  messageCopyText({ toolUse: { name: "", input: "x" } }) === "工具：tool\n\nx",
  positions.every((p) => p >= 0) && positions.every((p, i) => i === 0 || p > positions[i - 1]),
  messageCopyText({ toolUse: { name: "t", output: "O", result: "R" } }).includes("O")
    && !messageCopyText({ toolUse: { name: "t", output: "O", result: "R" } }).includes("R"),
  messageCopyText({ toolUse: { name: "t", output: "  ", result: "R" } }).includes("R"),
  messageCopyText({ toolUse: { name: "t", executionState: "completed", durationMs: 1500 } }).includes("耗时 2 秒")
    && !messageCopyText({ toolUse: { name: "t", executionState: "queued", durationMs: 1500 } }).includes("耗时"),
  messageCopyText({ approval: { toolName: "boss_hr_greet", description: "打招呼", decision: "approve" } })
    === "审批工具：boss_hr_greet\n\n审批说明：打招呼\n\n审批：已批准",
  !duplicated.includes("审批工具：") && duplicated.includes("审批说明：d"),
  messageCopyText({ toolUse: { name: "t", input: "x", source: { ref: "R", tool: "t", queriedAt: "2026-11-24T10:30:00Z" } } })
    .includes("查询于：2026-11-24T10:30:00Z"),
  messageCopyText({ thinkingContent: "秘密" }) === "",
];
process.stdout.write(JSON.stringify({ cases }));
"""

EXPECTED_CASES = (True,) * 15
LABELS = {"cases": "用例"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _rewrite(relative: str) -> str:
    text = _read(relative).replace('"@boss-harness/shared"', f'"{(ROOT / SHARED).as_uri()}"')
    return RELATIVE.sub(r'\1"./\2.ts"', text)


def _write_chain(directory: Path) -> Path:
    for name in DEPENDENCIES:
        (directory / name).write_text(_rewrite(f"{DATA}/{name}"), encoding="utf-8")
    target = directory / "messageCopy.ts"
    target.write_text(_rewrite(TARGET), encoding="utf-8")
    return target


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = _write_chain(Path(directory))
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 消息复制文本试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 消息复制文本试算失败，请核对 Node.js 24+ 与 messageCopy.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的消息复制文本结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"消息复制文本{label}数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"消息复制文本{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_message_copy.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_message_copy.py")
    if "共 6 项结构、15 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_message_copy.py 检查 6 项结构、15 项行为")
    return 2


def check_message_copy() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_message_copy()
    except (OSError, ValueError) as error:
        print(f"消息复制文本核对失败，{error}", file=sys.stderr)
        return 2
    print(f"消息复制文本一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
