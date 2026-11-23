#!/usr/bin/env python3
"""核对 GitHub Actions 工作流的静态安全配置。"""

from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
CHECKOUT = "actions/checkout@"
STEP = re.compile(r"^ {6}- ")
USES = re.compile(r"(?m)^\s*(?:-\s*)?uses:\s*(\S+)\s*$")
PERMISSIONS = re.compile(r"(?m)^( *)permissions:\s*(.*)$")
CHECK_SCRIPT = re.compile(r"scripts/(check_[A-Za-z0-9_]+\.py)")
ACTION_REF = re.compile(r"^actions/[A-Za-z0-9_-]+@v\d+$")
FORBIDDEN_TRIGGERS = ("pull_request_target", "workflow_run")
JOB = re.compile(r"(?m)^  ([A-Za-z0-9_-]+):\s*$")
TIMEOUT = re.compile(r"(?m)^    timeout-minutes:\s*([1-9]\d*)\s*$")
MATRIX_JOB = "python-matrix"
TOMLIB_IMPORT = re.compile(r"(?m)^(?:from tomllib import|import tomllib)\b")
AUDIT_COMMANDS = (
    "npm audit --audit-level=moderate --omit=dev",
    "npm audit --audit-level=critical",
)


def _steps(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if STEP.match(line):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _check_workflow(path: Path) -> tuple[int, int]:
    name = path.relative_to(ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {name}") from None
    for trigger in FORBIDDEN_TRIGGERS:
        if trigger in text:
            raise ValueError(f"{name} 不得使用 {trigger} 触发器")
    jobs_heading = re.search(r"(?m)^jobs:\s*$", text)
    if jobs_heading is None:
        raise ValueError(f"{name} 缺少 jobs")
    jobs_text = text[jobs_heading.end():]
    jobs = list(JOB.finditer(jobs_text))
    if not jobs:
        raise ValueError(f"{name} 的 jobs 下没有作业")
    for index, job in enumerate(jobs):
        end = jobs[index + 1].start() if index + 1 < len(jobs) else len(jobs_text)
        if TIMEOUT.search(jobs_text[job.end():end]) is None:
            raise ValueError(f"{name} 的作业 {job.group(1)} 缺少正整数 timeout-minutes")
    permissions = re.search(r"(?m)^permissions:\s*\n((?: {2}\S.*(?:\n|$))+)", text)
    if permissions is None:
        raise ValueError(f"{name} 缺少顶层 permissions")
    block = permissions.group(1)
    if re.search(r"(?m)^ {2}contents:\s*read\s*$", block) is None:
        raise ValueError(f"{name} 的 permissions 缺少 contents: read")
    if re.search(r"(?m)^ {2}\S.*:\s*write\s*$", block):
        raise ValueError(f"{name} 的 permissions 含 write 权限")
    if any(match.group(1) for match in PERMISSIONS.finditer(text)):
        raise ValueError(f"{name} 只允许顶层 permissions，不得在 job 或 step 中声明")
    if (re.search(r"(?m)^concurrency:\s*$", text) is None
            or "cancel-in-progress: true" not in text):
        raise ValueError(f"{name} 的 concurrency 应启用 cancel-in-progress: true")
    checkouts = 0
    for step in _steps(text):
        if CHECKOUT not in step:
            continue
        checkouts += 1
        if "persist-credentials: false" not in step:
            raise ValueError(f"{name} 的 actions/checkout 缺少 persist-credentials: false")
    if checkouts == 0:
        raise ValueError(f"{name} 缺少 actions/checkout 步骤")
    actions = USES.findall(text)
    outside = sorted(action for action in actions if not action.startswith("actions/"))
    if outside:
        raise ValueError(f"{name} 使用了未登记的 action：" + "、".join(outside))
    mutable = sorted(action for action in actions if not ACTION_REF.match(action))
    if mutable:
        raise ValueError(f"{name} 的 action 必须固定到 v<主版本>：" + "、".join(mutable))
    return checkouts, len(actions)


def _matrix_problems(workflows: list[str], sources: dict[str, str]) -> list[str]:
    found: list[str] = []
    for text in workflows:
        heading = re.search(r"(?m)^jobs:\s*$", text)
        if heading is None:
            continue
        jobs_text = text[heading.end():]
        jobs = list(JOB.finditer(jobs_text))
        for index, job in enumerate(jobs):
            if job.group(1) != MATRIX_JOB:
                continue
            end = jobs[index + 1].start() if index + 1 < len(jobs) else len(jobs_text)
            for name in sorted(set(CHECK_SCRIPT.findall(jobs_text[job.end():end]))):
                source = sources.get(name)
                if source is None:
                    found.append(f"{MATRIX_JOB} 引用了不存在的检查脚本 {name}")
                elif TOMLIB_IMPORT.search(source):
                    found.append(f"{name} 在 Python 3.10 矩阵中运行但导入了 tomllib")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"CI 工作流安全配置变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _matrix_self_check() -> int:
    workflow = (
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - name: Verify versions\n"
        "        run: python scripts/check_versions.py\n"
        "  python-matrix:\n"
        "    steps:\n"
        "      - name: Verify demo\n"
        "        run: python scripts/check_demo.py\n"
    )
    sources = {"check_versions.py": "import tomllib\n", "check_demo.py": "print('ok')\n"}
    checked = 0
    checked += _expect_value(len(_matrix_problems([workflow], sources)), 0, "矩阵兼容")
    leaked = workflow.replace(
        "run: python scripts/check_demo.py",
        "run: python scripts/check_demo.py\n"
        "      - name: Verify versions\n"
        "        run: python scripts/check_versions.py",
    )
    checked += _expect_value(len(_matrix_problems([leaked], sources)), 1, "矩阵内 tomllib")
    ghost = workflow.replace("scripts/check_demo.py", "scripts/check_ghost.py")
    checked += _expect_value(len(_matrix_problems([ghost], sources)), 1, "矩阵内未知脚本")
    outside = workflow.replace("scripts/check_versions.py", "scripts/check_ghost.py")
    checked += _expect_value(len(_matrix_problems([outside], sources)), 0, "矩阵外未知脚本")
    return checked


def check_workflows() -> tuple[int, int, int, int]:
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not paths:
        raise ValueError(".github/workflows 下没有工作流")
    checkouts = 0
    actions = 0
    for path in paths:
        count, total = _check_workflow(path)
        checkouts += count
        actions += total
    scripts = {path.name for path in (ROOT / "scripts").glob("check_*.py")}
    if not scripts:
        raise ValueError("scripts 下没有 check_*.py")
    referenced: set[str] = set()
    combined: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        combined.append(text)
        referenced.update(CHECK_SCRIPT.findall(text))
    missing = sorted(scripts - referenced)
    unknown = sorted(referenced - scripts)
    if missing or unknown:
        raise ValueError(
            "CI 检查脚本覆盖不一致：未接入 " + ("、".join(missing) or "无")
            + "；引用不存在 " + ("、".join(unknown) or "无")
        )
    absent = [command for command in AUDIT_COMMANDS if command not in "\n".join(combined)]
    if absent:
        raise ValueError("工作流缺少依赖审计命令：" + "、".join(absent))
    sources: dict[str, str] = {}
    for name in sorted(scripts):
        try:
            sources[name] = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        except OSError:
            raise ValueError(f"无法读取 scripts/{name}") from None
    matrix = _matrix_problems(combined, sources)
    if matrix:
        raise ValueError("工作流矩阵兼容不一致：" + "；".join(matrix))
    _matrix_self_check()
    return len(paths), checkouts, actions, len(scripts)


def main() -> int:
    try:
        workflows, checkouts, actions, scripts = check_workflows()
    except (OSError, ValueError) as error:
        print(f"CI 工作流安全配置核对失败，{error}", file=sys.stderr)
        return 2
    print(
        f"CI 工作流安全配置一致：{workflows} 个工作流、{checkouts} 个 checkout、"
        f"{actions} 个 action、{scripts} 个检查脚本全覆盖"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
