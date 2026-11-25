/**
 * 资料库页面访问状态。
 *
 * 工作区页面切换时 `WorkspacePages` 保持挂载，筛选词因此可以跨页面保留；但文件详情
 * 是覆盖页面的临时浮层，只属于打开它的那次资料库访问。把页面与详情放在同一个状态
 * 对象里，页面变化时同步出新访问并丢弃旧详情，返回资料库不会自动重开上一次的弹窗。
 * 同步必须幂等：同一页面原样返回，调用方据此在渲染期同步而不会陷入循环。
 */
export interface LibraryVisit {
  /** 状态对应的页面；与当前 `page` 不一致时表示还停留在上一次访问。 */
  page: string;
  /** 当前访问打开的文件路径；没有打开详情时为 null。 */
  file: string | null;
}

/** 页面变化时开启新一次访问并丢弃详情；同一页面原样返回。 */
export function syncLibraryVisit(visit: LibraryVisit, page: string): LibraryVisit {
  return visit.page === page ? visit : { page, file: null };
}

/** 打开或关闭文件详情；路径没有变化时原样返回，避免多余的渲染。 */
export function withLibraryFile(visit: LibraryVisit, file: string | null): LibraryVisit {
  return visit.file === file ? visit : { ...visit, file };
}
