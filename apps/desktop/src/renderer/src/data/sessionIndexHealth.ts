/**
 * `config/read` 中的会话索引健康度。
 *
 * 内核会跳过无法解析的会话日志，避免单个坏文件拖垮其余会话恢复；
 * 这些文件只在这里暴露。旧内核不返回字段，或字段形状不可信时返回 null，
 * 界面按「未报告」处理，不把坏数据渲染成告警或正常。
 */
export interface SessionIndexHealth {
  /** 无法建立索引的文件总数，可能大于 ids.length。 */
  count: number;
  /** 内核返回的会话 id 快照，按字典序排列；形状非法的值被忽略。 */
  ids: string[];
}

/** 内核最多返回 20 个 id；这里同样截断，防止异常内核撑大界面。 */
export const SESSION_INDEX_MAX_IDS = 20;
const MAX_THREAD_ID_LENGTH = 64;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function readSessionIndexHealth(config: unknown): SessionIndexHealth | null {
  if (!isRecord(config)) return null;
  const count = config.unreadableThreadCount;
  if (typeof count !== "number" || !Number.isInteger(count) || count <= 0) return null;
  const ids: string[] = [];
  const raw = config.unreadableThreadIds;
  if (Array.isArray(raw)) {
    for (const value of raw) {
      if (ids.length >= SESSION_INDEX_MAX_IDS) break;
      if (typeof value !== "string" || value.length === 0 || value.length > MAX_THREAD_ID_LENGTH) continue;
      if (!ids.includes(value)) ids.push(value);
    }
  }
  return { count, ids };
}
