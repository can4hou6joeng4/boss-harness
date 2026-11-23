#!/usr/bin/env python3
"""核对上下文构成拆分规则。

`contextBreakdown.ts` 把 `context/read.breakdown` 拆成可展示的构成项：存在历史用量
基线时只展示基线与新增消息，否则要求四段旧明细齐全。这里静态核对模块契约，并用
Node 直接加载真实模块覆盖字段缺失、类型非法、负数、零总和与额外字段等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/contextBreakdown.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 把 `context/read.breakdown` 拆成可展示的构成项。",
    "export interface ContextBreakdownPart {",
    "export interface ContextBreakdown {",
    "const count = (value: unknown): number | undefined =>",
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : undefined;',
    "export function contextBreakdown(value: unknown): ContextBreakdown | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const messages = count(fields.messages);",
    "const baseline = count(fields.usageBaseline);",
    "if (baseline !== undefined) {",
    "if (messages === undefined) return null;",
    'key: "usageBaseline", label: "历史用量基线", tokens: baseline',
    'key: "messages", label: "新增消息", tokens: messages',
    "const system = count(fields.system), tools = count(fields.tools), options = count(fields.options);",
    "if (system === undefined || messages === undefined || tools === undefined || options === undefined) return null;",
    'key: "system", label: "系统提示", tokens: system',
    'key: "messages", label: "消息历史", tokens: messages',
    'key: "tools", label: "工具定义", tokens: tools',
    'key: "options", label: "选项", tokens: options',
    "const total = parts.reduce((sum, part) => sum + part.tokens, 0);",
    "return total > 0 ? { calibrated: baseline !== undefined, parts, total } : null;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { contextBreakdown } = await import(pathToFileURL(process.argv[1]).href);
const shape = value => value === null ? null : {
  calibrated: value.calibrated,
  total: value.total,
  parts: value.parts.map(part => [part.key, part.label, part.tokens]),
};
const result = {
  cases: [
    shape(contextBreakdown(null)),
    shape(contextBreakdown([])),
    shape(contextBreakdown(Object.assign([], { usageBaseline: 1, messages: 2 }))),
    shape(contextBreakdown("breakdown")),
    shape(contextBreakdown({})),
    shape(contextBreakdown({ usageBaseline: 100, messages: 50 })),
    shape(contextBreakdown({ usageBaseline: 0, messages: 5 })),
    shape(contextBreakdown({ usageBaseline: 100 })),
    shape(contextBreakdown({ usageBaseline: 100, messages: -1 })),
    shape(contextBreakdown({ usageBaseline: 100, messages: 1.5 })),
    shape(contextBreakdown({ usageBaseline: 100, messages: 0 })),
    shape(contextBreakdown({ usageBaseline: 100, messages: 0, system: 7, tools: 9 })),
    shape(contextBreakdown({ system: 10, messages: 20, tools: 30, options: 40 })),
    shape(contextBreakdown({ system: 0, messages: 0, tools: 0, options: 0 })),
    shape(contextBreakdown({ system: 0, messages: 20, tools: 0, options: 1 })),
    shape(contextBreakdown({ system: 10, messages: 20, tools: 30 })),
    shape(contextBreakdown({ system: 10, messages: 20, tools: -1, options: 40 })),
    shape(contextBreakdown({ system: 1.5, messages: 20, tools: 30, options: 40 })),
    shape(contextBreakdown({ system: 10, messages: 20, tools: 30, options: 40, extra: true })),
    shape(contextBreakdown({ usageBaseline: "100", system: 1, messages: 2, tools: 3, options: 4 })),
    shape(contextBreakdown({ usageBaseline: null, system: 1, messages: 2, tools: 3, options: 4 })),
    shape(contextBreakdown({ usageBaseline: 0, messages: 0 })),
  ],
};
process.stdout.write(JSON.stringify(result));
"""


def _part(key, label, tokens):
    return [key, label, tokens]


BASELINE = {
    "calibrated": True,
    "total": 150,
    "parts": [_part("usageBaseline", "历史用量基线", 100), _part("messages", "新增消息", 50)],
}
UNITS = [_part("system", "系统提示", 10), _part("messages", "消息历史", 20),
         _part("tools", "工具定义", 30), _part("options", "选项", 40)]
EXPECTED = (
    None,
    None,
    None,
    None,
    None,
    BASELINE,
    {"calibrated": True, "total": 5, "parts": [_part("usageBaseline", "历史用量基线", 0), _part("messages", "新增消息", 5)]},
    None,
    None,
    None,
    {"calibrated": True, "total": 100, "parts": [_part("usageBaseline", "历史用量基线", 100), _part("messages", "新增消息", 0)]},
    {"calibrated": True, "total": 100, "parts": [_part("usageBaseline", "历史用量基线", 100), _part("messages", "新增消息", 0)]},
    {"calibrated": False, "total": 100, "parts": UNITS},
    None,
    {"calibrated": False, "total": 21, "parts": [_part("system", "系统提示", 0), _part("messages", "消息历史", 20), _part("tools", "工具定义", 0), _part("options", "选项", 1)]},
    None,
    None,
    None,
    {"calibrated": False, "total": 100, "parts": UNITS},
    {"calibrated": False, "total": 10, "parts": [_part("system", "系统提示", 1), _part("messages", "消息历史", 2), _part("tools", "工具定义", 3), _part("options", "选项", 4)]},
    {"calibrated": False, "total": 10, "parts": [_part("system", "系统提示", 1), _part("messages", "消息历史", 2), _part("tools", "工具定义", 3), _part("options", "选项", 4)]},
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 上下文构成试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 上下文构成试算失败，请核对 Node.js 24+ 与 contextBreakdown.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的上下文构成结果") from None
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Node 未返回 cases 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"上下文构成{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"上下文构成{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED, "拆分")


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_breakdown.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_breakdown.py")
    if "共 21 项结构、22 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_breakdown.py 检查 21 项结构、21 项行为")
    return 2


def check_context_breakdown() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_breakdown()
    except (OSError, ValueError) as error:
        print(f"上下文构成规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文构成规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
