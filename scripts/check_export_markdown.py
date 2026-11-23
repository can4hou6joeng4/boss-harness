#!/usr/bin/env python3
"""核对会话导出 Markdown 的定界与代码围栏。

导出的 Markdown 会被用户放进工单、聊天或代码托管页面渲染。用户与模型正文可能包含
反引号、换行或整行围栏，元数据还可能包含平台返回的任意文本：正文只能走按最长反引号
动态加长的代码围栏，单行元数据必须经 `_inline_text` 转义链接、原生 HTML、强调与表格
定界符，标识符再包成行内代码。这里固定这些入口与围栏算法，并直接调用四个纯函数核对
替换结果，避免新增字段把可执行的 Markdown 拼进导出。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import (  # noqa: E402
    _approval_label,
    _code_text,
    _compaction_facts,
    _fence,
    _inline_code,
    _inline_text,
    _suggested_file_name,
    _turn_status_label,
    _usage_line,
)

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
    'f"{_inline_text(key)}={_inline_text(json.dumps(value, ensure_ascii=False))}"',
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
LABEL_FRAGMENTS = (
    '_TURN_STATUS = {"completed": "已完成", "interrupted": "已中断", "blocked": "已阻断", "error": "出错",',
    '"running": "进行中（导出时尚未结束）"}',
    '_APPROVAL_DECISIONS = {"approve": "用户批准", "deny": "用户拒绝", "expired": "审批已失效"}',
    'return _TURN_STATUS.get(value, "状态不明") if isinstance(value, str) else "状态不明"',
    'return "等待审批"',
    'return _APPROVAL_DECISIONS.get(value, "状态不明") if isinstance(value, str) else "状态不明"',
    'return "无模型请求记录" if bucket is None else _tokens(bucket)',
    'if bucket["requests"] == 0:\n        return "无模型请求记录"',
    "parts.append(f\"输入 {bucket['promptTokens']:,} / 输出 {bucket['outputTokens']:,} token\")",
    'parts.append(f"provider 未上报用量 {unreported} 次（不按 0 计）")',
    'return f"boss-harness-session-{thread_id}-{view}.{extension}"',
    'if "enabled" in policy:',
    'details.append("开启" if policy["enabled"] else "关闭")',
    'if "triggerPercent" in policy:',
    "details.append(f\"阈值 {policy['triggerPercent']}%\")",
    'if "keepRecentTokens" in policy:',
    "details.append(f\"保留最近 {policy['keepRecentTokens']} token\")",
    'facts = ["自动压缩：" + " · ".join(details)] if details else []',
    'if any(key in policy for key in ("provider", "model", "effort")):',
    "line = f\"摘要线路：{policy.get('provider') or '—'} / {policy.get('model') or '—'}\"",
    "line += f\" · {policy['effort']}\"",
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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"导出 Markdown 行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _behavior_checks() -> int:
    checked = 0

    checked += _expect_value(_code_text("a`b"), "a'b", "反引号归一")
    checked += _expect_value(_code_text("a\rb\nc"), "a b c", "换行归一")
    checked += _expect_value(_code_text("plain text"), "plain text", "安全文本")
    checked += _expect_value(_code_text(None), "None", "空值转文本")
    checked += _expect_value(_code_text(5), "5", "数值转文本")

    checked += _expect_value(_inline_text("a`b\nc"), "a'b c", "行内先归一")
    checked += _expect_value(_inline_text("\\"), "\\\\", "反斜杠转义")
    checked += _expect_value(
        _inline_text("[]<>*_~|"), "\\[\\]\\<\\>\\*\\_\\~\\|", "行内定界符")
    checked += _expect_value(
        _inline_text("a`b\r\nc[*]_~|<>"),
        "a'b  c\\[\\*\\]\\_\\~\\|\\<\\>", "行内组合")
    checked += _expect_value(_inline_text(None), "None", "行内空值")
    checked += _expect_value(_inline_text("plain"), "plain", "行内安全文本")

    checked += _expect_value(_inline_code("a`b\nc"), "`a'b c`", "行内代码归一")
    checked += _expect_value(_inline_code("a*b"), "`a*b`", "行内代码不转义")
    checked += _expect_value(_inline_code(None), "`None`", "行内代码空值")

    checked += _expect_value(_fence("abc"), "```text\nabc\n```", "默认围栏")
    checked += _expect_value(_fence("{}", "json"), "```json\n{}\n```", "语言围栏")
    checked += _expect_value(_fence("```"), "````text\n```\n````", "反引号围栏加长")
    checked += _expect_value(
        _fence("~~~~~"), "``````text\n~~~~~\n``````", "波浪线围栏加长")
    checked += _expect_value(
        _fence("````\n~~~~"), "`````text\n````\n~~~~\n`````", "混合围栏取最长")
    checked += _expect_value(_fence(""), "```text\n\n```", "空正文围栏")
    checked += _expect_value(_fence("a\nb"), "```text\na\nb\n```", "围栏保留换行")
    checked += _label_checks()
    return checked


def _label_checks() -> int:
    # 标签降级：已知取值写固定文案，未知字符串与非字符串一律「状态不明」。
    checked = 0
    for value, expected in (("completed", "已完成"), ("interrupted", "已中断"),
                            ("blocked", "已阻断"), ("error", "出错"),
                            ("running", "进行中（导出时尚未结束）")):
        checked += _expect_value(_turn_status_label(value), expected, f"回合状态 {value}")
    for value in ("mystery", None, 42):
        checked += _expect_value(_turn_status_label(value), "状态不明", f"未知回合状态 {value!r}")
    checked += _expect_value(_approval_label(None), "等待审批", "审批等待")
    for value, expected in (("approve", "用户批准"), ("deny", "用户拒绝"),
                            ("expired", "审批已失效")):
        checked += _expect_value(_approval_label(value), expected, f"审批结论 {value}")
    for value in ("unknown", 0, ["approve"]):
        checked += _expect_value(_approval_label(value), "状态不明", f"未知审批结论 {value!r}")
    # 用量行：缺省与零请求同一句式；已上报、未上报与无可验证分支按固定顺序拼接。
    checked += _expect_value(_usage_line(None), "无模型请求记录", "用量缺省")
    empty = {"requests": 0, "verifiedRequests": 0, "promptTokens": 0, "outputTokens": 0,
             "unverifiedRequests": 0, "unverifiedReasons": {}}
    checked += _expect_value(_usage_line(empty), "无模型请求记录", "零请求用量")
    verified = {"requests": 2, "verifiedRequests": 1, "promptTokens": 1500,
                "outputTokens": 200, "unverifiedRequests": 0, "unverifiedReasons": {}}
    checked += _expect_value(_usage_line(verified),
                             "模型请求 2 次；输入 1,500 / 输出 200 token", "已验证用量行")
    unreported = {"requests": 3, "verifiedRequests": 1, "promptTokens": 10, "outputTokens": 5,
                  "unverifiedRequests": 2, "unreportedRequests": 2, "unverifiedReasons": {}}
    checked += _expect_value(
        _usage_line(unreported),
        "模型请求 3 次；输入 10 / 输出 5 token；provider 未上报用量 2 次（不按 0 计）",
        "未上报用量行")
    unverified = {"requests": 1, "verifiedRequests": 0, "promptTokens": 0, "outputTokens": 0,
                  "unverifiedRequests": 0, "unverifiedReasons": {}}
    checked += _expect_value(_usage_line(unverified),
                             "模型请求 1 次；无可验证的 provider 用量", "无可验证用量行")
    # 默认文件名：只含固定前缀、会话 id、视图与扩展名。
    checked += _expect_value(_suggested_file_name("abc", "full", "md"),
                             "boss-harness-session-abc-full.md", "导出文件名")
    checked += _expect_value(_suggested_file_name("id-9", "branch", "html"),
                             "boss-harness-session-id-9-branch.html", "分支导出文件名")
    # 自动压缩事实：开关、阈值、保留量合成一行，线路与 effort 单独一行。
    for policy, expected in (
        ({}, []),
        ({"enabled": True}, ["自动压缩：开启"]),
        ({"enabled": False, "triggerPercent": 80, "keepRecentTokens": 1000},
         ["自动压缩：关闭 · 阈值 80% · 保留最近 1000 token"]),
        ({"provider": "anthropic", "model": "claude", "effort": "high"},
         ["摘要线路：anthropic / claude · high"]),
        ({"model": "m"}, ["摘要线路：— / m"]),
        ({"enabled": True, "provider": "openai"},
         ["自动压缩：开启", "摘要线路：openai / —"]),
    ):
        checked += _expect_value(_compaction_facts(policy), expected, f"压缩事实 {policy}")
    return checked


def check_export_markdown() -> int:
    export = _read(EXPORT)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    checked += _expect(LABEL_FRAGMENTS, export, EXPORT)
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
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_export_markdown()
    except ValueError as error:
        print(f"导出 Markdown 定界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 Markdown 定界一致：{checked} 项中和入口、围栏算法、队列事实、导出标签与纯函数行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
