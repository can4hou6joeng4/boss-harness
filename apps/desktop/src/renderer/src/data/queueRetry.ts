import type { QueueItem } from "@boss-harness/protocol";

/**
 * 暂停项能否通过「重新排队」恢复：重新入队会用持久化的完整输入创建新请求，
 * 再撤回旧项。任何可能已经进入会话（`inputPersisted`）或已关联既有请求
 * （`deduplicated`）的暂停项都不能重试，否则会重复执行同一份输入。
 */
export function queueItemRetryable(item: QueueItem): boolean {
  if (item.kind !== "followUp" || item.status !== "paused" || item.deduplicated === true) return false;
  // 启动失败沿用原有条件：只有确认输入尚未写入会话才允许重试。
  if (item.failureCode === "TURN_START_FAILED") return item.inputPersisted === false;
  // 摘要失败暂停发生在投递之前；仍要求输入没有进入会话，避免投递竞态后重复。
  return item.pausedReason === "COMPACTION_FAILED" && item.inputPersisted !== true;
}

/** 暂停原因文案；未知来源保持通用「已暂停」，不推测用户看不到的事实。 */
export function queuePauseReasonText(item: QueueItem): string | null {
  if (item.kind !== "followUp" || item.status !== "paused"
    || item.pausedReason !== "COMPACTION_FAILED") return null;
  if (item.deduplicated === true) return "摘要未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";
  if (item.inputPersisted === true) return "摘要未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";
  return "摘要未完成，已暂停；可重新排队或撤回。";
}
