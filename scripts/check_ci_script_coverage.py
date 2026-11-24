#!/usr/bin/env python3
"""固化 CI 接线不变量：每个检查脚本都在工作流里被命名步骤执行。

`npm run check` 在本地遍历 `scripts/check_*.py` 全量执行；CI 则在
`.github/workflows/build.yml` 中为脚本维护独立的 `- name: Verify ...` /
`run: python scripts/check_*.py` 步骤。新增脚本漏接工作流时回归保护只在本地
生效，删除脚本后残留步骤会让 CI 直接失败。这里解析工作流中的脚本引用，与
`scripts/check_*.py` 的实际文件双向核对，并要求每个引用步骤都有命名。
"""

from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
WORKFLOW = ".github/workflows/build.yml"
SCRIPT_DIR = "scripts"
SCRIPT_GLOB = "check_*.py"
RUN_PATTERN = re.compile(r"(?m)^\s+run: python (scripts/check_[a-z0-9_]+\.py)\s*$")
SCRIPT_LINE = re.compile(r"^(?:- )?run: python (scripts/check_[a-z0-9_]+\.py)$")
REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])(scripts/check_[a-z0-9_]+\.py)(?![A-Za-z0-9_.])"
)
STEP_NAME_PREFIX = "- name: Verify "


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def scan_scripts() -> list[str]:
    return [
        f"{SCRIPT_DIR}/{path.name}"
        for path in sorted((ROOT / SCRIPT_DIR).glob(SCRIPT_GLOB))
    ]


def referenced_scripts(workflow: str) -> list[str]:
    found: list[str] = []
    for line in workflow.splitlines():
        if line.strip().startswith("#"):
            continue
        found.extend(match.group(1) for match in REFERENCE_PATTERN.finditer(line))
    return found


def missing_from_workflow(files: list[str], referenced: list[str]) -> list[str]:
    cited = set(referenced)
    return sorted(path for path in files if path not in cited)


def unknown_references(referenced: list[str], files: list[str]) -> list[str]:
    known = set(files)
    return sorted({path for path in referenced if path not in known})


def unnamed_steps(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    unnamed: list[str] = []
    for index, line in enumerate(lines):
        match = SCRIPT_LINE.fullmatch(line.strip())
        if match is None:
            continue
        previous = next(
            (candidate.strip() for candidate in reversed(lines[:index]) if candidate.strip()),
            "",
        )
        if not previous.startswith(STEP_NAME_PREFIX):
            unnamed.append(match.group(1))
    return unnamed


def _check_real_workflow() -> None:
    files = scan_scripts()
    workflow = _read(WORKFLOW)
    referenced = referenced_scripts(workflow)
    if not referenced:
        raise ValueError(f"{WORKFLOW} 未找到检查脚本引用")
    missing = missing_from_workflow(files, referenced)
    if missing:
        raise ValueError("以下检查脚本未接入 CI：" + "、".join(missing))
    unknown = unknown_references(referenced, files)
    if unknown:
        raise ValueError("工作流引用了不存在的检查脚本：" + "、".join(unknown))
    unnamed = unnamed_steps(workflow)
    if unnamed:
        raise ValueError("以下 CI 步骤缺少 Verify 名称：" + "、".join(unnamed))


def _check_behaviors() -> int:
    _check_real_workflow()

    sample = (
        "steps:\n"
        "  - name: Verify alpha\n"
        "    run: python scripts/check_alpha.py\n"
        "  - name: Verify beta\n"
        "    run: python scripts/check_beta.py\n"
    )
    if referenced_scripts(sample) != ["scripts/check_alpha.py", "scripts/check_beta.py"]:
        raise ValueError("引用解析内容或顺序不符")
    if referenced_scripts("") != []:
        raise ValueError("空工作流应无引用")
    if missing_from_workflow(
        ["scripts/check_alpha.py", "scripts/check_gamma.py"], referenced_scripts(sample)
    ) != ["scripts/check_gamma.py"]:
        raise ValueError("遗漏脚本应被列出")
    if missing_from_workflow(
        ["scripts/check_beta.py", "scripts/check_alpha.py"], referenced_scripts(sample)
    ) != []:
        raise ValueError("完整覆盖不应报遗漏")
    if unknown_references(
        referenced_scripts(sample), ["scripts/check_alpha.py", "scripts/check_beta.py"]
    ) != []:
        raise ValueError("真实引用不应报悬空")
    if unknown_references(["scripts/check_gamma.py"], ["scripts/check_alpha.py"]) != [
        "scripts/check_gamma.py"
    ]:
        raise ValueError("悬空引用应被列出")
    if unnamed_steps("      - run: python scripts/check_alpha.py\n") != [
        "scripts/check_alpha.py"
    ]:
        raise ValueError("无名步骤应被列出")
    if unnamed_steps(
        "      - name: Verify alpha\n        run: python scripts/check_alpha.py\n"
    ) != []:
        raise ValueError("命名步骤不应被列出")
    if unnamed_steps("") != []:
        raise ValueError("空工作流应无无名步骤")
    embedded = (
        "env:\n"
        '  SOURCE_VERSION="$(python scripts/check_alpha.py)"\n'
        "steps:\n"
        "  # python scripts/check_beta.py\n"
        "  - name: Verify gamma\n"
        "    run: python scripts/check_gamma.py\n"
    )
    if referenced_scripts(embedded) != ["scripts/check_alpha.py", "scripts/check_gamma.py"]:
        raise ValueError("内嵌命令应算作引用且注释行不算")
    if referenced_scripts("xscripts/check_alpha.py") != []:
        raise ValueError("前缀相近的脚本路径不应算作引用")
    if referenced_scripts("scripts/check_alpha.pyc") != []:
        raise ValueError("后缀相近的脚本路径不应算作引用")
    if missing_from_workflow(
        ["scripts/check_gamma.py", "scripts/check_beta.py", "scripts/check_alpha.py"],
        ["scripts/check_alpha.py"],
    ) != ["scripts/check_beta.py", "scripts/check_gamma.py"]:
        raise ValueError("遗漏列表应稳定排序")
    if unnamed_steps(
        "      - name: Run alpha\n        run: python scripts/check_alpha.py\n"
    ) != ["scripts/check_alpha.py"]:
        raise ValueError("非 Verify 名称应被列出")
    return 14


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_ci_script_coverage.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_ci_script_coverage.py")
    if "共 10 项结构、14 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_ci_script_coverage.py 检查 10 项结构、14 项行为")
    return 2


FRAGMENTS = (
    'WORKFLOW = ".github/workflows/build.yml"',
    'SCRIPT_GLOB = "check_*.py"',
    "RUN_PATTERN = re.compile(",
    "SCRIPT_LINE = re.compile(",
    "REFERENCE_PATTERN = re.compile(",
    "def scan_scripts() -> list[str]:",
    "def referenced_scripts(workflow: str) -> list[str]:",
    "def missing_from_workflow(files: list[str], referenced: list[str]) -> list[str]:",
    "def unknown_references(referenced: list[str], files: list[str]) -> list[str]:",
    "def unnamed_steps(workflow: str) -> list[str]:",
)


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_ci_script_coverage() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, Path(__file__).read_text(encoding="utf-8"), __file__)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_ci_script_coverage()
    except (OSError, ValueError) as error:
        print(f"CI 脚本接线核对失败，{error}", file=sys.stderr)
        return 2
    print(f"CI 脚本接线一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
