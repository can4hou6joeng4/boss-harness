import { useCallback, useEffect, useRef, useState } from "react";
import type { AutoCompactionPolicy, TurnAutoCompactionOverride } from "@boss-harness/protocol";
import { harnessErrorText, readConfig } from "./harnessBridge";
import { DEFAULT_AUTO_COMPACTION_DRAFT, autoCompactionDraftFrom as draftFrom, resetAutoCompactionDraft, type AutoCompactionDraft } from "./compactionDraft";

export type { AutoCompactionDraft } from "./compactionDraft";
const _POLICY_TEXT_LIMIT = 200;
const policyText = (value: unknown): string | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= _POLICY_TEXT_LIMIT ? trimmed : null;
};
/**
 * 自动压缩默认值的自读校验。
 *
 * `config/read` 的回执属于外部输入：`ContextPanel` 把 `defaults.provider` /
 * `model` / `effort` 直接作为 React 子节点渲染，对象、数组或数字不会走 `??`
 * 回退，渲染期抛「Objects are not valid as a React child」；`ContextPanel` 位于
 * 应用级错误边界之下，整个桌面界面会被错误页替换，重试后再次打开面板又会崩溃。
 * 这里与 cockpitData 的同一回执消费方保持一致：线路字段只接受收敛后的非空文本，
 * 其余按「未提供」处理；核心数值字段不合法时整体按默认值缺失处理。
 */
export const autoCompactionPolicyValue = (value: unknown): AutoCompactionPolicy | null => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const policy = value as Record<string, unknown>;
  const triggerPercent = policy.triggerPercent, keepRecentTokens = policy.keepRecentTokens;
  if (typeof policy.enabled !== "boolean"
    || typeof triggerPercent !== "number" || !Number.isSafeInteger(triggerPercent) || triggerPercent < 1 || triggerPercent > 100
    || typeof keepRecentTokens !== "number" || !Number.isSafeInteger(keepRecentTokens)
    || keepRecentTokens < 1 || keepRecentTokens > 1_000_000) return null;
  return {
    enabled: policy.enabled,
    triggerPercent,
    keepRecentTokens,
    provider: policyText(policy.provider),
    model: policyText(policy.model),
    effort: policyText(policy.effort),
  };
};

/**
 * 下一回合自动压缩覆盖：草稿只影响「应用到下一回合」后的那一次发送。
 *
 * 未应用草稿与已应用覆盖都按会话保存在 App 生命周期内，因此关闭面板或切换会话
 * 不会丢失；不会写入会话或全局配置。覆盖在发送请求后立即消耗，无论回执是否已知
 * 都不再自动重发。
 */
