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
  // 摘要失败发生在投递之前，归档又要求会话空闲；两者仍要求输入没有进入会话，避免重复。
  if (item.pausedReason === "COMPACTION_FAILED" || item.pausedReason === "THREAD_ARCHIVED") {
    return item.inputPersisted !== true;
  }
  return false;
}

/** 暂停原因文案；未知来源不推测原因，只说明可核对的事实与下一步。 */
export function queuePauseReasonText(item: QueueItem): string | null {
  if (item.status !== "paused") return null;
  if (item.kind === "steering") {
    return "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。";
  }
  if (item.kind !== "followUp") return null;
  if (item.pausedReason === "THREAD_ARCHIVED") {
    if (item.deduplicated === true) return "会话归档时暂停，不会自动投递；该输入已关联既有请求，请核对后决定是否撤回。";
    if (item.inputPersisted === true) return "会话归档时暂停，不会自动投递；输入已写入会话，请核对后决定是否撤回。";
    return "会话归档时暂停，不会自动投递；恢复会话后可重新排队或撤回。";
  }
  if (item.pausedReason === "COMPACTION_FAILED") {
    if (item.deduplicated === true) return "摘要未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";
    if (item.inputPersisted === true) return "摘要未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";
    return "摘要未完成，已暂停；可重新排队或撤回。";
  }
  // 这两类暂停已有各自的说明段落，交由面板负责，避免同一项显示两条重复文案。
  if (item.failureCode === "TURN_START_FAILED" || item.deduplicated === true) return null;
  if (item.inputPersisted === true) return "已暂停且不会自动投递；输入已写入会话，请核对后决定是否撤回。";
  return "已暂停且不会自动投递；当前不支持直接重新排队，请核对后决定是否撤回或作为新消息提交。";
}
