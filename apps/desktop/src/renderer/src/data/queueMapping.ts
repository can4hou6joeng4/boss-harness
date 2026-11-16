import type { QueueItem, QueueListResponse, QueueStatusCounts } from "@boss-harness/protocol";

/**
 * 内核只返回有界投影：暂停项优先，排队 / 投递中项使用剩余名额（待处理合计最多 200 项），
 * 已结束项再使用剩余名额并另受 50 项上限；totalItems / activeItems / truncated 说明全量。
 * 渲染层必须保留这些字段，否则界面上会无痕丢掉队列记录，待处理数量也会偏小。
 */
export interface QueuePage {
  items: QueueItem[];
  totalItems?: number;
  /** 内核按全部持久项统计的待处理数（排队 / 投递中 / 暂停）；旧内核缺省。 */
  activeItems?: number;
  /** 内核按全部持久项统计的分类计数，不受条目投影截断影响；旧内核缺省。 */
  counts?: QueueStatusCounts;
  truncated?: boolean;
  /**
   * 本地变更对分类计数的增量，只由渲染层的本地合入填写，内核投影不会携带。
   * 截断投影拿不到完整分类，合并徽标时用它把已知计数校正到新的状态组成。
   */
  countsDelta?: QueueStatusDelta;
}

/** 分类计数的增量，可为负数；只覆盖占用待处理计数的状态。 */
export interface QueueStatusDelta {
  queued: number;
  delivering: number;
  paused: number;
}

/** 待处理状态：排队、投递中与暂停都占用待处理计数。面板、徽标与本地合入共用同一口径。 */
export function isQueueActive(status: QueueItem["status"]): status is "queued" | "delivering" | "paused" {
  return status === "queued" || status === "delivering" || status === "paused";
}

/** 已载入条目在两次本地投影之间的分类增量；未载入项不在两侧，不会被误算。 */
export function queueCountsDelta(previous: readonly QueueItem[], next: readonly QueueItem[]): QueueStatusDelta {
  const delta: QueueStatusDelta = { queued: 0, delivering: 0, paused: 0 };
  for (const item of previous) if (isQueueActive(item.status)) delta[item.status] -= 1;
  for (const item of next) if (isQueueActive(item.status)) delta[item.status] += 1;
  return delta;
}

