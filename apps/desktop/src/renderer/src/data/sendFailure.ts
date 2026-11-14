import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";

/**
 * 发送失败的主提示。
 * 内核明确拒绝说明请求没有进入会话，不能再写成「结果尚未确认」；
 * 断连、IPC 失败或回执不可读仍按不确定处理。
 */
export function sendFailureNotice(error: unknown): string {
  return isHarnessRpcRejection(error)
    ? `发送失败：${harnessErrorText(error)}。正在读取会话状态，请核对后重试。`
    : `提交结果尚未确认：${harnessErrorText(error)}。正在读取会话状态，请核对记录后再决定下一步。`;
}

/** 读取失败记录已含原因与处理建议；保留发送主因，不重复包裹读取说明。 */
export function sendFailureRecheckNotice(error: unknown, verificationFailure: string): string {
  const primary = isHarnessRpcRejection(error) ? "发送失败" : "提交结果尚未确认";
  return `${primary}：${harnessErrorText(error)}；${verificationFailure}`;
}
