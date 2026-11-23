#!/usr/bin/env python3
"""核对智能体消息的代码围栏切分。

`markdownBlocks.ts` 按行识别围栏：反引号围栏允许前缀正文，波浪号围栏只在行首
（最多三个空格）识别；结束围栏必须独占一行、同一种标记且不短于起始围栏；流式或
被截断而未闭合的围栏按到文末的代码块处理。代码块只裁剪首尾空白行、保留缩进，
CRLF 正文按 Unix 换行输出；长反引号串按线性扫描，不能回退到平方级回溯。这里用
Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = "apps/desktop/src/renderer/src/data/markdownBlocks.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

BLOCK_FRAGMENTS = (
    "export interface MarkdownBlock {",
    'type: "text" | "code";',
    "const LANG_CHAR = /[A-Za-z0-9_+.#-]/;",
    "const TILDE_OPENING_FENCE = /^([ \\t]{0,3})(~{3,})[ \\t]*([A-Za-z0-9_+.#-]*)[ \\t]*$/;",
    "const CLOSING_FENCE = /^[ \\t]*(`{3,}|~{3,})[ \\t]*$/;",
    "function fenceLanguage(line: string, start: number): string | null {",
    'while (index < line.length && (line[index] === " " || line[index] === "\\t")) index += 1;',
    "while (index < line.length && LANG_CHAR.test(line[index]!)) index += 1;",
    "return index === line.length ? lang : null;",
    "function backtickOpeningFence(line: string): { prefixLength: number; run: string; language: string } | null {",
    'for (let index = line.indexOf("`"); index !== -1; ) {',
    'while (end < line.length && line[end] === "`") end += 1;',
    "if (end - index >= 3) {",
    "if (language !== null) return { prefixLength: index, run: line.slice(index, end), language };",
    'index = line.indexOf("`", end);',
    'return value.replace(/\\r\\n/g, "\\n");',
    "export function trimCodeBlankLines(value: string): string {",
    "while (first <= last && !lines[first]!.trim()) first += 1;",
    "while (last >= first && !lines[last]!.trim()) last -= 1;",
    'return first > last ? "" : lines.slice(first, last + 1).join("\\n");',
    "export function splitMarkdownBlocks(content: string): MarkdownBlock[] {",
    'const line = rawLine.endsWith("\\r") ? rawLine.slice(0, -1) : rawLine;',
    "const closing = CLOSING_FENCE.exec(line)?.[1];",
    "if (closing && closing[0] === fence.marker && closing.length >= fence.length) {",
    "content: trimCodeBlankLines(normalizeCode(content.slice(codeStart, offset))) });",
    "textStart = closingStart + closing.length;",
    "const tilde = backtick ? null : TILDE_OPENING_FENCE.exec(line);",
    "const fenceStart = offset + (isTilde ? 0 : prefixLength);",
    'if (fenceStart > textStart) blocks.push({ type: "text", content: content.slice(textStart, fenceStart) });',
    'fence = { marker: isTilde ? "~" : "`", length: run.length, lang: language || "text" };',
    "codeStart = newline < 0 ? content.length : newline + 1;",
    'blocks.push({ type: "code", lang: fence.lang, content: trimCodeBlankLines(normalizeCode(content.slice(codeStart))) });',
    "} else if (textStart < content.length) {",
    'blocks.push({ type: "text", content: content.slice(textStart) });',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { splitMarkdownBlocks, trimCodeBlankLines } = await import(pathToFileURL(process.argv[1]).href);
const split = content => splitMarkdownBlocks(content).map(block => [block.type, block.lang ?? null, block.content]);
const F = "```";
const started = performance.now();
const longRun = splitMarkdownBlocks("`".repeat(60000) + "!" + "\n" + ("``` x ").repeat(20000) + "!");
const elapsed = performance.now() - started;
const results = {
  text: [
    split("a ``js\nhello"),
    split(""),
    split(`${F}not a fence!\ntext`),
    split("see ~~~ here\nmore"),
    split("    ~~~\nx"),
  ],
  fences: [
    split(`a\n${F}py\nx = 1\n${F}\nb`),
    split(`${F}\ncode\n${F}`),
    split(`intro ${F}ts\ncode\n${F}`),
    split(`a \`\` b ${F}py\nx`),
    split(`${F}c#\nx\n${F}`),
    split(`${F} py \t\nx\n${F}`),
    split(`${F}\n${F}`),
  ],
  closing: [
    split(`${F}\`\n${F}\ninner\n${F}\n${F}\``),
    split(`${F}\`\na\n${F}\nb`),
    split(`${F}\na\n${F} trailing\nb`),
    split(`${F}\na\n${F}  \nb`),
    split(`${F}\na\n~~~\nb\n${F}`),
    split(`~~~\na\n${F}\nb\n~~~~`),
  ],
  tilde: [
    split("~~~sh\nls\n~~~"),
    split("a\n   ~~~\nx\n~~~\nb"),
    split("~~~ py \nx"),
  ],
  streaming: [
    split(`${F}js\nlet a`),
    split(`${F}js`),
    split(`done\n${F}js\n`),
  ],
  code: [
    split(`${F}py\r\na\r\nb\r\n${F}\r\nend`),
    split(`${F}py\n\n    if x:\n        y\n \n${F}`),
    trimCodeBlankLines("\n\n  a\n\n b \n \n"),
    trimCodeBlankLines("  \n\t\n"),
    trimCodeBlankLines("x"),
  ],
  linear: [
    longRun.map(block => [block.type, block.content.length]),
    elapsed < 2000,
  ],
};
process.stdout.write(JSON.stringify(results));
"""

