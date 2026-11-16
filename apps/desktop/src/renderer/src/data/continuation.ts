import type { TurnContinuationBoundary, TurnContinuationReadResponse } from "@boss-harness/protocol";
import { safeSlice } from "@boss-harness/shared";

/**
 * `turn/continuation/read` 回执的形状校验。
 *
 * 会话区直接把 `warning` 与 `reason` 作为 React 子节点渲染，`eligible` 决定是否
 * 提供「继续中断回合」按钮，`boundary` 决定检查点文案，`completedToolCalls` 进入
 * 模板字符串。内核回执损坏或跨版本不兼容时，对象字段会让会话区落入应用级错误
 * 边界，非布尔 `eligible` 又会让不可续接的回合显示续接按钮。这里对身份与全部
 * 展示字段整体校验；`boundary` / `completedToolCalls` / `reason` / `reasonCode`
 * 缺失时保持旧内核兼容。
 */
const ID_LIMIT = 200;
const WARNING_LIMIT = 2048;
const REASON_LIMIT = 2048;
const REASON_CODE_LIMIT = 120;
const BOUNDARIES: ReadonlySet<string> = new Set(["user_input", "completed_tool_batch"]);

const isId = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;
const isCount = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const plainRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

function invalid(): never {
  throw new Error("续接预检回执无法识别，已停止操作。");
}

export interface ContinuationExpectation {
  threadId: string;
  sourceTurnId: string;
}

/** 校验并收敛一份续接预检回执；无法识别时抛出与既有预检失败一致的错误。 */
export function continuationReadOf(value: unknown, expected: ContinuationExpectation): TurnContinuationReadResponse {
  const raw = plainRecord(value);
  if (!raw || raw.threadId !== expected.threadId || raw.sourceTurnId !== expected.sourceTurnId) {
    throw new Error("预检结果与来源回合不一致");
  }
  if (!isId(raw.threadId) || !isId(raw.sourceTurnId)) invalid();
  if (typeof raw.eligible !== "boolean") invalid();
  if (typeof raw.warning !== "string") invalid();
  const result: TurnContinuationReadResponse = {
    threadId: raw.threadId,
    sourceTurnId: raw.sourceTurnId,
    eligible: raw.eligible,
    warning: safeSlice(raw.warning, WARNING_LIMIT),
  };
  // 检查点边界只接受两个已知值：未知值会被会话区显示成「已完成的工具批次」。
  if (raw.boundary !== undefined && raw.boundary !== null) {
    if (typeof raw.boundary !== "string" || !BOUNDARIES.has(raw.boundary)) invalid();
    result.boundary = raw.boundary as TurnContinuationBoundary;
  }
  // 已完成工具调用次数进入模板字符串：只接受非负安全整数。
  if (raw.completedToolCalls !== undefined && raw.completedToolCalls !== null) {
    if (!isCount(raw.completedToolCalls)) invalid();
    result.completedToolCalls = raw.completedToolCalls;
  }
  // 原因与原因码只用于说明不可续接的缘由；空白按缺失处理，过长截断且不切开代理对。
  for (const [key, limit] of [["reason", REASON_LIMIT], ["reasonCode", REASON_CODE_LIMIT]] as const) {
    const field = raw[key];
    if (field === undefined || field === null) continue;
    if (typeof field !== "string") invalid();
    const text = field.trim();
    if (!text) continue;
    result[key] = safeSlice(text, limit);
  }
  return result;
}
