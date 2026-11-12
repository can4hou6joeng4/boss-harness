import { useState, useSyncExternalStore } from "react";
import type { QueueItem } from "@boss-harness/protocol";
import { harnessErrorText } from "./harnessBridge";

/** 一条排队消息的未保存编辑：条目快照用于条目移出队列后仍可核对与复制。 */
export interface QueueEditDraft {
  item: QueueItem;
  draft: string;
  originalInput: string;
}
interface QueueEditorState {
  editing: QueueEditDraft | null;
  saving: boolean;
  editError: string;
}
type DraftChange = QueueEditDraft | null | ((current: QueueEditDraft | null) => QueueEditDraft | null);

/** 编辑正文与保存回执共用生命周期，不能随对话区卸载而遗忘提交锁或迟到结果。 */
function createEditor() {
  let state: QueueEditorState = { editing: null, saving: false, editError: "" };
  const listeners = new Set<() => void>();
  const update = (next: QueueEditorState) => {
    if (next === state) return;
    state = next;
    for (const listener of listeners) listener();
  };
  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },
    setEditing: (change: DraftChange) => {
      const editing = typeof change === "function" ? change(state.editing) : change;
      if (editing !== state.editing) update({ ...state, editing });
    },
    setEditError: (editError: string) => {
      if (editError !== state.editError) update({ ...state, editError });
    },
    saveEditing: async (write: (draft: QueueEditDraft) => Promise<unknown>) => {
      const submitted = state.editing;
      // 同步持有锁：通知切回后的新组件也不能在原回执到达前再次提交。
      if (!submitted || state.saving) return;
      update({ ...state, saving: true, editError: "" });
      try {
        await write(submitted);
        // 即使没有任何组件订阅，成功仍须清除原会话草稿，避免下次打开复活旧正文。
        update({ editing: null, saving: false, editError: "" });
      } catch (cause) {
        update({ ...state, saving: false, editError: `保存失败：${harnessErrorText(cause)}。草稿仍保留在编辑框中。` });
      }
    },
  };
}

/** 仅保存在应用内存，按会话隔离；导航不取消写入，也不自动重放失败的保存。 */
const editors = new Map<string, ReturnType<typeof createEditor>>();

export function useQueueEditor(threadId?: string) {
  // 未关联会话时沿用组件自身生命周期，不把匿名面板的正文混进会话缓存。
  const [localEditor] = useState(createEditor);
  let editor = localEditor;
  if (threadId) {
    const existing = editors.get(threadId);
    if (existing) editor = existing;
    else { editor = createEditor(); editors.set(threadId, editor); }
  }
  const state = useSyncExternalStore(editor.subscribe, editor.getSnapshot);
  return { ...state, setEditing: editor.setEditing, setEditError: editor.setEditError, saveEditing: editor.saveEditing };
}
