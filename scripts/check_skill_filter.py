#!/usr/bin/env python3
"""核对技能菜单与未加载项的筛选规则。

`skillFilter.ts` 把查询归一化为 NFKC + zh-CN 小写后做包含匹配：技能按
id、名称与描述跨字段匹配，问题项按 id 与原因匹配；空查询原样返回原数组。
这里用 Node 直接调用真实模块，逐项核对上述规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL_FILTER = "apps/desktop/src/renderer/src/data/skillFilter.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FILTER_FRAGMENTS = (
    'const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("zh-CN");',
    "export function filterSkills(skills: SkillDescriptor[], query: string): SkillDescriptor[] {",
    "const needle = normalize(query).trim();",
    "if (!needle) return skills;",
    'return skills.filter(skill => normalize([skill.id, skill.name, skill.description].join("\\n")).includes(needle));',
    "export function filterSkillProblems(problems: SkillProblem[], query: string): SkillProblem[] {",
    "if (!needle) return problems;",
    "return problems.filter(problem => normalize(`${problem.id}\\n${problem.reason}`).includes(needle));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { filterSkills, filterSkillProblems } = await import(pathToFileURL(process.argv[1]).href);
const skill = (id, name, description) => ({ id, name, description });
const skills = [
  skill("alpha", "简历筛选", "按岗位匹配简历"),
  skill("beta", "Beta Tool", "resume search"),
];
const problem = (id, reason) => ({ id, reason });
const problems = [
  problem("alpha", "缺少 SKILL.md"),
  problem("gamma", "frontmatter 无法解析"),
];
const ids = (items) => items.map((item) => item.id);
const results = [
  filterSkills(skills, "") === skills,
  filterSkills(skills, "   ") === skills,
  ids(filterSkills(skills, "ALPHA")),
  ids(filterSkills(skills, "简历")),
  ids(filterSkills(skills, "匹配简历")),
  ids(filterSkills(skills, "ＡＬＰＨＡ")),
  ids(filterSkills(skills, "RESUME")),
  ids(filterSkills(skills, "alpha\n简历")),
  ids(filterSkills(skills, "nothing")),
  filterSkillProblems(problems, "") === problems,
  ids(filterSkillProblems(problems, "ALPHA")),
  ids(filterSkillProblems(problems, "解析")),
  ids(filterSkillProblems(problems, "不存在")),
];
process.stdout.write(JSON.stringify(results));
"""

EXPECTED = (
    True,
    True,
    ["alpha"],
    ["alpha"],
    ["alpha"],
    ["alpha"],
    ["beta"],
    ["alpha"],
    [],
    True,
    ["alpha"],
    ["gamma"],
    [],
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
             str(ROOT / SKILL_FILTER)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 技能筛选试算失败，请核对 Node.js 24+ 与 skillFilter.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的技能筛选结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回技能筛选矩阵")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"技能筛选用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"技能筛选第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_filter.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_filter.py")
    if "共 8 项结构、13 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_filter.py 检查 8 项结构、13 项行为")
    return 2


def check_skill_filter() -> tuple[int, int]:
    structure = _expect(FILTER_FRAGMENTS, _read(SKILL_FILTER), SKILL_FILTER)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_filter()
    except (OSError, ValueError) as error:
        print(f"技能筛选规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能筛选规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
