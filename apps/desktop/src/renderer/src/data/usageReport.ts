import { safeSlice } from "@boss-harness/shared";
import type { ThreadUsageBucket, ThreadUsageCacheWaste, ThreadUsageSummaryJob, ThreadUsageTurn } from "@boss-harness/protocol";
import type { UsageView } from "./useThreadUsage";
import { turnTimingLabel } from "./turnTiming";

/**
 * 会话用量的共享文案与 CSV 导出。
 *
 * 数值只来自 `thread/usage/read` 已校验的 provider 上报：`verifiedRequests === 0`
 * 或字段为 `null` 时导出空单元格，不把“未知”写成 0；费用无价目来源，不输出。
 */

/** 内核 usage.verify_usage 的不计入原因；未知原因原样显示。 */
export const USAGE_REASONS: Record<string, string> = {
  missing: "未上报用量", invalidType: "字段类型错误", negative: "含负数", outOfRange: "超出合理范围",
  inconsistent: "字段互相矛盾", zero: "全部为零", unknownProvider: "未知 provider",
};

/** 摘要任务来源；内核未记录 origin 时只显示任务类型。 */
export function usageJobSource(job: ThreadUsageSummaryJob): string {
  return job.kind === "branchSummary" ? "分支摘要"
    : job.origin === "user" ? "手动压缩" : job.origin === "model" ? "自动压缩" : "摘要任务";
}

/** 摘要任务触发原因。 */
export const USAGE_JOB_REASONS: Record<string, string> = {
  threshold: "触达阈值", budget: "预算不足", overflow: "上下文溢出",
};

/** provider 未上报 usage 的请求数（旧内核不返回时为 0，仍由原因 missing 标注）。 */
export function usageUnreported(bucket: ThreadUsageBucket): number {
  return bucket.unreportedRequests ?? 0;
}

/** 没有可验证请求时数值不可知；调用方用空值或“—”展示，不把 0 当成上报事实。 */
export function usageAmount(bucket: ThreadUsageBucket, value: number | null): number | null {
  return bucket.verifiedRequests === 0 || value === null ? null : value;
}

/** 未计入原因与次数，保持内核返回的顺序。 */
export function usageReasonEntries(bucket: ThreadUsageBucket): Array<{ label: string; count: number }> {
  return Object.entries(bucket.unverifiedReasons)
    .map(([reason, count]) => ({ label: USAGE_REASONS[reason] ?? reason, count }));
}

/** 单行摘要片段：压缩空白后截断，空内容回退到给定文案。 */
export function usageClip(text: string | undefined, fallback: string): string {
  const value = (text ?? "").replace(/\s+/g, " ").trim();
  if (!value) return fallback;
  return value.length > 40 ? safeSlice(value, 40) + "…" : value;
}

export const USAGE_CSV_COLUMNS = [
  "类别", "回合", "说明", "模型", "provider", "请求", "计入请求", "未计入请求", "未上报请求",
  "输入", "未缓存输入", "缓存读取", "缓存写入", "输出", "推理", "未计入原因",
] as const;

/** 导出所需的已加载数据；`ThreadUsageState["data"]` 结构上可直接传入。 */
export interface UsageReportData {
  view: UsageView;
  turnCount: number;
  turns: ThreadUsageTurn[];
  truncated: boolean;
  summaryTasks: ThreadUsageBucket;
  totals: ThreadUsageBucket;
  summaryJobs?: ThreadUsageSummaryJob[];
  summaryJobCount?: number;
  summaryJobsTruncated?: boolean;
  cacheWaste?: ThreadUsageCacheWaste;
}

export interface UsageReportContext {
  /** 与界面一致：把回合 id 映射为“第 N 回合”。 */
  turnLabel: (turnId: string) => string;
  /** 该回合的用户输入，用于“说明”列。 */
  inputOf: (turnId: string) => string | undefined;
}

type Cell = string | number | null;

/**
 * 以 `= + - @`、制表符或回车开头的内容会被电子表格当成公式执行；
 * 导出时加前导单引号，保留原文但不让它在表格里运行。
 */
const FORMULA_PREFIX = /^[=+\-@\t\r]/;

