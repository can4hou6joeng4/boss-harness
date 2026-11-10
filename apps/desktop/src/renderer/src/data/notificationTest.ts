/** 主进程测试通知的返回值解读；未确认的情况不能显示成「已发送」。 */
export type NotificationTestOutcome = "sent" | "unsupported" | "failed" | "unconfirmed";

export function readNotificationTestResult(value: unknown): NotificationTestOutcome {
  if (!value || typeof value !== "object") return "unconfirmed";
  const record = value as Record<string, unknown>;
  if (record.sent === true) return "sent";
  if (record.sent === false && record.supported === false) return "unsupported";
  // 平台支持却返回未发送：主进程的 show() 同步抛错，请求根本没有发出去。
  // 这与「已请求发送、但无法确认是否展示」是两种状态，不能混为一谈。
  if (record.sent === false && record.supported === true) return "failed";
  return "unconfirmed";
}

/**
 * 设置页「发送测试通知」之后的状态提示。
 *
 * 只有 `sent` 能说「已请求展示」；发送失败是请求没发出去，与无法识别返回值的
 * 「未能确认」分开表述，避免用户等待一条不会出现的通知。
 */
export function notificationTestStatus(outcome: NotificationTestOutcome): string {
  switch (outcome) {
    case "sent": return "已请求系统展示测试通知，请留意桌面提醒。";
    case "unsupported": return "当前系统不支持系统通知，审批与回合结束不会弹窗提醒。";
    case "failed": return "系统支持通知，但发送请求失败；请检查系统通知权限后重试。";
    default: return "测试通知返回了无法识别的结果，未能确认是否展示；请检查本机内核与系统通知权限。";
  }
}
