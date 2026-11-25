#!/usr/bin/env python3
"""核对项目首页只写稳定事实：不追加版本更新说明，且保留发布状态、许可证与安装范围。

`CONTRIBUTING.md` 约定 README 只检查定位、启动方式、发布状态、许可证与安装范围是否准确，
近期进展与版本更新说明留在 CHANGELOG；版本候选频繁推进时，首页很容易被追加候选号、
逐版本变化或「更新日志」小节。这里扫描 README：禁止 `rc.N` / `X.Y.Z-rc` /
Python 包写法 `X.Y.ZrcN` 候选号、版本号或更新说明类标题、本机绝对路径；要求保留
CHANGELOG / 项目状态 / 发布约定 / 许可证 / 安全 / 支持 / 贡献 / 安装 / 用户与桌面指南
等稳定链接，以及「`main` 是开发分支」「桌面从源码构建」「MIT License」与 Releases 链接。
行为侧用合成 Markdown 核对每条规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
README = "README.md"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
RC_PATTERN = re.compile(
    r"\brc\.\d+\b|\d+\.\d+\.\d+-rc|\d+\.\d+\.\d+rc\d+", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)
VERSION_HEADING = re.compile(
    r"\d+\.\d+\.\d+|rc\.\d+|更新日志|更新说明|版本更新|近期进展|发布说明|What's new|Release notes",
    re.IGNORECASE,
)
LOCAL_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\\\Users")
REQUIRED_LINKS = (
    "CHANGELOG.md", "docs/STATUS.md", "RELEASING.md", "LICENSE", "SECURITY.md",
    "SUPPORT.md", "CONTRIBUTING.md", "SETUP.md", "docs/USER_GUIDE.md", "docs/DESKTOP_GUIDE.md",
)
REQUIRED_PHRASES = (
    "`main` 是开发分支", "桌面从源码构建", "MIT License",
    "数据离开本机只经过两条路径", "不包含遥测、崩溃上报或自动更新检查",
)
REQUIRED_URL = "https://github.com/can4hou6joeng4/boss-harness/releases"
ENGLISH_HEADING = "## English overview"
ENGLISH_PHRASES = (
    "The shell does not import kernel code.",
    "`main` is the development branch and source candidates are not releases",
    "The desktop is built from source and has no standalone installer yet.",
    "14 allowlisted tools (13 read-only plus one greeting action that requires approval on every call)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _violations(text: str, label: str = "README.md") -> list[str]:
    found: list[str] = []
    for match in RC_PATTERN.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(f"{label}:{line} 含候选版本号 {match.group(0)}")
    for match in HEADING.finditer(text):
        if VERSION_HEADING.search(match.group(1)):
            line = text.count("\n", 0, match.start()) + 1
            found.append(f"{label}:{line} 标题含版本或更新说明：{match.group(1)}")
    for match in LOCAL_PATH.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(f"{label}:{line} 含本机绝对路径")
    for link in REQUIRED_LINKS:
        if f"]({link})" not in text:
            found.append(f"{label} 缺少稳定链接 {link}")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            found.append(f"{label} 缺少稳定表述 {phrase}")
    if REQUIRED_URL not in text:
        found.append(f"{label} 缺少 Releases 链接")
    start = text.find(ENGLISH_HEADING)
    if start < 0:
        found.append(f"{label} 缺少英文概览章节")
    else:
        section = text[start + len(ENGLISH_HEADING):]
        end = section.find("\n## ")
        english = section if end < 0 else section[:end]
        for phrase in ENGLISH_PHRASES:
            if phrase not in english:
                found.append(f"{label} 英文概览缺少稳定表述 {phrase}")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"首页稳定事实变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    violations = _violations(_read(README))
    if violations:
        raise ValueError("首页稳定事实变化：" + "；".join(violations))
    return (3 + len(REQUIRED_LINKS) + len(REQUIRED_PHRASES) + 1
            + len(ENGLISH_PHRASES) + 1)


def _clean_sample() -> str:
    links = " ".join(f"[{link}]({link})" for link in REQUIRED_LINKS)
    phrases = " ".join(REQUIRED_PHRASES)
    english = "\n".join(f"- **要点**：{phrase}" for phrase in ENGLISH_PHRASES)
    return (f"# 项目\n\n{phrases}\n\n{links}\n\n已发布版本以 [Releases]({REQUIRED_URL}) 为准。\n"
            f"\n{ENGLISH_HEADING}\n\n{english}\n")


def _expect_count(source: str, expected: int, label: str) -> int:
    found = _violations(source, label)
    return _expect_value(len(found), expected, label)


def _check_behaviors() -> int:
    checked = 0
    checked += _expect_count(_clean_sample(), 0, "干净首页")
    checked += _expect_count(_clean_sample() + "\n当前候选 0.2.0-rc.9。\n", 1, "候选版本号")
    checked += _expect_count(_clean_sample() + "\n当前候选 1.4.2-rc.7。\n", 1, "任意候选版本号")
    checked += _expect_count(_clean_sample() + "\n当前候选 0.2.0rc9。\n", 1, "Python 候选版本号")
    checked += _expect_count(_clean_sample() + "\n## 更新日志\n", 1, "更新日志标题")
    checked += _expect_count(_clean_sample() + "\n## 0.2.0\n", 1, "版本标题")
    checked += _expect_count(_clean_sample() + "\n路径 /Users/example/project。\n", 1, "本机路径")
    checked += _expect_count(_clean_sample().replace("[SUPPORT.md](SUPPORT.md) ", ""), 1,
                             "缺少稳定链接")
    checked += _expect_count(_clean_sample().replace("桌面从源码构建", ""), 1, "缺少稳定表述")
    checked += _expect_count(_clean_sample().replace(ENGLISH_HEADING, "## English summary"), 1,
                             "缺少英文概览章节")
    checked += _expect_count(_clean_sample().replace(ENGLISH_PHRASES[0], ""), 1,
                             "英文概览缺少稳定表述")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_readme_stability.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_readme_stability.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少首页稳定事实检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"首页稳定事实一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
