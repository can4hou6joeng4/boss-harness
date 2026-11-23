#!/usr/bin/env python3
"""核对渲染异常的摘要与详情收敛。

`errorReport.ts` 把任意抛出值收敛成有上限的文本：单行摘要 300 字符、详情
4000 字符；截断按 UTF-16 预算但不切开代理对；摘要折叠连续空白，详情只去掉
首尾空白行并保留行首缩进；Error 与形似对象取 message（为空时取 name）与
堆栈，字符串折叠后作摘要并在有换行或截断时保留原文，其余值走 JSON 或
`String()`，失败时给出固定文案。这里用 Node 在临时目录加载真实模块（改写共享
包 URL）逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ERROR_REPORT = "apps/desktop/src/renderer/src/data/errorReport.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

REPORT_FRAGMENTS = (
    "export const MAX_ERROR_MESSAGE_LENGTH = 300;",
    "export const MAX_ERROR_DETAIL_LENGTH = 4_000;",
    "export function truncateErrorText(text: string, limit: number): string {",
    'if (limit <= 0) return "…";',
    "if (text.length <= limit) return text;",
    "return `${safeSlice(text, limit - 1)}…`;",
    "export function collapseErrorWhitespace(text: string): string {",
    'return text.replace(/\\s+/g, " ").trim();',
    "export function trimErrorBlankLines(text: string): string {",
    "const lines = text.split(/\\r?\\n/);",
    'while (start < end && !(lines[start] ?? "").trim()) start += 1;',
    'while (end > start && !(lines[end - 1] ?? "").trim()) end -= 1;',
    'return lines.slice(start, end).join("\\n");',
    'if (typeof record.message !== "string") return null;',
    'name: typeof record.name === "string" && record.name ? record.name : "Error",',
    'stack: typeof record.stack === "string" ? record.stack : "",',
    'if (typeof value === "string") return value;',
    'if (value === null) return "null";',
    'if (value === undefined) return "undefined";',
    "const json = JSON.stringify(value);",
    "return Object.prototype.toString.call(value);",
    'return "无法描述的异常值";',
    "export function describeThrown(value: unknown): ErrorReport {",
    'const collapsed = collapseErrorWhitespace(parts.message || parts.name) || "未知错误";',
    "const stack = trimErrorBlankLines(parts.stack);",
    "if (stack) detail = truncateErrorText(stack, MAX_ERROR_DETAIL_LENGTH);",
    "else if (collapsed.length > MAX_ERROR_MESSAGE_LENGTH) detail = truncateErrorText(collapsed, MAX_ERROR_DETAIL_LENGTH);",
    "const needsDetail = text !== collapsed || collapsed.length > MAX_ERROR_MESSAGE_LENGTH;",
    "export function errorSummary(report: ErrorReport, scope: string): string {",
    "return label ? `${label}渲染失败：${report.message}` : report.message;",
    "export function errorDetailText(report: ErrorReport, context: ErrorDetailContext): string {",
    "区域：${collapseErrorWhitespace(context.scope) || \"未知区域\"}",
    "摘要：${report.message}",
    'if (detail) lines.push("", "堆栈：", detail);',
    'lines.push("", "组件栈：", truncateErrorText(componentStack, MAX_ERROR_DETAIL_LENGTH));',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  truncateErrorText, collapseErrorWhitespace, trimErrorBlankLines, describeThrown,
  errorSummary, errorDetailText, MAX_ERROR_MESSAGE_LENGTH, MAX_ERROR_DETAIL_LENGTH,
} = await import(pathToFileURL(process.argv[1]).href);
const results = {
  truncate: [
    [truncateErrorText("abc", 0), truncateErrorText("abc", -1), truncateErrorText("abc", 3), truncateErrorText("abcd", 3), truncateErrorText("😀😀", 3)],
  ],
  whitespace: [
    [collapseErrorWhitespace(" a\n\tb  c "), collapseErrorWhitespace("a　b"), collapseErrorWhitespace("   ")],
    [
      trimErrorBlankLines("\n  \n  indented\nline\n \r\n"),
      trimErrorBlankLines("a\r\nb"),
      trimErrorBlankLines("\n \n"),
    ],
  ],
  describe: [
    (() => {
      const error = new Error("boom");
      const report = describeThrown(error);
      return [report.message, typeof report.detail, report.detail ? report.detail.startsWith("Error: boom") : false];
    })(),
    (() => {
      const empty = describeThrown({ message: "" });
      const blanks = describeThrown({ message: "   " });
      const text = describeThrown("   ");
      return [
        empty.message, empty.detail === undefined,
        blanks.message, blanks.detail === undefined,
        text.message, text.detail === undefined,
      ];
    })(),
    (() => {
      const report = describeThrown({ name: "Custom", message: "x".repeat(350) });
      return [report.message.length, report.message.endsWith("…"), report.detail.length];
    })(),
    (() => {
      const report = describeThrown("line1\nline2");
      return [report.message, report.detail];
    })(),
    (() => {
      const report = describeThrown("boom");
      return [report.message, report.detail === undefined];
    })(),
    [null, undefined, 42, { a: 1 }, [1, 2]].map(value => describeThrown(value).message),
    (() => {
      const circular = {};
      circular.self = circular;
      return [describeThrown(circular).message, describeThrown(10n).message];
    })(),
    (() => {
      const report = describeThrown("y".repeat(500));
      return [report.message.length, report.message.endsWith("…"), report.detail.length];
    })(),
    (() => {
      const report = describeThrown({ message: "m", name: 42, stack: " s \n" });
      return [report.message, report.detail];
    })(),
    (() => {
      const report = describeThrown(new Error(""));
      return [report.message, report.detail ? report.detail.startsWith("Error") : false];
    })(),
  ],
  summary: [
    [errorSummary({ message: "boom" }, "会话区"), errorSummary({ message: "boom" }, "  "), errorSummary({ message: "boom" }, " a  b ")],
  ],
  detail: [
    errorDetailText({ message: "boom", detail: "\nstack\n" }, { scope: "会话区", occurredAt: "2026-11-23T00:00:00Z" }),
    errorDetailText({ message: "boom" }, { scope: "  ", occurredAt: "t", componentStack: "\n comp \n" }),
    (() => {
      const text = errorDetailText({ message: "boom" }, { scope: "s", occurredAt: "t", componentStack: "c".repeat(4100) });
      const last = text.split("\n").at(-1);
      return [last.length, last.endsWith("…")];
    })(),
  ],
  limits: [MAX_ERROR_MESSAGE_LENGTH, MAX_ERROR_DETAIL_LENGTH],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_TRUNCATE = (["…", "…", "abc", "ab…", "😀…"],)
EXPECTED_WHITESPACE = (
    ["a b c", "a b", ""],
    ["  indented\nline", "a\nb", ""],
)
EXPECTED_DESCRIBE = (
    ["boom", "string", True],
    ["Error", True, "未知错误", True, "未知错误", True],
    [300, True, 350],
    ["line1 line2", "line1\nline2"],
    ["boom", True],
    ["null", "undefined", "42", '{"a":1}', "[1,2]"],
    ["[object Object]", "10"],
    [300, True, 500],
    ["m", " s "],
    ["Error", True],
)
EXPECTED_SUMMARY = (["会话区渲染失败：boom", "boom", "a b渲染失败：boom"],)
EXPECTED_DETAIL = (
    "区域：会话区\n时间：2026-11-23T00:00:00Z\n摘要：boom\n\n堆栈：\nstack",
    "区域：未知区域\n时间：t\n摘要：boom\n\n组件栈：\n comp ",
    [4000, True],
)
EXPECTED_LIMITS = (300, 4000)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        shared = (ROOT / SHARED).as_uri()
        target = base / "errorReport.ts"
        target.write_text(
            _read(ERROR_REPORT).replace('from "@boss-harness/shared"', f'from "{shared}"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 错误报告试算失败，请核对 Node.js 24+ 与 errorReport.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的错误报告结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回错误报告矩阵")
    for key in ("truncate", "whitespace", "describe", "summary", "detail", "limits"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"错误报告{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"错误报告{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["truncate"], EXPECTED_TRUNCATE, "截断")
    checked += _compare(payload["whitespace"], EXPECTED_WHITESPACE, "空白")
    checked += _compare(payload["describe"], EXPECTED_DESCRIBE, "描述")
    checked += _compare(payload["summary"], EXPECTED_SUMMARY, "摘要")
    checked += _compare(payload["detail"], EXPECTED_DETAIL, "详情")
    checked += _compare(payload["limits"], EXPECTED_LIMITS, "上限")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_error_report.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_error_report.py")
    if "共 35 项结构、19 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_error_report.py 检查 35 项结构、19 项行为")
    return 2


def check_error_report() -> tuple[int, int]:
    structure = _expect(REPORT_FRAGMENTS, _read(ERROR_REPORT), ERROR_REPORT)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_error_report()
    except (OSError, ValueError) as error:
        print(f"错误报告规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"错误报告规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
