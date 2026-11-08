/**
 * 跨包共享的小工具。对应 Codex 的 shared-node。
 */

const pad2 = (part: number) => String(part).padStart(2, "0");

// 内核输出形如 `2026-11-05T08:00:00.123456+00:00`；演示与导出数据也用 `Z`。
const ISO_DATE_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

/**
 * 严格解析内核与持久记录中的 ISO 日期时间。
 *
 * `Date.parse` 会把 `"1"`、`"2026"`、只有日期的字符串或带空格的本地时间都猜成具体
 * 时刻；这里只接受带秒与时区的完整 ISO 时间，缺失、空白或无法解析时返回 null。
 * 桌面时间工具、回合耗时、用量行、会话排序与相对时间共用这一判定。
 */
export function parseIsoDateTime(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!ISO_DATE_TIME.test(trimmed)) return null;
  const at = new Date(trimmed);
  return Number.isNaN(at.getTime()) ? null : at;
}

/**
 * 本机时区的补零日期 `YYYY-MM-DD`。与桌面 `timeFormat` 的日期时间同一约定，
 * 不依赖 ICU 区域数据，避免英文或其他区域给出 `10/9/2026` 一类格式。
 * 非法 Date 返回空字符串，避免界面出现 `NaN-NaN-NaN`。
 */
export function formatLocalDate(at: Date): string {
  if (Number.isNaN(at.getTime())) return "";
  return `${at.getFullYear()}-${pad2(at.getMonth() + 1)}-${pad2(at.getDate())}`;
}

/**
 * 相对时间：不足 1 分钟为「刚刚」，其后按分钟 / 小时 / 天取整；满 30 天回退本机日期
 * `YYYY-MM-DD`。`now` 让调用方与离线验证固定参考时刻，缺省取当前时间。
 * 只接受完整 ISO 时间；坏值返回空字符串，不显示虚构的相对时间。
 */
export function formatRelativeTime(iso: string, now: number = Date.now()): string {
  const at = parseIsoDateTime(iso);
  if (!at) return "";
  const then = at.getTime();
  const reference = Number.isFinite(now) ? now : Date.now();
  const seconds = Math.max(0, Math.floor((reference - then) / 1000));
  if (seconds < 60) return "刚刚";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return formatLocalDate(new Date(then));
}

/**
 * 按 UTF-16 偏移截断，但不切开代理对：边界落在补充平面字符中间时少取一个码元。
 * 长度预算仍按 `String.length` 计算，调用方无需改用码点计数。
 */
export function safeSlice(text: string, end: number): string {
  const limit = Math.min(Math.floor(end), text.length);
  if (!Number.isFinite(limit) || limit <= 0) return "";
  const last = text.charCodeAt(limit - 1);
  return text.slice(0, last >= 0xd800 && last <= 0xdbff ? limit - 1 : limit);
}

export function truncate(text: string, max: number): string {
  if (max <= 0) return "";
  return text.length <= max ? text : `${safeSlice(text, max - 1)}…`;
}

/**
 * 去掉 Electron `ipcRenderer.invoke` 拼接的错误包装，只留下真实原因。
 *
 * 主进程抛出的错误跨 IPC 后只剩 `Error invoking remote method '<channel>': <String(error)>`；
 * `String(error)` 带错误名：普通错误为 `Error: `，本项目的内核 RPC 错误为 `HarnessRpcError: `。
 */
export function stripIpcErrorWrapper(message: string): string {
  return message.replace(/^Error invoking remote method '[^']+': (?:Error|HarnessRpcError): /, "");
}
