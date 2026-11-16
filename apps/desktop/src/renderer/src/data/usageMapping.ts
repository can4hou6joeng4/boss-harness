import type {
  AutoCompactionPolicy, ThreadUsageBucket, ThreadUsageCacheWaste, ThreadUsageReadResponse,
  ThreadUsageSummaryJob, ThreadUsageTurn,
} from "@boss-harness/protocol";
import { safeSlice } from "@boss-harness/shared";
import { parseIsoDateTime } from "./timeFormat";

const COUNT_KEYS = ["requests", "verifiedRequests", "unverifiedRequests", "promptTokens",
  "uncachedInputTokens", "outputTokens"] as const;
const NULLABLE_KEYS = ["cacheReadTokens", "cacheWriteTokens", "reasoningTokens"] as const;
/** 未验证原因最多展示 20 项；合计校验仍覆盖全部键，避免截断掩盖矛盾。 */
const REASON_LIMIT = 20;

export const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;

export function bucketOf(value: unknown): ThreadUsageBucket | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!COUNT_KEYS.every(key => isCount(raw[key])) || !NULLABLE_KEYS.every(key => raw[key] === null || isCount(raw[key]))) return null;
  const requests = raw.requests as number, verified = raw.verifiedRequests as number;
  const unverified = raw.unverifiedRequests as number;
  // 内核每次请求恰好计入已验证或未验证之一；两项合计必须等于请求总数，否则分类无法解释差额。
  if (verified + unverified !== requests) return null;
  const reasons = raw.unverifiedReasons;
  if (!reasons || typeof reasons !== "object" || Array.isArray(reasons)) return null;
  // 空原型承接内核返回的任意原因键；普通对象会给 "__proto__" 赋值走 setter，丢掉该条数据。
  const unverifiedReasons: Record<string, number> = Object.create(null) as Record<string, number>;
  let reasonTotal = 0, keptReasons = 0;
  for (const [reason, amount] of Object.entries(reasons as Record<string, unknown>)) {
    if (!isCount(amount) || !Number.isSafeInteger(reasonTotal + amount)) return null;
    reasonTotal += amount;
    if (keptReasons < REASON_LIMIT) {
      unverifiedReasons[safeSlice(reason, 40)] = amount;
      keptReasons += 1;
    }
  }
  // 每个未验证请求恰好记录一次原因；展示截断不影响这里对全部键的合计校验。
  if (reasonTotal !== unverified) return null;
  // 新内核才返回 unreportedRequests（未上报 usage，unverifiedRequests 的子集）；旧内核缺省视为不区分。
  const unreported = raw.unreportedRequests;
  if (unreported !== undefined && (!isCount(unreported) || unreported > unverified)) return null;
  const bucket = {} as ThreadUsageBucket;
  for (const key of COUNT_KEYS) bucket[key] = raw[key] as number;
  for (const key of NULLABLE_KEYS) bucket[key] = raw[key] as number | null;
  if (unreported !== undefined) bucket.unreportedRequests = unreported;
  // 费用不展示：内核当前无可信价目来源，界面固定标注“未计价”。
  return { ...bucket, unverifiedReasons, costUsd: null, costSource: "unavailable" };
}

const strings = (value: unknown, limit: number): string[] | null => Array.isArray(value) && value.every(item => typeof item === "string")
  ? (value as string[]).slice(0, limit).map(item => safeSlice(item, 120)) : null;

/**
 * 缓存未命中估算；旧内核与「当前分支」视图不返回该字段。
 * 返回 undefined 表示字段缺失，null 表示字段存在但形状非法（由调用方整体报错）。
 */
export function cacheWasteOf(value: unknown): ThreadUsageCacheWaste | null | undefined {
  if (value === undefined) return undefined;
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!isCount(raw.missedTokens) || !isCount(raw.missCount)) return null;
  return { missedTokens: raw.missedTokens, missCount: raw.missCount };
}

