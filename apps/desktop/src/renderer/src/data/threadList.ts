import type { ThreadSummary } from "@boss-harness/protocol";

const ID_LIMIT = 200;
const TITLE_LIMIT = 500;
const TIME_LIMIT = 64;
const CODE_LIMIT = 120;
const TURN_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "interrupted", "blocked", "error"]);

function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

/** 可选字符串字段：缺省保持缺省；出现时必须是有界字符串，否则返回 `undefined`。 */
function optionalText(value: unknown, limit: number): string | null | undefined {
  if (value === undefined || value === null) return null;
  return typeof value === "string" && value.length <= limit ? value : undefined;
}

/**
 * `thread/list` 的会话条目校验。
 *
 * 侧栏把条目直接映射为 `SessionItem`：`id` 用于去重、key、选择 / 重命名 / 删除目标，
 * `title` 与 `updatedAt` 用于展示与排序，`lastTurn.turnId` 会作为恢复目标继续传递。
 * 缺 `id` 的条目会被 `sessionRows` 的按 id 去重静默吞掉，重复 `id` 让多个会话共用同一
 * 目标；因此这里逐项校验，调用方遇到非法条目整体失败，不展示部分可疑列表。
 */
export function threadSummaryOf(value: unknown): ThreadSummary | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!text(raw.id, ID_LIMIT)) return null;
  if (typeof raw.title !== "string" || raw.title.length > TITLE_LIMIT) return null;
  if (typeof raw.updatedAt !== "string" || raw.updatedAt.length > TIME_LIMIT) return null;
  if (raw.archived !== undefined && typeof raw.archived !== "boolean") return null;
  const provider = optionalText(raw.provider, ID_LIMIT);
  const model = optionalText(raw.model, ID_LIMIT);
  const reasoningEffort = optionalText(raw.reasoningEffort, ID_LIMIT);
  if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;
  const lastTurn = raw.lastTurn;
  if (lastTurn !== undefined && lastTurn !== null) {
    if (!lastTurn || typeof lastTurn !== "object" || Array.isArray(lastTurn)) return null;
    const turn = lastTurn as Record<string, unknown>;
    if (!text(turn.turnId, ID_LIMIT)) return null;
    if (typeof turn.status !== "string" || !TURN_STATUSES.has(turn.status)) return null;
    if (optionalText(turn.failureCode, CODE_LIMIT) === undefined) return null;
    if (optionalText(turn.taskResumePolicy, CODE_LIMIT) === undefined) return null;
  }
  return raw as unknown as ThreadSummary;
}

/** 分页合并后的重复检查；重复 id 会让侧栏静默合并会话并把操作落到同一目标。 */
export function uniqueThreadIds(items: { id: string }[]): boolean {
  return new Set(items.map(item => item.id)).size === items.length;
}
