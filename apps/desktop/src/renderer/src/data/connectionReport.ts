import type { ConnectionCheck, ConnectionReport } from "@boss-harness/protocol";

const SUMMARY_LIMIT = 4096;
const CODE_LIMIT = 120;
const NAME_LIMIT = 200;
const TIME_LIMIT = 64;

const STATES: ReadonlySet<string> = new Set(["unchecked", "checking", "ready", "failed", "blocked", "disabled"]);
const BROWSER_SOURCES: ReadonlySet<string> = new Set(["inherit", "auto", "existing-browser", "stored-cookie"]);
const TEXT_FIELDS = ["provider", "model", "authState", "binarySource"] as const;

/**
 * `connection/check` 与 `connection/read` 的卡片校验。
 *
 * 设置页假定 `cli`、`model`、`platform` 三张卡片都存在，并在渲染期读取
 * `state`、`summary`、`authState` 与 `browserSourcePolicy`；缺卡片或 `null`
 * 会让 `Object.values(report).some(check => check.state === "checking")` 抛错，
 * 未知状态让徽标与来源标签显示为空白。
 */
function checkOf(value: unknown): ConnectionCheck | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.state !== "string" || !STATES.has(raw.state)) return null;
  if (typeof raw.summary !== "string" || raw.summary.length > SUMMARY_LIMIT) return null;
  if (raw.checkedAt !== undefined && raw.checkedAt !== null
    && (typeof raw.checkedAt !== "string" || raw.checkedAt.length > TIME_LIMIT)) return null;
  if (raw.code !== undefined && raw.code !== null
    && (typeof raw.code !== "string" || raw.code.length > CODE_LIMIT)) return null;
  const check: ConnectionCheck = { state: raw.state as ConnectionCheck["state"], summary: raw.summary };
  if (raw.checkedAt !== undefined) check.checkedAt = raw.checkedAt as string | null;
  if (raw.code !== undefined) check.code = raw.code as string | null;
  for (const field of TEXT_FIELDS) {
    const text = raw[field];
    if (text === undefined) continue;
    if (typeof text !== "string" || text.length > NAME_LIMIT) return null;
    check[field] = text;
  }
  if (raw.browserSourcePolicy !== undefined) {
    if (typeof raw.browserSourcePolicy !== "string" || !BROWSER_SOURCES.has(raw.browserSourcePolicy)) return null;
    check.browserSourcePolicy = raw.browserSourcePolicy as NonNullable<ConnectionCheck["browserSourcePolicy"]>;
  }
  if (raw.requestRejected !== undefined) {
    if (typeof raw.requestRejected !== "boolean") return null;
    check.requestRejected = raw.requestRejected;
  }
  return check;
}

/** 三张卡片必须同时存在且形状合法；任一不满足即整体返回 `null`。 */
export function connectionReportOf(value: unknown): ConnectionReport | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const cli = checkOf(raw.cli);
  const model = checkOf(raw.model);
  const platform = checkOf(raw.platform);
  if (!cli || !model || !platform) return null;
  return { cli, model, platform };
}
