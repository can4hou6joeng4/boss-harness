#!/usr/bin/env python3
"""核对项目状态页只写稳定事实：不追加当前候选号，且保留发布状态与验收入口。

`docs/STATUS.md` 说明源码候选与实际发布的区别。每个源码候选都会递增版本号，
状态页很容易被追加「当前候选 rc.N」或临时进展，变成第二份 CHANGELOG；发布状态、
待验收范围与联系入口也可能在整理时被移走。这里扫描状态页：禁止出现当前候选
版本号（含 npm / Python 两种写法与 `rc.N`）、本机绝对路径；要求保留五个固定章节、
根文档与 Issue 滚动记录的稳定链接、已发布 tag 链接，以及开发分支、候选不等于发布、
npm / PyPI 尚未发布的稳定表述。行为侧用合成 Markdown 核对每条规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STATUS = "docs/STATUS.md"
PACKAGE = "package.json"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
REQUIRED_HEADINGS = (
    "## 发布状态",
    "## 已具备",
    "## 待完成与待验收",
    "## 非目标",
    "## 参与方式",
)
RELATIVE_LINKS = (
    "../README.md", "../package.json", "../CHANGELOG.md", "../RELEASING.md",
    "../SUPPORT.md", "../SECURITY.md", "../CONTRIBUTING.md", "TECHNICAL_REFERENCE.md",
)
REQUIRED_URLS = (
    "https://github.com/can4hou6joeng4/boss-harness/issues/2351",
    "https://github.com/can4hou6joeng4/boss-harness/issues/2312",
    "https://github.com/can4hou6joeng4/boss-harness/releases",
)
REQUIRED_PHRASES = ("`main` 是开发分支", "不等同于已发布", "尚未发布到 npm 或 PyPI")
ROLLING_RELEASE_ENTRY = "https://github.com/can4hou6joeng4/boss-harness/issues/2351"
NEXT_RELEASE_MARKER = "下一次实际预发布"
RELEASE_TAG = re.compile(
    r"https://github\.com/can4hou6joeng4/boss-harness/releases/tag/v0\.2\.0-rc\.\d+")
LOCAL_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\\\Users")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _version() -> str:
    try:
        return json.loads(_read(PACKAGE))["version"]
    except (ValueError, KeyError, TypeError):
        raise ValueError(f"{PACKAGE} 缺少版本号") from None


def _candidate_pattern(version: str) -> re.Pattern[str]:
    tokens = [version, version.replace("-rc.", "rc")]
    if "-rc." in version:
        tokens.append("rc." + version.split("-rc.", 1)[1])
    return re.compile("|".join(re.escape(token) for token in tokens), re.IGNORECASE)


def _violations(text: str, version: str, label: str = STATUS) -> list[str]:
    found: list[str] = []
    seen: set[int] = set()
    for match in _candidate_pattern(version).finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        if line in seen:
            continue
        seen.add(line)
        found.append(f"{label}:{line} 含当前候选版本号 {match.group(0)}")
    for match in LOCAL_PATH.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(f"{label}:{line} 含本机绝对路径")
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            found.append(f"{label} 缺少章节 {heading}")
    for link in RELATIVE_LINKS:
        if f"]({link}" not in text:
            found.append(f"{label} 缺少稳定链接 {link}")
    for url in REQUIRED_URLS:
        if url not in text:
            found.append(f"{label} 缺少稳定入口 {url}")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            found.append(f"{label} 缺少稳定表述 {phrase}")
    for line_number, line in enumerate(text.splitlines(), 1):
        if NEXT_RELEASE_MARKER in line and ROLLING_RELEASE_ENTRY not in line:
            found.append(f"{label}:{line_number} 的「下一次实际预发布」未指向滚动记录")
    if RELEASE_TAG.search(text) is None:
        found.append(f"{label} 缺少已发布 tag 链接")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"状态页稳定事实变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    label = STATUS
    violations = _violations(_read(STATUS), _version(), label)
    if violations:
        raise ValueError("状态页稳定事实变化：" + "；".join(violations))
    return (len(REQUIRED_HEADINGS) + len(RELATIVE_LINKS) + len(REQUIRED_URLS)
            + len(REQUIRED_PHRASES) + 4)


def _clean_sample(version: str) -> str:
    headings = "\n\n".join(f"{heading}\n\n占位。" for heading in REQUIRED_HEADINGS)
    links = " ".join(f"[目标{i}]({link})" for i, link in enumerate(RELATIVE_LINKS))
    urls = " ".join(f"[入口{i}]({url})" for i, url in enumerate(REQUIRED_URLS))
    phrases = " ".join(REQUIRED_PHRASES)
    tag = "https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15"
    return f"# 状态\n\n{phrases}\n\n{links}\n\n{urls}\n\n[已发布]({tag})\n\n{headings}\n"


def _expect_count(source: str, version: str, expected: int, label: str) -> int:
    return _expect_value(len(_violations(source, version, label)), expected, label)


def _check_behaviors() -> int:
    version = "0.2.0-rc.9"
    checked = 0
    checked += _expect_count(_clean_sample(version), version, 0, "干净状态页")
    checked += _expect_count(_clean_sample(version).replace("# 状态", "# 状态 0.2.0-rc.9"),
                             version, 1, "当前候选版本号")
    checked += _expect_count(_clean_sample(version).replace("# 状态", "# 状态 0.2.0rc9"),
                             version, 1, "Python 版本写法")
    checked += _expect_count(_clean_sample(version).replace("# 状态", "# 状态 rc.9"),
                             version, 1, "短候选号")
    checked += _expect_count(_clean_sample(version).replace("## 非目标\n", ""),
                             version, 1, "缺少章节")
    checked += _expect_count(_clean_sample(version).replace("](../RELEASING.md", "](RELEASING.md"),
                             version, 1, "缺少稳定链接")
    checked += _expect_count(_clean_sample(version).replace("](https://github.com/can4hou6joeng4/boss-harness/issues/2312) ",
                                                          "", 1),
                             version, 1, "缺少滚动记录入口")
    checked += _expect_count(_clean_sample(version).replace("尚未发布到 npm 或 PyPI", ""),
                             version, 1, "缺少稳定表述")
    checked += _expect_count(_clean_sample(version).replace("# 状态", "# 状态 /Users/example/x"),
                             version, 1, "本机路径")
    checked += _expect_count(_clean_sample(version).replace(
        "https://github.com/can4hou6joeng4/boss-harness/releases/tag/v0.2.0-rc.15", ""),
        version, 1, "缺少已发布 tag")
    checked += _expect_count(
        _clean_sample(version) + "\n下一次实际预发布：见 [旧计划](https://github.com/can4hou6joeng4/boss-harness/issues/3259)\n",
        version, 1, "下一次发布未指向滚动记录")
    checked += _expect_count(
        _clean_sample(version) + f"\n下一次实际预发布：见 [滚动记录]({ROLLING_RELEASE_ENTRY})\n",
        version, 0, "下一次发布滚动记录")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_status_stability.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_status_stability.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少状态页稳定事实检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"状态页稳定事实一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
