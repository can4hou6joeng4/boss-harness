import type { ContextCompactJob } from "@boss-harness/protocol";

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
    && typeof job.throughTurnId === "string" && ["running", "completed", "failed", "cancelled"].includes(job.status)
    && (job.kind === undefined || job.kind === "branchSummary");
}

/** 只返回本面板管理的手动 / 自动压缩任务；分支摘要返回 null。 */
export function manualCompactionJob(job: ContextCompactJob): ContextCompactJob | null {
  return job.kind === "branchSummary" ? null : job;
}
