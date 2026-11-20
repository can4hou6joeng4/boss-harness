import { useCallback, useEffect, useRef, useState } from "react";
import type { ThreadUsageBucket, ThreadUsageCacheWaste, ThreadUsageReadResponse, ThreadUsageSummaryJob, ThreadUsageTurn } from "@boss-harness/protocol";
import { harnessErrorText, readThreadUsage } from "./harnessBridge";
import { readPagedItems } from "./pagedRead";
import { branchPageLeafOf, sameLeafAcrossPages } from "./branchPages";
import { bucketOf, cacheWasteOf, isCount as count, summaryJobsOf, turnOf, verifyUsageTurns } from "./usageMapping";

/**
 * 会话用量（只在内核声明 capabilities.threadUsage 时启用）。
 * 数据只来自 thread/usage/read：内核按回合汇总已持久的 provider 上报用量，不估算、不计价。
 * 界面只做形状校验与展示；未上报字段保持 null，由组件显示为“—”。
 */
export type UsageView = "log" | "branch";
export interface ThreadUsageState {
  loading: boolean;
  error: string;
  view: UsageView;
  data?: { threadId: string; view: UsageView; turnCount: number; turns: ThreadUsageTurn[]; truncated: boolean;
    summaryTasks: ThreadUsageBucket; totals: ThreadUsageBucket;
    /** 旧内核不返回摘要任务明细。 */
    summaryJobs?: ThreadUsageSummaryJob[]; summaryJobCount?: number; summaryJobsTruncated?: boolean;
    /** 缓存未命中估算；只有“全部记录”视图的新内核返回。 */
    cacheWaste?: ThreadUsageCacheWaste };
}

const MAX_PAGES = 10;
/** 分支视图翻页期间位置变化：各页的回合与合计分属不同位置，放弃并让用户刷新。 */
const USAGE_LEAF_DRIFT = "当前分支在读取用量期间发生变化（切换了分支或开始了新回合），本次结果可能混用两个位置的用量，已放弃；请刷新后重试。";

/** 按页读取（每页 200 个回合，最多 10 页），任一页形状不符即整体报错，不展示部分可疑数据。 */
async function readAll(threadId: string, view: UsageView, valid: () => boolean): Promise<ThreadUsageState["data"]> {
  let head: ThreadUsageReadResponse | null = null;
  let summaryTasks: ThreadUsageBucket | null = null, totals: ThreadUsageBucket | null = null;
  let summaryMeta: ReturnType<typeof summaryJobsOf> | null = null;
  let cacheWaste: ThreadUsageCacheWaste | undefined;
  let lastTurnCount: number | undefined;
  // 分支视图的每一页都带有内核计算该页时的位置；合计取自第一页、回合逐页拼接，位置必须一致。
  const leaves: (string | null)[] = [];
  const reads = await readPagedItems<ThreadUsageTurn>("回合用量", async cursor => {
    const page: ThreadUsageReadResponse = await readThreadUsage(threadId, view, cursor);
    if (!valid()) throw new Error("回合用量读取已过期");
    if (!page || page.threadId !== threadId || page.view !== view || page.source !== "provider-usage"
      || !Array.isArray(page.turns) || !count(page.turnCount) || (page.nextCursor !== null && typeof page.nextCursor !== "string")) {
      throw new Error("内核返回的用量不属于当前会话或格式无法识别");
    }
    if (view === "branch") {
      // 「全部记录」不随位置变化，不读取；旧内核不返回 branch 时保持原有行为。
      const leaf = branchPageLeafOf(page.branch, threadId);
      if (leaf === "invalid") throw new Error("内核返回的用量位置信息不属于当前会话或无法识别");
      if (leaf !== "missing") leaves.push(leaf.leafTurnId);
    }
    lastTurnCount = page.turnCount;
    head ??= page;
    summaryTasks ??= bucketOf(page.summaryTasks);
    totals ??= bucketOf(page.totals);
    if (!summaryTasks || !totals) throw new Error("内核返回的用量汇总格式无法识别");
    const pageMeta = page.summaryJobs === undefined ? null : summaryJobsOf(page);
    summaryMeta ??= pageMeta;
    const waste = cacheWasteOf(page.cacheWaste);
    if (waste === null) throw new Error("内核返回的缓存未命中统计格式无法识别");
    cacheWaste ??= waste;
    const turns: ThreadUsageTurn[] = [];
    for (const item of page.turns) {
      const turn = turnOf(item);
      if (!turn) throw new Error("内核返回的回合用量格式无法识别");
      turns.push(turn);
    }
    return { items: turns, nextCursor: page.nextCursor ?? null };
  }, MAX_PAGES);
  // 回合数相同的两条分支拼在一起既不重复、总数也对得上；先按位置判断，再做条目校验。
  if (!sameLeafAcrossPages(leaves)) throw new Error(USAGE_LEAF_DRIFT);
  // 截断时无法知道后面还有多少条目，只校验已读部分不重复；完整读完时以最后一页的总数为准。
  verifyUsageTurns(reads.items, reads.truncated ? undefined : lastTurnCount);
  return { threadId, view, turnCount: lastTurnCount ?? head!.turnCount, turns: reads.items, truncated: reads.truncated,
    summaryTasks: summaryTasks!, totals: totals!, ...(summaryMeta ?? {}),
    ...(cacheWaste ? { cacheWaste } : {}) };
}

