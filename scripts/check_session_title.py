#!/usr/bin/env python3
"""核对会话标题的项目前缀剥离与码点截断。

首页、快速提问、侧栏与分支标签都依赖 `sessionTitleFromPrompt` 与
`compactTitle`：先剥离「招聘项目：…」前缀，再折叠空白、按 Unicode 码点
截断，空内容回退「新会话」。这里固定这些顺序与上限，避免把项目前缀带进
标题、切开代理对，或在本未超限时加上省略号。
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TITLE = "apps/desktop/src/renderer/src/data/sessionTitle.ts"
SHARED = "packages/shared/src/index.ts"
HARNESS_SESSION = "harness/src/boss_harness/session.py"

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    "export const SESSION_TITLE_LIMIT = 32;",
    'export const SESSION_TITLE_FALLBACK = "新会话";',
    "const PROJECT_PREFIX = /^\\s*招聘项目：[^\\n]*\\n\\n/;",
    'return prompt.replace(PROJECT_PREFIX, "");',
    'return Array.from(text).slice(0, limit).join("");',
    'const collapsed = stripProjectPrefix(prompt).replace(/\\s+/g, " ").trim();',
    "return (codePointLength(collapsed) > limit ? sliceCodePoints(collapsed, limit) : collapsed) || SESSION_TITLE_FALLBACK;",
    'const collapsed = (text ?? "").replace(/\\s+/g, " ").trim();',
    "if (!collapsed || limit <= 0) return fallback;",
    'return codePointLength(collapsed) > limit ? `${sliceCodePoints(collapsed, limit).trimEnd()}…` : collapsed;',
)

ORDERED = (
    # 前缀剥离只替换固定格式，不匹配时原样返回。
    (
        "export function stripProjectPrefix(prompt: string): string {",
        'return prompt.replace(PROJECT_PREFIX, "");',
    ),
    # 截断按码点展开，不直接切 UTF-16 码元。
    (
        "function sliceCodePoints(text: string, limit: number): string {",
        'return Array.from(text).slice(0, limit).join("");',
    ),
    # 生成顺序：前缀 → 折叠空白 → trim → 码点判定 → 截断 → 回退。
    (
        'const collapsed = stripProjectPrefix(prompt).replace(/\\s+/g, " ").trim();',
        "return (codePointLength(collapsed) > limit ? sliceCodePoints(collapsed, limit) : collapsed) || SESSION_TITLE_FALLBACK;",
    ),
    # 紧凑标题：空值或非正上限回退，超限才截断并保留省略号。
    (
        "if (!collapsed || limit <= 0) return fallback;",
        'return codePointLength(collapsed) > limit ? `${sliceCodePoints(collapsed, limit).trimEnd()}…` : collapsed;',
    ),
)


NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { stripProjectPrefix, sessionTitleFromPrompt, compactTitle } =
  await import(pathToFileURL(process.argv[1]).href);
const emoji = (count) => "😀".repeat(count);
const results = [
  stripProjectPrefix("招聘项目：某公司\n\n帮我筛选简历"),
  sessionTitleFromPrompt("正文\n\n招聘项目：x\n\n后续"),
  stripProjectPrefix("招聘项目：x正文"),
  stripProjectPrefix("招聘项目：x\ny"),
  sessionTitleFromPrompt("a\n\t b   c"),
  sessionTitleFromPrompt("  hello  "),
  sessionTitleFromPrompt("   "),
  sessionTitleFromPrompt("招聘项目：x\n\n   "),
  sessionTitleFromPrompt("a".repeat(33)),
  sessionTitleFromPrompt(emoji(33)),
  sessionTitleFromPrompt("a".repeat(32)),
  compactTitle("  ", 10, "回退"),
  compactTitle("abc", 0, "回退"),
  compactTitle("abcdef", 3),
  compactTitle("ab cd", 2),
  compactTitle("😀😀", 2),
  compactTitle(null, 5),
];
process.stdout.write(JSON.stringify(results));
"""

EXPECTED = (
    "帮我筛选简历",
    "正文 招聘项目：x 后续",
    "招聘项目：x正文",
    "招聘项目：x\ny",
    "a b c",
    "hello",
    "新会话",
    "新会话",
    "a" * 32,
    "😀" * 32,
    "a" * 32,
    "回退",
    "回退",
    "abc…",
    "ab…",
    "😀😀",
    "",
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _node_matrix() -> list:
    # CI 的 Verify 步骤可能先于 npm 安装执行，包名导入会解析失败；复制到临时目录
    # 并把 `@boss-harness/shared` 改成仓库内 file URL，不依赖 node_modules。
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "sessionTitle.ts"
        target.write_text(
            _read(TITLE).replace('from "@boss-harness/shared"', f'from "{(ROOT / SHARED).as_uri()}"'),
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
                "Node 会话标题试算失败，请核对 Node.js 24+ 与 sessionTitle.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的会话标题结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回会话标题矩阵")
    return payload


def _check_behaviors() -> int:
    actual = _node_matrix()
    if len(actual) != len(EXPECTED):
        raise ValueError(f"会话标题用例数量变化：期望 {len(EXPECTED)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, EXPECTED)):
        if got != want:
            raise ValueError(f"会话标题第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(EXPECTED)


def check_session_title() -> tuple[int, int]:
    title = _read(TITLE)
    checked = 0
    checked += _expect(FRAGMENTS, title, TITLE)
    for group in ORDERED:
        checked += _ordered(group, title, TITLE)
    # 反向断言：不得回到直接按码元截断，不得在未超限时补省略号。
    for forbidden in ("prompt.slice(", "prompt.substring(", "collapsed.slice(", "collapsed.substring("):
        if forbidden in title:
            raise ValueError(f"{TITLE} 必须按 Unicode 码点截断，不得使用 {forbidden}")
    if re.search(r"codePointLength\(collapsed\)\s*>=\s*limit", title):
        raise ValueError(f"{TITLE} 的超限判断必须严格大于 limit，避免未超限时截断")
    # 桌面默认标题上限必须落在内核的标题上限内，避免合法标题被拒绝。
    harness = _read(HARNESS_SESSION)
    match = re.search(r"MAX_THREAD_TITLE_CHARS = (\d+)", harness)
    if not match:
        raise ValueError(f"{HARNESS_SESSION} 缺少 MAX_THREAD_TITLE_CHARS")
    limit = int(re.search(r"SESSION_TITLE_LIMIT = (\d+)", title).group(1))
    if not 1 <= limit <= int(match.group(1)):
        raise ValueError(f"{TITLE} 的 SESSION_TITLE_LIMIT 必须在 1 与内核上限 {match.group(1)} 之间")
    structure = checked + 3
    behavior = _check_behaviors()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_session_title()
    except (OSError, ValueError) as error:
        print(f"会话标题核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话标题一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
