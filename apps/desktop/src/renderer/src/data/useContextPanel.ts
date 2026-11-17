import { useCallback, useEffect, useRef, useState } from "react";
import type { ContextCompactJob, ContextReadResponse } from "@boss-harness/protocol";
import { compactionReferenceOf, contextJobOf, manualCompactionJob } from "./contextJob";
import { contextPlanOf, type ContextPlan } from "./contextPlan";
import { contextReadOf } from "./contextRead";
import { disconnectPatch, missingJobPatch, settleReadFlight } from "./contextPanelState";
import { abortContextCompaction, harnessErrorText, planContextCompaction, readContext, readContextCompaction, startContextCompaction } from "./harnessBridge";

interface StartAttempt {
  sourceDigest: string;
  throughTurnId: string;
  priorJobId?: string;
}
export interface ContextPanelState {
  keepRecentTokens: string;
  budget?: ContextReadResponse;
  plan?: ContextPlan;
  job?: ContextCompactJob;
  lifecycleActive: boolean | null;
  reading: boolean;
  planning: boolean;
  starting: boolean;
  cancelRequested: boolean;
  cancelInFlight: boolean;
  turnActive: boolean;
  unknownStart?: StartAttempt;
  unavailableJob?: string;
  discoveryStopped?: boolean;
  startRejection?: string;
  error: string;
}
const initial = (): ContextPanelState => ({ keepRecentTokens: "20000", lifecycleActive: null, reading: false, planning: false, starting: false, cancelRequested: false, cancelInFlight: false, turnActive: false, error: "" });
const terminal = (job: ContextCompactJob) => job.status !== "running";
const rpcResponseError = (error: unknown): error is Error & { rpcError: true; code: number } => Boolean(error && typeof error === "object"
  && (error as { rpcError?: unknown }).rpcError === true && typeof (error as { code?: unknown }).code === "number");
