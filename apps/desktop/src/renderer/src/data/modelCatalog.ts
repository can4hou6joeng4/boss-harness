import type { ModelCapabilities, ModelDescriptor } from "@boss-harness/protocol";

const ID_LIMIT = 200;
const PROVIDER_LIMIT = 100;
const SOURCE_LIMIT = 100;
const MAX_EFFORTS = 16;

function text(value: unknown, limit: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= limit;
}

function capabilitiesOf(value: unknown): ModelCapabilities | null | undefined {
  if (value === undefined || value === null) return null;
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  if (!Number.isSafeInteger(raw.contextWindow) || (raw.contextWindow as number) < 0) return undefined;
  if (!Number.isSafeInteger(raw.maxOutputTokens) || (raw.maxOutputTokens as number) < 0) return undefined;
  if (!text(raw.capabilitySource, SOURCE_LIMIT)) return undefined;
  if (typeof raw.capacityIsEstimate !== "boolean") return undefined;
  let reasoningEfforts: string[] | undefined;
  if (raw.reasoningEfforts !== undefined) {
    if (!Array.isArray(raw.reasoningEfforts) || raw.reasoningEfforts.length > MAX_EFFORTS
      || !raw.reasoningEfforts.every(effort => text(effort, ID_LIMIT))) return undefined;
    reasoningEfforts = [...raw.reasoningEfforts];
  }
  return { contextWindow: raw.contextWindow as number, maxOutputTokens: raw.maxOutputTokens as number,
    capabilitySource: raw.capabilitySource, capacityIsEstimate: raw.capacityIsEstimate,
    ...(reasoningEfforts ? { reasoningEfforts } : {}) };
}

/**
 * `model/list` 的线路条目校验。
 *
 * 输入区模型菜单直接读取 `configured` / `available` 过滤，并用 `provider`、`id`
 * 渲染与提交选择；`null` 条目会让过滤在渲染期抛错，缺 id 或重复 `provider:id` 让
 * 菜单 key 冲突、选择目标为空。`capabilities` 供设置页与驾驶舱展示上下文窗口，
 * 出现时必须是完整对象。
 */
export function modelDescriptorOf(value: unknown): ModelDescriptor | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (!text(raw.id, ID_LIMIT) || !text(raw.provider, PROVIDER_LIMIT)) return null;
  if (typeof raw.configured !== "boolean" || typeof raw.available !== "boolean") return null;
  const capabilities = capabilitiesOf(raw.capabilities);
  if (capabilities === undefined) return null;
  return {
    id: raw.id,
    provider: raw.provider,
    configured: raw.configured,
    available: raw.available,
    ...(capabilities ? { capabilities } : {}),
  };
}

/** 同一列表内的重复 `provider:id` 会让菜单项共用 key，选择目标无法区分。 */
export function uniqueModelKeys(items: { provider: string; id: string }[]): boolean {
  return new Set(items.map(item => `${item.provider}:${item.id}`)).size === items.length;
}

/** 进程以显式 none 启动时的说明；模型菜单与连接设置共用同一句，处理办法是换启动方式而不是补配置。 */
export const MODEL_CALLS_DISABLED_NOTE = "进程以 none 线路启动，不调用模型；需要模型时改用具体 provider 重新启动";

const NO_MODEL_MATCH = "未找到匹配模型";
const NO_MODEL_ROUTE = "没有可用的本机模型线路";

/**
 * 模型菜单的空态文案与进程级禁用附注。
 *
 * 显式 none 下 `model/list` 仍返回可选的 `none · none`，菜单并不为空：禁用说明要作为附注显示在
 * 选项之后，只放在空态里用户看不到。目录为空（尚未读到或读取失败）时同一句说明顶替「没有可用的
 * 本机模型线路」，不重复显示两遍。预览模式的选项是内置示例，与进程线路无关，不显示说明。
 */
export function modelMenuHints(input: { preview: boolean; modelCount: number; matchCount: number; modelCallsDisabled: boolean }): { empty: string; note: string } {
  const disabled = !input.preview && input.modelCallsDisabled;
  if (input.matchCount > 0) return { empty: "", note: disabled ? MODEL_CALLS_DISABLED_NOTE : "" };
  if (input.preview || input.modelCount > 0) return { empty: NO_MODEL_MATCH, note: disabled ? MODEL_CALLS_DISABLED_NOTE : "" };
  return { empty: disabled ? MODEL_CALLS_DISABLED_NOTE : NO_MODEL_ROUTE, note: "" };
}
