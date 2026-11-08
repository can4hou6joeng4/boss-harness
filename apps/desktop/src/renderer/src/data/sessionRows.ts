import type { ProjectFolder, SessionItem } from "./mockData";
import { parseIsoDateTime } from "./timeFormat";

export interface SessionRow { session: SessionItem; project: string; }
export interface SessionRowOptions { includeArchived?: boolean }

export function sessionRows(folders: ProjectFolder[], query = "", options: SessionRowOptions = {}): SessionRow[] {
  const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("zh-CN");
  const keywords = normalize(query).trim().split(/\s+/).filter(Boolean);
  const seen = new Set<string>();
  // 坏时间与缺失时间同样按 0 处理，落到列表末尾；不再被 Date.parse 猜成 2001 年之类的位置。
  const timestamp = (session: SessionItem) => parseIsoDateTime(session.updatedAt)?.getTime() ?? 0;
  return folders.flatMap(folder => folder.sessions.map(session => ({ session, project: folder.name })))
    .filter(row => {
      // 已归档聊天默认只在侧栏「已归档」分组出现；只有显式要求时才纳入全局搜索。
      if (row.session.archived === true && options.includeArchived !== true) return false;
      if (seen.has(row.session.id)) return false;
      seen.add(row.session.id);
      const text = normalize(`${row.session.title} ${row.project}`);
      return keywords.every(keyword => text.includes(keyword));
    })
    .sort((a, b) => timestamp(b.session) - timestamp(a.session));
}
