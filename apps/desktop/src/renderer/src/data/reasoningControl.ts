import type { ThreadReasoningReadResponse } from "@boss-harness/protocol";

/** 推理设置操作的可用性：断连或没有会话时必须给出原因，不能静默丢弃点击。 */
export type ReasoningAction = "读取" | "保存";

export type ReasoningTarget =
  | { ok: true; threadId: string }
  | { ok: false; notice: string };

/**
 * 解析操作目标；不可执行时带回可见提示。
 *
 * `useSessionReasoning` 曾在断连时直接 return：既不设 pending 也不设 error，
 * Composer 的「重新加载推理设置」与档位按钮点了毫无反应，用户无法判断原因。
 */
export function reasoningTarget(action: ReasoningAction, threadId: string | null, connected: boolean): ReasoningTarget {
  if (!connected) return { ok: false, notice: `无法${action}会话推理设置：本地内核未连接。恢复连接后再试。` };
  if (!threadId) return { ok: false, notice: `无法${action}会话推理设置：当前没有可操作的会话。` };
  return { ok: true, threadId };
}

/**
 * 规范化 `thread/reasoning/read` 回执；字段缺失或类型不符时返回 `null`。
 *
 * 回执来自进程边界。`supported` 被写成非布尔真值时，输入区菜单会把有效档位
 * 标成「不在当前模型支持列表中」；`summaryActive` 为真值字符串时，摘要占用
 * 轮询判定持续成立，hook 会每秒重读同一份响应。归属与每个字段都必须成立，
 * 未知字段不进入结果。
 */
export function reasoningReadOf(value: unknown, expectedThreadId: string): ThreadReasoningReadResponse | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (raw.threadId !== expectedThreadId || typeof raw.model !== "string") return null;
  if (raw.effort !== null && typeof raw.effort !== "string") return null;
  if (raw.configuredEffort !== null && typeof raw.configuredEffort !== "string") return null;
  if (typeof raw.supported !== "boolean" || typeof raw.summaryActive !== "boolean") return null;
  if (!Array.isArray(raw.availableEfforts) || raw.availableEfforts.some(effort => typeof effort !== "string")) return null;
  if (typeof raw.capabilitySource !== "string" || typeof raw.capabilityIsEstimate !== "boolean") return null;
  return {
    threadId: expectedThreadId,
    model: raw.model,
    effort: raw.effort,
    configuredEffort: raw.configuredEffort,
    supported: raw.supported,
    summaryActive: raw.summaryActive,
    availableEfforts: raw.availableEfforts as string[],
    capabilitySource: raw.capabilitySource,
    capabilityIsEstimate: raw.capabilityIsEstimate,
  };
}
