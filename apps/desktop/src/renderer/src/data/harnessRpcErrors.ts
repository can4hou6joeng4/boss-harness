/**
 * 渲染层统一解包主进程保留的内核错误。
 *
 * `window.boss.request` 是原始 IPC，主进程对 `preservesRpcError` 方法返回
 * `__harnessRpcError` 而不是抛错；调用方若不解包会把错误对象误当成功响应。
 */
export interface HarnessRpcErrorShape extends Error {
  name: "HarnessRpcError";
  code: number;
  data: unknown;
  rpcError: true;
}

export function throwIfHarnessRpcError<T>(response: T): T {
  if (!response || typeof response !== "object" || !("__harnessRpcError" in response)) return response;
  const rpc = (response as { __harnessRpcError?: unknown }).__harnessRpcError;
  if (!rpc || typeof rpc !== "object") return response;
  const { code, message, data } = rpc as { code?: unknown; message?: unknown; data?: unknown };
  if (typeof code !== "number" || typeof message !== "string") return response;
  const error = new Error(message) as HarnessRpcErrorShape;
  error.name = "HarnessRpcError";
  error.code = code;
  error.data = data;
  error.rpcError = true;
  throw error;
}
