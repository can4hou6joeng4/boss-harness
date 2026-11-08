import type { SessionItem } from "./mockData";
import { parseIsoDateTime } from "./timeFormat";

/**
 * 会话更新时间排序键：只接受完整 ISO 时间。
 *
 * 缺失、空字符串、只有年份或旧版本本地时间都不能被 `Date.parse` 猜成具体时刻；
 * 统一按 0 处理，降序排列时落到列表末尾。侧栏与会话行共用这一判定，避免两处排序
 * 对同一份 `updatedAt` 给出不同顺序。
 */
export function sessionUpdatedAt(session: SessionItem): number {
  return parseIsoDateTime(session.updatedAt)?.getTime() ?? 0;
}
