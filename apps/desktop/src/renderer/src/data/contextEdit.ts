import type { ContextEditReadResponse } from "@boss-harness/protocol";
import { safeSlice } from "@boss-harness/shared";

/**
 * `context/edit/read` 回执的形状校验。
 *
 * 编辑弹窗把 `reason` 直接作为状态说明与警告正文渲染：对象或数组会让 React 抛
 * “Objects are not valid as a React child”，整个弹窗落入错误边界；超长字符串没有
 * 上限，会铺满弹窗；数字会被静默显示。身份、来源摘要、正文与布尔标记之外，
 * 这里同时收敛可选原因，读取与提交后的回读共用这一入口。
 */
const ID_LIMIT = 200;
/** 单条消息正文上限的两倍余量；内核编辑读取受约 1 MiB 响应预算约束。 */
const TEXT_LIMIT = 2_000_000;
const REASON_LIMIT = 4096;
const SOURCE_DIGEST = /^[a-f0-9]{64}$/;

const isText = (value: unknown): value is string => typeof value === "string" && value.length <= TEXT_LIMIT;
const isId = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;
const plainRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

function invalid(): never {
  throw new Error("上下文编辑响应与当前消息不匹配，已停止操作。");
}

export interface ContextEditExpectation {
  threadId: string;
  itemId: string;
}

/** 校验并收敛一份上下文编辑回执；无法识别时抛出与既有提示一致的错误。 */
export function contextEditOf(value: unknown, expected: ContextEditExpectation): ContextEditReadResponse {
  const raw = plainRecord(value);
  if (!raw || raw.threadId !== expected.threadId || raw.itemId !== expected.itemId) invalid();
  if (!isId(raw.threadId) || !isId(raw.itemId)) invalid();
  if (typeof raw.sourceDigest !== "string" || !SOURCE_DIGEST.test(raw.sourceDigest)) invalid();
  if (!isText(raw.originalText)) invalid();
  if (raw.currentText !== null && !isText(raw.currentText)) invalid();
  if (typeof raw.canEdit !== "boolean" || typeof raw.excluded !== "boolean") invalid();
  const result: ContextEditReadResponse = {
    threadId: raw.threadId,
    itemId: raw.itemId,
    sourceDigest: raw.sourceDigest,
    originalText: raw.originalText,
    currentText: raw.currentText,
    canEdit: raw.canEdit,
    excluded: raw.excluded,
  };
  // 原因只用于说明「为什么不可编辑」：空白按缺失处理，过长截断且不切开代理对。
  if (raw.reason !== undefined && raw.reason !== null) {
    if (typeof raw.reason !== "string") invalid();
    const reason = raw.reason.trim();
    if (reason) result.reason = safeSlice(reason, REASON_LIMIT);
  }
  return result;
}
