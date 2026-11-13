import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { ModalSurface } from "./ModalSurface";
import { IconSearch, IconChat, IconChevronRight, IconClose } from "./Icons";
import type { ProjectFolder, SessionItem } from "../data/mockData";
import { sessionRows } from "../data/sessionRows";
import { useLocalNow } from "../data/useLocalNow";
import { buildSearchOptions, searchHitFocus, searchRoleLabel, type SearchOption } from "../data/searchOptions";
import { searchEmptyCopy, searchStatusText, type MessageSearchState } from "../data/searchStatus";
import { splitKernelQueryHighlight, splitQueryHighlight } from "../data/findHighlight";
import { visibleThreadSearchHits, liveMessageSearchState, type MessageSearchSettlement, type ThreadSearchBatch } from "../data/messageSearch";
import { searchThreadMessages } from "../data/harnessBridge";
import { clearRecentSearches, readRecentSearches, rememberRecentSearch, RECENT_SEARCH_MIN_LENGTH } from "../data/recentSearches";
import { findSeedFromSelection, isEditableTarget } from "../data/findSeed";
import { formatRelativeTime } from "@boss-harness/shared";

/** 与 `thread/search` 的上限及「仅显示部分结果」的说明一致：内核最多返回 50 条。 */
const MESSAGE_SEARCH_LIMIT = 50;

/**
 * 用 `mark` 标出关键词；无命中时原样输出。
 * 标题与项目名按空白拆分关键词、与会话过滤共用整串 NFKC 小写归一化；消息片段来自内核搜索，
 * 用内核 casefold 归一化。项目名同样参与过滤，必须一并标注，否则命中的结果行看不出原因。
 */
function Highlighted({ text, query, kernel = false }: { text: string; query: string; kernel?: boolean }) {
  const segments = kernel ? splitKernelQueryHighlight(text, query) : splitQueryHighlight(text, query);
  return <>{segments.map((segment, index) => segment.match
    ? <mark className="search-match" key={index}>{segment.text}</mark>
    : segment.text)}</>;
}

