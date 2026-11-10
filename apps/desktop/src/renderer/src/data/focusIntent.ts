/**
 * 通知定位意图与会话列表加载状态的判定。
 *
 * 系统通知的定位载荷通常在主窗口重建、渲染层重载或连接刚恢复时到达，此时 `thread/list`
 * 可能尚未返回。不能把「列表还没加载」当成「会话不存在」而丢弃定位意图：已找到目标就
 * 应用；列表尚未加载完就等待；列表加载完成仍找不到（已删除或不在当前工作区）才放弃。
 * 审批定位与回合结束定位共用这一规则。
 */
export type FocusResolution = "apply" | "wait" | "drop";

export function focusResolution(sessionsLoaded: boolean, sessionFound: boolean): FocusResolution {
  if (sessionFound) return "apply";
  return sessionsLoaded ? "drop" : "wait";
}
