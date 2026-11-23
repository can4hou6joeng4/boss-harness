#!/usr/bin/env python3
"""核对从回合技能标签跳转时的聚焦目标解析。

`skillFocus.ts` 在目录命中时立即返回目标，目录尚未命中时只有 `loading` 状态
保持等待，其余终态结束等待；空焦点值立即结束。这里静态核对模块契约，并用 Node
直接加载真实模块覆盖五种目录状态与焦点边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/skillFocus.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { SkillDescriptor } from "@boss-harness/protocol";',
    'import type { SkillCatalogState } from "./harnessBridge";',
    " * 从回合技能标签跳转时，目录就绪后再决定聚焦目标。",
    " * 找到返回 id；目录已给出终态但不存在时返回空并结束等待；",
    " * 仍在读取时保持 pending，等下一次目录更新。",
    "export function resolveSkillFocus(focusId: string | null | undefined, skills: SkillDescriptor[], state: SkillCatalogState): { selectedId: string | null; done: boolean } {",
    "if (!focusId) return { selectedId: null, done: true };",
    "if (skills.some(skill => skill.id === focusId)) return { selectedId: focusId, done: true };",
    'return { selectedId: null, done: state !== "loading" };',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { resolveSkillFocus } = await import(pathToFileURL(process.argv[1]).href);
const sk = id => ({ id, name: `名${id}`, description: "", digest: "d", bytes: 1 });
const run = (focus, ids, state) => resolveSkillFocus(focus, ids.map(sk), state);
const result = [
  run(null, [], "loading"),
  run(undefined, [], "ready"),
  run("", [], "loading"),
  run("a", [], "loading"),
  run("a", [], "unavailable"),
  run("a", [], "ready"),
  run("a", [], "empty"),
  run("a", [], "error"),
  run("a", ["a"], "loading"),
  run("a", ["b", "a"], "error"),
  run("A", ["a"], "ready"),
  run("a", ["a", "a"], "loading"),
];
process.stdout.write(JSON.stringify(result));
"""

DONE_NULL = {"selectedId": None, "done": True}
PENDING = {"selectedId": None, "done": False}
FOUND = {"selectedId": "a", "done": True}
EXPECTED = (
    DONE_NULL, DONE_NULL, DONE_NULL,
    PENDING, DONE_NULL, DONE_NULL, DONE_NULL, DONE_NULL,
    FOUND, FOUND, DONE_NULL, FOUND,
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 聚焦目标试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 聚焦目标试算失败，请核对 Node.js 24+ 与 skillFocus.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的聚焦目标结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回聚焦目标列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"聚焦目标用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"聚焦目标第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_focus.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_focus.py")
    if "共 9 项结构、12 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_focus.py 检查 9 项结构、12 项行为")
    return 2


def check_skill_focus() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_focus()
    except (OSError, ValueError) as error:
        print(f"技能聚焦目标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能聚焦目标一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
