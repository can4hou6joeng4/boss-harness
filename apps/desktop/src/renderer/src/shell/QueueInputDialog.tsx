import type { QueueItem } from "@boss-harness/protocol";
import { ModalSurface } from "../components/ModalSurface";
import type { CopyFeedback } from "../data/clipboardCopy";
import { queuePauseDetail, queueStatusLabel } from "../data/queueStatus";
import { compactionLabel, compactionTitle } from "./queueCompaction";

/**
 * 完整输入窗口的只读内容：状态与暂停说明复用列表的文案函数，
 * 避免同一个队列项在列表和窗口里显示不同的状态或原因。
 */
export function QueueInputDialogContent({ item, input, skillLabels, retryAvailable, copyFeedback, onCopy }: {
  item: QueueItem;
  input: string;
  skillLabels: string[];
  /** 列表中当前是否提供重新排队入口；只影响启动失败且输入未写入会话时的说明。 */
  retryAvailable: boolean;
  copyFeedback: CopyFeedback | null;
  onCopy: () => void;
}): JSX.Element {
  const detail = queuePauseDetail(item, retryAvailable);
  return <div className="dialog-form queue-input-dialog">
    <p className="dialog-note">{item.kind === "steering" ? "当前回合" : "后续回合"} · {queueStatusLabel(item)} · 只读展示持久化正文，关闭不会重新提交或修改队列。</p>
    {detail && <p className="dialog-note queue-input-detail">{detail}</p>}
    {(skillLabels.length > 0 || item.autoCompaction) && <div className="queue-input-facts">
      {skillLabels.length > 0 && <span title={skillLabels.join("、")}>技能：{skillLabels.join("、")}</span>}
      {item.autoCompaction && <span title={compactionTitle(item.autoCompaction)}>{compactionLabel(item.autoCompaction)}</span>}
    </div>}
    <pre className="turn-queue-full-input">{input || "（空输入）"}</pre>
    <div className="dialog-actions queue-input-actions">
      {copyFeedback && <span className={copyFeedback.ok ? "queue-input-copy-status" : "queue-input-copy-error"} role="status">
        {copyFeedback.ok ? "已复制完整输入" : `复制失败：${copyFeedback.reason}；正文仍在窗口中`}
      </span>}
      <button className="secondary-button" disabled={!input} title="复制持久化正文，不会重新提交或修改队列" onClick={onCopy}>复制完整输入</button>
    </div>
  </div>;
}

export function QueueInputDialog(props: {
  item: QueueItem;
  input: string;
  skillLabels: string[];
  retryAvailable: boolean;
  copyFeedback: CopyFeedback | null;
  onCopy: () => void;
  onClose: () => void;
}): JSX.Element {
  return <ModalSurface title="队列消息完整输入" onClose={props.onClose}>
    <QueueInputDialogContent item={props.item} input={props.input} skillLabels={props.skillLabels}
      retryAvailable={props.retryAvailable} copyFeedback={props.copyFeedback} onCopy={props.onCopy} />
  </ModalSurface>;
}
