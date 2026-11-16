import type {
  ContextBranchSummaryIssue, ContextCompactionJobStatus, ContextReadResponse,
  SystemPromptInfo, SystemPromptSectionInfo, WorkspaceInstructionsState,
} from "@boss-harness/protocol";
import { compactionReferenceOf } from "./contextJob";

/**
 * `context/read` 回执的形状校验。
 *
 * 上下文面板直接渲染回执：必填数字参与预算比例与容量展示，`systemPromptInfo`
 * 与 `branchSummaryIssues` 会被 `.map` / `.slice` 消费，工作区说明按 `status`
 * 分支展示。任一字段畸形都可能让面板渲染抛错并落入应用级错误边界；无法识别
 * 的必填字段整体拒绝，展示型可选字段逐项收敛为缺失，不展示部分可疑数据。
 */
const ID_LIMIT = 200;
const TEXT_LIMIT = 4096;
const MAX_SECTIONS = 64;
const MAX_ISSUES = 20;
const REQUEST_SOURCES: ReadonlySet<string> = new Set(["active", "preview", "default"]);
const INSTRUCTION_STATUSES: ReadonlySet<string> = new Set(["loaded", "empty", "too_large", "unreadable"]);
const CORE_COUNTS = [
  "estimatedInputTokens", "contextWindow", "outputReserve", "inputBudget",
  "messageCount", "requestedOutputTokens", "modelMaxOutputTokens",
] as const;
const CORE_TEXTS = ["estimateMethod", "capabilitySource", "model", "provider"] as const;
const CORE_FLAGS = ["capacityIsEstimate", "withinBudget", "usageApplied"] as const;

const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const isText = (value: unknown, limit: number): value is string =>
  typeof value === "string" && value.length <= limit;
const plainRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

function invalid(): never {
  throw new Error("上下文预算回执无法识别");
}

/** 会话标识或可选短字符串；缺失、`null` 与非法值都按缺失处理。 */
function optionalId(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT ? value : undefined;
}

/** `string | null` 可选字段：保留 `null` 语义，非法值按缺失。标识类字段不接受空串。 */
function optionalNullableText(value: unknown, limit: number, allowEmpty = false): string | null | undefined {
  if (value === null) return null;
  if (typeof value !== "string" || value.length > limit || (!allowEmpty && value.length === 0)) return undefined;
  return value;
}

function workspaceInstructionsOf(value: unknown): WorkspaceInstructionsState | null | undefined {
  if (value === undefined || value === null) return value;
  const raw = plainRecord(value);
  if (!raw) return undefined;
  if (typeof raw.path !== "string" || raw.path.length === 0 || raw.path.length > TEXT_LIMIT) return undefined;
  if (typeof raw.status !== "string" || !INSTRUCTION_STATUSES.has(raw.status)) return undefined;
  if (raw.bytes !== null && !isCount(raw.bytes)) return undefined;
  if (!isCount(raw.limitBytes)) return undefined;
  return {
    path: raw.path,
    status: raw.status as WorkspaceInstructionsState["status"],
    bytes: raw.bytes as number | null,
    limitBytes: raw.limitBytes,
  };
}

function systemPromptOf(value: unknown): SystemPromptInfo | undefined {
  if (value === undefined) return undefined;
  const raw = plainRecord(value);
  if (!raw || !isCount(raw.bytes)) return undefined;
  if (raw.sections === undefined) return { bytes: raw.bytes };
  if (!Array.isArray(raw.sections) || raw.sections.length > MAX_SECTIONS) return undefined;
  const sections: SystemPromptSectionInfo[] = [];
  for (const item of raw.sections) {
    const section = plainRecord(item);
    if (!section) continue;
    if (typeof section.id !== "string" || section.id.length === 0 || section.id.length > ID_LIMIT) continue;
    if (!isText(section.title, TEXT_LIMIT) || !isCount(section.bytes)) continue;
    sections.push({ id: section.id, title: section.title, bytes: section.bytes });
  }
  return { bytes: raw.bytes, sections };
}

function issuesOf(value: unknown): ContextBranchSummaryIssue[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value)) return undefined;
  const issues: ContextBranchSummaryIssue[] = [];
  for (const item of value) {
    const issue = plainRecord(item);
    if (!issue) continue;
    // 记录本身缺少 id 时协议允许空字符串，不能按缺失丢弃。
    if (typeof issue.entryId !== "string" || issue.entryId.length > ID_LIMIT) continue;
    if (typeof issue.reason !== "string" || issue.reason.length === 0 || issue.reason.length > TEXT_LIMIT) continue;
    issues.push({ entryId: issue.entryId, reason: issue.reason });
  }
  return issues.slice(0, MAX_ISSUES);
}

/**
 * 解析 `context/read` 回执；`expectedThreadId` 必须与回执归属一致。
 * 必填字段缺失或类型不符时抛出「上下文预算回执无法识别」，调用方按读取失败
 * 处理并保留上一次成功状态。
 */
