import type { MessageItem } from "./mockData";

/**
 * 输入区的已发送消息历史。
 *
 * 只读取本会话渲染层已有的用户消息，不额外请求内核、不落盘：切换会话后输入区随
 * `ConversationArea` 一起重新挂载，历史自然跟随当前会话。附件展开后的正文可能远超
 * 可编辑范围，这类超长消息直接跳过，避免把输入区塞满。
 */
export const MAX_RECALL_PROMPTS = 50;
export const MAX_RECALL_CHARS = 20_000;

export interface PromptRecallState {
  /** 历史下标；-1 表示当前草稿。 */
  index: number;
  /** 进入历史前的草稿，回到 -1 时原样恢复。 */
  draft: string;
}

export interface PromptRecallResult {
  state: PromptRecallState;
  text: string;
}

type RecallMessage = Pick<MessageItem, "role" | "content">;

/** 可调取的用户输入：从旧到新，跳过空白与超长条目，最多保留最近 50 条。 */
export function recallablePrompts(messages: readonly RecallMessage[]): string[] {
  const prompts: string[] = [];
  for (let cursor = messages.length - 1; cursor >= 0 && prompts.length < MAX_RECALL_PROMPTS; cursor -= 1) {
    const message = messages[cursor];
    if (message?.role !== "user" || typeof message.content !== "string") continue;
    const text = message.content.trim();
    if (!text || text.length > MAX_RECALL_CHARS) continue;
    prompts.push(text);
  }
  return prompts.reverse();
}

/**
 * ↑：空闲时从草稿进入最新一条并记住草稿；在历史中向更早移动。
 * 已在最早一条时保持原样，让原生光标行为继续生效。
 */
export function recallOlder(prompts: readonly string[], state: PromptRecallState, value: string): PromptRecallResult {
  const count = prompts.length;
  if (!count) return { state, text: value };
  // 历史在下一次渲染前缩短（例如发送后清空）时，回到空闲草稿，不用旧下标猜内容。
  if (state.index >= count) return { state: { index: -1, draft: state.draft }, text: value };
  if (state.index === -1) return { state: { index: count - 1, draft: value }, text: prompts[count - 1] ?? value };
  if (state.index === 0) return { state, text: value };
  const index = state.index - 1;
  return { state: { index, draft: state.draft }, text: prompts[index] ?? value };
}

/** ↓：在历史中向更近移动；越过最新一条回到进入历史前的草稿。空闲时保持原样。 */
export function recallNewer(prompts: readonly string[], state: PromptRecallState, value: string): PromptRecallResult {
  const count = prompts.length;
  if (!count || state.index < 0) return { state, text: value };
  if (state.index >= count) return { state: { index: -1, draft: state.draft }, text: value };
  if (state.index === count - 1) return { state: { index: -1, draft: state.draft }, text: state.draft };
  const index = state.index + 1;
  return { state: { index, draft: state.draft }, text: prompts[index] ?? value };
}

/**
 * 输入框文本变化后如何收敛历史游标。
 *
 * `owned` 是输入区最近一次自己写回的文本：只有历史调取（以及同源的快捷指令补全）
 * 会同步它。其余变化来自「编辑消息」「恢复队列消息」或父层清空，当前内容已经不是
 * 调取的那一条，旧下标与进入历史前的草稿都不再对应输入框。继续保留会让下一次 ↑
 * 覆盖新填入的正文，Esc 也会用旧草稿替换它，因此必须回到空闲态。
 */
export function recallAfterValueChange(state: PromptRecallState, value: string, owned: string): PromptRecallState {
  if (state.index === -1 || value === owned) return state;
  return { index: -1, draft: "" };
}

export interface RecallKeyEvent {
  key: string;
  selectionStart: number | null;
  selectionEnd: number | null;
  shiftKey: boolean;
  altKey: boolean;
  metaKey: boolean;
  ctrlKey: boolean;
}

/**
 * 箭头键是否交给历史调取。
 *
 * 空闲时只有「↑ + 无选区 + 光标在开头」进入历史，避免打断多行编辑中的正常移动；
 * 进入历史后上下键始终用于浏览，光标位置不再参与判定。⇧ / ⌥ / ⌘ / Ctrl 组合
 * 保留原生的选择、按词或按行移动。
 */
export function recallKeyDirection(event: RecallKeyEvent, browsing: boolean): "older" | "newer" | null {
  if (event.shiftKey || event.altKey || event.metaKey || event.ctrlKey) return null;
  if (event.key === "ArrowUp" && (browsing || (event.selectionStart === 0 && event.selectionEnd === 0))) return "older";
  if (event.key === "ArrowDown" && browsing) return "newer";
  return null;
}
