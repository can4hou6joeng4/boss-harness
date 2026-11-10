import type { AutoCompactionPolicy } from "@boss-harness/protocol";

export interface AutoCompactionDraft {
  enabled: boolean;
  triggerPercent: string;
  keepRecentTokens: string;
}

/** 内核默认值尚未读出时的占位草稿；与首次打开面板显示的值一致。 */
export const DEFAULT_AUTO_COMPACTION_DRAFT: AutoCompactionDraft = { enabled: true, triggerPercent: "80", keepRecentTokens: "20000" };

export const autoCompactionDraftFrom = (
  policy: Pick<AutoCompactionPolicy, "enabled" | "triggerPercent" | "keepRecentTokens">,
): AutoCompactionDraft => ({ enabled: policy.enabled, triggerPercent: String(policy.triggerPercent), keepRecentTokens: String(policy.keepRecentTokens) });

/**
 * 覆盖被消耗或清除后的草稿。
 *
 * 覆盖只作用于一次发送：消耗后表单必须回到内核默认值，否则面板上方的「内核默认」
 * 与下方输入框长期不一致，用户会把一次性覆盖当成默认值再次应用。内核默认值尚未
 * 读出（读取失败或尚未返回）时回到占位草稿，与首次打开面板的显示保持一致。
 */
export function resetAutoCompactionDraft(
  defaults: Pick<AutoCompactionPolicy, "enabled" | "triggerPercent" | "keepRecentTokens"> | undefined,
): AutoCompactionDraft {
  return defaults ? autoCompactionDraftFrom(defaults) : { ...DEFAULT_AUTO_COMPACTION_DRAFT };
}
