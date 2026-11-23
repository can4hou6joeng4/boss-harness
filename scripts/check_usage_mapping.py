#!/usr/bin/env python3
"""核对用量映射与摘要任务的收敛规则。

`usageMapping.ts` 把内核的回合用量收敛成界面结构：计数必须是非负安全整数，
`verified + unverified` 必须等于请求总数；原因表用空原型承接任意键，合计必须
等于未验证请求数，超过 20 项合并为「其他 N 种原因」并在撞名时补空格；
`unreportedRequests` 必须与 `missing` 对账。回合字段限制 providers / models
条数、标识 1–128 码点、状态与 ISO 时间走白名单，技能 id 去重并最多 10 项，
压缩策略只保留已记录且合法的字段。分页结束后回合标识不得重复、总数必须与
声明一致；摘要任务同样校验形状、标识重复与计数，并据此推断截断。这里用 Node
在临时目录加载真实模块（共享包与 `./timeFormat` 导入改写为文件 URL）逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
USAGE = "apps/desktop/src/renderer/src/data/usageMapping.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

USAGE_FRAGMENTS = (
    'const COUNT_KEYS = ["requests", "verifiedRequests", "unverifiedRequests", "promptTokens",',
    'const NULLABLE_KEYS = ["cacheReadTokens", "cacheWriteTokens", "reasoningTokens"] as const;',
    "const REASON_LIMIT = 20;",
    "export const isCount = (value: unknown): value is number =>",
    "typeof value === \"number\" && Number.isSafeInteger(value) && value >= 0;",
    "export function bucketOf(value: unknown): ThreadUsageBucket | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "if (!COUNT_KEYS.every(key => isCount(raw[key])) || !NULLABLE_KEYS.every(key => raw[key] === null || isCount(raw[key]))) return null;",
    "if (verified + unverified !== requests) return null;",
    "const unverifiedReasons: Record<string, number> = Object.create(null) as Record<string, number>;",
    "if (!isCount(amount) || !Number.isSafeInteger(reasonTotal + amount)) return null;",
    'if (reason === "missing") missingTotal = amount;',
    "if (keptReasons < REASON_LIMIT) {",
    "let label = `其他 ${otherReasons} 种原因`;",
    "while (Object.prototype.hasOwnProperty.call(unverifiedReasons, label)) label += \" \";",
    "if (reasonTotal !== unverified) return null;",
    "if (unreported !== undefined && (!isCount(unreported) || unreported !== missingTotal)) return null;",
    "bucket.unreportedRequests = unreported ?? missingTotal;",
    'return { ...bucket, unverifiedReasons, costUsd: null, costSource: "unavailable" };',
    "const strings = (value: unknown, limit: number): string[] | null => Array.isArray(value) && value.every(item => typeof item === \"string\")",
    "? (value as string[]).slice(0, limit) : null;",
    "export function cacheWasteOf(value: unknown): ThreadUsageCacheWaste | null | undefined {",
    "if (value === undefined) return undefined;",
    "if (!isCount(raw.missedTokens) || !isCount(raw.missCount)) return null;",
    "const SKILL_LIMIT = 10;",
    "const SKILL_ID_LIMIT = 200;",
    "function skillIdsOf(value: unknown): string[] | undefined {",
    "if (typeof item === \"string\" && codePointLength(item) > 0 && codePointLength(item) <= SKILL_ID_LIMIT && !ids.includes(item)) ids.push(item);",
    "return ids.length ? ids : undefined;",
    'const POLICY_KEYS = ["enabled", "triggerPercent", "keepRecentTokens", "provider", "model", "effort"] as const;',
    'const POLICY_PROVIDERS = new Set(["anthropic", "openai", "codex"]);',
    'const POLICY_EFFORTS = new Set(["none", "minimal", "low", "medium", "high", "xhigh", "max"]);',
    "const POLICY_MAX_TOKENS = 1_000_000;",
    "const POLICY_MAX_MODEL = 200;",
    "if (keys.length === 0 || keys.some(key => !(POLICY_KEYS as readonly string[]).includes(key))) return undefined;",
    "&& trigger >= 1 && trigger <= 100)) return undefined;",
    "&& keep >= 1 && keep <= POLICY_MAX_TOKENS)) return undefined;",
    "&& (typeof provider !== \"string\" || !POLICY_PROVIDERS.has(provider))) return undefined;",
    "&& (typeof model !== \"string\" || !model.trim() || codePointLength(model) > POLICY_MAX_MODEL || /\\s/.test(model))) return undefined;",
    "&& (typeof effort !== \"string\" || !POLICY_EFFORTS.has(effort))) return undefined;",
    'const TURN_STATUSES = new Set(["running", "completed", "interrupted", "blocked", "error"]);',
    "typeof value === \"string\" && value.length <= 64 && parseIsoDateTime(value) ? value : undefined;",
    "export function turnOf(value: unknown): ThreadUsageTurn | null {",
    "const providers = strings(raw.providers, 8), models = strings(raw.models, 8);",
    "if (typeof raw.status === \"string\" && TURN_STATUSES.has(raw.status))",
    "export function verifyUsageTurns(turns: ThreadUsageTurn[], declaredTotal: number | undefined): void {",
    "throw new Error(`回合用量条目标识重复：${safeSlice(turn.turnId, 40)}`);",
    "throw new Error(`回合用量条目数不一致：声明 ${declaredTotal} 个，实际读取 ${turns.length} 个`);",
    "export function summaryJobOf(value: unknown): ThreadUsageSummaryJob | null {",
    'throw new Error("内核返回的摘要任务用量格式无法识别");',
    "throw new Error(`摘要任务用量条目标识重复：${safeSlice(job.jobId, 40)}`);",
    "if (count < page.summaryJobs.length) throw new Error(\"内核返回的摘要任务计数与明细不一致\");",
    "summaryJobsTruncated: page.summaryJobsTruncated === true || count > jobs.length,",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  isCount, bucketOf, cacheWasteOf, turnOf, verifyUsageTurns, summaryJobOf, summaryJobsOf,
} = await import(pathToFileURL(process.argv[1]).href);
const counts = {
  requests: 3, verifiedRequests: 2, unverifiedRequests: 1, promptTokens: 10,
  uncachedInputTokens: 5, outputTokens: 7, cacheReadTokens: 1, cacheWriteTokens: null, reasoningTokens: 2,
};
const bucket = (over = {}) => ({ ...counts, unverifiedReasons: { missing: 1 }, ...over });
const turnBase = () => ({ ...bucket(), turnId: "t1", providers: ["anthropic"], models: ["m"] });
const summaryBase = () => ({
  ...bucket(), jobId: "j1", turnId: "t1", kind: "compaction", reason: "threshold", origin: "user",
  providers: ["anthropic"], models: ["m"],
});
const thrown = (fn) => { try { fn(); return "ok"; } catch (error) { return error.message; } };
const results = {
  counts: [
    [0, 1, -1, 1.5, "1", null, Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER + 1].map(isCount),
    [bucketOf(bucket()), bucketOf(null), bucketOf([]), bucketOf("x"), bucketOf(bucket({ requests: "3" }))]
      .map(value => value === null ? null : [value.requests, value.costUsd, value.costSource]),
  ],
  bucket: [
    bucketOf(bucket({ verifiedRequests: 3 })),
    bucketOf(bucket({ unverifiedRequests: 5 })),
    bucketOf(bucket({ cacheReadTokens: -1 })),
    bucketOf(bucket({ cacheReadTokens: 0 })),
    bucketOf({ ...bucket(), unverifiedReasons: [] }),
    bucketOf({ ...bucket(), unverifiedReasons: { missing: 2 } }),
    bucketOf({ ...bucket(), unverifiedReasons: { missing: "1" } }),
    bucketOf({ ...bucket(), unverifiedReasons: null }),
  ].map(value => value ? [value.requests, value.unreportedRequests] : null),
  reasons: [
    (() => {
      const reasons = JSON.parse('{"missing": 1, "__proto__": 2}');
      const value = bucketOf(bucket({ requests: 5, verifiedRequests: 2, unverifiedRequests: 3, unverifiedReasons: reasons }));
      return [
        value !== null,
        Object.keys(value.unverifiedReasons),
        Object.getPrototypeOf(value.unverifiedReasons),
        value.unverifiedReasons["__proto__"],
        value.unreportedRequests,
      ];
    })(),
    (() => {
      const reasons = {};
      for (let index = 1; index <= 25; index += 1) reasons["r" + index] = 1;
      const value = bucketOf(bucket({ requests: 25, verifiedRequests: 0, unverifiedRequests: 25, unverifiedReasons: reasons }));
      const keys = Object.keys(value.unverifiedReasons);
      return [keys.length, keys.slice(0, 3), keys.at(20), value.unverifiedReasons[keys.at(20)], value.unreportedRequests];
    })(),
    (() => {
      const reasons = {};
      for (let index = 1; index <= 19; index += 1) reasons["r" + index] = 1;
      reasons["其他 1 种原因"] = 1;
      reasons.extra = 1;
      const value = bucketOf(bucket({ requests: 21, verifiedRequests: 0, unverifiedRequests: 21, unverifiedReasons: reasons }));
      const keys = Object.keys(value.unverifiedReasons);
      return [keys.length, keys.at(-1), keys.at(-2), value.unverifiedReasons[keys.at(-1)]];
    })(),
  ],
  unreported: [
    [1, 0, "1"].map(unreported => {
      const value = bucketOf(bucket({ unreportedRequests: unreported }));
      return value ? value.unreportedRequests : null;
    }),
  ],
  cache: [
    [undefined, null, { missedTokens: 3, missCount: 2 }, { missedTokens: 3 }, "x", []].map(value => {
      const result = cacheWasteOf(value);
      return result === undefined ? "undefined" : result;
    }),
  ],
  turns: [
    (() => {
      const value = turnOf({
        ...turnBase(), startedAt: "2026-11-23T08:00:00Z",
        completedAt: "2026-11-23T08:01:00+08:00", status: "completed",
      });
      return [
        value.turnId, value.providers, value.models, value.startedAt, value.completedAt,
        value.status, value.unreportedRequests, "skillIds" in value, "compactionPolicy" in value,
      ];
    })(),
    [
      turnOf({ ...bucket(), turnId: "", providers: [], models: [] }),
      turnOf({ ...bucket(), turnId: "x".repeat(129), providers: [], models: [] }),
      turnOf({ ...bucket(), turnId: "t", providers: [1], models: [] }),
      turnOf({ ...bucket(), turnId: "t", providers: [], models: [null] }),
    ].map(value => value === null ? null : "kept"),
    [turnOf({ ...turnBase(), status: "unknown" }), turnOf({ ...turnBase(), status: 42 })]
      .map(value => value.status ?? "missing"),
    (() => {
      const value = turnOf({ ...turnBase(), startedAt: "bad", completedAt: "2026-11-23T08:00:00Z" });
      return [value.startedAt ?? null, value.completedAt, Object.hasOwn(value, "startedAt")];
    })(),
    (() => {
      const value = turnOf({
        ...bucket(), turnId: "t",
        providers: Array.from({ length: 10 }, (_, index) => "p" + index), models: ["m"],
      });
      return [value.providers.length, value.providers.at(-1)];
    })(),
  ],
  skills: [
    turnOf({ ...turnBase(), skillIds: ["a", "a", "", "x".repeat(201), "b"] }).skillIds,
    turnOf({ ...turnBase(), skillIds: "a" }).skillIds ?? "missing",
    turnOf({ ...turnBase(), skillIds: [] }).skillIds ?? "missing",
    (() => {
      const value = turnOf({ ...turnBase(), skillIds: Array.from({ length: 12 }, (_, index) => "s" + index) });
      return [value.skillIds.length, value.skillIds.at(-1)];
    })(),
  ],
  policy: [
    turnOf({ ...turnBase(), compactionPolicy: {
      enabled: true, triggerPercent: 80, keepRecentTokens: 100000, provider: "openai", model: "gpt-5", effort: "high",
    } }).compactionPolicy,
    [
      {}, { enabled: "true" }, { triggerPercent: 0 }, { triggerPercent: 1.5 }, { triggerPercent: 101 },
      { keepRecentTokens: 0 }, { keepRecentTokens: 1000001 }, { provider: "x" }, { model: "" },
      { model: " a " }, { model: "a".repeat(201) }, { effort: "huge" }, { extra: 1 },
    ].map(policy => turnOf({ ...turnBase(), compactionPolicy: policy }).compactionPolicy === undefined ? "dropped" : "kept"),
    [
      turnOf({ ...turnBase(), compactionPolicy: { provider: null, model: null, effort: null, triggerPercent: 50 } }).compactionPolicy,
      turnOf({ ...turnBase(), compactionPolicy: { enabled: true, triggerPercent: null } }).compactionPolicy === undefined ? "dropped" : "kept",
    ],
  ],
  verify: [
    [
      thrown(() => verifyUsageTurns([], 0)),
      thrown(() => verifyUsageTurns([], undefined)),
      thrown(() => verifyUsageTurns([{ turnId: "a" }, { turnId: "b" }], 2)),
      thrown(() => verifyUsageTurns([{ turnId: "a".repeat(50) }, { turnId: "a".repeat(50) }], 2)),
      thrown(() => verifyUsageTurns([{ turnId: "a" }], 2)),
      thrown(() => verifyUsageTurns([{ turnId: "a" }, { turnId: "b" }], undefined)),
    ],
  ],
  summary: [
    (() => {
      const job = summaryJobOf({ ...summaryBase(), kind: null, origin: null, active: false, throughTurnId: null });
      return [job.kind, job.reason, job.origin, "active" in job, job.throughTurnId, job.jobId];
    })(),
    [
      { kind: "other" }, { reason: "manual" }, { origin: "system" }, { active: "yes" }, { active: null },
      { jobId: "" }, { jobId: "x".repeat(129) }, { throughTurnId: "x".repeat(129) }, { providers: "a" },
    ].map(over => summaryJobOf({ ...summaryBase(), ...over }) === null ? "null" : "kept"),
    (() => {
      const job = summaryJobOf({ ...summaryBase(), active: true, throughTurnId: "u1" });
      return [job.active, job.throughTurnId, "throughTurnId" in job];
    })(),
    (() => {
      const { turnId, ...rest } = summaryBase();
      return summaryJobOf(rest);
    })(),
  ],
  jobs: [
    Object.keys(summaryJobsOf({})),
    [
      thrown(() => summaryJobsOf({ summaryJobs: {} })),
      thrown(() => summaryJobsOf({ summaryJobs: [], summaryJobCount: -1 })),
      thrown(() => summaryJobsOf({ summaryJobs: [], summaryJobsTruncated: "yes" })),
      thrown(() => summaryJobsOf({ summaryJobs: [{ ...summaryBase(), kind: "other" }] })),
    ],
    (() => {
      const meta = summaryJobsOf({
        summaryJobs: [summaryBase(), { ...summaryBase(), jobId: "j2" }, { ...summaryBase(), jobId: "j3" }],
        summaryJobCount: 3,
      });
      return [meta.summaryJobs.length, meta.summaryJobCount, meta.summaryJobsTruncated];
    })(),
    (() => {
      const meta = summaryJobsOf({ summaryJobs: [summaryBase()], summaryJobCount: 5 });
      return [meta.summaryJobCount, meta.summaryJobsTruncated];
    })(),
    (() => {
      const many = Array.from({ length: 60 }, (_, index) => ({ ...summaryBase(), jobId: "j" + index }));
      const meta = summaryJobsOf({ summaryJobs: many, summaryJobCount: 60 });
      return [
        meta.summaryJobs.length, meta.summaryJobCount, meta.summaryJobsTruncated,
        meta.summaryJobs[0].jobId, meta.summaryJobs.at(-1).jobId,
      ];
    })(),
    thrown(() => summaryJobsOf({ summaryJobs: [summaryBase(), summaryBase()] })),
    thrown(() => summaryJobsOf({ summaryJobs: [summaryBase(), { ...summaryBase(), jobId: "j2" }], summaryJobCount: 1 })),
    (() => {
      const meta = summaryJobsOf({ summaryJobs: [summaryBase()], summaryJobCount: 2, summaryJobsTruncated: false });
      return meta.summaryJobsTruncated;
    })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_COUNTS = (
    [True, True, False, False, False, False, True, False],
    [[3, None, "unavailable"], None, None, None, None],
)
EXPECTED_BUCKET = (None, None, None, [3, 1], None, None, None, None)
EXPECTED_REASONS = (
    [True, ["missing", "__proto__"], None, 2, 1],
    [21, ["r1", "r2", "r3"], "其他 5 种原因", 5, 0],
    [21, "其他 1 种原因 ", "其他 1 种原因", 1],
)
EXPECTED_UNREPORTED = ([1, None, None],)
EXPECTED_CACHE = (["undefined", None, {"missedTokens": 3, "missCount": 2}, None, None, None],)
EXPECTED_TURNS = (
    ["t1", ["anthropic"], ["m"], "2026-11-23T08:00:00Z", "2026-11-23T08:01:00+08:00", "completed", 1, False, False],
    [None, None, None, None],
    ["missing", "missing"],
    [None, "2026-11-23T08:00:00Z", False],
    [8, "p7"],
)
EXPECTED_SKILLS = (["a", "b"], "missing", "missing", [10, "s9"])
EXPECTED_POLICY = (
    {"enabled": True, "triggerPercent": 80, "keepRecentTokens": 100000, "provider": "openai", "model": "gpt-5", "effort": "high"},
    ["dropped"] * 13,
    [{"triggerPercent": 50, "provider": None, "model": None, "effort": None}, "dropped"],
)
EXPECTED_VERIFY = (
    ["ok", "ok", "ok", "回合用量条目标识重复：" + "a" * 40, "回合用量条目数不一致：声明 2 个，实际读取 1 个", "ok"],
)
EXPECTED_SUMMARY = (
    [None, "threshold", None, False, None, "j1"],
    ["null"] * 9,
    [True, "u1", True],
    None,
)
EXPECTED_JOBS = (
    [],
    ["内核返回的摘要任务用量格式无法识别"] * 4,
    [3, 3, False],
    [5, True],
    [50, 60, True, "j10", "j59"],
    "摘要任务用量条目标识重复：j1",
    "内核返回的摘要任务计数与明细不一致",
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
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        shared = (ROOT / SHARED).as_uri()
        target = base / "usageMapping.ts"
        target.write_text(
            _read(USAGE)
            .replace('from "@boss-harness/shared"', f'from "{shared}"')
            .replace('from "./timeFormat"', f'from "{shared}"'),
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
                "Node 用量映射试算失败，请核对 Node.js 24+ 与 usageMapping.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的用量映射结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回用量映射矩阵")
    for key in ("counts", "bucket", "reasons", "unreported", "cache", "turns", "skills", "policy", "verify", "summary", "jobs"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"用量映射{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"用量映射{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["counts"], EXPECTED_COUNTS, "计数")
    checked += _compare(payload["bucket"], EXPECTED_BUCKET, "桶校验")
    checked += _compare(payload["reasons"], EXPECTED_REASONS, "原因")
    checked += _compare(payload["unreported"], EXPECTED_UNREPORTED, "未上报")
    checked += _compare(payload["cache"], EXPECTED_CACHE, "缓存")
    checked += _compare(payload["turns"], EXPECTED_TURNS, "回合")
    checked += _compare(payload["skills"], EXPECTED_SKILLS, "技能")
    checked += _compare(payload["policy"], EXPECTED_POLICY, "策略")
    checked += _compare(payload["verify"], EXPECTED_VERIFY, "分页校验")
    checked += _compare(payload["summary"], EXPECTED_SUMMARY, "摘要任务")
    checked += _compare(payload["jobs"], EXPECTED_JOBS, "任务列表")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_usage_mapping.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_usage_mapping.py")
    if "共 53 项结构、40 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_usage_mapping.py 检查 53 项结构、40 项行为")
    return 2


def check_usage_mapping() -> tuple[int, int]:
    structure = _expect(USAGE_FRAGMENTS, _read(USAGE), USAGE)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_usage_mapping()
    except (OSError, ValueError) as error:
        print(f"用量映射规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量映射规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
