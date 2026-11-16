import type { WorkspaceInstructionsState } from "@boss-harness/protocol";

/**
 * 工作区说明读取回执的共享判定。
 *
 * 两个入口（「技能与工具」页与上下文面板编辑器）都按 `STATUS_TEXT[status]`
 * 渲染状态：未知状态会得到 `undefined` 并显示成空白；`bytes` 未校验时
 * `toLocaleString` 会把非法值显示成 `NaN` 或 `[object Object]`。枚举与计数
 * 在这里集中收敛，调用方按「回执无法识别」处理。
 */
const STATUSES: ReadonlySet<string> = new Set(["loaded", "empty", "too_large", "unreadable"]);

export function workspaceInstructionStatusOf(value: unknown): WorkspaceInstructionsState["status"] | null {
  return typeof value === "string" && STATUSES.has(value)
    ? value as WorkspaceInstructionsState["status"] : null;
}

/** 字节数允许为 `null`（超限或不可读时未知），否则必须是非负安全整数。 */
export function workspaceInstructionBytesOf(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (typeof value === "number" && Number.isSafeInteger(value) && value >= 0) return value;
  return undefined;
}
