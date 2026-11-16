/**
 * 分页游标链。
 *
 * 单轮分页只允许不断前进到没见过的游标。异常内核若返回环状游标（A → B → A），
 * 只比较相邻游标会反复请求同一批页：列表重复渲染同一条目，会话恢复还会翻满
 * 页数上限。调用方在发出下一页请求前登记游标，重复即整体失败，不展示可疑数据。
 */
export function trackCursor(seen: Set<string>, next: string, label: string): void {
  if (seen.has(next)) throw new Error(`${label}分页未前进`);
  seen.add(next);
}
