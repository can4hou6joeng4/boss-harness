#!/usr/bin/env python3
"""核对快速提问的模型线路解析。

`quickAsk.ts` 把快速提问落到一条可用的 provider/model 线路：当前会话优先，
其次进程默认线路，最后目录里同一 provider 的条目。provider 与 model 必须
来自同一条线路——没有 provider 的旧会话不能把 model 与默认 provider 拼成
一对；空串与纯空白视为缺失；解析不出或线路为 `none` 时明确失败。这里用
Node 直接调用真实 `resolveQuickAskRoute`，逐项核对上述规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
QUICK_ASK = "apps/desktop/src/renderer/src/data/quickAsk.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

QUICK_ASK_FRAGMENTS = (
    "function usable(value: unknown): value is string {",
    'return typeof value === "string" && value.trim().length > 0;',
    "export function resolveQuickAskRoute(session: RouteFields | null | undefined,",
    "const sessionProvider = session && usable(session.provider) ? session.provider.trim() : undefined;",
    "const sessionModel = session && usable(session.model) ? session.model.trim() : undefined;",
    "const defaultProvider = defaultModel && usable(defaultModel.provider) ? defaultModel.provider.trim() : undefined;",
    "const defaultModelId = defaultModel && usable(defaultModel.model) ? defaultModel.model.trim() : undefined;",
    "const provider = sessionProvider ?? defaultProvider;",
    "const catalogModel = models?.find(candidate => candidate.provider === provider)?.id;",
    "const model = sessionProvider !== undefined && sessionModel !== undefined",
    ": provider !== undefined && provider === defaultProvider && defaultModelId !== undefined",
    ": usable(catalogModel) ? catalogModel.trim() : undefined;",
    "if (!provider || !model) {",
    'return { ok: false, reason: "没有可用的模型线路，无法提问。请先在设置中配置模型。" };',
    'if (provider.toLowerCase() === "none") {',
    'return { ok: false, reason: "当前模型线路为 none（未配置模型），无法提问。" };',
    "return { ok: true, route: { provider, model } };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { resolveQuickAskRoute } = await import(pathToFileURL(process.argv[1]).href);
const res = (outcome) => (outcome.ok ? { ok: true, provider: outcome.route.provider, model: outcome.route.model }
  : { ok: false, reason: outcome.reason });
const results = [
  res(resolveQuickAskRoute({ provider: " openai ", model: " gpt " }, null, [])),
  res(resolveQuickAskRoute({ provider: "openai" }, { provider: "anthropic", model: "claude" },
    [{ provider: "openai", id: "o1" }])),
  res(resolveQuickAskRoute({ model: "legacy-model" }, { provider: "openai", model: "gpt-5" }, [])),
  res(resolveQuickAskRoute({ model: "legacy" }, { provider: "openai" },
    [{ provider: "openai", id: "o2" }])),
  res(resolveQuickAskRoute(null, { provider: "openai", model: "gpt" }, [])),
  res(resolveQuickAskRoute(null, null, [{ provider: "openai", id: "o3" }])),
  res(resolveQuickAskRoute(undefined, undefined, undefined)),
  res(resolveQuickAskRoute(null, { provider: "none", model: "x" }, [])),
  res(resolveQuickAskRoute({ provider: "  ", model: "  " }, { provider: "openai", model: "gpt" }, [])),
  res(resolveQuickAskRoute({ provider: "openai" }, { provider: "openai", model: " gpt " },
    [{ provider: "openai", id: "o1" }])),
  res(resolveQuickAskRoute({ provider: "openai" }, { provider: "anthropic", model: "claude" },
    [{ provider: "anthropic", id: "a1" }, { provider: "openai", id: "o4" }])),
  res(resolveQuickAskRoute({ provider: "openai" }, null, [{ provider: "openai", id: "   " }])),
  res(resolveQuickAskRoute({ provider: "None", model: "x" }, null, [])),
];
process.stdout.write(JSON.stringify(results));
"""

MISSING = {"ok": False, "reason": "没有可用的模型线路，无法提问。请先在设置中配置模型。"}
NONE_ROUTE = {"ok": False, "reason": "当前模型线路为 none（未配置模型），无法提问。"}

EXPECTED = (
    {"ok": True, "provider": "openai", "model": "gpt"},
    {"ok": True, "provider": "openai", "model": "o1"},
    {"ok": True, "provider": "openai", "model": "gpt-5"},
    {"ok": True, "provider": "openai", "model": "o2"},
    {"ok": True, "provider": "openai", "model": "gpt"},
    MISSING,
    MISSING,
    NONE_ROUTE,
    {"ok": True, "provider": "openai", "model": "gpt"},
    {"ok": True, "provider": "openai", "model": "gpt"},
    {"ok": True, "provider": "openai", "model": "o4"},
    MISSING,
    NONE_ROUTE,
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
             str(ROOT / QUICK_ASK)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 快速提问试算失败，请核对 Node.js 24+ 与 quickAsk.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的快速提问结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回快速提问矩阵")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"快速提问线路用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"快速提问线路第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_quick_ask.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_quick_ask.py")
    if "共 17 项结构、13 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_quick_ask.py 检查 17 项结构、12 项行为")
    return 2


def check_quick_ask() -> tuple[int, int]:
    structure = _expect(QUICK_ASK_FRAGMENTS, _read(QUICK_ASK), QUICK_ASK)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_quick_ask()
    except (OSError, ValueError) as error:
        print(f"快速提问线路核对失败，{error}", file=sys.stderr)
        return 2
    print(f"快速提问线路一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
