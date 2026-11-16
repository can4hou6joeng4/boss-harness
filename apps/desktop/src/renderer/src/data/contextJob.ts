import type { ContextCompactJob, ContextCompactionJobStatus } from "@boss-harness/protocol";
import { safeSlice } from "@boss-harness/shared";

const COMPACTION_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "failed", "cancelled"]);
const COMPACTION_REASONS: ReadonlySet<string> = new Set(["threshold", "budget", "overflow"]);
const JOB_ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;
const SOURCE_DIGEST = /^[0-9a-f]{64}$/;
const ID_LIMIT = 200;
const CODE_LIMIT = 120;
const MESSAGE_LIMIT = 4096;
const MODEL_LIMIT = 200;
const EFFORT_LIMIT = 64;
const MAX_ABANDONED_TURNS = 10_000;

const isId = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;
const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const plainRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

function invalid(): never {
  throw new Error("摘要任务回执无法识别");
}

/**
 * `context/read.compactionJob` 的已校验引用。
 * `null` 表示内核没有保留任务，`undefined` 表示旧内核未提供发现信息。
 */
export interface CompactionReference {
  jobId: string;
  status: ContextCompactionJobStatus;
  active: boolean;
}

/**
 * 校验摘要任务引用。缺 `jobId`、未知状态或非布尔 `active` 的引用会让面板把占用状态
 * 写死并持续轮询，必须整体拒绝，不能按合法对象直接使用。
 */
export function compactionReferenceOf(value: unknown): CompactionReference | null | undefined {
  if (value === undefined || value === null) return value;
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("摘要任务引用无法识别");
  const raw = value as Record<string, unknown>;
  if (typeof raw.jobId !== "string" || !JOB_ID_PATTERN.test(raw.jobId)
    || typeof raw.status !== "string" || !COMPACTION_STATUSES.has(raw.status)
    || typeof raw.active !== "boolean") throw new Error("摘要任务引用无法识别");
  return { jobId: raw.jobId, status: raw.status as ContextCompactionJobStatus, active: raw.active };
}

/**
 * 摘要任务的自读校验与收敛。
 *
 * 分支摘要与手动 / 自动压缩共用同一条任务通道（`context/compaction*` 通知与
 * `context/read.compactionJob` 引用），`kind` 缺省表示上下文压缩。身份、来源摘要、
 * 状态或 `kind` 不合法时返回 `null`：通知按不适用丢弃，回执由调用方按归属不一致
 * 处理。展示字段（触发原因、进度计数、模型信息、失败说明）逐项收敛：
 * `ContextPanel` 把计数交给 `toLocaleString`、把 `message` 等作为 React 子节点渲染，
 * 对象或 `null` 会让整个面板落入错误边界；未知 `reason` 又会把手动任务显示成自动任务。
 * 缺失或 `null` 的可选字段按旧内核未提供处理；`result` 历史快照面板不渲染，
 * 存活状态由独立读取维护，因此不进入状态。
 */
export function contextJobOf(value: unknown): ContextCompactJob | null {
  const raw = plainRecord(value);
  if (!raw || !isId(raw.threadId) || typeof raw.jobId !== "string" || !JOB_ID_PATTERN.test(raw.jobId)
    || typeof raw.sourceDigest !== "string" || !SOURCE_DIGEST.test(raw.sourceDigest)
    || !isId(raw.throughTurnId)
    || typeof raw.status !== "string" || !COMPACTION_STATUSES.has(raw.status)
    || (raw.kind !== undefined && raw.kind !== "branchSummary")) return null;
  const job: ContextCompactJob = {
    jobId: raw.jobId,
    threadId: raw.threadId,
    throughTurnId: raw.throughTurnId,
    sourceDigest: raw.sourceDigest,
    status: raw.status as ContextCompactionJobStatus,
  };
  if (raw.kind === "branchSummary") job.kind = "branchSummary";
  if (raw.reason !== undefined && raw.reason !== null) {
    if (typeof raw.reason !== "string" || !COMPACTION_REASONS.has(raw.reason)) invalid();
    job.reason = raw.reason as ContextCompactJob["reason"];
  }
  const text = (key: string, limit: number): string | undefined => {
    const field = raw[key];
    if (field === undefined || field === null) return undefined;
    if (typeof field !== "string") invalid();
    return safeSlice(field, limit);
  };
  const id = (key: string): string | undefined => {
    const field = raw[key];
    if (field === undefined || field === null) return undefined;
    if (!isId(field)) invalid();
    return field;
  };
  const count = (key: string): number | undefined => {
    const field = raw[key];
    if (field === undefined || field === null) return undefined;
    if (!isCount(field)) invalid();
    return field;
  };
  const code = text("code", CODE_LIMIT);
  if (code !== undefined) job.code = code;
  const message = text("message", MESSAGE_LIMIT);
  if (message !== undefined) job.message = message;
  const turnId = id("turnId");
  if (turnId !== undefined) job.turnId = turnId;
  const summaryProvider = text("summaryProvider", MODEL_LIMIT);
  if (summaryProvider !== undefined) job.summaryProvider = summaryProvider;
  const summaryModel = text("summaryModel", MODEL_LIMIT);
  if (summaryModel !== undefined) job.summaryModel = summaryModel;
  const summaryEffort = text("summaryEffort", EFFORT_LIMIT);
  if (summaryEffort !== undefined) job.summaryEffort = summaryEffort;
  const modelRequestCount = count("modelRequestCount");
  if (modelRequestCount !== undefined) job.modelRequestCount = modelRequestCount;
  const processedCharacters = count("processedCharacters");
  if (processedCharacters !== undefined) job.processedCharacters = processedCharacters;
  const totalCharacters = count("totalCharacters");
  if (totalCharacters !== undefined) job.totalCharacters = totalCharacters;
  const retainedItemCount = count("retainedItemCount");
  if (retainedItemCount !== undefined) job.retainedItemCount = retainedItemCount;
  const estimatedRetainedTokens = count("estimatedRetainedTokens");
  if (estimatedRetainedTokens !== undefined) job.estimatedRetainedTokens = estimatedRetainedTokens;
  const firstKeptItemId = id("firstKeptItemId");
  if (firstKeptItemId !== undefined) job.firstKeptItemId = firstKeptItemId;
  const targetTurnId = id("targetTurnId");
  if (targetTurnId !== undefined) job.targetTurnId = targetTurnId;
  const fromTurnId = id("fromTurnId");
  if (fromTurnId !== undefined) job.fromTurnId = fromTurnId;
  if (raw.requestRejected !== undefined && raw.requestRejected !== null) {
    if (typeof raw.requestRejected !== "boolean") invalid();
    job.requestRejected = raw.requestRejected;
  }
  if (raw.abandonedTurnIds !== undefined && raw.abandonedTurnIds !== null) {
    if (!Array.isArray(raw.abandonedTurnIds) || raw.abandonedTurnIds.length > MAX_ABANDONED_TURNS) invalid();
    job.abandonedTurnIds = raw.abandonedTurnIds.map(value => {
      if (!isId(value)) invalid();
      return value;
    });
  }
  return job;
}

/** 只返回本面板管理的手动 / 自动压缩任务；分支摘要返回 null。 */
export function manualCompactionJob(job: ContextCompactJob): ContextCompactJob | null {
  return job.kind === "branchSummary" ? null : job;
}
