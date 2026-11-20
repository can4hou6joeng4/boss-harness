/**
 * 持久条目的展示字段收敛。
 *
 * 内核只保证条目是对象、审批是对象；可选展示字段可能来自旧版本或损坏的
 * 持久化记录。渲染层直接把这些字段交给 React 会让整个会话视图抛错，
 * 因此统一在映射入口按协议逐项校验：类型不符就退化为缺省，合法值原样保留。
 */
import type { ApprovalState, ThreadItem } from "@boss-harness/protocol";

const TOOL_STATUSES = new Set<NonNullable<ThreadItem["status"]>>(["running", "completed", "failed"]);
const TOOL_EXECUTION_STATES = new Set<NonNullable<ThreadItem["executionState"]>>([
  "queued", "pending_approval", "approved", "not_approved", "executing",
  "completed", "failed", "not_executed", "outcome_unknown",
]);
const APPROVAL_DECISIONS = new Set<NonNullable<ApprovalState["decision"]>>(["approve", "deny", "expired"]);

/** 普通对象：排除数组与 null，审批参数和工具参数只接受键值对。 */
export function plainRecord(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : undefined;
}

/** 字符串字段只接受字符串；对象、数组、数字一律退化为缺省。 */
export function itemText(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

/**
 * 回合标识只接受非空字符串。
 *
 * 事件归属过滤、分支入口与用量分组都按这个标识做相等比较：对象等畸形值进来后，
 * 正常字符串事件会被判定成其它回合并被静默丢弃，分支入口还会把对象发给内核。
 */
export function turnIdOf(value: unknown): string | undefined {
  return typeof value === "string" && value ? value : undefined;
}

/** 工具名必须是非空字符串，否则卡片标题回退到占位名。 */
export function itemToolName(value: unknown): string {
  return typeof value === "string" && value ? value : "tool";
}

/** 校验事件或条目里的工具状态；未知值按缺失处理，不把内核新增状态当成已知。 */
export function toolStatus(value: unknown): ThreadItem["status"] {
  return typeof value === "string" && TOOL_STATUSES.has(value as NonNullable<ThreadItem["status"]>)
    ? value as NonNullable<ThreadItem["status"]> : undefined;
}

export function toolExecutionState(value: unknown): ThreadItem["executionState"] {
  return typeof value === "string" && TOOL_EXECUTION_STATES.has(value as NonNullable<ThreadItem["executionState"]>)
    ? value as NonNullable<ThreadItem["executionState"]> : undefined;
}

export function approvalDecision(value: unknown): NonNullable<ApprovalState["decision"]> | undefined {
  return typeof value === "string" && APPROVAL_DECISIONS.has(value as NonNullable<ApprovalState["decision"]>)
    ? value as NonNullable<ApprovalState["decision"]> : undefined;
}

/**
 * 审批是否必须逐次确认。
 *
 * 「本次会话记住选择」与自动批准都按这个标记放行：只有内核明确给出布尔 `false`
 * 才算可记住；缺省、`null`、数字或字符串等畸形值一律按必须逐次确认处理。
 * 实时卡片、恢复后的卡片、记住写入与自动批准共用这一判定：字段缺失不能把
 * 对外操作显示成可记住，也不能让自动批准代替用户确认。
 */
export function approvalConsequential(value: unknown): boolean {
  return value !== false;
}

/** 来源标记三字段都必须是字符串；缺一项就整体丢弃，不显示半截来源。 */
export function itemSource(value: unknown): ThreadItem["source"] {
  const source = plainRecord(value);
  if (!source) return undefined;
  const ref = itemText(source.ref);
  const tool = itemText(source.tool);
  const queriedAt = itemText(source.queriedAt);
  return ref !== undefined && tool !== undefined && queriedAt !== undefined
    ? { ref, tool, queriedAt } : undefined;
}

function wholeCount(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0;
}

/** 分段结果引用：字段完整才交给 ChunkedResult，避免 undefined 参与数字格式化。 */
export function itemResultRef(value: unknown): ThreadItem["resultRef"] {
  const reference = plainRecord(value);
  if (!reference) return undefined;
  const { threadId, itemId, sha256, encoding, byteLength, characterLength } = reference;
  if (typeof threadId !== "string" || typeof itemId !== "string" || encoding !== "json"
    || typeof sha256 !== "string" || !wholeCount(byteLength) || !wholeCount(characterLength)) return undefined;
  return { threadId, itemId, encoding: "json", sha256, byteLength, characterLength };
}

/** 上下文编辑标记：entryId 与 excluded 都合法才保留。 */
export function itemContextEdit(value: unknown): ThreadItem["contextEdit"] {
  const edit = plainRecord(value);
  if (!edit) return undefined;
  const entryId = itemText(edit.entryId);
  return entryId !== undefined && typeof edit.excluded === "boolean"
    ? { entryId, excluded: edit.excluded } : undefined;
}
