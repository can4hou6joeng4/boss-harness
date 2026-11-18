import type {
  AutoCompactionSource,
  ConfigReadResponse,
  RuntimeResourceOwner,
  RuntimeResourceWaiter,
  RuntimeResourcesReadResponse,
} from "@boss-harness/protocol";
import { safeSlice } from "@boss-harness/shared";
import type { QueuePage } from "./queueMapping";
import { labeledValue } from "./taskCheck";

/** 驾驶舱只展示内核已声明或有持久记录的事实；字段缺失时保留为 undefined，由界面显示「未提供」。 */
export interface CockpitConfig {
  protocolVersion?: string;
  provider?: string;
  model?: string;
  /** 进程以显式 none 启动；旧内核或自动回退不返回该字段。 */
  modelCallsDisabled?: boolean;
  maxOutputTokens?: number;
  parallelThreads?: number;
  maxRetainedTurns?: number;
  maxModelRequests?: number;
  steeringMode?: string;
  maxAttachmentStorageBytes?: number;
  maxAttachmentStorageObjects?: number;
  contextWindow?: number;
  modelMaxOutputTokens?: number;
  reasoningEfforts?: string[];
  capacityIsEstimate?: boolean;
  capabilitySource?: string;
  toolBundleId?: string;
  approvalPolicy?: string;
  approvalTimeoutSeconds?: number;
  autoCompaction?: {
    enabled?: boolean;
    triggerPercent?: number;
    keepRecentTokens?: number;
    provider?: string;
    model?: string;
    effort?: string | null;
  };
  autoCompactionSource?: AutoCompactionSource;
}

export interface CockpitTool {
  name: string;
  description: string;
  readOnly: boolean;
  requiresApproval: boolean;
  executionMode?: "sequential" | "parallel";
}

export interface CockpitModel {
  id: string;
  provider: string;
  configured: boolean;
  available: boolean;
  contextWindow?: number;
  maxOutputTokens?: number;
  reasoningEfforts?: string[];
  capacityIsEstimate?: boolean;
}

export interface CockpitQueue {
  active?: number;
  queued: number;
  delivering: number;
  paused: number;
  /** 分类计数来自内核持久统计，不受投影截断影响。 */
  countsExact?: boolean;
  truncated: boolean;
}

const MAX_TEXT = 400;
const REFRESH_METHODS = new Set([
  "turn/started",
  "turn/completed",
  "approval/requested",
  "approval/decided",
  "queue/updated",
  "context/compactionStarted",
  "context/compactionCompleted",
  "context/compactionFailed",
  "context/compacted",
]);

/** 只有会改变面板所展示快照的通知才触发自动刷新；未知方法或非字符串不猜。 */
export function shouldRefreshCockpit(method: unknown): boolean {
  return typeof method === "string" && REFRESH_METHODS.has(method);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function text(value: unknown, limit = MAX_TEXT): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= limit ? trimmed : undefined;
}

function integer(value: unknown, minimum = 0): number | undefined {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum ? value : undefined;
}

function finite(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : undefined;
}

