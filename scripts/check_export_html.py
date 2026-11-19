#!/usr/bin/env python3
"""核对会话导出 HTML 的转义与页面约束。

导出的 HTML 会让用户直接在浏览器里打开，会话标题、正文、工具参数与结果都来自模型
或招聘平台，必须全部经 `html.escape(..., quote=True)` 进入页面；页面只允许内联样式，
不得含脚本、事件属性、外链或帧。这里固定每个用户字段的转义入口与文档头约束，避免
后续改动把未转义文本拼进页面。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"

EXPORT_FRAGMENTS = (
    "from html import escape",
    "def _h(value: Any) -> str:\n    return escape(str(value), quote=True)",
    "_h(meta['threadId'])",
    "_h(meta['title'])",
    "_h(meta['exportedAt'])",
    "_h(meta['serverVersion'])",
    "_h(meta['protocolVersion'])",
    "_h(usage['source'])",
    "_h(_tokens(usage['totals']))",
    "_h(_tokens(usage['summaryTasks']))",
    "_h(_inline_text('；'.join(_summary_job_facts(job))))",
    "_h(issue['entryId'])",
    "_h(issue['reason'])",
    '_h(unit["turnId"])',
    "_h(status)",
    '_h(unit["usageLabel"])',
    '_h(unit["text"] or "（空）")',
    '_h(unit["text"] or "（无文本）")',
    '_h(a["mediaType"] or "未知类型")',
    '_h(a["bytes"] if a["bytes"] is not None else "?")',
    '_h(unit["toolName"])',
    '_h(execution["label"])',
    '_h(execution["state"])',
    '_h(unit["status"])',
    "_h(decision)",
    '_h(approval["decidedAt"])',
    '_h(approval["deadline"])',
    '_h(unit["errorCode"])',
    '_h(unit["recoveryAction"])',
    "_h(key)}={_h(value)",
    "\"；\".join(f\"{_h(key)}={_h(value)}\" for key, value in unit[\"source\"].items())",
    "_h(json.dumps(value, ensure_ascii=False))",
    '_h(result["text"])',
    '_h("；".join(_result_facts(result)))',
    '_h(unit["label"])',
    '_h(unit.get("createdAt") or "—")',
    "_h(extra_text)",
    '_h(item["queueId"])',
    "_h(kind)",
    "_h(fact)",
    '_h(item["input"] or "（空）")',
    'http-equiv="Content-Security-Policy"',
    '<meta name="referrer" content="no-referrer">',
    "<meta charset=\"utf-8\">",
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
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


def check_export_html() -> int:
    export = _read(EXPORT)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    # 文档头：doctype → CSP → referrer → 标题，页脚闭合完整。
    checked += _ordered(
        (
            "'<!doctype html>'",
            '<meta http-equiv="Content-Security-Policy"',
            '<meta name="referrer" content="no-referrer">',
            "<title>BOSS Harness 会话导出</title>",
            "</footer></body></html>",
        ),
        export,
        EXPORT,
    )
    # 结果明文：只在 included 分支内转义后写入 pre。
    checked += _ordered(
        (
            "elif result[\"included\"]:\n            parts.append(f'<li>结果明文（平台事实；含个人信息，请勿外传）：</li></ul>'",
            '_h(result["text"])',
            'return "".join(parts) + "</div>"',
        ),
        export,
        EXPORT,
    )
    # 队列：id、事实与完整输入都经 _h 后写入。
    checked += _ordered(
        (
            "def _render_queue_html(queue: dict) -> str:",
            '_h(item["queueId"])',
            "_h(fact)",
            '_h(item["input"] or "（空）")',
        ),
        export,
        EXPORT,
    )
    # 反向断言：页面不得含脚本、事件属性、帧或外链资源。
    for forbidden in ("<script", "<iframe", "<object", "<embed", "onclick=", "onerror=", "javascript:", "src=", "href="):
        if forbidden in export:
            raise ValueError(f"{EXPORT} 的导出 HTML 不得包含 {forbidden}")
    return checked + 1


def main() -> int:
    try:
        checked = check_export_html()
    except ValueError as error:
        print(f"导出 HTML 转义核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 HTML 转义一致：{checked} 项字段、文档头与页面防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
