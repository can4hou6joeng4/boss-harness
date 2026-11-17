import type { ContextCompactJob } from "@boss-harness/protocol";

interface DisconnectState {
  unknownStart?: unknown;
  job?: ContextCompactJob;
  error: string;
}

export interface DisconnectPatch {
  plan: undefined;
  reading: false;
  planning: false;
  starting: false;
  cancelInFlight: false;
  turnActive: false;
  error: string;
}

/**
 * 连接断开或尚未就绪时，面板里由当前连接推导的易失状态都要复位。
 *
 * `turnActive` 与 App 的 `runningThreadIds` 来自同一事实：宿主断连会关闭旧传输与
 * 内核进程，重连新建进程且不重放通知，旧回合不可能继续运行。这里必须与 App 一起
 * 复位，否则「会话正在运行」会永久挡住手动压缩，直到该会话凑巧再来一个
 * `turn/completed` 或 `thread/updated`。
 *
 * `unknownStart` 与运行中的摘要任务仍保留原有提示，等重连后核对，不重复开始。
 */
/**
 * 读取航班收尾：只有仍持有该会话读取槽位的航班才能清理槽位并消费尾随刷新标记。
 * 断连会清空槽位并开启新 epoch，但断连前的读取不会被取消；旧航班迟到落地时
 * 不得删除或消费重连后新航班登记的刷新请求，否则面板会漏掉一次必要的重读。
 * 返回 true 表示调用方应立即补发读取。
 */
export function settleReadFlight<T>(
  flights: Map<string, T>, pending: Set<string>, id: string, flight: T,
): boolean {
  if (flights.get(id) !== flight) return false;
  flights.delete(id);
  return pending.delete(id);
}

export function disconnectPatch(state: DisconnectState): DisconnectPatch {
  return {
    plan: undefined, reading: false, planning: false, starting: false, cancelInFlight: false,
    turnActive: false,
    error: state.unknownStart ? "开始压缩的回执未知。重连后只核对原任务，不会重复开始。"
      : state.job?.status === "running" ? "连接已断开，摘要任务状态待核对。" : state.error,
  };
}

export interface MissingJobPatch {
  unknownStart: undefined;
  starting: false;
  discoveryStopped: false;
  unavailableJob?: string;
  error: string;
}

/**
 * 内核明确没有保留任务（`context/read.compactionJob === null`）时的状态收敛。
 *
 * 摘要任务只存在于本机内核进程中：记录缺失说明上次开始请求对应的任务已随进程
 * 重启消失或已被淘汰，不可能仍在执行。保留 `unknownStart` 会永久禁用计划与开始
 * 按钮——发现轮询在 `discoveryStopped` 后停止，用户没有任何恢复入口，只能新建
 * 会话。这里把「结果未知」降级为可读说明并允许重新生成计划：旧任务不会再执行，
 * 也不存在与旧任务并发开始的重复压缩。仍在本地运行中的任务（`job.status ===
 * "running"`）仍按不可用处理，不自动清理。
 */
export function missingJobPatch(state: DisconnectState): MissingJobPatch {
  return {
    unknownStart: undefined,
    starting: false,
    discoveryStopped: false,
    ...(state.job?.status === "running" ? { unavailableJob: state.job.jobId } : {}),
    error: state.unknownStart
      ? "本机内核没有保留上次开始压缩对应的任务（可能随进程重启丢失）；旧任务不会再执行，可重新生成计划。"
      : state.job?.status === "running"
        ? "本地内核已不再保留上次运行中的摘要任务；它可能随进程重启丢失，无法恢复。可基于当前会话重新生成计划。"
        : state.error,
  };
}
