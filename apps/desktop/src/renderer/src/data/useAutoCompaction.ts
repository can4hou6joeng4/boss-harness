import { useCallback, useEffect, useRef, useState } from "react";
import type { AutoCompactionPolicy, TurnAutoCompactionOverride } from "@boss-harness/protocol";
import { harnessErrorText, readConfig } from "./harnessBridge";
import { DEFAULT_AUTO_COMPACTION_DRAFT, autoCompactionDraftFrom as draftFrom, resetAutoCompactionDraft, type AutoCompactionDraft } from "./compactionDraft";

export type { AutoCompactionDraft } from "./compactionDraft";
interface PendingOverride {
  threadId: string;
  policy: TurnAutoCompactionOverride;
}
const policyValue = (value: unknown): AutoCompactionPolicy | null => {
  const policy = value as AutoCompactionPolicy | undefined;
  if (!policy || typeof policy.enabled !== "boolean" ||
    !Number.isSafeInteger(policy.triggerPercent) || policy.triggerPercent < 1 || policy.triggerPercent > 100 ||
    !Number.isSafeInteger(policy.keepRecentTokens) || policy.keepRecentTokens < 1 || policy.keepRecentTokens > 1_000_000) return null;
  return policy;
};

/**
 * 下一回合自动压缩覆盖：草稿只影响「应用到下一回合」后的那一次发送。
 *
 * 覆盖值保存在 App 生命周期内，因此关闭面板不会丢失，但不会写入会话或全局配置；
 * 发送请求后立即消耗，无论回执是否已知都不再自动重发。
 */
export function useAutoCompaction(threadId: string | null, open: boolean, connected: boolean) {
  const [defaults, setDefaults] = useState<AutoCompactionPolicy>();
  const [override, setOverride] = useState<PendingOverride | null>(null);
  const overrideRef = useRef<PendingOverride | null>(null);
  const lastThread = useRef<string | null>(null);
  const seededFor = useRef<string | null>(null);
  // 每次用户改动草稿都递增；读取默认值的回执只在不晚于读取起点时才能覆盖草稿。
  const editVersion = useRef(0);
  const [draft, setDraft] = useState<AutoCompactionDraft>(DEFAULT_AUTO_COMPACTION_DRAFT);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { overrideRef.current = override; }, [override]);

  // 会话切换时回到内核默认草稿；已应用的覆盖只属于原会话。
  useEffect(() => {
    if (lastThread.current === threadId) return;
    lastThread.current = threadId;
    seededFor.current = null;
    const pending = overrideRef.current;
    setDraft(pending && pending.threadId === threadId ? draftFrom(pending.policy) : DEFAULT_AUTO_COMPACTION_DRAFT);
    setError("");
  }, [threadId]);

  // 打开面板时读取一次内核默认值；不覆盖已应用的本会话覆盖草稿。
  useEffect(() => {
    if (!open || !connected || !threadId) return;
    let cancelled = false;
    const versionAtStart = editVersion.current;
    setReading(true);
    readConfig().then(config => {
      if (cancelled) return;
      const policy = policyValue(config.autoCompaction);
      if (!policy) {
        setError("当前内核未返回自动压缩默认值；仍可显式设置本回合覆盖。");
        return;
      }
      setDefaults(policy);
      setError("");
      // 首次读取才用默认值填充草稿；关闭再打开不覆盖用户尚未应用的编辑。
      // 读取期间表单仍可编辑，回执晚于用户改动时保留草稿，只更新上方展示的内核默认值。
      if (seededFor.current !== threadId) {
        seededFor.current = threadId;
        if (editVersion.current === versionAtStart) {
          const pending = overrideRef.current;
          setDraft(pending && pending.threadId === threadId ? draftFrom(pending.policy) : draftFrom(policy));
        }
      }
    }).catch(cause => {
      // 默认值读取失败时用户仍可手动设置；保留断连、超时或内核错误码，才知道是重连还是改配置。
      if (!cancelled) setError(`读取自动压缩默认值失败：${harnessErrorText(cause)}；仍可显式设置本回合覆盖。`);
    }).finally(() => {
      if (!cancelled) setReading(false);
    });
    return () => { cancelled = true; };
  }, [open, connected, threadId]);

  const trigger = Number(draft.triggerPercent), keep = Number(draft.keepRecentTokens);
  const valid = Number.isSafeInteger(trigger) && trigger >= 1 && trigger <= 100
    && Number.isSafeInteger(keep) && keep >= 1 && keep <= 1_000_000;

  const setEnabled = useCallback((enabled: boolean) => { editVersion.current += 1; setDraft(previous => ({ ...previous, enabled })); }, []);
  const setTriggerPercent = useCallback((value: string) => { editVersion.current += 1; setDraft(previous => ({ ...previous, triggerPercent: value })); }, []);
  const setKeepRecentTokens = useCallback((value: string) => { editVersion.current += 1; setDraft(previous => ({ ...previous, keepRecentTokens: value })); }, []);

  const apply = useCallback(() => {
    if (!threadId) return;
    if (!Number.isSafeInteger(trigger) || trigger < 1 || trigger > 100) {
      setError("触发阈值必须是 1 到 100 的整数百分比。");
      return;
    }
    if (!Number.isSafeInteger(keep) || keep < 1 || keep > 1_000_000) {
      setError("近期保留目标必须是 1 到 1000000 的整数 token。");
      return;
    }
    const next = { threadId, policy: { enabled: draft.enabled, triggerPercent: trigger, keepRecentTokens: keep } };
    overrideRef.current = next;
    setOverride(next);
    setError("");
  }, [threadId, draft.enabled, trigger, keep]);

  const clear = useCallback(() => {
    overrideRef.current = null;
    setOverride(null);
    setError("");
    // 内核默认值缺失时也复位，避免表单停留在已被清除的覆盖值上。
    seededFor.current = null;
    setDraft(resetAutoCompactionDraft(defaults));
  }, [defaults]);

  /** 取出并消耗本会话待应用的覆盖；发送失败或回执未知时也视为已消耗。 */
  const take = useCallback((id: string): TurnAutoCompactionOverride | undefined => {
    const pending = overrideRef.current;
    if (!pending || pending.threadId !== id) return undefined;
    overrideRef.current = null;
    setOverride(null);
    // 覆盖已随这次发送消耗：表单回到内核默认值，并清掉首次填充标记，下次打开时重新读取。
    seededFor.current = null;
    setDraft(resetAutoCompactionDraft(defaults));
    return pending.policy;
  }, [defaults]);

  return {
    defaults, draft, reading, error, valid,
    active: override && override.threadId === threadId ? override.policy : undefined,
    setEnabled, setTriggerPercent, setKeepRecentTokens, apply, clear, take,
  };
}

export type AutoCompactionController = ReturnType<typeof useAutoCompaction>;
