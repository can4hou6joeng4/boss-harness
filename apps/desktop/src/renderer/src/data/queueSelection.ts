import type { QueueItem } from "@boss-harness/protocol";

/** 折叠状态下面板最多渲染的待处理项；展开后由内核投影上限约束。 */
export const MAX_VISIBLE_QUEUE_ITEMS = 20;

const isPending = (item: QueueItem) => item.status === "queued" || item.status === "delivering";
const isTerminal = (item: QueueItem) => item.status === "delivered" || item.status === "cancelled";

/**
 * 折叠时优先保留暂停项：它们不会自动投递，只能由用户重新排队或撤回；
 * 剩余名额给最近的排队 / 投递中项，名额允许时再显示最近的已结束项。
 * 返回顺序仍取持久化顺序，避免展示顺序与队列实际顺序不一致。
 */
export function selectVisibleQueueItems(items: QueueItem[], expanded: boolean): QueueItem[] {
  if (expanded) return items;
  const paused = items.filter(item => item.status === "paused").slice(-MAX_VISIBLE_QUEUE_ITEMS);
  const pendingRoom = Math.max(0, MAX_VISIBLE_QUEUE_ITEMS - paused.length);
  const pending = pendingRoom ? items.filter(isPending).slice(-pendingRoom) : [];
  const terminalRoom = Math.max(0, MAX_VISIBLE_QUEUE_ITEMS - paused.length - pending.length);
  const terminal = terminalRoom ? items.filter(isTerminal).slice(-terminalRoom) : [];
  const keep = new Set([...paused, ...pending, ...terminal].map(item => item.id));
  return items.filter(item => keep.has(item.id));
}
