import { isTrustedRendererUrl } from "./security";

/**
 * 主窗口只使用受信渲染入口的剪贴板写入；其余浏览器权限都没有使用场景。
 * Electron 在没有处理器时默认批准所有请求，因此必须把唯一需要的权限点名。
 */
const MAIN_WINDOW_PERMISSIONS: ReadonlySet<string> = new Set(["clipboard-sanitized-write"]);

/**
 * 主窗口的权限判定：权限必须在显式白名单内，且请求来自受信的渲染入口
 * （打包后的 `file://` 页面或开发服务器）。平台登录使用独立隔离分区，
 * 已有自己的全拒绝处理器，不经过这里。
 */
export function allowsMainWindowPermission(
  permission: string,
  requestingUrl: string | undefined,
  entryFile: string,
  devUrl?: string,
): boolean {
  return Boolean(requestingUrl) && MAIN_WINDOW_PERMISSIONS.has(permission) &&
    isTrustedRendererUrl(requestingUrl!, entryFile, devUrl);
}
