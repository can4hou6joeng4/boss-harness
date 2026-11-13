import { UI_STORAGE_PREFIX } from "./uiStorage";

/**
 * 上次打开的会话 id 的本地存储键。启动时据此回到上次会话；停在首页（新建任务）或
 * 上次会话已删除时不记录，启动仍从首页开始。
 */
export const LAST_SESSION_KEY = UI_STORAGE_PREFIX + "lastSession";
/** 会话 id 由内核生成；超过这个长度按损坏记录处理，不拿来打开或恢复。 */
const MAX_SESSION_ID_LENGTH = 200;

/** 解析存储值；空白、超长或带首尾空白都视为没有可恢复的会话。 */
export function parseLastSessionId(raw: string | null): string | null {
  if (typeof raw !== "string") return null;
  const id = raw.trim();
  if (!id || id.length > MAX_SESSION_ID_LENGTH || id !== raw) return null;
  return id;
}

export function readLastSessionId(): string | null {
  try {
    return parseLastSessionId(localStorage.getItem(LAST_SESSION_KEY));
  } catch {
    // 隐私模式或存储被禁用：启动从首页开始，不影响本次使用。
    return null;
  }
}

/** 记录当前会话；传 null 表示停在首页或没有可恢复的会话，下次启动不恢复。 */
export function rememberLastSessionId(id: string | null): void {
  try {
    if (id) localStorage.setItem(LAST_SESSION_KEY, id);
    else localStorage.removeItem(LAST_SESSION_KEY);
  } catch {
    // 存储不可用时不恢复上次会话，不影响本次运行。
  }
}
