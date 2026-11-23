#!/usr/bin/env python3
"""核对停止失败的文案判定。

`stopFailure.ts` 区分「内核明确拒绝」与「停止请求未确认」两类失败：前者表示没有
取消任何回合，后者只表示结果未知；两类文案互斥，组合重新核对失败时还要去掉过渡语
并保留主因。桥接依赖在临时目录以固定桩替代，由 Node 直接加载真实模块执行用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/stopFailure.ts"
DEPENDENCY = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";',
    "export function stopFailureNotice(error: unknown): string {",
    "return isHarnessRpcRejection(error)",
    'export const stopMissingNotice = "未找到可停止的任务，正在重新读取会话状态。";',
    "export function stopFailureRecheckNotice(error: unknown, verificationFailure: string): string {",
    "const primary = isHarnessRpcRejection(error)",
    "export function stopMissingRecheckNotice(verificationFailure: string): string {",
)

DEPENDENCY_FRAGMENTS = (
    "export function isHarnessRpcRejection(error: unknown): boolean {",
    "export function harnessErrorText(error: unknown): string {",
)

STUB = """\
export function isHarnessRpcRejection(error: unknown): boolean {
  return Boolean(error && typeof error === "object" && (error as { rpcError?: unknown }).rpcError === true);
}

export function harnessErrorText(error: unknown): string {
  const value = error && typeof error === "object"
    ? error as { rpcError?: unknown; code?: unknown; message?: unknown; data?: unknown } : null;
  const data = value?.data && typeof value.data === "object" ? value.data as Record<string, unknown> : null;
  const message = typeof value?.message === "string" && value.message.trim()
    ? value.message.trim() : "无法读取本地内核响应";
  if (value?.rpcError === true && typeof value.code === "number") {
    return `${message}（内核 ${value.code}${typeof data?.code === "string" ? ` / ${data.code}` : ""}）`;
  }
  return message;
}
"""

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const m = await import(pathToFileURL(process.argv[1]).href);
const rejection = { rpcError: true, message: "回合已结束" };
const rejectionCoded = { rpcError: true, code: 409, message: "回合已结束", data: { code: "TURN_NOT_FOUND" } };
const plain = { message: "socket closed" };
const recheck = "读取失败：历史读取失败。";
const rejectionNotice = m.stopFailureNotice(rejection);
const plainNotice = m.stopFailureNotice(plain);
const rejectionRecheck = m.stopFailureRecheckNotice(rejection, recheck);
const plainRecheck = m.stopFailureRecheckNotice(plain, recheck);
const cases = [
  rejectionNotice === "停止请求未被内核受理：回合已结束。本次没有中断任何回合，正在重新读取会话状态。",
  m.stopFailureNotice(rejectionCoded) === "停止请求未被内核受理：回合已结束（内核 409 / TURN_NOT_FOUND）。本次没有中断任何回合，正在重新读取会话状态。",
  plainNotice === "停止请求未确认：socket closed。正在重新读取会话状态；不会自动重复停止。",
  m.stopFailureNotice(undefined) === "停止请求未确认：无法读取本地内核响应。正在重新读取会话状态；不会自动重复停止。",
  m.stopFailureNotice({ code: 409, message: "x" }) === "停止请求未确认：x。正在重新读取会话状态；不会自动重复停止。",
  rejectionNotice.includes("未被内核受理") && !rejectionNotice.includes("不会自动重复停止"),
  plainNotice.includes("未确认") && !plainNotice.includes("未被内核受理"),
  m.stopMissingNotice === "未找到可停止的任务，正在重新读取会话状态。",
  rejectionRecheck === "停止请求未被内核受理：回合已结束。本次没有中断任何回合；读取失败：历史读取失败。",
  plainRecheck === "停止请求未确认：socket closed。不会自动重复停止；读取失败：历史读取失败。",
  !rejectionRecheck.includes("正在重新读取"),
  m.stopMissingRecheckNotice(recheck) === "未找到可停止的任务；读取失败：历史读取失败。",
];
process.stdout.write(JSON.stringify({ cases }));
"""

EXPECTED_CASES = (True,) * 12
LABELS = {"cases": "用例"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "harnessBridge.ts").write_text(STUB, encoding="utf-8")
        target = Path(directory) / "stopFailure.ts"
        target.write_text(
            _read(TARGET).replace('from "./harnessBridge"', 'from "./harnessBridge.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 停止失败文案试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 停止失败文案试算失败，请核对 Node.js 24+ 与 stopFailure.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的停止失败文案结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"停止失败文案{label}数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"停止失败文案{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_stop_failure.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_stop_failure.py")
    if "共 9 项结构、12 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_stop_failure.py 检查 9 项结构、12 项行为")
    return 2


def check_stop_failure() -> tuple[int, int]:
    structure = (_expect(FRAGMENTS, _read(TARGET), TARGET)
                 + _expect(DEPENDENCY_FRAGMENTS, _read(DEPENDENCY), DEPENDENCY))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_stop_failure()
    except (OSError, ValueError) as error:
        print(f"停止失败文案核对失败，{error}", file=sys.stderr)
        return 2
    print(f"停止失败文案一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
