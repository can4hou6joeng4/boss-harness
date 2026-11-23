#!/usr/bin/env python3
"""核对队列项技能标签的校验、去重、上限与名称回退。

`queueSkillLabels.ts` 先校验 id 再计数，非法项不占用 10 项名额；按 id 去重，
目录中的非空名称优先，空名称回退 id，同名不同 id 不合并。这里静态核对模块结构，
并用 Node 直接加载真实模块覆盖输入边界与展示优先级。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueSkillLabels.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { SkillDescriptor } from "@boss-harness/protocol";',
    "const LABEL_LIMIT = 10;",
    "const ID_LIMIT = 200;",
    "/** 只接受非空、有界的字符串 id；非法项不占用 10 项名额。 */",
    "function skillId(value: unknown): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;',
    " * 队列项技能的可读标签：优先显示目录中的名称，找不到或名称为空时回退 id。",
    " * 先校验、后计数：跳过非法 id，按 id 去重并最多 10 项；目录不要求名称唯一，",
    " * 同名不同 id 是两个技能，不得按显示名合并。",
    "export function queueSkillLabels(skillIds: string[] | null | undefined, skills: SkillDescriptor[] = []): string[] {",
    "if (!Array.isArray(skillIds)) return [];",
    "const names = new Map(skills.map(skill => [skill.id, skill.name]));",
    "const labels: string[] = [];",
    "const seen = new Set<string>();",
    "for (const id of skillIds) {",
    "if (labels.length >= LABEL_LIMIT) break;",
    "if (!skillId(id) || seen.has(id)) continue;",
    "seen.add(id);",
    "const name = names.get(id);",
    'labels.push(typeof name === "string" && name.trim() ? name : id);',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { queueSkillLabels } = await import(pathToFileURL(process.argv[1]).href);
const sk = (id, name) => ({ id, name, description: "", digest: "d", bytes: 1 });
const run = (ids, skills = []) => queueSkillLabels(ids, skills);
const many = Array.from({ length: 12 }, (_, i) => `s${i}`);
const emptyFirst = [...Array(10).fill(""), "good"];
const longId = "x".repeat(200);
const tooLongId = "y".repeat(201);
const result = [
  run(null),
  run(undefined),
  run("a"),
  run([]),
  run(["a"]),
  run(["a"], [sk("a", "名称")]),
  run(["a"], [sk("a", "")]),
  run(["a"], [sk("a", "   ")]),
  run(["a"], [sk("a", "  名  ")]),
  run(["", tooLongId, 42, null, "a"], [sk("a", "名称")]),
  run(["a", "a"], [sk("a", "名称")]),
  run(many),
  run(emptyFirst),
  run(["a", "b"], [sk("a", "同名"), sk("b", "同名")]),
  run([longId]),
];
process.stdout.write(JSON.stringify(result));
"""

LONG_ID = "x" * 200
EXPECTED = (
    [], [], [], [],
    ["a"], ["名称"], ["a"], ["a"], ["  名  "],
    ["名称"], ["名称"],
    [f"s{i}" for i in range(10)],
    ["good"], ["同名", "同名"], [LONG_ID],
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
        raise ValueError("Node 技能标签试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 技能标签试算失败，请核对 Node.js 24+ 与 queueSkillLabels.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的技能标签结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回技能标签列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"技能标签用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"技能标签第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_skill_labels.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_skill_labels.py")
    if "共 20 项结构、15 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_skill_labels.py 检查 20 项结构、15 项行为")
    return 2


def check_queue_skill_labels() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_skill_labels()
    except (OSError, ValueError) as error:
        print(f"队列技能标签核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列技能标签一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
