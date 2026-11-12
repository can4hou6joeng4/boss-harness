import { useState, useSyncExternalStore } from "react";

/**
 * 模型线路切换的在途锁与错误按会话保留在应用生命周期内。
 *
 * 输入区会随通知切换会话卸载。切换锁与失败原因如果只存在组件里，切回后
 * 无法判断上一次设置是否仍在进行，还可能对同一会话重复发出设置请求；
 * 后台失败的原因也会随组件一起消失。异步回执由发起时的会话持有：即使
 * 没有组件订阅，迟到结果也会写入对应会话的缓存，下一次打开菜单时如实展示。
 */
export interface ModelSwitchState {
  /** 正在保存该会话的模型线路；同一会话同一时间只允许一个设置请求。 */
  pending: boolean;
  /** 最近一次设置的失败或未确认原因；下一次提交时清除。 */
  error: string;
}

function createSwitches() {
  let state: ModelSwitchState = { pending: false, error: "" };
  let token = 0;
  const listeners = new Set<() => void>();
  const update = (next: ModelSwitchState) => {
    if (next === state) return;
    state = next;
    for (const listener of listeners) listener();
  };
  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    /** 同步持有锁：回执到达前，任何新挂载的菜单都不能再次提交。 */
    begin: (): number | null => {
      if (state.pending) return null;
      token += 1;
      update({ pending: true, error: "" });
      return token;
    },
    /** 只结算发起时的那次设置；迟到结果不能改写后续请求的锁。 */
    settle: (forToken: number, error: string) => {
      if (forToken !== token) return;
      update({ pending: false, error });
    },
  };
}

const switches = new Map<string, ReturnType<typeof createSwitches>>();

/** 异步回执与组件生命周期无关：按会话取同一个实例结算。 */
export function modelSwitchFor(threadId: string) {
  const existing = switches.get(threadId);
  if (existing) return existing;
  const created = createSwitches();
  switches.set(threadId, created);
  return created;
}

export function useModelSwitch(threadId?: string) {
  // 未关联会话时沿用组件自身生命周期，不把匿名预览的状态混进会话缓存。
  const [local] = useState(createSwitches);
  const store = threadId ? modelSwitchFor(threadId) : local;
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { ...state, begin: store.begin, settle: store.settle, getState: store.getSnapshot };
}
