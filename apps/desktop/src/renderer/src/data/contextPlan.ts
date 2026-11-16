import type { ContextCompactPlan } from "@boss-harness/protocol";

/**
 * `context/compact/plan` 回执的形状校验。
 *
 * 上下文面板直接渲染计划：`retainedTurnIds.length` 在渲染期调用数组方法，
 * 计数字段经 `toLocaleString`，条目 id 作为 React 子节点。内核回执来自旧版本
 * 或损坏记录时，缺字段会让面板抛 `TypeError`，对象字段会让 React 拒绝渲染，
 * 整个面板落入应用级错误边界。这里对展示与开始压缩所需的字段整体校验；
 * 面板不渲染的协议字段（`sourceItemIds`、`digestVersion`、`checkpointDigest`）
 * 缺失时保持旧内核兼容。
 */
const ID_LIMIT = 200;
const MAX_RETAINED_TURNS = 10_000;
const SOURCE_DIGEST = /^[0-9a-f]{64}$/;
const SELECTIONS: ReadonlySet<string> = new Set(["explicit", "keepRecentTokens"]);

const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const isId = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;
const plainRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

function invalid(): never {
  throw new Error("整理计划回执无法识别");
}

/** 面板展示与开始压缩实际读取的计划字段；不渲染的协议字段不进入界面状态。 */
export type ContextPlan = Pick<ContextCompactPlan,
  "threadId" | "throughTurnId" | "sourceDigest" | "sourceItemCount" | "firstItemId" | "lastItemId"
  | "retainedItemCount" | "retainedTurnIds" | "firstKeptItemId" | "estimatedRetainedTokens"> & {
  retentionUsageApplied: boolean;
  retentionUsageAnchorCount: number;
};

export interface ContextPlanExpectation {
  /** 计划请求的会话；回执必须属于它。 */
  threadId: string;
  /** 请求里的近期保留目标；回执声明同一选择方式时必须一致。 */
  keepRecentTokens: number;
}

/**
 * 校验并收敛一份整理计划回执。
 *
 * 身份、来源摘要、回合边界、计数与保留回合必须合法；`firstKeptItemId` 只允许
 * `null` 或合法 id，`retentionUsageApplied` 为真时锚点计数必须大于零，避免面板
 * 显示「使用了 0 个锚点校准」。无法识别时抛出统一错误，由调用方显示失败原因。
 */
export function contextPlanOf(value: unknown, expected: ContextPlanExpectation): ContextPlan {
  const raw = plainRecord(value);
  if (!raw || raw.threadId !== expected.threadId) invalid();
  if (!isId(raw.throughTurnId)) invalid();
  if (typeof raw.sourceDigest !== "string" || !SOURCE_DIGEST.test(raw.sourceDigest)) invalid();
  if (!isCount(raw.sourceItemCount) || raw.sourceItemCount < 1) invalid();
  if (!isId(raw.firstItemId) || !isId(raw.lastItemId)) invalid();
  if (!isCount(raw.retainedItemCount) || !isCount(raw.estimatedRetainedTokens)) invalid();
  if (!Array.isArray(raw.retainedTurnIds) || raw.retainedTurnIds.length > MAX_RETAINED_TURNS) invalid();
  const retainedTurnIds: string[] = [];
  for (const item of raw.retainedTurnIds) {
    if (!isId(item) || retainedTurnIds.includes(item)) invalid();
    retainedTurnIds.push(item);
  }
  let firstKeptItemId: string | null = null;
  if (raw.firstKeptItemId !== undefined && raw.firstKeptItemId !== null) {
    if (!isId(raw.firstKeptItemId)) invalid();
    firstKeptItemId = raw.firstKeptItemId;
  }
  if ((raw.retainedItemCount > 0) !== (firstKeptItemId !== null)) invalid();
  // 选择方式与保留目标只用于核对回执是否对应本次请求；旧内核缺失时按兼容处理。
  if (raw.selection !== undefined) {
    if (typeof raw.selection !== "string" || !SELECTIONS.has(raw.selection)) invalid();
    if (raw.selection === "keepRecentTokens" && raw.keepRecentTokens !== expected.keepRecentTokens) invalid();
  }
  if (raw.keepRecentTokens !== undefined && raw.keepRecentTokens !== null && !isCount(raw.keepRecentTokens)) invalid();
  // 来源条目清单不参与展示；出现时必须与声明的条目数一致，缺失时兼容旧内核。
  if (raw.sourceItemIds !== undefined) {
    if (!Array.isArray(raw.sourceItemIds) || raw.sourceItemIds.length !== raw.sourceItemCount) invalid();
    if (raw.sourceItemIds.some(item => !isId(item))) invalid();
  }
  if (raw.digestVersion !== undefined && raw.digestVersion !== 2) invalid();
  if (raw.checkpointDigest !== undefined && raw.checkpointDigest !== null
    && (typeof raw.checkpointDigest !== "string" || !SOURCE_DIGEST.test(raw.checkpointDigest))) invalid();
  if (raw.retentionUsageApplied !== undefined && typeof raw.retentionUsageApplied !== "boolean") invalid();
  if (raw.retentionUsageAnchorCount !== undefined && !isCount(raw.retentionUsageAnchorCount)) invalid();
  const retentionUsageApplied = raw.retentionUsageApplied === true;
  const retentionUsageAnchorCount = isCount(raw.retentionUsageAnchorCount) ? raw.retentionUsageAnchorCount : 0;
  if (retentionUsageApplied && retentionUsageAnchorCount < 1) invalid();
  return {
    threadId: expected.threadId,
    throughTurnId: raw.throughTurnId,
    sourceDigest: raw.sourceDigest,
    sourceItemCount: raw.sourceItemCount,
    firstItemId: raw.firstItemId,
    lastItemId: raw.lastItemId,
    retainedItemCount: raw.retainedItemCount,
    retainedTurnIds,
    firstKeptItemId,
    estimatedRetainedTokens: raw.estimatedRetainedTokens,
    retentionUsageApplied,
    retentionUsageAnchorCount,
  };
}
