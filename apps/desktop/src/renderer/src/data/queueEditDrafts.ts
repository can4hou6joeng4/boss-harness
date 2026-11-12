import type { QueueItem } from "@boss-harness/protocol";

/** 一条排队消息的未保存编辑：条目快照用于条目移出队列后仍可核对与复制。 */
export interface QueueEditDraft {
  item: QueueItem;
  draft: string;
  originalInput: string;
}

/**
 * 未保存的排队消息编辑草稿按会话保留在应用生命周期内。
 *
 * 对话区随活动会话切换整体卸载，组件内 state 会丢失；通知定位与侧栏切换都会
 * 触发这条路径。草稿只有保存成功或用户确认丢弃时才清除，切换会话不应删除用户
 * 尚未提交的正文。条目快照与草稿一起保留，便于条目已投递或撤回后继续核对。
 */
const drafts = new Map<string, QueueEditDraft>();

export function readQueueEditDraft(threadId: string): QueueEditDraft | null {
  const draft = drafts.get(threadId);
  return draft ? { ...draft, item: { ...draft.item } } : null;
}

export function writeQueueEditDraft(threadId: string, draft: QueueEditDraft): void {
  drafts.set(threadId, { ...draft, item: { ...draft.item } });
}

export function clearQueueEditDraft(threadId: string): void {
  drafts.delete(threadId);
}
