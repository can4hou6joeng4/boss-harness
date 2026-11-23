#!/usr/bin/env python3
"""核对模型自动重试通知的归并与收敛规则。

`modelRetry.ts` 校验 retryStarted / retryEnded 载荷，合并为会话区观测状态，并在回合
收尾时收敛仍在等待的提示。这里静态核对模块契约，并用 Node 直接加载真实模块覆盖
字段上限、非法序号、文案归一化、结束原因、收尾收敛与倒计时等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/modelRetry.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ModelRetryEndedNotification, ModelRetryStartedNotification } from "@boss-harness/protocol";',
    " * 模型自动重试的会话区观测状态（仅展示；不参与重试判定、不触发任何请求）。",
    'export type ModelRetryPhase = "waiting" | "recovered" | "failed" | "aborted";',
    "const MAX_ATTEMPT = 100;",
    "const MAX_DELAY_MS = 3_600_000;",
    "const MAX_MESSAGE = 300;",
    "function boundedInteger(value: unknown, min: number, max: number): number | undefined {",
    "Number.isSafeInteger(value) && value >= min && value <= max ? value : undefined;",
    "function boundedText(value: unknown): string | undefined {",
    r'const text = value.replace(/\s+/g, " ").trim();',
    "const chars = Array.from(text);",
    'return chars.length > MAX_MESSAGE ? chars.slice(0, MAX_MESSAGE).join("") + "…" : text;',
    "function turnOf(value: unknown): string | undefined {",
    "export function reduceModelRetry(previous: ModelRetryStatus | undefined, method: string, raw: unknown, now: number): ModelRetryStatus | undefined {",
    'if (method === "model/retryStarted") {',
    "if (!threadId || attempt === undefined || maxAttempts === undefined || delayMs === undefined || attempt > maxAttempts) return previous;",
    'if (method === "model/retryEnded") {',
    'const phase: ModelRetryPhase = params.success ? "recovered" : params.reason === "aborted" ? "aborted" : "failed";',
    "export function settleModelRetryOnTurnEnd(previous: ModelRetryStatus | undefined, turnStatus: string | undefined, now: number): ModelRetryStatus | undefined {",
    'if (previous?.phase !== "waiting") return previous;',
    'return { ...previous, phase: "aborted", receivedAt: now, endedBeforeAttempt: true };',
    "export function retryRemainingSeconds(status: ModelRetryStatus, now: number): number {",
    "return Math.max(0, Math.ceil((status.receivedAt + status.delayMs - now) / 1000));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { reduceModelRetry, settleModelRetryOnTurnEnd, retryRemainingSeconds } = await import(pathToFileURL(process.argv[1]).href);
const summary = status => status === undefined ? null : {
  threadId: status.threadId,
  turnId: status.turnId ?? null,
  phase: status.phase,
  attempt: status.attempt,
  maxAttempts: status.maxAttempts ?? null,
  delayMs: status.delayMs ?? null,
  receivedAt: status.receivedAt,
  errorMessage: status.errorMessage ?? null,
  finalError: status.finalError ?? null,
  endedBeforeAttempt: status.endedBeforeAttempt === true,
};
const started = (extra = {}) => ({ threadId: "t1", attempt: 2, maxAttempts: 3, delayMs: 5000, ...extra });
const previous = { threadId: "t1", turnId: "turn-old", phase: "waiting", attempt: 2, maxAttempts: 4, delayMs: 1000, receivedAt: 500, errorMessage: "首轮超时" };
const normalized = reduceModelRetry(undefined, "model/retryStarted", started({ errorMessage: "  a  b  " }), 1000);
const truncated = reduceModelRetry(undefined, "model/retryStarted", started({ errorMessage: "🙂".repeat(301) }), 1000);
const result = {
  reduce: [
    summary(reduceModelRetry(undefined, "model/retryStarted", null, 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started(), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ attempt: 1 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ attempt: 101 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ maxAttempts: 1 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ delayMs: 0 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ delayMs: -1 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ delayMs: 3600001 }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ attempt: 2.5 }), 1000)),
    normalized?.errorMessage ?? null,
    truncated ? { length: Array.from(truncated.errorMessage ?? "").length, tail: (truncated.errorMessage ?? "").slice(-1) } : null,
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ turnId: "x".repeat(129) }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ turnId: "x".repeat(128) }), 1000)),
    summary(reduceModelRetry(undefined, "model/retryStarted", started({ attempt: 3, maxAttempts: 2 }), 1000)),
    summary(reduceModelRetry(previous, "model/retryEnded", { threadId: "t1", attempt: 2, success: true, finalError: "忽略" }, 2000)),
    summary(reduceModelRetry(previous, "model/retryEnded", { threadId: "t1", attempt: 2, success: false, reason: "aborted", finalError: "已停止" }, 2000)),
    summary(reduceModelRetry(previous, "model/retryEnded", { threadId: "t1", attempt: 2, success: false, reason: "timeout", finalError: "网络超时" }, 2000)),
    summary(reduceModelRetry(previous, "model/retryEnded", { threadId: "t1", attempt: 2, success: "yes" }, 2000)),
    summary(reduceModelRetry(previous, "model/retryEnded", { threadId: "t1", attempt: 0, success: false }, 2000)),
    summary(reduceModelRetry(previous, "model/unknown", started(), 2000)),
  ],
  settle: [
    summary(settleModelRetryOnTurnEnd(undefined, "completed", 1000)),
    summary(settleModelRetryOnTurnEnd({ ...previous, phase: "recovered" }, "completed", 1000)),
    summary(settleModelRetryOnTurnEnd({ ...previous, phase: "waiting" }, undefined, 1000)),
    summary(settleModelRetryOnTurnEnd({ ...previous, phase: "waiting" }, "interrupted", 1000)),
    summary(settleModelRetryOnTurnEnd({ ...previous, phase: "waiting" }, "failed", 1000)),
    summary(settleModelRetryOnTurnEnd({ ...previous, phase: "waiting" }, "completed", 1000)),
  ],
  remaining: [
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 0),
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 1000),
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 3500),
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 6000),
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 9000),
    retryRemainingSeconds({ ...previous, receivedAt: 1000, delayMs: 5000 }, 12000),
    retryRemainingSeconds({ ...previous, phase: "recovered", delayMs: 5000 }, 1000),
  ],
};
process.stdout.write(JSON.stringify(result));
"""


