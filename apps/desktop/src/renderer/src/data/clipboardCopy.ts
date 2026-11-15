import { useCallback, useEffect, useRef, useState } from "react";
import { safeSlice } from "@boss-harness/shared";

/**
 * 剪贴板写入的共享入口：界面只有在真正写入成功后才能显示「已复制」。
 * 失败时带回可读原因，原因只用于提示，不包含被复制的正文。
 */
export type CopyResult = { ok: true } | { ok: false; reason: string };

const MAX_REASON_LENGTH = 80;

export async function copyText(text: string): Promise<CopyResult> {
  const clipboard = typeof navigator === "undefined" ? undefined : navigator.clipboard;
  if (!clipboard || typeof clipboard.writeText !== "function") return { ok: false, reason: "当前环境不支持剪贴板写入" };
  try {
    await clipboard.writeText(text);
    return { ok: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : typeof error === "string" ? error : "";
    return { ok: false, reason: safeSlice(message.trim(), MAX_REASON_LENGTH) || "系统拒绝了剪贴板写入" };
  }
}

export interface CopyFeedback {
  /** 发起复制的控件标识（消息 id、代码块序号或文件名）。 */
  key: string;
  ok: boolean;
  reason?: string;
}

/** 复制反馈只描述最近一次点击；重置或卸载后，迟到回执不能恢复旧提示。 */
export function useClipboardCopy(resetMs = 2000) {
  const [feedback, setFeedback] = useState<CopyFeedback | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const version = useRef(0);
  const clear = useCallback(() => {
    if (timer.current !== undefined) clearTimeout(timer.current);
    timer.current = undefined;
  }, []);
  useEffect(() => () => { version.current += 1; clear(); }, [clear]);
  const copy = useCallback(async (text: string, key: string): Promise<CopyResult> => {
    const mine = ++version.current;
    clear();
    setFeedback(null);
    const result = await copyText(text);
    // 只使界面反馈失效，不取消已发起的系统写入；调用方仍拿到该次复制的实际结果。
    if (version.current !== mine) return result;
    setFeedback(result.ok ? { key, ok: true } : { key, ok: false, reason: result.reason });
    timer.current = setTimeout(() => {
      if (version.current !== mine) return;
      timer.current = undefined;
      setFeedback(null);
    }, resetMs);
    return result;
  }, [clear, resetMs]);
  const reset = useCallback(() => { version.current += 1; clear(); setFeedback(null); }, [clear]);
  return { feedback, copy, reset };
}
