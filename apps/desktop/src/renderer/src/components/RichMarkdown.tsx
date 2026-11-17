import React from "react";
import { useClipboardCopy } from "../data/clipboardCopy";
import { splitMarkdownBlocks } from "../data/markdownBlocks";
import { IconCopy, IconCheck, IconExternalLink } from "./Icons";

interface RichMarkdownProps {
  content: string;
}

/**
 * 与主进程 isAllowedExternalUrl 保持同一协议集合：只有这些链接交给系统打开。
 * 其余协议（javascript:、file: 等）既不导航也不交给系统，避免静默失败造成的误判。
 */
const EXTERNAL_SCHEMES = ["http:", "https:", "mailto:"];
function externalTarget(url: string): string | null {
  try {
    return EXTERNAL_SCHEMES.includes(new URL(url).protocol) ? url : null;
  } catch {
    return null;
  }
}

/** 配对未转义的圆括号；一次扫描避免未闭合链接反复搜索整段后文。 */
function linkDestinationEnds(text: string): Map<number, number> {
  const openings: number[] = [];
  const ends = new Map<number, number>();
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === "\\") { index += 1; continue; }
    if (character === "(") openings.push(index);
    else if (character === ")") {
      const opening = openings.pop();
      if (opening !== undefined) ends.set(opening, index);
    }
  }
  return ends;
}

type InlineToken = { kind: "link" | "code" | "bold"; index: number; text: string; end: number };

/**
 * 从 `from` 起找下一个行内标记：`[text](`、`` `code` `` 或 `**bold**`。
 *
 * 旧实现用一条全局正则反复 `exec`：未闭合的 `[`、反引号或 `**` 会让每个起点都搜索整段后文，
 * 合法但很长的一行（模型输出常见）因此平方级回溯、冻结渲染主线程。这里为三种闭合符缓存
 * 「下一个出现位置」，起点只前进不后退，整体一次扫描。
 */
function nextInlineToken(text: string, from: number): InlineToken | null {
  // -2 = 尚未搜索；-1 = 后续不存在。
  let bracket = -2, tick = -2, star = -2;
  for (let index = from; index < text.length; index += 1) {
    const character = text[index];
    if (character === "[") {
      if (bracket === -2 || (bracket !== -1 && bracket < index + 1)) bracket = text.indexOf("]", index + 1);
      if (bracket > index + 1 && text[bracket + 1] === "(") {
        return { kind: "link", index, text: text.slice(index + 1, bracket), end: bracket + 2 };
      }
    } else if (character === "`") {
      if (tick === -2 || (tick !== -1 && tick < index + 1)) tick = text.indexOf("`", index + 1);
      if (tick > index + 1) return { kind: "code", index, text: text.slice(index + 1, tick), end: tick + 1 };
    } else if (character === "*" && text[index + 1] === "*") {
      if (star === -2 || (star !== -1 && star < index + 2)) star = text.indexOf("*", index + 2);
      if (star > index + 2 && text[star + 1] === "*") {
        return { kind: "bold", index, text: text.slice(index + 2, star), end: star + 2 };
      }
    }
  }
  return null;
}

