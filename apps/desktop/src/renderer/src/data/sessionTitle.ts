import { codePointLength } from "@boss-harness/shared";

/** 侧栏会话标题上限；与内核默认标题保持一致的回退文案。 */
export const SESSION_TITLE_LIMIT = 32;
export const SESSION_TITLE_FALLBACK = "新会话";

/** 首页会把所选项目拼成「招聘项目：<名称>\n\n<正文>」；标题只取正文。 */
const PROJECT_PREFIX = /^\s*招聘项目：[^\n]*\n\n/;

/** 去掉首页固定格式的项目前缀；不匹配时原样返回。 */
export function stripProjectPrefix(prompt: string): string {
  return prompt.replace(PROJECT_PREFIX, "");
}

/** 按 Unicode 码点截断，不切开代理对；`limit` 按码点计数。 */
function sliceCodePoints(text: string, limit: number): string {
  return Array.from(text).slice(0, limit).join("");
}

/**
 * 新建会话标题：剥离项目前缀、折叠空白后按码点安全截断。
 * 只影响展示，发送给模型的输入保持不变。
 */
export function sessionTitleFromPrompt(prompt: string, limit = SESSION_TITLE_LIMIT): string {
  const collapsed = stripProjectPrefix(prompt).replace(/\s+/g, " ").trim();
  return (codePointLength(collapsed) > limit ? sliceCodePoints(collapsed, limit) : collapsed) || SESSION_TITLE_FALLBACK;
}

/** 会话顶栏与分支标签：折叠空白，超过上限时按 Unicode 码点安全截断并保留省略号。 */
export function compactTitle(text: string | null | undefined, limit: number, fallback = ""): string {
  const collapsed = (text ?? "").replace(/\s+/g, " ").trim();
  if (!collapsed || limit <= 0) return fallback;
  // 编码上限按码点计数：先判断是否真的超过上限，避免 emoji 标题未超限却被误加省略号。
  return codePointLength(collapsed) > limit ? `${sliceCodePoints(collapsed, limit).trimEnd()}…` : collapsed;
}
