import type { QueueStatusCounts } from "@boss-harness/protocol";
import type { QueuePage, QueueStatusDelta } from "./queueMapping";

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
  /** 截断投影下本地操作带来的分类增量；合并时用于校正上一次已知计数。 */
  delta?: QueueStatusDelta;
}

/**
 * 从有界队列投影推出徽标数值。
 *
 * `queue/list` 的条目是有界投影：截断时按条目统计的分项会偏小。内核给出的持久
 * 分类计数（counts）不受截断影响，优先使用；旧内核缺省时只保留待处理总数，
 * 分类留给会话列表刷新或本地增量校正，避免显示「待处理 8 条：排队 3」这种
 * 自相矛盾的分项。
 */
export function queueBadgeOf(page: QueuePage): QueueBadge {
  const counts: QueueStatusCounts = { queued: 0, delivering: 0, paused: 0 };
  for (const item of page.items) {
    if (item.status === "queued" || item.status === "delivering" || item.status === "paused") counts[item.status] += 1;
  }
  const loaded = counts.queued + counts.delivering + counts.paused;
  const activeItems = page.activeItems ?? loaded;
  // 持久分类不受投影截断影响，优先于按已载入条目推算的分项。
  if (page.counts && activeItems > 0) return { activeItems, counts: page.counts };
  const complete = page.truncated !== true && loaded === activeItems;
  if (complete && activeItems > 0) return { activeItems, counts };
  if (page.countsDelta && activeItems > 0) return { activeItems, delta: page.countsDelta };
  return { activeItems };
}

/**
 * 把徽标折算成会话行应显示的完整分类。
 *
 * 完整投影直接用内核计数；截断投影若带本地增量且已知计数与旧待处理总数一致，
 * 就把增量应用到已知计数。结果必须非负且与新的待处理总数一致，否则放弃分类、
 * 只保留总数，避免徽标显示自相矛盾的分项。
 */
function mergedQueueCounts(
  session: { queueActiveItems?: number; queueCounts?: QueueStatusCounts }, badge: QueueBadge,
): QueueStatusCounts | undefined {
  if (badge.counts) return badge.counts;
  const base = session.queueCounts;
  if (!base || base.queued + base.delivering + base.paused !== session.queueActiveItems) return undefined;
  if (!badge.delta) return badge.activeItems === session.queueActiveItems ? base : undefined;
  const counts: QueueStatusCounts = {
    queued: base.queued + badge.delta.queued,
    delivering: base.delivering + badge.delta.delivering,
    paused: base.paused + badge.delta.paused,
  };
  if (counts.queued < 0 || counts.delivering < 0 || counts.paused < 0) return undefined;
  if (counts.queued + counts.delivering + counts.paused !== badge.activeItems) return undefined;
  return counts;
}

/**
 * 会话列表里能承载徽标的最小形状；返回新数组，未命中或数值未变时返回 null。
 *
 * 截断投影不携带完整分类：总数未变时保留上一次的分类；本地变更带分类增量时，
 * 在已知计数与旧总数一致的前提下应用增量。分类与新的待处理总数对不上就放弃分类，
 * 避免暂停项从侧栏徽标和「待你处理」分组消失，或显示自相矛盾的分项。
 */
export function patchQueueBadge<T extends { id: string; queueActiveItems?: number; queueCounts?: QueueStatusCounts }>(
  sessions: readonly T[], threadId: string, badge: QueueBadge,
): T[] | null {
  let changed = false;
  const next = sessions.map(session => {
    if (session.id !== threadId) return session;
    const counts = mergedQueueCounts(session, badge);
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
