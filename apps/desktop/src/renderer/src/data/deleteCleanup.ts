import type { ComposerDraft } from "./composerDraft";
import type { MessageFeedbackStore } from "./messageFeedback";
import { parseFeedbackEntryKey } from "./messageFeedback";

/**
 * 删除聊天前说明会一并清除的本机内容。
 *
 * 删除已同时清理该会话的未发送草稿（#1040）与消息反馈（#1042），确认框需要
 * 如实列出实际存在的类别，用户才能在不可恢复操作前评估损失。只统计当前
 * 内存草稿与本地反馈中的真实条目，不虚构没有的内容；空草稿且无反馈时返回
 * 空数组，由调用方保持原有文案。
 */
export function deleteCleanupSummary(draft: ComposerDraft | undefined, feedback: MessageFeedbackStore, threadId: string): string[] {
  const parts: string[] = [];
  if (draft) {
    if (draft.text.trim()) parts.push("未发送正文");
    if (draft.attachments.length > 0) parts.push(`${draft.attachments.length} 个附件`);
    const skillCount = (draft.skillIds ?? []).length;
    if (skillCount > 0) parts.push(`${skillCount} 项已选技能`);
    if (draft.pendingReads > 0) parts.push("正在读取的附件");
  }
  let feedbackCount = 0;
  for (const key of Object.keys(feedback)) {
    if (parseFeedbackEntryKey(key)?.[0] === threadId) feedbackCount += 1;
  }
  if (feedbackCount > 0) parts.push(`${feedbackCount} 条消息反馈`);
  return parts;
}
