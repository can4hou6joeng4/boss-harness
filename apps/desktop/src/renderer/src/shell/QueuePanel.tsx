import { useEffect, useState } from "react";
import { safeSlice } from "@boss-harness/shared";
import type { QueueItem, SkillDescriptor } from "@boss-harness/protocol";
import { IconClose } from "../components/Icons";
import { ModalSurface } from "../components/ModalSurface";
import { useClipboardCopy } from "../data/clipboardCopy";
import { harnessErrorText } from "../data/harnessBridge";
import { queueRefreshErrorText, type QueueRefreshResult } from "../data/queueRefresh";
import { queueActionNotice, type QueueActionOutcome } from "../data/queueAction";
import { queueItemRetryable } from "../data/queueRetry";
import { queueSkillLabels } from "../data/queueSkillLabels";
import { queuePauseDetail, queueStatusLabel } from "../data/queueStatus";
import { selectVisibleQueueItems } from "../data/queueSelection";
import { syncQueueDialogItem, syncQueueEditDialog } from "../data/queueDialogs";
import { clearQueueEditDraft, readQueueEditDraft, writeQueueEditDraft } from "../data/queueEditDrafts";
import { QueueInputDialog } from "./QueueInputDialog";
import { compactionLabel, compactionTitle } from "./queueCompaction";

