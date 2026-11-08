/**
 * 界面统一的时间格式。
 *
 * 桌面界面的文案固定为简体中文，时间不能跟随系统区域：在英文或其他区域的机器上，
 * `Date#toLocaleString()` 会给出 `11/5/2026, 4:00:00 PM` 这类格式，与界面其余文案
 * 不一致，也让同一个来源时间在资料库与工具卡里显示成两种样子。这里统一按本机时区
 * 输出补零的 `YYYY-MM-DD HH:mm` 与 `HH:mm:ss`，不依赖 ICU 区域数据。日期部分与
 * `@boss-harness/shared` 的 `formatLocalDate` 共用同一实现。
 */

import { formatLocalDate, parseIsoDateTime } from "@boss-harness/shared";

/** 严格 ISO 解析与共享工具保持同一实现；桌面各数据层从本模块统一引用。 */
export { parseIsoDateTime };

const pad = (part: number) => String(part).padStart(2, "0");

/** 本机时区的完整日期时间：`YYYY-MM-DD HH:mm`；非法 Date 返回空字符串。 */
export function formatLocalDateTime(at: Date): string {
  if (Number.isNaN(at.getTime())) return "";
  return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** 本机时区的时刻：`HH:mm:ss`，用于同一次检查或最近一次刷新；非法 Date 返回空字符串。 */
export function formatLocalClock(at: Date): string {
  if (Number.isNaN(at.getTime())) return "";
  return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;
}

/** 严格解析 ISO 字符串并格式化为本机 `YYYY-MM-DD HH:mm`；无效返回空字符串。 */
export function formatIsoDateTime(value: unknown): string {
  const at = parseIsoDateTime(value);
  return at ? formatLocalDateTime(at) : "";
}

/** 严格解析 ISO 字符串并格式化为本机 `HH:mm:ss`；无效返回空字符串。 */
export function formatIsoClock(value: unknown): string {
  const at = parseIsoDateTime(value);
  return at ? formatLocalClock(at) : "";
}
