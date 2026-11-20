#!/usr/bin/env python3
"""核对会话导出 Markdown 的定界与代码围栏。

导出的 Markdown 会被用户放进工单、聊天或代码托管页面渲染。用户与模型正文可能包含
反引号、换行或整行围栏，元数据还可能包含平台返回的任意文本：正文只能走按最长反引号
动态加长的代码围栏，单行元数据必须经 `_inline_text` 转义链接、原生 HTML、强调与表格
定界符，标识符再包成行内代码。这里固定这些入口与围栏算法，避免新增字段把可执行的
Markdown 拼进导出。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"

EXPORT_FRAGMENTS = (
    "def _code_text(value: Any) -> str:",
    '"""Neutralise backticks and line breaks for a code span or escaped HTML text."""',
    'return str(value).replace("`", "\'").replace("\\r", " ").replace("\\n", " ")',
    "_INLINE_ESCAPES = str.maketrans({",
    r'    "\\": "\\\\",',
    r'    "[": "\\[",',
    r'    "]": "\\]",',
    r'    "<": "\\<",',
    r'    ">": "\\>",',
    r'    "*": "\\*",',
    r'    "_": "\\_",',
    r'    "~": "\\~",',
    r'    "|": "\\|",',
    "def _inline_text(value: Any) -> str:",
    '"""Escape inline Markdown delimiters in a single line of platform/user-supplied text."""',
    "return _code_text(value).translate(_INLINE_ESCAPES)",
    "def _inline_code(value: Any) -> str:",
    '"""A code span that cannot be broken by backticks or line breaks in platform-supplied text."""',
    'return "`" + _code_text(value) + "`"',
    "def _fence(text: str, language: str = \"text\") -> str:",
    'longest = max((len(run) for run in re.findall(r"`+|~+", text)), default=0)',
    'marker = "`" * max(3, longest + 1)',
    'return f"{marker}{language}\\n{text}\\n{marker}"',
    # 回合元数据：标识符走行内代码，其余单行文本经 _inline_text。
    "_inline_code(unit['turnId'])",
    "f\"开始：{_inline_text(unit['startedAt'] or '—')}\"",
    "f\"结束：{_inline_text(unit['completedAt'] or '—')}\"",
    "_inline_text(unit['provider'] or '—')",
    "_inline_text(unit['model'])",
    "_inline_code(unit['failureCode'])",
    '"、".join(_inline_code(item) for item in unit["skillIds"])',
    # 用户输入、模型输出与摘要正文：整段代码围栏。
    'parts = [title, "", _fence(unit["text"] or "（空）")]',
    '_inline_text(a[\'mediaType\'] or \'未知类型\')',
    '_inline_text(unit[\'status\'])',
    'parts = [f"### 模型输出（模型判断，未经平台核实）{status}", "", _fence(unit["text"] or "（无文本）")]',
    # 工具调用：名称、状态、错误码与来源全部经单行中和。
    "_inline_code(unit['toolName'])",
    "_inline_code(execution['state'])",
    "_inline_code(unit['status'])",
    "_inline_text(approval['decidedAt'])",
    "_inline_code(unit['errorCode'])",
    "_inline_text(unit['recoveryAction'])",
    'f"{key}={_inline_text(value)}"',
    'f"{_inline_text(key)}={json.dumps(value, ensure_ascii=False)}"',
    '_inline_text("；".join(facts))',
    # 结果明文：只在 included 分支以 json 围栏写入。
    'lines.append(_fence(result["text"], "json"))',
    # 摘要：生成时间、模型、任务 id 均为单行中和，正文走围栏。
    "_inline_text(unit['summaryModel'])",
    'extra += f"；摘要任务 {_inline_text(unit[\'summaryJobId\'])}"',
    "_inline_text(unit.get('createdAt') or '—')",
    '_fence(unit["text"] or "（空）")])',
    # 文档头：会话 id 为行内代码，标题中和后回退为破折号；摘要任务明细逐行中和。
    "_inline_code(meta['threadId'])",
    "_inline_text(meta['title']) or '—'",
    "header += [f\"  - {_inline_text('；'.join(_summary_job_facts(job)))}\" for job in shown]",
    "_inline_code(issue[\"entryId\"])",
    "_inline_text(issue['reason'])",
    # 队列：标题 id 行内代码，事实按 code 模式逐项中和，输入走围栏。
    'f"队列项 {_inline_code(item[\'queueId\'])} · "',
    'facts.append("失败码：" + (_inline_code(item["failureCode"]) if code else str(item["failureCode"])))',
    'values = [_inline_code(value) if code else value for value in item["skillIds"]]',
    "facts.extend(_inline_text(fact) if code else fact",
    'parts += [_fence(item["input"] or "（空）"), ""]',
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


def check_export_markdown() -> int:
    export = _read(EXPORT)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    # 辅助函数：先归一代码文本，再为正文转义行内定界符，最后按最长反引号计算围栏长度。
    checked += _ordered(
        (
            "def _code_text(value: Any) -> str:",
            'return str(value).replace("`", "\'").replace("\\r", " ").replace("\\n", " ")',
            "_INLINE_ESCAPES = str.maketrans({",
            r'    "|": "\\|",',
            "def _inline_text(value: Any) -> str:",
            "return _code_text(value).translate(_INLINE_ESCAPES)",
            "def _inline_code(value: Any) -> str:",
            'return "`" + _code_text(value) + "`"',
            "def _fence(text: str, language: str = \"text\") -> str:",
            'longest = max((len(run) for run in re.findall(r"`+|~+", text)), default=0)',
            'marker = "`" * max(3, longest + 1)',
            'return f"{marker}{language}\\n{text}\\n{marker}"',
        ),
        export,
        EXPORT,
    )
    # 用户输入与模型输出：正文围栏之前先写小标题，附件元数据逐项中和。
    checked += _ordered(
        (
            'if kind == "userInput":',
            'title = "### 用户输入" + ("（来自消息队列）" if unit["queued"] else "")',
            'parts = [title, "", _fence(unit["text"] or "（空）")]',
            '_inline_text(a[\'mediaType\'] or \'未知类型\')',
            'if kind == "modelOutput":',
            '_inline_text(unit[\'status\'])',
            '_fence(unit["text"] or "（无文本）")]',
        ),
        export,
        EXPORT,
    )
    # 工具结果：明文只在 included 分支进入围栏，其余分支只写中和后的事实。
    checked += _ordered(
        (
            'elif result["included"]:',
            'lines.append("- 结果明文（平台事实；含候选人个人信息，请勿外传）：")',
            'lines.append(_fence(result["text"], "json"))',
            'lines.append("- 结果（仅结构与状态，明文已省略）：" + _inline_text("；".join(facts)))',
        ),
        export,
        EXPORT,
    )
    # 摘要正文：生成时间与来源中和后才写围栏。
    checked += _ordered(
        (
            'if kind in {"branchSummary", "compactionSummary"}:',
            "_inline_text(unit.get('createdAt') or '—')",
            '_fence(unit["text"] or "（空）")])',
        ),
        export,
        EXPORT,
    )
    # 队列：标题、事实、输入依次写入，事实在 code 模式下自行中和。
    checked += _ordered(
        (
            "def _render_queue_markdown(queue: dict) -> str:",
            'parts += [f"### {_queue_heading(item)}", ""]',
            "facts = _queue_facts(item, code=True)",
            'parts += ["- " + "；".join(facts), ""]',
            'parts += [_fence(item["input"] or "（空）"), ""]',
        ),
        export,
        EXPORT,
    )
    # 反向断言：围栏不得退回固定三个反引号/波浪线，正文不得再经单行中和，
    # 行内代码不得改用会插入反斜杠的正文转义。
    for forbidden in ('marker = "```"', 'marker = "~~~"', 'return "```" +', "_inline_text(_fence",
                      '_inline_text(unit["text"]', 'return "`" + _inline_text(value) + "`"'):
        if forbidden in export:
            raise ValueError(f"{EXPORT} 的 Markdown 渲染不得包含 {forbidden}")
    return checked + 1


def main() -> int:
    try:
        checked = check_export_markdown()
    except ValueError as error:
        print(f"导出 Markdown 定界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 Markdown 定界一致：{checked} 项中和入口、围栏算法与队列事实")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
