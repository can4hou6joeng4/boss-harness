/**
 * 变更审阅的临时状态与目标会话。
 *
 * `UnifiedDiffModal` 关闭时只返回 `null`，组件实例仍挂载，文件下标与对比模式会跨
 * 关闭残留；可见性变化时开启新一次审阅并复位。目标会话则在打开时固定：背景会话
 * 切换后审阅必须立即关闭，否则弹窗内容会静默换成另一会话的变更。
 */
export type DiffReviewMode = "unified" | "split";

/** 一次审阅内的界面状态。 */
export interface DiffReviewVisit {
  open: boolean;
  selected: number;
  mode: DiffReviewMode;
}

/** 可见性变化时复位文件下标与对比模式；同一可见性保持原对象。 */
export function syncDiffReviewVisit(visit: DiffReviewVisit, open: boolean): DiffReviewVisit {
  return visit.open === open ? visit : { open, selected: 0, mode: "unified" };
}

/** 选择文件；下标未变化时原样返回。 */
export function withDiffReviewFile(visit: DiffReviewVisit, selected: number): DiffReviewVisit {
  return visit.selected === selected ? visit : { ...visit, selected };
}

/** 切换对比模式；模式未变化时原样返回。 */
export function withDiffReviewMode(visit: DiffReviewVisit, mode: DiffReviewMode): DiffReviewVisit {
  return visit.mode === mode ? visit : { ...visit, mode };
}

/** 只显示打开时绑定的会话；目标缺失或当前会话不匹配时关闭。 */
export function diffReviewVisible(open: boolean, targetThreadId: string | null, activeThreadId: string | null): boolean {
  return open && targetThreadId !== null && targetThreadId === activeThreadId;
}
