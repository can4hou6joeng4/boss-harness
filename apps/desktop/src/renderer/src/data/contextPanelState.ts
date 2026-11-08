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
export function disconnectPatch(state: DisconnectState): DisconnectPatch {
  return {
    plan: undefined, reading: false, planning: false, starting: false, cancelInFlight: false,
    turnActive: false,
    error: state.unknownStart ? "开始压缩的回执未知。重连后只核对原任务，不会重复开始。"
      : state.job?.status === "running" ? "连接已断开，摘要任务状态待核对。" : state.error,
  };
}
