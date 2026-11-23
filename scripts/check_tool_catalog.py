#!/usr/bin/env python3
"""核对工具目录条目与重名校验。

`toolCatalog.ts` 校验 `tool/list` 的条目，并检查同一清单内的工具名是否唯一。
这里静态核对模块契约，并用 Node 直接加载真实模块，覆盖对象形状、名称上限、
描述与布尔标记、输入模式浅拷贝、可选字节预算与执行模式、多余字段忽略及重名判定。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/toolCatalog.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ToolDescriptor } from "@boss-harness/protocol";',
    "const ID_LIMIT = 200;",
    "function text(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    " * 「技能与工具」页直接渲染 `name`、`description` 与 `readOnly`，并以 `name`",
    " * 抛错并落入应用级错误边界，缺名或重名让清单行共用 key、操作指错工具。",
    "export function toolDescriptorOf(value: unknown): ToolDescriptor | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "if (!text(raw.name, ID_LIMIT)) return null;",
    'if (typeof raw.description !== "string") return null;',
    'if (typeof raw.readOnly !== "boolean" || typeof raw.requiresApproval !== "boolean") return null;',
    'if (!raw.inputSchema || typeof raw.inputSchema !== "object" || Array.isArray(raw.inputSchema)) return null;',
    "if (!Number.isSafeInteger(raw.maxModelResultBytes) || (raw.maxModelResultBytes as number) < 0) return null;",
    'const executionMode = raw.executionMode === "sequential" || raw.executionMode === "parallel" ? raw.executionMode : undefined;',
    "if (raw.executionMode !== undefined && executionMode === undefined) return null;",
    "inputSchema: { ...(raw.inputSchema as Record<string, unknown>) },",
    "...(maxModelResultBytes !== undefined ? { maxModelResultBytes } : {}),",
    "...(executionMode ? { executionMode } : {}),",
    "/** 同一清单内的重复工具名会让 React key 冲突，行与权限标记无法区分。 */",
    "export function uniqueToolNames(items: { name: string }[]): boolean {",
    "return new Set(items.map(item => item.name)).size === items.length;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { toolDescriptorOf, uniqueToolNames } = await import(pathToFileURL(process.argv[1]).href);
const shape = descriptor => descriptor === null ? null : {
  name: descriptor.name,
  descriptionLength: descriptor.description.length,
  readOnly: descriptor.readOnly,
  requiresApproval: descriptor.requiresApproval,
  schemaKeys: Object.keys(descriptor.inputSchema),
  hasMax: "maxModelResultBytes" in descriptor,
  max: descriptor.maxModelResultBytes ?? null,
  executionMode: descriptor.executionMode ?? null,
  keys: Object.keys(descriptor).sort(),
};
const schema = { type: "object" };
const valid = { name: "boss_hr_greet", description: "打招呼", readOnly: false, requiresApproval: true, inputSchema: schema };
const copied = toolDescriptorOf(valid);
const attempt = value => shape(toolDescriptorOf(value));
const result = {
  descriptors: [
    attempt(null),
    attempt([]),
    attempt("tool"),
    attempt(valid),
    attempt({ ...valid, name: "" }),
    attempt({ ...valid, name: "x".repeat(200) }),
    attempt({ ...valid, name: "x".repeat(201) }),
    attempt({ ...valid, name: 42 }),
    attempt({ ...valid, description: 42 }),
    attempt({ ...valid, description: "" }),
    attempt({ ...valid, readOnly: undefined }),
    attempt({ ...valid, requiresApproval: "yes" }),
    attempt({ ...valid, inputSchema: undefined }),
    attempt({ ...valid, inputSchema: [] }),
    attempt({ ...valid, maxModelResultBytes: undefined }),
    attempt({ ...valid, maxModelResultBytes: 0 }),
    attempt({ ...valid, maxModelResultBytes: -1 }),
    attempt({ ...valid, maxModelResultBytes: 1.5 }),
    attempt({ ...valid, maxModelResultBytes: "10" }),
    attempt({ ...valid, executionMode: "sequential" }),
    attempt({ ...valid, executionMode: "parallel" }),
    attempt({ ...valid, executionMode: "batch" }),
    attempt({ ...valid, executionMode: undefined }),
    attempt({ ...valid, extra: true }),
  ],
  copy: [
    copied !== null && copied.inputSchema !== schema,
    copied !== null && copied.inputSchema !== schema && copied.inputSchema.type === "object",
  ],
  unique: [
    uniqueToolNames([]),
    uniqueToolNames([{ name: "a" }, { name: "b" }]),
    uniqueToolNames([{ name: "a" }, { name: "a" }]),
    uniqueToolNames([{ name: "a" }, { name: "b" }, { name: "a" }]),
    uniqueToolNames([{ name: "a" }, { name: " a " }]),
    uniqueToolNames([{ name: "" }, { name: "" }]),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

BASE = {
    "name": "boss_hr_greet", "descriptionLength": 3, "readOnly": False, "requiresApproval": True,
    "schemaKeys": ["type"], "hasMax": False, "max": None, "executionMode": None,
    "keys": ["description", "inputSchema", "name", "readOnly", "requiresApproval"],
}


def _base(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


EXPECTED_DESCRIPTORS = (
    None,
    None,
    None,
    _base(),
    None,
    _base(name="x" * 200),
    None,
    None,
    None,
    _base(descriptionLength=0),
    None,
    None,
    None,
    None,
    _base(),
    _base(hasMax=True, max=0, keys=["description", "inputSchema", "maxModelResultBytes", "name", "readOnly", "requiresApproval"]),
    None,
    None,
    None,
    _base(executionMode="sequential", keys=["description", "executionMode", "inputSchema", "name", "readOnly", "requiresApproval"]),
    _base(executionMode="parallel", keys=["description", "executionMode", "inputSchema", "name", "readOnly", "requiresApproval"]),
    None,
    _base(),
    _base(),
)
EXPECTED_COPY = (True, True)
EXPECTED_UNIQUE = (True, True, False, False, True, False)
LABELS = {"descriptors": "条目", "copy": "模式副本", "unique": "重名"}


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
        raise ValueError("Node 工具目录试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 工具目录试算失败，请核对 Node.js 24+ 与 toolCatalog.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的工具目录结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"工具目录{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"工具目录{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["descriptors"], EXPECTED_DESCRIPTORS, LABELS["descriptors"])
            + _compare(payload["copy"], EXPECTED_COPY, LABELS["copy"])
            + _compare(payload["unique"], EXPECTED_UNIQUE, LABELS["unique"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_tool_catalog.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_tool_catalog.py")
    if "共 21 项结构、32 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_tool_catalog.py 检查 21 项结构、32 项行为")
    return 2


def check_tool_catalog() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_tool_catalog()
    except (OSError, ValueError) as error:
        print(f"工具目录规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具目录规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
