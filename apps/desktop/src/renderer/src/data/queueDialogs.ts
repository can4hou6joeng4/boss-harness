import type { QueueItem } from "@boss-harness/protocol";

/**
 * 把对话框绑定的条目换成队列投影中的最新快照；条目已消失时返回 null。
 *
 * 内核投递、撤回或暂停后，条目会按 id 原位替换成终态并保留在投影里，id 判重
 * 不足以发现对话框已经失效：继续展示旧快照会让编辑框承诺「保存后投递的是这段
 * 正文」，实际内核只接受 `queued` 条目，保存必然失败。因此对话框跟随实时条目，
 * 由调用方按最新状态决定是否还允许保存。
 */
export function syncQueueDialogItem<T extends { item: QueueItem }>(
  current: T | null,
  items: QueueItem[],
): T | null {
  if (!current) return null;
  const live = items.find(item => item.id === current.item.id);
  return live ? { ...current, item: live } : null;
}
