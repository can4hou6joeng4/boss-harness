#!/usr/bin/env python3
"""核对工作区空状态与读取失败都给出可点的恢复操作。

「最近聊天」无会话、筛选无匹配、「资料库」筛选无匹配与工具清单读取失败
或为空都属于没有内容可展示的状态。只有一行文字时用户得自己回头找入口、
手动清空搜索框或重启应用；这里固定每处状态的数据标记、文案与按钮语义，
并要求样式保留紧凑布局、操作列与按钮间距。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES = "apps/desktop/src/renderer/src/shell/WorkspacePages.tsx"
SHELL = "apps/desktop/src/renderer/src/shell/AppShell.tsx"
STYLES = "apps/desktop/src/renderer/src/styles/replica.css"
DOCS = "docs/TECHNICAL_REFERENCE.md"

MARKER = re.compile(r'data-(recents|library)-empty="([a-z-]+)"')
EMPTY_STATES = (
    ("recents-none", "最近聊天无会话", ("还没有聊天", "开始一个任务", "onClick={onNewTask}")),
    ("recents-no-match", "最近聊天无匹配", ("没有找到匹配的聊天", "清空筛选", 'onClick={() => setQuery("")}')),
    ("library-no-match", "资料库无匹配", ("没有匹配的文件或来源", "清空筛选", 'onClick={() => setLibraryQuery("")}')),
    ("library-no-file-match", "资料库文件无匹配", ("没有匹配的文件", "清空筛选", 'onClick={() => setLibraryQuery("")}')),
    ("library-no-source-match", "资料库来源无匹配", ("没有匹配的来源", "清空筛选", 'onClick={() => setLibraryQuery("")}')),
)
TOOL_MARKERS = (
    ('toolCatalogState === "error" ? <div', "工具清单读取失败态", ("重新读取", "onClick={onRefreshTools}")),
    ('toolCatalogState === "empty" ? <div className="page-tool-empty">', "工具清单空态", ("重新读取", "onClick={onRefreshTools}")),
)
NEXT_TOOL = ': toolCatalogState ==='
SHELL_FRAGMENTS = (
    "const [toolRefresh, setToolRefresh] = useState(0);",
    "[props.harnessUp, toolRefresh]",
    "onRefreshTools={() => setToolRefresh(previous => previous + 1)}",
)
STYLE_FRAGMENTS = (
    ".page-empty.recent-empty { min-height: 280px; }",
    ".page-empty-action { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }",
    ".page-tool-empty .subtle-button { margin-top: 10px; display: flex; width: fit-content; }",
)
SEGMENT_LIMIT = 900


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _segments(text: str) -> dict[str, str]:
    matches = list(MARKER.finditer(text))
    found: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        found[f"{match.group(1)}-{match.group(2)}"] = text[match.start():min(end, match.start() + SEGMENT_LIMIT)]
    return found


def _problems(text: str) -> list[str]:
    found: list[str] = []
    segments = _segments(text)
    for marker, label, fragments in EMPTY_STATES:
        segment = segments.get(marker)
        if segment is None:
            found.append(f"{label}缺少数据标记 {marker}")
            continue
        missing = [fragment for fragment in fragments if fragment not in segment]
        if missing:
            found.append(f"{label}缺少：" + "、".join(missing))
    return found


def _tool_problems(text: str) -> list[str]:
    found: list[str] = []
    for marker, label, fragments in TOOL_MARKERS:
        start = text.find(marker)
        if start < 0:
            found.append(f"{label}缺少分支 {marker}")
            continue
        boundary = text.find(NEXT_TOOL, start + len(marker))
        segment = text[start:boundary if boundary > 0 else start + SEGMENT_LIMIT]
        missing = [fragment for fragment in fragments if fragment not in segment]
        if missing:
            found.append(f"{label}缺少：" + "、".join(missing))
    return found


def _fragment_problems(text: str, fragments: tuple[str, ...], label: str) -> list[str]:
    return [f"{label}缺少：" + fragment for fragment in fragments if fragment not in text]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"工作区空状态变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_behaviors() -> int:
    sample = (
        '<div className="page-empty-note page-empty-action" data-recents-empty="no-match">'
        '<p>没有找到匹配的聊天。</p>'
        '<button type="button" onClick={() => setQuery("")}>清空筛选</button></div>\n'
        '<div className="page-empty recent-empty" data-recents-empty="none"><h2>还没有聊天</h2>'
        '<button className="subtle-button" onClick={onNewTask}>开始一个任务</button></div>\n'
        '<div className="page-empty-note page-empty-action" data-library-empty="no-match">'
        '<p>没有匹配的文件或来源。</p>'
        '<button type="button" onClick={() => setLibraryQuery("")}>清空筛选</button></div>\n'
        '<div className="page-empty-note page-empty-action" data-library-empty="no-file-match">'
        '<p>没有匹配的文件。</p>'
        '<button type="button" onClick={() => setLibraryQuery("")}>清空筛选</button></div>\n'
        '<div className="page-empty-note page-empty-action" data-library-empty="no-source-match">'
        '<p>没有匹配的来源。</p>'
        '<button type="button" onClick={() => setLibraryQuery("")}>清空筛选</button></div>\n'
    )
    tool_sample = (
        '{toolCatalogState === "error" ? <div>工具清单读取失败。'
        '<button type="button" onClick={onRefreshTools}>重新读取</button></div>'
        ' : toolCatalogState === "empty" ? <div className="page-tool-empty">内核当前没有声明可用工具。'
        '<button type="button" onClick={onRefreshTools}>重新读取</button></div>'
        ' : <div>连接尚未就绪</div>}'
    )
    checked = 0
    checked += _expect_value(len(_problems(sample)), 0, "干净样本")
    checked += _expect_value(
        len(_problems(sample.replace('>清空筛选</button></div>\n<div className="page-empty recent-empty"',
                                      '></button></div>\n<div className="page-empty recent-empty"'))),
        1, "缺少最近聊天清空按钮")
    checked += _expect_value(
        len(_problems(sample.replace('onClick={() => setQuery("")}', 'onClick={() => setFile(null)}'))),
        1, "最近聊天清空按钮用错设置函数")
    checked += _expect_value(
        len(_problems(sample.replace(' onClick={onNewTask}', ''))), 1, "无会话空态缺少开始入口")
    checked += _expect_value(
        len(_problems(sample.replace('data-library-empty="no-match"', 'data-library-empty="none"'))),
        1, "缺少资料库空状态标记")
    checked += _expect_value(
        len(_problems(sample.replace(' data-library-empty="no-match"', ''))), 1, "资料库标记被删除")
    checked += _expect_value(
        len(_problems(sample.replace(
            '<p>没有匹配的文件。</p><button type="button" onClick={() => setLibraryQuery("")}>清空筛选</button>',
            '<p>没有匹配的文件。</p>'))),
        1, "资料库文件无匹配缺少清空筛选")
    checked += _expect_value(
        len(_problems(sample.replace(
            '<p>没有匹配的来源。</p><button type="button" onClick={() => setLibraryQuery("")}>清空筛选</button>',
            '<p>没有匹配的来源。</p><button type="button" onClick={() => setQuery("")}>清空筛选</button>'))),
        1, "资料库来源无匹配用错设置函数")
    checked += _expect_value(len(_tool_problems(tool_sample)), 0, "干净工具样本")
    checked += _expect_value(
        len(_tool_problems(tool_sample.replace(
            '<button type="button" onClick={onRefreshTools}>重新读取</button></div> : toolCatalogState === "empty"',
            '</div> : toolCatalogState === "empty"'))),
        1, "工具清单读取失败缺少重新读取")
    checked += _expect_value(
        len(_tool_problems(tool_sample.replace(
            '内核当前没有声明可用工具。<button type="button" onClick={onRefreshTools}>重新读取</button>',
            '内核当前没有声明可用工具。'))),
        1, "工具清单空态缺少重新读取")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_workspace_empty_states.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_workspace_empty_states.py")
    if "共 32 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_workspace_empty_states.py 检查 32 项结构、11 项行为")
    return 2


def check_workspace_empty_states() -> tuple[int, int]:
    pages = _read(PAGES)
    shell = _read(SHELL)
    styles = _read(STYLES)
    problems = _problems(pages) + _tool_problems(pages)
    problems += _fragment_problems(shell, SHELL_FRAGMENTS, SHELL)
    problems += _fragment_problems(styles, STYLE_FRAGMENTS, STYLES)
    if problems:
        raise ValueError("工作区空状态不一致：" + "；".join(problems))
    structure = len(EMPTY_STATES) * 4 + len(STYLE_FRAGMENTS) + len(TOOL_MARKERS) * 3 + len(SHELL_FRAGMENTS)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_workspace_empty_states()
    except (OSError, ValueError) as error:
        print(f"工作区空状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工作区空态一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
