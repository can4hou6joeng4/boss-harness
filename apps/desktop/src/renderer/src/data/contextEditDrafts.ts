/**
 * 消息上下文编辑的未保存替换文本按「会话 + 消息」保留在应用生命周期内。
 *
 * 编辑框由工作台外层持有，不随背景会话切换卸载；本缓存为意外卸载后的重开
 * 保留未提交正文。草稿只在提交成功或用户确认丢弃后清除，切换会话不删除
 * 用户尚未提交的正文。同一会话的不同消息各存各的，不互相覆盖。
 */
const drafts = new Map<string, string>();

const keyOf = (threadId: string, itemId: string) => `${threadId}\u0000${itemId}`;

export function readContextEditDraft(threadId: string, itemId: string): string | null {
  return drafts.get(keyOf(threadId, itemId)) ?? null;
}

export function writeContextEditDraft(threadId: string, itemId: string, draft: string): void {
  drafts.set(keyOf(threadId, itemId), draft);
}

export function clearContextEditDraft(threadId: string, itemId: string): void {
  drafts.delete(keyOf(threadId, itemId));
}
