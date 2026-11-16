import type { WorkspaceInstructionsState, WorkspaceInstructionsWriteResponse } from "@boss-harness/protocol";

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

/**
 * 保存回执的规范化结果；字段缺失或类型不符时返回 `null`。
 *
 * 保存后界面应以内核回执为准。只用本地 payload 合成状态时，正文的空白判定
 * 与内核不一致会给出相反提示（例如看起来为空、内核却按已加载注入）；真实
 * 保存路径、字节数与上限也不会进入界面。写入成功回执只可能是 `loaded` /
 * `empty`，其余状态说明回执不可信。
 */
export function workspaceInstructionWriteOf(value: unknown): WorkspaceInstructionsWriteResponse | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const status = workspaceInstructionStatusOf(raw.status);
  if (status !== "loaded" && status !== "empty") return null;
  const bytes = workspaceInstructionBytesOf(raw.bytes);
  if (bytes === null || bytes === undefined) return null;
  if (typeof raw.limitBytes !== "number" || !Number.isSafeInteger(raw.limitBytes) || raw.limitBytes <= 0) return null;
  if (typeof raw.path !== "string" || !raw.path || raw.path.length > 4096) return null;
  return { path: raw.path, bytes, status, limitBytes: raw.limitBytes };
}
