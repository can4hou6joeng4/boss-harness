import type { HarnessConnectionStatus } from "@boss-harness/app-client";
import type { ApprovalFocusTarget, BadgeCountResult, JsonRpcNotification, NotificationTestResult,
  PlatformLoginAction, PlatformLoginContext, PlatformLoginStatus, SessionExportSaveRequest,
  SessionExportSaveResult, StartupDiagnosis, ThreadFocusTarget } from "@boss-harness/protocol";

/**
 * 运行状态：宿主连接状态加上桌面主进程补充的字段。
 * preload 的返回类型与渲染层声明共用这一份定义，避免两侧手工同步。
 */
export interface DesktopHarnessStatus extends HarnessConnectionStatus {
  repoRoot: string;
  /** 握手前失败后的本地自检结论；连接恢复或显式重连后不再返回。 */
  startupDiagnosis?: StartupDiagnosis;
}

export interface BossVersions {
  electron: string;
  chrome: string;
  node: string;
  platform: string;
}

/**
 * 渲染层可见的桥接面：preload 实现与 env.d.ts 声明共用此类型。
 * 新增成员只需修改这里，两侧会同时接受类型检查。
 */
export interface BossBridge {
  request<T>(method: string, params?: unknown): Promise<T>;
  status(): Promise<DesktopHarnessStatus>;
  reconnect(): Promise<DesktopHarnessStatus>;
  /** 随时运行本地配置自检；与启动失败自检共用主进程里的命令、解释器、工作目录与环境。 */
  runStartupCheck(): Promise<StartupDiagnosis>;
  exportSession(request: SessionExportSaveRequest): Promise<SessionExportSaveResult>;
  platformLogin(action: PlatformLoginAction, context?: PlatformLoginContext): Promise<PlatformLoginStatus>;
  onPlatformLogin(listener: (status: PlatformLoginStatus) => void): () => void;
  onNotification(listener: (notification: JsonRpcNotification) => void): () => void;
  onApprovalFocus(listener: (target: ApprovalFocusTarget) => void): () => void;
  onThreadFocus(listener: (target: ThreadFocusTarget) => void): () => void;
  testNotification(): Promise<NotificationTestResult>;
  setBadgeCount(count: number): Promise<BadgeCountResult>;
  versions: BossVersions;
}
