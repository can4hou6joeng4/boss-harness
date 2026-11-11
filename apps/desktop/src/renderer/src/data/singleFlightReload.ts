/**
 * 单飞读取 + 尾随合并。
 *
 * 轮询、聚焦、页面重新可见与通知防抖共用一个读取动作时，读取在途期间的调用不能直接
 * 丢弃：那次调用往往对应一次内核状态变化，丢掉会让徽标停在旧值直到下一次轮询。
 * 这里只保留一个「结束后再读一次」的标记，避免并发请求，同时保证最后一次变化一定被读到。
 */
export interface SingleFlightReload {
  /** 请求一次读取；在途时只记录尾随标记，结束后补跑。 */
  run(): void;
  /** 卸载：不再补跑；已经在途的读取由调用方决定是否丢弃结果。 */
  cancel(): void;
}

export function createSingleFlightReload(
  task: () => Promise<void>,
  canRun: () => boolean = () => true,
): SingleFlightReload {
  let inFlight = false;
  let pending = false;
  let cancelled = false;
  const run = (): void => {
    if (cancelled || !canRun()) return;
    if (inFlight) {
      pending = true;
      return;
    }
    inFlight = true;
    let flight: Promise<void>;
    try {
      flight = task();
    } catch {
      // 同步抛错也要释放单飞标记，否则后续刷新会被永久挡住。
      flight = Promise.resolve();
    }
    void flight.catch(() => {
      // 读取失败保留上一次结果；是否提示由调用方的状态决定。
    }).finally(() => {
      inFlight = false;
      if (cancelled || !pending) return;
      pending = false;
      run();
    });
  };
  return {
    run,
    cancel() {
      cancelled = true;
      pending = false;
    },
  };
}
