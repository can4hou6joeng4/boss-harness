import { useState, useSyncExternalStore } from "react";

/**
 * 审批提交状态按会话保留在应用生命周期内。
 *
 * 对话区会随通知切换会话卸载。在途锁、失败原因、已提交标记与「记住选择」
 * 如果只存在组件里，切回后就无法判断上一次提交是否仍在进行、是否失败，
 * 还可能对同一条审批重复发出裁决。异步结果由发起时的会话持有：即使没有
 * 组件订阅，迟到回执也会写入对应会话的缓存，下一次进入时如实展示。
 */
export interface ApprovalSubmissionState {
  /** 正在提交的审批卡消息；同一会话同一时间只允许一张卡提交。 */
  pendingMessageId: string | null;
  /** 最近一次提交的未确认或拒绝原因；重新提交时清除。 */
  error: string;
  /** 「本次会话记住选择」按审批卡消息保存，通知切换后仍保留。 */
  remember: Record<string, boolean>;
}

function createSubmissions() {
  let state: ApprovalSubmissionState = { pendingMessageId: null, error: "", remember: {} };
  const listeners = new Set<() => void>();
  const update = (next: ApprovalSubmissionState) => {
    if (next === state) return;
    state = next;
    for (const listener of listeners) listener();
  };
  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    /** 同步持有锁：回执到达前，任何新挂载的组件都不能再次提交。 */
    begin: (messageId: string) => update({ ...state, pendingMessageId: messageId, error: "" }),
    /** 只结算发起时的那张卡；迟到结果不能改写另一条审批的锁。 */
    settle: (messageId: string, error: string) => {
      if (state.pendingMessageId !== messageId) return;
      update({ ...state, pendingMessageId: null, error });
    },
    setRemember: (messageId: string, checked: boolean) => {
      const remember = { ...state.remember };
      if (checked) remember[messageId] = true; else delete remember[messageId];
      update({ ...state, remember });
    },
  };
}

const submissions = new Map<string, ReturnType<typeof createSubmissions>>();

/** 异步回执与组件生命周期无关：按会话取同一个实例结算。 */
export function approvalSubmissionFor(threadId: string) {
  const existing = submissions.get(threadId);
  if (existing) return existing;
  const created = createSubmissions();
  submissions.set(threadId, created);
  return created;
}

export function useApprovalSubmission(threadId?: string) {
  // 未关联会话时沿用组件自身生命周期，不把匿名预览的状态混进会话缓存。
  const [local] = useState(createSubmissions);
  const store = threadId ? approvalSubmissionFor(threadId) : local;
  const state = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { ...state, setRemember: store.setRemember, getState: store.getSnapshot };
}
