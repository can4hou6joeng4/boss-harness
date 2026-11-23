#!/usr/bin/env python3
"""核对摘要面板的断连与任务状态收敛规则。

`contextPanelState.ts` 负责摘要面板在断连、任务记录缺失、开始回执未知、占用详情
持续不可核对和终态详情无法识别时的状态收敛：清掉由旧连接推导的易失状态，保留
仍在运行任务的核对入口，并在内核仍是并发裁决者的前提下解除没有恢复入口的界面
锁。这里直接用 Node 加载真实模块，核对每个收敛函数的字段、文案与阈值。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/contextPanelState.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "interface DisconnectState {",
    "unknownStart?: unknown;",
    "job?: ContextCompactJob;",
    "error: string;",
    "lifecycleReleased?: boolean;",
    "export interface DisconnectPatch {",
    "plan: undefined;",
    "reading: false;",
    "planning: false;",
    "starting: false;",
    "cancelInFlight: false;",
    "turnActive: false;",
    "lifecycleReleased: false;",
    "export function settleReadFlight<T>(",
    "flights: Map<string, T>, pending: Set<string>, id: string, flight: T,",
    "if (flights.get(id) !== flight) return false;",
    "flights.delete(id);",
    "return pending.delete(id);",
    "export function disconnectPatch(state: DisconnectState): DisconnectPatch {",
    "plan: undefined, reading: false, planning: false, starting: false, cancelInFlight: false,",
    "turnActive: false, lifecycleReleased: false,",
    'state.unknownStart ? "开始压缩的回执未知。重连后只核对原任务，不会重复开始。"',
    'state.job?.status === "running" ? "连接已断开，摘要任务状态待核对。" : state.error,',
    "export interface MissingJobPatch {",
    "unknownStart: undefined;",
    "discoveryStopped: false;",
    "unavailableJob?: string;",
    "lifecycleReleased?: false;",
    "export function missingJobPatch(state: DisconnectState): MissingJobPatch {",
    "unknownStart: undefined,",
    "starting: false,",
    "discoveryStopped: false,",
    "lifecycleReleased: false,",
    '...(state.job?.status === "running" ? { unavailableJob: state.job.jobId } : {}),',
    '"本机内核没有保留上次开始压缩对应的任务（可能随进程重启丢失）；旧任务不会再执行，可重新生成计划。"',
    '"本地内核已不再保留上次运行中的摘要任务；它可能随进程重启丢失，无法恢复。可基于当前会话重新生成计划。"',
    "export interface StartAttemptLike {",
    "sourceDigest: string;",
    "throughTurnId: string;",
    "priorJobId?: string;",
    "export function unresolvedStartPatch(job: { status: string }, attempt: StartAttemptLike | undefined): MissingJobPatch | null {",
    'if (!attempt || job.status === "running") return null;',
    '"上次开始压缩的回执未知，内核也没有保留它对应的任务；旧任务不会再执行，可重新生成计划。"',
    "export const LIFECYCLE_RELEASE_FAILURES = 3;",
    "export interface LifecycleReleasePatch {",
    "lifecycleActive: null;",
    "lifecycleReleased: true;",
    "export function lifecycleReleasePatch(failures: number): LifecycleReleasePatch | null {",
    "if (!Number.isFinite(failures) || failures < LIFECYCLE_RELEASE_FAILURES) return null;",
    "lifecycleActive: null,",
    "lifecycleReleased: true,",
    '"持续无法核对摘要任务的占用状态；已解除界面锁，内核仍会拒绝并发压缩。可稍后刷新预算或重新打开面板。"',
    "export function terminalDetailPatch(state: DisconnectState): MissingJobPatch {",
    '"内核报告摘要任务已结束，但详情无法识别；已停止跟踪并解除界面锁，可重新生成计划。"',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  settleReadFlight, disconnectPatch, missingJobPatch, unresolvedStartPatch,
  lifecycleReleasePatch, terminalDetailPatch,
} = await import(pathToFileURL(process.argv[1]).href);
const state = over => ({ error: "原错误", ...over });
const running = { jobId: "job-1", status: "running" };
const terminal = { jobId: "job-2", status: "completed" };
const attempt = { sourceDigest: "a".repeat(64), throughTurnId: "t-1" };
const f1 = { v: 1 };
const f2 = { v: 2 };
const f3 = { v: 1 };
const f4 = { v: 1 };
const settle = (flights, pending, id, flight) => {
  const map = new Map(flights);
  const set = new Set(pending);
  const result = settleReadFlight(map, set, id, flight);
  return [result, [...map.keys()], [...set]];
};
const result = {
  flights: [
    settle([["s1", f1], ["s2", f2]], ["s1", "s2"], "s1", f1),
    settle([["s1", f2]], [], "s1", f2),
    settle([["s1", "old"]], ["s1"], "s1", "new"),
    settle([], ["s1", "s2"], "s1", "old"),
    settle([["s1", f3]], ["s1"], "s1", f4),
    settle([["s2", "keep"]], ["s2"], "s1", "new"),
  ],
  disconnect: [
    disconnectPatch(state()),
    disconnectPatch(state({ unknownStart: "unknown", job: running })),
    disconnectPatch(state({ job: running })),
    disconnectPatch(state({ job: terminal })),
    disconnectPatch(state({ unknownStart: 1, job: terminal, lifecycleReleased: true })),
    disconnectPatch(state({ error: "" })),
  ],
  missing: [
    missingJobPatch(state()),
    missingJobPatch(state({ job: running })),
    missingJobPatch(state({ unknownStart: true, job: running })),
    missingJobPatch(state({ unknownStart: true })),
    missingJobPatch(state({ job: terminal, lifecycleReleased: true })),
    missingJobPatch(state({ error: "自定义" })),
  ],
  start: [
    unresolvedStartPatch({ status: "running" }, attempt),
    unresolvedStartPatch({ status: "completed" }, undefined),
    unresolvedStartPatch({ status: "completed" }, attempt),
    unresolvedStartPatch({ status: "error" }, { ...attempt, priorJobId: "job-0" }),
    unresolvedStartPatch({ status: "interrupted" }, attempt),
  ],
  lifecycle: [0, 1, 2, 3, 4, Number.NaN, Number.POSITIVE_INFINITY, -1, 2.5]
    .map(lifecycleReleasePatch),
  terminal: [
    terminalDetailPatch(state()),
    terminalDetailPatch(state({ job: running })),
    terminalDetailPatch(state({ unknownStart: true, job: terminal, lifecycleReleased: true })),
    terminalDetailPatch(state({ error: "自定义" })),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

DISCONNECT_BASE = {
    "reading": False, "planning": False, "starting": False, "cancelInFlight": False,
    "turnActive": False, "lifecycleReleased": False, "error": "原错误",
}
MISSING_BASE = {
    "starting": False, "discoveryStopped": False, "lifecycleReleased": False,
}
LIFECYCLE_PATCH = {
    "lifecycleActive": None,
    "lifecycleReleased": True,
    "error": "持续无法核对摘要任务的占用状态；已解除界面锁，内核仍会拒绝并发压缩。可稍后刷新预算或重新打开面板。",
}
TERMINAL_ERROR = "内核报告摘要任务已结束，但详情无法识别；已停止跟踪并解除界面锁，可重新生成计划。"

EXPECTED_FLIGHTS = (
    [True, ["s2"], ["s2"]],
    [False, [], []],
    [False, ["s1"], ["s1"]],
    [False, [], ["s1", "s2"]],
    [False, ["s1"], ["s1"]],
    [False, ["s2"], ["s2"]],
)
EXPECTED_DISCONNECT = (
    DISCONNECT_BASE,
    {**DISCONNECT_BASE, "error": "开始压缩的回执未知。重连后只核对原任务，不会重复开始。"},
    {**DISCONNECT_BASE, "error": "连接已断开，摘要任务状态待核对。"},
    DISCONNECT_BASE,
    {**DISCONNECT_BASE, "error": "开始压缩的回执未知。重连后只核对原任务，不会重复开始。"},
    {**DISCONNECT_BASE, "error": ""},
)
EXPECTED_MISSING = (
    {**MISSING_BASE, "error": "原错误"},
    {**MISSING_BASE, "unavailableJob": "job-1", "error": "本地内核已不再保留上次运行中的摘要任务；它可能随进程重启丢失，无法恢复。可基于当前会话重新生成计划。"},
    {**MISSING_BASE, "unavailableJob": "job-1", "error": "本机内核没有保留上次开始压缩对应的任务（可能随进程重启丢失）；旧任务不会再执行，可重新生成计划。"},
    {**MISSING_BASE, "error": "本机内核没有保留上次开始压缩对应的任务（可能随进程重启丢失）；旧任务不会再执行，可重新生成计划。"},
    {**MISSING_BASE, "error": "原错误"},
    {**MISSING_BASE, "error": "自定义"},
)
START_PATCH = {
    "starting": False,
    "discoveryStopped": False,
    "error": "上次开始压缩的回执未知，内核也没有保留它对应的任务；旧任务不会再执行，可重新生成计划。",
}
EXPECTED_START = (None, None, START_PATCH, START_PATCH, START_PATCH)
EXPECTED_LIFECYCLE = (None, None, None, LIFECYCLE_PATCH, LIFECYCLE_PATCH, None, None, None, None)
EXPECTED_TERMINAL = (
    {**MISSING_BASE, "error": TERMINAL_ERROR},
    {**MISSING_BASE, "unavailableJob": "job-1", "error": TERMINAL_ERROR},
    {**MISSING_BASE, "error": TERMINAL_ERROR},
    {**MISSING_BASE, "error": TERMINAL_ERROR},
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 摘要面板收敛试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 摘要面板收敛试算失败，请核对 Node.js 24+ 与 contextPanelState.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的摘要面板收敛结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回摘要面板收敛矩阵")
    for key in ("flights", "disconnect", "missing", "start", "lifecycle", "terminal"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"摘要面板收敛{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"摘要面板收敛{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["flights"], EXPECTED_FLIGHTS, "读取航班")
    checked += _compare(payload["disconnect"], EXPECTED_DISCONNECT, "断连收敛")
    checked += _compare(payload["missing"], EXPECTED_MISSING, "任务缺失")
    checked += _compare(payload["start"], EXPECTED_START, "开始回执")
    checked += _compare(payload["lifecycle"], EXPECTED_LIFECYCLE, "占用解锁")
    checked += _compare(payload["terminal"], EXPECTED_TERMINAL, "终态详情")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_panel_state.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_panel_state.py")
    if "共 54 项结构、36 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_panel_state.py 检查 54 项结构、36 项行为")
    return 2


def check_context_panel_state() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_panel_state()
    except (OSError, ValueError) as error:
        print(f"摘要面板收敛规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"摘要面板收敛规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
