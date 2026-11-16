import { useCallback, useEffect, useRef, useState } from "react";
import type { ContextBranchSummary, ContextBranchSummaryIssue, ContextCompactJob, InitializeResponse, QueueItem, ThreadBranchEndpoint, TurnSummary } from "@boss-harness/protocol";
import { abortContextCompaction, harnessErrorText, listBranchTurns, listQueue, listThreadBranches, readContext, readContextCompaction, setThreadLeaf } from "./harnessBridge";
import { readPagedItems } from "./pagedRead";
import { compactionReferenceOf } from "./contextJob";
import { branchSummariesOf } from "./branchSummaries";
import { branchEndpointOf, branchTurnOf, uniqueTurnIds } from "./branchPages";

/**
 * 会话内分支（只在内核同时声明 sessionLeaf / sessionBranchTree / sessionBranchViews 时启用）。
 * 界面只读分支端点与当前分支回合，切换经 thread/leaf/set；摘要任务复用上下文摘要任务的读取与取消。
 */
export interface BranchSupport { summary: boolean; /** 可读取被放弃分支摘要正文（sessionBranchSummaryRead）。 */ summaryRead: boolean }
export function branchSupport(capabilities?: InitializeResponse["capabilities"]): BranchSupport | null {
  if (capabilities?.sessionLeaf !== true || capabilities.sessionBranchTree !== true || capabilities.sessionBranchViews !== true) return null;
  return { summary: capabilities.sessionBranchSummary === true, summaryRead: capabilities.sessionBranchSummaryRead === true };
}

export interface SessionBranchState {
  loading: boolean;
  loaded: boolean;
  error: string;
  branched: boolean;
  leafTurnId: string | null;
  turnCount: number;
  endpoints: ThreadBranchEndpoint[];
  endpointsTruncated: boolean;
  /** 当前分支上的回合（自根到 leaf）。 */
  turns: TurnSummary[];
  /** 回合过多，界面只载入了前面的若干页；更晚的回合（可能含当前位置）未读取。 */
  turnsTruncated: boolean;
  summaries: ContextBranchSummary[];
  /** 未通过校验、未注入模型上下文的分支摘要条目（内核最多列出 20 条）。 */
  summaryIssues: ContextBranchSummaryIssue[];
  /** 失效条目总数；内核未返回时为已列出的条目数。 */
  summaryIssueCount: number;
  /** 摘要标记（被放弃分支的摘要条目）未能读取的原因；分支端点与切换不受影响。 */
  summaryError: string;
  /** 摘要任务状态读取或轮询失败的原因；事件推送仍然有效，显示的任务状态可能缺失或已过期。 */
  summaryPollError: string;
  summaryJob?: ContextCompactJob;
  switching: boolean;
  switchError: string;
  cancelInFlight: boolean;
}

const initial = (): SessionBranchState => ({ loading: false, loaded: false, error: "", branched: false, leafTurnId: null, turnCount: 0,
  endpoints: [], endpointsTruncated: false, turns: [], turnsTruncated: false, summaries: [], summaryIssues: [], summaryIssueCount: 0,
  summaryError: "", summaryPollError: "", switching: false, switchError: "", cancelInFlight: false });

/**
 * 按会话读取分支控制：弹窗固定目标时，聊天区仍需使用活动会话自己的摘要状态与取消入口，
 * 不能因为弹窗打开而把另一条会话的摘要任务显示到当前聊天上。
 */
export interface BranchThreadControl {
  state: SessionBranchState;
  cancelSummary: () => void;
  dismissSummaryJob: () => void;
}
const MAX_PAGES = 10;
const TERMINAL_TURN = new Set(["completed", "interrupted", "blocked", "error"]);
export const isSettledTurn = (status: string | null | undefined): boolean => Boolean(status && TERMINAL_TURN.has(status));

