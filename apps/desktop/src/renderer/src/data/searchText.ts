import { caseFold } from "./caseFold";

const LOCALE = "zh-CN";
const graphemes = new Intl.Segmenter(undefined, { granularity: "grapheme" });

/**
 * 会话内查找与命中高亮共用的归一化：整串 NFKC + 不区分大小写。
 * 整串处理才能保留上下文相关的大小写规则（如希腊词尾 sigma）。
 */
export const searchText = (value: string) => value.normalize("NFKC").toLocaleLowerCase(LOCALE);

/** 谚文组合单元的起始字符：预组合音节、组合 jamo（含扩展区）、兼容 jamo 或半角字母。 */
const HANGUL_BASE = /[\u1100-\u11FF\uA960-\uA97C\uD7B0-\uD7FB\u3131-\u318E\uFFA0-\uFFDC\uAC00-\uD7A3]/;
/** 可以并入前一个谚文组合单元的字母：不含预组合音节，避免整段韩文并成一簇。 */
const HANGUL_EXTEND = /[\u1100-\u11FF\uA960-\uA97C\uD7B0-\uD7FB\u3131-\u318E\uFFA0-\uFFDC]/;

interface SearchCluster {
  text: string;
  index: number;
  end: number;
}

/**
 * 字素簇切分，并把 NFKC 会跨簇组合的谚文字母并入前一个簇。
 * `Intl.Segmenter` 不会把兼容 jamo 或半角字母与相邻字母归为一簇，但 NFKC 会先把
 * 它们分解成组合 jamo 再合成音节（`ㄱ` + `ㅏ` → `가`、`가` + `ㄳ` → `갃`）；
 * 不合并会让按簇归一化漏掉这种等价关系。预组合音节仍各自成簇，避免把整段
 * 韩文并成一个组合单元，保留命中区间的粒度。
 */
function searchClusters(value: string): SearchCluster[] {
  const clusters: SearchCluster[] = [];
  let parts: string[] = [];
  let start = 0;
  let end = 0;
  let last = "";
  for (const { segment, index } of graphemes.segment(value)) {
    const first = segment[0] ?? "";
    if (parts.length && HANGUL_EXTEND.test(first) && HANGUL_BASE.test(last)) {
      parts.push(segment);
      end = index + segment.length;
    } else {
      if (parts.length) clusters.push({ text: parts.join(""), index: start, end });
      parts = [segment];
      start = index;
      end = index + segment.length;
    }
    last = segment[segment.length - 1] ?? "";
  }
  if (parts.length) clusters.push({ text: parts.join(""), index: start, end });
  return clusters;
}

export interface MappedSearchText {
  normalized: string;
  /** 每个归一化码元对应的原文起始偏移（UTF-16）。 */
  starts: number[];
  /** 每个归一化码元对应的原文结束偏移（UTF-16），覆盖生成它的整个字素簇。 */
  ends: number[];
}

/**
 * 归一化整段文本，并记录每个归一化码元对应的原文 UTF-16 区间。
 * NFKC 按字素簇进行，组合字符不会与基字符分离；小写仍取整串结果以保留上下文规则，
 * 再按码点的小写长度把结果映射回 NFKC 区间（词尾 sigma 等只改字形、不改长度）。
 */
export function searchTextWithMap(text: string): MappedSearchText {
  let nfkc = "";
  const nfkcStarts: number[] = [];
  const nfkcEnds: number[] = [];
  for (const { text: cluster, index, end } of searchClusters(text)) {
    const value = cluster.normalize("NFKC");
    for (let offset = 0; offset < value.length; offset += 1) {
      nfkc += value[offset];
      nfkcStarts.push(index);
      nfkcEnds.push(end);
    }
  }
  const normalized = nfkc.toLocaleLowerCase(LOCALE);
  const starts: number[] = [];
  const ends: number[] = [];
  for (let index = 0; index < nfkc.length;) {
    const codePoint = nfkc.codePointAt(index);
    if (codePoint === undefined) break;
    const char = String.fromCodePoint(codePoint);
    const start = nfkcStarts[index];
    const end = nfkcEnds[index + char.length - 1];
    if (start === undefined || end === undefined) break;
    for (let offset = 0; offset < char.toLocaleLowerCase(LOCALE).length; offset += 1) {
      starts.push(start);
      ends.push(end);
    }
    index += char.length;
  }
  // 长度不一致只可能来自区域设置特有的上下文转换；补齐或截断，保证映射与归一化文本等长。
  while (starts.length < normalized.length) {
    starts.push(starts[starts.length - 1] ?? 0);
    ends.push(ends[ends.length - 1] ?? text.length);
  }
  starts.length = normalized.length;
  ends.length = normalized.length;
  return { normalized, starts, ends };
}

/**
 * 内核搜索使用的归一化：按字素簇 NFKC + 逐码点 casefold。
 * 与 `searchText` 的整串小写刻意分开：内核 `_search_normalized` 用 casefold，
 * 两者在 `ß`/`ss`、`ς`/`σ` 等码点上结果不同。按簇归一化才能与内核一样
 * 把 NFD 重音与分解谚文组合成单个字符；兼容 jamo 与半角字母跨簇合成音节，
 * 由 `searchClusters` 并入相邻簇。
 */
export function kernelSearchText(value: string): string {
  let normalized = "";
  for (const cluster of searchClusters(value)) {
    for (const char of cluster.text.normalize("NFKC")) normalized += caseFold(char);
  }
  return normalized;
}

/** 与 `kernelSearchText` 对应的原文 UTF-16 区间映射。 */
export function kernelSearchTextWithMap(text: string): MappedSearchText {
  let normalized = "";
  const starts: number[] = [];
  const ends: number[] = [];
  for (const cluster of searchClusters(text)) {
    for (const char of cluster.text.normalize("NFKC")) {
      const folded = caseFold(char);
      for (let offset = 0; offset < folded.length; offset += 1) {
        normalized += folded[offset];
        starts.push(cluster.index);
        ends.push(cluster.end);
      }
    }
  }
  return { normalized, starts, ends };
}
