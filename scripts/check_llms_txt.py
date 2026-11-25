#!/usr/bin/env python3
"""核对根级 llms.txt 是稳定、可解析的代理入口。

`llms.txt` 按 llmstxt.org 的最小格式提供项目名、引用摘要和分节链接。检查只接受仓库内
存在的相对链接，拒绝候选版本号、本机路径、外部 URL 与构建 / 测试产物；结构侧固定
根文件的分节与关键入口、CI 工作流步骤和技术参考索引，行为侧用合成文本核对每条规则
都能检出且干净样本不误报。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "llms.txt"
DOCS = "docs/TECHNICAL_REFERENCE.md"
WORKFLOW = ".github/workflows/build.yml"

TITLE = "# BOSS Harness"
STRUCTURE_FRAGMENTS = (
    TITLE,
    "> 面向招聘任务的 Agent Harness",
    "## 快速入口",
    "## 开发与契约",
    "## 安全与支持",
    "- [README](README.md)",
    "- [技术参考](docs/TECHNICAL_REFERENCE.md)",
    "- [SECURITY.md](SECURITY.md)",
)
REQUIRED_TARGETS = (
    "README.md",
    "docs/STATUS.md",
    "CHANGELOG.md",
    "RELEASING.md",
    "CONTRIBUTING.md",
    "SETUP.md",
    "docs/README.md",
    "docs/TECHNICAL_REFERENCE.md",
    "docs/USER_GUIDE.md",
    "docs/DESKTOP_GUIDE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "LICENSE",
    "UPSTREAM.md",
)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
FORBIDDEN = (
    (re.compile(r"\brc\.\d+\b|\b\d+\.\d+\.\d+rc\d+\b"), "候选版本号"),
    (re.compile(r"/Users/|/home/|/private/tmp|/tmp/|file://"), "本机路径"),
    (re.compile(r"https?://"), "外部链接"),
    (re.compile(r"node_modules|\.venv|(?:^|[\s(/])dist/|(?:^|[\s(/])out/"), "构建或测试产物"),
)

GOOD_SAMPLE = """# BOSS Harness

> 稳定摘要。

## 入口

- [README](README.md)
- [文档](docs/README.md)
"""


def problems_of(text: str, root: Path, required: tuple[str, ...] = ()) -> list[str]:
    problems: list[str] = []
    lines = text.lstrip("﻿").splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or lines[first].strip() != TITLE:
        problems.append("首行必须是项目名一级标题")
    else:
        summary = next((line.strip() for line in lines[first + 1:] if line.strip()), "")
        if not summary.startswith(">"):
            problems.append("项目名后必须有引用块摘要")
        if any(line.startswith("# ") for line in lines[first + 1:]):
            problems.append("只能有一个一级标题")
    sections: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if line.startswith("## "):
            sections.append((index, line[3:].strip()))
    if len(sections) < 1:
        problems.append("至少需要一个分节")
    targets: list[str] = []
    for position, (index, _) in enumerate(sections):
        end = sections[position + 1][0] if position + 1 < len(sections) else len(lines)
        body = "\n".join(lines[index + 1:end])
        links = LINK_RE.findall(body)
        if not links:
            problems.append("每个分节至少需要一个链接")
        targets.extend(target for _, target in links)
    for target in targets:
        if target.startswith("/") or target.startswith("../") or ".." in Path(target).parts:
            problems.append(f"链接必须是仓库内相对路径：{target}")
        elif not (root / target).is_file():
            problems.append(f"链接目标不存在：{target}")
    for target in required:
        if target not in targets:
            problems.append(f"缺少必需入口：{target}")
    for pattern, label in FORBIDDEN:
        if pattern.search(text):
            problems.append(f"不得包含{label}")
    return problems


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _check_structures() -> int:
    checked = _expect(STRUCTURE_FRAGMENTS, _read(ENTRY), ENTRY)
    if "Verify llms.txt" not in _read(WORKFLOW) or "python scripts/check_llms_txt.py" not in _read(WORKFLOW):
        raise ValueError(f"{WORKFLOW} 未接入 llms.txt 检查")
    return checked + 1


def _check_behaviors() -> int:
    cases = [("干净样本", GOOD_SAMPLE, [])]
    cases.append(("缺少一级标题", GOOD_SAMPLE.replace(TITLE + "\n\n", ""), ["首行必须是项目名一级标题"]))
    cases.append(("缺少摘要", GOOD_SAMPLE.replace("> 稳定摘要。\n\n", ""), ["项目名后必须有引用块摘要"]))
    cases.append(("候选版本号", GOOD_SAMPLE.replace("稳定摘要。", "稳定摘要（rc.1）。"), ["不得包含候选版本号"]))
    cases.append(("本机路径", GOOD_SAMPLE.replace("稳定摘要。", "稳定摘要 /Users/example。"), ["不得包含本机路径"]))
    cases.append(("外部链接", GOOD_SAMPLE.replace("[README](README.md)", "[README](https://example.com)"), ["不得包含外部链接"]))
    cases.append(("分节无链接", GOOD_SAMPLE + "\n## 空节\n\n没有链接。\n", ["每个分节至少需要一个链接"]))
    cases.append(("目标不存在", GOOD_SAMPLE + "- [缺失](missing.md)\n", ["链接目标不存在：missing.md"]))
    cases.append(("缺少必需入口", GOOD_SAMPLE, ["缺少必需入口：docs/TECHNICAL_REFERENCE.md"]))
    failures: list[str] = []
    for name, text, expected in cases:
        required = ("docs/TECHNICAL_REFERENCE.md",) if name == "缺少必需入口" else ()
        found = problems_of(text, ROOT, required)
        if expected == []:
            if found:
                failures.append(f"{name}误报：{found[0]}")
        elif not any(item.startswith(expected[0]) for item in found):
            failures.append(f"{name}未检出")
    if failures:
        raise ValueError("；".join(failures))
    return len(cases)


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(DOCS)
    if "[`check_llms_txt.py`](#check_llms_txtpy)" not in reference:
        raise ValueError(f"{DOCS} 缺少 check_llms_txt.py 的索引链接")
    if "### `check_llms_txt.py`" not in reference:
        raise ValueError(f"{DOCS} 缺少 check_llms_txt.py 的章节")
    summary = f"共 {structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"{DOCS} 缺少 llms.txt 检查的计数：{summary}")


def main() -> int:
    try:
        problems = problems_of(_read(ENTRY), ROOT, REQUIRED_TARGETS)
        if problems:
            raise ValueError("；".join(problems))
        structures = _check_structures()
        behaviors = _check_behaviors()
        _check_documentation(structures, behaviors)
    except (OSError, ValueError) as error:
        print(f"llms.txt 入口核对失败，{error}", file=sys.stderr)
        return 2
    print(f"llms.txt 入口一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
