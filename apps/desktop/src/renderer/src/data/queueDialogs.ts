import type { QueueItem } from "@boss-harness/protocol";

/**
 * 队列项对话框的有效性：内核投递、撤回或重排后，条目会从列表中消失。
 * 队列面板在空队列时早退不渲染对话框，但状态仍会保留；下一次入队时，
 * 属于旧条目的「查看完整输入」「编辑排队消息」会连同草稿一起重现。
 * 因此按队列项 id 判断：条目不在当前列表里，对它的对话框就必须作废。
 */
export function dropMissingQueueDialog<T extends { item: QueueItem }>(
  current: T | null,
  items: QueueItem[],
): T | null {
  if (!current) return null;
  return items.some(item => item.id === current.item.id) ? current : null;
}
