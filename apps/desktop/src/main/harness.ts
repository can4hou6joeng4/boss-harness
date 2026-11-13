import { existsSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { app, dialog, ipcMain, Notification, BrowserWindow, type IpcMainInvokeEvent, type MessageBoxReturnValue } from "electron";
import { HarnessHostManager, HarnessRpcError, type HarnessConnectionStatus, type HarnessHostConnection } from "@boss-harness/app-client";
import type { ApprovalFocusTarget, BadgeCountResult, JsonRpcNotification, NotificationTestResult,
  SessionExportSaveResult, StartupDiagnosis, ThreadFocusTarget } from "@boss-harness/protocol";
import { isTrustedRendererUrl, sessionExportFileName, validateHarnessRequest, validateLoginContext,
  validateSessionExportRequest, validateThreadExportResponse } from "./security";
import { PlatformLogin } from "./platformLogin";
import { preservesRpcError } from "./rpcErrors";
import { sessionExportWriteError } from "./exportErrors";
import { writeSessionExport } from "./sessionExportWrite";
import { approvalNotificationContent, rememberApproval } from "./approvalNotification";
import { readTurnEvent, recordTurnStart, turnNotificationContent } from "./turnNotification";
import { quitConfirmationContent } from "./quitConfirmation";
import { normalizeBadgeCount } from "./notificationBadge";
import { NotificationRegistry } from "./notificationRegistry";
import { StartupDiagnostics, runStartupCheck } from "./startupCheck";

function findRepoRoot(start: string): string {
  let current = resolve(start);
  for (let depth = 0; depth < 6; depth += 1) {
    if (existsSync(resolve(current, "pnpm-workspace.yaml"))) return current;
    const parent = resolve(current, "..");
    if (parent === current) break;
    current = parent;
  }
  return resolve(start, "..", "..");
}

const manager = new HarnessHostManager();
const windows = new Set<BrowserWindow>();
let host: HarnessHostConnection | null = null;
let diagnostics: StartupDiagnostics | null = null;
let repoRoot = "";
let ipcRegistered = false;
const platformLogin = new PlatformLogin((method, params) => {
  if (!host) return Promise.reject(new Error("harness host is not attached"));
  return host.request(method, params);
}, status => {
  for (const window of windows) {
    if (!window.isDestroyed()) window.webContents.send("platform-login:status", status);
  }
});

/** A window, its current main frame and its entry URL must all match. */
function trustedSender(event: IpcMainInvokeEvent): void {
  const window = [...windows].find((candidate) => !candidate.isDestroyed() && candidate.webContents === event.sender);
  if (!window || !event.senderFrame || event.senderFrame !== event.sender.mainFrame) {
    throw new Error("untrusted harness IPC sender");
  }
  if (!isTrustedRendererUrl(event.senderFrame.url, resolve(__dirname, "../renderer/index.html"), process.env.ELECTRON_RENDERER_URL)) {
    throw new Error("untrusted harness IPC origin");
  }
}

function send(window: BrowserWindow, notification: JsonRpcNotification): void {
  if (window.isDestroyed() || window.webContents.isDestroyed()) return;
  try { window.webContents.send("harness:notification", notification); } catch {}
}

const notifiedApprovals = new Set<string>();
const notifications = new NotificationRegistry();

/** 全部窗口已关闭时（macOS 关闭主窗口），点击通知需要重新创建主窗口；由主进程入口注入。 */
let windowFactory: (() => BrowserWindow | null) | null = null;
export function setHarnessWindowFactory(factory: () => BrowserWindow | null): void {
  windowFactory = factory;
}

/** 点击系统通知后回到工作台：恢复最小化窗口并聚焦；没有窗口时创建新窗口，返回目标窗口。 */
function revealWindow(): BrowserWindow | null {
  const existing = [...windows].find((window) => !window.isDestroyed());
  if (!existing) return windowFactory?.() ?? null;
  if (existing.isMinimized()) existing.restore();
  existing.show();
  existing.focus();
  return existing;
}

/** 新窗口加载完成前发送会丢失；等主 frame 加载后再发，preload 会缓存到渲染层挂载时回放。 */
function sendWhenLoaded(target: BrowserWindow, channel: string, payload: unknown): void {
  const deliver = (): void => {
    if (target.isDestroyed() || target.webContents.isDestroyed()) return;
    try { target.webContents.send(channel, payload); } catch {}
  };
  if (target.webContents.isLoadingMainFrame()) target.webContents.once("did-finish-load", deliver);
  else deliver();
}

function sendApprovalFocus(target: BrowserWindow, focus: ApprovalFocusTarget): void {
  sendWhenLoaded(target, "harness:focus-approval", focus);
}

function sendThreadFocus(target: BrowserWindow, focus: ThreadFocusTarget): void {
  sendWhenLoaded(target, "harness:focus-thread", focus);
}

const turnStartedAt = new Map<string, number>();

/**
 * 连接断开或重连时清空运行中回合：上一代内核进程的回合无法继续，
 * 也不应让退出确认基于残留状态反复拦截。
 */
function forgetTurnsOnDisconnect(notification: JsonRpcNotification): void {
  if (notification.method !== "harness/connectionStatus") return;
  const params = notification.params as { state?: unknown } | undefined;
  if (params?.state !== "ready") turnStartedAt.clear();
}

/**
 * 窗口不在前台时，用系统通知提示运行较久（≥ 20 秒）的回合已结束。
 * 开始时间来自 `turn/started`；缺少配对开始时间时不猜测时长，也不提醒。
 */
function notifyTurn(notification: JsonRpcNotification): void {
  const event = readTurnEvent(notification);
  if (!event) return;
  if (event.kind === "started") {
    recordTurnStart(turnStartedAt, event.turnId, Date.now());
    return;
  }
  const startedAt = turnStartedAt.get(event.turnId);
  turnStartedAt.delete(event.turnId);
  if (startedAt === undefined || BrowserWindow.getFocusedWindow()) return;
  const content = turnNotificationContent(notification, startedAt);
  if (!content || !Notification.isSupported()) return;
  try {
    const native = new Notification({ title: content.title, body: content.body });
    // 点击后回到该回合所属会话；会话已删除或列表尚未加载时由渲染层保持当前视图。
    native.on("click", () => {
      const target = revealWindow();
      if (target) sendThreadFocus(target, { threadId: event.threadId });
    });
    notifications.show(native);
  } catch {}
}

/**
 * 窗口不在前台时用系统通知提示新的审批请求；同一 approvalId 只提醒一次。
 * 点击后聚焦工作台，定位字段齐全时再让渲染层打开会话并滚动到该审批卡。
 * 通知失败（系统不支持、权限或平台限制）只影响提醒，不影响窗口内通知转发。
 */
function notifyApproval(notification: JsonRpcNotification): void {
  if (BrowserWindow.getFocusedWindow()) return;
  const content = approvalNotificationContent(notification);
  if (!content || !rememberApproval(notifiedApprovals, content.approvalId)) return;
  if (!Notification.isSupported()) return;
  try {
    const native = new Notification({ title: content.title, body: content.body });
    native.on("click", () => {
      const target = revealWindow();
      if (!target || !content.threadId || !content.itemId) return;
      sendApprovalFocus(target, { threadId: content.threadId, itemId: content.itemId });
    });
    notifications.show(native);
  } catch {}
}

type DesktopConnectionStatus = HarnessConnectionStatus & { startupDiagnosis?: StartupDiagnosis };

/** 连接状态附带当前失败周期的本地自检结论；结论只在握手前失败后产生。 */
function connectionStatus(connection: HarnessHostConnection): DesktopConnectionStatus {
  const diagnosis = diagnostics?.result;
  return { ...connection.status(), ...(diagnosis ? { startupDiagnosis: diagnosis } : {}) };
}

/**
 * 握手前失败时安排一次本地自检，连接恢复后丢弃结论；转发给窗口的连接状态附带现有结论。
 * 自动重试期间的重复失败共用同一份结论，不重复启动自检进程。
 */
function withStartupDiagnosis(notification: JsonRpcNotification): JsonRpcNotification {
  if (notification.method !== "harness/connectionStatus") return notification;
  const status = notification.params as Partial<HarnessConnectionStatus> | undefined;
  if (status?.state === "ready") diagnostics?.reset();
  else if (status?.state === "disconnected" && status.startupFailed === true) diagnostics?.request();
  const diagnosis = diagnostics?.result;
  return diagnosis ? { ...notification, params: { ...status, startupDiagnosis: diagnosis } } : notification;
}

function createHost(): HarnessHostConnection {
  repoRoot = findRepoRoot(app.getAppPath());
  const venvPython = resolve(repoRoot, ".venv", "bin", "python");
  const python = process.env.BOSS_HARNESS_PYTHON ?? (existsSync(venvPython) ? venvPython : "python3");
  const env = {
    PYTHONPATH: resolve(repoRoot, "harness", "src"), PYTHONUNBUFFERED: "1",
    BOSS_HARNESS_PROVIDER: process.env.BOSS_HARNESS_PROVIDER ?? "openai",
  };
  const connection = manager.add({
    hostId: "local",
    clientInfo: { name: "boss-harness-desktop", version: app.getVersion() },
    supportsReconnect: true,
    // Explicit user recovery is also exposed; this small retry budget covers process crashes.
    autoReconnect: { maxAttempts: 3, initialDelayMs: 500, maxDelayMs: 5_000 },
    client: { command: python, args: ["-m", "boss_harness", "--listen", "stdio://"], cwd: repoRoot, env },
  });
  // 自检与内核共用解释器、工作目录和环境，结论才对应同一份启动配置；只额外固定输出编码。
  diagnostics = new StartupDiagnostics(
    (signal) => runStartupCheck({
      command: python, args: ["-m", "boss_harness", "--check"], cwd: repoRoot,
      env: { ...process.env, ...env, PYTHONIOENCODING: "utf-8" },
    }, signal),
    // 自检晚于断开通知结束：补发一次连接状态，窗口不需要轮询。
    () => {
      const status: JsonRpcNotification = {
        jsonrpc: "2.0", method: "harness/connectionStatus", params: connectionStatus(connection),
      };
      for (const window of windows) send(window, status);
    },
  );
  connection.onNotification((notification) => {
    forgetTurnsOnDisconnect(notification);
    const outgoing = withStartupDiagnosis(notification);
    for (const window of windows) send(window, outgoing);
    notifyApproval(notification);
    notifyTurn(notification);
  });
  return connection;
}

let quitConfirmed = false;
let quitPromptOpen = false;

/**
 * 存在运行中回合时拦截退出并显示原生确认框。
 * 返回 true 表示可以继续退出；选择「继续运行」会取消本次退出并恢复主窗口。
 */
function confirmQuit(event: { preventDefault(): void }): boolean {
  if (quitConfirmed) return true;
  const content = quitConfirmationContent(turnStartedAt.size);
  if (!content) return true;
  event.preventDefault();
  if (quitPromptOpen) return false;
  quitPromptOpen = true;
  const parent = [...windows].find((window) => !window.isDestroyed());
  let prompt: Promise<MessageBoxReturnValue>;
  try {
    prompt = parent ? dialog.showMessageBox(parent, content) : dialog.showMessageBox(content);
  } catch {
    prompt = Promise.reject(new Error("quit confirmation could not open"));
  }
  void prompt.then(({ response }) => {
    quitPromptOpen = false;
    if (response !== 1) { revealWindow(); return; }
    quitConfirmed = true;
    app.quit();
  }, () => {
    // 确认框无法显示或完成时按用户明确的退出意图继续退出，避免应用无法关闭。
    quitPromptOpen = false;
    quitConfirmed = true;
    app.quit();
  });
  return false;
}

function registerIPC(): void {
  if (ipcRegistered) return;
  ipcRegistered = true;
  ipcMain.handle("platform-login:action", async (event, action: unknown, payload: unknown) => {
    trustedSender(event);
    if (action === "status") return platformLogin.read();
    const context = validateLoginContext(payload);
    const parent = BrowserWindow.fromWebContents(event.sender)!;
    if (action === "open") {
      if (!host) throw new Error("harness host is not attached");
      // 只确认会话存在：读取全部条目与回合会让长会话撞上内核 1 MiB 响应预算，
      // 而登录本身不需要会话内容。
      await host.request("thread/read", { threadId: context.threadId, excludeTurns: true });
      if (parent.isDestroyed()) throw new Error("login parent was closed");
      return platformLogin.open(parent, context.threadId);
    }
    if (["layout", "back", "forward", "reload", "cancel"].includes(action as string)) {
      return platformLogin.control(parent, action as "layout" | "back" | "forward" | "reload" | "cancel", context);
    }
    throw new Error("invalid platform login action");
  });
  ipcMain.handle("harness:request", async (event, payload: unknown) => {
    trustedSender(event);
    const request = validateHarnessRequest(payload);
    if (!host) throw new Error("harness host is not attached");
    try { return await host.request(request.method, request.params); }
    catch (error) {
      if (preservesRpcError(request.method) && error instanceof HarnessRpcError && error.code !== -32603) {
        return { __harnessRpcError: { code: error.code, message: error.message, data: error.data } };
      }
      throw error;
    }
  });
  // Session export: the kernel renders redacted text, the main process asks where to save and writes it.
  // The renderer only receives the chosen file's base name and counts, never the exported content or path.
  let exportInFlight = false;
  ipcMain.handle("session-export:save", async (event, payload: unknown): Promise<SessionExportSaveResult | { __harnessRpcError: unknown }> => {
    trustedSender(event);
    const request = validateSessionExportRequest(payload);
    if (!host) throw new Error("harness host is not attached");
    if (exportInFlight) throw new Error("another session export is in progress");
    exportInFlight = true;
    try {
      let response: unknown;
      try {
        response = await host.request("thread/export", { threadId: request.threadId, view: request.view,
          format: request.format, includeToolResults: request.includeToolResults });
      } catch (error) {
        if (error instanceof HarnessRpcError && error.code !== -32603) {
          return { __harnessRpcError: { code: error.code, message: error.message, data: error.data } };
        }
        throw error;
      }
      const exported = validateThreadExportResponse(response, request);
      const parent = BrowserWindow.fromWebContents(event.sender);
      if (!parent || parent.isDestroyed()) throw new Error("export parent was closed");
      const filter = request.format === "markdown" ? { name: "Markdown", extensions: ["md"] }
        : request.format === "html" ? { name: "HTML", extensions: ["html"] } : { name: "JSON", extensions: ["json"] };
      const choice = await dialog.showSaveDialog(parent, {
        title: "导出会话", defaultPath: join(app.getPath("downloads"), sessionExportFileName(request)),
        filters: [filter],
        properties: ["createDirectory", "showOverwriteConfirmation"],
      });
      if (choice.canceled || !choice.filePath) return { saved: false, canceled: true };
      // Never follow a symlink picked (or pre-planted) at the save path, and do not report OS paths back.
      const written = await writeSessionExport(choice.filePath, exported.content).catch((error: unknown) => {
        // 提示只带 errno，不带系统路径；日志同样避免写入选中路径。
        const message = sessionExportWriteError(error);
        console.error("session export write failed", message);
        throw new Error(message);
      });
      if (written.permissionError) {
        // 内容已经写入；权限收紧失败只记录 errno，不影响保存结果。
        console.error("session export permission update failed", sessionExportWriteError(written.permissionError));
      }
      return { saved: true, fileName: basename(choice.filePath), bytes: Buffer.byteLength(exported.content, "utf8"),
        truncated: exported.truncated, turnCount: exported.turnCount, exportedTurnCount: exported.exportedTurnCount,
        toolResults: exported.toolResults, redactions: { ...exported.redactions },
        ...(written.permissionsUnchanged ? { permissionsUnchanged: true } : {}) };
    } finally {
      exportInFlight = false;
    }
  });
  ipcMain.handle("harness:status", (event) => {
    trustedSender(event);
    return { ...connectionStatus(manager.get()), repoRoot };
  });
  ipcMain.handle("harness:reconnect", async (event) => {
    trustedSender(event);
    const connection = manager.get();
    // 显式重连开启新的失败周期：旧结论对应的可能已经不是当前配置。
    diagnostics?.reset();
    // 启动失败不作为 IPC 异常抛出：原因由返回的连接状态与自检结论表达。
    try { await connection.reconnect(); } catch { /* 见返回的连接状态。 */ }
    await diagnostics?.settled();
    return { ...connectionStatus(connection), repoRoot };
  });
  ipcMain.handle("notification:badge", (event, value: unknown): BadgeCountResult => {
    trustedSender(event);
    const count = normalizeBadgeCount(value);
    // 非法数量忽略，保持现有徽标；平台不支持时返回 false，不影响侧栏与通知面板。
    if (count === null) return { applied: false };
    try { return { applied: app.setBadgeCount(count) }; } catch { return { applied: false }; }
  });
  ipcMain.handle("notification:test", (event): NotificationTestResult => {
    trustedSender(event);
    if (!Notification.isSupported()) return { sent: false, supported: false };
    try {
      const native = new Notification({ title: "Boss Harness", body: "系统通知可用：审批请求与较久回合结束会通过这里提醒。" });
      notifications.show(native);
      return { sent: true, supported: true };
    } catch {
      return { sent: false, supported: true };
    }
  });
  app.on("before-quit", (event) => {
    if (!confirmQuit(event)) return;
    platformLogin.cancel(); diagnostics?.reset(); diagnostics = null; manager.dispose(); host = null; windows.clear();
  });
}

/** Windows subscribe to the host registry; closing one window cannot stop the backend. */
export function attachHarness(window: BrowserWindow): void {
  if (windows.has(window)) return;
  windows.add(window);
  window.once("closed", () => { windows.delete(window); if (!windows.size) platformLogin.cancel(); });
  host ??= createHost();
  registerIPC();
  window.webContents.on("did-finish-load", () => {
    if (host) send(window, { jsonrpc: "2.0", method: "harness/connectionStatus", params: connectionStatus(host) });
  });
  void host.ensureReady().catch(() => { /* Host status conveys initialization and reconnect failures. */ });
}
