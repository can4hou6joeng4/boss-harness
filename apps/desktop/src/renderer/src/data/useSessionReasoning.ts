import { useCallback, useEffect, useRef, useState } from "react";
import type { ThreadReasoningReadResponse } from "@boss-harness/protocol";
import { harnessErrorText, readThreadReasoning, setThreadReasoning } from "./harnessBridge";
import { reasoningTarget } from "./reasoningControl";

export interface SessionReasoningControl {
  data: ThreadReasoningReadResponse | null;
  pending: boolean;
  error: string;
  refresh: () => Promise<void>;
  select: (effort: string | null) => Promise<void>;
}

interface ReasoningState {
  data: ThreadReasoningReadResponse | null;
  pending: boolean;
  error: string;
}

const initial = (): ReasoningState => ({ data: null, pending: false, error: "" });

/**
 * 会话推理档位的读取结果、保存在途锁与失败原因按会话保留在应用生命周期内。
 *
 * 输入区与模型菜单会随通知切换会话卸载；如果保存在途锁只存在单例 hook 中，
 * 切换会把它连同错误一起重置：原 `thread/reasoning/set` 仍在途却可再次提交，
 * 后台失败的原因也不可见。异步回执由发起时的会话持有，切换只改变展示的会话，
 * 不取消写入或遗忘回执；迟到结果不能清除另一个会话的状态。
 */
export function useSessionReasoning(threadId: string | null, connected: boolean): SessionReasoningControl {
  const [states, setStates] = useState<Record<string, ReasoningState>>({});
  const stateRef = useRef(states);
  stateRef.current = states;
  const current = useRef({ threadId, connected });
  current.current = { threadId, connected };
  // 连接代际：断连或重连后，旧连接上的读取与保存回执不再结算。
  const epoch = useRef(0);
  // 每个会话的读取版本：同一会话的迟到读取不能覆盖更新的一次。
  const readVersions = useRef(new Map<string, number>());
  // 每个会话同一时间只允许一个保存请求。
  const saving = useRef(new Set<string>());
  const update = useCallback((id: string, change: Partial<ReasoningState> | ((state: ReasoningState) => ReasoningState)) => {
    const previous = stateRef.current[id] ?? initial();
    const next = typeof change === "function" ? change(previous) : { ...previous, ...change };
    stateRef.current = { ...stateRef.current, [id]: next };
    setStates(stateRef.current);
  }, []);

  /** 读取并校验一个会话的推理设置；成功时按需清除该会话的失败原因。 */
  const load = useCallback(async (id: string, clearError: boolean): Promise<ThreadReasoningReadResponse> => {
    const connectionEpoch = epoch.current;
    const version = (readVersions.current.get(id) ?? 0) + 1;
    readVersions.current.set(id, version);
    const valid = () => epoch.current === connectionEpoch && readVersions.current.get(id) === version;
    try {
      const result = await readThreadReasoning(id);
      if (result.threadId !== id || !Array.isArray(result.availableEfforts)
        || result.availableEfforts.some(effort => typeof effort !== "string")
        || (result.effort !== null && typeof result.effort !== "string")) throw new Error("推理设置响应无效");
      if (valid()) update(id, state => ({ ...state, data: result, error: clearError ? "" : state.error }));
      return result;
    } catch (cause) {
      if (valid()) update(id, state => ({ ...state, error: `无法读取会话推理设置：${harnessErrorText(cause)}。请重新连接或重新加载会话后再试。` }));
      throw cause;
    }
  }, [update]);

  const refresh = useCallback(async () => {
    const { threadId: id, connected: available } = current.current;
    // 断连时不能静默返回：用户点了「重新加载」，必须知道为什么没有变化。
    const target = reasoningTarget("读取", id, available);
    if (!target.ok) { if (id) update(id, { error: target.notice }); return; }
    try { await load(target.threadId, true); } catch { /* 原因已写入该会话状态 */ }
  }, [load, update]);

  // 通知切换只改变展示的会话；每个会话首次进入时读取自己的设置，不重置其他会话。
  useEffect(() => {
    if (threadId && connected) void load(threadId, false).catch(() => { /* 原因已写入该会话状态 */ });
  }, [threadId, connected, load]);

  useEffect(() => {
    const unsubscribe = window.boss?.onNotification(raw => {
      const event = raw as { method?: string; params?: { threadId?: string } };
      const id = event.params?.threadId;
      if (!id || !current.current.connected) return;
      if (!["thread/reasoning/updated", "thread/model/updated", "turn/started", "turn/completed", "context/compactionStarted", "context/compactionCompleted", "context/compactionFailed"].includes(event.method ?? "")) return;
      // 当前会话与仍在保存的会话都需要刷新；其他会话切回时会自行读取。
      if (id !== current.current.threadId && !saving.current.has(id)) return;
      void load(id, false).catch(() => { /* 原因已写入该会话状态 */ });
    });
    return () => unsubscribe?.();
  }, [load]);

  // 断连后旧连接上的请求不会再有回执：解除在途锁，避免重连后一直显示保存中。
  useEffect(() => {
    if (connected) return;
    epoch.current += 1;
    saving.current.clear();
    for (const id of Object.keys(stateRef.current)) update(id, state => ({ ...state, pending: false }));
  }, [connected, update]);

  const currentState = threadId ? states[threadId] : undefined;
  const summaryData = currentState?.data;
  useEffect(() => {
    // Completion notifications precede worker/abort retirement. Re-read until
    // the retained summary model no longer restricts the session's choices.
    if (!connected || !threadId || !summaryData || summaryData.threadId !== threadId || !summaryData.summaryActive) return;
    const timer = setTimeout(() => { void load(threadId, false).catch(() => { /* 原因已写入该会话状态 */ }); }, 1000);
    return () => clearTimeout(timer);
  }, [summaryData, threadId, connected, load]);

  const select = useCallback(async (effort: string | null) => {
    const { threadId: id, connected: available } = current.current;
    // 档位按钮在 Composer 里没有按连接状态禁用，断连时点击必须给出可见原因。
    const target = reasoningTarget("保存", id, available);
    if (!target.ok) { if (id) update(id, { error: target.notice }); return; }
    if (saving.current.has(target.threadId)) return;
    const connectionEpoch = epoch.current;
    saving.current.add(target.threadId);
    update(target.threadId, { pending: true, error: "" });
    try {
      await setThreadReasoning(target.threadId, effort);
      if (epoch.current !== connectionEpoch) return;
      await load(target.threadId, true);
    } catch (cause) {
      if (epoch.current !== connectionEpoch) return;
      try {
        const actual = await load(target.threadId, false);
        if (epoch.current === connectionEpoch) {
          // 档位已经是目标值：保存实际成功，只是回执或首次回读失败；清除本轮读取错误。
          update(target.threadId, actual.effort === effort
            ? { error: "" }
            : { error: `设置未确认：${harnessErrorText(cause)}。请核对当前档位后再选择；没有自动重试。` });
        }
      } catch (verifyError) {
        if (epoch.current === connectionEpoch) {
          update(target.threadId, { error: `设置结果待核对：${harnessErrorText(cause)}；读取当前档位也失败（${harnessErrorText(verifyError)}）。重新连接后请核对；没有自动重试。` });
        }
      }
    } finally {
      if (epoch.current === connectionEpoch) {
        saving.current.delete(target.threadId);
        update(target.threadId, { pending: false });
      }
    }
  }, [load, update]);

  const state = threadId ? states[threadId] ?? initial() : initial();
  return {
    data: connected && state.data?.threadId === threadId ? state.data : null,
    pending: state.pending,
    error: state.error,
    refresh,
    select,
  };
}