def _summary(thread_id, phase, attempt, received_at, *, turn_id=None, max_attempts=None,
             delay_ms=None, error_message=None, final_error=None, ended=False):
    return {
        "threadId": thread_id, "turnId": turn_id, "phase": phase, "attempt": attempt,
        "maxAttempts": max_attempts, "delayMs": delay_ms, "receivedAt": received_at,
        "errorMessage": error_message, "finalError": final_error,
        "endedBeforeAttempt": ended,
    }


STARTED = _summary("t1", "waiting", 2, 1000, max_attempts=3, delay_ms=5000)
PREVIOUS = _summary("t1", "waiting", 2, 500, turn_id="turn-old", max_attempts=4,
                    delay_ms=1000, error_message="首轮超时")

EXPECTED_REDUCE = (
    None,
    STARTED,
    None,
    None,
    None,
    _summary("t1", "waiting", 2, 1000, max_attempts=3, delay_ms=0),
    None,
    None,
    None,
    "a b",
    {"length": 301, "tail": "…"},
    _summary("t1", "waiting", 2, 1000, max_attempts=3, delay_ms=5000),
    _summary("t1", "waiting", 2, 1000, turn_id="x" * 128, max_attempts=3, delay_ms=5000),
    None,
    _summary("t1", "recovered", 2, 2000, turn_id="turn-old", max_attempts=4,
             error_message="首轮超时"),
    _summary("t1", "aborted", 2, 2000, turn_id="turn-old", max_attempts=4,
             error_message="首轮超时", final_error="已停止"),
    _summary("t1", "failed", 2, 2000, turn_id="turn-old", max_attempts=4,
             error_message="首轮超时", final_error="网络超时"),
    PREVIOUS,
    PREVIOUS,
    PREVIOUS,
)
EXPECTED_SETTLE = (
    None,
    _summary("t1", "recovered", 2, 500, turn_id="turn-old", max_attempts=4,
             delay_ms=1000, error_message="首轮超时"),
    _summary("t1", "waiting", 2, 500, turn_id="turn-old", max_attempts=4,
             delay_ms=1000, error_message="首轮超时"),
    _summary("t1", "aborted", 2, 1000, turn_id="turn-old", max_attempts=4,
             delay_ms=1000, error_message="首轮超时", ended=True),
    None,
    None,
)
EXPECTED_REMAINING = (6, 5, 3, 0, 0, 0, 0)
LABELS = {"reduce": "归并", "settle": "收尾", "remaining": "倒计时"}


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
        raise ValueError("Node 模型重试试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 模型重试试算失败，请核对 Node.js 24+ 与 modelRetry.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的模型重试结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"模型重试{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"模型重试{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["reduce"], EXPECTED_REDUCE, LABELS["reduce"])
            + _compare(payload["settle"], EXPECTED_SETTLE, LABELS["settle"])
            + _compare(payload["remaining"], EXPECTED_REMAINING, LABELS["remaining"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_model_retry.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_model_retry.py")
    if "共 23 项结构、33 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_model_retry.py 检查 23 项结构、33 项行为")
    return 2


def check_model_retry() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_model_retry()
    except (OSError, ValueError) as error:
        print(f"模型重试规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型重试规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
