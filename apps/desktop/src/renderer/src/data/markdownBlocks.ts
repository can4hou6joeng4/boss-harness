/**
 * 智能体消息的代码围栏切分。
 *
 * 消息在流式输出中逐段到达：起始围栏先到、结束围栏后到；模型输出也可能被截断而
 * 没有结束围栏。这里按行识别围栏，未闭合的围栏按到文末的代码块处理，避免流式期间
 * 把代码原样显示成带围栏标记的普通文本。
 *
 * 围栏规则（比 CommonMark 宽松，只服务于本应用的单层渲染）：
 * - 起始围栏是行内第一次出现的三个以上反引号；波浪号围栏只在行首（最多三个空格）识别，
 *   避免正文里的装饰性 `~~~` 把后续内容变成代码块；围栏与语言标记之间允许空格 / Tab；
 * - 结束围栏必须独占一行、与起始围栏同一种标记且长度不短于起始围栏，因此代码正文里的
 *   反引号或波浪号不会提前结束代码块；
 * - 兼容 CRLF 正文与语言标记后的空格，正文整体按同一份文本展示与复制。
 */
export interface MarkdownBlock {
  type: "text" | "code";
  /** 代码块的语言标记；没有标记时为 `text`。文本块没有该字段。 */
  lang?: string;
  /** 文本块保留原文；代码块已去掉首尾空白行，保留每行自身的缩进。 */
  content: string;
}

/** 起始围栏的语言字符集；`#` 用于 `c#` / `f#` / `q#`。 */
const LANG_CHAR = /[A-Za-z0-9_+.#-]/;
/** 波浪号围栏只在行首（最多三个空格）识别；正文里的装饰性 `~~~` 不开启代码块。 */
const TILDE_OPENING_FENCE = /^([ \t]{0,3})(~{3,})[ \t]*([A-Za-z0-9_+.#-]*)[ \t]*$/;
/** 结束围栏：整行只有同一种标记与空白。 */
const CLOSING_FENCE = /^[ \t]*(`{3,}|~{3,})[ \t]*$/;

/** 从围栏标记末尾读出语言：两端允许空格 / Tab，中间只能是语言字符，其余字符判为失败。 */
function fenceLanguage(line: string, start: number): string | null {
  let index = start;
  while (index < line.length && (line[index] === " " || line[index] === "\t")) index += 1;
  const langStart = index;
  while (index < line.length && LANG_CHAR.test(line[index]!)) index += 1;
  const lang = line.slice(langStart, index);
  while (index < line.length && (line[index] === " " || line[index] === "\t")) index += 1;
  return index === line.length ? lang : null;
}

/**
 * 反引号起始围栏：前缀允许任意文本（与旧实现一致），取第一个能成立的反引号串。
 *
 * 旧实现用 `^(.*?)(`{3,})...$`：一行里的长反引号串后跟非法尾字符时，每个起点都尝试到串尾，
 * 平方级回溯会冻结渲染主线程。这里按反引号串前进，每个串只检查一次尾部，整体线性。
 */
function backtickOpeningFence(line: string): { prefixLength: number; run: string; language: string } | null {
  for (let index = line.indexOf("`"); index !== -1; ) {
    let end = index;
    while (end < line.length && line[end] === "`") end += 1;
    if (end - index >= 3) {
      const language = fenceLanguage(line, end);
      if (language !== null) return { prefixLength: index, run: line.slice(index, end), language };
    }
    index = line.indexOf("`", end);
  }
  return null;
}

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
  let fence: { marker: "`" | "~"; length: number; lang: string } | null = null;
  let codeStart = 0;
  while (offset <= content.length) {
    const newline = content.indexOf("\n", offset);
    const lineEnd = newline < 0 ? content.length : newline;
    const rawLine = content.slice(offset, lineEnd);
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
    if (fence) {
      const closing = CLOSING_FENCE.exec(line)?.[1];
      if (closing && closing[0] === fence.marker && closing.length >= fence.length) {
        const closingStart = offset + line.indexOf(fence.marker);
        blocks.push({ type: "code", lang: fence.lang,
          content: trimCodeBlankLines(normalizeCode(content.slice(codeStart, offset))) });
        fence = null;
        // 结束围栏行尾的空白仍属于后续文本，与旧实现的切分位置一致。
        textStart = closingStart + closing.length;
      }
    } else {
      const backtick = backtickOpeningFence(line);
      const tilde = backtick ? null : TILDE_OPENING_FENCE.exec(line);
      if (backtick || tilde) {
        const prefixLength = backtick ? backtick.prefixLength : (tilde![1] ?? "").length;
        const run = backtick ? backtick.run : tilde![2]!;
        const language = backtick ? backtick.language : tilde![3] ?? "";
        const isTilde = run[0] === "~";
        // 反引号前缀是围栏前的正文，需要保留；波浪号前缀只是行首缩进，属于围栏本身。
        const fenceStart = offset + (isTilde ? 0 : prefixLength);
        if (fenceStart > textStart) blocks.push({ type: "text", content: content.slice(textStart, fenceStart) });
        fence = { marker: isTilde ? "~" : "`", length: run.length, lang: language || "text" };
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
