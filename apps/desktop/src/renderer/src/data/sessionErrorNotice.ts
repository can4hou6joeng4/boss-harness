/**
 * `session/error` 通知的形状校验。
 *
 * 提示条把正文直接渲染为 React 子节点：对象或数组会抛
 * `Objects are not valid as a React child`，让整屏落入应用级错误边界；
 * 非字符串的会话标识会污染错误缓存与提示归属。无法识别的通知整条丢弃，
 * 保留上一次有效提示。
 */
import { safeSlice } from "@boss-harness/shared";

const ID_LIMIT = 200;
/** 提示条是单行摘要：折叠空白并按字符上限截断，避免损坏正文撑破布局。 */
const MESSAGE_LIMIT = 600;

/** 内核通知缺少正文时的通用说明；正文为空白字符串时同样使用。 */
export const SESSION_ERROR_FALLBACK = "任务遇到错误，请检查后重试。";

export interface SessionErrorNotice {
  threadId: string;
  message: string;
}

function compact(value: string): string {
  const collapsed = value.replace(/\s+/g, " ").trim();
  if (collapsed.length <= MESSAGE_LIMIT) return collapsed;
  return `${safeSlice(collapsed, MESSAGE_LIMIT - 1).trimEnd()}…`;
}

/**
 * 解析 `session/error` 参数。
 *
 * `threadId` 必须是长度有上限的非空字符串；`message` 缺省或为 `null` 时
 * 回退通用文案，是字符串时折叠空白并按上限截断，其余类型整条通知丢弃。
 * 多余字段不进入结果。
 */
export function sessionErrorNoticeOf(params: unknown): SessionErrorNotice | null {
  if (!params || typeof params !== "object" || Array.isArray(params)) return null;
  const raw = params as Record<string, unknown>;
  if (typeof raw.threadId !== "string" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT) return null;
  if (raw.message !== undefined && raw.message !== null && typeof raw.message !== "string") return null;
  const message = typeof raw.message === "string" ? compact(raw.message) : "";
  return { threadId: raw.threadId, message: message || SESSION_ERROR_FALLBACK };
}