const SKILL_LIMIT = 10;
const SKILL_ID_LIMIT = 200;

/** 与内核 _turn_skill_ids 一致：先校验、后计数，按 id 去重并最多 10 项；没有合法 id 时省略。 */
function skillIdsOf(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const ids: string[] = [];
  for (const item of value) {
    if (ids.length >= SKILL_LIMIT) break;
    if (typeof item === "string" && item.length > 0 && item.length <= SKILL_ID_LIMIT && !ids.includes(item)) ids.push(item);
  }
  return ids.length ? ids : undefined;
}

const POLICY_KEYS = ["enabled", "triggerPercent", "keepRecentTokens", "provider", "model", "effort"] as const;
const POLICY_PROVIDERS = new Set(["anthropic", "openai", "codex"]);
const POLICY_EFFORTS = new Set(["none", "minimal", "low", "medium", "high", "xhigh", "max"]);
const POLICY_MAX_TOKENS = 1_000_000;
const POLICY_MAX_MODEL = 200;

/**
 * 与内核 verified_policy 一致：只保留记录中实际存在且合法的字段；
 * 空对象、未知字段或任一非法值都按“未记录”处理，返回 undefined。
 * 非法策略只影响这个可选字段，不丢弃整页用量。
 */
function compactionPolicyOf(value: unknown): Partial<AutoCompactionPolicy> | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  const keys = Object.keys(raw);
  if (keys.length === 0 || keys.some(key => !(POLICY_KEYS as readonly string[]).includes(key))) return undefined;
  if ("enabled" in raw && typeof raw.enabled !== "boolean") return undefined;
  const trigger = raw.triggerPercent;
  if ("triggerPercent" in raw && !(typeof trigger === "number" && Number.isInteger(trigger)
    && trigger >= 1 && trigger <= 100)) return undefined;
  const keep = raw.keepRecentTokens;
  if ("keepRecentTokens" in raw && !(typeof keep === "number" && Number.isInteger(keep)
    && keep >= 1 && keep <= POLICY_MAX_TOKENS)) return undefined;
  const provider = raw.provider;
  if ("provider" in raw && provider !== null
    && (typeof provider !== "string" || !POLICY_PROVIDERS.has(provider))) return undefined;
  const model = raw.model;
  if ("model" in raw && model !== null
    && (typeof model !== "string" || !model.trim() || model.length > POLICY_MAX_MODEL || /\s/.test(model))) return undefined;
  const effort = raw.effort;
  if ("effort" in raw && effort !== null
    && (typeof effort !== "string" || !POLICY_EFFORTS.has(effort))) return undefined;
  const policy: Partial<AutoCompactionPolicy> = {};
  for (const key of POLICY_KEYS) if (key in raw) (policy as Record<string, unknown>)[key] = raw[key];
  return policy;
}

const TURN_STATUSES = new Set(["running", "completed", "interrupted", "blocked", "error"]);
const timestampOf = (value: unknown): string | undefined =>
  // 只接受带秒与时区的完整 ISO 时间，与工具来源和回合耗时共用同一判定；
  // 非法时间只影响耗时展示，不丢弃整行用量。
  typeof value === "string" && value.length <= 64 && parseIsoDateTime(value) ? value : undefined;

export function turnOf(value: unknown): ThreadUsageTurn | null {
  const bucket = bucketOf(value);
  if (!bucket) return null;
  const raw = value as Record<string, unknown>;
  const providers = strings(raw.providers, 8), models = strings(raw.models, 8);
  if (typeof raw.turnId !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(raw.turnId) || !providers || !models) return null;
  const compactionPolicy = compactionPolicyOf(raw.compactionPolicy);
  const skillIds = skillIdsOf(raw.skillIds);
  const timing: Partial<ThreadUsageTurn> = {};
  const startedAt = timestampOf(raw.startedAt), completedAt = timestampOf(raw.completedAt);
  if (startedAt) timing.startedAt = startedAt;
  if (completedAt) timing.completedAt = completedAt;
  if (typeof raw.status === "string" && TURN_STATUSES.has(raw.status)) timing.status = raw.status as ThreadUsageTurn["status"];
  return { ...bucket, turnId: raw.turnId, providers, models,
    ...(skillIds ? { skillIds } : {}),
    ...timing,
    ...(compactionPolicy ? { compactionPolicy } : {}) };
}

