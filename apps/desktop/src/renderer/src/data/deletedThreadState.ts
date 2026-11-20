/**
 * 删除会话时一并遗忘的连接内状态。
 *
 * 内核在 `thread/delete` 的回执之前广播 `thread/deleted`。回执丢失或形状不符时，
 * 桌面按约定保留列表并提示核对，但通知已经移除了侧栏条目：若被删除的正是当前
 * 会话，界面会停在已不存在的聊天上，还能继续发送。调用方据此统一清空消息缓存、
 * 队列投影、失败提示、条目版本、回合标识与记住的审批，并退出该会话的视图。
 */

/** 支持按键删除的连接内状态；`Map` 与 `Set` 都满足这一形状。 */
export type ForgettableByThread = { delete(key: string): boolean };

/**
 * 遗忘 `threadId` 在各项状态中的条目，返回是否确实删除过内容。
 *
 * 空字符串不处理，避免把畸形通知当成删除整个连接的状态；重复通知幂等，
 * 第二次调用返回 `false`。
 */
export function forgetDeletedThread(targets: readonly ForgettableByThread[], threadId: string): boolean {
  if (!threadId) return false;
  let forgotten = false;
  for (const target of targets) if (target.delete(threadId)) forgotten = true;
  return forgotten;
}
