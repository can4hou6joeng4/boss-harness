import { useCallback, useEffect, useRef, useState } from "react";
import type { ContextEditReadResponse } from "@boss-harness/protocol";
import { harnessErrorText, readContextEdit, writeContextEdit } from "../data/harnessBridge";
import { CONTEXT_EDIT_STALE_NOTICE, contextEditSubmitBlocked } from "../data/contextEditState";
import { ModalSurface } from "./ModalSurface";
import "../styles/context-edit.css";

interface Props {
  threadId: string;
  itemId: string;
  title: string;
  onClose: () => void;
  onChanged: (state: ContextEditReadResponse) => void;
}

function validate(value: ContextEditReadResponse, threadId: string, itemId: string): ContextEditReadResponse {
  if (value.threadId !== threadId || value.itemId !== itemId || !/^[a-f0-9]{64}$/.test(value.sourceDigest)
      || typeof value.originalText !== "string" || !(typeof value.currentText === "string" || value.currentText === null)
      || typeof value.canEdit !== "boolean" || typeof value.excluded !== "boolean") {
    throw new Error("上下文编辑响应与当前消息不匹配，已停止操作。");
  }
  return value;
}

export function ContextEditDialog({ threadId, itemId, title, onClose, onChanged }: Props) {
  const [record, setRecord] = useState<ContextEditReadResponse>();
  const [draft, setDraft] = useState("");
  // 最后一次有效读取 / 提交的正文独立保留；刷新失败或读取中都不会把草稿误当成已保存。
  const [baseline, setBaseline] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  // 读取失败后 record 仍是上一次成功的快照；重新读取成功前不得把它当作当前状态。
  const [stale, setStale] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);

  const draftRef = useRef(draft); draftRef.current = draft;
  const baselineRef = useRef(baseline); baselineRef.current = baseline;

  const refresh = useCallback(async () => {
    const keepDraft = draftRef.current !== baselineRef.current;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const next = validate(await readContextEdit(threadId, itemId), threadId, itemId);
      const current = next.currentText ?? next.originalText;
      setRecord(next);
      setBaseline(current);
      // 重新读取只更新权威快照，仍在编辑的替换文本不能被静默覆盖。
      if (keepDraft) {
        setNotice("已重新读取内核中的当前文本；你的未保存修改已保留。");
        setConfirmClose(false);
      } else {
        setDraft(current);
      }
      setUncertain(false);
      setStale(false);
      onChanged(next);
    } catch (cause) {
      setStale(true);
      setError(`读取会话上下文失败：${harnessErrorText(cause)}`);
    } finally {
      setLoading(false);
    }
  }, [itemId, onChanged, threadId]);

  useEffect(() => { void refresh(); }, [refresh]);

  const apply = async (replacementText: string | null) => {
    if (!record || saving || stale || !record.canEdit) return;
    setSaving(true);
    setError("");
    setUncertain(false);
    let writeError: unknown;
    try {
      await writeContextEdit({ threadId, itemId, sourceDigest: record.sourceDigest, replacementText });
    } catch (cause) {
      writeError = cause;
    }

    // A lost RPC response can follow a durable append. Read the authoritative
    // state before reporting failure; never repeat the append automatically.
    try {
      const actual = validate(await readContextEdit(threadId, itemId), threadId, itemId);
      const current = actual.currentText ?? actual.originalText;
      setRecord(actual);
      setStale(false);
      onChanged(actual);
      const expected = replacementText === null ? actual.excluded : !actual.excluded && actual.currentText === replacementText;
      if (expected) {
        setDraft(current);
        setBaseline(current);
        setError("");
        setUncertain(false);
      } else {
        // 回读显示编辑没有生效：基线换成权威文本，但保留用户仍在编辑的草稿，
        // 关闭前仍需确认，重试也仍使用这份正文；不自动重放写入。
        setBaseline(current);
        if (writeError) {
          setError("提交结果未确认。已重新读取当前上下文；请核对下方内容后再决定下一步。没有自动重试。");
          setUncertain(true);
        } else {
          setError("会话来源已变化，编辑没有按预期生效。请核对当前内容后重新操作。");
        }
      }
      setNotice("");
    } catch (cause) {
      // 回读失败时界面仍保留提交前的 record；标记过期，禁止基于旧快照继续提交。
      setStale(true);
      setError(writeError
        ? "提交结果和当前状态都无法确认。请先刷新并核对，不要重复提交。"
        : `提交后无法读取最新上下文（${harnessErrorText(cause)}），请稍后核对。`);
      setUncertain(true);
    } finally {
      setSaving(false);
    }
  };

  const excluded = record?.excluded ?? false;
  const changed = Boolean(record && !excluded && record.currentText !== record.originalText);
  const blocked = contextEditSubmitBlocked({ loading, saving, stale });
  // 未保存判定只看编辑器正文与最后一次有效基线；与「提交后当前是否已替换」无关。
  const dirty = draft !== baseline;
  // 关闭按钮、Esc 与遮罩共享同一入口：有修改先提示，再次关闭才丢弃。
  const close = () => {
    if (saving) return;
    if (dirty && !confirmClose) { setConfirmClose(true); return; }
    onClose();
  };
  const updateDraft = (value: string) => { setDraft(value); setNotice(""); setConfirmClose(false); };

  return <ModalSurface title={title} onClose={close} closeDisabled={saving} className="context-edit-dialog">
    <div className="context-edit-body">
      <p className="context-edit-note">这里只调整未来模型请求中的上下文。原始会话记录和已发生的操作保持不变。</p>
      {loading && <p className="context-edit-status" role="status">正在读取消息与当前上下文…</p>}
      {record && <>
        <section className="context-edit-state" aria-label="当前模型上下文状态">
          <strong>{excluded ? "此消息已从后续模型上下文排除" : changed ? "后续模型请求使用替换文本" : "后续模型请求使用原始文本"}</strong>
          <span>{record.canEdit ? "可追加新的上下文编辑" : record.reason || "此消息当前不可编辑"}</span>
        </section>
        {record && stale && <p className="context-edit-warning" role="status">{CONTEXT_EDIT_STALE_NOTICE}</p>}
        <section className="context-edit-source">
          <h3>原始会话文本</h3>
          <pre>{record.originalText || "（空文本）"}</pre>
        </section>
        <section className="context-edit-source">
          <h3>当前送入模型的文本</h3>
          <pre>{excluded ? "（此消息不进入后续模型上下文）" : record.currentText || "（空文本）"}</pre>
        </section>
        {record.canEdit && <label className="context-edit-label" htmlFor="context-edit-draft">替换文本{dirty ? " · 未保存" : ""}
          <textarea id="context-edit-draft" rows={7} value={draft} onChange={event => updateDraft(event.target.value)} disabled={saving || loading} />
        </label>}
        {record.canEdit && dirty && <p className="context-edit-status" role="status">替换文本尚未提交；编辑只在你点击下方按钮后生效。</p>}
        {notice && <p className="context-edit-status" role="status">{notice}</p>}
        {record.reason && !record.canEdit && <p className="context-edit-warning" role="status">{record.reason}</p>}
      </>}
      {error && <p className="context-edit-warning" role="alert">{error}</p>}
      {uncertain && !loading && <p className="context-edit-status" role="status">当前状态尚未确认；刷新只读取，不会再次提交编辑。</p>}
      {error && !loading && <button className="secondary-button" type="button" onClick={() => void refresh()} disabled={saving}>重新读取状态</button>}
      {confirmClose && dirty && <p className="context-edit-warning" role="alert">有未保存的替换文本；再次关闭将丢弃。</p>}
      <div className="context-edit-actions">
        <button className="secondary-button" type="button" onClick={close} disabled={saving}>关闭</button>
        {record?.canEdit && <>
          <button className="secondary-button" type="button" onClick={() => void apply(record.originalText)} disabled={blocked || (!excluded && !changed && draft === record.originalText)}>恢复原文</button>
          <button className="secondary-button" type="button" onClick={() => void apply(null)} disabled={blocked || excluded}>排除消息</button>
          <button className="solid-button" type="button" onClick={() => void apply(draft)} disabled={blocked || !draft.trim() || [...draft].length > 32000 || draft === record.currentText}>{saving ? "正在核对…" : "使用替换文本"}</button>
        </>}
      </div>
    </div>
  </ModalSurface>;
}
