#!/usr/bin/env python3
"""核对模型目录条目校验、菜单 key 去重与空态文案。

`modelCatalog.ts` 把 `model/list` 的线路条目收敛成菜单可直接使用的形状：`id` 与
`provider` 有长度上限，`configured` / `available` 必须是布尔，`capabilities` 出现
时上下文窗口与输出上限须为非负安全整数，`reasoningEfforts` 最多 16 项且逐项校验
并复制数组；重复 `provider:id` 由 `uniqueModelKeys` 拒绝；菜单空态按预览、目录
数量、匹配数量与 none 线路禁用分流，禁用说明只作为附注或顶替空目录文案。这里用
Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "apps/desktop/src/renderer/src/data/modelCatalog.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

CATALOG_FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const PROVIDER_LIMIT = 100;",
    "const SOURCE_LIMIT = 100;",
    "const MAX_EFFORTS = 16;",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    "if (value === undefined || value === null) return null;",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;',
    "if (!Number.isSafeInteger(raw.contextWindow) || (raw.contextWindow as number) < 0) return undefined;",
    "if (!Number.isSafeInteger(raw.maxOutputTokens) || (raw.maxOutputTokens as number) < 0) return undefined;",
    "if (!text(raw.capabilitySource, SOURCE_LIMIT)) return undefined;",
    'if (typeof raw.capacityIsEstimate !== "boolean") return undefined;',
    "if (!Array.isArray(raw.reasoningEfforts) || raw.reasoningEfforts.length > MAX_EFFORTS",
    "reasoningEfforts = [...raw.reasoningEfforts];",
    "export function modelDescriptorOf(value: unknown): ModelDescriptor | null {",
    "if (!text(raw.id, ID_LIMIT) || !text(raw.provider, PROVIDER_LIMIT)) return null;",
    'if (typeof raw.configured !== "boolean" || typeof raw.available !== "boolean") return null;',
    "const capabilities = capabilitiesOf(raw.capabilities);",
    "if (capabilities === undefined) return null;",
    "export function uniqueModelKeys(items: { provider: string; id: string }[]): boolean {",
    "return new Set(items.map(item => `${item.provider}:${item.id}`)).size === items.length;",
    'export const MODEL_CALLS_DISABLED_NOTE = "进程以 none 线路启动，不调用模型；需要模型时改用具体 provider 重新启动";',
    'const NO_MODEL_MATCH = "未找到匹配模型";',
    'const NO_MODEL_ROUTE = "没有可用的本机模型线路";',
    "const disabled = !input.preview && input.modelCallsDisabled;",
    'if (input.matchCount > 0) return { empty: "", note: disabled ? MODEL_CALLS_DISABLED_NOTE : "" };',
    'if (input.preview || input.modelCount > 0) return { empty: NO_MODEL_MATCH, note: disabled ? MODEL_CALLS_DISABLED_NOTE : "" };',
    'return { empty: disabled ? MODEL_CALLS_DISABLED_NOTE : NO_MODEL_ROUTE, note: "" };',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { modelDescriptorOf, uniqueModelKeys, modelMenuHints, MODEL_CALLS_DISABLED_NOTE } =
  await import(pathToFileURL(process.argv[1]).href);
const base = { id: "m", provider: "p", configured: true, available: true };
const goodCaps = { contextWindow: 1000, maxOutputTokens: 100, capabilitySource: "static", capacityIsEstimate: false };
const efforts = (count) => Array.from({ length: count }, (_, index) => `e${index}`);
const caps = (list) => ({ ...goodCaps, reasoningEfforts: list });
const results = {
  descriptor: [
    [null, [], "x", 42].map(modelDescriptorOf),
    (() => {
      const rows = [
        modelDescriptorOf({ ...base, id: "" }),
        modelDescriptorOf({ ...base, id: "x".repeat(201) }),
        modelDescriptorOf({ ...base, provider: "" }),
        modelDescriptorOf({ ...base, provider: "p".repeat(101) }),
        modelDescriptorOf({ ...base, id: "x".repeat(200), provider: "p".repeat(100) }),
      ];
      return [...rows.slice(0, 4).map(row => row === null), rows[4].id.length, rows[4].provider.length];
    })(),
    [
      modelDescriptorOf({ ...base, configured: "yes" }),
      modelDescriptorOf({ ...base, available: 1 }),
      modelDescriptorOf({ ...base, configured: false, available: false }),
    ].map(row => row === null),
    [
      modelDescriptorOf(base),
      modelDescriptorOf({ ...base, capabilities: null }),
    ].map(row => "capabilities" in row),
    [
      { ...goodCaps, contextWindow: -1 },
      { ...goodCaps, contextWindow: 1.5 },
      { ...goodCaps, contextWindow: "1000" },
      { ...goodCaps, maxOutputTokens: -1 },
      { ...goodCaps, maxOutputTokens: 0.5 },
      { ...goodCaps, capabilitySource: "" },
      { ...goodCaps, capabilitySource: "s".repeat(101) },
      { ...goodCaps, capacityIsEstimate: "no" },
      [goodCaps],
      "caps",
    ].map(value => modelDescriptorOf({ ...base, capabilities: value }) === null),
    (() => {
      const sixteen = modelDescriptorOf({ ...base, capabilities: caps(efforts(16)) });
      const seventeen = modelDescriptorOf({ ...base, capabilities: caps(efforts(17)) });
      const nonString = modelDescriptorOf({ ...base, capabilities: caps(["a", 1]) });
      const empty = modelDescriptorOf({ ...base, capabilities: caps([]) });
      return [sixteen.capabilities.reasoningEfforts.length, seventeen === null, nonString === null,
        Array.isArray(empty.capabilities.reasoningEfforts), empty.capabilities.reasoningEfforts.length];
    })(),
    (() => {
      const source = efforts(3);
      const descriptor = modelDescriptorOf({ ...base, capabilities: { ...goodCaps, reasoningEfforts: source } });
      source.push("late");
      return [descriptor.id, descriptor.provider, descriptor.configured, descriptor.available,
        descriptor.capabilities.contextWindow, descriptor.capabilities.maxOutputTokens,
        descriptor.capabilities.capabilitySource, descriptor.capabilities.capacityIsEstimate,
        descriptor.capabilities.reasoningEfforts];
    })(),
    (() => {
      const descriptor = modelDescriptorOf({ ...base, extra: 1, capabilities: { ...goodCaps, extra: 2 } });
      return [Object.keys(descriptor), Object.keys(descriptor.capabilities)];
    })(),
  ],
  keys: [
    [
      uniqueModelKeys([]),
      uniqueModelKeys([{ provider: "p", id: "m" }, { provider: "q", id: "m" }]),
      uniqueModelKeys([{ provider: "p", id: "m" }, { provider: "p", id: "m" }]),
      uniqueModelKeys([{ provider: "p", id: "m:n" }, { provider: "p:m", id: "n" }]),
    ],
  ],
  hints: (() => {
    const hints = (input) => modelMenuHints({ preview: false, modelCount: 0, matchCount: 0, modelCallsDisabled: false, ...input });
    return [
      hints({ modelCount: 3, matchCount: 2 }),
      hints({ modelCount: 3, matchCount: 2, modelCallsDisabled: true }),
      hints({ preview: true, matchCount: 2, modelCallsDisabled: true }),
      hints({ modelCount: 3, matchCount: 0 }),
      hints({ modelCount: 3, matchCount: 0, modelCallsDisabled: true }),
      hints({ modelCount: 0, matchCount: 0 }),
      hints({ modelCount: 0, matchCount: 0, modelCallsDisabled: true }),
      hints({ preview: true, matchCount: 0, modelCallsDisabled: true }),
    ];
  })(),
};
results.note = MODEL_CALLS_DISABLED_NOTE;
process.stdout.write(JSON.stringify(results));
"""

