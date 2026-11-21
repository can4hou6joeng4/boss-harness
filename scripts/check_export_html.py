#!/usr/bin/env python3
"""核对会话导出 HTML 的转义与页面约束。

导出的 HTML 会让用户直接在浏览器里打开，会话标题、正文、工具参数与结果都来自模型
或招聘平台，必须全部经 `html.escape(..., quote=True)` 进入页面；页面只允许内联样式，
不得含脚本、事件属性、外链或帧。这里固定每个用户字段的转义入口与文档头约束，并直接
调用 `_h` 与 `_render_html` 核对转义结果和页面结构，避免后续改动把未转义文本拼进页面。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import _h, _render_html  # noqa: E402

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
    "_h(_code_text('；'.join(_summary_job_facts(job))))",
    'extra.append(f"摘要任务 {_code_text(unit[\'summaryJobId\'])}")',
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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"导出 HTML 行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _meta(**overrides) -> dict:
    meta = {
        "view": "current",
        "usage": {
            "source": "provider",
            "totals": {"requests": 0},
            "summaryTasks": {"requests": 0},
            "summaryJobs": [],
            "summaryJobCount": 0,
        },
        "toolResults": "omitted",
        "threadId": "thread-1",
        "title": "会话标题",
        "exportedAt": "2026-11-22T00:00:00Z",
        "serverVersion": "0.2.0rc494",
        "protocolVersion": "0.2.0",
        "turnCount": 0,
    }
    meta.update(overrides)
    return meta


def _render(meta: dict | None = None, units=(), counts: dict | None = None,
            total_units: int = 0, max_bytes: int = 1024, queue: dict | None = None) -> str:
    return _render_html(
        meta or _meta(),
        list(units),
        counts or {"secrets": 0, "environment": 0, "paths": 0, "personalInfo": 0},
        total_units,
        max_bytes,
        queue or {"totalItems": 0, "items": []},
    )


def _behavior_checks() -> int:
    checked = _expect_value(
        _h('<a href="x">&\''), "&lt;a href=&quot;x&quot;&gt;&amp;&#x27;", "特殊字符转义")
    checked += _expect_value(_h(None), "None", "空值转义")
    checked += _expect_value(_h(5), "5", "数值转义")
    checked += _expect_value(_h("plain"), "plain", "安全文本")

    page = _render()
    checked += _expect_value(page.startswith("<!doctype html>"), True, "文档开头")
    checked += _expect_value("default-src 'none'" in page, True, "内容安全策略")
    checked += _expect_value(
        '<meta name="referrer" content="no-referrer">' in page, True, "来源策略")
    checked += _expect_value(page.endswith("</footer></body></html>\n"), True, "页脚闭合")
    checked += _expect_value(("<main>" in page, "</main>" in page), (True, True), "主体结构")

    hostile = _render(_meta(threadId="<script>alert(1)</script>",
                            title='"><img src=x onerror=1>'))
    checked += _expect_value("<script" in hostile, False, "脚本未注入")
    checked += _expect_value("<img" in hostile, False, "图片未注入")
    checked += _expect_value(
        "&lt;script&gt;alert(1)&lt;/script&gt;" in hostile, True, "会话 id 已转义")
    checked += _expect_value(
        "&quot;&gt;&lt;img src=x onerror=1&gt;" in hostile, True, "标题已转义")

    omitted = _render()
    checked += _expect_value("工具结果只保留结构与执行状态" in omitted, True, "省略提示")
    checked += _expect_value("未再做个人信息打码" in omitted, False, "省略不声明明文")
    included = _render(_meta(toolResults="included"))
    checked += _expect_value("未再做个人信息打码" in included, True, "明文提示")

    checked += _expect_value("视图：当前分支" in omitted, True, "当前分支视图")
    checked += _expect_value(
        "完整日志（含已切离分支）" in _render(_meta(view="log")), True, "日志视图")

    counted = _render(counts={"secrets": 1, "environment": 2, "paths": 3, "personalInfo": 4})
    checked += _expect_value(
        "凭据 / 令牌 1 处，环境变量 2 处，本机路径 3 处，个人信息 4 处" in counted,
        True, "脱敏统计")
    truncated = _render(total_units=2)
    checked += _expect_value(
        ("已截断" in truncated, "仅包含前 0 / 2 个条目" in truncated,
         "超出导出上限 1,024 字节" in truncated),
        (True, True, True), "截断提示")
    checked += _expect_value(
        "另有 3 个条目无法归属到任何回合" in _render(_meta(orphanEntries=3)),
        True, "孤立条目提示")
    checked += _expect_value("标题：—" in _render(_meta(title="")), True, "空标题回退")
    return checked


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
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_export_html()
    except ValueError as error:
        print(f"导出 HTML 转义核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 HTML 转义一致：{checked} 项字段、文档头、页面防护与渲染行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
