#!/usr/bin/env python3
"""核对摘要任务引用、回执与分支摘要任务的校验层级。

`contextJob.ts` 有三层差异：`compactionReferenceOf` 对畸形引用抛错；
`contextJobOf` 对身份、来源摘要、状态或 `kind` 不合法返回 `null`，但对已识别
任务上的畸形展示字段抛错；`branchJobOf` 把畸形载荷当作不适用并丢弃，不中断
事件回调。引用要求 `jobId` 匹配 1–128 位字母数字 / 下划线 / 连字符、状态与
`active` 合法；回执要求线程与贯穿回合标识有界、来源摘要为 64 位小写十六进制，
可选原因 / 文本 / 标识 / 计数 / 布尔 / 弃用回合数组逐项校验，文本按上限截断，
未知字段不进入结果。这里用 Node 在临时目录加载真实模块（共享包导入改写为
文件 URL）逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JOB = "apps/desktop/src/renderer/src/data/contextJob.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

JOB_FRAGMENTS = (
    'const COMPACTION_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "failed", "cancelled"]);',
    'const COMPACTION_REASONS: ReadonlySet<string> = new Set(["threshold", "budget", "overflow"]);',
    "const JOB_ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;",
    "const SOURCE_DIGEST = /^[0-9a-f]{64}$/;",
    "const ID_LIMIT = 200;",
    "const CODE_LIMIT = 120;",
    "const MESSAGE_LIMIT = 4096;",
    "const MODEL_LIMIT = 200;",
    "const EFFORT_LIMIT = 64;",
    "const MAX_ABANDONED_TURNS = 10_000;",
    "const isId = (value: unknown): value is string =>",
    'typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;',
    "const isCount = (value: unknown): value is number =>",
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0;',
    "const plainRecord = (value: unknown): Record<string, unknown> | null =>",
    'value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;',
    'throw new Error("摘要任务回执无法识别");',
    "export function compactionReferenceOf(value: unknown): CompactionReference | null | undefined {",
    "if (value === undefined || value === null) return value;",
    'if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("摘要任务引用无法识别");',
    "if (typeof raw.jobId !== \"string\" || !JOB_ID_PATTERN.test(raw.jobId)",
    "|| typeof raw.status !== \"string\" || !COMPACTION_STATUSES.has(raw.status)",
    '|| typeof raw.active !== "boolean") throw new Error("摘要任务引用无法识别");',
    "return { jobId: raw.jobId, status: raw.status as ContextCompactionJobStatus, active: raw.active };",
    "export function contextJobOf(value: unknown): ContextCompactJob | null {",
    "if (!raw || !isId(raw.threadId) || typeof raw.jobId !== \"string\" || !JOB_ID_PATTERN.test(raw.jobId)",
    "|| typeof raw.sourceDigest !== \"string\" || !SOURCE_DIGEST.test(raw.sourceDigest)",
    "|| !isId(raw.throughTurnId)",
    "|| typeof raw.status !== \"string\" || !COMPACTION_STATUSES.has(raw.status)",
    '|| (raw.kind !== undefined && raw.kind !== "branchSummary")) return null;',
    'if (raw.kind === "branchSummary") job.kind = "branchSummary";',
    'if (typeof raw.reason !== "string" || !COMPACTION_REASONS.has(raw.reason)) invalid();',
    "return safeSlice(field, limit);",
    "if (!isId(field)) invalid();",
    "if (raw.requestRejected !== undefined && raw.requestRejected !== null) {",
    'if (typeof raw.requestRejected !== "boolean") invalid();',
    "if (!Array.isArray(raw.abandonedTurnIds) || raw.abandonedTurnIds.length > MAX_ABANDONED_TURNS) invalid();",
    "if (!isId(value)) invalid();",
    "export function manualCompactionJob(job: ContextCompactJob): ContextCompactJob | null {",
    'return job.kind === "branchSummary" ? null : job;',
    "export function branchJobOf(value: unknown, threadId: string): ContextCompactJob | null {",
    "try { job = contextJobOf(value); } catch { return null; }",
    "return job !== null && job.kind === \"branchSummary\" && job.threadId === threadId ? job : null;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  compactionReferenceOf, contextJobOf, manualCompactionJob, branchJobOf,
} = await import(pathToFileURL(process.argv[1]).href);
const digest = "a".repeat(64);
const job = (over = {}) => ({ threadId: "t1", jobId: "j1", throughTurnId: "u1", sourceDigest: digest, status: "running", ...over });
const thrown = (fn) => { try { fn(); return "ok"; } catch (error) { return error.message; } };
const results = {
  refs: [
    [compactionReferenceOf(undefined) === undefined ? "undefined" : "bad", compactionReferenceOf(null) === null ? "null" : "bad"],
    compactionReferenceOf({ jobId: "job-1", status: "completed", active: true }),
    [42, [], "x", true].map(value => thrown(() => compactionReferenceOf(value))),
  ],
  refFields: [
    [
      { jobId: "" }, { jobId: "a".repeat(129) }, { jobId: "a b" }, { jobId: "a/b" },
      { status: "unknown" }, { active: "yes" }, { active: undefined },
    ].map(over => thrown(() => compactionReferenceOf({ jobId: "j", status: "running", active: true, ...over }))),
    ["a", "A1_-", "x".repeat(128)].map(jobId => compactionReferenceOf({ jobId, status: "running", active: false }).jobId.length),
  ],
  jobFull: [
    (() => {
      const value = contextJobOf(job({
        kind: "branchSummary", reason: "threshold", code: "c", message: "m", turnId: "u2",
        summaryProvider: "p", summaryModel: "m2", summaryEffort: "high",
        modelRequestCount: 2, processedCharacters: 10, totalCharacters: 20,
        retainedItemCount: 3, estimatedRetainedTokens: 100,
        firstKeptItemId: "f1", targetTurnId: "u3", fromTurnId: "u4",
        requestRejected: true, abandonedTurnIds: ["a1", "b2"], result: { ignored: true }, extra: 1,
      }));
      return [
        value.kind, value.reason, value.code, value.message, value.turnId, value.summaryProvider,
        value.summaryModel, value.summaryEffort, value.modelRequestCount, value.processedCharacters,
        value.totalCharacters, value.retainedItemCount, value.estimatedRetainedTokens,
        value.firstKeptItemId, value.targetTurnId, value.fromTurnId, value.requestRejected,
        value.abandonedTurnIds, "result" in value, "extra" in value,
      ];
    })(),
  ],
  jobMinimal: [Object.keys(contextJobOf(job())).sort()],
  jobIdentity: [
    [null, [], "x", {}].map(value => contextJobOf(value) === null ? "null" : "kept"),
    [
      job({ threadId: "" }), job({ threadId: "x".repeat(201) }),
      job({ jobId: "" }), job({ jobId: "x".repeat(129) }), job({ jobId: "a b" }),
      job({ sourceDigest: "a".repeat(63) }), job({ sourceDigest: "g".repeat(64) }),
      job({ throughTurnId: "" }), job({ status: "unknown" }), job({ kind: "compaction" }),
    ].map(value => contextJobOf(value) === null ? "null" : "kept"),
  ],
  jobReason: [
    (() => {
      const nullReason = contextJobOf(job({ reason: null }));
      const budget = contextJobOf(job({ reason: "budget" }));
      return ["reason" in nullReason, budget.reason, thrown(() => contextJobOf(job({ reason: "manual" })))];
    })(),
  ],
  jobText: [
    (() => {
      const value = contextJobOf(job({
        code: "c".repeat(200), message: "m".repeat(5000),
        summaryProvider: "p".repeat(250), summaryModel: "m".repeat(250), summaryEffort: "e".repeat(100),
      }));
      return [value.code.length, value.message.length, value.summaryProvider.length, value.summaryModel.length, value.summaryEffort.length];
    })(),
  ],
  jobTextInvalid: [
    [42, {}, true].map(code => thrown(() => contextJobOf(job({ code })))),
    (() => {
      const value = contextJobOf(job({ code: null, message: undefined }));
      return ["code" in value, "message" in value];
    })(),
  ],
  jobIds: [
    [job({ turnId: "" }), job({ firstKeptItemId: "x".repeat(201) }), job({ targetTurnId: 42 }), job({ fromTurnId: "" })]
      .map(value => thrown(() => contextJobOf(value))),
  ],
  jobCounts: [
    (() => {
      const value = contextJobOf(job({ modelRequestCount: 0, estimatedRetainedTokens: 100 }));
      return [value.modelRequestCount, value.estimatedRetainedTokens];
    })(),
    [job({ modelRequestCount: -1 }), job({ processedCharacters: 1.5 }), job({ totalCharacters: "20" }), job({ retainedItemCount: Number.MAX_SAFE_INTEGER + 1 })]
      .map(value => thrown(() => contextJobOf(value))),
  ],
  jobFlag: [
    (() => {
      const nullFlag = contextJobOf(job({ requestRejected: null }));
      return ["requestRejected" in nullFlag, contextJobOf(job({ requestRejected: false })).requestRejected, thrown(() => contextJobOf(job({ requestRejected: "yes" })))];
    })(),
  ],
  jobAbandoned: [
    (() => {
      const empty = contextJobOf(job({ abandonedTurnIds: [] }));
      return [empty.abandonedTurnIds.length, "abandonedTurnIds" in contextJobOf(job({ abandonedTurnIds: null })), thrown(() => contextJobOf(job({ abandonedTurnIds: "x" }))), thrown(() => contextJobOf(job({ abandonedTurnIds: ["a", ""] })))];
    })(),
    (() => {
      const full = contextJobOf(job({ abandonedTurnIds: Array.from({ length: 10_000 }, (_, index) => "t" + index) }));
      return [full.abandonedTurnIds.length, thrown(() => contextJobOf(job({ abandonedTurnIds: Array.from({ length: 10_001 }, (_, index) => "t" + index) })))];
    })(),
  ],
  manual: [
    manualCompactionJob(contextJobOf(job({ kind: "branchSummary" }))) === null ? "null" : "kept",
    manualCompactionJob(contextJobOf(job())).jobId,
  ],
  branch: [
    branchJobOf(job({ kind: "branchSummary" }), "t1").jobId,
    branchJobOf(job({ kind: "branchSummary" }), "t2") === null ? "null" : "kept",
    branchJobOf(job(), "t1") === null ? "null" : "kept",
    branchJobOf(null, "t1") === null ? "null" : "kept",
    branchJobOf(job({ kind: "branchSummary", reason: "manual" }), "t1") === null ? "null" : "kept",
  ],
};
process.stdout.write(JSON.stringify(results));
"""

