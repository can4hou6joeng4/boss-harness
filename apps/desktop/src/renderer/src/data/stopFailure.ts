import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";

/**
 * 停止请求的失败文案。
 *
 * 内核明确拒绝意味着它没有取消任何回合（例如界面展示的回合已经结束、活动回合已被
 * 后续回合替代），不能再说成「回执未确认」：后者只说明这一笔请求的结果未知，
 * 两种情况下用户该做的核对并不相同。停止是幂等控制操作，两者都不自动重发。
 */
export function stopFailureNotice(error: unknown): string {
  return isHarnessRpcRejection(error)
    ? `停止请求未被内核受理：${harnessErrorText(error)}。本次没有中断任何回合，正在重新读取会话状态。`
    : `停止请求未确认：${harnessErrorText(error)}。正在重新读取会话状态；不会自动重复停止。`;
}