/** App lifetime ownership: closing the view never cancels or forgets an operation. */
export function useContextPanel(threadId: string | null, connected: boolean, runningThreads: ReadonlySet<string>) {
  const [states, setStates] = useState<Record<string, ContextPanelState>>({});
  const stateRef = useRef(states);
  const [isOpen, setIsOpen] = useState(false);
  const current = useRef({ threadId, connected, isOpen, runningThreads });
  current.current = { threadId, connected, isOpen, runningThreads };
  const epoch = useRef(0);
  const alive = useRef(true);
  const revisions = useRef(new Map<string, number>());
  const jobs = useRef(new Map<string, ContextCompactJob>());
  const readFlights = useRef(new Map<string, Promise<void>>());
  const refreshAgain = useRef(new Set<string>());
  const cancelFlights = useRef(new Set<string>());
  const readVersions = useRef(new Map<string, number>());
  const planVersions = useRef(new Map<string, number>());
  const get = useCallback((id: string) => stateRef.current[id] ?? initial(), []);
  const update = useCallback((id: string, change: Partial<ContextPanelState> | ((state: ContextPanelState) => ContextPanelState)) => {
    if (!alive.current) return;
    const previous = stateRef.current[id] ?? initial();
    const next = typeof change === "function" ? change(previous) : { ...previous, ...change };
    stateRef.current = { ...stateRef.current, [id]: next };
    setStates(stateRef.current);
  }, []);
  const applyJob = useCallback((id: string, incoming: ContextCompactJob, adopt = false) => {
    // 分支摘要复用同一任务通道，但属于分支切换面板；本面板不展示、也不能取消它。
    if (!manualCompactionJob(incoming)) return;
    if (incoming.threadId !== id) throw new Error("摘要任务不属于当前会话，已停止关联");
    const known = jobs.current.get(incoming.jobId);
    if (known && (known.threadId !== id || known.sourceDigest !== incoming.sourceDigest || known.throughTurnId !== incoming.throughTurnId)) throw new Error("摘要任务来源不一致，已停止关联");
    // A terminal event wins over a late start/read response for the same job.
    const job = known && terminal(known) ? known : { ...known, ...incoming };
    jobs.current.set(job.jobId, job);
    update(id, state => {
      const attempt = state.unknownStart;
      const matched = attempt && job.reason === undefined && job.jobId !== attempt.priorJobId
        && job.sourceDigest === attempt.sourceDigest && job.throughTurnId === attempt.throughTurnId;
      if (!adopt && state.job && state.job.jobId !== job.jobId && !matched) return state;
      return { ...state, job, plan: undefined, unavailableJob: undefined,
        unknownStart: matched ? undefined : state.unknownStart, starting: matched ? false : state.starting,
        lifecycleActive: true,
        cancelRequested: terminal(job) ? false : state.cancelRequested,
        cancelInFlight: terminal(job) ? false : state.cancelInFlight,
        error: matched ? "" : state.error };
    });
  }, [update]);
  const refresh = useCallback((id: string): Promise<void> => {
    if (!current.current.connected) return Promise.resolve();
    const existing = readFlights.current.get(id);
    if (existing) { refreshAgain.current.add(id); return existing; }
    const connectionEpoch = epoch.current;
    const lifecycleRevision = revisions.current.get(id) ?? 0;
    const version = (readVersions.current.get(id) ?? 0) + 1;
    readVersions.current.set(id, version);
    update(id, { reading: true });
    const valid = () => alive.current && epoch.current === connectionEpoch && readVersions.current.get(id) === version;
    const flight = (async () => {
      try {
        const budget = contextReadOf(await readContext(id), id);
        if (!valid()) return;
        if ((revisions.current.get(id) ?? 0) !== lifecycleRevision) {
          refreshAgain.current.add(id);
          update(id, { budget });
          return;
        }
        const reference = compactionReferenceOf(budget.compactionJob);
        update(id, state => ({ ...state, budget, lifecycleActive: reference === undefined ? null : reference?.active ?? false,
          discoveryStopped: reference === undefined && state.unknownStart ? true : state.discoveryStopped,
          error: state.unknownStart || state.unavailableJob ? state.error : "" }));
        const knownJob = get(id).job;
        if (reference === null) {
          // 内核明确没有保留任务：清理未知开始状态，允许重新生成计划；
          // 保留会让计划与开始按钮永久禁用且没有恢复入口。
          update(id, state => ({ ...state, ...missingJobPatch(state) }));
          return;
        }
        const jobId = reference?.jobId ?? knownJob?.jobId;
        if (!jobId) return;
        try {
          const job = contextJobOf(await readContextCompaction(jobId));
          if (!valid()) return;
          if (!job || job.jobId !== jobId || job.threadId !== id) throw new Error("摘要任务响应归属不一致");
          if ((revisions.current.get(id) ?? 0) !== lifecycleRevision) {
            refreshAgain.current.add(id);
            return;
          }
          const attempt = get(id).unknownStart;
          const compatible = !attempt || (job.reason === undefined && job.jobId !== attempt.priorJobId
            && job.sourceDigest === attempt.sourceDigest && job.throughTurnId === attempt.throughTurnId);
          const manual = manualCompactionJob(job);
          if (reference && compatible && manual) applyJob(id, manual, true);
          else if (knownJob?.jobId === jobId && manual) applyJob(id, manual);
          // result.compactionJob is a historical snapshot; only this independent read owns liveness.
          if ((revisions.current.get(id) ?? 0) !== lifecycleRevision) {
            refreshAgain.current.add(id);
            return;
          }
          update(id, { lifecycleActive: reference === undefined ? null : reference.active });
        } catch (error) {
          if (valid() && rpcResponseError(error) && error.code === -32011) {
            update(id, { unavailableJob: jobId, error: "本地内核已不再保留这个摘要任务；可能由进程重启或记录淘汰造成。不会重放该任务，可基于当前会话重新规划。" });
          } else if (valid()) update(id, { error: `暂时无法核对摘要任务：${harnessErrorText(error)}。原任务编号已保留，可稍后重试。` });
        }
      } catch (error) {
        if (valid()) update(id, { error: `读取上下文失败：${harnessErrorText(error)}` });
      } finally {
        if (valid()) update(id, { reading: false });
      }
    })();
    readFlights.current.set(id, flight);
    void flight.finally(() => {
      if (settleReadFlight(readFlights.current, refreshAgain.current, id, flight)
        && current.current.connected && epoch.current === connectionEpoch) void refresh(id);
    });
    return flight;
  }, [applyJob, get, update]);

  useEffect(() => {
    alive.current = true;
    const unsubscribe = window.boss?.onNotification(event => {
      const params = event.params && typeof event.params === "object" ? event.params as Record<string, unknown> : {};
      if (event.method === "harness/disconnected" || (event.method === "harness/connectionStatus" && params.state !== "ready")) {
        epoch.current += 1;
        readFlights.current.clear();
        refreshAgain.current.clear();
        for (const id of Object.keys(stateRef.current)) update(id, state => ({ ...state, ...disconnectPatch(state) }));
        return;
      }
      if (event.method === "harness/connectionStatus" && params.state === "ready") {
        for (const [id, state] of Object.entries(stateRef.current)) {
          if (state.discoveryStopped) update(id, { discoveryStopped: false });
          if (state.job || state.unknownStart || (current.current.isOpen && id === current.current.threadId)) void refresh(id);
        }
        return;
      }
      const id = typeof params.threadId === "string" ? params.threadId : null;
      if (!id) return;
      // 任务通知载荷同样先收敛展示字段；畸形载荷按不适用丢弃，不能让通知回调抛错。
      let incoming: ContextCompactJob | null = null;
      if (event.method.startsWith("context/compaction")) {
        try { incoming = contextJobOf(params); } catch { incoming = null; }
      }
      if (incoming) {
        revisions.current.set(id, (revisions.current.get(id) ?? 0) + 1);
        update(id, state => ({ ...state, plan: undefined, planning: false, discoveryStopped: false }));
        const manual = manualCompactionJob(incoming);
        if (!manual) {
          // 分支摘要只占用线程；面板打开时刷新占用状态，但不采纳为当前手动摘要任务。
          if (current.current.isOpen && current.current.threadId === id) void refresh(id);
          return;
        }
        try {
          applyJob(id, manual, event.method === "context/compactionStarted");
          if (terminal(manual)) void refresh(id);
        } catch (error) { update(id, { error: harnessErrorText(error) }); }
      }
      if (["turn/started", "turn/completed", "thread/updated", "context/compacted"].includes(event.method)) {
        revisions.current.set(id, (revisions.current.get(id) ?? 0) + 1);
        update(id, state => ({ ...state, plan: undefined, planning: false,
          turnActive: event.method === "turn/started" ? true : ["turn/completed", "thread/updated"].includes(event.method) ? false : state.turnActive }));
        if (current.current.isOpen && current.current.threadId === id) void refresh(id);
      }
    });
    const timer = setInterval(() => {
      if (!current.current.connected) return;
      for (const [id, state] of Object.entries(stateRef.current)) {
        if ((state.unknownStart && !state.discoveryStopped) || state.lifecycleActive === true || (state.job?.status === "running" && !state.unavailableJob)) void refresh(id);
      }
    }, 1500);
    return () => { alive.current = false; unsubscribe?.(); clearInterval(timer); };
  }, [applyJob, refresh, update]);
  useEffect(() => {
    if (connected) {
      for (const [id, state] of Object.entries(stateRef.current)) if (state.job || (state.unknownStart && !state.discoveryStopped) || (isOpen && id === threadId)) {
        if (state.discoveryStopped) update(id, { discoveryStopped: false });
        void refresh(id);
      }
    }
  }, [connected, threadId, isOpen, refresh]);
  useEffect(() => { if (isOpen && threadId && connected) void refresh(threadId); }, [isOpen, threadId, connected, refresh]);

  const changeKeepRecent = useCallback((value: string) => {
    const id = current.current.threadId;
    if (!id) return;
    planVersions.current.set(id, (planVersions.current.get(id) ?? 0) + 1);
    update(id, { keepRecentTokens: value, plan: undefined, planning: false });
  }, [update]);
  const plan = useCallback(async () => {
    const { threadId: id, connected: available, runningThreads: running } = current.current;
    if (!id || !available) return;
    const state = get(id), keepRecentTokens = Number(state.keepRecentTokens);
    const activeJob = state.job?.status === "running" && state.lifecycleActive !== false;
    if (state.planning || state.starting || state.unknownStart || activeJob || state.lifecycleActive === true || state.turnActive || running.has(id) || state.budget?.requestSource === "active") return;
    if (!Number.isSafeInteger(keepRecentTokens) || keepRecentTokens <= 0) { update(id, { error: "近期保留目标必须是正整数" }); return; }
    const connectionEpoch = epoch.current, revision = revisions.current.get(id) ?? 0;
    const version = (planVersions.current.get(id) ?? 0) + 1;
    planVersions.current.set(id, version);
    const valid = () => alive.current && epoch.current === connectionEpoch && planVersions.current.get(id) === version && (revisions.current.get(id) ?? 0) === revision;
    update(id, { planning: true, plan: undefined, error: "", startRejection: undefined });
    try {
      const result = await planContextCompaction({ threadId: id, keepRecentTokens });
      if (!valid()) return;
      // 计划字段直接进入面板渲染：在写入状态前整体校验，畸形回执按生成失败处理。
      const plan = contextPlanOf(result, { threadId: id, keepRecentTokens });
      update(id, { plan });
    } catch (error) { if (valid()) update(id, { error: `无法生成整理计划：${harnessErrorText(error)}` }); }
    finally { if (valid()) update(id, { planning: false }); }
  }, [get, update]);
  const start = useCallback(async () => {
    const { threadId: id, connected: available, runningThreads: running } = current.current;
    if (!id || !available) return;
    const state = get(id), selected = state.plan;
    if (!selected || state.starting || state.unknownStart || (state.job?.status === "running" && state.lifecycleActive !== false) || state.lifecycleActive === true || state.turnActive || running.has(id) || state.budget?.requestSource === "active") return;
    const connectionEpoch = epoch.current;
    const attempt = { sourceDigest: selected.sourceDigest, throughTurnId: selected.throughTurnId, priorJobId: state.budget?.compactionJob?.jobId ?? state.job?.jobId };
    update(id, { starting: true, unknownStart: attempt, discoveryStopped: false, plan: undefined, cancelRequested: false, error: "", startRejection: undefined });
    try {
      const result = await startContextCompaction({ threadId: id, throughTurnId: selected.throughTurnId, sourceDigest: selected.sourceDigest });
      const started = contextJobOf(result);
      if (!alive.current || epoch.current !== connectionEpoch) return;
      if (!started || !manualCompactionJob(started) || started.threadId !== id || started.sourceDigest !== attempt.sourceDigest || started.throughTurnId !== attempt.throughTurnId || started.jobId === attempt.priorJobId) throw new Error("开始压缩的任务响应归属不一致");
      applyJob(id, started, !get(id).job || get(id).job?.jobId === started.jobId);
      update(id, { starting: false, discoveryStopped: false });
      void refresh(id);
    } catch (error) {
      if (!alive.current || epoch.current !== connectionEpoch) return;
      if (rpcResponseError(error)) {
        update(id, currentState => {
          const observedStart = currentState.job && currentState.job.jobId !== attempt.priorJobId
            && currentState.job.reason === undefined && currentState.job.sourceDigest === attempt.sourceDigest
            && currentState.job.throughTurnId === attempt.throughTurnId;
          return { ...currentState, starting: false, unknownStart: undefined,
            plan: undefined, discoveryStopped: false,
            startRejection: observedStart ? undefined : `内核拒绝了本次开始请求：${harnessErrorText(error)}。请刷新预算并生成新计划；没有自动重试。` };
        });
      } else update(id, currentState => ({ ...currentState, starting: false,
        error: currentState.unknownStart ? `开始压缩回执未知：${harnessErrorText(error)}。计划可能过期；先核对原任务，不会剥除来源校验或重复开始。` : currentState.error }));
      void refresh(id);
    }
  }, [applyJob, get, refresh, update]);
  const cancel = useCallback(async () => {
    const { threadId: id, connected: available } = current.current;
    if (!id || !available) return;
    const state = get(id), job = state.job;
    if (!job || terminal(job) || state.lifecycleActive === false || job.reason || state.cancelInFlight || state.unavailableJob) return;
    const connectionEpoch = epoch.current;
    if (cancelFlights.current.has(job.jobId)) return;
    cancelFlights.current.add(job.jobId);
    update(id, { cancelRequested: true, cancelInFlight: true, error: "" });
    try {
      const result = await abortContextCompaction(job.jobId);
      const cancelled = contextJobOf(result);
      if (!alive.current || epoch.current !== connectionEpoch) return;
      if (!cancelled || !manualCompactionJob(cancelled) || cancelled.reason || cancelled.jobId !== job.jobId || cancelled.threadId !== id || cancelled.sourceDigest !== job.sourceDigest) throw new Error("取消回执不属于手动摘要任务");
      applyJob(id, cancelled);
      void refresh(id);
    } catch (error) { if (alive.current && epoch.current === connectionEpoch) update(id, { cancelRequested: false, error: `取消回执未知：${harnessErrorText(error)}。请核对原任务，尚未确认收尾。` }); }
    finally {
      cancelFlights.current.delete(job.jobId);
      if (alive.current && epoch.current === connectionEpoch) update(id, { cancelInFlight: false });
    }
  }, [applyJob, get, refresh, update]);
  const state = threadId ? states[threadId] ?? initial() : initial();
  return { isOpen, open: () => setIsOpen(true), close: () => setIsOpen(false), state, changeKeepRecent, plan, start, cancel,
    refresh: () => threadId ? refresh(threadId) : Promise.resolve(),
    busy: Boolean(threadId && (runningThreads.has(threadId) || state.turnActive)) };
}
