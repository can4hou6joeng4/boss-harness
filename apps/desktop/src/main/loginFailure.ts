import { safeSlice, stripIpcErrorWrapper } from "@boss-harness/shared";
import { rendererGoneSummary, type RendererGoneDetails } from "./rendererRecovery";

/**
 * 平台登录流程失败时的诊断信息。
 *
 * 主进程此前把打开、保存失败都写成同一条固定摘要；保留内核原因码与可读消息，
 * 才能区分「内核拒绝/忙」与「本机断连」。消息去掉 Electron 的 IPC 包装前缀并限制长度。
 */
export function loginFailureDetail(error: unknown): { code?: string; message?: string } {
  const value = error && typeof error === "object"
    ? error as { data?: unknown; message?: unknown } : null;
  const data = value?.data && typeof value.data === "object" ? value.data as { code?: unknown } : null;
  const code = typeof data?.code === "string" && data.code ? data.code : undefined;
  const raw = typeof value?.message === "string" ? stripIpcErrorWrapper(value.message).trim() : "";
  return { ...(code ? { code } : {}), ...(raw ? { message: safeSlice(raw, 200) } : {}) };
}

/** 登录页渲染进程退出时给用户的说明；正常关闭与意外退出发出不同提示。 */
export function loginViewGoneSummary(details: RendererGoneDetails | null | undefined): string {
  if (details?.reason === "clean-exit") return "官方登录页已关闭，请重新打开官方页面";
  return `官方登录页界面进程已退出：${rendererGoneSummary(details)}，请重新打开官方页面`;
}