function rpcDetail(error: unknown): { rpc: boolean; code: number | null; text: string } {
  const value = error && typeof error === "object" ? error as { rpcError?: unknown; code?: unknown } : null;
  const code = value?.rpcError === true && typeof value.code === "number" ? value.code : null;
  // 与界面其他位置一致：harnessErrorText 会剥掉 IPC 包装前缀并自行附上内核错误码。
  return { rpc: code !== null, code, text: harnessErrorText(error) };
}

/** 内核没有这个摘要任务：可能随进程重启丢失，或被任务记录保留窗口淘汰。 */
const JOB_NOT_FOUND = -32011;

function isBranchJob(value: unknown, threadId: string): value is ContextCompactJob {
  if (!value || typeof value !== "object") return false;
  const job = value as ContextCompactJob;
  return job.kind === "branchSummary" && job.threadId === threadId && typeof job.jobId === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(job.jobId)
    && ["running", "completed", "failed", "cancelled"].includes(job.status);
}

/** 切换前的界面侧阻断原因；与内核 thread/leaf/set 的 -32004 拒绝条件对应。 */
export function branchSwitchBlock(options: { connected: boolean; archived: boolean; running: boolean; queueItems: QueueItem[]; compacting: boolean; switching: boolean }): string | null {
  if (!options.connected) return "本地内核未连接，暂不能切换分支。";
  if (options.archived) return "会话已归档，暂不能切换分支：请先在侧栏「已归档」中恢复会话（内核 -32004：请先恢复会话，再切换分支）。";
  if (options.switching) return "正在切换分支，请稍候。";
  if (options.running) return "回合运行中，暂不能切换分支：请先停止或等待回合结束（内核 -32004：请先中断该会话的运行回合）。";
  if (options.compacting) return "正在生成摘要，暂不能切换分支：请等待完成或先取消摘要（内核 -32004：该会话正在生成摘要）。";
  if (options.queueItems.some(item => item.status === "queued" || item.status === "delivering")) {
    return "队列中仍有排队或投递中的消息，暂不能切换分支：请等待投递完成或先撤回（排队消息切换后会自动投递到新分支，界面先行阻断；投递中时内核返回 -32004）。已暂停的消息不会自动投递，可在切换后重新排队或撤回。";
  }
  return null;
}

