import type { QueueItem } from "@boss-harness/protocol";
import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";
import { isQueueActive, queueCountsDelta, type QueuePage } from "./queueMapping";

/**
 * 队列操作（撤回、重新排队）的结果。
 *
 * 只返回 boolean 无法区分「请求根本没有发出」与「请求可能生效但回执不可读」：
 * 前者要提示用户先处理原因（断连、状态已变化），后者必须让用户核对队列，
 * 不能当成失败直接重试。
 */
export type QueueActionOutcome =
  | { status: "done" }
  | { status: "skipped"; reason: string }
  | { status: "uncertain" };

/** 重新排队分两步：`partial` 表示新项已受理，但旧项撤回尚未确认。 */
export type QueueRetryOutcome = QueueActionOutcome | { status: "partial" };

/** 面板内提示；部分完成仍须停止后续操作，避免重复创建已经受理的新项。 */
export function queueActionNotice(action: "撤回" | "重新排队", outcome: QueueRetryOutcome): string | null {
  if (outcome.status === "partial") return "重新排队已受理，但旧队列项撤回结果尚未确认；请先刷新队列，核对并撤回仍保留的旧项，不要重复重新排队。";
  if (outcome.status === "skipped") return `${action}没有发出：${outcome.reason}。`;
  if (outcome.status === "uncertain") return `${action}结果尚未确认；请先核对队列状态，再决定是否重试。`;
  return null;
}

/**
 * 重新排队入队失败：内核明确拒绝说明请求没有发出，可安全按 `skipped` 提示；
 * 断连、IPC 或回执不可读没有拒绝标记，调用方必须按「未确认」处理。
 */
export function queueRetryRejection(error: unknown): QueueActionOutcome | null {
  return isHarnessRpcRejection(error) ? { status: "skipped", reason: harnessErrorText(error) } : null;
}

/**
 * 重新排队后的本地列表。旧项只有在确认撤回后才移出界面：撤回回执不可读时，
 * 它可能仍是内核里的暂停项，不能因为一次本地更新就把它隐藏。
 */
export function queueRetryLocalItems(previous: QueueItem[], oldId: string, created: QueueItem,
  removed: boolean): QueueItem[] {
  const kept = previous.filter(item => item.id !== created.id && (!removed || item.id !== oldId));
  return [...kept, created];
}

/**
 * 重新排队已受理但队列刷新失败时的本地投影。
 *
 * 待处理总数沿用与 `patchQueuePage` 相同的口径：已有内核持久总数时按旧项撤下与新项加入增减；
 * 缺少总数且投影完整时才用已载入数；截断且缺省保持未知，不把可见计数写成内核总数。
 * 截断投影同时记录已载入条目的分类增量，供徽标合并把已知分类校正到新的状态组成。
 */
export function queueRetryPage(page: QueuePage | undefined, previousItems: QueueItem[], oldId: string,
  created: QueueItem, removed: boolean): QueuePage {
  const items = queueRetryLocalItems(previousItems, oldId, created, removed);
  const previousOld = (page?.items ?? previousItems).find(entry => entry.id === oldId);
  const droppedOld = removed && previousOld !== undefined && isQueueActive(previousOld.status);
  const addedCreated = isQueueActive(created.status) ? 1 : 0;
  let activeItems: number | undefined;
  if (typeof page?.activeItems === "number") {
    activeItems = Math.max(0, page.activeItems + addedCreated - (droppedOld ? 1 : 0));
  } else if (page?.truncated !== true) {
    activeItems = items.filter(entry => isQueueActive(entry.status)).length;
  }
  let totalItems: number | undefined;
  if (typeof page?.totalItems === "number") {
    // 旧项撤下与新项加入相互抵消；撤回未确认时旧项仍计入，总数只增加新项。
    totalItems = Math.max(page.totalItems + (removed ? 0 : 1), items.length);
  } else if (items.length > 0) {
    totalItems = items.length;
  }
  const countsDelta = page?.truncated === true ? queueCountsDelta(previousItems, items) : undefined;
  return { items, totalItems, activeItems, truncated: page?.truncated, countsDelta };
}