const QUEUE_KINDS: ReadonlySet<string> = new Set(["steering", "followUp"]);
const QUEUE_STATUSES: ReadonlySet<string> = new Set(["queued", "delivering", "delivered", "paused", "cancelled"]);
const QUEUE_PAUSE_REASONS: ReadonlySet<string> = new Set(["COMPACTION_FAILED", "THREAD_ARCHIVED", "TURN_NOT_COMPLETED"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** 自动压缩覆盖是部分字段：缺省继承内核默认值，出现时必须与界面读取的类型一致。 */
function isAutoCompaction(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (value.enabled !== undefined && typeof value.enabled !== "boolean") return false;
  if (value.triggerPercent !== undefined && !Number.isSafeInteger(value.triggerPercent)) return false;
  if (value.keepRecentTokens !== undefined && !Number.isSafeInteger(value.keepRecentTokens)) return false;
  return true;
}

/**
 * 队列项逐项校验。界面直接渲染 `id` / `kind` / `input` / `status` 并把 `input` 当 React 子节点，
 * 畸形元素会在渲染期抛错并落到会话区错误边界，因此状态里只允许通过校验的条目。
 */
export function isQueueItem(value: unknown): value is QueueItem {
  if (!isRecord(value)) return false;
  if (typeof value.id !== "string" || value.id.length === 0) return false;
  if (typeof value.kind !== "string" || !QUEUE_KINDS.has(value.kind)) return false;
  if (typeof value.input !== "string") return false;
  if (typeof value.status !== "string" || !QUEUE_STATUSES.has(value.status)) return false;
  if (value.expectedTurnId != null && typeof value.expectedTurnId !== "string") return false;
  if (value.clientUserMessageId != null && typeof value.clientUserMessageId !== "string") return false;
  if (value.skillIds !== undefined
    && !(Array.isArray(value.skillIds) && value.skillIds.every(id => typeof id === "string"))) return false;
  if (value.autoCompaction !== undefined && !isAutoCompaction(value.autoCompaction)) return false;
  if (value.failureCode !== undefined && value.failureCode !== "TURN_START_FAILED") return false;
  if (value.pausedReason !== undefined && (typeof value.pausedReason !== "string"
    || !QUEUE_PAUSE_REASONS.has(value.pausedReason))) return false;
  if (value.executionStarted !== undefined && value.executionStarted !== false) return false;
  if (value.turnId !== undefined && typeof value.turnId !== "string") return false;
  if (value.inputPersisted !== undefined && typeof value.inputPersisted !== "boolean") return false;
  if (value.deduplicated !== undefined && typeof value.deduplicated !== "boolean") return false;
  if (value.inputTruncated !== undefined && typeof value.inputTruncated !== "boolean") return false;
  return true;
}

function isSafeCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

/**
 * 校验持久分类计数：三个非负安全整数，传入待处理总数时必须与之相等。
 * 不可信的分项不能进入界面，避免徽标显示与待处理总数矛盾的数字。
 */
export function queueStatusCountsOf(value: unknown, activeItems?: number): QueueStatusCounts | null {
  if (!isRecord(value)) return null;
  const queued = value.queued;
  const delivering = value.delivering;
  const paused = value.paused;
  if (!isSafeCount(queued) || !isSafeCount(delivering) || !isSafeCount(paused)) return null;
  const counts: QueueStatusCounts = { queued, delivering, paused };
  if (activeItems !== undefined
    && counts.queued + counts.delivering + counts.paused !== activeItems) return null;
  return counts;
}

/** 列表整体校验：任一项非法即整体不可用，避免只渲染一部分时界面数量与内核总数对不上。 */
export function queueItemsOf(value: unknown): QueueItem[] | null {
  if (!Array.isArray(value)) return null;
  const items: QueueItem[] = [];
  for (const item of value) {
    if (!isQueueItem(item)) return null;
    items.push(item);
  }
  return items;
}

interface QueuePageMetadata {
  totalItems?: unknown;
  activeItems?: unknown;
  counts?: unknown;
  truncated?: unknown;
}

/** `queue/list` 与 `thread/resume` 共用的元数据校验；非法值按缺失处理，不进入界面。 */
function queuePageWithMetadata(items: QueueItem[], metadata: QueuePageMetadata): QueuePage {
  const page: QueuePage = { items };
  const loadedActive = items.filter(item => isQueueActive(item.status)).length;
  const total = metadata.totalItems;
  // 总数只接受不小于已载入项的安全整数；异常时退回按已载入项计算。
  if (typeof total === "number" && Number.isSafeInteger(total) && total >= items.length) page.totalItems = total;
  const active = metadata.activeItems;
  // 待处理数可以大于已载入项，但不能超过持久总数。
  if (typeof active === "number" && Number.isSafeInteger(active) && active >= 0
    && (page.totalItems === undefined || active <= page.totalItems)) page.activeItems = active;
  // 总数或待处理数大于已载入规模时投影必然不完整：截断标记缺失或误报 false 都不能让
  // 提交核对把未载入的消息当成不存在，也不能让队列面板漏掉未载入提示。
  if ((page.totalItems !== undefined && page.totalItems > items.length)
    || (page.activeItems !== undefined && page.activeItems > loadedActive)) {
    page.truncated = true;
  } else if (typeof metadata.truncated === "boolean") {
    page.truncated = metadata.truncated;
  }
  // 分项必须与已接受的待处理总数一致；不一致时退回按已载入项处理，不展示不可信的分项。
  if (page.activeItems !== undefined) {
    const counts = queueStatusCountsOf(metadata.counts, page.activeItems);
    if (counts) page.counts = counts;
  }
  return page;
}

/** 校验并保留队列列表的总数 / 待处理数 / 截断元数据；items 形状不符时返回 null，交由调用方按不可用处理。 */
export function queuePageOf(response: QueueListResponse | null | undefined): QueuePage | null {
  if (!response) return null;
  const items = queueItemsOf(response.items);
  return items ? queuePageWithMetadata(items, response) : null;
}

/**
 * 校验 `thread/resume` 快照中的队列投影。恢复路径与 `queue/list` 共用同一组元数据规则：
 * 非法总数、待处理数、分类或截断标记按缺失处理，避免把不可信数字写进缓存与队列面板。
 */
export function queuePageOfSnapshot(snapshot: {
  queue?: unknown;
  queueTotalItems?: unknown;
  queueActiveItems?: unknown;
  queueCounts?: unknown;
  queueTruncated?: unknown;
}): QueuePage | null {
  const items = queueItemsOf(snapshot.queue);
  return items ? queuePageWithMetadata(items, {
    totalItems: snapshot.queueTotalItems,
    activeItems: snapshot.queueActiveItems,
    counts: snapshot.queueCounts,
    truncated: snapshot.queueTruncated,
  }) : null;
}

/**
 * 在队列投影里查找「提交结果未确认」的消息。
 *
 * 投影只保留有限条目：`truncated` 为真表示还有未载入的记录，此时未命中不能证明消息不在队列。
 * 只有投影完整时才允许返回 `missing`，避免界面把「没读到」当成「不存在」并引导重复提交。
 */
export type QueueSubmissionLookup =
  | { status: "found"; item: QueueItem }
  | { status: "cancelled"; item: QueueItem }
  | { status: "missing" }
  | { status: "unknown" };

export function queueSubmissionLookup(page: QueuePage, clientUserMessageId: string): QueueSubmissionLookup {
  const item = page.items.find(candidate => candidate.clientUserMessageId === clientUserMessageId);
  if (item) return item.status === "cancelled" ? { status: "cancelled", item } : { status: "found", item };
  return page.truncated === true ? { status: "unknown" } : { status: "missing" };
}

/**
 * 把本地新入队、撤回或编辑的条目合入当前会话的队列投影。
 * 重新计算待处理数量与总数，使界面与侧栏徽标即时收敛，不依赖后续轮询。
 */
export function patchQueuePage(page: QueuePage | undefined, item: QueueItem): QueuePage {
  const currentItems = page?.items ?? [];
  const index = currentItems.findIndex(existing => existing.id === item.id);
  const exists = index >= 0;
  const previousItem = exists ? currentItems[index] : undefined;
  const items = exists
    ? currentItems.map((existing, i) => i === index ? item : existing)
    : [...currentItems, item];

  const wasActive = previousItem ? isQueueActive(previousItem.status) : false;
  const nowActive = isQueueActive(item.status);

  const loadedActive = items.filter(entry => isQueueActive(entry.status)).length;
  let activeItems: number | undefined;
  if (typeof page?.activeItems === "number") {
    const delta = (!wasActive && nowActive) ? 1 : (wasActive && !nowActive) ? -1 : 0;
    activeItems = Math.max(0, page.activeItems + delta);
  } else if (page?.truncated !== true) {
    // 只有完整投影的已载入数才等于内核全量；截断时保持缺省，
    // 让面板与驾驶舱继续标注「按已载入项统计」而不是伪装成内核总数。
    activeItems = loadedActive;
  }

  let totalItems: number | undefined;
  if (typeof page?.totalItems === "number") {
    totalItems = Math.max(page.totalItems + (exists ? 0 : 1), items.length);
  } else if (items.length > 0) {
    totalItems = items.length;
  }

  // 本地操作只触及已载入条目，分类差异可以精确应用；截断投影同时留给徽标合并校正旧内核。
  const delta = queueCountsDelta(currentItems, items);
  const countsDelta = page?.truncated === true ? delta : undefined;
  let counts: QueueStatusCounts | undefined;
  if (page?.counts) {
    const next = {
      queued: page.counts.queued + delta.queued,
      delivering: page.counts.delivering + delta.delivering,
      paused: page.counts.paused + delta.paused,
    };
    if (next.queued >= 0 && next.delivering >= 0 && next.paused >= 0
      && (activeItems === undefined
        || next.queued + next.delivering + next.paused === activeItems)) counts = next;
  }
  return {
    items,
    totalItems,
    activeItems,
    counts,
    truncated: page?.truncated,
    countsDelta,
  };
}
