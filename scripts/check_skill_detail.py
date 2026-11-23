#!/usr/bin/env python3
"""核对桌面技能详情的归属过滤与目录刷新选中态决策。

`skillDetail.ts` 用很小的纯函数挡住两类界面错位：详情正文必须与原条目的标识一致，
否则在 effect 清空前会挂到新选中的技能上；目录刷新期间不能因为空数组就断言技能已删除。
这里既核对模块结构，也用 Node 直接加载真实模块试算边界用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/skillDetail.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { SkillDescriptor, SkillReadResponse } from "@boss-harness/protocol";',
    "export function visibleSkillDetail(",
    "selected: SkillDescriptor | null,",
    "detail: SkillReadResponse | null,",
    "): SkillReadResponse | null {",
    "return selected && detail && detail.id === selected.id ? detail : null;",
    "export function skillSelectionSurvives(",
    "loading: boolean,",
    "skills: readonly SkillDescriptor[],",
    "selectedId: string | null,",
    "): boolean {",
    "return !selectedId || loading || skills.some(skill => skill.id === selectedId);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { visibleSkillDetail, skillSelectionSurvives } =
  await import(pathToFileURL(process.argv[1]).href);
const selected = id => ({ id, name: "名称", description: "说明", digest: `d-${id}`, bytes: 10 });
const detail = (id, over = {}) => ({
  ...selected(id), content: "正文", limitBytes: 4096, ...over,
});
const shared = detail("a");
const skills = [selected("a"), selected("b")];
const details = [detail("a")];
const before = JSON.stringify({ skills, details, shared });
const result = {
  details: [
    visibleSkillDetail(null, null),
    visibleSkillDetail(selected("a"), null),
    visibleSkillDetail(null, detail("a")),
    visibleSkillDetail(selected("a"), detail("b")),
    visibleSkillDetail(selected("a"), detail("a")),
    visibleSkillDetail(selected("a"), detail("a", { name: "其他", extra: "保留" })),
    visibleSkillDetail(selected(""), detail("")),
  ],
  identity: [visibleSkillDetail(selected("a"), shared) === shared],
  survives: [
    skillSelectionSurvives(false, [], null),
    skillSelectionSurvives(false, [], ""),
    skillSelectionSurvives(true, [], "a"),
    skillSelectionSurvives(false, [], "a"),
    skillSelectionSurvives(false, [selected("a")], "a"),
    skillSelectionSurvives(false, [selected("b")], "a"),
    skillSelectionSurvives(false, skills, "b"),
    skillSelectionSurvives(true, [selected("b")], "a"),
    skillSelectionSurvives(false, skills, null),
  ],
};
visibleSkillDetail(selected("a"), details[0]);
skillSelectionSurvives(false, skills, "b");
result.immutable = [
  JSON.stringify({ skills, details, shared }) === before,
  shared.content === "正文" && shared.limitBytes === 4096,
];
process.stdout.write(JSON.stringify(result));
"""

SELECT_A = {"id": "a", "name": "名称", "description": "说明", "digest": "d-a", "bytes": 10}
DETAIL_A = {**SELECT_A, "content": "正文", "limitBytes": 4096}
DETAIL_B = {**DETAIL_A, "id": "b", "digest": "d-b"}
DETAIL_A_EXTRA = {**DETAIL_A, "name": "其他", "extra": "保留"}
DETAIL_EMPTY = {**DETAIL_A, "id": "", "digest": "d-"}

EXPECTED_DETAILS = (
    None, None, None, None, DETAIL_A, DETAIL_A_EXTRA, DETAIL_EMPTY,
)
EXPECTED_IDENTITY = (True,)
EXPECTED_SURVIVES = (
    True, True, True, False, True, False, True, True, True,
)
EXPECTED_IMMUTABLE = (True, True)


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
        raise ValueError("Node 技能详情试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 技能详情试算失败，请核对 Node.js 24+ 与 skillDetail.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的技能详情结果") from None
    for key in ("details", "identity", "survives", "immutable"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"技能详情{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"技能详情{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["details"], EXPECTED_DETAILS, "详情归属")
    checked += _compare(payload["identity"], EXPECTED_IDENTITY, "原样返回")
    checked += _compare(payload["survives"], EXPECTED_SURVIVES, "选中态")
    checked += _compare(payload["immutable"], EXPECTED_IMMUTABLE, "入参不变")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_detail.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_detail.py")
    if "共 12 项结构、19 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_detail.py 检查 12 项结构、19 项行为")
    return 2


def check_skill_detail() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_detail()
    except (OSError, ValueError) as error:
        print(f"技能详情规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能详情规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
