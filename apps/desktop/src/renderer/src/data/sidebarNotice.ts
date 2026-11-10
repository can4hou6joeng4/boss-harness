/**
 * 侧栏操作回执（复制路径、复制 id 等）。
 *
 * 连续两次复制同一内容时文案完全相同；若状态只存字符串，React 会认为没有变化，
 * 计时器不会重排、`role="status"` 也不会重新播报。因此每次都生成新记录并递增
 * `seq`：组件按 `seq` 作为 key 重建提示节点，计时器依赖整条记录而不是文案。
 */
export type SidebarNotice = { text: string; seq: number };

export const EMPTY_SIDEBAR_NOTICE: SidebarNotice = { text: "", seq: 0 };

/** 提示停留时长（毫秒）；从每次新的回执开始计算。 */
export const SIDEBAR_NOTICE_TIMEOUT_MS = 2600;

export function nextSidebarNotice(current: SidebarNotice, text: string): SidebarNotice {
  return { text, seq: current.seq + 1 };
}

/** 计时器到点后清空文案；已经为空时返回原对象，避免无意义的状态更新。 */
export function clearSidebarNotice(current: SidebarNotice): SidebarNotice {
  return current.text ? { ...current, text: "" } : current;
}