F = "```"
EXPECTED_TEXT = (
    [["text", None, "a ``js\nhello"]],
    [],
    [["text", None, f"{F}not a fence!\ntext"]],
    [["text", None, "see ~~~ here\nmore"]],
    [["text", None, "    ~~~\nx"]],
)
EXPECTED_FENCES = (
    [["text", None, "a\n"], ["code", "py", "x = 1"], ["text", None, "\nb"]],
    [["code", "text", "code"]],
    [["text", None, "intro "], ["code", "ts", "code"]],
    [["text", None, "a `` b "], ["code", "py", "x"]],
    [["code", "c#", "x"]],
    [["code", "py", "x"]],
    [["code", "text", ""]],
)
EXPECTED_CLOSING = (
    [["code", "text", f"{F}\ninner\n{F}"]],
    [["code", "text", f"a\n{F}\nb"]],
    [["code", "text", f"a\n{F} trailing\nb"]],
    [["code", "text", "a"], ["text", None, "  \nb"]],
    [["code", "text", "a\n~~~\nb"]],
    [["code", "text", f"a\n{F}\nb"]],
)
EXPECTED_TILDE = (
    [["code", "sh", "ls"]],
    [["text", None, "a\n"], ["code", "text", "x"], ["text", None, "\nb"]],
    [["code", "py", "x"]],
)
EXPECTED_STREAMING = (
    [["code", "js", "let a"]],
    [["code", "js", ""]],
    [["text", None, "done\n"], ["code", "js", ""]],
)
EXPECTED_CODE = (
    [["code", "py", "a\nb"], ["text", None, "\r\nend"]],
    [["code", "py", "    if x:\n        y"]],
    "  a\n\n b ",
    "",
    "x",
)
EXPECTED_LINEAR = (
    [["text", 60000 + 1 + 1 + 6 * 20000 + 1]],
    True,
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / BLOCKS)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=120,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 围栏切分试算超时，请核对 markdownBlocks.ts 是否回退到平方级回溯") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 围栏切分试算失败，请核对 Node.js 24+ 与 markdownBlocks.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的围栏切分结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回围栏切分矩阵")
    for key in ("text", "fences", "closing", "tilde", "streaming", "code", "linear"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"围栏切分{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"围栏切分{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["text"], EXPECTED_TEXT, "普通文本")
    checked += _compare(payload["fences"], EXPECTED_FENCES, "起始围栏")
    checked += _compare(payload["closing"], EXPECTED_CLOSING, "结束围栏")
    checked += _compare(payload["tilde"], EXPECTED_TILDE, "波浪号围栏")
    checked += _compare(payload["streaming"], EXPECTED_STREAMING, "未闭合围栏")
    checked += _compare(payload["code"], EXPECTED_CODE, "代码正文")
    checked += _compare(payload["linear"], EXPECTED_LINEAR, "线性扫描")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_markdown_blocks.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_markdown_blocks.py")
    if "共 34 项结构、31 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_markdown_blocks.py 检查 34 项结构、31 项行为")
    return 2


def check_markdown_blocks() -> tuple[int, int]:
    structure = _expect(BLOCK_FRAGMENTS, _read(BLOCKS), BLOCKS)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_markdown_blocks()
    except (OSError, ValueError) as error:
        print(f"围栏切分规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"围栏切分规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
