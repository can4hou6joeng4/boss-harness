#!/usr/bin/env python3
"""核对发布约定与上游记录：授权边界、发布拼写、资产口径与固定提交。

`RELEASING.md` 是发布授权的书面边界：tag、Release、资产上传与注册表发布各自需要
单独授权，源码 PR 授权不自动覆盖这些动作。`UPSTREAM.md` 的每条吸收记录引用 Pi 的
固定提交作为核对依据。这里锁定这些稳定事实，防止授权边界被放宽或固定提交引用漂移；
两个文件不得含本机绝对路径。行为侧用合成 Markdown 核对每条规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
LOCAL_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\\\Users")

RELEASING = "RELEASING.md"
UPSTREAM = "UPSTREAM.md"
PI_COMMIT = "b4899f59ef0fba6507c2e619fd804dcde51920ba"

RELEASING_PHRASES = (
    "发布仍需要对应授权",
    "完整 40 位 head SHA",
    "Python 使用对应的 PEP 440 拼写",
    "尚未执行的检查写为待执行",
    "不等于 GitHub Release 资产",
)
AUTHORIZATION_ACTIONS = (
    "推送 annotated tag。",
    "创建 GitHub Release，并标为候选预发布。",
    "上传已核对的资产。",
    "向 npm、PyPI 等注册表发布",
)
AUTHORIZATION_BOUNDARY = (
    "源码 PR 的推送 / 合并授权，不自动覆盖 tag、Release、注册表或第三方社区发送"
)


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


def _releasing_problems(text: str) -> list[str]:
    found = _local_path_problems(text, RELEASING)
    found += _missing_phrases(text, RELEASING_PHRASES, RELEASING, "稳定表述")
    found += _missing_phrases(text, AUTHORIZATION_ACTIONS, RELEASING, "授权动作")
    found += _missing_phrases(text, (AUTHORIZATION_BOUNDARY,), RELEASING, "授权边界")
    return found


def _upstream_problems(text: str) -> list[str]:
    found = _local_path_problems(text, UPSTREAM)
    found += _missing_phrases(text, (PI_COMMIT,), UPSTREAM, "固定提交")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"发布文档变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    problems = _releasing_problems(_read(RELEASING)) + _upstream_problems(_read(UPSTREAM))
    if problems:
        raise ValueError("发布文档变化：" + "；".join(problems))
    return (1 + len(RELEASING_PHRASES) + len(AUTHORIZATION_ACTIONS) + 1
            + 1 + 1)


def _clean_releasing() -> str:
    phrases = "\n".join(RELEASING_PHRASES)
    actions = "\n".join(f"- {action}" for action in AUTHORIZATION_ACTIONS)
    return (f"# 发布约定\n\n{phrases}\n\n{AUTHORIZATION_BOUNDARY}\n\n{actions}\n")


def _clean_upstream() -> str:
    return f"# 上游吸收记录\n\n重新核对 Pi MIT 固定提交 `{PI_COMMIT}` 的会话管理实现。\n"


def _expect_count(found: int, expected: int, label: str) -> int:
    return _expect_value(found, expected, label)


def _check_behaviors() -> int:
    checked = 0
    checked += _expect_count(len(_releasing_problems(_clean_releasing())), 0, "干净发布约定")
    checked += _expect_count(len(_upstream_problems(_clean_upstream())), 0, "干净上游记录")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace("发布仍需要对应授权", ""))),
        1, "缺少授权触发条件")
    for action in AUTHORIZATION_ACTIONS:
        checked += _expect_count(
            len(_releasing_problems(_clean_releasing().replace(action, ""))),
            1, f"缺少授权动作 {action}")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace("完整 40 位 head SHA", ""))),
        1, "缺少完整提交绑定")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace("尚未执行的检查写为待执行", ""))),
        1, "缺少待执行口径")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace("不等于 GitHub Release 资产", ""))),
        1, "缺少资产口径")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace(AUTHORIZATION_BOUNDARY, ""))),
        1, "缺少授权边界")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing() + "路径 /Users/example/project。\n")),
        1, "发布约定本机路径")
    checked += _expect_count(
        len(_upstream_problems(_clean_upstream().replace(PI_COMMIT, "main"))),
        1, "缺少固定提交")
    checked += _expect_count(
        len(_upstream_problems(_clean_upstream() + "路径 /home/example。\n")),
        1, "上游记录本机路径")
    checked += _expect_count(
        len(_releasing_problems(_clean_releasing().replace("# 发布约定", "# 发布与授权约定"))),
        0, "无关措辞调整")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_release_docs.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_release_docs.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少发布文档检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"发布文档一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
