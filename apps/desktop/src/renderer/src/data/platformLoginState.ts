import type { PlatformLoginStatus } from "@boss-harness/protocol";

const LOGIN_STATES: ReadonlySet<string> = new Set([
  "idle", "opening", "waiting", "saving", "succeeded", "failed", "blocked", "cancelled", "disabled",
]);
const LOGIN_PHASES: ReadonlySet<string> = new Set(["scan", "confirm", "credentials", "verify"]);
const LOGIN_IDENTITIES: ReadonlySet<string> = new Set(["jobSeeker", "recruiter", "unknown"]);
const SUMMARY_LIMIT = 4096;
const CODE_LIMIT = 120;
const ID_LIMIT = 200;

/** 主进程正在占用登录，与 `PlatformLogin.open` 的占用判定一致。 */
export const loginActive = (status: PlatformLoginStatus): boolean => ["opening", "waiting", "saving"].includes(status.state);

/** 登录已结束；只有这些状态值得让设置页重读连接检查。 */
export const loginSettled = (status: PlatformLoginStatus): boolean =>
  ["succeeded", "blocked", "failed", "cancelled"].includes(status.state);

/**
 * 登录状态回执的形状校验。
 *
 * 主进程广播与 `platformLogin` 调用回执进入界面状态前都要逐项核对：
 * `AppShell` 直接读取 `status.threadId`，引导卡片直接渲染 `summary` / `code`。
 * 缺 `summary`、未知 `state` 或非字符串的 `code` 会让引导条常驻无取消入口，
 * 或让 React 渲染对象直接抛错；无法识别的回执整体拒绝，界面保留上一次有效状态。
 */
export function platformLoginStatusOf(value: unknown): PlatformLoginStatus | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.state !== "string" || !LOGIN_STATES.has(raw.state)) return null;
  if (typeof raw.summary !== "string" || raw.summary.length > SUMMARY_LIMIT) return null;
  if (raw.code !== undefined && raw.code !== null
    && (typeof raw.code !== "string" || raw.code.length > CODE_LIMIT)) return null;
  if (raw.phase !== undefined && (typeof raw.phase !== "string" || !LOGIN_PHASES.has(raw.phase))) return null;
  if (raw.identity !== undefined && (typeof raw.identity !== "string" || !LOGIN_IDENTITIES.has(raw.identity))) return null;
  for (const key of ["threadId", "browserId"] as const) {
    const item = raw[key];
    if (item !== undefined && (typeof item !== "string" || item.length === 0 || item.length > ID_LIMIT)) return null;
  }
  let browser: PlatformLoginStatus["browser"];
  if (raw.browser !== undefined) {
    const candidate = raw.browser;
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
    const fields = candidate as Record<string, unknown>;
    if (typeof fields.available !== "boolean" || typeof fields.loading !== "boolean"
      || typeof fields.canGoBack !== "boolean" || typeof fields.canGoForward !== "boolean") return null;
    browser = { available: fields.available, loading: fields.loading,
      canGoBack: fields.canGoBack, canGoForward: fields.canGoForward };
  }
  return {
    state: raw.state as PlatformLoginStatus["state"],
    summary: raw.summary,
    ...(raw.code !== undefined ? { code: raw.code as string | null } : {}),
    ...(raw.phase !== undefined ? { phase: raw.phase as PlatformLoginStatus["phase"] } : {}),
    ...(raw.identity !== undefined ? { identity: raw.identity as PlatformLoginStatus["identity"] } : {}),
    ...(raw.threadId !== undefined ? { threadId: raw.threadId as string } : {}),
    ...(raw.browserId !== undefined ? { browserId: raw.browserId as string } : {}),
    ...(browser ? { browser } : {}),
  };
}

/**
 * `open` 失败后的全局状态回落。
 *
 * 失败不保证主进程状态已变：另一会话正在等待扫码、宿主未连接或父窗口已销毁时，
 * 主进程会在改动状态之前抛错。此时全局状态仍属于那次登录，`threadId` 与
 * `browserId` 决定另一会话的原生浏览器可见性与取消入口，不能用本会话的失败态
 * 覆盖。只有状态不属于其他会话、且本会话不在活跃登录中时，才写入失败态。
 */
export function fallbackLoginStatus(previous: PlatformLoginStatus, threadId: string): PlatformLoginStatus {
  if (previous.threadId !== undefined && previous.threadId !== threadId) return previous;
  if (loginActive(previous)) return previous;
  return { threadId, state: "failed", summary: "官方登录页尚未打开" };
}
