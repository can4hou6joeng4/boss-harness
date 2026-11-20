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
 * `title` 与 `updatedAt` 用于展示与排序，`summaryTurnOf` 选出的回合编号会作为恢复目标继续传递。
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
  if (raw.toolPolicy !== undefined && raw.toolPolicy !== "readOnly" && raw.toolPolicy !== "approval") return null;
  const provider = optionalText(raw.provider, ID_LIMIT);
  const model = optionalText(raw.model, ID_LIMIT);
  const reasoningEffort = optionalText(raw.reasoningEffort, ID_LIMIT);
  if (provider === undefined || model === undefined || reasoningEffort === undefined) return null;
  // 两个末回合字段都会进入侧栏状态与继续目标，按同一规则校验。
  if (!summaryTurnValid(raw.lastTurn) || !summaryTurnValid(raw.branchLastTurn)) return null;
  return raw as unknown as ThreadSummary;
}

function summaryTurnValid(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value !== "object" || Array.isArray(value)) return false;
  const turn = value as Record<string, unknown>;
  if (!text(turn.turnId, ID_LIMIT)) return false;
  if (typeof turn.status !== "string" || !TURN_STATUSES.has(turn.status)) return false;
  if (optionalText(turn.failureCode, CODE_LIMIT) === undefined) return false;
  return optionalText(turn.taskResumePolicy, CODE_LIMIT) !== undefined;
}

/**
 * 侧栏状态、失败标记与继续入口使用的回合。
 *
 * 切换过分支位置的会话带有 `branchLastTurn`（当前分支末回合，位于会话开头时为 null）；
 * 此时日志末回合 `lastTurn` 可能属于已放弃的分支，不能再代表会话现状。没有该字段时
 * （未切换过位置，或索引尚未重建）沿用 `lastTurn`。
 */
export function summaryTurnOf(thread: ThreadSummary): ThreadSummary["lastTurn"] {
  return thread.branchLastTurn !== undefined ? thread.branchLastTurn : thread.lastTurn;
}

/** 分页合并后的重复检查；重复 id 会让侧栏静默合并会话并把操作落到同一目标。 */
export function uniqueThreadIds(items: { id: string }[]): boolean {
  return new Set(items.map(item => item.id)).size === items.length;
}
