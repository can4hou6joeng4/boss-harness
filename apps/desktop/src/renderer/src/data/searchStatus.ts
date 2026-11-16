import { codePointLength } from "@boss-harness/shared";

/** 搜索弹窗的消息搜索状态；与组件内的状态机保持一致。 */
export type MessageSearchState = "idle" | "loading" | "ready" | "error" | "tooLong";

/** 触发消息搜索的最少字符数：按 Unicode 码点计数，与界面文案「至少 2 个字符」一致。 */
export const MESSAGE_SEARCH_MIN_LENGTH = 2;

/**
 * 消息搜索的查询上限：按 Unicode 码点计数，与主进程 `thread/search` 安全校验及内核
 * `_text(maximum=200)` 一致。超限时不发请求，由界面说明原因。
 */
export const MESSAGE_SEARCH_MAX_LENGTH = 200;

/**
 * 状态行的文字。
 *
 * 消息搜索失败时，只报标题命中数量会掩盖消息部分未完成；读屏用户依赖这个
 * `role="status"` 区域获知失败，因此失败信息必须进入状态行。截断同理：命中标题旁的
 * 「仅显示部分结果」可能只以悬停提示说明原因，状态行必须自己给出结论，否则只听到
 * 数量的用户会把部分结果当成完整结果。零命中且截断时，状态行与空态使用同一说法。
 * 搜索词超限同样要说明「未搜索消息」，不能与失败混淆。
 */
export function searchStatusText(
  query: string,
  chatCount: number,
  messageCount: number,
  messageState: MessageSearchState,
  truncated = false,
): string {
  if (!query.trim()) return "最近聊天";
  if (messageState === "ready") {
    if (truncated) {
      return messageCount > 0
        ? `找到 ${chatCount} 个聊天、${messageCount} 条消息（仅显示部分结果）`
        : `找到 ${chatCount} 个聊天；消息搜索不完整`;
    }
    return `找到 ${chatCount} 个聊天、${messageCount} 条消息`;
  }
  if (messageState === "tooLong") return `找到 ${chatCount} 个聊天；搜索词超过 ${MESSAGE_SEARCH_MAX_LENGTH} 字符，未搜索消息`;
  if (messageState === "error") return `找到 ${chatCount} 个聊天；消息搜索失败`;
  return `找到 ${chatCount} 个聊天`;
}

export interface SearchEmptyCopy {
  title: string;
  hint: string;
}

/**
 * 结果区为空时的文案。
 *
 * 空态只能描述真正完成的搜索范围：消息搜索失败、旧内核不支持消息搜索、查询
 * 短于 2 个字符或超过 200 个字符时，标题为空并不能说明消息内容没有命中，不能用
 * 「没有找到相关聊天或消息」给出完整结论。
 */
export function searchEmptyCopy(
  query: string,
  messageState: MessageSearchState,
  searchMessages: boolean,
): SearchEmptyCopy {
  if (!query.trim()) return { title: "还没有聊天", hint: "创建聊天后，可以在这里快速找到它" };
  if (!searchMessages) {
    return {
      title: "没有找到相关聊天",
      hint: "当前内核只按标题与项目搜索；升级内核后可搜索消息内容",
    };
  }
  if (messageState === "error") {
    return {
      title: "标题中没有匹配的聊天",
      hint: "消息搜索失败，暂时无法确认消息内容是否有命中；可稍后重试或换个关键词",
    };
  }
  if (messageState === "tooLong") {
    return {
      title: "没有找到匹配的聊天",
      hint: `标题中没有匹配；消息搜索需要 ${MESSAGE_SEARCH_MAX_LENGTH} 个字符以内，可缩短搜索词后重试`,
    };
  }
  if (codePointLength(query.trim()) < MESSAGE_SEARCH_MIN_LENGTH) {
    return {
      title: "没有找到匹配的聊天",
      hint: "标题中没有匹配；输入至少 2 个字符可同时搜索消息内容",
    };
  }
  // 消息搜索尚未完成（组件在 loading 时不渲染空态；idle 是发起检索前的一帧）。
  if (messageState !== "ready") {
    return {
      title: "正在搜索消息…",
      hint: "标题结果已更新；消息内容仍在检索中",
    };
  }
  return { title: "没有找到相关聊天或消息", hint: "试试其他关键词、项目名称或消息内容" };
}
