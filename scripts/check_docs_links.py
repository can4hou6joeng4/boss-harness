#!/usr/bin/env python3
"""核对面向用户与贡献者的 Markdown 相对链接。"""

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
    "docs/changelog-rc15-details.md",
)
INDEX = "docs/README.md"
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DEFINITION = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "#")


def _links(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {path.relative_to(ROOT).as_posix()}") from None
    # 示例代码与行内代码里的方括号不是文档链接。
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    return LINK.findall(text) + DEFINITION.findall(text)


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


def check_docs_links() -> tuple[int, int]:
    broken: list[str] = []
    checked = 0
    for relative in SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise ValueError(f"缺少文档 {relative}")
        for raw in _links(path):
            target = raw.strip()
            if not target or target.startswith(EXTERNAL):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            checked += 1
            if not (path.parent / target).exists():
                broken.append(f"{relative} -> {target}")
    if broken:
        raise ValueError("相对链接不存在：" + "；".join(sorted(broken)))
    return checked, _check_index()


def main() -> int:
    try:
        checked, indexed = check_docs_links()
    except ValueError as error:
        print(f"文档链接核对失败，{error}", file=sys.stderr)
        return 2
    print(f"文档相对链接一致：{checked} 个链接；索引覆盖 {indexed} 篇文档")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
