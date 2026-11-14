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

/** 没有可停止回合时的说明；与读取失败记录组合时去掉「正在重新读取」的过渡语。 */
export const stopMissingNotice = "未找到可停止的任务，正在重新读取会话状态。";

/** 读取失败记录已含原因与处理建议；保留停止主因，不重复包裹读取说明。 */
export function stopFailureRecheckNotice(error: unknown, verificationFailure: string): string {
  const primary = isHarnessRpcRejection(error)
    ? `停止请求未被内核受理：${harnessErrorText(error)}。本次没有中断任何回合`
    : `停止请求未确认：${harnessErrorText(error)}。不会自动重复停止`;
  return `${primary}；${verificationFailure}`;
}

export function stopMissingRecheckNotice(verificationFailure: string): string {
  return `未找到可停止的任务；${verificationFailure}`;
}
