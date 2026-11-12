import { useEffect, useRef, useState } from "react";
import type { WorkspaceInstructionsText } from "@boss-harness/protocol";
import { harnessErrorText, readWorkspaceInstructions, writeWorkspaceInstructions } from "../data/harnessBridge";

export interface WorkspaceInstructionsEditorProps {
  open: boolean;
  connected: boolean;
  onClose: () => void;
  /** 保存成功后刷新上下文预算，让新的文件状态立即出现在面板里。 */
  onSaved: () => void;
  /** 未保存状态交给外层，面板关闭前也能提示，避免整块收起时静默丢稿。 */
  onDirtyChange?: (dirty: boolean) => void;
  /** 保存在途状态交给外层，关闭面板或离开页面前据此拦截。 */
  onSavingChange?: (saving: boolean) => void;
}

const byteLength = (value: string) => new TextEncoder().encode(value).length;
const STATUS_TEXT: Record<WorkspaceInstructionsText["status"], string> = {
  loaded: "已加载",
  empty: "空文件，未注入",
  too_large: "超过上限，已忽略；保存会以新内容替换",
  unreadable: "无法读取（需普通 UTF-8 文件且不是符号链接）；保存会以新内容替换",
};

/**
 * 工作区常驻说明的查看与保存。固定写入内核声明的首选路径；
 * 旧位置仍生效时明确提示保存后旧文件不再被读取。
 */
