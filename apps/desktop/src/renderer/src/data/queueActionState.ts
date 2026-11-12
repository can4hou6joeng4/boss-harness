import { useState, useSyncExternalStore } from "react";

/**
 * 队列重新排队与撤回的在途状态按会话保留在应用生命周期内。
 *
 * 对话区会随通知切换会话卸载。在途锁、失败原因与待核对提示如果只存在面板里，
 * 切回后就无法判断上一次写操作是否仍在进行，还可能对同一条队列项再次提交。
 * 异步结果由发起时的会话持有：即使没有组件订阅，迟到回执也会写入对应会话的
 * 缓存，下一次进入时如实展示。
 */
export interface QueueActionState {
  /** 正在重新排队的队列项；与撤回共用同一把会话级锁。 */
  pendingRetryId: string | null;
  /** 正在撤回的队列项；同一会话同一时间只允许一个队列写操作。 */
  pendingRemoveId: string | null;
  /** 面板级提示：刷新、读取或重新排队的失败与待核对原因。 */
  error: string;
  /** 撤回确认框的提示；确认框未打开时并入面板级提示，避免背景失败不可见。 */
  removeMessage: string;
}

function createActions() {
  let state: QueueActionState = { pendingRetryId: null, pendingRemoveId: null, error: "", removeMessage: "" };
  const listeners = new Set<() => void>();
  const update = (next: QueueActionState) => {
    if (next === state) return;
    state = next;
    for (const listener of listeners) listener();
  };
  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    /** 同步持有锁：回执到达前，任何新挂载的面板都不能再次提交。 */
    beginRetry: (itemId: string) => update({ ...state, pendingRetryId: itemId, error: "", removeMessage: "" }),
    /** 只结算发起时的那次操作；迟到结果不能改写另一条队列项的锁。 */
    settleRetry: (itemId: string, error: string) => {
      if (state.pendingRetryId !== itemId) return;
      update({ ...state, pendingRetryId: null, error });
    },
    beginRemove: (itemId: string) => update({ ...state, pendingRemoveId: itemId, error: "", removeMessage: "" }),
    settleRemove: (itemId: string, removeMessage: string) => {
      if (state.pendingRemoveId !== itemId) return;
      update({ ...state, pendingRemoveId: null, removeMessage });
    },
    setError: (error: string) => update({ ...state, error }),
    setRemoveMessage: (removeMessage: string) => update({ ...state, removeMessage }),
  };
}

const actions = new Map<string, ReturnType<typeof createActions>>();

/** 异步回执与组件生命周期无关：按会话取同一个实例结算。 */
export function queueActionsFor(threadId: string) {
  const existing = actions.get(threadId);
  if (existing) return existing;
  const created = createActions();
  actions.set(threadId, created);
  return created;
}

export function useQueueActions(threadId?: string) {
  // 未关联会话时沿用组件自身生命周期，不把匿名面板的状态混进会话缓存。
  const [local] = useState(createActions);
  const store = threadId ? queueActionsFor(threadId) : local;
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { ...state, getState: store.getSnapshot, beginRetry: store.beginRetry, settleRetry: store.settleRetry,
    beginRemove: store.beginRemove, settleRemove: store.settleRemove, setError: store.setError, setRemoveMessage: store.setRemoveMessage };
}
