/**
 * 回合结束系统通知的会话定位载荷。
 *
 * 主进程只从内核事件里取 `threadId`，但 IPC 载荷仍可能损坏或被替换；这里按与会话
 * 定位字段相同的上限重新校验，读不到就放弃定位，绝不猜测或新建会话。
 */
const FIELD_LIMIT = 200;

export function readThreadFocus(value: unknown): { threadId: string } | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const threadId = typeof record.threadId === "string" ? record.threadId.trim() : "";
  return threadId && threadId.length <= FIELD_LIMIT ? { threadId } : null;
}
