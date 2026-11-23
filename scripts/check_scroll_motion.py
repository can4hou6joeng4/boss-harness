#!/usr/bin/env python3
"""核对聊天区滚动动效的解析规则。

`scrollMotion.ts` 决定 JavaScript 滚动是否使用平滑动效：应用内「减少动态效果」与
系统 `prefers-reduced-motion` 任一开启时使用即时滚动。这里静态核对模块契约，
并在 Node 中注入 `document` / `window` 桩，覆盖组合判定与各种缺失、异常环境。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/scrollMotion.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 聊天区滚动的动效解析。",
    " * CSS 的 `scroll-behavior` 会被显式 `behavior: \"smooth\"` 覆盖，因此 JavaScript 发起的",
    " * 滚动必须自己遵守「减少动态效果」：应用内设置与系统 `prefers-reduced-motion` 任一",
    " * 开启时使用即时滚动，避免设置说明与实际行为不一致。",
    'export type ScrollBehavior = "auto" | "smooth";',
    "export function resolveScrollBehavior(appMotion: string | undefined | null, systemPrefersReduced: boolean): ScrollBehavior {",
    'return appMotion === "reduced" || systemPrefersReduced ? "auto" : "smooth";',
    "/** 读取当前文档上的应用设置与系统偏好；环境缺失时退回平滑滚动。 */",
    "export function currentScrollBehavior(): ScrollBehavior {",
    "try { appMotion = document.documentElement.dataset.motion; } catch { /* 文档不可用时按未设置处理。 */ }",
    'try { systemPrefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true; } catch { /* 系统偏好不可用时按未开启处理。 */ }',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { resolveScrollBehavior, currentScrollBehavior } = await import(pathToFileURL(process.argv[1]).href);
const run = (documentValue, windowValue) => {
  if (documentValue === undefined) delete globalThis.document;
  else globalThis.document = documentValue;
  if (windowValue === undefined) delete globalThis.window;
  else globalThis.window = windowValue;
  return currentScrollBehavior();
};
const result = {
  resolve: [
    resolveScrollBehavior("reduced", false),
    resolveScrollBehavior("reduced", true),
    resolveScrollBehavior("default", false),
    resolveScrollBehavior("REDUCED", false),
    resolveScrollBehavior(undefined, true),
    resolveScrollBehavior(null, true),
    resolveScrollBehavior(undefined, false),
    resolveScrollBehavior("", false),
    resolveScrollBehavior("default", true),
  ],
  current: [
    run(undefined, undefined),
    run({ documentElement: { dataset: { motion: "reduced" } } }, undefined),
    run({ documentElement: { dataset: {} } }, { matchMedia: () => ({ matches: true }) }),
    run({ documentElement: { dataset: { motion: "default" } } }, { matchMedia: () => ({ matches: false }) }),
    run({}, { matchMedia: () => ({ matches: true }) }),
    run({ documentElement: { dataset: { motion: "default" } } }, { matchMedia: () => { throw new Error("blocked"); } }),
    run({}, undefined),
    run({ documentElement: { dataset: { motion: "reduced" } } }, { matchMedia: () => undefined }),
    run({ documentElement: { dataset: { motion: "default" } } }, { matchMedia: () => ({ matches: 1 }) }),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_RESOLVE = ("auto", "auto", "smooth", "smooth", "auto", "auto", "smooth", "smooth", "auto")
EXPECTED_CURRENT = ("smooth", "auto", "auto", "smooth", "auto", "smooth", "smooth", "auto", "smooth")
LABELS = {"resolve": "解析", "current": "环境"}


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
        raise ValueError("Node 滚动动效试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 滚动动效试算失败，请核对 Node.js 24+ 与 scrollMotion.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的滚动动效结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"滚动动效{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"滚动动效{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["resolve"], EXPECTED_RESOLVE, LABELS["resolve"])
            + _compare(payload["current"], EXPECTED_CURRENT, LABELS["current"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_scroll_motion.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_scroll_motion.py")
    if "共 11 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_scroll_motion.py 检查 11 项结构、18 项行为")
    return 2


def check_scroll_motion() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_scroll_motion()
    except (OSError, ValueError) as error:
        print(f"滚动动效规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"滚动动效规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
