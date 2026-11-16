/**
 * 内核 `platform/login/*` 回执的形状校验。
 *
 * 这些回执决定主进程登录状态机的占用、取消与轮询分支：未知 `state` 或缺失
 * `summary` 一旦经 `update()` 写入 `this.status`，占用判定与取消入口全部失真，
 * 而渲染层对同一值整体拒绝后主进程与界面会脱节。无法识别的回执整体拒绝，
 * 调用方按失败处理，并且只在内核 `id` 合法时才补发取消请求。
 *
 * 字段规则与渲染层 `data/platformLoginState.ts` 的 `platformLoginStatusOf()` 对齐；
 * 主进程不 import 渲染层模块，两份校验各自覆盖所在进程的消费面。
 */

const LOGIN_STATES: ReadonlySet<string> = new Set([
  "idle", "opening", "waiting", "saving", "succeeded", "failed", "blocked", "cancelled", "disabled",
]);
const LOGIN_PHASES: ReadonlySet<string> = new Set(["scan", "confirm", "credentials", "verify"]);
const LOGIN_IDENTITIES: ReadonlySet<string> = new Set(["jobSeeker", "recruiter", "unknown"]);
const SUMMARY_LIMIT = 4096;
const CODE_LIMIT = 120;
const ID_LIMIT = 200;

/** 校验后的内核回执：只含协议字段，`id` 用于定位随后的 cancel / read。 */
export interface LoginAttemptStatus {
  state: "idle" | "opening" | "waiting" | "saving" | "succeeded" | "failed" | "blocked" | "cancelled" | "disabled";
  summary: string;
  code?: string | null;
  phase?: "scan" | "confirm" | "credentials" | "verify";
  identity?: "jobSeeker" | "recruiter" | "unknown";
  id?: string;
}

/** 回执里的内核 attempt id；只有合法字符串才可用于补发取消。 */
export function attemptIdOf(value: unknown): string | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const id = (value as Record<string, unknown>).id;
  return typeof id === "string" && id.length > 0 && id.length <= ID_LIMIT ? id : undefined;
}

export function loginAttemptOf(value: unknown): LoginAttemptStatus | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.state !== "string" || !LOGIN_STATES.has(raw.state)) return null;
  if (typeof raw.summary !== "string" || raw.summary.length > SUMMARY_LIMIT) return null;
  if (raw.code !== undefined && raw.code !== null
    && (typeof raw.code !== "string" || raw.code.length > CODE_LIMIT)) return null;
  if (raw.phase !== undefined && (typeof raw.phase !== "string" || !LOGIN_PHASES.has(raw.phase))) return null;
  if (raw.identity !== undefined && (typeof raw.identity !== "string" || !LOGIN_IDENTITIES.has(raw.identity))) return null;
  if (raw.id !== undefined && (typeof raw.id !== "string" || raw.id.length === 0 || raw.id.length > ID_LIMIT)) return null;
  return {
    state: raw.state as LoginAttemptStatus["state"],
    summary: raw.summary,
    ...(raw.code !== undefined ? { code: raw.code as string | null } : {}),
    ...(raw.phase !== undefined ? { phase: raw.phase as LoginAttemptStatus["phase"] } : {}),
    ...(raw.identity !== undefined ? { identity: raw.identity as LoginAttemptStatus["identity"] } : {}),
    ...(raw.id !== undefined ? { id: raw.id as string } : {}),
  };
}