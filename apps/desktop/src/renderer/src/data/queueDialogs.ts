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

/**
 * 目标移出当前投影后，未保存的编辑正文仍是用户的唯一副本，保留供复制或明确丢弃。
 * 调用方必须从当前列表判断能否保存，不能沿用保留快照里的 queued 状态。
 * 无修改的编辑窗口仍随目标消失关闭，避免后续新条目复活旧窗口。
 */
export function syncQueueEditDialog<T extends { item: QueueItem; draft: string; originalInput: string }>(
  current: T | null,
  items: QueueItem[],
): T | null {
  return syncQueueDialogItem(current, items)
    ?? (current && current.draft !== current.originalInput ? current : null);
}
