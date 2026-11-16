import type { SkillDescriptor } from "@boss-harness/protocol";

const ID_LIMIT = 200;
const NAME_LIMIT = 200;
const DESCRIPTION_LIMIT = 2000;
const DIGEST_LIMIT = 128;

/**
 * `skills/list` 的技能条目校验。
 *
 * 技能页直接读取 `id`、`name`、`description` 做筛选与渲染，用 `id` 记录选中项、
 * 用 `digest` 作为读取、写入与删除的并发校验。`null` 条目会让筛选在读取属性时抛错；
 * 缺 `id` 或重复 `id` 会让选中与摘要指向错误条目。同一响应里的 `problems` 已经
 * 逐项校验，技能条目也必须同等对待。
 */
export function skillDescriptorOf(value: unknown): SkillDescriptor | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.id !== "string" || raw.id.length === 0 || raw.id.length > ID_LIMIT) return null;
  if (typeof raw.name !== "string" || raw.name.length > NAME_LIMIT) return null;
  if (typeof raw.description !== "string" || raw.description.length > DESCRIPTION_LIMIT) return null;
  if (typeof raw.digest !== "string" || raw.digest.length === 0 || raw.digest.length > DIGEST_LIMIT) return null;
  if (!Number.isSafeInteger(raw.bytes) || (raw.bytes as number) < 0) return null;
  if (raw.nameTruncated !== undefined && typeof raw.nameTruncated !== "boolean") return null;
  if (raw.descriptionTruncated !== undefined && typeof raw.descriptionTruncated !== "boolean") return null;
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description,
    digest: raw.digest,
    bytes: raw.bytes as number,
    ...(raw.nameTruncated === true ? { nameTruncated: true } : {}),
    ...(raw.descriptionTruncated === true ? { descriptionTruncated: true } : {}),
  };
}

/** 同一目录内的重复 id 会让选中项与摘要校验指向第一个条目。 */
export function uniqueSkillIds(items: { id: string }[]): boolean {
  return new Set(items.map(item => item.id)).size === items.length;
}
