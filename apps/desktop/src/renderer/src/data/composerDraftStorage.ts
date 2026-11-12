/**
 * 未发送草稿的本地持久化。
 *
 * 只保存正文、技能 id 与历史调取期间进入前的正文：附件原文按既有边界只留在内存，
 * 提交流程状态（submitting / queueSubmission）也不落盘。存储键沿用 UI 命名空间，
 * 旧 `boss-cli.ui.*` 由启动迁移补齐。
 */
import { MAX_MESSAGE_TEXT_LENGTH, createComposerDraft, type ComposerDraft } from "./composerDraft";
import { UI_STORAGE_PREFIX } from "./uiStorage";

export const COMPOSER_DRAFT_STORAGE_KEY = UI_STORAGE_PREFIX + "composerDrafts";
/** 超过内核单条消息上限的草稿不持久化，避免重启后恢复成无法发送的内容。 */
export const MAX_DRAFT_TEXT_LENGTH = MAX_MESSAGE_TEXT_LENGTH;
/** 最多保留的会话草稿数量；超出时丢弃最久未修改的条目。 */
export const MAX_SESSION_DRAFTS = 20;
const MAX_SKILL_IDS = 50;
/** 项目 id 的上限；本地分组 id 形如 `group-` + UUID，留足余量但拒绝异常超长值。 */
const MAX_PROJECT_ID_LENGTH = 200;
const STORE_VERSION = 1;

export interface PersistedComposerDraft {
  text: string;
  skillIds: string[];
  updatedAt: number;
  /** 仅首页条目保存：当时选中的招聘项目 id；会话草稿忽略该字段。 */
  projectId?: string;
  /**
   * 历史调取期间进入前的正文。调取只把原稿留在组件内，重启恢复时优先使用该字段，
   * 避免被调取的历史消息覆盖尚未发送的原稿。
   */
  recallDraft?: string;
}

export interface PersistedComposerDraftStore {
  home?: PersistedComposerDraft;
  sessions: Record<string, PersistedComposerDraft>;
}

/** 只需要本地存储的读取、写入与删除；不可用时传 null，草稿退回内存态。 */
export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): DraftStorage | null {
  try { return localStorage; } catch { return null; }
}

/** 校验单个条目；空正文且无技能、类型错误或超限都视为没有草稿。 */
function draftEntry(value: unknown): PersistedComposerDraft | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as { text?: unknown; skillIds?: unknown; updatedAt?: unknown; projectId?: unknown; recallDraft?: unknown };
  if (typeof record.text !== "string" || record.text.length > MAX_DRAFT_TEXT_LENGTH) return null;
  const skillIds = Array.isArray(record.skillIds)
    ? [...new Set(record.skillIds.filter((id): id is string => typeof id === "string" && id.trim().length > 0))].slice(0, MAX_SKILL_IDS)
    : [];
  // 旧版本条目没有调取字段；非法类型或超长值忽略，按普通正文恢复，不影响已有草稿。
  const recallDraft = typeof record.recallDraft === "string" && record.recallDraft.length <= MAX_DRAFT_TEXT_LENGTH
    ? record.recallDraft : undefined;
  if (!record.text.trim() && skillIds.length === 0) return null;
  const updatedAt = typeof record.updatedAt === "number" && Number.isFinite(record.updatedAt) && record.updatedAt >= 0
    ? record.updatedAt
    : 0;
  // 旧版本条目没有项目字段，按「不指定项目」恢复；非法类型同样忽略，不影响正文与技能。
  const projectId = typeof record.projectId === "string" && record.projectId.trim() === record.projectId
    && record.projectId.trim().length > 0 && record.projectId.length <= MAX_PROJECT_ID_LENGTH
    ? record.projectId : undefined;
  return { text: record.text, skillIds, updatedAt, ...(projectId ? { projectId } : {}), ...(recallDraft !== undefined ? { recallDraft } : {}) };
}

/** 按最近修改保留有限条目；同时间戳按会话 id 排序，保证结果稳定。 */
function prune(store: PersistedComposerDraftStore): PersistedComposerDraftStore {
  const sessions = Object.entries(store.sessions)
    .sort(([idA, a], [idB, b]) => b.updatedAt - a.updatedAt || idA.localeCompare(idB))
    .slice(0, MAX_SESSION_DRAFTS);
  return { ...(store.home ? { home: store.home } : {}), sessions: Object.fromEntries(sessions) };
}

/** 解析已写入的草稿库；版本不符、结构错误或空值一律视为没有草稿。 */
export function parseComposerDraftStore(value: unknown): PersistedComposerDraftStore {
  const empty: PersistedComposerDraftStore = { sessions: {} };
  if (!value || typeof value !== "object" || Array.isArray(value)) return empty;
  const record = value as { version?: unknown; home?: unknown; sessions?: unknown };
  if (record.version !== STORE_VERSION) return empty;
  const sessions: Record<string, PersistedComposerDraft> = {};
  if (record.sessions && typeof record.sessions === "object" && !Array.isArray(record.sessions)) {
    for (const [id, raw] of Object.entries(record.sessions)) {
      if (!id.trim()) continue;
      const entry = draftEntry(raw);
      if (entry) sessions[id] = entry;
    }
  }
  return prune({ home: draftEntry(record.home) ?? undefined, sessions });
}