export function useThreadUsage(threadId: string | null, connected: boolean, supported: boolean, branchViews: boolean, runningIds: ReadonlySet<string>) {
  const [targetId, setTargetId] = useState<string | null>(null);
  const [state, setState] = useState<ThreadUsageState>({ loading: false, error: "", view: "log" });
  const version = useRef(0);
  const latestThread = useRef(threadId);
  latestThread.current = threadId;
  // 目标在打开时固定：通知切换活动会话不能改换读取对象。
  const running = Boolean(targetId && runningIds.has(targetId));
  const current = useRef({ threadId: targetId, connected, supported, view: state.view });
  // 内核未声明 sessionBranchViews 时只读全部记录。
  current.current = { threadId: targetId, connected, supported, view: branchViews ? state.view : "log" };
  const refresh = useCallback(async () => {
    const { threadId: id, connected: up, supported: ok, view } = current.current;
    const mine = ++version.current;
    if (!id || !up || !ok) { setState(previous => ({ ...previous, loading: false, data: undefined })); return; }
    setState(previous => ({ ...previous, loading: true, error: "", data: previous.data?.threadId === id && previous.data.view === view ? previous.data : undefined }));
    try {
      const data = await readAll(id, view, () => version.current === mine);
      if (version.current === mine) setState(previous => ({ ...previous, loading: false, error: "", data }));
    } catch (error) {
      if (version.current === mine) setState(previous => ({ ...previous, loading: false, error: harnessErrorText(error), data: undefined }));
    }
  }, []);
  // 打开目标、切换视图、目标回合开始 / 结束与重新连接时重新读取；关闭时作废未完成的读取。
  useEffect(() => {
    if (targetId === null) { version.current += 1; return; }
    void refresh();
  }, [targetId, connected, supported, branchViews, state.view, running, refresh]);
  // 能力消失时收起；活动会话变化不影响已固定的目标。
  useEffect(() => { if (!supported) setTargetId(null); }, [supported]);
  return {
    isOpen: targetId !== null && supported, targetId,
    state: branchViews || state.view === "log" ? state : { ...state, view: "log" as const },
    open: useCallback((id?: string) => { const next = id ?? latestThread.current; if (next) setTargetId(next); }, []),
    close: useCallback(() => setTargetId(null), []),
    refresh,
    setView: useCallback((view: UsageView) => setState(previous => previous.view === view ? previous : { ...previous, view, data: undefined }), []),
  };
}
