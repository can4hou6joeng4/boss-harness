import type { MessageBoxOptions } from "electron";

export type QuitConfirmationOptions = Pick<MessageBoxOptions,
  "type" | "title" | "message" | "detail" | "buttons" | "defaultId" | "cancelId" | "noLink">;

/**
 * 退出确认内容：只在存在运行中回合时返回。
 * 默认按钮与取消按钮都落在「继续运行」，避免回车或 Esc 误中断招聘任务。
 */
export function quitConfirmationContent(runningTurns: number): QuitConfirmationOptions | null {
  const count = Number.isFinite(runningTurns) ? Math.floor(runningTurns) : 0;
  if (count < 1) return null;
  return {
    type: "warning",
    title: "退出 BOSS Harness",
    message: count === 1 ? "有 1 个招聘任务正在运行" : `有 ${count} 个招聘任务正在运行`,
    detail: "现在退出会中断正在运行的回合；已排队但尚未开始的后续消息会保留，已执行的招聘操作不会撤回。",
    buttons: ["继续运行", "停止并退出"],
    defaultId: 0,
    cancelId: 0,
    noLink: true,
  };
}
