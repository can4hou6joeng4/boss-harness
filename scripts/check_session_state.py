#!/usr/bin/env python3
"""核对会话内异步操作的归属判定。

`sessionState.ts` 用对象身份判断 resume 元数据是否仍可写回当前会话，用线程与回合
标识判断续接提示是否仍属于本次请求。这里静态核对模块契约，并用 Node 直接加载真实
模块覆盖身份相等、字段相同但对象不同、空值与字段不匹配等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/sessionState.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { SessionItem } from "./mockData";',
    " * 会话内异步操作的归属判定。",
    " * 选中会话后发起的读取可能比列表刷新更晚返回：改名、归档与切换线路都会触发 refresh",
    " * 并替换当前会话对象。异步回调只有仍指向同一对象时才能写回，否则会用旧快照覆盖新值。",
    "/** resume 快照的元数据写回目标；选中时的对象已被列表刷新替换时返回 null。 */",
    "export function resumedSession(current: SessionItem | null, selected: SessionItem): SessionItem | null {",
    "return current === selected ? selected : null;",
    "export interface ContinuationIdentity {",
    "threadId: string;",
    "sourceTurnId: string;",
    "/** 提示是否属于本次续接请求；期间切换会话后，新会话的提示不得被清理。 */",
    "export function matchesContinuation<T extends ContinuationIdentity>(current: T | null | undefined, check: ContinuationIdentity): current is T {",
    "return Boolean(current && current.threadId === check.threadId && current.sourceTurnId === check.sourceTurnId);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { resumedSession, matchesContinuation } = await import(pathToFileURL(process.argv[1]).href);
const session = (id, name) => ({ id, name, cwd: `/workspace/${id}` });
const s1 = session("a", "甲");
const s2 = session("a", "甲");
const check = { threadId: "t1", sourceTurnId: "turn1" };
const result = {
  resumed: [
    resumedSession(s1, s1) === s1,
    resumedSession(s2, s1) === null,
    resumedSession(null, s1) === null,
    resumedSession(s1, s2) === null,
  ],
  matches: [
    matchesContinuation(null, check),
    matchesContinuation(undefined, check),
    matchesContinuation({ ...check }, check),
    matchesContinuation({ threadId: "t2", sourceTurnId: "turn1" }, check),
    matchesContinuation({ threadId: "t1", sourceTurnId: "turn2" }, check),
    matchesContinuation({ threadId: "", sourceTurnId: "turn1" }, check),
    matchesContinuation({ threadId: "t1", sourceTurnId: "turn1", extra: "保留" }, check),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_RESUMED = (True, True, True, True)
EXPECTED_MATCHES = (
    False, False, True, False, False, False, True,
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 会话归属试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 会话归属试算失败，请核对 Node.js 24+ 与 sessionState.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的会话归属结果") from None
    for key in ("resumed", "matches"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"会话归属{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"会话归属{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["resumed"], EXPECTED_RESUMED, "resume 身份")
    checked += _compare(payload["matches"], EXPECTED_MATCHES, "续接标识")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_session_state.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_session_state.py")
    if "共 13 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_session_state.py 检查 13 项结构、11 项行为")
    return 2


def check_session_state() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_session_state()
    except (OSError, ValueError) as error:
        print(f"会话归属规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话归属规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
