import { formatDurationMs } from "@boss-harness/shared";
import { parseIsoDateTime } from "./timeFormat";

/**
 * 回合耗时展示：只用内核返回的开始/完成时间计算，不读取本机时钟，
 * 因此运行中的回合不会因为界面刷新出现持续增长的「已用」数字。
 */
export interface TurnTimingInput {
  startedAt?: string;
  completedAt?: string;
  status?: string;
}

/** 与工具来源、用量行共用严格 ISO 判定；坏时间不参与耗时计算。 */
const parse = (value: string | undefined): number | null => parseIsoDateTime(value)?.getTime() ?? null;

/** 只有两个时间都可解析且结束不早于开始时才给出耗时。 */
export function turnDurationMs(turn: TurnTimingInput): number | null {
  const start = parse(turn.startedAt), end = parse(turn.completedAt);
  return start === null || end === null || end < start ? null : end - start;
}

/** 时长文案与桌面结束通知、内核导出共用 `@boss-harness/shared` 的同一实现。 */
export const formatDuration = formatDurationMs;

/** 回合标签下的耗时说明；无法计算时运行中的回合显示「进行中」，其余返回 null。 */
export function turnTimingLabel(turn: TurnTimingInput): string | null {
  const duration = turnDurationMs(turn);
  if (duration !== null) return `用时 ${formatDuration(duration)}`;
  return turn.status === "running" ? "进行中" : null;
}