export function QueuePanel({ items, threadId, totalItems, activeItems, truncated, onRemove, onRetry, onReadFull, onUpdateInput, skills = [], connected = true, onRefresh }: {
  items: QueueItem[];
  /** 所属会话；未保存的编辑草稿按会话保留，对话区随切换卸载后仍能恢复。 */
  threadId?: string;
  /** 技能目录；用于把队列项里的技能 id 显示为名称，缺失时回退 id。 */
  skills?: SkillDescriptor[];
  /** 内核侧总数；旧内核不返回时为 undefined。 */
  totalItems?: number;
  /** 内核按全部持久项统计的待处理数；旧内核缺省时按已载入项计算。 */
  activeItems?: number;
  /** 内核只返回有界投影，仍有未载入的队列记录。 */
  truncated?: boolean;
  /** 内核连接状态；断开时队列内容可能已过期，刷新按钮禁用。 */
  connected?: boolean;
  /** 手动重读当前会话队列；成功返回 `{ ok: true }`，失败带回原因。 */
  onRefresh?: () => Promise<QueueRefreshResult>;
  /** 读取队列项在持久化记录中的完整输入，仅供核对，不会重新提交。 */
  onReadFull?: (item: QueueItem) => Promise<QueueItem>;
  /** 改写仍在排队（queued）的队列项正文；正文被截断时必须先经 onReadFull 读取全文。 */
  onUpdateInput?: (item: QueueItem, input: string) => Promise<QueueItem>;
  /** 撤回队列项；`skipped` 表示请求没有发出，`uncertain` 表示结果无法确认。 */
  onRemove: (id: string) => Promise<QueueActionOutcome>;
  /** 重新排队暂停项；结果语义与 onRemove 一致。 */
  onRetry?: (item: QueueItem) => Promise<QueueActionOutcome>;
}): JSX.Element | null {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [reading, setReading] = useState<string | null>(null);
  const [viewing, setViewing] = useState<{ item: QueueItem; input: string } | null>(null);
  // 列表刷新会把条目换成截断预览；编辑基线必须保留最初读取的完整正文。
  const [editing, setEditing] = useState<{ item: QueueItem; draft: string; originalInput: string } | null>(() => threadId ? readQueueEditDraft(threadId) : null);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [confirmEditClose, setConfirmEditClose] = useState(false);
  // 撤回会永久移除排队消息，必须显式确认；对话框保留打开时的条目快照，
  // 列表刷新后仍能核对正文，并由实时状态决定是否还允许提交。
  const [removeTarget, setRemoveTarget] = useState<QueueItem | null>(null);
  const [removeBusy, setRemoveBusy] = useState(false);
  const [removeMessage, setRemoveMessage] = useState("");
  // 折叠状态优先显示暂停项；展开后渲染内核已载入的全部条目。
  const [showAll, setShowAll] = useState(false);
  const clipboard = useClipboardCopy();
  // 目标消失时关闭只读与无修改窗口；有修改的编辑器继续显示，供复制或明确丢弃。
  // 条目仍在时同步最新快照，保存权限始终以当前列表为准。
  useEffect(() => {
    setViewing(current => syncQueueDialogItem(current, items));
    setEditing(current => syncQueueEditDialog(current, items));
  }, [items]);
  // 未保存的编辑按会话保留：切换会话会卸载整个对话区，切回时恢复同一份草稿。
  // 保存成功或确认丢弃由 setEditing(null) 清除；条目消失但有修改时继续保留供复制。
  useEffect(() => {
    if (!threadId) return;
    if (editing) writeQueueEditDraft(threadId, editing);
    else clearQueueEditDraft(threadId);
  }, [threadId, editing]);
  if (!items.length && !editing && !removeTarget) return null;
  const editChanged = editing !== null && editing.draft !== editing.originalInput;
  // 撤回确认框绑定实时条目：条目被投递或撤回后禁止继续提交，但保留正文供核对。
  const removeLive = removeTarget ? items.find(item => item.id === removeTarget.id) : undefined;
  const removeItem = removeLive ?? removeTarget;
  const removeAvailable = Boolean(removeLive && (removeLive.status === "queued" || removeLive.status === "paused"));
  const removeSkillLabels = removeItem ? queueSkillLabels(removeItem.skillIds, skills) : [];
  const refresh = async () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true); setError("");
    try {
      const reason = queueRefreshErrorText(await onRefresh());
      if (reason) setError(`刷新队列失败：${reason}。队列面板保留上一次内容。`);
    } catch (cause) {
      setError(`刷新队列失败：${harnessErrorText(cause)}。队列面板保留上一次内容。`);
    } finally {
      setRefreshing(false);
    }
  };
  const canRetry = (item: QueueItem) => Boolean(onRetry) && queueItemRetryable(item);
  const showFullInput = async (item: QueueItem) => {
    if (!onReadFull || reading) return;
    clipboard.reset();
    setReading(item.id); setError("");
    try {
      const full = await onReadFull(item);
      setViewing({ item: full, input: full.input });
    } catch (cause) {
      setError(`读取完整输入失败：${harnessErrorText(cause)}。队列面板仍显示预览。`);
    } finally {
      setReading(null);
    }
  };
  const startEditing = async (item: QueueItem) => {
    if (!onUpdateInput || reading || saving || item.status !== "queued") return;
    setError(""); setEditError(""); setConfirmEditClose(false);
    if (!item.inputTruncated) { setEditing({ item, draft: item.input, originalInput: item.input }); return; }
    if (!onReadFull) { setError("列表只显示截断预览，当前无法读取完整正文进行编辑。"); return; }
    // 截断项必须先用 queue/get 取回全文，绝不能把 600 字符预览当成正文保存。
    setReading(item.id);
    try {
      const full = await onReadFull(item);
      // 读取期间条目可能已被投递或撤回：此时打开编辑框只会得到一次必然失败的保存。
      if (full.status !== "queued") { setError(`这条消息${queueStatusLabel(full)}，已无法编辑。`); return; }
      setEditing({ item: full, draft: full.input, originalInput: full.input });
    } catch (cause) {
      setError(`读取完整输入失败：${harnessErrorText(cause)}。未进入编辑，预览保持不变。`);
    } finally {
      setReading(null);
    }
  };
  // 取消、关闭按钮、Esc 与遮罩共享同一入口；继续编辑后旧的丢弃确认失效。
  const closeEdit = () => {
    if (saving) return;
    if (editChanged && !confirmEditClose) {
      setConfirmEditClose(true);
      return;
    }
    setEditing(null); setEditError(""); setConfirmEditClose(false);
  };
  const saveEdit = async () => {
    if (!editing || !onUpdateInput || saving) return;
    const live = items.find(item => item.id === editing.item.id);
    if (!live || live.status !== "queued") {
      setEditError("这条消息已不在排队中，修改未保存。草稿仍保留在编辑框中。");
      return;
    }
    if (!editing.draft.trim()) { setEditError("正文不能为空。"); return; }
    if (!editChanged) { setEditing(null); setEditError(""); return; }
    setSaving(true); setEditError(""); setConfirmEditClose(false);
    try {
      await onUpdateInput(editing.item, editing.draft);
      setEditing(null);
    } catch (cause) {
      setEditError(`保存失败：${harnessErrorText(cause)}。草稿仍保留在编辑框中。`);
    } finally {
      setSaving(false);
    }
  };
  const retry = async (item: QueueItem) => {
    setPending(item.id); setError("");
    try {
      const notice = queueActionNotice("重新排队", await onRetry!(item));
      if (notice) setError(notice);
    } catch (cause) {
      // 入队或回执异常：请求可能已经发出，无法证明没有生效，按未确认处理。
      setError(`重新排队结果尚未确认：${harnessErrorText(cause)}。请核对队列状态。`);
    } finally {
      setPending(null);
    }
  };
  // 首次点击只打开确认框，不发出任何队列写请求；取消或关闭保持条目原样。
  const startRemove = (item: QueueItem) => {
    if (pending !== null) return;
    setError(""); setRemoveMessage(""); setRemoveTarget(item);
  };
  const closeRemove = () => {
    if (removeBusy) return;
    setRemoveTarget(null); setRemoveMessage("");
  };
  const confirmRemove = async () => {
    if (!removeTarget || removeBusy || !removeAvailable) return;
    const id = removeTarget.id;
    setRemoveBusy(true); setRemoveMessage("");
    try {
      const notice = queueActionNotice("撤回", await onRemove(id));
      // 结果未确认时保留确认框与正文，让用户看到提示后再决定是否核对。
      if (notice) setRemoveMessage(notice);
      else { setRemoveTarget(null); setRemoveMessage(""); }
    } catch (cause) {
      setRemoveMessage(`撤回结果尚未确认：${harnessErrorText(cause)}。请核对队列状态。`);
    } finally {
      setRemoveBusy(false);
    }
  };
  const collapsedItems = selectVisibleQueueItems(items, false);
  const visibleItems = showAll ? selectVisibleQueueItems(items, true) : collapsedItems;
  // 折叠状态下仍有未显示项时提供展开入口；展开后显示全部已载入项。
  const collapsedHidden = collapsedItems.length < items.length;
  const pendingCount = activeItems ?? items.filter(item => item.status === "queued" || item.status === "delivering" || item.status === "paused").length;
  // 内核投影与界面自身的 20 条上限都可能隐藏记录；总数只用于说明，不参与任何业务判断。
  const total = Math.max(totalItems ?? items.length, items.length);
  const kernelHidden = truncated === true;
  const hiddenNote = [
    kernelHidden
      ? total > items.length ? `共 ${total} 项，已载入 ${items.length} 项` : `列表已截断，已载入 ${items.length} 项`
      : "",
    visibleItems.length < items.length ? `仅显示 ${visibleItems.length} 项` : "",
  ].filter(Boolean).join("，");
  // 完整输入视图与列表使用同一套技能映射，避免同一个队列项在两处显示不一致。
  // 编辑只对当前列表中仍在排队的条目开放；保留草稿的旧快照不能授予保存权限。
  const editingLiveItem = editing ? items.find(item => item.id === editing.item.id) : undefined;
  const editingQueued = editingLiveItem?.status === "queued";
  const viewingSkillIds = viewing?.item.skillIds ?? [];
  const viewingSkillLabels = queueSkillLabels(viewingSkillIds, skills);
  const copyFeedback = viewing && clipboard.feedback?.key === viewing.item.id ? clipboard.feedback : null;
  return <>
    {items.length > 0 && <section className="turn-queue" aria-label="任务队列" aria-live="polite">
    <div className="turn-queue-heading"><strong>任务队列</strong><span data-queue-pending={pendingCount} title={activeItems !== undefined ? "待处理数量由内核按全部持久队列项统计。"
      : kernelHidden ? "待处理数量按内核已载入的队列项统计。" : undefined}>{pendingCount} 项待处理</span>
      {hiddenNote && <span className="turn-queue-more" data-queue-total={total} data-queue-truncated={kernelHidden ? "true" : "false"} data-queue-visible={visibleItems.length}
        title={kernelHidden ? `内核只返回有界投影（待处理与已结束条目各自封顶），更早的队列记录未载入。${activeItems !== undefined
          ? "待处理数量仍按全部持久项统计。" : "待处理数量按已载入项统计。"}` : "任务队列较长，界面只显示最近的项目。"}>{hiddenNote}</span>}
      {collapsedHidden && <button type="button" className="turn-queue-show-all" aria-expanded={showAll}
        data-queue-expanded={showAll ? "true" : "false"}
        title={showAll ? "收起队列，优先显示暂停项与最近的待投递项" : "显示内核已载入的全部队列项"}
        onClick={() => setShowAll(current => !current)}>{showAll ? "收起" : "展开全部"}</button>}
      {onRefresh && <button type="button" className="turn-queue-refresh" disabled={refreshing || !connected}
        title={connected ? "重新读取当前会话的队列状态" : "本机内核未连接，恢复连接后再刷新"}
        onClick={() => { void refresh(); }}>{refreshing ? "刷新中…" : "刷新"}</button>}
    </div>
    {!connected && <p className="turn-queue-stale" role="status">本机内核已断开，队列状态可能已过期；恢复连接后会重新读取。</p>}
    <ul>
      {visibleItems.map(item => <li key={item.id}>
        <div className="turn-queue-item-copy">
          <span className={`turn-queue-kind is-${item.kind}`}>{item.kind === "steering" ? "当前回合" : "后续回合"}</span>
          <span className="turn-queue-status">{queueStatusLabel(item)}</span>
          {(() => {
            const labels = queueSkillLabels(item.skillIds, skills);
            return labels.length
              ? <span className="turn-queue-skills" title={labels.join("、")}>技能：{labels.join("、")}</span>
              : null;
          })()}
          {item.autoCompaction && <span className="turn-queue-skills" title={compactionTitle(item.autoCompaction)}>{compactionLabel(item.autoCompaction)}</span>}
          {item.inputTruncated && <span className="turn-queue-skills" title="列表只显示前 600 字符；可点击「查看完整输入」核对全文，重新排队会读取并复用完整输入">正文已截断</span>}
          <p title={item.input}>{item.input}</p>
          {item.inputTruncated && onReadFull && <button type="button" className="turn-queue-expand" disabled={reading !== null}
            title="读取内核持久化的完整输入，仅供核对，不会重新提交"
            onClick={() => { void showFullInput(item); }}>{reading === item.id ? "读取中…" : "查看完整输入"}</button>}
          {(() => {
            const detail = queuePauseDetail(item, canRetry(item));
            return detail ? <p className="turn-queue-error">{detail}</p> : null;
          })()}
        </div>
        {onUpdateInput && item.status === "queued" && <button type="button" className="turn-queue-edit" title="编辑排队中的正文；不会提前投递" disabled={reading !== null || saving} onClick={() => { void startEditing(item); }}>编辑</button>}
        {canRetry(item) && <button type="button" className="turn-queue-retry" disabled={pending !== null || !connected}
          title={connected ? "用同一输入与技能重新创建队列消息，并撤回旧项" : "本机内核未连接，恢复连接后再重新排队"}
          onClick={() => { void retry(item); }}>重新排队</button>}
        {(item.status === "queued" || item.status === "paused") && <button type="button" aria-label={`撤回排队消息：${safeSlice(item.input, 80)}`}
          aria-haspopup="dialog"
          title={!connected ? "本机内核未连接，恢复连接后再撤回" : item.status === "paused" ? "取消暂停的队列消息（需要确认）" : "撤回排队消息（需要确认）"}
          disabled={pending !== null || !connected} onClick={() => startRemove(item)}
        ><IconClose size={14} /></button>}
      </li>)}
    </ul>
    {error && <p className="turn-queue-error" role="status">{error}</p>}
    </section>}
    {viewing && <QueueInputDialog item={viewing.item} input={viewing.input} skillLabels={viewingSkillLabels}
      retryAvailable={canRetry(viewing.item)} copyFeedback={copyFeedback}
      onCopy={() => { void clipboard.copy(viewing.input, viewing.item.id); }} onClose={() => setViewing(null)} />}
    {editing && <ModalSurface title="编辑排队消息" onClose={closeEdit} closeDisabled={saving}>
      <div className="dialog-form queue-input-dialog">
        <p className="dialog-note">{editing.item.kind === "steering" ? "当前回合" : "后续回合"} · {editingQueued
          ? "只修改正文；技能与自动压缩覆盖保持不变，保存后仍需等待投递。"
          : editingLiveItem ? `这条消息${queueStatusLabel(editingLiveItem)}，修改无法保存；可复制正文后关闭。`
            : "当前列表已不包含这条消息，修改无法保存；草稿仍保留，可选中并复制正文后关闭。"}</p>
        <textarea className="queue-input-editor" aria-label="排队消息正文" rows={10} maxLength={100000} disabled={saving}
          value={editing.draft} onChange={event => { setEditing(current => current ? { ...current, draft: event.target.value } : current); setConfirmEditClose(false); }} />
        <div className="queue-input-editor-meta"><span>{editing.draft.length} / 100000 字符</span>
          <span className={!editingQueued || !editing.draft.trim() ? "is-warning" : ""}>{!editingQueued ? "修改无法保存"
            : editing.draft.trim() ? "保存后投递的是这段正文" : "正文不能为空"}</span></div>
        {confirmEditClose && editChanged && <p className="queue-input-edit-error" role="alert">有未保存的修改；再次关闭将丢弃。</p>}
        {editError && <p className="queue-input-edit-error" role="alert">{editError}</p>}
        <div className="dialog-actions">
          <button className="secondary-button" disabled={saving} onClick={closeEdit}>取消</button>
          <button className="solid-button" disabled={saving || !editingQueued || !editing.draft.trim() || !editChanged}
            onClick={() => { void saveEdit(); }}>{saving ? "保存中…" : "保存"}</button>
        </div>
      </div>
    </ModalSurface>}
    {removeItem && <ModalSurface title="撤回排队消息" onClose={closeRemove} closeDisabled={removeBusy} className="queue-remove-dialog">
      <div className="dialog-form queue-input-dialog">
        <p className="dialog-note">{removeItem.kind === "steering" ? "当前回合" : "后续回合"} · {removeLive
          ? queueStatusLabel(removeLive) : "已不在当前列表"}。撤回后这条消息不会再投递，正文也不会自动恢复。</p>
        <p className="turn-queue-full-input" data-queue-remove-input>{removeItem.input}</p>
        {removeItem.inputTruncated && <p className="dialog-note">列表只显示前 600 字符；撤回的是内核保存的完整消息。</p>}
        {removeSkillLabels.length > 0 && <p className="queue-input-facts"><span>技能：{removeSkillLabels.join("、")}</span></p>}
        {removeItem.autoCompaction && <p className="queue-input-facts"><span>{compactionLabel(removeItem.autoCompaction)}</span></p>}
        {!removeLive && !removeMessage && <p className="queue-input-edit-error" role="alert">这条消息已不在队列中；可能已被投递或撤回。</p>}
        {removeLive && !removeAvailable && !removeMessage && <p className="queue-input-edit-error" role="alert">这条消息{queueStatusLabel(removeLive)}，已无法撤回。</p>}
        {!connected && !removeMessage && <p className="queue-input-edit-error" role="alert">本机内核未连接，恢复连接后才能撤回。</p>}
        {removeMessage && <p className="queue-input-edit-error" role="alert">{removeMessage}</p>}
        <div className="dialog-actions">
          <button type="button" className="secondary-button" disabled={removeBusy} onClick={closeRemove}>取消</button>
          <button type="button" className="solid-button danger-button" disabled={removeBusy || !removeAvailable || !connected}
            onClick={() => { void confirmRemove(); }}>{removeBusy ? "正在撤回…" : "确认撤回"}</button>
        </div>
      </div>
    </ModalSurface>}
  </>;
}
