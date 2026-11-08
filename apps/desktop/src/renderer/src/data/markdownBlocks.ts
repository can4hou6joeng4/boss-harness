/**
 * 智能体消息的代码围栏切分。
 *
 * 消息在流式输出中逐段到达：起始围栏先到、结束围栏后到；模型输出也可能被截断而
 * 没有结束围栏。这里按行识别围栏，未闭合的围栏按到文末的代码块处理，避免流式期间
 * 把代码原样显示成带反引号的普通文本。
 *
 * 围栏规则（比 CommonMark 宽松，只服务于本应用的单层渲染）：
 * - 起始围栏是行内第一次出现的三个以上反引号，其后只能跟语言标记与空白；
 * - 结束围栏必须独占一行，长度不短于起始围栏，因此代码正文里的反引号不会提前结束代码块；
 * - 兼容 CRLF 正文与语言标记后的空格，正文整体按同一份文本展示与复制。
 */
export interface MarkdownBlock {
  type: "text" | "code";
  /** 代码块的语言标记；没有标记时为 `text`。文本块没有该字段。 */
  lang?: string;
  /** 文本块保留原文；代码块已去掉首尾空白行，保留每行自身的缩进。 */
  content: string;
}

/** 起始围栏：前缀允许任意文本（与旧实现一致），其后是语言标记与行尾空白。 */
const OPENING_FENCE = /^(.*?)(`{3,})([A-Za-z0-9_+.-]*)[ \t]*$/;
/** 结束围栏：整行只有反引号与空白。 */
const CLOSING_FENCE = /^[ \t]*(`{3,})[ \t]*$/;

/** CRLF 正文按 Unix 换行显示与复制，避免代码块里混入不可见的 `\r`。 */
function normalizeCode(value: string): string {
  return value.replace(/\r\n/g, "\n");
}

/**
 * 只裁剪代码块首尾的空白行，保留第一行与最后一行自身的缩进。
 *
 * 旧实现用 `trim()`：`    if x:` 会显示成 `if x:`，而复制仍带缩进，所见与所得不一致。
 * 同样，空代码块返回空串，不显示多余空行。
 */
export function trimCodeBlankLines(value: string): string {
  const lines = value.split("\n");
  let first = 0;
  let last = lines.length - 1;
  while (first <= last && !lines[first]!.trim()) first += 1;
  while (last >= first && !lines[last]!.trim()) last -= 1;
  return first > last ? "" : lines.slice(first, last + 1).join("\n");
}

/** 把正文切成文本块与代码块；代码块内容与展示、复制共用同一份文本。 */
export function splitMarkdownBlocks(content: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  let textStart = 0;
  let offset = 0;
  let fence: { length: number; lang: string } | null = null;
  let codeStart = 0;
  while (offset <= content.length) {
    const newline = content.indexOf("\n", offset);
    const lineEnd = newline < 0 ? content.length : newline;
    const rawLine = content.slice(offset, lineEnd);
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
    if (fence) {
      const closing = CLOSING_FENCE.exec(line)?.[1];
      if (closing && closing.length >= fence.length) {
        const closingStart = offset + line.indexOf("`");
        blocks.push({ type: "code", lang: fence.lang,
          content: trimCodeBlankLines(normalizeCode(content.slice(codeStart, offset))) });
        fence = null;
        // 结束围栏行尾的空白仍属于后续文本，与旧实现的切分位置一致。
        textStart = closingStart + closing.length;
      }
    } else {
      const opening = OPENING_FENCE.exec(line);
      if (opening) {
        const [, prefix = "", ticks = "", marker] = opening;
        const fenceStart = offset + prefix.length;
        if (fenceStart > textStart) blocks.push({ type: "text", content: content.slice(textStart, fenceStart) });
        fence = { length: ticks.length, lang: marker || "text" };
        codeStart = newline < 0 ? content.length : newline + 1;
      }
    }
    if (newline < 0) break;
    offset = newline + 1;
  }
  if (fence) {
    // 流式输出或被截断的回复没有结束围栏：剩余内容仍是代码，不能退回普通文本。
    blocks.push({ type: "code", lang: fence.lang, content: trimCodeBlankLines(normalizeCode(content.slice(codeStart))) });
  } else if (textStart < content.length) {
    blocks.push({ type: "text", content: content.slice(textStart) });
  }
  return blocks;
}