function cell(value: Cell): string {
  if (value === null || value === "") return "";
  const text = String(value);
  const safe = FORMULA_PREFIX.test(text) ? `'${text}` : text;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

const emptyRow = (): Cell[] => Array.from({ length: USAGE_CSV_COLUMNS.length }, () => null);

function noteRow(category: string, note: string): Cell[] {
  const cells = emptyRow();
  cells[0] = category;
  cells[2] = note;
  return cells;
}

function bucketRow(bucket: ThreadUsageBucket, options: {
  category: string; note?: string; turn?: string; models?: string[]; providers?: string[];
}): Cell[] {
  const reasonText = usageReasonEntries(bucket).map(({ label, count }) => `${label} ${count} 次`).join("、");
  return [
    options.category,
    options.turn ?? "",
    options.note ?? "",
    (options.models ?? []).join("、"),
    (options.providers ?? []).join("、"),
    bucket.requests,
    bucket.verifiedRequests,
    bucket.unverifiedRequests,
    usageUnreported(bucket),
    usageAmount(bucket, bucket.promptTokens),
    usageAmount(bucket, bucket.uncachedInputTokens),
    usageAmount(bucket, bucket.cacheReadTokens),
    usageAmount(bucket, bucket.cacheWriteTokens),
    usageAmount(bucket, bucket.outputTokens),
    usageAmount(bucket, bucket.reasoningTokens),
    reasonText,
  ];
}

/**
 * 把当前视图的用量拼成 RFC 4180 CSV（CRLF 行尾，带表头）。
 * 行序与弹窗一致：合计、缓存未命中、摘要任务合计、摘要任务明细、每回合，最后是截断说明。
 * 只导出界面已经加载的数据，不额外读取，因此结果与屏幕上看到的范围一致。
 */
export function buildUsageCsv(data: UsageReportData, context: UsageReportContext): string {
  const rows: Cell[][] = [];
  rows.push(bucketRow(data.totals, {
    category: "本会话合计",
    note: data.view === "branch" ? "当前分支（只统计当前分支上的回合）" : "全部记录（包含已切离分支上的回合）",
  }));
  if (data.cacheWaste) {
    rows.push(noteRow("缓存未命中", `未命中 ${data.cacheWaste.missedTokens} token（${data.cacheWaste.missCount} 次）`));
  }
  if (data.summaryTasks.requests > 0) {
    rows.push(bucketRow(data.summaryTasks, { category: "摘要任务合计", note: "摘要任务不区分分支" }));
  }
  const jobs = data.summaryJobs ?? [];
  for (const job of jobs) {
    const note = [
      usageJobSource(job),
      job.reason ? USAGE_JOB_REASONS[job.reason] ?? job.reason : "",
      job.origin === "user" ? "手动" : job.origin === "model" ? "自动" : "",
      job.active ? "当前生效" : "",
      job.throughTurnId && job.throughTurnId !== job.turnId ? `摘要至 ${context.turnLabel(job.throughTurnId)}` : "",
    ].filter(Boolean).join(" · ");
    rows.push(bucketRow(job, {
      category: "摘要任务明细",
      note,
      turn: job.turnId ? context.turnLabel(job.turnId) : "",
      models: job.models,
      providers: job.providers,
    }));
  }
  for (const turn of data.turns) {
    const timing = turnTimingLabel(turn);
    const note = [usageClip(context.inputOf(turn.turnId), turn.turnId), timing ?? ""].filter(Boolean).join(" · ");
    rows.push(bucketRow(turn, {
      category: "回合",
      note,
      turn: context.turnLabel(turn.turnId),
      models: turn.models,
      providers: turn.providers,
    }));
  }
  if (data.truncated) {
    rows.push(noteRow("说明", `每回合用量仅包含前 ${data.turns.length} 个，共 ${data.turnCount} 个有记录的回合`));
  }
  if (data.summaryJobsTruncated) {
    const total = data.summaryJobCount ?? jobs.length;
    rows.push(noteRow("说明", `摘要任务明细仅包含最近 ${jobs.length} 个，共 ${total} 个`));
  }
  const lines = [USAGE_CSV_COLUMNS.join(","), ...rows.map(row => row.map(cell).join(","))];
  return lines.join("\r\n") + "\r\n";
}
