import type { ContextCompactJob, ContextCompactionJobStatus } from "@boss-harness/protocol";

const COMPACTION_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "failed", "cancelled"]);
const JOB_ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;

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
 * 会话摘要任务的自读校验。
 *
 * 分支摘要与手动 / 自动压缩共用同一条任务通道（`context/compaction*` 通知与
 * `context/read.compactionJob` 引用），`kind` 缺省表示上下文压缩。只接受这两种
 * 已知取值：其他值视为不可信响应，避免未知任务类型被当成本面板的手动摘要。
 */
export function isContextJob(value: unknown): value is ContextCompactJob {
  if (!value || typeof value !== "object") return false;
  const job = value as ContextCompactJob;
  return typeof job.threadId === "string" && typeof job.jobId === "string"
    && typeof job.sourceDigest === "string" && /^[0-9a-f]{64}$/.test(job.sourceDigest)
    && typeof job.throughTurnId === "string" && COMPACTION_STATUSES.has(job.status)
    && (job.kind === undefined || job.kind === "branchSummary");
}

/** 只返回本面板管理的手动 / 自动压缩任务；分支摘要返回 null。 */
export function manualCompactionJob(job: ContextCompactJob): ContextCompactJob | null {
  return job.kind === "branchSummary" ? null : job;
}