export function contextReadOf(value: unknown, expectedThreadId: string): ContextReadResponse {
  const raw = plainRecord(value);
  if (!raw) invalid();
  if (typeof raw.threadId !== "string" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT
    || raw.threadId !== expectedThreadId) invalid();
  if (typeof raw.requestSource !== "string" || !REQUEST_SOURCES.has(raw.requestSource)) invalid();
  for (const key of CORE_COUNTS) if (!isCount(raw[key])) invalid();
  for (const key of CORE_TEXTS) if (!isText(raw[key], TEXT_LIMIT)) invalid();
  for (const key of CORE_FLAGS) if (typeof raw[key] !== "boolean") invalid();
  if (raw.usage !== null && !plainRecord(raw.usage)) invalid();
  if (raw.checkpoint !== null && !plainRecord(raw.checkpoint)) invalid();

  const result: ContextReadResponse = {
    threadId: raw.threadId,
    estimatedInputTokens: raw.estimatedInputTokens as number,
    estimateMethod: raw.estimateMethod as string,
    contextWindow: raw.contextWindow as number,
    outputReserve: raw.outputReserve as number,
    inputBudget: raw.inputBudget as number,
    messageCount: raw.messageCount as number,
    requestedOutputTokens: raw.requestedOutputTokens as number,
    modelMaxOutputTokens: raw.modelMaxOutputTokens as number,
    capabilitySource: raw.capabilitySource as string,
    capacityIsEstimate: raw.capacityIsEstimate as boolean,
    withinBudget: raw.withinBudget as boolean,
    model: raw.model as string,
    provider: raw.provider as string,
    usageApplied: raw.usageApplied as boolean,
    requestSource: raw.requestSource as ContextReadResponse["requestSource"],
    checkpoint: raw.checkpoint as ContextReadResponse["checkpoint"],
    usage: raw.usage as ContextReadResponse["usage"],
  };

  const turnId = optionalId(raw.turnId);
  if (turnId !== undefined) result.turnId = turnId;
  const summaryAvailable = raw.summaryAvailable;
  if (typeof summaryAvailable === "boolean") result.summaryAvailable = summaryAvailable;
  const checkpointIssue = raw.checkpointIssue;
  if (typeof checkpointIssue === "string" && checkpointIssue.length <= TEXT_LIMIT) result.checkpointIssue = checkpointIssue;
  if (raw.summaryUsage === null) result.summaryUsage = null;
  else if (plainRecord(raw.summaryUsage)) result.summaryUsage = { ...raw.summaryUsage as Record<string, unknown> };
  if (raw.lastBudget === null) result.lastBudget = null;
  else if (plainRecord(raw.lastBudget)) result.lastBudget = { ...raw.lastBudget as Record<string, unknown> } as unknown as ContextReadResponse["lastBudget"];
  const breakdown = plainRecord(raw.breakdown);
  if (breakdown) result.breakdown = { ...breakdown } as ContextReadResponse["breakdown"];
  const reasoningEffort = optionalNullableText(raw.reasoningEffort, ID_LIMIT);
  if (reasoningEffort !== undefined) result.reasoningEffort = reasoningEffort;
  const requestFingerprint = optionalNullableText(raw.requestFingerprint, ID_LIMIT);
  if (requestFingerprint !== undefined) result.requestFingerprint = requestFingerprint;
  const usageAnchorTurnId = optionalNullableText(raw.usageAnchorTurnId, ID_LIMIT);
  if (usageAnchorTurnId !== undefined) result.usageAnchorTurnId = usageAnchorTurnId;

  // 摘要任务引用沿用既有严格校验：非法引用会让面板把占用状态写死并持续轮询。
  const reference = compactionReferenceOf(raw.compactionJob);
  if (reference !== undefined) result.compactionJob = reference as { jobId: string; status: ContextCompactionJobStatus; active: boolean };
  // 分支摘要条目由分支读取路径逐项校验；这里只保留数组形状，避免非数组值进入会话区。
  if (Array.isArray(raw.branchSummaries)) result.branchSummaries = raw.branchSummaries as ContextReadResponse["branchSummaries"];

  // 问题清单与损坏总数必须互相自洽：总数不能少于可见条数，否则两字段都丢弃。
  const issues = issuesOf(raw.branchSummaryIssues);
  const issueTotal = raw.branchSummaryIssueCount;
  if (issues !== undefined) {
    if (issueTotal === undefined) {
      result.branchSummaryIssues = issues;
    } else if (isCount(issueTotal) && issueTotal >= issues.length) {
      result.branchSummaryIssues = issues;
      result.branchSummaryIssueCount = issueTotal;
    }
  } else if (isCount(issueTotal)) {
    result.branchSummaryIssueCount = issueTotal;
  }

  const instructions = workspaceInstructionsOf(raw.workspaceInstructions);
  if (instructions !== undefined) result.workspaceInstructions = instructions;
  const systemPrompt = systemPromptOf(raw.systemPromptInfo);
  if (systemPrompt !== undefined) result.systemPromptInfo = systemPrompt;
  return result;
}