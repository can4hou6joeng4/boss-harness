#!/usr/bin/env python3
"""核对「重试此轮对话」的可用性、原文回溯与技能携带规则。

`messageRetry.ts` 决定重试按钮是否可用（运行中 / 任务阻断），以及要重新
发送什么：用户消息取自身，代理消息回溯到该回合最近一条用户消息（不跳过
空文本，也不退到更早的回合）；重试请求重新携带该回合记录、且当前技能目录
仍确认存在的技能，去重且最多 10 个，未知 id 会被内核拒绝。查询走
`turnSkills.ts` 的 `turnSkillIdsFor`，只认映射自有条目。这里用 Node 在临时
目录加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RETRY = "apps/desktop/src/renderer/src/data/messageRetry.ts"
TURN_SKILLS = "apps/desktop/src/renderer/src/data/turnSkills.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

RETRY_FRAGMENTS = (
    "const MAX_RETRY_SKILLS = 10;",
    "export function retryBlockReason(running: boolean, taskBlocked: boolean): RetryBlockReason | null {",
    'if (running) return "running";',
    'if (taskBlocked) return "taskBlocked";',
    "function retryableText(item: MessageItem): string | null {",
    "const text = item.content?.trim();",
    "return text ? text : null;",
    "function retrySource(messages: readonly MessageItem[], messageId: string): { item: MessageItem; text: string } | null {",
    "const index = messages.findIndex(item => item.id === messageId);",
    "if (index < 0) return null;",
    'if (target.role === "user") {',
    "for (let cursor = index - 1; cursor >= 0; cursor -= 1) {",
    "export function retryTextForMessage(messages: readonly MessageItem[], messageId: string): string | null {",
    "export function retryRequestForMessage(",
    "const turnId = source.item.turnId;",
    "const recorded = turnSkillIdsFor(turnSkillIds, turnId);",
    "const available = new Set(availableSkillIds);",
    "if (skillIds.length >= MAX_RETRY_SKILLS) break;",
    'if (typeof id === "string" && available.has(id) && !skillIds.includes(id)) skillIds.push(id);',
    "return { text: source.text, skillIds };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { retryBlockReason, retryTextForMessage, retryRequestForMessage } =
  await import(pathToFileURL(process.argv[1]).href);
const msg = (id, role, content, extra = {}) => ({ id, role, content, ...extra });
const text = (messages, id) => retryTextForMessage(messages, id);
const request = (messages, id, skills, available) =>
  retryRequestForMessage(messages, id, skills, available);
const results = {
  blocked: [
    retryBlockReason(true, true),
    retryBlockReason(false, true),
    retryBlockReason(false, false),
  ],
  texts: [
    text([msg("u1", "user", "  hi  ")], "u1"),
    text([msg("u1", "user", "t1"), msg("a1", "agent", "x"), msg("u2", "user", "t2"), msg("a2", "agent", "y")], "a2"),
    text([msg("u1", "user", "u"), msg("a1", "agent", "x"), msg("a2", "agent", "y")], "a2"),
    text([msg("u1", "user", "hi")], "missing"),
    text([msg("u1", "user", "   ")], "u1"),
    text([msg("a1", "agent", "x")], "a1"),
    text([msg("u0", "user", "older"), msg("u1", "user", "   "), msg("a1", "agent", "x")], "a1"),
  ],
  requests: [
    request([msg("u1", "user", "hi", { turnId: "turn-1" })], "u1", { "turn-1": ["a", "b"] }, ["b", "c"]),
    request([msg("u1", "user", "hi", { turnId: "turn-1" })], "u1",
      { "turn-1": ["a", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"] },
      ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]),
    request([msg("u1", "user", "hi")], "u1", { "turn-1": ["a"] }, ["a"]),
    request([msg("u1", "user", "hi")], "missing", { "turn-1": ["a"] }, ["a"]),
    request([msg("u1", "user", "hi", { turnId: "turn-1" })], "u1", { "turn-1": ["a"] }, []),
    request([msg("u1", "user", "hi", { turnId: "constructor" })], "u1", {}, []),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_BLOCKED = ("running", "taskBlocked", None)
EXPECTED_TEXTS = ("hi", "t2", "u", None, None, None, None)
EXPECTED_REQUESTS = (
    {"text": "hi", "skillIds": ["b"]},
    {"text": "hi", "skillIds": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]},
    {"text": "hi", "skillIds": []},
    None,
    {"text": "hi", "skillIds": []},
    {"text": "hi", "skillIds": []},
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # messageRetry 经无扩展名相对路径导入 turnSkills；Node 的类型剥离只解析显式
    # 扩展名，所以复制到临时目录并改写导入，不改动仓库源文件。
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base / "turnSkills.ts").write_text(_read(TURN_SKILLS), encoding="utf-8")
        retry = base / "messageRetry.ts"
        retry.write_text(
            _read(RETRY).replace('from "./turnSkills"', 'from "./turnSkills.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(retry)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 重试规则试算失败，请核对 Node.js 24+ 与 messageRetry.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的重试规则结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回重试规则矩阵")
    for key in ("blocked", "texts", "requests"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"重试{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"重试{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["blocked"], EXPECTED_BLOCKED, "可用性")
    checked += _compare(payload["texts"], EXPECTED_TEXTS, "原文")
    checked += _compare(payload["requests"], EXPECTED_REQUESTS, "请求")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_message_retry.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_message_retry.py")
    if "共 20 项结构、16 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_message_retry.py 检查 20 项结构、16 项行为")
    return 2


def check_message_retry() -> tuple[int, int]:
    structure = _expect(RETRY_FRAGMENTS, _read(RETRY), RETRY)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_message_retry()
    except (OSError, ValueError) as error:
        print(f"重试规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"重试规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