export function WorkspaceInstructionsEditor(props: WorkspaceInstructionsEditorProps) {
  const [info, setInfo] = useState<WorkspaceInstructionsText | null>(null);
  const [content, setContent] = useState("");
  // 最后一次有效读取或保存的正文独立保留，读取中或读取失败不会把草稿标记为已保存。
  const [baselineContent, setBaselineContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const dirty = content !== baselineContent;
  const reportDirty = props.onDirtyChange;
  // 重连会触发重读：读取开始时已有未保存修改，则回执只更新内核事实，不覆盖输入框。
  const dirtyRef = useRef(dirty);
  useEffect(() => { dirtyRef.current = dirty; }, [dirty]);
  // 保存回执必须绑定发起它的那次编辑会话：关闭或重新打开后，旧回执不能再改写状态。
  const openRef = useRef(props.open);
  openRef.current = props.open;
  const mountedRef = useRef(true);
  const saveAttempt = useRef(0);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; saveAttempt.current += 1; };
  }, []);
  const reportSaving = props.onSavingChange;
  useEffect(() => { reportSaving?.(props.open && saving); }, [props.open, saving, reportSaving]);
  useEffect(() => () => { reportSaving?.(false); }, [reportSaving]);
  useEffect(() => {
    if (!props.open) {
      // 显式关闭（含确认丢弃）后重新打开要从内核重新读取，不能恢复旧草稿。
      // 让仍在途的保存失去身份，避免迟到回执把已清空的状态当成新基线。
      saveAttempt.current += 1;
      setInfo(null); setContent(""); setBaselineContent(""); setLoading(false); setSaving(false);
      setError(""); setNotice(""); setConfirmDiscard(false);
      return;
    }
    if (!props.connected) return;
    let active = true;
    const keepDraft = dirtyRef.current;
    const previousContent = baselineContent;
    setLoading(true); setError(""); setNotice(""); setInfo(null); setConfirmDiscard(false);
    readWorkspaceInstructions().then(value => {
      if (!active) return;
      // 内核返回的正文与上限是保存判定的唯一依据；不在这里补默认值。
      if (!value || typeof value.content !== "string" || typeof value.path !== "string"
        || typeof value.pathPreferred !== "string" || typeof value.limitBytes !== "number") {
        setError("内核返回的工作区说明无法识别。");
        return;
      }
      setInfo(value);
      setBaselineContent(value.content);
      if (keepDraft) {
        // 保留用户草稿；内核正文确有变化时明确提示，不静默替换。
        setNotice(value.content !== previousContent
          ? "内核中的工作区说明已在重新连接后更新；已保留你尚未保存的修改。"
          : "已重新连接并读取内核中的工作区说明；你的未保存修改已保留。");
        return;
      }
      setContent(value.content);
    }).catch(cause => { if (active) setError(`读取工作区说明失败：${harnessErrorText(cause)}`); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [props.open, props.connected]);
  useEffect(() => { reportDirty?.(props.open && dirty); }, [props.open, dirty, reportDirty]);
  if (!props.open) return null;
  const bytes = byteLength(content);
  const limit = info?.limitBytes ?? 8 * 1024;
  const overLimit = bytes > limit;
  // 第一次点击只提示，第二次才真正关闭，避免把刚写的说明误丢掉。
  // 保存在途时写入已经发出，此时允许关闭会让「丢弃」与随后落盘互相矛盾。
  const close = () => {
    if (saving) { setNotice("正在保存，完成前不能关闭。"); return; }
    if (dirty && !confirmDiscard) {
      setConfirmDiscard(true);
      setNotice("有未保存的修改；再次点击关闭将丢弃。");
      return;
    }
    setConfirmDiscard(false);
    props.onClose();
  };
  const save = async () => {
    if (saving || overLimit || !info || !props.connected) return;
    const attempt = ++saveAttempt.current;
    const payload = content;
    const payloadBytes = bytes;
    setSaving(true); setError(""); setNotice("");
    try {
      await writeWorkspaceInstructions(payload);
      // 已关闭、已卸载或已开始新编辑会话：回执不得落回当前界面。
      if (!mountedRef.current || !openRef.current || saveAttempt.current !== attempt) return;
      // 保存后草稿就是新基线，未保存提示随之消失。
      setInfo(previous => previous ? { ...previous, content: payload, bytes: payloadBytes, status: payload.trim() ? "loaded" : "empty" } : previous);
      setBaselineContent(payload);
      setConfirmDiscard(false);
      setNotice(`已保存 ${payloadBytes} 字节，下一回合生效。`);
      props.onSaved();
    } catch (cause) {
      if (!mountedRef.current || !openRef.current || saveAttempt.current !== attempt) return;
      setError(`保存失败：${harnessErrorText(cause)}`);
    } finally {
      if (saveAttempt.current === attempt) setSaving(false);
    }
  };
  return <div className="context-panel-instructions-editor">
    <div className="context-panel-instructions-editor-head">
      <strong>工作区常驻说明</strong>
      <span>{loading ? "正在读取…" : info ? `${info.path} · ${STATUS_TEXT[info.status]}` : "尚未读取"}{dirty ? " · 未保存" : ""}</span>
    </div>
    {!props.connected && <p className="context-panel-warning" role="status">本地内核未连接，无法读取或保存工作区说明。</p>}
    {info && info.path !== info.pathPreferred && <p className="context-panel-note">当前读取的是旧位置；保存会写入 {info.pathPreferred}，此后旧文件不再被读取。</p>}
    <label className="context-panel-instructions-editor-field" htmlFor="workspace-instructions-text">正文（UTF-8，最多 {limit.toLocaleString("zh-CN")} 字节）<textarea id="workspace-instructions-text" rows={8} value={content} disabled={loading || saving || !props.connected} onChange={event => { setContent(event.target.value); setNotice(""); setConfirmDiscard(false); }} /></label>
    <div className="context-panel-instructions-editor-actions">
      <span className={overLimit ? "context-panel-warning" : "context-panel-note"} role={overLimit ? "alert" : undefined}>{bytes.toLocaleString("zh-CN")} / {limit.toLocaleString("zh-CN")} 字节{overLimit ? "，超出上限，无法保存" : ""}</span>
      <button type="button" className="secondary-button" onClick={close} disabled={saving}>{confirmDiscard ? "确认丢弃修改" : "关闭"}</button>
      <button type="button" className="solid-button" onClick={() => { void save(); }} disabled={!info || loading || saving || overLimit || !props.connected}>{saving ? "正在保存…" : "保存"}</button>
    </div>
    {saving && <p className="context-panel-note" role="status">正在保存，完成前不能关闭。</p>}
    {notice && <p className="context-panel-note" role="status">{notice}</p>}
    {error && <p className="context-panel-warning" role="alert">{error}</p>}
    <p className="context-panel-note">保存后下一回合重新读取；内容只是上下文，不改变工具权限、审批要求或只读限制。</p>
  </div>;
}
