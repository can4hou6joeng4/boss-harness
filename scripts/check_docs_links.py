#!/usr/bin/env python3
"""核对面向用户与贡献者的 Markdown 相对链接、页内锚点与检查脚本说明覆盖。"""

from __future__ import annotations

import re
from pathlib import Path
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "README.md", "SETUP.md", "CONTRIBUTING.md", "RELEASING.md", "SECURITY.md", "SUPPORT.md",
    "CODE_OF_CONDUCT.md", "UPSTREAM.md", "CHANGELOG.md", "docs/README.md",
    "docs/USER_GUIDE.md", "docs/DESKTOP_GUIDE.md", "docs/TECHNICAL_REFERENCE.md",
    "docs/STATUS.md", "docs/changelog-rc15-details.md",
    "harness/README.md", ".github/PULL_REQUEST_TEMPLATE.md",
)
INDEX = "docs/README.md"
ROOT_DOCUMENTS = ("SETUP.md",)
REFERENCE = "docs/TECHNICAL_REFERENCE.md"
SCRIPT_HEADING = re.compile(r"^### `(check_[A-Za-z0-9_]+\.py)`[ \t]*$", re.MULTILINE)
INDEX_SECTION = "## 构建前检查"
INDEX_HEADER = "| 领域 | 脚本 |"
INDEX_LINK = re.compile(r"\[`(check_[A-Za-z0-9_]+\.py)`\]\(#[^)]*\)")
MARKDOWN_DIRS = ("", "docs", "harness", ".github")
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DEFINITION = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
EXTERNAL = ("http://", "https://", "mailto:", "tel:")
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CLOSING_HASHES = re.compile(r"[ \t]+#+$")
HTML_TAG = re.compile(r"<[^>]+>")
LINK_TEXT = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_fences(text: str, name: str) -> str:
    """移除 ``` 与 ~~~ 代码围栏；未闭合时拒绝整份文档。"""
    kept: list[str] = []
    fence: str | None = None
    width = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        match = FENCE.match(content)
        if fence is None:
            if match is None:
                kept.append(line)
                continue
            marker, info = match.groups()
            if marker[0] == "`" and "`" in info:
                kept.append(line)
                continue
            fence = marker[0]
            width = len(marker)
            kept.append("\n" if line.endswith("\n") else "")
            continue
        if (match is not None and match.group(1)[0] == fence
                and len(match.group(1)) >= width and not match.group(2).strip()):
            fence = None
        kept.append("\n" if line.endswith("\n") else "")
    if fence is not None:
        raise ValueError(f"{name} 存在未闭合的代码围栏")
    return "".join(kept)


