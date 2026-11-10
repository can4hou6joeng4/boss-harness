import type { QueueStatusCounts } from "@boss-harness/protocol";
import type { QueuePage } from "./queueMapping";

/**
 * 侧栏会话行的队列徽标。
 *
 * 徽标与会话列表一起来自 `thread/list` 投影，`queue/updated` 只让界面重读当前会话的
 * 队列面板，因此徽标会停在旧数字上，暂停项也显示不出来。这里用同一次 `queue/list`
 * 投影推出徽标，避免为一次队列变化再刷新整个会话列表。
 */
export interface QueueBadge {
  activeItems: number;
  /** 仅在投影完整（未截断且分类之和等于待处理总数）时提供。 */
  counts?: QueueStatusCounts;
}

/**
 * 从有界队列投影推出徽标数值。
 *
 * `queue/list` 的条目是有界投影：截断时分类计数会偏小，但内核仍给出全部持久项的
 * 待处理总数。此时只保留总数，分类留给下一次会话列表刷新校正，避免显示
 * 「待处理 8 条：排队 3」这种自相矛盾的分项。
 */
export function queueBadgeOf(page: QueuePage): QueueBadge {
  const counts: QueueStatusCounts = { queued: 0, delivering: 0, paused: 0 };
  for (const item of page.items) {
    if (item.status === "queued" || item.status === "delivering" || item.status === "paused") counts[item.status] += 1;
  }
  const loaded = counts.queued + counts.delivering + counts.paused;
  const activeItems = page.activeItems ?? loaded;
  const complete = page.truncated !== true && loaded === activeItems;
  return complete && activeItems > 0 ? { activeItems, counts } : { activeItems };
}

/** 会话列表里能承载徽标的最小形状；返回新数组，未命中或数值未变时返回 null。 */
export function patchQueueBadge<T extends { id: string; queueActiveItems?: number; queueCounts?: QueueStatusCounts }>(
  sessions: readonly T[], threadId: string, badge: QueueBadge,
): T[] | null {
  let changed = false;
  const next = sessions.map(session => {
    if (session.id !== threadId) return session;
    const counts = badge.counts;
    if (session.queueActiveItems === badge.activeItems
      && session.queueCounts?.queued === counts?.queued
      && session.queueCounts?.delivering === counts?.delivering
      && session.queueCounts?.paused === counts?.paused) return session;
    changed = true;
    return counts
      ? { ...session, queueActiveItems: badge.activeItems, queueCounts: counts }
      : { ...session, queueActiveItems: badge.activeItems, queueCounts: undefined };
  });
  return changed ? next : null;
}