SENTINEL = "摘要任务回执无法识别"
REF_SENTINEL = "摘要任务引用无法识别"
EXPECTED_REFS = (
    ["undefined", "null"],
    {"jobId": "job-1", "status": "completed", "active": True},
    [REF_SENTINEL, REF_SENTINEL, REF_SENTINEL, REF_SENTINEL],
)
EXPECTED_REF_FIELDS = (
    [REF_SENTINEL] * 7,
    [1, 4, 128],
)
EXPECTED_JOB_FULL = (
    [
        "branchSummary", "threshold", "c", "m", "u2", "p", "m2", "high", 2, 10,
        20, 3, 100, "f1", "u3", "u4", True, ["a1", "b2"], False, False,
    ],
)
EXPECTED_JOB_MINIMAL = (["jobId", "sourceDigest", "status", "threadId", "throughTurnId"],)
EXPECTED_JOB_IDENTITY = (
    ["null", "null", "null", "null"],
    ["null"] * 10,
)
EXPECTED_JOB_REASON = ([False, "budget", SENTINEL],)
EXPECTED_JOB_TEXT = ([120, 4096, 200, 200, 64],)
EXPECTED_JOB_TEXT_INVALID = ([SENTINEL, SENTINEL, SENTINEL], [False, False])
EXPECTED_JOB_IDS = ([SENTINEL, SENTINEL, SENTINEL, SENTINEL],)
EXPECTED_JOB_COUNTS = ([0, 100], [SENTINEL, SENTINEL, SENTINEL, SENTINEL])
EXPECTED_JOB_FLAG = ([False, False, SENTINEL],)
EXPECTED_JOB_ABANDONED = (
    [0, False, SENTINEL, SENTINEL],
    [10000, SENTINEL],
)
EXPECTED_MANUAL = ("null", "j1")
EXPECTED_BRANCH = ("j1", "null", "null", "null", "null")


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "contextJob.ts"
        target.write_text(
            _read(JOB).replace('from "@boss-harness/shared"', f'from "{(ROOT / SHARED).as_uri()}"'),
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
                "Node 摘要任务试算失败，请核对 Node.js 24+ 与 contextJob.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的摘要任务结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回摘要任务矩阵")
    for key in ("refs", "refFields", "jobFull", "jobMinimal", "jobIdentity", "jobReason", "jobText",
                "jobTextInvalid", "jobIds", "jobCounts", "jobFlag", "jobAbandoned", "manual", "branch"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"摘要任务{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"摘要任务{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["refs"], EXPECTED_REFS, "引用")
    checked += _compare(payload["refFields"], EXPECTED_REF_FIELDS, "引用字段")
    checked += _compare(payload["jobFull"], EXPECTED_JOB_FULL, "完整回执")
    checked += _compare(payload["jobMinimal"], EXPECTED_JOB_MINIMAL, "最小回执")
    checked += _compare(payload["jobIdentity"], EXPECTED_JOB_IDENTITY, "身份")
    checked += _compare(payload["jobReason"], EXPECTED_JOB_REASON, "原因")
    checked += _compare(payload["jobText"], EXPECTED_JOB_TEXT, "文本")
    checked += _compare(payload["jobTextInvalid"], EXPECTED_JOB_TEXT_INVALID, "文本非法")
    checked += _compare(payload["jobIds"], EXPECTED_JOB_IDS, "标识")
    checked += _compare(payload["jobCounts"], EXPECTED_JOB_COUNTS, "计数")
    checked += _compare(payload["jobFlag"], EXPECTED_JOB_FLAG, "布尔")
    checked += _compare(payload["jobAbandoned"], EXPECTED_JOB_ABANDONED, "弃用回合")
    checked += _compare(payload["manual"], EXPECTED_MANUAL, "手动压缩")
    checked += _compare(payload["branch"], EXPECTED_BRANCH, "分支摘要")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_job.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_job.py")
    if "共 43 项结构、26 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_job.py 检查 43 项结构、26 项行为")
    return 2


def check_context_job() -> tuple[int, int]:
    structure = _expect(JOB_FRAGMENTS, _read(JOB), JOB)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_job()
    except (OSError, ValueError) as error:
        print(f"摘要任务规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"摘要任务规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