NOTE = "进程以 none 线路启动，不调用模型；需要模型时改用具体 provider 重新启动"
NO_MATCH = "未找到匹配模型"
NO_ROUTE = "没有可用的本机模型线路"

EXPECTED_DESCRIPTOR = (
    [None, None, None, None],
    [True, True, True, True, 200, 100],
    [True, True, False],
    [False, False],
    [True, True, True, True, True, True, True, True, True, True],
    [16, True, True, True, 0],
    ["m", "p", True, True, 1000, 100, "static", False, ["e0", "e1", "e2"]],
    [
        ["id", "provider", "configured", "available", "capabilities"],
        ["contextWindow", "maxOutputTokens", "capabilitySource", "capacityIsEstimate"],
    ],
)
EXPECTED_KEYS = ([True, True, False, False],)
EXPECTED_HINTS = (
    {"empty": "", "note": ""},
    {"empty": "", "note": NOTE},
    {"empty": "", "note": ""},
    {"empty": NO_MATCH, "note": ""},
    {"empty": NO_MATCH, "note": NOTE},
    {"empty": NO_ROUTE, "note": ""},
    {"empty": NOTE, "note": ""},
    {"empty": NO_MATCH, "note": ""},
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / CATALOG)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 模型目录试算失败，请核对 Node.js 24+ 与 modelCatalog.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的模型目录结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回模型目录矩阵")
    for key in ("descriptor", "keys", "hints"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    if payload.get("note") != NOTE:
        raise ValueError(f"MODEL_CALLS_DISABLED_NOTE 文案变化：{payload.get('note')!r}")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"模型目录{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"模型目录{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["descriptor"], EXPECTED_DESCRIPTOR, "条目")
    checked += _compare(payload["keys"], EXPECTED_KEYS, "去重")
    checked += _compare(payload["hints"], EXPECTED_HINTS, "空态")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_model_catalog.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_model_catalog.py")
    if "共 27 项结构、17 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_model_catalog.py 检查 27 项结构、17 项行为")
    return 2


def check_model_catalog() -> tuple[int, int]:
    structure = _expect(CATALOG_FRAGMENTS, _read(CATALOG), CATALOG)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_model_catalog()
    except (OSError, ValueError) as error:
        print(f"模型目录规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型目录规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
