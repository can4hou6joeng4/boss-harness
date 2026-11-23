#!/usr/bin/env python3
"""核对推理设置的操作提示与读取回执校验。

`reasoningControl.ts` 先判断操作目标：断连与无会话都要给出可见原因，不能静默
丢掉点击；再按白名单归一化 `thread/reasoning/read` 回执，`supported` 与
`summaryActive` 必须是真正的布尔值，可空档位只允许 `null` 或字符串，档位数组
只允许字符串。这里用 Node 直接加载真实模块核对这两组规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/reasoningControl.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'export type ReasoningAction = "读取" | "保存";',
    '| { ok: true; threadId: string }',
    "| { ok: false; notice: string };",
    'export function reasoningTarget(action: ReasoningAction, threadId: string | null, connected: boolean): ReasoningTarget {',
    'if (!connected) return { ok: false, notice: `无法${action}会话推理设置：本地内核未连接。恢复连接后再试。` };',
    'if (!threadId) return { ok: false, notice: `无法${action}会话推理设置：当前没有可操作的会话。` };',
    "return { ok: true, threadId };",
    'export function reasoningReadOf(value: unknown, expectedThreadId: string): ThreadReasoningReadResponse | null {',
    "if (!value || typeof value !== \"object\" || Array.isArray(value)) return null;",
    "if (raw.threadId !== expectedThreadId || typeof raw.model !== \"string\") return null;",
    'if (raw.effort !== null && typeof raw.effort !== "string") return null;',
    'if (raw.configuredEffort !== null && typeof raw.configuredEffort !== "string") return null;',
    'if (typeof raw.supported !== "boolean" || typeof raw.summaryActive !== "boolean") return null;',
    'if (!Array.isArray(raw.availableEfforts) || raw.availableEfforts.some(effort => typeof effort !== "string")) return null;',
    'if (typeof raw.capabilitySource !== "string" || typeof raw.capabilityIsEstimate !== "boolean") return null;',
    "threadId: expectedThreadId,",
    "model: raw.model,",
    "effort: raw.effort,",
    "configuredEffort: raw.configuredEffort,",
    "supported: raw.supported,",
    "summaryActive: raw.summaryActive,",
    "availableEfforts: raw.availableEfforts as string[],",
    "capabilitySource: raw.capabilitySource,",
    "capabilityIsEstimate: raw.capabilityIsEstimate,",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { reasoningTarget, reasoningReadOf } = await import(pathToFileURL(process.argv[1]).href);
const base = () => ({
  threadId: "t-1", model: "model-a", effort: null, configuredEffort: "medium",
  supported: true, summaryActive: false, availableEfforts: ["low", "medium"],
  capabilitySource: "catalog", capabilityIsEstimate: false,
});
const result = {
  targets: [
    reasoningTarget("读取", null, false),
    reasoningTarget("保存", "t-1", false),
    reasoningTarget("读取", null, true),
    reasoningTarget("保存", "", true),
    reasoningTarget("读取", "t-1", true),
    reasoningTarget("保存", "t-2", true),
  ],
  reads: [
    reasoningReadOf(base(), "t-1"),
    reasoningReadOf(null, "t-1"),
    reasoningReadOf([], "t-1"),
    reasoningReadOf(base(), "t-2"),
    reasoningReadOf({ ...base(), model: undefined }, "t-1"),
    reasoningReadOf({ ...base(), model: 42 }, "t-1"),
    reasoningReadOf({ ...base(), effort: "low" }, "t-1"),
    reasoningReadOf({ ...base(), effort: undefined }, "t-1"),
    reasoningReadOf({ ...base(), configuredEffort: 42 }, "t-1"),
    reasoningReadOf({ ...base(), supported: "true" }, "t-1"),
    reasoningReadOf({ ...base(), summaryActive: "true" }, "t-1"),
    reasoningReadOf({ ...base(), availableEfforts: undefined }, "t-1"),
    reasoningReadOf({ ...base(), availableEfforts: "low" }, "t-1"),
    reasoningReadOf({ ...base(), availableEfforts: ["low", 42] }, "t-1"),
    reasoningReadOf({ ...base(), capabilitySource: undefined }, "t-1"),
    reasoningReadOf({ ...base(), capabilityIsEstimate: "false" }, "t-1"),
    reasoningReadOf({ ...base(), extra: "ignored" }, "t-1"),
    reasoningReadOf({ ...base(), effort: null, configuredEffort: null }, "t-1"),
    reasoningReadOf({ ...base(), availableEfforts: [] }, "t-1"),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

BASE_READ = {
    "threadId": "t-1", "model": "model-a", "effort": None, "configuredEffort": "medium",
    "supported": True, "summaryActive": False, "availableEfforts": ["low", "medium"],
    "capabilitySource": "catalog", "capabilityIsEstimate": False,
}
EXPECTED_TARGETS = (
    {"ok": False, "notice": "无法读取会话推理设置：本地内核未连接。恢复连接后再试。"},
    {"ok": False, "notice": "无法保存会话推理设置：本地内核未连接。恢复连接后再试。"},
    {"ok": False, "notice": "无法读取会话推理设置：当前没有可操作的会话。"},
    {"ok": False, "notice": "无法保存会话推理设置：当前没有可操作的会话。"},
    {"ok": True, "threadId": "t-1"},
    {"ok": True, "threadId": "t-2"},
)
EXPECTED_READS = (
    BASE_READ,
    None, None, None, None, None,
    {**BASE_READ, "effort": "low"},
    None, None, None, None, None, None, None, None, None,
    BASE_READ,
    {**BASE_READ, "configuredEffort": None},
    {**BASE_READ, "availableEfforts": []},
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
        raise ValueError("Node 推理设置试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 推理设置试算失败，请核对 Node.js 24+ 与 reasoningControl.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的推理设置结果") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("targets"), list) or not isinstance(payload.get("reads"), list):
        raise ValueError("Node 未返回推理设置矩阵")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"推理设置{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"推理设置{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["targets"], EXPECTED_TARGETS, "操作目标")
    checked += _compare(payload["reads"], EXPECTED_READS, "回执校验")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_reasoning_control.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_reasoning_control.py")
    if "共 24 项结构、25 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_reasoning_control.py 检查 24 项结构、25 项行为")
    return 2


def check_reasoning_control() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_reasoning_control()
    except (OSError, ValueError) as error:
        print(f"推理设置规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"推理设置规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
