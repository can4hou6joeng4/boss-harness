import type { QueueItem } from "@boss-harness/protocol";
import { queuePauseReasonText } from "./queueRetry";

const LABELS: Record<QueueItem["status"], string> = {
  queued: "排队中",
  delivering: "正在投递",
  delivered: "已投递",
  paused: "已暂停",
  cancelled: "已撤回",
};

/**
 * 列表与完整输入窗口共用的状态文案：暂停项按内核记录的具体来源显示，
 * 关联去重项说明输入已进入既有回合，其余状态沿用通用标签。
 */
export function queueStatusLabel(item: QueueItem): string {
  if (item.status === "paused" && item.failureCode === "TURN_START_FAILED") return "启动失败，未执行";
  if (item.status === "paused" && item.pausedReason === "COMPACTION_FAILED") return "摘要失败，已暂停";
  if (item.status === "paused" && item.pausedReason === "THREAD_ARCHIVED") return "归档时暂停";
  if (item.status === "paused" && item.pausedReason === "TURN_NOT_COMPLETED") return "回合未完成，已暂停";
  if (item.status === "delivered" && item.deduplicated) return "已关联已有回合";
  return LABELS[item.status];
}

/**
 * 暂停项的说明段落，列表与完整输入窗口共用。`retryAvailable` 只影响启动失败
 * 且输入未写入会话时的下一步描述；其余文案不随重试入口变化。
 */
export function queuePauseDetail(item: QueueItem, retryAvailable: boolean): string | null {
  if (item.status !== "paused") return null;
  if (item.failureCode === "TURN_START_FAILED") {
    if (item.inputPersisted === true) return "输入已保留在当前会话，核对后可发起新任务。";
    if (item.inputPersisted === false) {
      return retryAvailable ? "输入尚未写入当前会话，可直接重新排队。" : "输入尚未写入当前会话，核对后可发起新任务。";
    }
    return "请先核对当前会话，再决定是否发起新任务。";
  }
  if (item.deduplicated === true && item.kind === "followUp" && item.pausedReason === undefined) {
    return "已暂停且不会自动投递；该输入已关联旧请求，请核对当前会话后决定是否撤回或发起新任务。";
  }
  return queuePauseReasonText(item);
}
