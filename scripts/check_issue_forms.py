#!/usr/bin/env python3
"""核对 GitHub Issue 表单、联系入口与 PR 模板保持可用且指向仓库内文件。

Issue 表单是公开反馈入口：控件类型拼错、缺少必填校验或 `body` 结构失效时，
GitHub 只会静默显示错误。`config.yml` 的 `blob/main/...` 联系链接指向仓库文档，
文档移动后链接腐烂，而通用链接检查只覆盖相对链接、跳过外链。PR 模板里的
「单行 `type(scope): 中文描述`」与「`Closes #N`」同样是贡献约定的入口提示。
这里扫描三份 `.github` 治理文件，并用合成 YAML / Markdown 核对每条规则。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ".github/ISSUE_TEMPLATE"
FORMS = (f"{TEMPLATES}/bug_report.yml", f"{TEMPLATES}/feature_request.yml")
CONFIG = f"{TEMPLATES}/config.yml"
PR_TEMPLATE = ".github/PULL_REQUEST_TEMPLATE.md"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ALLOWED_TYPES = frozenset({"markdown", "input", "textarea", "dropdown", "checkboxes"})
BLOB_PREFIX = "https://github.com/can4hou6joeng4/boss-harness/blob/main/"
PR_REQUIRED = ("Closes #", "type(scope): 中文描述")
BODY_ITEM = re.compile(r"^  - type:[ \t]*(\S+)[ \t]*$")
CONTACT_ITEM = re.compile(r"^  - name:[ \t]*(.*)$")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _top_level(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{key}:[ \t]*(\S.*)$", text)
    return match.group(1).strip() if match else None


def _body_items(body: str) -> list[tuple[str, str]]:
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in body.splitlines():
        match = BODY_ITEM.match(line)
        if match is not None:
            current = [match.group(1), ""]
            items.append(current)
        elif current is not None:
            current[1] += line + "\n"
    return [(kind, block) for kind, block in items]


def _form_problems(text: str, label: str = "表单") -> list[str]:
    problems: list[str] = []
    for key in ("name", "description"):
        if _top_level(text, key) is None:
            problems.append(f"{label} 缺少 {key}")
    body = re.search(r"(?m)^body:[ \t]*$", text)
    if body is None:
        problems.append(f"{label} 缺少 body")
        return problems
    items = _body_items(text[body.end():])
    raw_items = len(re.findall(r"(?m)^  - ", text[body.end():]))
    if raw_items != len(items):
        problems.append(f"{label} 有无法解析的控件条目")
    if not items:
        problems.append(f"{label} 的 body 没有控件")
        return problems
    required = 0
    for index, (kind, block) in enumerate(items, 1):
        where = f"{label} 第 {index} 个控件"
        if kind not in ALLOWED_TYPES:
            problems.append(f"{where} 使用未知类型 {kind}")
        elif kind != "markdown":
            if re.search(r"(?m)^    id:[ \t]*\S", block) is None:
                problems.append(f"{where}（{kind}）缺少 id")
            if re.search(r"(?m)^    attributes:", block) is None:
                problems.append(f"{where}（{kind}）缺少 attributes")
        if re.search(r"(?m)^      required:[ \t]*true[ \t]*$", block):
            required += 1
    if required == 0:
        problems.append(f"{label} 没有任何必填控件")
    return problems


def _contact_items(text: str) -> list[tuple[str, str]]:
    items: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        match = CONTACT_ITEM.match(line)
        if match is not None:
            current = [match.group(1).strip(), ""]
            items.append(current)
        elif current is not None:
            current[1] += line + "\n"
    return [(name, block) for name, block in items]


def _contact_problems(text: str, label: str = CONFIG) -> list[str]:
    problems: list[str] = []
    if re.search(r"(?m)^blank_issues_enabled:[ \t]*(true|false)[ \t]*$", text) is None:
        problems.append(f"{label} 缺少布尔 blank_issues_enabled")
    if re.search(r"(?m)^contact_links:[ \t]*$", text) is None:
        problems.append(f"{label} 缺少 contact_links")
        return problems
    items = _contact_items(text)
    raw_items = len(re.findall(r"(?m)^  - ", text))
    if raw_items != len(items):
        problems.append(f"{label} 有无法解析的联系入口")
    if not items:
        problems.append(f"{label} 的 contact_links 为空")
    for index, (name, block) in enumerate(items, 1):
        where = f"{label} 第 {index} 个联系入口"
        if not name:
            problems.append(f"{where} 缺少 name")
        if re.search(r"(?m)^    about:[ \t]*\S", block) is None:
            problems.append(f"{where} 缺少 about")
        match = re.search(r"(?m)^    url:[ \t]*(\S+)[ \t]*$", block)
        if match is None:
            problems.append(f"{where} 缺少 url")
            continue
        url = match.group(1)
        if not url.startswith("https://"):
            problems.append(f"{where} 不是 https URL：{url}")
            continue
        if url.startswith(BLOB_PREFIX):
            target = unquote(url[len(BLOB_PREFIX):].split("#", 1)[0])
            if not (ROOT / target).is_file():
                problems.append(f"{where} 指向不存在的文件：{target}")
    return problems


def _pr_problems(text: str, label: str = PR_TEMPLATE) -> list[str]:
    return [f"{label} 缺少 {phrase}" for phrase in PR_REQUIRED if phrase not in text]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"Issue 表单边界变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    problems: list[str] = []
    for relative in FORMS:
        problems.extend(_form_problems(_read(relative), relative))
    problems.extend(_contact_problems(_read(CONFIG), CONFIG))
    problems.extend(_pr_problems(_read(PR_TEMPLATE), PR_TEMPLATE))
    if problems:
        raise ValueError("Issue 表单边界变化：" + "；".join(problems))
    return len(FORMS) * 6 + 6 + len(PR_REQUIRED)


def _clean_form() -> str:
    return (
        "name: 示例\n"
        "description: 示例表单\n"
        "body:\n"
        "  - type: markdown\n"
        "    attributes:\n"
        "      value: |\n"
        "        说明。\n"
        "  - type: textarea\n"
        "    id: scenario\n"
        "    attributes:\n"
        "      label: 场景\n"
        "    validations:\n"
        "      required: true\n"
    )


def _clean_config() -> str:
    return (
        "blank_issues_enabled: true\n"
        "contact_links:\n"
        "  - name: 支持\n"
        f"    url: {BLOB_PREFIX}SUPPORT.md\n"
        "    about: 先按文档分流。\n"
    )


def _expect_count(found: list[str], expected: int, label: str) -> int:
    return _expect_value(len(found), expected, label)


def _check_behaviors() -> int:
    checked = 0
    form = _clean_form()
    checked += _expect_count(_form_problems(form), 0, "干净表单")
    checked += _expect_count(_form_problems(form.replace("description: 示例表单\n", "")), 1,
                             "缺少 description")
    checked += _expect_count(_form_problems(form.replace("type: textarea", "type: calendar")), 1,
                             "未知控件类型")
    checked += _expect_count(_form_problems(form.replace("    id: scenario\n", "")), 1,
                             "缺少 id")
    checked += _expect_count(_form_problems(form.replace("      required: true", "      required: false")), 1,
                             "没有必填控件")
    checked += _expect_count(_form_problems(form.replace("body:", "fields:")), 1, "缺少 body")
    config = _clean_config()
    checked += _expect_count(_contact_problems(config), 0, "干净联系入口")
    checked += _expect_count(_contact_problems(config.replace("    about: 先按文档分流。\n", "")), 1,
                             "缺少 about")
    checked += _expect_count(_contact_problems(config.replace("https://", "http://")), 1,
                             "非 https 链接")
    checked += _expect_count(_contact_problems(config.replace("SUPPORT.md", "docs/NOPE.md")), 1,
                             "失效 blob 路径")
    checked += _expect_count(_contact_problems(config.replace("blank_issues_enabled: true\n", "")), 1,
                             "缺少 blank_issues_enabled")
    template = "标题使用单行 `type(scope): 中文描述`；用单独一行 `Closes #N` 关联 Issue。\n"
    checked += _expect_count(_pr_problems(template), 0, "干净 PR 模板")
    checked += _expect_count(_pr_problems(template.replace("Closes #", "")), 1,
                             "缺少 Closes")
    checked += _expect_count(_pr_problems(template.replace("type(scope): 中文描述", "")), 1,
                             "缺少标题约定")
    checked += _expect_count(_form_problems(form.replace("  - type: textarea", "  - label: 控件")), 1,
                             "无法解析的控件条目")
    checked += _expect_count(_contact_problems(config.replace("  - name: 支持", "  - label: 支持")), 2,
                             "无法解析的联系入口")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_issue_forms.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_issue_forms.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少 Issue 表单检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"Issue 表单边界一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
