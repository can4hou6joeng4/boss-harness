#!/usr/bin/env python3
"""核对上下文回执的必填字段与可选展示收敛。

`contextRead.ts` 直接决定上下文面板能否渲染：会话归属必须与请求一致，预算计数
必须是非负安全整数，方法 / 来源 / 模型 / 供应商与三个布尔标记必须齐全；`usage`
与 `checkpoint` 只接受记录或 `null`。可选字段缺失时省略，`null` 语义保留；
摘要任务的记录字段复制后透传，引用沿用 `contextJob.ts` 的严格校验；分支摘要
只保留数组形状。系统提示词按 64 节上限、逐项过滤非法分节；问题清单逐项过滤并
截断 20 条，总数不能少于可见条数，否则两者都丢弃；工作区说明严格校验路径、
状态、字节与上限。这里在临时目录复制 `contextRead.ts` / `contextJob.ts` 并改写
导入，用 Node 逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
READ = "apps/desktop/src/renderer/src/data/contextRead.ts"
JOB = "apps/desktop/src/renderer/src/data/contextJob.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

READ_FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const TEXT_LIMIT = 4096;",
    "const MAX_SECTIONS = 64;",
    "const MAX_ISSUES = 20;",
    'const REQUEST_SOURCES: ReadonlySet<string> = new Set(["active", "preview", "default"]);',
    'const INSTRUCTION_STATUSES: ReadonlySet<string> = new Set(["loaded", "empty", "too_large", "unreadable"]);',
    "const CORE_COUNTS = [",
    '"estimatedInputTokens", "contextWindow", "outputReserve", "inputBudget",',
    '"messageCount", "requestedOutputTokens", "modelMaxOutputTokens",',
    'const CORE_TEXTS = ["estimateMethod", "capabilitySource", "model", "provider"] as const;',
    'const CORE_FLAGS = ["capacityIsEstimate", "withinBudget", "usageApplied"] as const;',
    "const isCount = (value: unknown): value is number =>",
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0;',
    "const isText = (value: unknown, limit: number): value is string =>",
    'typeof value === "string" && value.length <= limit;',
    "const plainRecord = (value: unknown): Record<string, unknown> | null =>",
    'value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;',
    'throw new Error("上下文预算回执无法识别");',
    "function optionalId(value: unknown): string | undefined {",
    "return typeof value === \"string\" && value.length > 0 && value.length <= ID_LIMIT ? value : undefined;",
    "function optionalNullableText(value: unknown, limit: number, allowEmpty = false): string | null | undefined {",
    "if (value === null) return null;",
    "if (typeof value !== \"string\" || value.length > limit || (!allowEmpty && value.length === 0)) return undefined;",
    "function workspaceInstructionsOf(value: unknown): WorkspaceInstructionsState | null | undefined {",
    "if (typeof raw.path !== \"string\" || raw.path.length === 0 || raw.path.length > TEXT_LIMIT) return undefined;",
    "if (typeof raw.status !== \"string\" || !INSTRUCTION_STATUSES.has(raw.status)) return undefined;",
    "if (raw.bytes !== null && !isCount(raw.bytes)) return undefined;",
    "if (!isCount(raw.limitBytes)) return undefined;",
    "function systemPromptOf(value: unknown): SystemPromptInfo | undefined {",
    "if (!raw || !isCount(raw.bytes)) return undefined;",
    "if (raw.sections === undefined) return { bytes: raw.bytes };",
    "if (!Array.isArray(raw.sections) || raw.sections.length > MAX_SECTIONS) return undefined;",
    'if (typeof section.id !== "string" || section.id.length === 0 || section.id.length > ID_LIMIT) continue;',
    "if (!isText(section.title, TEXT_LIMIT) || !isCount(section.bytes)) continue;",
    "function issuesOf(value: unknown): ContextBranchSummaryIssue[] | undefined {",
    'if (typeof issue.entryId !== "string" || issue.entryId.length > ID_LIMIT) continue;',
    'if (typeof issue.reason !== "string" || issue.reason.length === 0 || issue.reason.length > TEXT_LIMIT) continue;',
    "return issues.slice(0, MAX_ISSUES);",
    "export function contextReadOf(value: unknown, expectedThreadId: string): ContextReadResponse {",
    "|| raw.threadId !== expectedThreadId) invalid();",
    'if (typeof raw.requestSource !== "string" || !REQUEST_SOURCES.has(raw.requestSource)) invalid();',
    "for (const key of CORE_COUNTS) if (!isCount(raw[key])) invalid();",
    "if (raw.usage !== null && !plainRecord(raw.usage)) invalid();",
    "if (raw.checkpoint !== null && !plainRecord(raw.checkpoint)) invalid();",
    "if (raw.summaryUsage === null) result.summaryUsage = null;",
    "else if (plainRecord(raw.summaryUsage)) result.summaryUsage = { ...raw.summaryUsage as Record<string, unknown> };",
    'else if (plainRecord(raw.lastBudget)) result.lastBudget = { ...raw.lastBudget as Record<string, unknown> } as unknown as ContextReadResponse["lastBudget"];',
    "if (Array.isArray(raw.branchSummaries)) result.branchSummaries = raw.branchSummaries as ContextReadResponse[\"branchSummaries\"];",
    "if (issueTotal === undefined) {",
    "} else if (isCount(issueTotal) && issueTotal >= issues.length) {",
    "} else if (isCount(issueTotal)) {",
    "const instructions = workspaceInstructionsOf(raw.workspaceInstructions);",
    "const systemPrompt = systemPromptOf(raw.systemPromptInfo);",
    "return result;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { contextReadOf } = await import(pathToFileURL(process.argv[1]).href);
const core = {
  threadId: "t1", requestSource: "active",
  estimatedInputTokens: 100, estimateMethod: "heuristic", contextWindow: 200000,
  outputReserve: 1000, inputBudget: 199000, messageCount: 5,
  requestedOutputTokens: 2000, modelMaxOutputTokens: 8000,
  capabilitySource: "provider", capacityIsEstimate: true, withinBudget: false,
  model: "m", provider: "p", usageApplied: true,
  usage: null, checkpoint: null,
};
const read = (over = {}, expected = "t1") => contextReadOf({ ...core, ...over }, expected);
const thrown = (fn) => { try { fn(); return "ok"; } catch (error) { return error.message; } };
const results = {
  core: [
    (() => {
      const value = read();
      return [Object.keys(value).length, value.threadId, value.requestSource, value.usage, value.checkpoint];
    })(),
    [
      thrown(() => read({}, "t2")),
      thrown(() => read({ threadId: "" })),
      thrown(() => read({ threadId: "x".repeat(201) })),
      thrown(() => contextReadOf(null, "t1")),
      thrown(() => contextReadOf([], "t1")),
      thrown(() => read({ requestSource: "other" })),
      thrown(() => read({ estimatedInputTokens: -1 })),
      thrown(() => read({ contextWindow: 1.5 })),
      thrown(() => read({ messageCount: "5" })),
      thrown(() => read({ provider: 42 })),
      thrown(() => read({ withinBudget: "yes" })),
      thrown(() => read({ usage: "x" })),
      thrown(() => read({ checkpoint: [] })),
    ],
  ],
  optional: [
    (() => { const value = read({ turnId: "u1" }); return [value.turnId, "turnId" in read()]; })(),
    ["", "x".repeat(201), 42, null].map(turnId => "turnId" in read({ turnId })),
  ],
  flags: [
    [read({ summaryAvailable: true }), read({ summaryAvailable: false }), read({ summaryAvailable: "yes" })]
      .map(value => "summaryAvailable" in value ? value.summaryAvailable : "missing"),
  ],
  issueText: [
    [read({ checkpointIssue: "x" }), read({ checkpointIssue: "" }), read({ checkpointIssue: "x".repeat(4097) }), read({ checkpointIssue: 42 })]
      .map(value => "checkpointIssue" in value ? value.checkpointIssue.length : "missing"),
  ],
  records: [
    (() => {
      const summary = read({ summaryUsage: { a: 1 } });
      const budget = read({ lastBudget: { b: 2 } });
      const breakdown = read({ breakdown: { c: 3 } });
      return [summary.summaryUsage, budget.lastBudget, breakdown.breakdown,
        "summaryUsage" in read({ summaryUsage: "x" }), "lastBudget" in read({ lastBudget: [] }),
        "breakdown" in read({ breakdown: null })];
    })(),
    (() => {
      const value = read({ summaryUsage: null, lastBudget: null });
      return [value.summaryUsage, value.lastBudget];
    })(),
  ],
  nullable: [
    [read({ reasoningEffort: null }), read({ reasoningEffort: "high" }), read({ reasoningEffort: "" }), read({ reasoningEffort: "x".repeat(201) })]
      .map(value => "reasoningEffort" in value ? value.reasoningEffort : "missing"),
    [read({ requestFingerprint: null }), read({ requestFingerprint: "f" })]
      .map(value => "requestFingerprint" in value ? value.requestFingerprint : "missing"),
    [read({ usageAnchorTurnId: null }), read({ usageAnchorTurnId: "a" })]
      .map(value => "usageAnchorTurnId" in value ? value.usageAnchorTurnId : "missing"),
  ],
  job: [
    (() => {
      const absent = read();
      const nullJob = read({ compactionJob: null });
      const valid = read({ compactionJob: { jobId: "j1", status: "running", active: true } });
      return ["compactionJob" in absent, nullJob.compactionJob, valid.compactionJob];
    })(),
    thrown(() => read({ compactionJob: { jobId: "", status: "running", active: true } })),
  ],
  branchSummaries: [
    read({ branchSummaries: [{ entryId: "e", summary: "s" }] }).branchSummaries,
    "branchSummaries" in read({ branchSummaries: "x" }),
  ],
  issues: [
    (() => {
      const value = read({ branchSummaryIssues: [
        { entryId: "", reason: "empty-entry" }, { entryId: "e2", reason: "why" },
        { entryId: 1, reason: "bad" }, { reason: "" },
      ] });
      return [value.branchSummaryIssues, "branchSummaryIssueCount" in value];
    })(),
    (() => {
      const value = read({ branchSummaryIssues: [{ entryId: "e", reason: "why" }], branchSummaryIssueCount: 5 });
      return [value.branchSummaryIssues.length, value.branchSummaryIssueCount];
    })(),
    (() => {
      const value = read({ branchSummaryIssues: [{ entryId: "e", reason: "why" }], branchSummaryIssueCount: 0 });
      return ["branchSummaryIssues" in value, "branchSummaryIssueCount" in value];
    })(),
    (() => {
      const value = read({ branchSummaryIssueCount: 3 });
      return ["branchSummaryIssues" in value, value.branchSummaryIssueCount];
    })(),
    (() => {
      const value = read({ branchSummaryIssues: "x", branchSummaryIssueCount: 2 });
      return ["branchSummaryIssues" in value, value.branchSummaryIssueCount];
    })(),
    read({ branchSummaryIssues: Array.from({ length: 25 }, (_, index) => ({ entryId: "e" + index, reason: "why" })) }).branchSummaryIssues.length,
  ],
  instructions: [
    (() => {
      const value = read({ workspaceInstructions: { path: "/x", status: "loaded", bytes: 10, limitBytes: 100, extra: 1 } });
      return [value.workspaceInstructions, "extra" in value.workspaceInstructions];
    })(),
    [
      read({ workspaceInstructions: { path: "/x", status: "other", bytes: null, limitBytes: 1 } }),
      read({ workspaceInstructions: { path: "", status: "loaded" } }),
      read({ workspaceInstructions: { path: "/x", status: "loaded", bytes: -1, limitBytes: 1 } }),
      read({ workspaceInstructions: { path: "/x", status: "loaded", bytes: null, limitBytes: -1 } }),
      read({ workspaceInstructions: [] }),
      read({ workspaceInstructions: "x" }),
    ].map(value => "workspaceInstructions" in value ? "kept" : "missing"),
    (() => {
      const nullValue = read({ workspaceInstructions: null });
      return [nullValue.workspaceInstructions, "workspaceInstructions" in read()];
    })(),
  ],
  prompt: [
    (() => {
      const value = read({ systemPromptInfo: { bytes: 50 } });
      return [value.systemPromptInfo, "sections" in value.systemPromptInfo];
    })(),
    (() => {
      const value = read({ systemPromptInfo: { bytes: 50, sections: [
        { id: "s1", title: "t", bytes: 1 }, { id: "", title: "t", bytes: 1 },
        { id: "s2", title: 42, bytes: 1 }, null, { id: "s3", title: "t2", bytes: 2 },
      ] } });
      return [value.systemPromptInfo.sections, value.systemPromptInfo.bytes];
    })(),
    [
      read({ systemPromptInfo: { bytes: -1 } }),
      read({ systemPromptInfo: { bytes: 1, sections: Array.from({ length: 65 }, (_, index) => ({ id: "s" + index, title: "t", bytes: 1 })) } }),
      read({ systemPromptInfo: { bytes: 1, sections: "x" } }),
      read({ systemPromptInfo: "x" }),
      read({ systemPromptInfo: null }),
    ].map(value => "systemPromptInfo" in value ? "kept" : "missing"),
  ],
  usageCheckpoint: [
    (() => { const value = read({ usage: { totalTokens: 5 }, checkpoint: { id: "c" } }); return [value.usage, value.checkpoint]; })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

SENTINEL = "上下文预算回执无法识别"
EXPECTED_CORE = (
    [18, "t1", "active", None, None],
    [SENTINEL] * 13,
)
EXPECTED_OPTIONAL = (
    ["u1", False],
    [False, False, False, False],
)
EXPECTED_FLAGS = ([True, False, "missing"],)
EXPECTED_ISSUE_TEXT = ([1, 0, "missing", "missing"],)
EXPECTED_RECORDS = (
    [{"a": 1}, {"b": 2}, {"c": 3}, False, False, False],
    [None, None],
)
EXPECTED_NULLABLE = (
    [None, "high", "missing", "missing"],
    [None, "f"],
    [None, "a"],
)
EXPECTED_JOB = (
    [False, None, {"jobId": "j1", "status": "running", "active": True}],
    "摘要任务引用无法识别",
)
EXPECTED_BRANCH_SUMMARIES = ([{"entryId": "e", "summary": "s"}], False)
EXPECTED_ISSUES = (
    [[{"entryId": "", "reason": "empty-entry"}, {"entryId": "e2", "reason": "why"}], False],
    [1, 5],
    [False, False],
    [False, 3],
    [False, 2],
    20,
)
EXPECTED_INSTRUCTIONS = (
    [{"path": "/x", "status": "loaded", "bytes": 10, "limitBytes": 100}, False],
    ["missing"] * 6,
    [None, False],
)
EXPECTED_PROMPT = (
    [{"bytes": 50}, False],
    [[{"id": "s1", "title": "t", "bytes": 1}, {"id": "s3", "title": "t2", "bytes": 2}], 50],
    ["missing"] * 5,
)
EXPECTED_USAGE_CHECKPOINT = ([{"totalTokens": 5}, {"id": "c"}],)


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
        (base / "contextJob.ts").write_text(
            _read(JOB).replace('from "@boss-harness/shared"', f'from "{shared}"'),
            encoding="utf-8",
        )
        target = base / "contextRead.ts"
        target.write_text(_read(READ).replace('from "./contextJob"', 'from "./contextJob.ts"'), encoding="utf-8")
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
                "Node 上下文回执试算失败，请核对 Node.js 24+ 与 contextRead.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的上下文回执结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回上下文回执矩阵")
    for key in ("core", "optional", "flags", "issueText", "records", "nullable", "job",
                "branchSummaries", "issues", "instructions", "prompt", "usageCheckpoint"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"上下文回执{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"上下文回执{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["core"], EXPECTED_CORE, "核心")
    checked += _compare(payload["optional"], EXPECTED_OPTIONAL, "可选标识")
    checked += _compare(payload["flags"], EXPECTED_FLAGS, "布尔")
    checked += _compare(payload["issueText"], EXPECTED_ISSUE_TEXT, "诊断文本")
    checked += _compare(payload["records"], EXPECTED_RECORDS, "记录")
    checked += _compare(payload["nullable"], EXPECTED_NULLABLE, "可空文本")
    checked += _compare(payload["job"], EXPECTED_JOB, "摘要引用")
    checked += _compare(payload["branchSummaries"], EXPECTED_BRANCH_SUMMARIES, "分支摘要")
    checked += _compare(payload["issues"], EXPECTED_ISSUES, "问题清单")
    checked += _compare(payload["instructions"], EXPECTED_INSTRUCTIONS, "工作区说明")
    checked += _compare(payload["prompt"], EXPECTED_PROMPT, "系统提示词")
    checked += _compare(payload["usageCheckpoint"], EXPECTED_USAGE_CHECKPOINT, "用量与检查点")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_read.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_read.py")
    if "共 54 项结构、28 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_read.py 检查 54 项结构、28 项行为")
    return 2


def check_context_read() -> tuple[int, int]:
    structure = _expect(READ_FRAGMENTS, _read(READ), READ)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_read()
    except (OSError, ValueError) as error:
        print(f"上下文回执规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文回执规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
