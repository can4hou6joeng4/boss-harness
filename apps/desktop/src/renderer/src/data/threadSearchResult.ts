import type { ThreadSearchMatch } from "@boss-harness/protocol";

/**
 * `thread/search` 回执的形状校验。
 *
 * 命中条目会直接进入搜索弹窗：`threadId` / `itemId` 被拼进选项 key 与定位意图，
 * `snippet` 交给关键词高亮做字符串归一化。非字符串片段会让渲染期抛错，
 * 损坏标识让命中去重与「打开并定位」失效，未知角色把工具命中显示成助手。
 * 无法识别的回执整体拒绝，弹窗沿用既有错误态。
 */
const ID_LIMIT = 200;
const TITLE_LIMIT = 4096;
const SNIPPET_LIMIT = 4096;
/** 请求侧上限为 50；这里只兜住异常内核，超过即视为矛盾响应。 */
export const SEARCH_MATCH_LIMIT = 200;

const ROLES: ReadonlySet<string> = new Set(["user", "agent", "tool"]);

export interface ThreadSearchResult {
  matches: ThreadSearchMatch[];
  truncated: boolean;
}

function boundedText(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

export function threadSearchMatchOf(value: unknown): ThreadSearchMatch | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!boundedText(raw.threadId, ID_LIMIT)) return null;
  // 标题与片段允许为空：内核可能返回空标题或命中边界上的空片段，空文本渲染安全。
  if (typeof raw.threadTitle !== "string" || raw.threadTitle.length > TITLE_LIMIT) return null;
  if (!boundedText(raw.itemId, ID_LIMIT)) return null;
  if (typeof raw.role !== "string" || !ROLES.has(raw.role)) return null;
  if (typeof raw.snippet !== "string" || raw.snippet.length > SNIPPET_LIMIT) return null;
  return {
    threadId: raw.threadId,
    threadTitle: raw.threadTitle,
    itemId: raw.itemId,
    role: raw.role as ThreadSearchMatch["role"],
    snippet: raw.snippet,
  };
}

export function threadSearchResultOf(value: unknown): ThreadSearchResult | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!Array.isArray(raw.matches) || raw.matches.length > SEARCH_MATCH_LIMIT) return null;
  if (raw.truncated !== undefined && typeof raw.truncated !== "boolean") return null;
  const matches: ThreadSearchMatch[] = [];
  for (const item of raw.matches) {
    const match = threadSearchMatchOf(item);
    if (!match) return null;
    matches.push(match);
  }
  return { matches, truncated: raw.truncated === true };
}