export function SearchDialog({ folders, onSelect, onClose, searchMessages = false, searchArchived = false, onOpenMessage }: {
  folders: ProjectFolder[];
  onSelect: (session: SessionItem) => void;
  onClose: () => void;
  /** 内核声明 threadSearch 能力时为真；否则只按标题与项目搜索。 */
  searchMessages?: boolean;
  /** 内核声明 threadSearchArchived 能力时为真；为假时不发送 includeArchived。 */
  searchArchived?: boolean;
  /** 打开会话并定位到命中的消息；缺省时退回只打开会话。工具命中传入展开工具块的意图，查询词用于目标消息内的关键词高亮。 */
  onOpenMessage?: (session: SessionItem, itemId: string, revealToolBlock: boolean, query: string) => void;
}) {
  const now = useLocalNow();
  // 与聊天内查找一致：打开时沿用适合作为关键词的选中文本，单行、非空白且不超过 120 个字符。
  const [query, setQuery] = useState(() => findSeedFromSelection(
    typeof window === "undefined" ? null : window.getSelection()?.toString(),
    { editable: typeof document === "undefined" ? false : isEditableTarget(document.activeElement) },
  ) ?? "");
  // 显式选择绑定结果标识，异步消息命中插入前方时仍打开原对象；未选择时默认首项。
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [hitBatch, setHitBatch] = useState<ThreadSearchBatch | null>(null);
  const [messageState, setMessageState] = useState<MessageSearchState>("idle");
  // 最近一次请求完成（成功或失败）时的输入；不等同于当前输入，用于避免把旧状态当成当前结论。
  const [settled, setSettled] = useState<MessageSearchSettlement | null>(null);
  const [recent, setRecent] = useState<string[]>(readRecentSearches);
  const [includeArchived, setIncludeArchived] = useState(false);
  const rows = sessionRows(folders, query, { includeArchived });
  const allRows = sessionRows(folders, "", { includeArchived });
  const rowsById = new Map(allRows.map(row => [row.session.id, row]));
  const availableThreadIds = new Set(allRows.map(row => row.session.id));
  const { matches: hits, truncated: hitsTruncated } = searchMessages
    ? visibleThreadSearchHits(hitBatch, query, includeArchived, availableThreadIds)
    : { matches: [], truncated: false };
  // 输入或归档范围变化后，旧批次立即失效；在新请求完成前按检索中呈现，不给出「没有命中」的结论。
  const shownMessageState = liveMessageSearchState(messageState, query, includeArchived, settled, searchMessages);
  const options = buildSearchOptions(rows, hits, rowsById);
  const messageOptions = options.filter((option): option is Extract<SearchOption, { kind: "message" }> => option.kind === "message");
  const sessionOptions = options.filter((option): option is Extract<SearchOption, { kind: "session" }> => option.kind === "session");
  // 状态行与空态必须与实际完成的搜索范围一致：消息搜索失败或未启用时不能宣称消息没有命中。
  const empty = searchEmptyCopy(query, shownMessageState, searchMessages);
  const status = searchStatusText(query, rows.length, messageOptions.length, shownMessageState);
  const inputRef = useRef<HTMLInputElement>(null), resultsRef = useRef<HTMLDivElement>(null);
  const listId = useId(), statusId = useId();
  const selected = Math.max(0, options.findIndex(option => option.key === selectedKey));
  useLayoutEffect(() => {
    resultsRef.current?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selected, options[selected]?.key]);
  useEffect(() => {
    const needle = query.trim();
    if (!searchMessages || needle.length < 2) {
      setHitBatch(null); setMessageState("idle"); setSettled(null);
      return;
    }
    let cancelled = false;
    setMessageState("loading");
    const timer = window.setTimeout(() => {
      void searchThreadMessages(needle, MESSAGE_SEARCH_LIMIT, includeArchived).then(result => {
        if (cancelled) return;
        // 响应形状不可信：matches 不是数组时按失败处理，不能把畸形值带进渲染期。
        if (!result || !Array.isArray(result.matches)) {
          setHitBatch(null); setSettled({ query: needle, includeArchived }); setMessageState("error");
          return;
        }
        setHitBatch({ query: needle, includeArchived, matches: result.matches, truncated: result.truncated === true });
        setSettled({ query: needle, includeArchived });
        setMessageState("ready");
      }).catch(() => {
        if (cancelled) return;
        setHitBatch(null); setSettled({ query: needle, includeArchived }); setMessageState("error");
      });
    }, 250);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [query, searchMessages, includeArchived]);
  const openOption = (option: SearchOption | undefined) => {
    if (!option) return;
    if (query.trim().length >= RECENT_SEARCH_MIN_LENGTH) setRecent(rememberRecentSearch(query));
    if (option.kind === "session") { onSelect(option.row.session); onClose(); return; }
    if (onOpenMessage) {
      const focus = searchHitFocus(option.hit, query);
      onOpenMessage(option.row.session, focus.itemId, focus.revealToolBlock, focus.query);
      onClose();
    } else { onSelect(option.row.session); onClose(); }
  };
  const move = (delta: number) => {
    const next = options.length ? options[(selected + delta + options.length) % options.length] : undefined;
    setSelectedKey(next?.key ?? null);
  };
  const optionProps = (option: SearchOption) => {
    const current = options.findIndex(entry => entry.key === option.key);
    return {
      role: "option" as const, tabIndex: -1, id: `${listId}-${current}`, "aria-selected": current === selected,
      className: `search-result${current === selected ? " highlighted" : ""}${option.kind === "message" ? " search-message-hit" : ""}`,
      onPointerMove: (event: React.PointerEvent) => { if (event.pointerType === "mouse" && (event.movementX || event.movementY)) setSelectedKey(option.key); },
      onClick: () => openOption(option),
    };
  };
  return <ModalSurface title="搜索聊天" onClose={onClose} className="search-dialog">
    <div className="search-field"><IconSearch size={19} /><input ref={inputRef} role="combobox" aria-label="搜索聊天和项目" aria-autocomplete="list" aria-expanded="true" aria-controls={listId} aria-describedby={statusId} aria-activedescendant={options.length ? `${listId}-${selected}` : undefined} autoComplete="off" placeholder="搜索聊天和项目…" value={query} onChange={event => { setQuery(event.target.value); setSelectedKey(null); }} onKeyDown={event => {
      if (event.nativeEvent.isComposing || event.keyCode === 229 || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
      if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
      if (event.key === "Enter" && options[selected]) { event.preventDefault(); event.stopPropagation(); openOption(options[selected]); }
    }} />{query && <button type="button" className="search-clear" aria-label="清除搜索" onClick={() => { setQuery(""); setSelectedKey(null); inputRef.current?.focus(); }}><IconClose size={15} /></button>}</div>
    <div className="search-results" ref={resultsRef}>
      <p id={statusId} role="status">{status}</p>
      {!query.trim() && recent.length > 0 && <div className="search-recent" role="group" aria-label="最近搜索">
        <span className="search-recent-label">最近搜索</span>
        {recent.map(term => <button type="button" key={term} className="search-recent-chip" onClick={() => { setQuery(term); setSelectedKey(null); inputRef.current?.focus(); }}>{term}</button>)}
        <button type="button" className="search-recent-clear" onClick={() => { clearRecentSearches(); setRecent([]); }}>清除</button>
      </div>}
      <div id={listId} role="listbox" aria-label="聊天与消息搜索结果">
        {query.trim().length >= 2 && searchMessages && <>
          <p className="search-message-heading" role="presentation">{shownMessageState === "loading" ? "正在搜索消息…"
            : shownMessageState === "error" ? "消息搜索失败，可继续按标题查找"
            : messageOptions.length ? <>{`消息命中`}{hitsTruncated && <span className="search-truncated" title="搜索有界：最多 100 个会话、50 条消息，较早或过多的命中不会全部返回">仅显示部分结果</span>}</>
            : "没有匹配的消息"}</p>
          {messageOptions.map(option => {
            const { hit, row } = option;
            return <button type="button" key={option.key} title={hit.snippet} {...optionProps(option)}>
              <IconChat size={17} /><span><strong><Highlighted text={row.session.title} query={query} /></strong><small>{row.session.archived === true ? "已归档 · " : ""}<Highlighted text={row.project} query={query} /> · {searchRoleLabel(hit.role)} · <Highlighted text={hit.snippet} query={query} kernel /></small></span><IconChevronRight size={13} />
            </button>;
          })}
        </>}
        {sessionOptions.map(option => {
          const { row } = option;
          return <button type="button" key={option.key} {...optionProps(option)}><IconChat size={17} /><span><strong><Highlighted text={row.session.title} query={query} /></strong><small>{row.session.archived === true ? "已归档 · " : ""}<Highlighted text={row.project} query={query} /> · {row.session.updatedAt ? formatRelativeTime(row.session.updatedAt, now) : row.session.timeAgo}</small></span><IconChevronRight size={13} /></button>;
        })}
      </div>
      {!sessionOptions.length && !messageOptions.length && shownMessageState !== "loading" && <div className="search-empty"><IconSearch size={28} /><strong>{empty.title}</strong><span>{empty.hint}</span></div>}
    </div><div className="search-footer">{searchArchived && <label className="search-archived-toggle" title="同时搜索已归档会话；归档不会删除消息"><input type="checkbox" checked={includeArchived} onChange={event => { setIncludeArchived(event.target.checked); setSelectedKey(null); }} />含已归档</label>}<span><kbd>↑</kbd><kbd>↓</kbd> 选择</span><span><kbd>↵</kbd> 打开</span><span><kbd>esc</kbd> 关闭</span></div>
  </ModalSurface>;
}