export function useAutoCompaction(threadId: string | null, open: boolean, connected: boolean) {
  const [defaults, setDefaults] = useState<AutoCompactionPolicy>();
  // 已应用但尚未被发送消耗的覆盖，按会话 id 分别保留。
  const [overrides, setOverrides] = useState<Record<string, TurnAutoCompactionOverride>>({});
  const overridesRef = useRef(overrides); overridesRef.current = overrides;
  const lastThread = useRef<string | null>(null);
  // 尚未应用的手动改动按会话保留；读取默认值的回执不能覆盖任一草稿。
  const sessionDrafts = useRef(new Map<string, AutoCompactionDraft>());
  // 记录存在未应用手动改动的会话，避免关闭重开、读取失败后重试或重连时的回执覆盖草稿。
  const dirtyThreads = useRef(new Set<string>());
  // 已取出但结果未知的覆盖：明确拒绝时按取出时的标记恢复；期间重新应用、清除或再次取用则不再恢复。
  const consumed = useRef(new Map<string, { policy: TurnAutoCompactionOverride; stamp: number }>());
  const stamps = useRef(new Map<string, number>());
  const stampOf = (id: string) => {
    const next = (stamps.current.get(id) ?? 0) + 1;
    stamps.current.set(id, next);
    return next;
  };
  // 每次用户改动草稿都递增；读取默认值的回执只在不晚于读取起点时才能覆盖草稿。
  const editVersion = useRef(0);
  const [draft, setDraft] = useState<AutoCompactionDraft>(DEFAULT_AUTO_COMPACTION_DRAFT);
  const draftRef = useRef(draft); draftRef.current = draft;
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");

  // 删除通知先于删除回执：移除该会话的未应用草稿、已应用覆盖与改动标记，
  // 避免删除未被确认时重新打开会话看到删除前的覆盖；同时作废在途默认值读取。
  useEffect(() => {
    const unsubscribe = window.boss?.onNotification(event => {
      const params = event.params && typeof event.params === "object" ? event.params as Record<string, unknown> : {};
      if (event.method !== "thread/deleted" || typeof params.deletedThreadId !== "string") return;
      const id = params.deletedThreadId;
      if (!id) return;
      sessionDrafts.current.delete(id);
      dirtyThreads.current.delete(id);
      consumed.current.delete(id);
      stamps.current.delete(id);
      editVersion.current += 1;
      if (lastThread.current === id) {
        const reset = resetAutoCompactionDraft(undefined);
        draftRef.current = reset;
        setDraft(reset);
        setError("");
      }
      setOverrides(previous => {
        if (!Object.prototype.hasOwnProperty.call(previous, id)) return previous;
        const next = { ...previous };
        delete next[id];
        return next;
      });
    });
    return () => unsubscribe?.();
  }, []);

  // 会话切换时显示该会话自己的未应用草稿、已应用覆盖或内核默认值。
  useEffect(() => {
    if (lastThread.current === threadId) return;
    lastThread.current = threadId;
    const saved = threadId ? sessionDrafts.current.get(threadId) : undefined;
    const pending = threadId ? overridesRef.current[threadId] : undefined;
    const next = saved ?? (pending ? draftFrom(pending) : DEFAULT_AUTO_COMPACTION_DRAFT);
    draftRef.current = next;
    setDraft(next);
    setError("");
  }, [threadId]);

  // 打开面板时读取最新内核默认值；只在没有未应用草稿且读取期间未编辑时才同步表单。
  useEffect(() => {
    // 面板关闭、断连或未选中会话时没有在途读取，复位读取态后再返回。
    if (!open || !connected || !threadId) { setReading(false); return; }
    let cancelled = false;
    const versionAtStart = editVersion.current;
    setReading(true);
    readConfig().then(config => {
      if (cancelled) return;
      const policy = autoCompactionPolicyValue(config.autoCompaction);
      if (!policy) {
        setError("当前内核未返回自动压缩默认值；仍可显式设置本回合覆盖。");
        return;
      }
      setDefaults(policy);
      setError("");
      // 读取期间、失败后或关闭再打开期间的未应用编辑均保留；仅更新上方展示的内核默认值。
      if (editVersion.current === versionAtStart && !dirtyThreads.current.has(threadId)) {
        const pending = overridesRef.current[threadId];
        const next = pending ? draftFrom(pending) : draftFrom(policy);
        draftRef.current = next;
        setDraft(next);
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

  const updateDraft = useCallback((transform: (previous: AutoCompactionDraft) => AutoCompactionDraft) => {
    editVersion.current += 1;
    const next = transform(draftRef.current);
    draftRef.current = next;
    if (threadId) {
      dirtyThreads.current.add(threadId);
      sessionDrafts.current.set(threadId, next);
    }
    setDraft(next);
  }, [threadId]);

  const setEnabled = useCallback((enabled: boolean) => { updateDraft(previous => ({ ...previous, enabled })); }, [updateDraft]);
  const setTriggerPercent = useCallback((value: string) => { updateDraft(previous => ({ ...previous, triggerPercent: value })); }, [updateDraft]);
  const setKeepRecentTokens = useCallback((value: string) => { updateDraft(previous => ({ ...previous, keepRecentTokens: value })); }, [updateDraft]);

  const apply = useCallback(() => {
    if (!threadId) return;
    const current = draftRef.current;
    const nextTrigger = Number(current.triggerPercent), nextKeep = Number(current.keepRecentTokens);
    if (!Number.isSafeInteger(nextTrigger) || nextTrigger < 1 || nextTrigger > 100) {
      setError("触发阈值必须是 1 到 100 的整数百分比。");
      return;
    }
    if (!Number.isSafeInteger(nextKeep) || nextKeep < 1 || nextKeep > 1_000_000) {
      setError("近期保留目标必须是 1 到 1000000 的整数 token。");
      return;
    }
    const policy: TurnAutoCompactionOverride = { enabled: current.enabled, triggerPercent: nextTrigger, keepRecentTokens: nextKeep };
    const nextOverrides = { ...overridesRef.current, [threadId]: policy };
    overridesRef.current = nextOverrides;
    dirtyThreads.current.delete(threadId);
    sessionDrafts.current.delete(threadId);
    consumed.current.delete(threadId);
    stampOf(threadId);
    const synced = draftFrom(policy);
    draftRef.current = synced;
    setDraft(synced);
    setOverrides(nextOverrides);
    setError("");
  }, [threadId]);

  const clear = useCallback(() => {
    if (threadId) {
      dirtyThreads.current.delete(threadId);
      sessionDrafts.current.delete(threadId);
      consumed.current.delete(threadId);
      stampOf(threadId);
      if (Object.prototype.hasOwnProperty.call(overridesRef.current, threadId)) {
        const { [threadId]: _removed, ...rest } = overridesRef.current;
        overridesRef.current = rest;
        setOverrides(rest);
      }
    }
    setError("");
    // 内核默认值缺失时也复位，避免表单停留在已被清除的覆盖值上。
    const reset = resetAutoCompactionDraft(defaults);
    draftRef.current = reset;
    setDraft(reset);
  }, [defaults, threadId]);

  /**
   * 取出并消耗本会话待应用的覆盖；回执未知或成功时视为已消耗。
   * 明确拒绝时调用方用返回值调用 `restore` 写回。
   */
  const take = useCallback((id: string): TurnAutoCompactionOverride | undefined => {
    const pending = overridesRef.current[id];
    if (!pending) return undefined;
    const { [id]: _removed, ...rest } = overridesRef.current;
    overridesRef.current = rest;
    dirtyThreads.current.delete(id);
    sessionDrafts.current.delete(id);
    consumed.current.set(id, { policy: pending, stamp: stampOf(id) });
    setOverrides(rest);
    // 覆盖已随这次发送消耗：若当前正显示该会话，表单回到内核默认值，下次打开可继续同步最新默认值。
    if (lastThread.current === id) {
      const reset = resetAutoCompactionDraft(defaults);
      draftRef.current = reset;
      setDraft(reset);
    }
    return pending;
  }, [defaults]);

  /**
   * 明确拒绝后恢复本次取出的覆盖。只有取出后没有重新应用、清除或再次取用时才恢复；
   * 回执未知与成功路径不调用，保持「已消耗」语义。
   */
  const restore = useCallback((id: string, policy: TurnAutoCompactionOverride | undefined) => {
    if (!policy) return;
    const record = consumed.current.get(id);
    if (!record || record.policy !== policy || record.stamp !== stamps.current.get(id)) return;
    consumed.current.delete(id);
    stampOf(id);
    const next = { ...overridesRef.current, [id]: policy };
    overridesRef.current = next;
    setOverrides(next);
    if (lastThread.current === id) {
      const restored = draftFrom(policy);
      draftRef.current = restored;
      setDraft(restored);
    }
  }, []);

  return {
    defaults, draft, reading, error, valid,
    active: threadId ? overrides[threadId] : undefined,
    setEnabled, setTriggerPercent, setKeepRecentTokens, apply, clear, take, restore,
  };
}

export type AutoCompactionController = ReturnType<typeof useAutoCompaction>;