export function loadComposerDraftStore(storage: DraftStorage | null = defaultStorage()): PersistedComposerDraftStore {
  const empty: PersistedComposerDraftStore = { sessions: {} };
  if (!storage) return empty;
  try {
    const raw = storage.getItem(COMPOSER_DRAFT_STORAGE_KEY);
    return raw === null ? empty : parseComposerDraftStore(JSON.parse(raw));
  } catch { return empty; }
}

/** 只取可持久化字段；附件、提交中与队列待核对状态都不进入本地存储。 */
function collectDraft(draft: ComposerDraft | undefined): { text: string; skillIds: string[]; recallDraft?: string } | null {
  if (!draft) return null;
  if (draft.text.length > MAX_DRAFT_TEXT_LENGTH) return null;
  const skillIds = [...new Set((draft.skillIds ?? []).filter(id => typeof id === "string" && id.trim().length > 0))].slice(0, MAX_SKILL_IDS);
  if (!draft.text.trim() && skillIds.length === 0) return null;
  // 原稿超过存储上限时与普通超长草稿一致：不持久化，但保留当前被调取的正文。
  const recallDraft = draft.recallDraft !== undefined && draft.recallDraft.length <= MAX_DRAFT_TEXT_LENGTH ? draft.recallDraft : undefined;
  return { text: draft.text, skillIds, ...(recallDraft !== undefined ? { recallDraft } : {}) };
}

function sameDraft(a: { text: string; skillIds: string[]; recallDraft?: string } | null, b: PersistedComposerDraft | undefined): boolean {
  return Boolean(a && b && a.text === b.text && a.skillIds.length === b.skillIds.length
    && a.skillIds.every((id, index) => id === b.skillIds[index]) && a.recallDraft === b.recallDraft);
}

/**
 * 保存首页与各会话草稿。内容未变的条目标记沿用原时间戳，避免别的会话的修改
 * 把未改动的草稿顶到前面；全空时删除存储键。存储不可用或超限时静默跳过，
 * 输入本身不受影响。`homeProjectId` 只随首页条目保存，供重启后恢复项目选择。
 */
export function saveComposerDrafts(
  home: ComposerDraft,
  sessions: Record<string, ComposerDraft>,
  storage: DraftStorage | null = defaultStorage(),
  now = Date.now(),
  homeProjectId = "",
): void {
  if (!storage) return;
  try {
    const previous = loadComposerDraftStore(storage);
    const next: PersistedComposerDraftStore = { sessions: {} };
    const add = (id: string | null, draft: ComposerDraft | undefined, previousEntry: PersistedComposerDraft | undefined) => {
      const current = collectDraft(draft);
      // 只有项目没有正文与技能的草稿不需要单独保存，避免为一次项目点选写入空草稿。
      if (!current) return;
      const unchanged = sameDraft(current, previousEntry)
        && (id !== null || (previousEntry?.projectId ?? "") === (homeProjectId || ""));
      const entry: PersistedComposerDraft = { ...current, updatedAt: unchanged ? previousEntry!.updatedAt : now };
      if (id === null && homeProjectId) entry.projectId = homeProjectId;
      if (id === null) next.home = entry;
      else next.sessions[id] = entry;
    };
    add(null, home, previous.home);
    for (const [id, draft] of Object.entries(sessions)) {
      if (!id.trim()) continue;
      add(id, draft, previous.sessions[id]);
    }
    const pruned = prune(next);
    if (!pruned.home && Object.keys(pruned.sessions).length === 0) {
      storage.removeItem(COMPOSER_DRAFT_STORAGE_KEY);
      return;
    }
    storage.setItem(COMPOSER_DRAFT_STORAGE_KEY, JSON.stringify({ version: STORE_VERSION, ...pruned }));
  } catch {
    // 存储被禁用或配额已满：草稿仍保留在内存中，不阻断输入与发送。
  }
}

/**
 * 恢复为可编辑草稿；每次恢复使用新的内部 id，避免与发送中的旧草稿串线。
 * 调取期间退出时保存的是「被调取正文 + 进入前的原稿」，恢复只取原稿，调取状态本身不跨重启。
 */
export function restoreComposerDraft(entry?: PersistedComposerDraft): ComposerDraft {
  const draft = createComposerDraft();
  return entry ? { ...draft, text: entry.recallDraft ?? entry.text, skillIds: entry.skillIds } : draft;
}

export function restoreSessionDrafts(store: PersistedComposerDraftStore): Record<string, ComposerDraft> {
  return Object.fromEntries(Object.entries(store.sessions).map(([id, entry]) => [id, restoreComposerDraft(entry)]));
}
