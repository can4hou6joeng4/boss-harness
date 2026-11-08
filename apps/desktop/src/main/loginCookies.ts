/**
 * 平台登录 cookie 的选择规则。
 *
 * Electron 的 cookie 存储允许同名 cookie 按域（host-only 与 domain）或路径并存，
 * `cookies.get` 会一起返回；内核只需要一份 `name → value` 映射。这里按浏览器语义
 * 选择更具体的一条：host-only 优先于 domain cookie，路径更长优先，域更长优先。
 * 只有域、路径与 host-only 完全相同的真正歧义才继续硬失败，避免静默连到未知身份的会话。
 */

export interface LoginCookie {
  name: string;
  value: string;
  domain?: string;
  path?: string;
  hostOnly?: boolean;
}

export interface LoginCookieSelection {
  cookies: Record<string, string>;
  /** 被更具体（或同值）同名 cookie 覆盖的条数；只用于日志，不含值。 */
  superseded: number;
}

/** 只接受官方登录域；`.zhipin.com` 归一后与 `zhipin.com` 相同。 */
const LOGIN_DOMAINS = new Set(["zhipin.com", "www.zhipin.com"]);

function loginDomain(cookie: LoginCookie): string | null {
  const domain = cookie.domain?.replace(/^\./, "").toLowerCase();
  return domain && LOGIN_DOMAINS.has(domain) ? domain : null;
}

function pathLength(cookie: LoginCookie): number {
  return (cookie.path ?? "/").length;
}

/** > 0 表示 a 更具体；0 表示域、路径与 host-only 完全相同。 */
function compareSpecificity(a: LoginCookie, aDomain: string, b: LoginCookie, bDomain: string): number {
  const hostOnly = (cookie: LoginCookie): number => cookie.hostOnly === true ? 1 : 0;
  if (hostOnly(a) !== hostOnly(b)) return hostOnly(a) - hostOnly(b);
  if (pathLength(a) !== pathLength(b)) return pathLength(a) - pathLength(b);
  return aDomain.length - bDomain.length;
}

export function selectLoginCookies(values: readonly LoginCookie[]): LoginCookieSelection {
  const chosen = new Map<string, { cookie: LoginCookie; domain: string }>();
  let superseded = 0;
  for (const cookie of values) {
    const domain = loginDomain(cookie);
    if (!domain) continue;
    const current = chosen.get(cookie.name);
    if (!current) {
      chosen.set(cookie.name, { cookie, domain });
      continue;
    }
    if (current.cookie.value === cookie.value) {
      superseded += 1;
      continue;
    }
    const order = compareSpecificity(cookie, domain, current.cookie, current.domain);
    if (order === 0) throw new Error("conflicting cookies");
    if (order > 0) chosen.set(cookie.name, { cookie, domain });
    superseded += 1;
  }
  const cookies: Record<string, string> = Object.create(null);
  for (const [name, entry] of chosen) cookies[name] = entry.cookie.value;
  return { cookies, superseded };
}
