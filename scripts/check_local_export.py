#!/usr/bin/env python3
"""核对本地 Markdown 导出的标题收敛与拼装顺序。

内核不支持 `threadExport` 时，标题栏回退到渲染层 `exportMarkdown`。标题属于元数据：
必须折叠连续空白、去除首尾空白、按共享 `safeSlice` 限制 200 个字符并在空标题时回退，
不能把换行或超长标题带进 `#` 标题行。正文、段落、列表与工具复制文本保持原有顺序，
不改写用户或模型自己的 Markdown 正文。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "apps/desktop/src/renderer/src/data/exportMarkdown.ts"

EXPORT_FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    'import { messageCopyText } from "./messageCopy";',
    'const exportedTitle = safeSlice(title.replace(/\\s+/g, " ").trim(), 200) || "当前会话";',
    "const sections = messages.map(message => {",
    "const tool = message.toolUse || message.approval",
    "? messageCopyText({ toolUse: message.toolUse, approval: message.approval })",
    "const body = [",
    "message.content,",
    "...(message.paragraphs ?? []),",
    "...(message.bullets ?? []).map(line => `- ${line}`),",
    "tool,",
    '].filter(Boolean).join("\\n\\n");',
    'return `## ${message.role === "user" ? "你" : "BOSS Harness"}\\n\\n${body}`;',
    'return `# ${exportedTitle}\\n\\n${sections.join("\\n\\n")}`;',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_local_export() -> int:
    export = _read(EXPORT)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    # 标题先收敛，再进入消息拼装与最终模板。
    checked += _ordered(
        (
            'const exportedTitle = safeSlice(title.replace(/\\s+/g, " ").trim(), 200) || "当前会话";',
            "const sections = messages.map(message => {",
            "const tool = message.toolUse || message.approval",
            "const body = [",
            "message.content,",
            "...(message.paragraphs ?? []),",
            "...(message.bullets ?? []).map(line => `- ${line}`),",
            "tool,",
            'return `## ${message.role === "user" ? "你" : "BOSS Harness"}\\n\\n${body}`;',
            'return `# ${exportedTitle}\\n\\n${sections.join("\\n\\n")}`;',
        ),
        export,
        EXPORT,
    )
    # 反向断言：标题不得直接进入模板，也不得绕过共享截断。
    for forbidden in ("`# ${title}`", "title.slice(", "substring("):
        if forbidden in export:
            raise ValueError(f"{EXPORT} 的本地导出不得包含 {forbidden}")
    return checked + 1


def main() -> int:
    try:
        checked = check_local_export()
    except ValueError as error:
        print(f"本地导出核对失败，{error}", file=sys.stderr)
        return 2
    print(f"本地导出一致：{checked} 项标题收敛、拼装顺序与反向防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
