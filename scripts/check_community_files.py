#!/usr/bin/env python3
"""核对社区入口文件：安全报告渠道、支持分流、贡献约定与行为准则的稳定事实。

外部贡献者与安全报告者首先读到 SECURITY / SUPPORT / CONTRIBUTING / CODE_OF_CONDUCT。
这里锁定它们的稳定入口与约定：SUPPORT 的 Issue 模板链接必须与 `.github/ISSUE_TEMPLATE/`
实际文件名一致；安全政策保留私密报告入口、授权边界与上游职责划分；贡献约定保留提交格式
与「测试材料仅保留本地」；行为准则引用安全政策与贡献约定。文件不得含本机绝对路径。
行为侧用合成 Markdown 核对每条规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
TEMPLATE_DIR = ".github/ISSUE_TEMPLATE"
TEMPLATE_LINK = re.compile(r"issues/new\?template=([a-z0-9_]+\.yml)")
LOCAL_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\\\Users")

SECURITY = "SECURITY.md"
SUPPORT = "SUPPORT.md"
CONTRIBUTING = "CONTRIBUTING.md"
CONDUCT = "CODE_OF_CONDUCT.md"

SECURITY_PHRASES = (
    "Security → Report a vulnerability",
    "需要单独授权",
    "boss-agent-cli",
    "不承诺固定响应时限",
)
SUPPORT_TEMPLATES = ("bug_report.yml", "feature_request.yml")
SUPPORT_LINKS = ("SECURITY.md", "CODE_OF_CONDUCT.md")
CONTRIBUTING_PHRASES = (
    "type(scope): 中文描述",
    "Closes #N",
    "测试材料仅保留本地",
)
CONDUCT_LINKS = ("SECURITY.md", "CONTRIBUTING.md")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _local_path_problems(text: str, label: str) -> list[str]:
    found: list[str] = []
    for match in LOCAL_PATH.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(f"{label}:{line} 含本机绝对路径")
    return found


def _missing_phrases(text: str, phrases, label: str, kind: str) -> list[str]:
    return [f"{label} 缺少{kind} {phrase}" for phrase in phrases if phrase not in text]


def _security_problems(text: str) -> list[str]:
    found = _local_path_problems(text, SECURITY)
    found += _missing_phrases(text, SECURITY_PHRASES, SECURITY, "稳定表述")
    return found


def _support_problems(text: str, templates: set[str]) -> list[str]:
    found = _local_path_problems(text, SUPPORT)
    links = TEMPLATE_LINK.findall(text)
    for name in SUPPORT_TEMPLATES:
        if name not in links:
            found.append(f"{SUPPORT} 缺少 Issue 模板链接 {name}")
        elif links.count(name) > 1:
            found.append(f"{SUPPORT} 重复引用 Issue 模板 {name}")
    for name in links:
        if name not in templates:
            found.append(f"{SUPPORT} 引用了不存在的模板 {name}")
    for link in SUPPORT_LINKS:
        if f"]({link})" not in text:
            found.append(f"{SUPPORT} 缺少稳定链接 {link}")
    return found


def _contributing_problems(text: str) -> list[str]:
    found = _local_path_problems(text, CONTRIBUTING)
    found += _missing_phrases(text, CONTRIBUTING_PHRASES, CONTRIBUTING, "稳定约定")
    return found


def _conduct_problems(text: str) -> list[str]:
    found = _local_path_problems(text, CONDUCT)
    for link in CONDUCT_LINKS:
        if f"]({link})" not in text:
            found.append(f"{CONDUCT} 缺少稳定链接 {link}")
    if "私密渠道" not in text:
        found.append(f"{CONDUCT} 缺少私密报告渠道表述")
    return found


def _templates() -> set[str]:
    directory = ROOT / TEMPLATE_DIR
    try:
        names = {path.name for path in directory.iterdir() if path.suffix == ".yml"}
    except OSError:
        raise ValueError(f"无法读取 {TEMPLATE_DIR}") from None
    if not names:
        raise ValueError(f"{TEMPLATE_DIR} 没有任何模板")
    return names


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"社区入口变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    templates = _templates()
    problems = (
        _security_problems(_read(SECURITY))
        + _support_problems(_read(SUPPORT), templates)
        + _contributing_problems(_read(CONTRIBUTING))
        + _conduct_problems(_read(CONDUCT))
    )
    if problems:
        raise ValueError("社区入口变化：" + "；".join(problems))
    return (1 + len(SECURITY_PHRASES)
            + 1 + len(SUPPORT_TEMPLATES) + len(SUPPORT_LINKS)
            + 1 + len(CONTRIBUTING_PHRASES)
            + 1 + len(CONDUCT_LINKS) + 1)


def _clean_security() -> str:
    return ("# 安全政策\n\n首选 GitHub 的 Security → Report a vulnerability 入口。\n"
            "启用这些入口需要单独授权。\n上游 boss-agent-cli 的问题不属于本仓库。\n"
            "本项目不承诺固定响应时限。\n")


def _clean_support() -> str:
    base = "https://github.com/can4hou6joeng4/boss-harness/issues/new?template="
    return ("# 支持\n\n"
            f"[Bug]({base}bug_report.yml) [Feature]({base}feature_request.yml)\n"
            "安全问题见 [安全政策](SECURITY.md)，互动见 [行为准则](CODE_OF_CONDUCT.md)。\n")


def _clean_contributing() -> str:
    return ("# 贡献\n\n- 主题固定为 `type(scope): 中文描述`。\n"
            "- 正文用 `Closes #N` 关联 Issue。\n- 测试材料仅保留本地。\n")


def _clean_conduct() -> str:
    return ("# 行为准则\n\n通过私密渠道联系维护者。\n"
            "见 [安全政策](SECURITY.md) 与 [贡献与交付约定](CONTRIBUTING.md)。\n")


def _expect_count(found: int, expected: int, label: str) -> int:
    return _expect_value(found, expected, label)


def _check_behaviors() -> int:
    templates = set(SUPPORT_TEMPLATES) | {"config.yml"}
    checked = 0
    checked += _expect_count(len(_security_problems(_clean_security())), 0, "干净安全政策")
    checked += _expect_count(len(_support_problems(_clean_support(), templates)), 0, "干净支持页")
    checked += _expect_count(len(_contributing_problems(_clean_contributing())), 0, "干净贡献约定")
    checked += _expect_count(len(_conduct_problems(_clean_conduct())), 0, "干净行为准则")
    checked += _expect_count(
        len(_support_problems(re.sub(r"\[Bug\]\([^)]*bug_report\.yml\)\s*", "",
                                     _clean_support()), templates)),
        1, "缺少 Issue 模板引用")
    checked += _expect_count(
        len(_support_problems(_clean_support().replace("feature_request.yml", "ghost.yml"),
                              templates)), 2, "引用不存在的模板")
    checked += _expect_count(
        len(_support_problems(
            _clean_support() + "再次见 https://github.com/can4hou6joeng4/boss-harness"
            "/issues/new?template=bug_report.yml。\n", templates)),
        1, "重复引用模板")
    checked += _expect_count(
        len(_security_problems(_clean_security().replace("Security → Report a vulnerability", ""))),
        1, "缺少报告渠道")
    checked += _expect_count(
        len(_security_problems(_clean_security() + "路径 /Users/example/project。\n")),
        1, "本机路径")
    checked += _expect_count(
        len(_contributing_problems(_clean_contributing().replace("type(scope): 中文描述", ""))),
        1, "缺少提交格式")
    checked += _expect_count(
        len(_conduct_problems(_clean_conduct().replace("[安全政策](SECURITY.md)", "安全政策"))),
        1, "缺少安全政策链接")
    checked += _expect_count(
        len(_security_problems(_clean_security().replace("# 安全政策", "# 安全政策与响应"))),
        0, "无关措辞调整")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_community_files.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_community_files.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少社区入口检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"社区入口一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