def _links_from(text: str, name: str) -> list[str]:
    # 示例代码与行内代码里的方括号不是文档链接。
    text = _strip_fences(text, name)
    text = COMMENT.sub("", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    return LINK.findall(text) + DEFINITION.findall(text)


def _links(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {path.relative_to(ROOT).as_posix()}") from None
    return _links_from(text, path.relative_to(ROOT).as_posix())


def _section(text: str, heading: str, name: str) -> str:
    if heading not in text:
        raise ValueError(f"{name} 缺少章节：{heading}")
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def _slug(text: str) -> str:
    """按 GitHub 标题锚点的常用规则生成 slug。"""
    text = CLOSING_HASHES.sub("", text)
    text = HTML_TAG.sub("", text)
    text = LINK_TEXT.sub(r"\1", text)
    text = text.replace("`", "").lower().strip()
    # 保留字母、数字、空格、连字符与下划线；其余标点与符号不进入锚点。
    text = "".join(character for character in text
                   if character.isalnum() or character in " _-")
    return text.replace(" ", "-")


def _headings(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {path.relative_to(ROOT).as_posix()}") from None
    text = _strip_fences(text, path.relative_to(ROOT).as_posix())
    text = COMMENT.sub("", text)
    slugs: set[str] = set()
    for match in HEADING.finditer(text):
        base = _slug(match.group(1))
        if not base:
            continue
        slug = base
        suffix = 0
        while slug in slugs:
            suffix += 1
            slug = f"{base}-{suffix}"
        slugs.add(slug)
    return slugs


def _check_index() -> int:
    path = ROOT / INDEX
    linked = set()
    for raw in _links(path):
        if raw.startswith(EXTERNAL):
            continue
        target = unquote(raw.split("#", 1)[0])
        if target:
            linked.add((path.parent / target).resolve())
    documents = sorted((ROOT / "docs").glob("*.md"))
    missing = [document.name for document in documents
               if document.name != "README.md" and document.resolve() not in linked]
    if missing:
        raise ValueError(f"{INDEX} 未索引：" + "、".join(missing))
    return len(documents) - 1


def _check_root_navigation() -> int:
    """根目录引导文档必须进入首页导航表与文档索引，索引检查只覆盖 docs/*.md。"""
    missing = []
    for page in ("README.md", INDEX):
        path = ROOT / page
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            raise ValueError(f"无法读取 {page}") from None
        scope = _section(text, "## 项目导航", page) if page == "README.md" else text
        linked = set()
        for raw in _links_from(scope, page):
            if raw.startswith(EXTERNAL):
                continue
            target = unquote(raw.split("#", 1)[0])
            if target:
                linked.add((path.parent / target).resolve())
        for name in ROOT_DOCUMENTS:
            if (ROOT / name).resolve() not in linked:
                missing.append(f"{page} → {name}")
    if missing:
        raise ValueError("根文档缺少导航入口：" + "、".join(missing))
    return len(ROOT_DOCUMENTS) * 2


def _check_coverage() -> int:
    """仓库内约定位置的 Markdown 必须全部登记，避免新增文档漏检。"""
    found: set[str] = set()
    for directory in MARKDOWN_DIRS:
        base = ROOT / directory if directory else ROOT
        for path in base.glob("*.md"):
            found.add(path.relative_to(ROOT).as_posix())
    missing = sorted(found - set(SOURCES))
    if missing:
        raise ValueError("文档检查未覆盖：" + "、".join(missing))
    absent = sorted(set(SOURCES) - found)
    if absent:
        raise ValueError("登记文档不在约定位置：" + "、".join(absent))
    return len(found)


def _reference_text() -> str:
    try:
        return (ROOT / REFERENCE).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {REFERENCE}") from None


def _index_names(text: str) -> list[str]:
    """「构建前检查」索引表列出的脚本名；表外正文里的脚本链接不计入。"""
    section_text = _section(COMMENT.sub("", _strip_fences(text, REFERENCE)),
                            INDEX_SECTION, REFERENCE)
    names: list[str] = []
    in_table = False
    for line in section_text.splitlines():
        if not in_table:
            if line.strip() == INDEX_HEADER:
                in_table = True
            continue
        if not line.lstrip().startswith("|"):
            break
        names.extend(INDEX_LINK.findall(line))
    if not in_table:
        raise ValueError(f"{REFERENCE} 缺少索引表：{INDEX_HEADER}")
    return names


def _index_problems(names: list[str], scripts: set[str]) -> list[str]:
    """索引表与脚本集合的差异：缺项、未知脚本、重复条目分别列出。"""
    problems: list[str] = []
    missing = sorted(scripts - set(names))
    unknown = sorted(set(names) - scripts)
    repeated = sorted({name for name in names if names.count(name) > 1})
    if missing:
        problems.append("索引表缺少 " + "、".join(missing))
    if unknown:
        problems.append("索引表列出不存在的脚本 " + "、".join(unknown))
    if repeated:
        problems.append("索引表重复 " + "、".join(repeated))
    return problems


def _index_self_check() -> int:
    """用合成表格核对缺项 / 未知 / 重复 / 完整四种情形，表外链接不计入。"""
    alpha = "[`check_alpha.py`](#check_alphapy)"
    beta = "[`check_beta.py`](#check_betapy)"
    gamma = "[`check_gamma.py`](#check_gammapy)"
    scripts = {"check_alpha.py", "check_beta.py"}
    prose = f"\n正文提到 {beta} 不算索引。\n"

    def sample(rows: str) -> str:
        return f"{INDEX_SECTION}\n\n{INDEX_HEADER}\n| --- | --- |\n| 示例 | {rows} |\n{prose}"

    cases = (
        (sample(f"{alpha}、{beta}"), ()),
        (sample(alpha), ("索引表缺少 check_beta.py",)),
        (sample(f"{alpha}、{beta}、{gamma}"), ("索引表列出不存在的脚本 check_gamma.py",)),
        (sample(f"{alpha}、{beta}、{beta}"), ("索引表重复 check_beta.py",)),
    )
    for text, expected in cases:
        problems = tuple(_index_problems(_index_names(text), scripts))
        if problems != expected:
            raise ValueError(f"索引表自检未按预期工作：得到 {problems!r}，期望 {expected!r}")
    return len(cases)


def _check_reference_index() -> int:
    """「构建前检查」索引表必须覆盖全部脚本且不列未知或重复条目。"""
    names = _index_names(_reference_text())
    scripts = {path.name for path in (ROOT / "scripts").glob("check_*.py")}
    if not scripts:
        raise ValueError("scripts 下没有 check_*.py")
    problems = _index_problems(names, scripts)
    if problems:
        raise ValueError(f"{REFERENCE} 的索引表不一致：" + "；".join(problems))
    _index_self_check()
    return len(scripts)


def _check_script_reference() -> int:
    """检查脚本的说明只在技术参考维护一份：每个脚本恰有一个同名小节。"""
    text = _reference_text()
    documented = SCRIPT_HEADING.findall(COMMENT.sub("", _strip_fences(text, REFERENCE)))
    scripts = {path.name for path in (ROOT / "scripts").glob("check_*.py")}
    if not scripts:
        raise ValueError("scripts 下没有 check_*.py")
    missing = sorted(scripts - set(documented))
    unknown = sorted(set(documented) - scripts)
    repeated = sorted({name for name in documented if documented.count(name) > 1})
    if missing or unknown or repeated:
        raise ValueError(
            f"{REFERENCE} 的检查脚本小节不一致：缺少 " + ("、".join(missing) or "无")
            + "；脚本不存在 " + ("、".join(unknown) or "无")
            + "；重复 " + ("、".join(repeated) or "无")
        )
    return len(scripts)


def check_docs_links() -> tuple[int, int, int, int, int, int, int]:
    broken: list[str] = []
    bad_anchors: list[str] = []
    checked = 0
    anchors = 0
    for relative in SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise ValueError(f"缺少文档 {relative}")
        for raw in _links(path):
            target = raw.strip()
            if not target or target.startswith(EXTERNAL):
                continue
            path_part, _, fragment = unquote(target).partition("#")
            checked += 1
            destination = path.parent / path_part if path_part else path
            if path_part and not destination.exists():
                broken.append(f"{relative} -> {path_part}")
                continue
            if not fragment:
                continue
            anchors += 1
            if destination.suffix.lower() != ".md" or not destination.is_file():
                continue
            if fragment not in _headings(destination):
                bad_anchors.append(f"{relative} -> {target}")
    if broken:
        raise ValueError("相对链接不存在：" + "；".join(sorted(broken)))
    if bad_anchors:
        raise ValueError("页内锚点不存在：" + "；".join(sorted(bad_anchors)))
    return (checked, anchors, _check_index(), _check_coverage(),
            _check_script_reference(), _check_root_navigation(),
            _check_reference_index())


def main() -> int:
    try:
        (checked, anchors, indexed, covered, scripts, root_entries,
         table_scripts) = check_docs_links()
    except ValueError as error:
        print(f"文档链接核对失败，{error}", file=sys.stderr)
        return 2
    print(
        f"文档相对链接一致：{checked} 个链接、{anchors} 个页内锚点；"
        f"索引覆盖 {indexed} 篇文档，根文档入口 {root_entries} 处，"
        f"检查覆盖 {covered} 篇 Markdown，{scripts} 个检查脚本均有说明小节，"
        f"索引表覆盖 {table_scripts} 个脚本"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
