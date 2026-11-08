/**
 * 主窗口导航失败的判断。
 *
 * `webContents.loadURL` / `loadFile` 的 Promise 在导航被新导航取代时以 `ERR_ABORTED`（`errno: -3`）
 * 拒绝；这是正常的重载 / 跳转竞争，不是界面加载失败。真实失败仍会由 `did-fail-load` 上报，
 * 这里只做主进程内可离线验证的纯决策。
 */

/** `loadURL` / `loadFile` 拒绝时本项目会用到的字段。 */
export interface NavigationFailure {
  errno?: unknown;
  code?: unknown;
}

/** Electron 用 -3 表示一次导航被另一次导航中止。 */
export const NAVIGATION_ABORTED_ERRNO = -3;

/** 旧导航被新导航取代；调用方不应把它展示成加载失败。 */
export function isAbortedNavigation(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const failure = error as NavigationFailure;
  return failure.errno === NAVIGATION_ABORTED_ERRNO || failure.code === "ERR_ABORTED";
}

/** 只有仍是当前加载、且不是被取代的旧导航时才报告失败。 */
export function shouldReportLoadFailure(error: unknown, isCurrent: boolean): boolean {
  return isCurrent && !isAbortedNavigation(error);
}
