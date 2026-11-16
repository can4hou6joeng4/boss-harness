import type { ThreadBranchEndpoint, TurnStatus, TurnSummary } from "@boss-harness/protocol";

const TURN_STATUSES: ReadonlySet<string> = new Set<TurnStatus>(["running", "completed", "interrupted", "blocked", "error"]);
const TURN_ID_LIMIT = 200;
const TEXT_LIMIT = 4096;
const MAX_DEPTH = 1_000_000;

function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

/** 可选文本字段：缺省按 `null` 兼容旧内核；非法值返回 `undefined`。 */
function optionalText(value: unknown, limit: number): string | null | undefined {
  if (value === undefined || value === null) return null;
  return typeof value === "string" && value.length <= limit ? value : undefined;
}

/**
 * `thread/branches/list` 的端点条目校验。
 *
 * 分支弹窗直接渲染 `turnId`、`depth`、`isLeaf` 等字段并把 `turnId` 当作切换目标；
 * `null`、缺字段或类型不符的条目会让渲染期抛错，而弹窗位于应用级错误边界内，整个
 * 界面会被替换。锚定字段、布尔标记与深度必须合法，时间与预览字段只要求字符串。
 */
export function branchEndpointOf(value: unknown): ThreadBranchEndpoint | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!text(raw.turnId, TURN_ID_LIMIT) || !text(raw.branchTurnId, TURN_ID_LIMIT)) return null;
  if (raw.status !== null && (typeof raw.status !== "string" || !TURN_STATUSES.has(raw.status))) return null;
  const startedAt = optionalText(raw.startedAt, TEXT_LIMIT);
  const updatedAt = optionalText(raw.updatedAt, TEXT_LIMIT);
  const completedAt = optionalText(raw.completedAt, TEXT_LIMIT);
  const forkTurnId = optionalText(raw.forkTurnId, TURN_ID_LIMIT);
  const branchInputPreview = optionalText(raw.branchInputPreview, TEXT_LIMIT);
  const inputPreview = optionalText(raw.inputPreview, TEXT_LIMIT);
  if ([startedAt, updatedAt, completedAt, forkTurnId, branchInputPreview, inputPreview].some(item => item === undefined)) return null;
  if (!Number.isSafeInteger(raw.depth) || (raw.depth as number) < 0 || (raw.depth as number) > MAX_DEPTH) return null;
  if (typeof raw.containsLeaf !== "boolean" || typeof raw.isLeaf !== "boolean" || typeof raw.selectable !== "boolean") return null;
  return {
    turnId: raw.turnId,
    status: raw.status as TurnStatus | null,
    startedAt: startedAt!,
    updatedAt: updatedAt!,
    completedAt: completedAt!,
    depth: raw.depth as number,
    forkTurnId: forkTurnId!,
    branchTurnId: raw.branchTurnId,
    branchInputPreview: branchInputPreview!,
    inputPreview: inputPreview!,
    containsLeaf: raw.containsLeaf,
    isLeaf: raw.isLeaf,
    selectable: raw.selectable,
  };
}

/**
 * 分支视图 `thread/turns/list` 的回合条目校验。
 *
 * 其他会话的回合属于响应归属错误：此前被静默过滤，列表会少于内核声明且没有截断提示；
 * 现在整体拒绝。`updatedAt` 只用于展示，缺省兼容旧内核，出现时必须是字符串。
 */
export function branchTurnOf(value: unknown, threadId: string): TurnSummary | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!text(raw.turnId, TURN_ID_LIMIT) || raw.threadId !== threadId) return null;
  if (typeof raw.status !== "string" || !TURN_STATUSES.has(raw.status)) return null;
  if (raw.updatedAt !== undefined && (typeof raw.updatedAt !== "string" || raw.updatedAt.length > TEXT_LIMIT)) return null;
  return raw as unknown as TurnSummary;
}

/** 分页合并后的重复检查；重复 `turnId` 会让两行共用 key 与切换目标。 */
export function uniqueTurnIds(items: { turnId: string }[]): boolean {
  return new Set(items.map(item => item.turnId)).size === items.length;
}
