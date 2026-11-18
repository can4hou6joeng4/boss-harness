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
    if "pull_request_target" in text:
        raise ValueError(f"{name} 不得使用 pull_request_target")
    permissions = re.search(r"(?m)^permissions:\s*\n((?: {2}\S.*(?:\n|$))+)", text)
    if permissions is None:
        raise ValueError(f"{name} 缺少顶层 permissions")
    block = permissions.group(1)
    if re.search(r"(?m)^ {2}contents:\s*read\s*$", block) is None:
        raise ValueError(f"{name} 的 permissions 缺少 contents: read")
    if re.search(r"(?m)^ {2}\S.*:\s*write\s*$", block):
        raise ValueError(f"{name} 的 permissions 含 write 权限")
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
    return checkouts, len(actions)


def check_workflows() -> tuple[int, int, int]:
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not paths:
        raise ValueError(".github/workflows 下没有工作流")
    checkouts = 0
    actions = 0
    for path in paths:
        count, total = _check_workflow(path)
        checkouts += count
        actions += total
    return len(paths), checkouts, actions


def main() -> int:
    try:
        workflows, checkouts, actions = check_workflows()
    except (OSError, ValueError) as error:
        print(f"CI 工作流安全配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"CI 工作流安全配置一致：{workflows} 个工作流、{checkouts} 个 checkout、{actions} 个 action")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
