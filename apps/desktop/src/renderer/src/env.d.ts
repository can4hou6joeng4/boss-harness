/// <reference types="vite/client" />

import type { ApprovalFocusTarget, BadgeCountResult, JsonRpcNotification, NotificationTestResult, PlatformLoginStatus, PlatformLoginAction, PlatformLoginContext, SessionExportSaveRequest, SessionExportSaveResult, StartupDiagnosis, ThreadFocusTarget } from "@boss-harness/protocol";
import type { HarnessConnectionStatus } from "@boss-harness/app-client";

/** 主进程返回的连接状态：宿主状态、仓库根目录，以及握手前失败后的本地自检结论。 */
type DesktopHarnessStatus = HarnessConnectionStatus & { repoRoot: string; startupDiagnosis?: StartupDiagnosis };

declare global {
  /** 构建时由 electron-vite 注入的发布版本号。 */
  const __APP_VERSION__: string;

  interface Window {
    boss: {
      request<T>(method: string, params?: unknown): Promise<T>;
      status(): Promise<DesktopHarnessStatus>;
      reconnect(): Promise<DesktopHarnessStatus>;
      exportSession(request: SessionExportSaveRequest): Promise<SessionExportSaveResult>;
      platformLogin(action: PlatformLoginAction, context?: PlatformLoginContext): Promise<PlatformLoginStatus>;
      onPlatformLogin(listener: (status: PlatformLoginStatus) => void): () => void;
      onNotification(listener: (notification: JsonRpcNotification) => void): () => void;
      onApprovalFocus(listener: (target: ApprovalFocusTarget) => void): () => void;
      onThreadFocus(listener: (target: ThreadFocusTarget) => void): () => void;
      testNotification(): Promise<NotificationTestResult>;
      setBadgeCount(count: number): Promise<BadgeCountResult>;
      /** 运行环境版本；浏览器预览没有该字段。 */
      versions?: { electron?: string; chrome?: string; node?: string; platform?: string };
    };
  }
}

export {};
