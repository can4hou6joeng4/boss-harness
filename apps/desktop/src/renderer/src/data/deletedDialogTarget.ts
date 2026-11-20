/**
 * 弹窗目标随会话删除失效。
 *
 * 上下文面板、用量、导出、分支与回退弹窗在打开时固定目标会话。删除回执未确认时
 * 列表按约定保留，内核仍可能已经提交删除并广播 `thread/deleted`；此时固定在被删除
 * 会话上的弹窗必须收起，不能继续对已不存在的会话读取或提交操作。其他会话与空目标
 * 原样返回同一个对象，调用方据此判断是否需要改动界面状态。
 */
export type DialogThreadTarget = { threadId: string } | null;

export function detachedTarget<T extends DialogThreadTarget>(target: T, deleted: string): T | null {
  if (!target || !deleted) return target;
  return target.threadId === deleted ? null : target;
}