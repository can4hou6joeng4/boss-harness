#!/usr/bin/env python3
"""核对会话历史路由栈的修剪与可达扫描。

`routeHistory.ts` 在会话删除后移除栈内指向它的路由：光标按「原位置或其后最近
一条」调整，越过末尾时收敛到末条；栈内没有该会话或光标非法时返回 null，保留
的路由对象引用不变。后退 / 前进从光标按方向扫描最近一条可达路由，越界、非整数
光标、零增量或全部不可达时返回 -1。这里用 Node 直接加载真实泛型模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HISTORY = "apps/desktop/src/renderer/src/data/routeHistory.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

HISTORY_FRAGMENTS = (
    "export interface SessionHistoryPrune<Route extends HistoryRouteLike> {",
    "routes: Route[];",
    "cursor: number;",
    "export function dropSessionHistory<Route extends HistoryRouteLike>(",
    "if (!Number.isSafeInteger(cursor) || cursor < 0 || cursor >= routes.length) return null;",
    "const matches = (route: HistoryRouteLike | undefined): boolean =>",
    "route !== undefined && route.sessionId === sessionId;",
    "if (!routes.some(matches)) return null;",
    "const removedBefore = routes.slice(0, cursor).filter(matches).length;",
    "const remaining = routes.filter(route => !matches(route));",
    "return { routes: remaining, cursor: Math.max(0, Math.min(cursor - removedBefore, remaining.length - 1)) };",
    "export function nextReachableIndex<Route>(",
    "if (!Number.isSafeInteger(cursor) || cursor < 0 || cursor >= routes.length",
    "|| !Number.isSafeInteger(delta) || delta === 0) return -1;",
    "for (let index = cursor + delta; index >= 0 && index < routes.length; index += delta) {",
    "const route = routes[index];",
    "if (route !== undefined && reachable(route)) return index;",
    "return -1;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { dropSessionHistory, nextReachableIndex } = await import(pathToFileURL(process.argv[1]).href);
const route = (page, sessionId) => (sessionId === undefined ? { page } : { page, sessionId });
const summarize = (prune) => (prune ? [prune.routes.map(item => item.page), prune.cursor] : null);
const base = [route("home"), route("a", "s1"), route("b", "s2"), route("c", "s1"), route("d", "s1")];
const results = {
  drop: [
    [
      [-1, 1.5, base.length, Number.NaN].map(cursor => summarize(dropSessionHistory(base, cursor, "s1"))),
      summarize(dropSessionHistory([], 0, "s1")),
    ],
    summarize(dropSessionHistory(base, 2, "zzz")),
    summarize(dropSessionHistory([route("home"), route("a", "s1"), route("b", "s2")], 1, "s1")),
    summarize(dropSessionHistory([route("home"), route("a", "s1"), route("b", "s2")], 0, "s1")),
    summarize(dropSessionHistory(base, 3, "s1")),
    summarize(dropSessionHistory([route("home"), route("a", "s1"), route("b", "s2"), route("c", "s3")], 2, "s1")),
    summarize(dropSessionHistory([route("home"), route("a", "s1")], 1, "s1")),
    summarize(dropSessionHistory(base, 4, "s1")),
    summarize(dropSessionHistory([route("home"), route("a", "s1"), route("b", "s1")], 2, "s1")),
    (() => {
      const first = route("home");
      const second = route("a", "s1");
      const third = route("b", "s2");
      const prune = dropSessionHistory([first, second, third], 2, "s1");
      return [prune.routes[0] === first, prune.routes[1] === third];
    })(),
  ],
  next: [
    nextReachableIndex([{ ok: true }, { ok: false }, { ok: true }], 0, 1, item => item.ok),
    nextReachableIndex([{ ok: true }, { ok: false }, { ok: true }], 2, -1, item => item.ok),
    nextReachableIndex([{ ok: true }, { ok: false }, { ok: false }], 0, 1, item => item.ok),
    [
      nextReachableIndex([{ ok: true }, { ok: false }, { ok: true }], 0, 2, item => item.ok),
      nextReachableIndex([{ ok: true }, { ok: true }, { ok: false }], 0, 2, item => item.ok),
    ],
    [
      [-1, 3, 1.5, Number.NaN].map(cursor => nextReachableIndex([{ ok: true }, { ok: true }, { ok: true }], cursor, 1, item => item.ok)),
      [0, 1.5, Number.NaN].map(delta => nextReachableIndex([{ ok: true }, { ok: true }, { ok: true }], 0, delta, item => item.ok)),
    ],
    nextReachableIndex([], 0, 1, item => item.ok),
    nextReachableIndex([{ ok: true }, { ok: true }], 0, -1, item => item.ok),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_DROP = (
    [[None, None, None, None], None],
    None,
    [["home", "b"], 1],
    [["home", "b"], 0],
    [["home", "b"], 1],
    [["home", "b", "c"], 1],
    [["home"], 0],
    [["home", "b"], 1],
    [["home"], 0],
    [True, True],
)
EXPECTED_NEXT = (
    2,
    0,
    -1,
    [2, -1],
    [[-1, -1, -1, -1], [-1, -1, -1]],
    -1,
    -1,
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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / HISTORY)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 历史路由试算失败，请核对 Node.js 24+ 与 routeHistory.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的历史路由结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回历史路由矩阵")
    for key in ("drop", "next"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"历史路由{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"历史路由{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["drop"], EXPECTED_DROP, "修剪")
    checked += _compare(payload["next"], EXPECTED_NEXT, "可达")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_route_history.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_route_history.py")
    if "共 18 项结构、17 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_route_history.py 检查 18 项结构、17 项行为")
    return 2


def check_route_history() -> tuple[int, int]:
    structure = _expect(HISTORY_FRAGMENTS, _read(HISTORY), HISTORY)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_route_history()
    except (OSError, ValueError) as error:
        print(f"历史路由规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"历史路由规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
