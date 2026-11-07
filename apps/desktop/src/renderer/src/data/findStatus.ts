/**
 * 聊天内查找的状态文案。
 *
 * 计数单位是「处命中」，与 `findStep` 的跳转单位一致：同一条消息里的多处命中可以逐个
 * 跳转，只报消息数会让用户以为 Enter 没有生效。只有「含详情可命中 N 条消息」按消息数，
 * 因为它说的是去哪些消息里找。
 *
 * 高亮有全局上限：超出后不再收集区间，其后的匹配消息各按一处停靠。此时状态行必须
 * 说明「仅前 N 处高亮」，否则用户会把可停靠数当成真实命中数，也会把没有高亮的跳转
 * 当成查找失效。
 */
import { FIND_HIGHLIGHT_LIMIT } from "./findHighlight";

export interface FindStatusInput {
  /** 查找框原文，可能只有空白。 */
  query: string;
  /** 可跳转的命中处数。每条匹配消息至少一处。 */
  total: number;
  /** 当前位次，从 0 开始；越界时收敛到合法范围。 */
  position: number;
  /**
   * 仅正文没有命中时，勾选「含工具、审批与思考」后能命中的消息数。
   * `undefined` 表示未计算或已勾选详情，此时不给提示。
   */
  detailHits?: number;
  /** 命中处超过高亮上限时为真；此时总数含仅按消息停靠的位置。 */
  capped?: boolean;
  /** 高亮上限，与区间收集共用；缺省取 `FIND_HIGHLIGHT_LIMIT`。 */
  highlightLimit?: number;
}

/**
 * 状态行文字。
 *
 * 正文有命中时不提示详情：此时用户在逐处跳转，插一句「含详情还能命中更多」只会
 * 干扰当前路径；只有正文一无所获时，这句提示才是下一步该做的事。
 */
export function findStatusText(input: FindStatusInput): string {
  if (!input.query.trim()) return "输入关键词";
  const whole = (value: number): number => Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
  const total = whole(input.total);
  if (total > 0) {
    const position = Math.min(whole(input.position), total - 1);
    const limit = whole(input.highlightLimit ?? FIND_HIGHLIGHT_LIMIT);
    return input.capped === true
      ? `第 ${position + 1} / ${total} 处命中 · 仅前 ${limit} 处高亮`
      : `第 ${position + 1} / ${total} 处命中`;
  }
  const detailHits = whole(input.detailHits ?? 0);
  if (detailHits > 0) return `正文无匹配 · 含详情可命中 ${detailHits} 条消息`;
  return "无匹配消息";
}