export function useSessionBranches(threadId: string | null, connected: boolean, support: BranchSupport | null,
  onSwitched: (threadId: string) => Promise<unknown> | void) {
  const [states, setStates] = useState<Record<string, SessionBranchState>>({});
  const stateRef = useRef(states);
  const current = useRef({ threadId, connected, support, onSwitched });
  current.current = { threadId, connected, support, onSwitched };
  // 分支弹窗打开时固定目标；通知切换活动会话不能改换切换与删除摘要的对象。
  const target = useRef<{ threadId: string; connected: boolean; support: BranchSupport } | null>(null);
  useEffect(() => { if (!connected || !support) target.current = null; }, [connected, support]);
  const versions = useRef(new Map<string, number>());
  const pollFailures = useRef(new Map<string, number>());
  const epoch = useRef(0);
  const alive = useRef(true);
  const update = useCallback((id: string, change: Partial<SessionBranchState> | ((state: SessionBranchState) => SessionBranchState)) => {
    if (!alive.current) return;
    const previous = stateRef.current[id] ?? initial();
    const next = typeof change === "function" ? change(previous) : { ...previous, ...change };
    stateRef.current = { ...stateRef.current, [id]: next };
    setStates(stateRef.current);
  }, []);
  const applyJob = useCallback((id: string, job: ContextCompactJob) => {
    update(id, state => {
      const known = state.summaryJob;
      if (known && known.jobId !== job.jobId && known.status === "running" && job.status !== "running") return state;
      // 终态优先于迟到的 running 读取。
      if (known && known.jobId === job.jobId && known.status !== "running") return state;
      return { ...state, summaryJob: { ...(known?.jobId === job.jobId ? known : {}), ...job },
        summaryPollError: "", cancelInFlight: job.status === "running" && known?.jobId === job.jobId ? state.cancelInFlight : false };
    });
  }, [update]);
  /** 内核明确表示任务不存在：缓存的 running 再也不可能变为终态，继续保留会一直阻断切换与新建回合。 */
  const dropMissingJob = useCallback((id: string, jobId: string) => {
    update(id, state => state.summaryJob?.jobId === jobId && state.summaryJob.status === "running"
      ? { ...state, summaryJob: undefined, cancelInFlight: false,
          summaryPollError: "本地内核已不再保留这个摘要任务：可能随进程重启丢失，或被任务记录淘汰；不会自动重放。已清除过期状态，可重新生成摘要。" }
      : state);
  }, [update]);

  const refresh = useCallback(async (id: string): Promise<void> => {
    if (!current.current.connected || !current.current.support) return;
    const version = (versions.current.get(id) ?? 0) + 1;
    versions.current.set(id, version);
    const connectionEpoch = epoch.current;
    const valid = () => alive.current && epoch.current === connectionEpoch && versions.current.get(id) === version;
    update(id, { loading: true });
    try {
      let head: Awaited<ReturnType<typeof listThreadBranches>> | null = null;
      const endpointPage = await readPagedItems("分支列表", async cursor => {
        const page = await listThreadBranches(id, cursor);
        if (!valid()) throw new Error("分支列表读取已过期");
        if (page.threadId !== id || !Array.isArray(page.endpoints)
          || typeof page.branched !== "boolean" || !Number.isSafeInteger(page.turnCount) || page.turnCount < 0
          || (page.leafTurnId !== null && (typeof page.leafTurnId !== "string"
            || page.leafTurnId.length === 0 || page.leafTurnId.length > 200))) {
          throw new Error("分支列表不属于当前会话或格式无法识别");
        }
        // 端点条目直接渲染并作为切换目标；损坏条目不能让弹窗在应用级错误边界里接管界面。
        const endpoints = page.endpoints.map(branchEndpointOf);
        if (endpoints.some(endpoint => endpoint === null)) throw new Error("分支列表包含无法识别的端点");
        head ??= page;
        return { items: endpoints as ThreadBranchEndpoint[], nextCursor: page.nextCursor ?? null };
      }, MAX_PAGES);
      if (!uniqueTurnIds(endpointPage.items)) throw new Error("分支列表包含重复端点");
      const turnPage = await readPagedItems("当前分支回合", async cursor => {
        const page = await listBranchTurns(id, cursor);
        if (!valid()) throw new Error("当前分支回合读取已过期");
        if (page.view !== "branch" || !Array.isArray(page.turns)) throw new Error("当前分支回合响应无效");
        // 其他会话的回合是归属错误，不能静默过滤后展示少一截的列表。
        const turns = page.turns.map(turn => branchTurnOf(turn, id));
        if (turns.some(turn => turn === null)) throw new Error("当前分支回合响应包含无法识别的条目");
        return { items: turns as TurnSummary[], nextCursor: page.nextCursor ?? null };
      }, MAX_PAGES);
      if (!uniqueTurnIds(turnPage.items)) throw new Error("当前分支回合包含重复条目");
      let summaries: ContextBranchSummary[] = [];
      let summaryIssues: ContextBranchSummaryIssue[] = [];
      let summaryIssueCount = 0;
      let summaryError = "";
      let jobId: string | undefined;
      try {
        const context = await readContext(id);
        if (!valid()) return;
        if (context.threadId === id) {
          // 摘要标记由会话区直接渲染；一条损坏条目会让整段会话落入错误边界。
          const read = branchSummariesOf(context.branchSummaries);
          summaries = read.summaries;
          if (read.dropped > 0) {
            summaryError = `有 ${read.dropped} 条摘要标记无法识别，已隐藏；分支端点和切换不受影响。`;
          }
          // 损坏条目不影响有效摘要与切换；但界面不能把「摘要记录失效」显示成「没有生成摘要」。
          summaryIssues = (Array.isArray(context.branchSummaryIssues) ? context.branchSummaryIssues : [])
            .filter(issue => Boolean(issue) && typeof issue === "object"
              && typeof issue.entryId === "string" && typeof issue.reason === "string");
          const total = context.branchSummaryIssueCount;
          summaryIssueCount = typeof total === "number" && Number.isSafeInteger(total) && total >= summaryIssues.length
            ? total : summaryIssues.length;
          const reference = compactionReferenceOf(context.compactionJob);
          if (reference?.active) jobId = reference.jobId;
        }
      } catch (error) {
        // 摘要条目只用于标注，不影响分支列表与切换；但界面不能把「读不到」显示成「没有摘要」。
        summaryError = `摘要标记未能读取：${rpcDetail(error).text}。分支端点和切换不受影响。`;
      }
      // 摘要读取失败时同样要检查版本：读完两个列表后可能已有更新的刷新写入状态，
      // 这里再写会把旧 leaf / 端点覆盖回去，还会清掉新写入的错误与摘要提示。
      if (!valid()) return;
      pollFailures.current.delete(id);
      update(id, state => ({ ...state, loading: false, loaded: true, error: "", branched: head?.branched ?? false,
        leafTurnId: head?.leafTurnId ?? null, turnCount: head?.turnCount ?? 0, endpoints: endpointPage.items,
        endpointsTruncated: endpointPage.truncated, turns: turnPage.items, turnsTruncated: turnPage.truncated, summaries,
        summaryIssues, summaryIssueCount, summaryError, summaryPollError: "" }));
      const known = stateRef.current[id]?.summaryJob;
      const watch = jobId ?? (known?.status === "running" ? known.jobId : undefined);
      if (watch) {
        try {
          const job = await readContextCompaction(watch);
          if (valid() && isBranchJob(job, id)) applyJob(id, job);
        } catch (error) {
          const detail = rpcDetail(error);
          if (!valid()) return;
          if (detail.code === JOB_NOT_FOUND && !jobId) {
            // 内核已不持有该任务，而 context/read 也没有报告活动任务：轮询只会一直失败。
            // 继续保留 running 会永久阻断切换分支与新建回合；清除后新任务仍可由事件重新上报。
            pollFailures.current.delete(id);
            dropMissingJob(id, watch);
            return;
          }
          // 读不到任务详情时面板既没有进度也没有取消入口，不能让人误以为没有任务；之后的轮询或事件会补齐。
          if (jobId) update(id, { summaryPollError: `摘要任务状态未能读取：${detail.text}。可能暂时无法显示进度或取消入口。` });
        }
      }
    } catch (error) {
      if (valid()) update(id, { loading: false, error: `读取分支失败：${rpcDetail(error).text}` });
    }
  }, [applyJob, dropMissingJob, update]);

  useEffect(() => {
    alive.current = true;
    const unsubscribe = window.boss?.onNotification(event => {
      const params = event.params && typeof event.params === "object" ? event.params as Record<string, unknown> : {};
      if (event.method === "harness/disconnected" || (event.method === "harness/connectionStatus" && params.state !== "ready")) {
        epoch.current += 1;
        pollFailures.current.clear();
        for (const id of Object.keys(stateRef.current)) update(id, state => ({ ...state, loading: false, cancelInFlight: false, summaryPollError: "",
          switching: false, switchError: state.switching
            ? "内核连接已变化；请在恢复连接后重新核对分支位置，再决定是否切换。不会自动重试。" : state.switchError }));
        return;
      }
      const id = typeof params.threadId === "string" ? params.threadId : null;
      if (!id || !current.current.support) return;
      if (event.method.startsWith("context/compaction") && isBranchJob(params, id)) {
        applyJob(id, params);
        if (params.status !== "running") void refresh(id);
        return;
      }
      if (["thread/leafChanged", "turn/completed", "thread/updated", "context/compacted"].includes(event.method) && id === current.current.threadId) {
        void refresh(id);
      }
    });
    const timer = setInterval(() => {
      if (!current.current.connected) return;
      for (const [id, state] of Object.entries(stateRef.current)) {
        const job = state.summaryJob;
        const connectionEpoch = epoch.current;
        // 轮询只属于发出时的连接与运行任务：旧任务的迟到 running 不能覆盖新任务，
        // 旧失败也不能累加到新任务或清掉它的提示；终态和断连同样使读取作废。
        const valid = () => alive.current && epoch.current === connectionEpoch
          && stateRef.current[id]?.summaryJob?.jobId === job?.jobId && stateRef.current[id]?.summaryJob?.status === "running";
        if (job?.status === "running") void readContextCompaction(job.jobId).then(next => {
          if (!valid() || !isBranchJob(next, id) || next.jobId !== job.jobId) return;
          applyJob(id, next);
          if (next.status !== "running") void refresh(id);
          pollFailures.current.delete(id);
          if (stateRef.current[id]?.summaryPollError) update(id, { summaryPollError: "" });
        }).catch(error => {
          if (!valid()) return;
          const detail = rpcDetail(error);
          // 内核明确表示任务不存在时，轮询永远等不到终态；不清理就会永久阻断切换与新建回合。
          if (detail.code === JOB_NOT_FOUND) {
            pollFailures.current.delete(id);
            dropMissingJob(id, job.jobId);
            return;
          }
          // 轮询只是补齐事件推送；连续失败时任务状态会停在旧值，不能一直静默。
          const failures = (pollFailures.current.get(id) ?? 0) + 1;
          pollFailures.current.set(id, failures);
          if (failures < 3) return;
          const text = `摘要任务状态未能刷新：${detail.text}。显示的任务状态可能已过期。`;
          if (stateRef.current[id]?.summaryPollError !== text) update(id, { summaryPollError: text });
        });
      }
    }, 2000);
    return () => { alive.current = false; unsubscribe?.(); clearInterval(timer); };
  }, [applyJob, dropMissingJob, refresh, update]);
  useEffect(() => { if (threadId && connected && support) void refresh(threadId); }, [threadId, connected, support, refresh]);

  const switchTo = useCallback(async (turnId: string | null, summarize: boolean): Promise<boolean> => {
    const targetSnapshot = target.current;
    const { threadId: activeId, connected: available, support: supported } = current.current;
    const id = targetSnapshot?.threadId ?? activeId;
    if (!id || !available || !supported) return false;
    if (targetSnapshot && (!targetSnapshot.connected || targetSnapshot.support !== supported)) return false;
    const state = stateRef.current[id] ?? initial();
    if (state.switching) return false;
    const connectionEpoch = epoch.current;
    const valid = () => alive.current && epoch.current === connectionEpoch;
    update(id, { switching: true, switchError: "" });
    let attempted = false;
    try {
      // 目标可能已不在前台，界面上的队列投影属于活动会话；切换前必须重新核对目标自己的队列。
      const queue = await listQueue(id);
      // 预读回执只属于发出时的连接；重连后不能据旧队列状态继续提交切换。
      if (!valid()) return false;
      if (queue.items.some(item => item.status === "queued" || item.status === "delivering")) {
        update(id, { switchError: "队列中仍有排队或投递中的消息，暂不能切换分支：请等待投递完成或先撤回（排队消息切换后会自动投递到新分支）。" });
        return false;
      }
      attempted = true;
      const result = await setThreadLeaf(summarize && supported.summary ? { threadId: id, turnId, summarize: true } : { threadId: id, turnId });
      if (!valid()) return false;
      if (result.threadId !== id || result.leafTurnId !== turnId) throw new Error("切换回执与所选位置不一致");
      if (result.summaryJob && isBranchJob(result.summaryJob, id)) applyJob(id, result.summaryJob);
      await current.current.onSwitched(id);
      // 会话重读也可能跨越重连；旧调用不能把新打开的分支窗口作为成功收起。
      return valid();
    } catch (error) {
      if (!valid()) return false;
      const detail = rpcDetail(error);
      update(id, { switchError: attempted
        ? detail.rpc ? `内核拒绝切换，分支保持不变：${detail.text}` : `切换结果尚未确认：${detail.text}。已重新读取分支状态；不会自动重试。`
        : `未能核对目标会话的队列，分支未切换：${detail.text}` });
      if (attempted && !detail.rpc) await current.current.onSwitched(id);
      return false;
    } finally {
      // 断连时已释放旧操作；旧 finally 不能清除新连接上另一次切换的忙碌状态。
      if (valid()) {
        update(id, { switching: false });
        void refresh(id);
      }
    }
  }, [applyJob, refresh, update]);

  const cancelSummaryFor = useCallback(async (id: string) => {
    const job = stateRef.current[id]?.summaryJob;
    if (!current.current.connected || !job || job.status !== "running" || stateRef.current[id]?.cancelInFlight) return;
    const connectionEpoch = epoch.current;
    // 取消与收尾只属于发起时的连接和任务；旧回执不能替换新任务或释放其取消锁。
    const valid = () => alive.current && epoch.current === connectionEpoch
      && stateRef.current[id]?.summaryJob?.jobId === job.jobId;
    update(id, { cancelInFlight: true });
    try {
      const result = await abortContextCompaction(job.jobId);
      if (!valid()) return;
      if (!isBranchJob(result, id) || result.jobId !== job.jobId) throw new Error("取消摘要回执与当前任务不一致");
      applyJob(id, result);
    } catch (error) {
      // 已确认的终态优先于迟到取消失败，不再把完成任务描述为回执未知。
      if (valid() && stateRef.current[id]?.summaryJob?.status === "running") {
        update(id, { switchError: `取消摘要的回执未知：${rpcDetail(error).text}。请稍后刷新核对。` });
      }
    } finally {
      if (valid()) {
        update(id, { cancelInFlight: false });
        void refresh(id);
      }
    }
  }, [applyJob, refresh, update]);
  const cancelSummary = useCallback(async () => {
    const id = current.current.threadId;
    if (id) await cancelSummaryFor(id);
  }, [cancelSummaryFor]);

  const dismissSummaryJobFor = useCallback((id: string) => {
    update(id, state => state.summaryJob?.status === "running" ? state : { ...state, summaryJob: undefined });
  }, [update]);
  const dismissSummaryJob = useCallback(() => {
    const id = current.current.threadId;
    if (id) dismissSummaryJobFor(id);
  }, [dismissSummaryJobFor]);

  const clearSwitchErrorFor = useCallback((id: string) => update(id, { switchError: "" }), [update]);
  const clearSwitchError = useCallback(() => {
    const id = current.current.threadId;
    if (id) clearSwitchErrorFor(id);
  }, [clearSwitchErrorFor]);

  /** 打开弹窗时固定目标；之后的读取、切换与摘要取消都使用该会话。 */
  const openFor = useCallback((id: string) => {
    const { connected: available, support: supported } = current.current;
    if (!id || !available || !supported) return;
    target.current = { threadId: id, connected: available, support: supported };
    clearSwitchErrorFor(id);
    void refresh(id);
  }, [clearSwitchErrorFor, refresh]);
  const closeTarget = useCallback(() => { target.current = null; }, []);
  const threadControl = (id: string | null): BranchThreadControl => ({
    state: id ? states[id] ?? initial() : initial(),
    cancelSummary: id ? () => { void cancelSummaryFor(id); } : () => {},
    dismissSummaryJob: id ? () => dismissSummaryJobFor(id) : () => {},
  });

  const state = threadId ? states[threadId] ?? initial() : initial();
  return { state, support, refresh: () => threadId ? refresh(threadId) : Promise.resolve(),
    refreshFor: (id: string) => refresh(id), openFor, closeTarget, threadControl,
    switchTo, cancelSummary, dismissSummaryJob, clearSwitchError };
}
export type SessionBranchControl = ReturnType<typeof useSessionBranches>;
