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
