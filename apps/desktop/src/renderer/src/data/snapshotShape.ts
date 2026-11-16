import type { ThreadReadResponse } from "@boss-harness/protocol";

const SNAPSHOT_ID_PATTERN = /^[a-f0-9]{32}$/;

/**
 * `thread/resume` / `thread/read` 快照的身份与基本形状校验。
 *
 * 恢复流程按快照自身的 `thread.id` 写缓存与运行状态，调用方还会用快照的
 * `provider` / `model` 更新当前会话线路；普通路径缺少与分支路径相同的身份
 * 校验时，属于另一个会话的回执会把消息与线路错置到当前会话。
 */
export function assertThreadSnapshot(value: unknown, threadId: string): void {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("会话快照响应无效");
  const snapshot = value as Record<string, unknown>;
  const thread = snapshot.thread;
  if (!thread || typeof thread !== "object" || Array.isArray(thread)
    || (thread as Record<string, unknown>).id !== threadId) throw new Error("会话快照响应无效");
  if (snapshot.snapshotId !== undefined
    && (typeof snapshot.snapshotId !== "string" || !SNAPSHOT_ID_PATTERN.test(snapshot.snapshotId))) {
    throw new Error("会话快照标识无效");
  }
  if (!Array.isArray(snapshot.items)) throw new Error("会话快照条目无效");
}

/** 校验通过后收窄为协议类型；分页读取条目仍由调用方自行覆盖 `items`。 */
export function threadSnapshotOf(value: unknown, threadId: string): ThreadReadResponse {
  assertThreadSnapshot(value, threadId);
  return value as ThreadReadResponse;
}
