import { codePointLength } from "@boss-harness/shared";

/**
 * 「后续模型上下文」对话框的提交闸门。
 *
 * 读取或提交后回读失败时，界面会保留上一次成功读取的快照；该快照可能已经过期，
 * 在重新读取成功前不能再基于它提交编辑。
 */
export interface ContextEditGate {
  loading: boolean;
  saving: boolean;
  stale: boolean;
}

export function contextEditSubmitBlocked(gate: ContextEditGate): boolean {
  return gate.loading || gate.saving || gate.stale;
}

/**
 * 替换文本上限：按 Unicode 码点计数，与主进程 `context/edit` 的安全校验及使用指南
 * 的「最多 32000 字符」一致。界面不能直接用 HTML `maxLength`，它按 UTF-16 码元计数。
 */
export const CONTEXT_EDIT_MAX_TEXT_LENGTH = 32_000;

/** 替换文本是否超过上限；`null` 表示排除消息，不受正文上限约束。 */
export function contextEditTextTooLong(text: string | null): boolean {
  return text !== null && codePointLength(text) > CONTEXT_EDIT_MAX_TEXT_LENGTH;
}

/** 旧快照提示；与提交闸门一起使用，明确说明界面展示的不是当前事实。 */
export const CONTEXT_EDIT_STALE_NOTICE = "下方是上次成功读取的上下文快照，可能已过期；重新读取成功前不会提交新的编辑。";
