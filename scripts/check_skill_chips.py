#!/usr/bin/env python3
"""核对输入区技能标签的映射、去重、失效标记与展示截断。

`skillChips.ts` 把草稿中的技能 id 映射成可渲染标签：id 原样保留，名称与描述
折叠空白并安全截断；未知 id 仅在目录已确认时标记为失效；重复 id 去重且最多
展示 10 项。这里静态核对模块结构，并用 Node 加载真实模块与真实 `safeSlice`
试算行为边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/skillChips.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"
SAFE_IMPORT = 'import { safeSlice } from "@boss-harness/shared";\n'
TYPE_IMPORT = 'import type { SkillDescriptor } from "@boss-harness/protocol";\n'

FRAGMENTS = (
    SAFE_IMPORT.rstrip("\n"),
    TYPE_IMPORT.rstrip("\n"),
    "/** 输入区最多展示的已选技能；与每回合可选 10 项技能保持一致。 */",
    "export const SKILL_CHIP_LIMIT = 10;",
    "const NAME_LIMIT = 60;",
    "const DESCRIPTION_LIMIT = 200;",
    "export interface SkillChip {",
    "id: string;",
    "name: string;",
    "stale: boolean;",
    "description?: string;",
    "function compact(value: unknown, limit: number): string {",
    'if (typeof value !== "string") return "";',
    r'return safeSlice(value.replace(/\s+/g, " ").trim(), limit);',
    "export function skillChips(ids: readonly string[], skills: readonly SkillDescriptor[], catalogKnown = true): SkillChip[] {",
    "const byId = new Map(skills.map(skill => [skill.id, skill]));",
    "const seen = new Set<string>();",
    "const chips: SkillChip[] = [];",
    "if (chips.length >= SKILL_CHIP_LIMIT) break;",
    "if (!raw || seen.has(raw)) continue;",
    "seen.add(raw);",
    "const skill = byId.get(raw);",
    "const displayId = compact(raw, NAME_LIMIT) || raw;",
    "if (!skill) {",
    "chips.push({ id: raw, name: displayId, stale: catalogKnown });",
    "continue;",
    "const description = compact(skill.description, DESCRIPTION_LIMIT);",
    'chips.push({ id: raw, name: compact(skill.name, NAME_LIMIT) || displayId, stale: false, ...(description ? { description } : {}) });',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { safeSlice } = await import(pathToFileURL(process.argv[2]).href);
globalThis.safeSlice = safeSlice;
const { skillChips, SKILL_CHIP_LIMIT } = await import(pathToFileURL(process.argv[1]).href);
const sk = (id, over = {}) => ({
  id, name: `技能${id}`, description: `说明${id}`, digest: `d${id}`, bytes: 10, ...over,
});
const run = (ids, skills, known) => skillChips(ids, skills, known);
const many = Array.from({ length: SKILL_CHIP_LIMIT + 1 }, (_, i) => `s${i}`);
const longId = "i".repeat(61);
const longName = "n".repeat(61);
const longDesc = "d".repeat(201);
const emojiName = "x" + "😀".repeat(30);
const emojiDesc = "😀".repeat(100) + "x";
const result = [
  run([], []),
  run(["a"], []),
  run(["a"], [], false),
  run(["a"], [sk("a")]),
  run(["a"], [sk("a", { description: "" })]),
  run(["a"], [sk("a", { description: "   " })]),
  run(["a"], [sk("a", { name: "  " })]),
  run(["a", "a"], []),
  run(["", "a"], []),
  run(["a", "b", "a"], []),
  run(many, []),
  run(["b", "a"], [sk("a"), sk("b")]),
  run(["a"], [sk("a", { name: "  多   空   格  " })]),
  run(["a"], [sk("a", { name: longName })]),
  run(["a"], [sk("a", { name: emojiName })]),
  run(["a"], [sk("a", { description: longDesc })]),
  run(["a"], [sk("a", { description: emojiDesc })]),
  run(["  a   b  "], []),
  run([longId], []),
  run(["a"], [sk("a")], false),
  run(["a", "missing"], [sk("a")], false),
  run(["a", "b"], [sk("a")]),
];
process.stdout.write(JSON.stringify(result));
"""


def chip(identifier: str, name: str, stale: bool, description: str | None = None) -> dict:
    return {
        "id": identifier,
        "name": name,
        "stale": stale,
        **({"description": description} if description is not None else {}),
    }


LONG_ID = "i" * 61
LONG_NAME = "n" * 60
LONG_DESC = "d" * 200
EMOJI_NAME = "x" + "😀" * 29
EMOJI_DESC = "😀" * 100
EXPECTED = (
    [],
    [chip("a", "a", True)],
    [chip("a", "a", False)],
    [chip("a", "技能a", False, "说明a")],
    [chip("a", "技能a", False)],
    [chip("a", "技能a", False)],
    [chip("a", "a", False, "说明a")],
    [chip("a", "a", True)],
    [chip("a", "a", True)],
    [chip("a", "a", True), chip("b", "b", True)],
    [chip(f"s{i}", f"s{i}", True) for i in range(10)],
    [chip("b", "技能b", False, "说明b"), chip("a", "技能a", False, "说明a")],
    [chip("a", "多 空 格", False, "说明a")],
    [chip("a", LONG_NAME, False, "说明a")],
    [chip("a", EMOJI_NAME, False, "说明a")],
    [chip("a", "技能a", False, LONG_DESC)],
    [chip("a", "技能a", False, EMOJI_DESC)],
    [chip("  a   b  ", "a b", True)],
    [chip(LONG_ID, LONG_ID[:60], True)],
    [chip("a", "技能a", False, "说明a")],
    [chip("a", "技能a", False, "说明a"), chip("missing", "missing", False)],
    [chip("a", "技能a", False, "说明a"), chip("b", "b", True)],
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _run_node(target: Path) -> list:
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / "skillChips.ts"
        source = target.read_text(encoding="utf-8")
        if SAFE_IMPORT not in source:
            raise ValueError("目标模块缺少 safeSlice 导入，无法在隔离目录中试算")
        copy.write_text(source.replace(SAFE_IMPORT, "", 1).replace(TYPE_IMPORT, "", 1), encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
                    str(copy), str(ROOT / SHARED),
                ],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 技能标签试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 技能标签试算失败，请核对 Node.js 24+ 与 skillChips.ts"
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
    return _compare(_run_node(ROOT / TARGET), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_chips.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_chips.py")
    if "共 28 项结构、22 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_chips.py 检查 28 项结构、22 项行为")
    return 2


def check_skill_chips() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_chips()
    except (OSError, ValueError) as error:
        print(f"技能标签规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能标签规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
