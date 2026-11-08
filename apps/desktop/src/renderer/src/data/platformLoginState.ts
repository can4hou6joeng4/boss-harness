import type { PlatformLoginStatus } from "@boss-harness/protocol";

/** 主进程正在占用登录，与 `PlatformLogin.open` 的占用判定一致。 */
export const loginActive = (status: PlatformLoginStatus): boolean => ["opening", "waiting", "saving"].includes(status.state);

/**
 * `open` 失败后的全局状态回落。
 *
 * 失败不保证主进程状态已变：另一会话正在等待扫码、宿主未连接或父窗口已销毁时，
 * 主进程会在改动状态之前抛错。此时全局状态仍属于那次登录，`threadId` 与
 * `browserId` 决定另一会话的原生浏览器可见性与取消入口，不能用本会话的失败态
 * 覆盖。只有状态不属于其他会话、且本会话不在活跃登录中时，才写入失败态。
 */
export function fallbackLoginStatus(previous: PlatformLoginStatus, threadId: string): PlatformLoginStatus {
  if (previous.threadId !== undefined && previous.threadId !== threadId) return previous;
  if (loginActive(previous)) return previous;
  return { threadId, state: "failed", summary: "官方登录页尚未打开" };
}
