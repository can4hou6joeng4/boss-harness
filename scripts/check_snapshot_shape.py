#!/usr/bin/env python3
"""核对会话恢复快照的身份与线路字段校验。

`snapshotShape.ts` 在恢复前挡住不属于当前会话的回执、非字符串或超长的线路字段、
格式错误的快照标识与缺失条目数组；`threadSnapshotOf` 只在校验通过后把值收窄为协议
类型。这里用 Node 直接加载真实模块核对每条拒绝分支与成功收窄。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/snapshotShape.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "const SNAPSHOT_ID_PATTERN = /^[a-f0-9]{32}$/;",
    "const ROUTE_TEXT_LIMIT = 200;",
    "export function assertSnapshotRouteFields(thread: unknown): void {",
    'if (!thread || typeof thread !== "object" || Array.isArray(thread)) throw new Error("会话快照响应无效");',
    'for (const key of ["provider", "model"]) {',
    "const field = raw[key];",
    "if (field !== undefined && field !== null",
    '&& (typeof field !== "string" || field.length > ROUTE_TEXT_LIMIT)) {',
    'throw new Error("会话快照线路字段无效");',
    "export function assertThreadSnapshot(value: unknown, threadId: string): void {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("会话快照响应无效");',
    "const thread = snapshot.thread;",
    "if (!thread || typeof thread !== \"object\" || Array.isArray(thread)",
    '|| (thread as Record<string, unknown>).id !== threadId) throw new Error("会话快照响应无效");',
    "assertSnapshotRouteFields(thread);",
    "if (snapshot.snapshotId !== undefined",
    '&& (typeof snapshot.snapshotId !== "string" || !SNAPSHOT_ID_PATTERN.test(snapshot.snapshotId))) {',
    'throw new Error("会话快照标识无效");',
    'if (!Array.isArray(snapshot.items)) throw new Error("会话快照条目无效");',
    "export function threadSnapshotOf(value: unknown, threadId: string): ThreadReadResponse {",
    "assertThreadSnapshot(value, threadId);",
    "return value as ThreadReadResponse;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { assertSnapshotRouteFields, assertThreadSnapshot, threadSnapshotOf } =
  await import(pathToFileURL(process.argv[1]).href);
const capture = action => {
  try { action(); return "ok"; }
  catch (error) { return "err:" + (error?.message ?? String(error)); }
};
const snapshot = (over = {}) => ({
  thread: { id: "th-1" }, items: [], ...over,
});
const route = (over = {}) => ({ id: "th-1", ...over });
const result = {
  routes: [
    capture(() => assertSnapshotRouteFields(null)),
    capture(() => assertSnapshotRouteFields([])),
    capture(() => assertSnapshotRouteFields({})),
    capture(() => assertSnapshotRouteFields(route({ provider: "openai", model: "m-1" }))),
    capture(() => assertSnapshotRouteFields(route({ provider: null, model: null }))),
    capture(() => assertSnapshotRouteFields(route({ provider: undefined, model: "m-1" }))),
    capture(() => assertSnapshotRouteFields(route({ provider: 42 }))),
    capture(() => assertSnapshotRouteFields(route({ model: {} }))),
    capture(() => assertSnapshotRouteFields(route({ provider: "p".repeat(201) }))),
    capture(() => assertSnapshotRouteFields(route({ model: "m".repeat(200) }))),
  ],
  snapshots: [
    capture(() => assertThreadSnapshot(null, "th-1")),
    capture(() => assertThreadSnapshot([], "th-1")),
    capture(() => assertThreadSnapshot({}, "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ thread: null }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ thread: { id: "th-2" } }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot(), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ items: [1] }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ snapshotId: "a".repeat(32) }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ snapshotId: "A".repeat(32) }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ snapshotId: "a".repeat(31) }), "th-1")),
    capture(() => assertThreadSnapshot(snapshot({ thread: route({ provider: 42 }) }), "th-1")),
  ],
  narrowed: [
    (() => { const value = snapshot(); return threadSnapshotOf(value, "th-1") === value ? "same" : "other"; })(),
    capture(() => { threadSnapshotOf(snapshot({ thread: { id: "th-2" } }), "th-1"); }),
    capture(() => { threadSnapshotOf(snapshot({ items: undefined }), "th-1"); }),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

INVALID_SNAPSHOT = "err:会话快照响应无效"
INVALID_ROUTE = "err:会话快照线路字段无效"
EXPECTED_ROUTES = (
    INVALID_SNAPSHOT, INVALID_SNAPSHOT, "ok", "ok", "ok", "ok",
    INVALID_ROUTE, INVALID_ROUTE, INVALID_ROUTE, "ok",
)
EXPECTED_SNAPSHOTS = (
    INVALID_SNAPSHOT, INVALID_SNAPSHOT, INVALID_SNAPSHOT, INVALID_SNAPSHOT, INVALID_SNAPSHOT,
    "ok", "ok", "ok", "err:会话快照标识无效", "err:会话快照标识无效", INVALID_ROUTE,
)
EXPECTED_NARROWED = ("same", INVALID_SNAPSHOT, "err:会话快照条目无效")


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
        raise ValueError("Node 会话快照试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 会话快照试算失败，请核对 Node.js 24+ 与 snapshotShape.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的会话快照结果") from None
    for key in ("routes", "snapshots", "narrowed"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"会话快照{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"会话快照{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["routes"], EXPECTED_ROUTES, "线路字段")
    checked += _compare(payload["snapshots"], EXPECTED_SNAPSHOTS, "快照形状")
    checked += _compare(payload["narrowed"], EXPECTED_NARROWED, "类型收窄")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_snapshot_shape.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_snapshot_shape.py")
    if "共 22 项结构、24 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_snapshot_shape.py 检查 22 项结构、24 项行为")
    return 2


def check_snapshot_shape() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_snapshot_shape()
    except (OSError, ValueError) as error:
        print(f"会话快照规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话快照规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