function boolean(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function compactionSource(value: unknown): AutoCompactionSource | undefined {
  return value === "environment" || value === "stored" || value === "default" || value === "explicit" ? value : undefined;
}

function textList(value: unknown, limit = 32): string[] | undefined {
  if (!Array.isArray(value) || value.length > limit) return undefined;
  const items = value.filter((item): item is string => typeof item === "string" && item.length > 0 && item.length <= MAX_TEXT);
  return items.length === value.length ? items : undefined;
}

/** 读取 config/read 中驾驶舱会用到的字段；未知或非法字段直接省略，不用默认值冒充事实。 */
export function readCockpitConfig(value: unknown): CockpitConfig {
  if (!isObject(value)) throw new Error("内核配置响应无法识别");
  const response = value as ConfigReadResponse & Record<string, unknown>;
  const capabilities = isObject(response.modelCapabilities) ? response.modelCapabilities : undefined;
  const policy = isObject(response.autoCompaction) ? response.autoCompaction : undefined;
  const config: CockpitConfig = {
    ...(text(response.protocolVersion) ? { protocolVersion: text(response.protocolVersion) } : {}),
    ...(text(response.provider) ? { provider: text(response.provider) } : {}),
    ...(text(response.model) ? { model: text(response.model) } : {}),
    ...(integer(response.maxOutputTokens) !== undefined ? { maxOutputTokens: integer(response.maxOutputTokens) } : {}),
    ...(integer(response.parallelThreads) !== undefined ? { parallelThreads: integer(response.parallelThreads) } : {}),
    ...(integer(response.maxRetainedTurns) !== undefined ? { maxRetainedTurns: integer(response.maxRetainedTurns) } : {}),
    ...(integer(response.maxModelRequests) !== undefined ? { maxModelRequests: integer(response.maxModelRequests) } : {}),
    ...(text(response.steeringMode) ? { steeringMode: text(response.steeringMode) } : {}),
    ...(response.modelCallsDisabled === true ? { modelCallsDisabled: true } : {}),
    ...(integer(response.maxAttachmentStorageBytes) !== undefined ? { maxAttachmentStorageBytes: integer(response.maxAttachmentStorageBytes) } : {}),
    ...(integer(response.maxAttachmentStorageObjects) !== undefined ? { maxAttachmentStorageObjects: integer(response.maxAttachmentStorageObjects) } : {}),
    ...(text(response.toolBundleId) ? { toolBundleId: text(response.toolBundleId) } : {}),
    ...(text(response.approvalPolicy) ? { approvalPolicy: text(response.approvalPolicy) } : {}),
    ...(integer(response.approvalTimeoutSeconds) !== undefined ? { approvalTimeoutSeconds: integer(response.approvalTimeoutSeconds) } : {}),
    ...(compactionSource(response.autoCompactionSource) ? { autoCompactionSource: compactionSource(response.autoCompactionSource) } : {}),
  };
  if (capabilities) {
    const contextWindow = integer(capabilities.contextWindow, 1);
    const modelMaxOutputTokens = integer(capabilities.maxOutputTokens, 1);
    const reasoningEfforts = textList(capabilities.reasoningEfforts);
    const capacityIsEstimate = boolean(capabilities.capacityIsEstimate);
    const capabilitySource = text(capabilities.capabilitySource);
    if (contextWindow !== undefined) config.contextWindow = contextWindow;
    if (modelMaxOutputTokens !== undefined) config.modelMaxOutputTokens = modelMaxOutputTokens;
    if (reasoningEfforts) config.reasoningEfforts = reasoningEfforts;
    if (capacityIsEstimate !== undefined) config.capacityIsEstimate = capacityIsEstimate;
    if (capabilitySource) config.capabilitySource = capabilitySource;
  }
  if (policy) {
    const enabled = boolean(policy.enabled);
    const triggerPercent = integer(policy.triggerPercent, 1);
    const keepRecentTokens = integer(policy.keepRecentTokens, 1);
    const provider = text(policy.provider);
    const model = text(policy.model);
    const effort = policy.effort === null ? null : text(policy.effort);
    config.autoCompaction = {
      ...(enabled !== undefined ? { enabled } : {}),
      ...(triggerPercent !== undefined && triggerPercent <= 100 ? { triggerPercent } : {}),
      ...(keepRecentTokens !== undefined ? { keepRecentTokens } : {}),
      ...(provider ? { provider } : {}),
      ...(model ? { model } : {}),
      ...(effort !== undefined ? { effort } : {}),
    };
  }
  return config;
}

function readOwner(value: unknown): RuntimeResourceOwner | null {
  if (!isObject(value)) return null;
  const kind = value.kind;
  const state = value.state;
  if (kind !== "turn" && kind !== "manualCompaction" && kind !== "automaticCompaction") return null;
  if (state !== "active" && state !== "cleanup") return null;
  const id = text(value.id, 200);
  const threadId = text(value.threadId, 200);
  const ageSeconds = finite(value.ageSeconds);
  const cancelRequested = boolean(value.cancelRequested);
  const abortPending = boolean(value.abortPending);
  if (!id || !threadId || ageSeconds === undefined || cancelRequested === undefined || abortPending === undefined) return null;
  return {
    kind, id, threadId, state, ageSeconds, cancelRequested, abortPending,
    phase: text(value.phase, 100) ?? null,
    phaseStatus: text(value.phaseStatus, 100) ?? null,
  };
}

function readWaiter(value: unknown): RuntimeResourceWaiter | null {
  if (!isObject(value)) return null;
  const threadId = text(value.threadId, 200);
  const position = integer(value.position, 1);
  const waitingSeconds = finite(value.waitingSeconds);
  if (!threadId || position === undefined || waitingSeconds === undefined) return null;
  return { threadId, position, waitingSeconds };
}

/** 严格校验资源快照；任一 owner / waiter 形状不符时整体报错，不展示半份运行状态。 */
export function readCockpitResources(value: unknown): RuntimeResourcesReadResponse {
  if (!isObject(value) || !Array.isArray(value.owners) || !Array.isArray(value.waiters)) {
    throw new Error("内核运行资源响应无法识别");
  }
  const required = (key: string): number => {
    const parsed = integer(value[key]);
    if (parsed === undefined) throw new Error("内核运行资源响应缺少有效计数字段");
    return parsed;
  };
  const turnCapacity = required("turnCapacity");
  const activeTurnCount = required("activeTurnCount");
  const maxRetainedTurns = required("maxRetainedTurns");
  const retainedTurnCount = required("retainedTurnCount");
  const ownerCount = required("ownerCount");
  const waiterCount = required("waiterCount");
  const owners = value.owners.map(readOwner);
  const waiters = value.waiters.map(readWaiter);
  if (owners.some(owner => owner === null) || waiters.some(waiter => waiter === null)) {
    throw new Error("内核运行资源条目格式无法识别");
  }
  // 计数必须覆盖已返回的明细；小于明细数是自相矛盾的快照，整体拒绝。
  if (ownerCount < owners.length || waiterCount < waiters.length) {
    throw new Error("内核运行资源计数与明细不一致");
  }
  // 并发回合不能超过并发容量，保留回合不能超过保留上限，每个保留回合都必须出现在 owner 列表中。
  // 违反任一项的快照会渲染出「5 / 2」这类不可能的分式或掩盖 owner 记录缺口，整体拒绝。
  if (activeTurnCount > turnCapacity) {
    throw new Error("内核运行资源计数超过并发容量");
  }
  if (retainedTurnCount > maxRetainedTurns) {
    throw new Error("内核运行资源计数超过保留上限");
  }
  if (ownerCount < retainedTurnCount) {
    throw new Error("内核运行资源计数未覆盖保留回合");
  }
  const ownersTruncated = boolean(value.ownersTruncated);
  const waitersTruncated = boolean(value.waitersTruncated);
  if (ownersTruncated === undefined || waitersTruncated === undefined) {
    throw new Error("内核运行资源响应缺少截断标记");
  }
  // 与队列投影同一口径：计数大于已载入规模时投影必然不完整，标记缺失或误报
  // false 都不能让面板把明细当成全部；标记为真时保持原值。
  const ownersIncomplete = ownersTruncated || ownerCount > owners.length;
  const waitersIncomplete = waitersTruncated || waiterCount > waiters.length;
  return {
    turnCapacity,
    activeTurnCount,
    maxRetainedTurns,
    retainedTurnCount,
    ownerCount,
    owners: owners as RuntimeResourceOwner[],
    ownersTruncated: ownersIncomplete,
    waiterCount,
    waiters: waiters as RuntimeResourceWaiter[],
    waitersTruncated: waitersIncomplete,
  };
}

/** 工具清单逐项校验；非法条目丢弃并保留其余可展示项。 */
export function readCockpitTools(values: unknown): CockpitTool[] {
  if (!Array.isArray(values)) throw new Error("内核工具清单无法识别");
  return values.flatMap(value => {
    if (!isObject(value)) return [];
    const name = text(value.name, 200);
    // 描述超长时截断并标记省略，避免把半句话当成完整规则；预算内原样保留。
    const rawDescription = typeof value.description === "string" ? value.description : "";
    const description = rawDescription.length > 600 ? `${safeSlice(rawDescription, 600)}…` : rawDescription;
    const readOnly = boolean(value.readOnly);
    const requiresApproval = boolean(value.requiresApproval);
    const executionMode = value.executionMode === "sequential" || value.executionMode === "parallel" ? value.executionMode : undefined;
    if (!name || readOnly === undefined || requiresApproval === undefined) return [];
    return [{ name, description, readOnly, requiresApproval, ...(executionMode ? { executionMode } : {}) }];
  });
}

/** 模型目录逐项校验；非法条目丢弃，不在界面展示无法核对的线路。 */
export function readCockpitModels(values: unknown): CockpitModel[] {
  if (!Array.isArray(values)) throw new Error("内核模型目录无法识别");
  return values.flatMap(value => {
    if (!isObject(value)) return [];
    const id = text(value.id, 300);
    const provider = text(value.provider, 100);
    const configured = boolean(value.configured);
    const available = boolean(value.available);
    if (!id || !provider || configured === undefined || available === undefined) return [];
    const capabilities = isObject(value.capabilities) ? value.capabilities : undefined;
    const contextWindow = capabilities ? integer(capabilities.contextWindow, 1) : undefined;
    const maxOutputTokens = capabilities ? integer(capabilities.maxOutputTokens, 1) : undefined;
    const reasoningEfforts = capabilities ? textList(capabilities.reasoningEfforts) : undefined;
    const capacityIsEstimate = capabilities ? boolean(capabilities.capacityIsEstimate) : undefined;
    return [{
      id, provider, configured, available,
      ...(contextWindow !== undefined ? { contextWindow } : {}),
      ...(maxOutputTokens !== undefined ? { maxOutputTokens } : {}),
      ...(reasoningEfforts ? { reasoningEfforts } : {}),
      ...(capacityIsEstimate !== undefined ? { capacityIsEstimate } : {}),
    }];
  });
}

/**
 * 队列投影统计：分类优先使用内核按全部持久项统计的 `counts`，与队列面板、侧栏徽标一致；
 * 旧内核缺省分类或其合计与待处理总数不一致时，才退回按本次有界返回的可见项统计。
 */
export function readCockpitQueue(page: QueuePage | null): CockpitQueue | null {
  if (!page) return null;
  const visible = { queued: 0, delivering: 0, paused: 0 };
  for (const item of page.items) {
    if (item.status === "queued") visible.queued += 1;
    else if (item.status === "delivering") visible.delivering += 1;
    else if (item.status === "paused") visible.paused += 1;
  }
  const total = page.totalItems ?? page.items.length;
  const active = page.activeItems;
  const persistent = page.counts && active !== undefined
    && page.counts.queued + page.counts.delivering + page.counts.paused === active ? page.counts : undefined;
  const counts = persistent ?? visible;
  return {
    ...(active !== undefined ? { active } : {}),
    ...counts,
    ...(persistent ? { countsExact: true } : {}),
    truncated: page.truncated === true || page.items.length < total,
  };
}

/** 秒数转可读运行时长；只用于展示，不参与任何超时判断。 */
export function durationText(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "未知";
  // 先取整秒再分支：浮点尾数不能让「2 分」抖动成「2 分 0 秒」。
  const whole = Math.floor(seconds);
  if (whole < 1) return "不足 1 秒";
  if (whole < 60) return `${whole} 秒`;
  const minutes = Math.floor(whole / 60);
  if (minutes < 60) return whole % 60 === 0 ? `${minutes} 分` : `${minutes} 分 ${whole % 60} 秒`;
  const hours = Math.floor(minutes / 60);
  return minutes % 60 === 0 ? `${hours} 小时` : `${hours} 小时 ${minutes % 60} 分`;
}

export function ownerKindLabel(kind: RuntimeResourceOwner["kind"]): string {
  switch (kind) {
    case "turn": return "业务回合";
    case "manualCompaction": return "手动摘要";
    case "automaticCompaction": return "自动摘要";
  }
}

export function ownerStateLabel(state: RuntimeResourceOwner["state"]): string {
  return state === "active" ? "运行中" : "收尾中";
}

/** 内核 config/read 的固定策略取值；未知取值原样标注，新内核新增策略时不会显示错标签。 */
const APPROVAL_POLICY_LABELS: Record<string, string> = {
  "each-consequential-call": "每次对外操作逐次批准",
};
const STEERING_MODE_LABELS: Record<string, string> = {
  all: "全部转向消息一次投递",
  "one-at-a-time": "转向消息逐条投递",
};
const CAPABILITY_SOURCE_LABELS: Record<string, string> = {
  configured: "显式容量配置",
  "legacy-default": "旧版默认容量",
};

export function approvalPolicyLabel(policy: string): string {
  return labeledValue(APPROVAL_POLICY_LABELS, policy);
}

export function steeringModeLabel(mode: string): string {
  return labeledValue(STEERING_MODE_LABELS, mode);
}

export function capabilitySourceLabel(source: string): string {
  return labeledValue(CAPABILITY_SOURCE_LABELS, source);
}

/** 短标识：保留前 8 位，避免在窄卡片里撑破布局。 */
export function shortId(value: string): string {
  return value.length <= 12 ? value : `${value.slice(0, 8)}…`;
}

export function compactionSummary(config: CockpitConfig): string {
  const policy = config.autoCompaction;
  if (!policy || policy.enabled === undefined) return "未提供";
  if (!policy.enabled) return "已关闭";
  const trigger = policy.triggerPercent === undefined ? "阈值未提供" : `${policy.triggerPercent}% 触发`;
  const keep = policy.keepRecentTokens === undefined ? "保留目标未提供" : `保留 ${policy.keepRecentTokens} token`;
  const route = [policy.provider, policy.model].filter(Boolean).join(" / ");
  return [trigger, keep, route ? `摘要线路 ${route}${policy.effort ? ` · ${policy.effort}` : ""}` : null]
    .filter(Boolean).join(" · ");
}

/** 当前会话的待处理队列摘要；没有会话时不展示该行。旧内核没有持久总数时明确标注为可见计数。 */
export function queueSummaryText(queue: CockpitQueue | null): string {
  if (!queue) return "未选择会话";
  const visible = queue.queued + queue.delivering + queue.paused;
  const active = queue.active !== undefined
    ? `待处理 ${queue.active} 项`
    : `可见待处理 ${visible} 项（旧内核未提供总数）`;
  // 只有分类确实来自可见项时才提示口径；持久分类已是全量事实，不需要降级说明。
  const visibleNote = queue.truncated && queue.countsExact !== true ? "（分类按可见项计数）" : "";
  return `${active} · 排队 ${queue.queued} / 投递中 ${queue.delivering} / 暂停 ${queue.paused}${visibleNote}`;
}
