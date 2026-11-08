/**
 * 界面统一的时间格式。
 *
 * 桌面界面的文案固定为简体中文，时间不能跟随系统区域：在英文或其他区域的机器上，
 * `Date#toLocaleString()` 会给出 `11/5/2026, 4:00:00 PM` 这类格式，与界面其余文案
 * 不一致，也让同一个来源时间在资料库与工具卡里显示成两种样子。这里统一按本机时区
 * 输出补零的 `YYYY-MM-DD HH:mm` 与 `HH:mm:ss`，不依赖 ICU 区域数据。日期部分与
 * `@boss-harness/shared` 的 `formatLocalDate` 共用同一实现。
 */

import { formatLocalDate } from "@boss-harness/shared";

const pad = (part: number) => String(part).padStart(2, "0");

// 内核输出形如 `2026-11-05T08:00:00.123456+00:00`；演示与导出数据也用 `Z`。
const ISO_DATE_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

/**
 * 严格解析内核与持久记录中的 ISO 日期时间。
 *
 * `Date.parse` 会把 `"1"`、`"2026"`、只有日期的字符串或带空格的本地时间都猜成具体
 * 时刻；这里只接受带秒与时区的完整 ISO 时间，缺失、空白或无法解析时返回 null。
 * 工具来源、回合耗时、用量行与会话排序共用这一判定，同一时间在各界面得到相同结论。
 */
export function parseIsoDateTime(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!ISO_DATE_TIME.test(trimmed)) return null;
  const at = new Date(trimmed);
  return Number.isNaN(at.getTime()) ? null : at;
}

/** 本机时区的完整日期时间：`YYYY-MM-DD HH:mm`。 */
export function formatLocalDateTime(at: Date): string {
  return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** 本机时区的时刻：`HH:mm:ss`，用于同一次检查或最近一次刷新。 */
export function formatLocalClock(at: Date): string {
  return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;
}
