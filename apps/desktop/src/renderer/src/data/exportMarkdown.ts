import { safeSlice } from "@boss-harness/shared";
import type { MessageItem } from "./mockData";
import { messageCopyText } from "./messageCopy";

/**
 * 标题栏「导出为 Markdown」的正文拼装。
 * 正文、段落与导出列表保持原有顺序；工具与审批记录复用复制文本，保留结果徽标、
 * 耗时、审批结论或期限、来源、错误码与恢复建议，避免导出的写操作看起来像已成功。
 * 标题是元数据：折叠为单行、限制 200 个字符（不拆分代理对），避免换行或超长标题破坏导出结构。
 */
export function exportMarkdown(title: string, messages: MessageItem[]): string {
  const exportedTitle = safeSlice(title.replace(/\s+/g, " ").trim(), 200) || "当前会话";
  const sections = messages.map(message => {
    const tool = message.toolUse || message.approval
      ? messageCopyText({ toolUse: message.toolUse, approval: message.approval })
      : "";
    const body = [
      message.content,
      ...(message.paragraphs ?? []),
      ...(message.bullets ?? []).map(line => `- ${line}`),
      tool,
    ].filter(Boolean).join("\n\n");
    return `## ${message.role === "user" ? "你" : "BOSS Harness"}\n\n${body}`;
  });
  return `# ${exportedTitle}\n\n${sections.join("\n\n")}`;
}