const idOrNull = (value: unknown): string | null | undefined => value === null ? null
  : typeof value === "string" && value.length > 0 && value.length <= 128 ? value : undefined;

export function summaryJobOf(value: unknown): ThreadUsageSummaryJob | null {
  const bucket = bucketOf(value);
  if (!bucket) return null;
  const raw = value as Record<string, unknown>;
  const providers = strings(raw.providers, 8), models = strings(raw.models, 8);
  const jobId = idOrNull(raw.jobId), turnId = idOrNull(raw.turnId);
  const kind = raw.kind === null ? null : raw.kind === "compaction" || raw.kind === "branchSummary" ? raw.kind : undefined;
  const reason = raw.reason === null ? null
    : raw.reason === "threshold" || raw.reason === "budget" || raw.reason === "overflow" ? raw.reason : undefined;
  const origin = raw.origin === null ? null : raw.origin === "user" || raw.origin === "model" ? raw.origin : undefined;
  const active = raw.active === undefined ? undefined : typeof raw.active === "boolean" ? raw.active : null;
  // 与协议一致：缺失时省略，null 表示分支摘要 / 无记录；只拒绝非空但非法的值。
  const throughTurnId = idOrNull(raw.throughTurnId);
  if (!jobId || !providers || !models || kind === undefined || turnId === undefined
    || reason === undefined || origin === undefined || active === null
    || (raw.throughTurnId !== undefined && throughTurnId === undefined)) return null;
  return { ...bucket, jobId, kind, turnId, reason, origin, providers, models,
    ...(throughTurnId !== undefined ? { throughTurnId } : {}),
    ...(active ? { active: true } : {}) };
}

/** 摘要任务明细的展示上限；内核当前也按 50 条截断，界面仍自行兜底。 */
const MAX_SUMMARY_JOBS = 50;

export interface SummaryJobsMeta {
  summaryJobs?: ThreadUsageSummaryJob[];
  summaryJobCount?: number;
  summaryJobsTruncated?: boolean;
}

/**
 * 摘要任务明细在每页重复返回；任一页形状不符即报错，展示时只取第一份。
 * 计数必须覆盖已接收明细，小于明细数是自相矛盾的快照；计数大于已展示明细
 * （含本地展示上限）时明细必然不完整，不能信任缺失或误报 false 的截断标记。
 */
export function summaryJobsOf(
  page: Pick<ThreadUsageReadResponse, "summaryJobs" | "summaryJobCount" | "summaryJobsTruncated">,
): SummaryJobsMeta {
  if (page.summaryJobs === undefined) return {};
  if (!Array.isArray(page.summaryJobs) || (page.summaryJobCount !== undefined && !isCount(page.summaryJobCount))
    || (page.summaryJobsTruncated !== undefined && typeof page.summaryJobsTruncated !== "boolean")) {
    throw new Error("内核返回的摘要任务用量格式无法识别");
  }
  const jobs = page.summaryJobs.slice(0, MAX_SUMMARY_JOBS).map(summaryJobOf);
  if (jobs.some(job => !job)) throw new Error("内核返回的摘要任务用量格式无法识别");
  const count = page.summaryJobCount ?? page.summaryJobs.length;
  if (count < page.summaryJobs.length) throw new Error("内核返回的摘要任务计数与明细不一致");
  return {
    summaryJobs: jobs as ThreadUsageSummaryJob[],
    summaryJobCount: count,
    summaryJobsTruncated: page.summaryJobsTruncated === true || count > jobs.length,
  };
}
