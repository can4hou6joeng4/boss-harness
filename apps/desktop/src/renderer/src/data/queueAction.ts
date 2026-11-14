import type { QueueItem } from "@boss-harness/protocol";
import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";

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
