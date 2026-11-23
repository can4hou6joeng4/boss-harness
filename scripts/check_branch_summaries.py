#!/usr/bin/env python3
"""核对分支摘要条目的逐项校验规则。

`branchSummaries.ts` 校验 `context/read.branchSummaries`，非法条目丢弃并计数，
合法条目继续展示。这里静态核对模块契约，并用 Node 直接加载真实模块覆盖非数组
输入、标识上限与重复、可选引用、废弃回合数组、字符数与顺序保留等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/branchSummaries.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ContextBranchSummary } from "@boss-harness/protocol";',
    "const ENTRY_ID_LIMIT = 200;",
    "const MAX_ABANDONED_TURNS = 1000;",
    "const TURN_ID_LIMIT = 200;",
    "function text(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    "function optionalRef(value: unknown): string | null | undefined {",
    "if (value === undefined || value === null) return null;",
    "return text(value, TURN_ID_LIMIT) ? value : undefined;",
    " * 整段会话区落入错误边界。与同响应的 `branchSummaryIssues` 一致：非法条目丢弃并",
    "export function branchSummariesOf(value: unknown): { summaries: ContextBranchSummary[]; dropped: number } {",
    "if (!Array.isArray(value)) return { summaries: [], dropped: 0 };",
    "const seen = new Set<string>();",
    "if (!text(raw.entryId, ENTRY_ID_LIMIT) || seen.has(raw.entryId)) { dropped += 1; continue; }",
    "const targetTurnId = optionalRef(raw.targetTurnId);",
    "if (targetTurnId === undefined || fromTurnId === undefined || summaryJobId === undefined) { dropped += 1; continue; }",
    "if (!Array.isArray(abandoned) || abandoned.length > MAX_ABANDONED_TURNS",
    'if (typeof raw.characters !== "number" || !Number.isSafeInteger(raw.characters) || raw.characters < 0) { dropped += 1; continue; }',
    "seen.add(raw.entryId);",
    "abandonedTurnIds: [...abandoned],",
    "return { summaries, dropped };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { branchSummariesOf } = await import(pathToFileURL(process.argv[1]).href);
const shape = result => ({
  n: result.summaries.length,
  dropped: result.dropped,
  entries: result.summaries.map(s => ({
    idLength: s.entryId.length,
    targetTurnId: s.targetTurnId,
    fromTurnId: s.fromTurnId,
    summaryJobId: s.summaryJobId,
    abandoned: s.abandonedTurnIds.length,
    firstAbandoned: s.abandonedTurnIds[0] ?? null,
    characters: s.characters,
  })),
});
const valid = { entryId: "e1", targetTurnId: "t1", fromTurnId: "t0", abandonedTurnIds: ["a1", "a2"], summaryJobId: "j1", characters: 10 };
const copySource = { ...valid, abandonedTurnIds: ["a1", "a2"] };
const copied = branchSummariesOf([copySource]);
copySource.abandonedTurnIds.push("a3");
const result = {
  cases: [
    shape(branchSummariesOf(null)),
    shape(branchSummariesOf({})),
    shape(branchSummariesOf([])),
    shape(branchSummariesOf([valid])),
    shape(branchSummariesOf([{ ...valid, entryId: "" }])),
    shape(branchSummariesOf([{ ...valid, entryId: "x".repeat(201) }])),
    shape(branchSummariesOf([{ ...valid, entryId: "x".repeat(200) }])),
    shape(branchSummariesOf([valid, { ...valid, characters: 20 }])),
    shape(branchSummariesOf([{ entryId: "e1", abandonedTurnIds: [], characters: 0 }])),
    shape(branchSummariesOf([{ ...valid, targetTurnId: null, fromTurnId: null, summaryJobId: null }])),
    shape(branchSummariesOf([{ ...valid, targetTurnId: "x".repeat(201) }])),
    shape(branchSummariesOf([{ ...valid, targetTurnId: 42 }])),
    shape(branchSummariesOf([null])),
    shape(branchSummariesOf([[]])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: undefined }])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: {} }])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: Array.from({ length: 1001 }, (_, i) => `a${i}`) }])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: Array.from({ length: 1000 }, (_, i) => `a${i}`) }])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: [""] }])),
    shape(branchSummariesOf([{ ...valid, abandonedTurnIds: ["x".repeat(201)] }])),
    shape(branchSummariesOf([{ ...valid, characters: -1 }])),
    shape(branchSummariesOf([{ ...valid, characters: 1.5 }])),
    shape(branchSummariesOf([{ ...valid, characters: "10" }])),
    shape(branchSummariesOf([{ ...valid, characters: 0 }])),
    shape(branchSummariesOf([valid, { ...valid, entryId: "e2", characters: -1 }, { ...valid, characters: 30 }, { ...valid, entryId: "e3", characters: 0 }])),
  ],
  copy: [copied.summaries[0]?.abandonedTurnIds.length ?? null],
};
process.stdout.write(JSON.stringify(result));
"""


def _entry(id_length, characters, *, target="t1", source="t0", job="j1", abandoned=2, first="a1"):
    return {
        "idLength": id_length, "targetTurnId": target, "fromTurnId": source,
        "summaryJobId": job, "abandoned": abandoned, "firstAbandoned": first,
        "characters": characters,
    }


EMPTY = {"n": 0, "dropped": 0, "entries": []}
VALID = {"n": 1, "dropped": 0, "entries": [_entry(2, 10)]}
EXPECTED_CASES = (
    EMPTY,
    EMPTY,
    EMPTY,
    VALID,
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 1, "dropped": 0, "entries": [_entry(200, 10)]},
    {"n": 1, "dropped": 1, "entries": [_entry(2, 10)]},
    {"n": 1, "dropped": 0, "entries": [_entry(2, 0, target=None, source=None, job=None, abandoned=0, first=None)]},
    {"n": 1, "dropped": 0, "entries": [_entry(2, 10, target=None, source=None, job=None)]},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 1, "dropped": 0, "entries": [_entry(2, 10, abandoned=1000, first="a0")]},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 0, "dropped": 1, "entries": []},
    {"n": 1, "dropped": 0, "entries": [_entry(2, 0)]},
    {"n": 2, "dropped": 2, "entries": [_entry(2, 10), _entry(2, 0, target="t1", source="t0", job="j1")]},
)
EXPECTED_COPY = (2,)
LABELS = {"cases": "条目", "copy": "数组复制"}


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
        raise ValueError("Node 分支摘要试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 分支摘要试算失败，请核对 Node.js 24+ 与 branchSummaries.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的分支摘要结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"分支摘要{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"分支摘要{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"]) + _compare(payload["copy"], EXPECTED_COPY, LABELS["copy"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_branch_summaries.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_branch_summaries.py")
    if "共 21 项结构、26 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_branch_summaries.py 检查 21 项结构、25 项行为")
    return 2


def check_branch_summaries() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_branch_summaries()
    except (OSError, ValueError) as error:
        print(f"分支摘要规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支摘要规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
