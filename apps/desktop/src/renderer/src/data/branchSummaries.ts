import type { ContextBranchSummary } from "@boss-harness/protocol";

const ENTRY_ID_LIMIT = 200;
const MAX_ABANDONED_TURNS = 1000;
const TURN_ID_LIMIT = 200;

function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

/** 可选引用字段：缺省按 `null` 兼容旧内核；非法值返回 `undefined`。 */
function optionalRef(value: unknown): string | null | undefined {
  if (value === undefined || value === null) return null;
  return text(value, TURN_ID_LIMIT) ? value : undefined;
}

/**
 * `context/read.branchSummaries` 的逐项校验。
 *
 * 会话区在渲染期读取 `targetTurnId` 定位摘要标记，标记组件再读取
 * `abandonedTurnIds.length` 与 `characters`；一条 `null`、缺数组或非数值的条目会让
 * 整段会话区落入错误边界。与同响应的 `branchSummaryIssues` 一致：非法条目丢弃并
 * 计数，由调用方提示，合法条目继续展示。`entryId` 在同一响应内必须唯一，重复会让
 * 多个标记共用同一 React key 与正文读取目标。
 */
export function branchSummariesOf(value: unknown): { summaries: ContextBranchSummary[]; dropped: number } {
  if (!Array.isArray(value)) return { summaries: [], dropped: 0 };
  const summaries: ContextBranchSummary[] = [];
  const seen = new Set<string>();
  let dropped = 0;
  for (const item of value) {
    if (!item || typeof item !== "object" || Array.isArray(item)) { dropped += 1; continue; }
    const raw = item as Record<string, unknown>;
    if (!text(raw.entryId, ENTRY_ID_LIMIT) || seen.has(raw.entryId)) { dropped += 1; continue; }
    const targetTurnId = optionalRef(raw.targetTurnId);
    const fromTurnId = optionalRef(raw.fromTurnId);
    const summaryJobId = optionalRef(raw.summaryJobId);
    if (targetTurnId === undefined || fromTurnId === undefined || summaryJobId === undefined) { dropped += 1; continue; }
    const abandoned = raw.abandonedTurnIds;
    if (!Array.isArray(abandoned) || abandoned.length > MAX_ABANDONED_TURNS
      || !abandoned.every(turnId => text(turnId, TURN_ID_LIMIT))) { dropped += 1; continue; }
    if (typeof raw.characters !== "number" || !Number.isSafeInteger(raw.characters) || raw.characters < 0) { dropped += 1; continue; }
    seen.add(raw.entryId);
    summaries.push({
      entryId: raw.entryId,
      targetTurnId,
      fromTurnId,
      abandonedTurnIds: [...abandoned],
      summaryJobId,
      characters: raw.characters,
    });
  }
  return { summaries, dropped };
}
