/**
 * 队列读取的先后守卫。
 *
 * 事件通知、手动刷新、提交核对与撤回复核会并发发起 `queue/list`，而本地入队、撤回、编辑
 * 成功后又直接收敛面板。读取返回顺序不保证与发出顺序一致：较早发出的读取若后到，会用
 * 变化前的数据覆盖已撤回 / 已编辑的条目，直到下一次通知才恢复。
 *
 * 这里按会话维护代数：每次发起读取领一个票据，只有票据仍是该会话最新一代时才允许写入；
 * 本地已提交的变更调用 `invalidate` 推进代数，让此前发出的读取全部失效。
 */
export interface QueueReadTicket {
  /** 票据仍是最新一代时执行写入；已被更新读取或本地变更取代时丢弃。 */
  commit(apply: () => void): void;
  /** 票据是否仍是最新一代；用于失败提示等不应覆盖新结果的出口。 */
  isCurrent(): boolean;
}

export interface QueueReadGuard {
  /** 为一次读取领票；同一会话此前发出的票据随即失效。 */
  issue(threadId: string): QueueReadTicket;
  /** 本地已提交的变更：让该会话此前发出的读取全部失效。 */
  invalidate(threadId: string): void;
}

export function createQueueReadGuard(): QueueReadGuard {
  const generations = new Map<string, number>();
  const current = (threadId: string): number => generations.get(threadId) ?? 0;
  const bump = (threadId: string): number => {
    const next = current(threadId) + 1;
    generations.set(threadId, next);
    return next;
  };
  return {
    issue(threadId: string): QueueReadTicket {
      const generation = bump(threadId);
      const isCurrent = (): boolean => current(threadId) === generation;
      return {
        isCurrent,
        commit(apply: () => void): void {
          if (isCurrent()) apply();
        },
      };
    },
    invalidate(threadId: string): void {
      bump(threadId);
    },
  };
}
