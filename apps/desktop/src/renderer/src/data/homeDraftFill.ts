import type { ComposerDraft } from "./composerDraft";

/**
 * 工作区页把模板或技能带回首页草稿前的判断。
 *
 * 首页建议卡早已在「已有未发送正文」时先确认再覆盖；工作区的模板入口此前直接
 * `newTask()` 重置草稿，会把正文、附件与已选技能一起静默清空。这里把同一约定
 * 抽成纯函数：正文、附件、技能、正在读取附件与提交中都算「有未发送内容」，
 * 只有真正空白的草稿才允许直接写入模板。
 */
export function homeDraftHasContent(draft: ComposerDraft): boolean {
  return Boolean(draft.text.trim()) || draft.attachments.length > 0 || (draft.skillIds ?? []).length > 0
    || draft.pendingReads > 0 || draft.submitting;
}

/**
 * 模板入口的填充策略：草稿为空时直接应用；否则必须先确认。
 * 草稿内容本来就是该模板时无需再确认，与首页建议卡一致。
 */
export function templateFillIntent(draft: ComposerDraft, template: string): "apply" | "confirm" {
  if (!homeDraftHasContent(draft)) return "apply";
  const sameText = draft.text.trim() === template.trim();
  if (sameText && draft.attachments.length === 0 && (draft.skillIds ?? []).length === 0) return "apply";
  return "confirm";
}

/**
 * 技能入口只把技能并入已选列表，保留正文与附件，并沿用原草稿。
 * 已选或已达 10 项上限时原样返回，由输入区继续显示原有提示。
 */
export function withHomeDraftSkill(draft: ComposerDraft, skillId: string): ComposerDraft {
  const current = draft.skillIds ?? [];
  if (current.includes(skillId) || current.length >= 10) return draft;
  return { ...draft, skillIds: [...current, skillId] };
}
