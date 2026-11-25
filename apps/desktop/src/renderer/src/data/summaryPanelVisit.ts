/**
 * 摘要面板临时 UI 状态。
 *
 * `RightPanel` 在关闭时返回 `null` 但保持挂载；`menu` 与 `expanded` 因此会跨关闭
 * 残留，下次展开无需点击就出现菜单并抢走焦点。把可见性与临时状态放进同一个对象，
 * 可见性变化时开启新一次访问并复位临时状态；同一可见性原样返回，以便调用方在
 * 渲染期幂等同步。
 */
export interface SummaryPanelVisit {
  /** 对象对应的面板可见性；与当前 `isOpen` 不一致时表示临时状态尚未复位。 */
  open: boolean;
  /** 「摘要选项」菜单是否展开。 */
  menu: boolean;
  /** 「来源」详情是否展开。 */
  expanded: boolean;
}

/** 面板可见性变化时复位临时状态；同一可见性保持原对象。 */
export function syncSummaryPanelVisit(visit: SummaryPanelVisit, open: boolean): SummaryPanelVisit {
  return visit.open === open ? visit : { open, menu: false, expanded: false };
}

/** 展开或关闭菜单；状态未变化时原样返回。 */
export function withSummaryPanelMenu(visit: SummaryPanelVisit, menu: boolean): SummaryPanelVisit {
  return visit.menu === menu ? visit : { ...visit, menu };
}

/** 展开或收起来源详情；状态未变化时原样返回。 */
export function withSummaryPanelExpanded(visit: SummaryPanelVisit, expanded: boolean): SummaryPanelVisit {
  return visit.expanded === expanded ? visit : { ...visit, expanded };
}