export const RichMarkdown: React.FC<RichMarkdownProps> = ({ content }) => {  const { feedback, copy } = useClipboardCopy();

  const handleCopyCode = (code: string, index: number) => {
    // 只有写入成功才显示「已复制」；失败时给出原因，避免用户粘贴出旧内容才发现。
    void copy(code, String(index));
  };

  // 围栏切分放在纯函数里：流式未闭合、CRLF 与代码正文里的反引号都由它处理，
  // 展示与「复制代码」共用同一份已裁剪首尾空白行的正文。
  const parts = splitMarkdownBlocks(content);

  // 行内解析器（解析链接、粗体、行内代码）
  const renderInline = (text: string) => {
    // 匹配:
    // 1. [text]( -> 链接开头，目标终点由圆括号配对表确定
    // 2. `code` -> 行内代码
    // 3. **bold** -> 粗体
    const linkEnds = linkDestinationEnds(text);

    const elements: React.ReactNode[] = [];
    let currentIdx = 0;
    let token = nextInlineToken(text, currentIdx);

    while (token !== null) {
      if (token.index > currentIdx) {
        elements.push(text.slice(currentIdx, token.index));
      }

      if (token.kind === "link") {
        const linkText = token.text;
        const opening = token.end - 1;
        const closing = linkEnds.get(opening);
        if (closing === undefined || closing === opening + 1) {
          // 流式输出尚未闭合时保留原文，不把地址的一部分变成可点击链接。
          elements.push(text.slice(token.index, token.end));
          currentIdx = token.end;
          token = nextInlineToken(text, currentIdx);
          continue;
        }
        const linkUrl = text.slice(opening + 1, closing).replace(/\\([\\()])/g, "$1");
        currentIdx = closing + 1;
        const target = externalTarget(linkUrl);
        const isCitation = linkText.startsWith("来源") || /^\d+$/.test(linkText) || linkText.includes("↗") || linkText.includes("GitHub");

        if (isCitation) {
          elements.push(
            <a
              key={token.index}
              href={linkUrl}
              target="_blank"
              rel="noreferrer"
              className="chat-citation-pill"
              title={target ? `打开链接: ${target}` : `${linkUrl}（该链接协议不会打开）`}
              onClick={(e) => {
                e.preventDefault();
                if (target) window.open(target, "_blank");
              }}
            >
              <span>{linkText}</span>
              <IconExternalLink size={10} style={{ opacity: 0.7 }} />
            </a>
          );
        } else {
          elements.push(
            <a
              key={token.index}
              href={linkUrl}
              className="chat-inline-link"
              title={target ? target : `${linkUrl}（该链接协议不会打开）`}
              onClick={(e) => {
                // 一律拦截默认导航：外部协议交给主进程，其余协议（javascript: 等）不在渲染进程里执行。
                e.preventDefault();
                if (target) window.open(target, "_blank");
              }}
            >
              {linkText}
            </a>
          );
        }
      } else if (token.kind === "code") {
        // 行内代码 `code`
        elements.push(
          <code key={token.index} className="chat-inline-code">
            {token.text}
          </code>
        );
        currentIdx = token.end;
      } else {
        // 粗体 **bold**
        elements.push(
          <strong key={token.index} style={{ fontWeight: 600, color: "var(--text-main)" }}>
            {token.text}
          </strong>
        );
        currentIdx = token.end;
      }

      token = nextInlineToken(text, currentIdx);
    }

    if (currentIdx < text.length) {
      elements.push(text.slice(currentIdx));
    }

    return elements;
  };

  return (
    <div className="agent-markdown">
      {parts.map((part, pIdx) => {
        if (part.type === "code") {
          return (
            <div key={pIdx} className="code-block-wrapper">
              <div className="code-block-header">
                <span>{part.lang}</span>
                <button
                  type="button"
                  className="code-block-copy-btn"
                  title={feedback?.key === String(pIdx) && !feedback.ok ? `复制失败：${feedback.reason}` : "复制代码到剪贴板"}
                  onClick={() => handleCopyCode(part.content, pIdx)}
                >
                  {feedback?.key === String(pIdx) && feedback.ok ? (
                    <>
                      <IconCheck size={11} style={{ color: "var(--accent-green)" }} />
                      <span style={{ color: "var(--accent-green)" }}>已复制</span>
                    </>
                  ) : feedback?.key === String(pIdx) ? (
                    <>
                      <IconCopy size={11} style={{ color: "var(--text-muted)" }} />
                      <span style={{ color: "var(--text-muted)" }}>复制失败</span>
                    </>
                  ) : (
                    <>
                      <IconCopy size={11} />
                      <span>复制代码</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="code-block-pre">
                <code>{part.content}</code>
              </pre>
            </div>
          );
        }

        // 常规文本行处理
        const lines = part.content.split("\n");
        return (
          <React.Fragment key={pIdx}>
            {lines.map((line, lIdx) => {
              const trimmed = line.trim();
              if (!trimmed) return <div key={lIdx} style={{ height: 6 }} />;

              // 引用块
              if (trimmed.startsWith("> ")) {
                return (
                  <blockquote key={lIdx} className="chat-blockquote">
                    {renderInline(trimmed.slice(2))}
                  </blockquote>
                );
              }

              // 无序列表
              if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                return (
                  <div key={lIdx} className="chat-list-item">
                    <span className="chat-list-bullet">•</span>
                    <span>{renderInline(trimmed.slice(2))}</span>
                  </div>
                );
              }

              // 有序列表
              const orderedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
              if (orderedMatch) {
                return (
                  <div key={lIdx} className="chat-list-item">
                    <span className="chat-list-num">{orderedMatch[1]}.</span>
                    <span>{renderInline(orderedMatch[2] ?? "")}</span>
                  </div>
                );
              }

              // 标题
              const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
              if (heading) {
                const level = heading[1]!.length;
                return React.createElement(`h${level}`, { key: lIdx, className: `chat-heading chat-heading-${level}` }, renderInline(heading[2]!));
              }

              return <p key={lIdx}>{renderInline(line)}</p>;
            })}
          </React.Fragment>
        );
      })}
    </div>
  );
};
