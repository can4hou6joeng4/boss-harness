#!/usr/bin/env python3
"""核对工具耗时文案与状态优先级。

`toolTiming.ts` 的完成文案只在终态可用：内核 `durationMs` 优先，缺失时用本机
开始 / 结束时钟回退；排队、等待审批、已批准未开始、执行中、未获批准与未执行
即使误带 `durationMs` 也不显示成已完成。运行中文案中，等待审批只显示「已等待」，
未获批准与未执行返回空，其余按开始时间显示「已运行」，排队且只有 `waitingSince`
时显示「排队」。任一时间为负数、非有限数或结束早于开始时，不虚构时长。这里在
临时目录复制 `toolTiming.ts` / `turnTiming.ts` 并改写导入，用 Node 逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOL = "apps/desktop/src/renderer/src/data/toolTiming.ts"
TURN = "apps/desktop/src/renderer/src/data/turnTiming.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

TOOL_FRAGMENTS = (
    "const validTime = (value: unknown): value is number =>",
    'typeof value === "number" && Number.isFinite(value) && value >= 0;',
    "export function toolDurationMs(value: unknown): number | undefined {",
    "return validTime(value) ? value : undefined;",
    'const NON_TERMINAL_STATES: ReadonlySet<NonNullable<ToolTimingInput["executionState"]>> =',
    'new Set(["queued", "pending_approval", "approved", "executing", "not_approved", "not_executed"]);',
    "export function toolCompletedTimingLabel(toolUse: ToolTimingInput): string | null {",
    "if (toolUse.executionState && NON_TERMINAL_STATES.has(toolUse.executionState)) return null;",
    "const duration = toolDurationMs(toolUse.durationMs);",
    "if (duration !== undefined) return `耗时 ${formatDuration(duration)}`;",
    "if (toolUse.endedAt === undefined) return null;",
    "if (!validTime(toolUse.startedAt) || !validTime(toolUse.endedAt) || toolUse.endedAt < toolUse.startedAt) return null;",
    "return `耗时 ${formatDuration(toolUse.endedAt - toolUse.startedAt)}`;",
    "export function toolTimingLabel(toolUse: ToolTimingInput, now = Date.now()): string | null {",
    "const completed = toolCompletedTimingLabel(toolUse);",
    "if (completed) return completed;",
    "if (toolUse.endedAt !== undefined) return null;",
    "if (!validTime(now)) return null;",
    'if (toolUse.executionState === "pending_approval") {',
    "? `已等待 ${formatDuration(Math.max(0, now - toolUse.waitingSince))}` : null;",
    'if (toolUse.executionState === "not_approved" || toolUse.executionState === "not_executed") return null;',
    "if (validTime(toolUse.startedAt)) return `已运行 ${formatDuration(Math.max(0, now - toolUse.startedAt))}`;",
    'if (validTime(toolUse.waitingSince) && toolUse.executionState === "queued") {',
    "return `排队 ${formatDuration(Math.max(0, now - toolUse.waitingSince))}`;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { toolDurationMs, toolCompletedTimingLabel, toolTimingLabel } =
  await import(pathToFileURL(process.argv[1]).href);
const now = 61_000;
const results = {
  duration: [
    [0, 499, 500, 999, 1000, 59_500, 60_000, 90_000, 3_600_000, 3_660_000,
      -1, Number.NaN, Number.POSITIVE_INFINITY, "1", null].map(value => {
      const result = toolDurationMs(value);
      return result === undefined ? "undefined" : Number.isFinite(result) ? result : String(result);
    }),
  ],
  completed: [
    toolCompletedTimingLabel({ executionState: "completed", durationMs: 1500 }),
    toolCompletedTimingLabel({ durationMs: 0 }),
    toolCompletedTimingLabel({ startedAt: 1000, endedAt: 61_000 }),
    toolCompletedTimingLabel({ endedAt: 61_000 }),
    toolCompletedTimingLabel({ startedAt: 61_000, endedAt: 1000 }),
    toolCompletedTimingLabel({ startedAt: -1, endedAt: 1000 }),
    toolCompletedTimingLabel({ executionState: "executing", durationMs: 1500 }),
    toolCompletedTimingLabel({ executionState: "queued", durationMs: 1500 }),
  ],
  pending: [
    toolTimingLabel({ executionState: "pending_approval", waitingSince: 1000 }, now),
    toolTimingLabel({ executionState: "pending_approval", waitingSince: -1 }, now),
    toolTimingLabel({ executionState: "pending_approval" }, now),
    toolTimingLabel({ executionState: "pending_approval", startedAt: 1000 }, now),
  ],
  denied: [
    toolTimingLabel({ executionState: "not_approved", startedAt: 1000 }, now),
    toolTimingLabel({ executionState: "not_executed", startedAt: 1000 }, now),
  ],
  running: [
    toolTimingLabel({ startedAt: 1000 }, now),
    toolTimingLabel({ startedAt: 61_000 }, 1000),
    toolTimingLabel({ startedAt: -1 }, now),
    toolTimingLabel({ startedAt: 1000 }, Number.NaN),
    toolTimingLabel({ startedAt: 1000 }, -1),
  ],
  queued: [
    toolTimingLabel({ executionState: "queued", waitingSince: 1000 }, now),
    toolTimingLabel({ executionState: "queued", waitingSince: 61_000 }, 1000),
    toolTimingLabel({ executionState: "queued", startedAt: 1000 }, now),
    toolTimingLabel({ waitingSince: 1000 }, now),
  ],
  priority: [
    toolTimingLabel({ executionState: "pending_approval", startedAt: 1000, waitingSince: 1000 }, now),
    toolTimingLabel({ executionState: "completed", durationMs: 1500, startedAt: 1000, endedAt: 1000 }, now),
    toolTimingLabel({ executionState: "pending_approval", waitingSince: 1000, endedAt: 1000 }, now),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_DURATION = (
    [0, 499, 500, 999, 1000, 59500, 60000, 90000, 3600000, 3660000,
     "undefined", "undefined", "undefined", "undefined", "undefined"],
)
EXPECTED_COMPLETED = (
    "耗时 2 秒",
    "耗时 不足 1 秒",
    "耗时 1 分",
    None,
    None,
    None,
    None,
    None,
)
EXPECTED_PENDING = ("已等待 1 分", None, None, None)
EXPECTED_DENIED = (None, None)
EXPECTED_RUNNING = ("已运行 1 分", "已运行 不足 1 秒", None, None, None)
EXPECTED_QUEUED = ("排队 1 分", "排队 不足 1 秒", "已运行 1 分", None)
EXPECTED_PRIORITY = ("已等待 1 分", "耗时 2 秒", None)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        shared = (ROOT / SHARED).as_uri()
        (base / "turnTiming.ts").write_text(
            _read(TURN)
            .replace('from "@boss-harness/shared"', f'from "{shared}"')
            .replace('from "./timeFormat"', f'from "{shared}"'),
            encoding="utf-8",
        )
        target = base / "toolTiming.ts"
        target.write_text(_read(TOOL).replace('from "./turnTiming"', 'from "./turnTiming.ts"'), encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 工具耗时试算失败，请核对 Node.js 24+ 与 toolTiming.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的工具耗时结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回工具耗时矩阵")
    for key in ("duration", "completed", "pending", "denied", "running", "queued", "priority"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"工具耗时{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"工具耗时{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["duration"], EXPECTED_DURATION, "时长")
    checked += _compare(payload["completed"], EXPECTED_COMPLETED, "完成")
    checked += _compare(payload["pending"], EXPECTED_PENDING, "等待")
    checked += _compare(payload["denied"], EXPECTED_DENIED, "未执行")
    checked += _compare(payload["running"], EXPECTED_RUNNING, "运行")
    checked += _compare(payload["queued"], EXPECTED_QUEUED, "排队")
    checked += _compare(payload["priority"], EXPECTED_PRIORITY, "优先级")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_tool_timing.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_tool_timing.py")
    if "共 24 项结构、27 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_tool_timing.py 检查 24 项结构、27 项行为")
    return 2


def check_tool_timing() -> tuple[int, int]:
    structure = _expect(TOOL_FRAGMENTS, _read(TOOL), TOOL)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_tool_timing()
    except (OSError, ValueError) as error:
        print(f"工具耗时规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具耗时规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
