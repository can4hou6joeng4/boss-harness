import type { UsageView } from "./useThreadUsage";

/** 「会话用量」范围单选组的选项顺序，同时用于方向键循环与渲染。 */
export const USAGE_VIEWS: readonly UsageView[] = ["log", "branch"];

/**
 * 方向键在用量范围单选组内的目标视图；其它按键返回 `null`。
 *
 * 按 WAI-ARIA 单选组惯例支持左右与上下方向键并循环移动：从「当前分支」按 → 回到
 * 「全部记录」。只负责计算目标，是否切换、是否移动焦点由调用方决定。
 */
export function usageViewStep(view: UsageView, key: string): UsageView | null {
  const delta = key === "ArrowRight" || key === "ArrowDown" ? 1
    : key === "ArrowLeft" || key === "ArrowUp" ? -1 : 0;
  if (!delta) return null;
  const index = USAGE_VIEWS.indexOf(view);
  if (index < 0) return null;
  return USAGE_VIEWS[(index + delta + USAGE_VIEWS.length) % USAGE_VIEWS.length]!;
}
