#!/usr/bin/env python3
"""核对工作区说明回执的状态、字节数与保存结果判定。

`workspaceInstructions.ts` 被技能与工具页和上下文面板编辑器共用：状态只允许四种
枚举，字节数允许 `null` 但否则必须是非负安全整数，保存回执只接受 `loaded` /
`empty` 并携带正整数上限与非空路径。这里用 Node 直接加载真实模块核对这些边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/workspaceInstructions.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'const STATUSES: ReadonlySet<string> = new Set(["loaded", "empty", "too_large", "unreadable"]);',
    "export function workspaceInstructionStatusOf(value: unknown): WorkspaceInstructionsState[\"status\"] | null {",
    "return typeof value === \"string\" && STATUSES.has(value)",
    "? value as WorkspaceInstructionsState[\"status\"] : null;",
    "export function workspaceInstructionBytesOf(value: unknown): number | null | undefined {",
    "if (value === null) return null;",
    'if (typeof value === "number" && Number.isSafeInteger(value) && value >= 0) return value;',
    "return undefined;",
    "export function workspaceInstructionWriteOf(value: unknown): WorkspaceInstructionsWriteResponse | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const status = workspaceInstructionStatusOf(raw.status);",
    'if (status !== "loaded" && status !== "empty") return null;',
    "const bytes = workspaceInstructionBytesOf(raw.bytes);",
    "if (bytes === null || bytes === undefined) return null;",
    'if (typeof raw.limitBytes !== "number" || !Number.isSafeInteger(raw.limitBytes) || raw.limitBytes <= 0) return null;',
    'if (typeof raw.path !== "string" || !raw.path || raw.path.length > 4096) return null;',
    "return { path: raw.path, bytes, status, limitBytes: raw.limitBytes };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  workspaceInstructionStatusOf, workspaceInstructionBytesOf, workspaceInstructionWriteOf,
} = await import(pathToFileURL(process.argv[1]).href);
const write = over => workspaceInstructionWriteOf({
  path: "AGENTS.md", bytes: 12, status: "loaded", limitBytes: 32768, ...over,
});
const result = {
  statuses: ["loaded", "empty", "too_large", "unreadable", "RUNNING", "", null, 42, {}]
    .map(workspaceInstructionStatusOf),
  bytes: [
    0, 123, null, -1, 1.5, "12", undefined, Number.MAX_SAFE_INTEGER,
    Number.POSITIVE_INFINITY, Number.NaN,
  ].map(workspaceInstructionBytesOf),
  writes: [
    write({}),
    write({ status: "empty", bytes: 0 }),
    workspaceInstructionWriteOf(null),
    workspaceInstructionWriteOf([]),
    write({ status: "too_large" }),
    write({ status: undefined }),
    write({ bytes: null }),
    write({ bytes: undefined }),
    write({ bytes: -1 }),
    write({ limitBytes: 0 }),
    write({ limitBytes: -1 }),
    write({ limitBytes: 1.5 }),
    write({ limitBytes: "32768" }),
    write({ limitBytes: undefined }),
    write({ path: "" }),
    write({ path: "x".repeat(4097) }),
    write({ path: 42 }),
    write({ extra: "ignored" }),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_STATUSES = (
    "loaded", "empty", "too_large", "unreadable", None, None, None, None, None,
)
EXPECTED_BYTES = (
    0, 123, None, None, None, None, None, 9007199254740991, None, None,
)
LOADED = {"path": "AGENTS.md", "bytes": 12, "status": "loaded", "limitBytes": 32768}
EXPECTED_WRITES = (
    LOADED,
    {"path": "AGENTS.md", "bytes": 0, "status": "empty", "limitBytes": 32768},
    None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    LOADED,
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
        raise ValueError("Node 工作区说明试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 工作区说明试算失败，请核对 Node.js 24+ 与 workspaceInstructions.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的工作区说明结果") from None
    for key in ("statuses", "bytes", "writes"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"工作区说明{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"工作区说明{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["statuses"], EXPECTED_STATUSES, "状态枚举")
    checked += _compare(payload["bytes"], EXPECTED_BYTES, "字节数")
    checked += _compare(payload["writes"], EXPECTED_WRITES, "保存回执")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_workspace_instruction_receipts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_workspace_instruction_receipts.py")
    if "共 17 项结构、37 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_workspace_instruction_receipts.py 检查 17 项结构、37 项行为")
    return 2


def check_workspace_instruction_receipts() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_workspace_instruction_receipts()
    except (OSError, ValueError) as error:
        print(f"工作区说明规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工作区说明规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
