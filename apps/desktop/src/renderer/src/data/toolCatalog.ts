import type { ToolDescriptor } from "@boss-harness/protocol";

const ID_LIMIT = 200;

function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

/**
 * `tool/list` 的条目校验。
 *
 * 「技能与工具」页直接渲染 `name`、`description` 与 `readOnly`，并以 `name`
 * 作为 React key；驾驶舱也读取同一份清单。`null` 条目会让渲染期读 `name`
 * 抛错并落入应用级错误边界，缺名或重名让清单行共用 key、操作指错工具。
 */
export function toolDescriptorOf(value: unknown): ToolDescriptor | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!text(raw.name, ID_LIMIT)) return null;
  if (typeof raw.description !== "string") return null;
  if (typeof raw.readOnly !== "boolean" || typeof raw.requiresApproval !== "boolean") return null;
  if (!raw.inputSchema || typeof raw.inputSchema !== "object" || Array.isArray(raw.inputSchema)) return null;
  let maxModelResultBytes: number | undefined;
  if (raw.maxModelResultBytes !== undefined) {
    if (!Number.isSafeInteger(raw.maxModelResultBytes) || (raw.maxModelResultBytes as number) < 0) return null;
    maxModelResultBytes = raw.maxModelResultBytes as number;
  }
  const executionMode = raw.executionMode === "sequential" || raw.executionMode === "parallel" ? raw.executionMode : undefined;
  if (raw.executionMode !== undefined && executionMode === undefined) return null;
  return {
    name: raw.name,
    description: raw.description,
    readOnly: raw.readOnly,
    requiresApproval: raw.requiresApproval,
    inputSchema: { ...(raw.inputSchema as Record<string, unknown>) },
    ...(maxModelResultBytes !== undefined ? { maxModelResultBytes } : {}),
    ...(executionMode ? { executionMode } : {}),
  };
}

/** 同一清单内的重复工具名会让 React key 冲突，行与权限标记无法区分。 */
export function uniqueToolNames(items: { name: string }[]): boolean {
  return new Set(items.map(item => item.name)).size === items.length;
}
