#!/usr/bin/env python3
"""核对面向用户与贡献者的 Markdown 相对链接与页内锚点。"""

from __future__ import annotations

import re
from pathlib import Path
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "README.md", "CONTRIBUTING.md", "RELEASING.md", "SECURITY.md", "SUPPORT.md",
    "CODE_OF_CONDUCT.md", "UPSTREAM.md", "CHANGELOG.md", "docs/README.md",
    "docs/USER_GUIDE.md", "docs/DESKTOP_GUIDE.md", "docs/TECHNICAL_REFERENCE.md",
    "docs/STATUS.md", "docs/changelog-rc15-details.md",
)
INDEX = "docs/README.md"
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DEFINITION = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
EXTERNAL = ("http://", "https://", "mailto:", "tel:")
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$", re.MULTILINE)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CLOSING_HASHES = re.compile(r"[ \t]+#+$")
HTML_TAG = re.compile(r"<[^>]+>")
LINK_TEXT = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


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


def _links(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {path.relative_to(ROOT).as_posix()}") from None
    # 示例代码与行内代码里的方括号不是文档链接。
    text = _strip_fences(text, path.relative_to(ROOT).as_posix())
    text = re.sub(r"`[^`\n]*`", "", text)
    return LINK.findall(text) + DEFINITION.findall(text)


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


def check_docs_links() -> tuple[int, int, int]:
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
    return checked, anchors, _check_index()


def main() -> int:
    try:
        checked, anchors, indexed = check_docs_links()
    except ValueError as error:
        print(f"文档链接核对失败，{error}", file=sys.stderr)
        return 2
    print(f"文档相对链接一致：{checked} 个链接、{anchors} 个页内锚点；索引覆盖 {indexed} 篇文档")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
