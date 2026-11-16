import type { QueueItem, TurnListResponse, TurnSummary } from "@boss-harness/protocol";

const SKILL_LIMIT = 10;
const ID_LIMIT = 200;
const MAX_CURSOR_LENGTH = 2048;
/** 与内核 session.py 的 _IDENTIFIER 一致：字母数字开头，最长 128。 */
const TURN_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
/** 回合列表分页上限：技能标签只是辅助信息，异常内核不能让它无限翻页。 */
export const TURN_SKILL_PAGE_LIMIT = 20;

/**
 * 映射对象不继承 Object.prototype：回合 id 来自响应，`__proto__` 等键
 * 在普通对象上会改写原型而不是成为条目。
 */
function skillMap(): Record<string, string[]> {
  return Object.create(null) as Record<string, string[]>;
}

/** 回合 id 必须符合内核标识符规则；不符的回合不产生映射，也不会成为对象键。 */
function turnIdOf(value: unknown): string | null {
  return typeof value === "string" && TURN_ID.test(value) ? value : null;
}

/** 先校验、后计数：跳过空值、非字符串与超长 id，去重并限 10 项。 */
function normalizeSkillIds(value: unknown): string[] {
  const ids: string[] = [];
  if (!Array.isArray(value)) return ids;
  for (const id of value) {
    if (ids.length >= SKILL_LIMIT) break;
    if (typeof id === "string" && id.length > 0 && id.length <= ID_LIMIT && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

/**
 * 从回合摘要提取「本次注入的技能」映射。
 * 旧内核或畸形记录不产生伪技能，也不会挤掉后面的合法 id。
 */
export function collectTurnSkillIds(turns: TurnSummary[] | null | undefined): Record<string, string[]> {
  const result = skillMap();
  if (!Array.isArray(turns)) return result;
  for (const turn of turns) {
    const turnId = turnIdOf(turn?.turnId);
    if (!turnId) continue;
    const ids = normalizeSkillIds(turn.skillIds);
    if (ids.length) result[turnId] = ids;
  }
  return result;
}

/**
 * 从队列页提取可以直接信任的「已投递回合技能」。
 * 去重回执（deduplicated）关联的是已有请求，队列项记录的是本次请求携带的技能，
 * 未必等于该回合实际注入的技能；与直接发送路径一致，交给回合列表核对，不写入标签。
 */
export function deliveredTurnSkills(items: readonly QueueItem[] | null | undefined): Record<string, string[]> {
  const result = skillMap();
  if (!Array.isArray(items)) return result;
  for (const item of items) {
    if (!item || item.status !== "delivered" || item.deduplicated === true) continue;
    const turnId = turnIdOf(item.turnId);
    if (!turnId) continue;
    const ids = normalizeSkillIds(item.skillIds);
    if (ids.length) result[turnId] = ids;
  }
  return result;
}

/**
 * 校验一页 `thread/turns/list` 响应并提取技能映射。
 * `turns` 不是数组或游标形状不符时返回 null，交由调用方按读取失败处理；
 * 回合内容沿用 `collectTurnSkillIds` 的逐项过滤。
 */
export function turnSkillPageOf(response: TurnListResponse | null | undefined):
  { skills: Record<string, string[]>; nextCursor: string | null } | null {
  if (!response || !Array.isArray(response.turns)) return null;
  const next = response.nextCursor ?? null;
  if (next !== null && (typeof next !== "string" || !next || next.length > MAX_CURSOR_LENGTH)) return null;
  return { skills: collectTurnSkillIds(response.turns), nextCursor: next };
}

/**
 * 查询某回合注入的技能。
 *
 * `turnSkillIds` 由普通对象承接并按 id 合并；直接下标查询在未命中的 `turnId`
 * 恰好等于 `constructor`、`hasOwnProperty` 等原型成员时会取到函数，而不是
 * `undefined`。会话区随后把该值当技能数组调用 `.map`，会让整段消息渲染崩溃。
 * 这里只认映射自己的条目，缺失或形状不符一律返回空数组。
 */
export function turnSkillIdsFor(
  mapping: Readonly<Record<string, readonly string[]>> | null | undefined,
  turnId: string | null | undefined,
): readonly string[] {
  if (!mapping || typeof turnId !== "string"
    || !Object.prototype.hasOwnProperty.call(mapping, turnId)) return [];
  const ids = mapping[turnId];
  return Array.isArray(ids) ? ids : [];
}
