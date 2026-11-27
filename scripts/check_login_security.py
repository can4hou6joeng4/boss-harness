#!/usr/bin/env python3
"""核对平台登录的官方域名、Cookie 选择与回执形状。

登录页在隔离分区里访问官方站点，成功后只把官方域的 Cookie 交给内核。域名判定、
Cookie 具体性选择、主进程与渲染层对登录回执的字段上限、失败诊断的脱敏都必须
一致：任何一处放宽都可能把非官方页面或无身份会话当成成功登录。验证页判定另外
从源码提取正则，对真实 passport 验证地址与近似路径做行为对照。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SECURITY = "apps/desktop/src/main/security.ts"
COOKIES = "apps/desktop/src/main/loginCookies.ts"
ATTEMPT = "apps/desktop/src/main/loginAttempt.ts"
STATE = "apps/desktop/src/renderer/src/data/platformLoginState.ts"
FAILURE = "apps/desktop/src/main/loginFailure.ts"

SECURITY_FRAGMENTS = (
    "export function isOfficialLoginUrl(url: string): boolean {",
    'return parsed.protocol === "https:" && !parsed.username && !parsed.password &&',
    '(!parsed.port || parsed.port === "443") &&',
    '(parsed.hostname === "zhipin.com" || parsed.hostname.endsWith(".zhipin.com"));',
    "export function isLoginVerificationUrl(url: string): boolean {",
    "try { return /(?:security-check|captcha|\\/verify(?:\\.html)?(?:\\/|$)|\\/security\\.html(?:\\/|$))/i.test(new URL(url).pathname); }",
    "catch { return true; }",
    "export function loginCaptureReadiness(url: string, cookies: Record<string, string>): {",
    "if (!isOfficialLoginUrl(url) || isLoginVerificationUrl(url)) {",
    'if (!cookies.wt2) return { ready: false, phase: "scan",',
    'const identity = /^\\/web\\/geek\\//.test(page.pathname) ? "jobSeeker"',
    ': /^\\/web\\/(?:boss|chat)\\//.test(page.pathname) ? "recruiter" : "unknown";',
    'if (page.hostname !== "www.zhipin.com" || !(page.pathname === "/" || /^\\/web\\/(?:geek|boss|chat)\\//.test(page.pathname))) {',
    "if (!cookies.__zp_stoken__) {",
    'return { ready: true, phase: "verify", identity, summary: "正在验证账号并保存连接，请稍候；此过程不会发送消息或修改职位" };',
    "export function loginViewBounds(value: unknown, content: { width: number; height: number }): PlatformLoginContext[\"bounds\"] | null {",
    'if (!["x", "y", "width", "height"].every(key => typeof bounds[key] === "number" && Number.isFinite(bounds[key]))) return null;',
    "if (x < 0 || y < 48 || width < 100 || height < 80 || x + width > content.width + 1 || y + height > content.height + 1) return null;",
    "return { x: Math.ceil(x), y: Math.ceil(y), width: Math.floor(width), height: Math.floor(height) };",
    "export function validateLoginContext(value: unknown): PlatformLoginContext {",
    'if (typeof context.threadId !== "string" || !/^[a-zA-Z0-9_-]{1,200}$/.test(context.threadId)) throw new Error("invalid login thread");',
    'if (context.browserId !== undefined && (typeof context.browserId !== "string" || context.browserId.length > 100)) throw new Error("invalid login browser");',
    'if (context.visible !== undefined && typeof context.visible !== "boolean") throw new Error("invalid login visibility");',
)
COOKIE_FRAGMENTS = (
    'const LOGIN_DOMAINS = new Set(["zhipin.com", "www.zhipin.com"]);',
    'const domain = cookie.domain?.replace(/^\\./, "").toLowerCase();',
    "return domain && LOGIN_DOMAINS.has(domain) ? domain : null;",
    "const hostOnly = (cookie: LoginCookie): number => cookie.hostOnly === true ? 1 : 0;",
    "if (hostOnly(a) !== hostOnly(b)) return hostOnly(a) - hostOnly(b);",
    "if (pathLength(a) !== pathLength(b)) return pathLength(a) - pathLength(b);",
    "return aDomain.length - bDomain.length;",
    "if (current.cookie.value === cookie.value) {",
    'if (order === 0) throw new Error("conflicting cookies");',
    "if (order > 0) chosen.set(cookie.name, { cookie, domain });",
    "const cookies: Record<string, string> = Object.create(null);",
    "for (const [name, entry] of chosen) cookies[name] = entry.cookie.value;",
    "return { cookies, superseded };",
)
PARITY_FRAGMENTS = (
    'const LOGIN_STATES: ReadonlySet<string> = new Set([\n  "idle", "opening", "waiting", "saving", "succeeded", "failed", "blocked", "cancelled", "disabled",\n]);',
    'const LOGIN_PHASES: ReadonlySet<string> = new Set(["scan", "confirm", "credentials", "verify"]);',
    'const LOGIN_IDENTITIES: ReadonlySet<string> = new Set(["jobSeeker", "recruiter", "unknown"]);',
    "const SUMMARY_LIMIT = 4096;",
    "const CODE_LIMIT = 120;",
    "const ID_LIMIT = 200;",
)
ATTEMPT_FRAGMENTS = (
    "export function attemptIdOf(value: unknown): string | undefined {",
    "return typeof id === \"string\" && id.length > 0 && id.length <= ID_LIMIT ? id : undefined;",
    "export function loginAttemptOf(value: unknown): LoginAttemptStatus | null {",
    'if (typeof raw.state !== "string" || !LOGIN_STATES.has(raw.state)) return null;',
    'if (typeof raw.summary !== "string" || raw.summary.length > SUMMARY_LIMIT) return null;',
    "if (raw.id !== undefined && (typeof raw.id !== \"string\" || raw.id.length === 0 || raw.id.length > ID_LIMIT)) return null;",
)
STATE_FRAGMENTS = (
    "export function platformLoginStatusOf(value: unknown): PlatformLoginStatus | null {",
    'if (typeof raw.state !== "string" || !LOGIN_STATES.has(raw.state)) return null;',
    'for (const key of ["threadId", "browserId"] as const) {',
    "if (item !== undefined && (typeof item !== \"string\" || item.length === 0 || item.length > ID_LIMIT)) return null;",
    'export const loginActive = (status: PlatformLoginStatus): boolean => ["opening", "waiting", "saving"].includes(status.state);',
)
FAILURE_FRAGMENTS = (
    "const data = value?.data && typeof value.data === \"object\" ? value.data as { code?: unknown } : null;",
    "const code = typeof data?.code === \"string\" && data.code ? data.code : undefined;",
    'const raw = typeof value?.message === "string" ? stripIpcErrorWrapper(value.message).trim() : "";',
    "return { ...(code ? { code } : {}), ...(raw ? { message: safeSlice(raw, 200) } : {}) };",
    'if (details?.reason === "clean-exit") return "官方登录页已关闭，请重新打开官方页面";',
)
#: 从 `security.ts` 提取验证页正则，避免另写一份副本造成漂移。
VERIFICATION_PATTERN = re.compile(
    r"return /(.+?)/i\.test\(new URL\(url\)\.pathname\);")
#: 上游 `auth/login_diagnostics.py` 登记的真实验证页，以及近似路径的不误判。
VERIFICATION_CASES = (
    ("https://www.zhipin.com/web/passport/zp/verify.html?callbackUrl=https%3A%2F%2Fwww.zhipin.com%2F", True),
    ("https://www.zhipin.com/web/passport/zp/security.html", True),
    ("https://www.zhipin.com/web/passport/zp/verify", True),
    ("https://www.zhipin.com/web/passport/zp/verify/step", True),
    ("https://www.zhipin.com/security-check", True),
    ("https://www.zhipin.com/captcha", True),
    ("https://www.zhipin.com/web/geek/job", False),
    ("https://www.zhipin.com/web/user/", False),
    ("https://www.zhipin.com/web/user/verify-settings", False),
    ("https://www.zhipin.com/web/passport/zp/security", False),
)


def _check_verification_urls(security: str) -> int:
    match = VERIFICATION_PATTERN.search(security)
    if not match:
        raise ValueError(f"{SECURITY} 缺少可提取的验证页正则")
    pattern = re.compile(match.group(1))
    for url, expected in VERIFICATION_CASES:
        actual = bool(pattern.search(urlsplit(url).path))
        if actual != expected:
            raise ValueError(f"{SECURITY} 验证页判定不符：{url} 期望 {expected}，实际 {actual}")
    return len(VERIFICATION_CASES)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_login_security() -> int:
    security = _read(SECURITY)
    cookies = _read(COOKIES)
    attempt = _read(ATTEMPT)
    state = _read(STATE)
    failure = _read(FAILURE)
    checked = 0
    checked += _expect(SECURITY_FRAGMENTS, security, SECURITY)
    checked += _expect(COOKIE_FRAGMENTS, cookies, COOKIES)
    checked += _expect(ATTEMPT_FRAGMENTS, attempt, ATTEMPT)
    checked += _expect(STATE_FRAGMENTS, state, STATE)
    checked += _expect(FAILURE_FRAGMENTS, failure, FAILURE)
    for fragment in PARITY_FRAGMENTS:
        if fragment not in attempt or fragment not in state:
            raise ValueError(f"登录回执上限在 {ATTEMPT} 与 {STATE} 不一致：{fragment}")
        checked += 1
    # 官方地址：协议、端口与主机名的判定顺序。
    checked += _ordered(
        (
            'return parsed.protocol === "https:" && !parsed.username && !parsed.password &&',
            '(!parsed.port || parsed.port === "443") &&',
            '(parsed.hostname === "zhipin.com" || parsed.hostname.endsWith(".zhipin.com"));',
        ),
        security,
        SECURITY,
    )
    # 抓取就绪：先排除非官方与验证页，再看扫码与认证信息。
    checked += _ordered(
        (
            "if (!isOfficialLoginUrl(url) || isLoginVerificationUrl(url)) {",
            "if (!cookies.wt2) return { ready: false, phase: \"scan\",",
            'if (page.hostname !== "www.zhipin.com"',
            "if (!cookies.__zp_stoken__) {",
            'return { ready: true, phase: "verify", identity,',
        ),
        security,
        SECURITY,
    )
    # Cookie：同值跳过、真正歧义失败、更具体者胜出。
    checked += _ordered(
        (
            "if (current.cookie.value === cookie.value) {",
            'if (order === 0) throw new Error("conflicting cookies");',
            "if (order > 0) chosen.set(cookie.name, { cookie, domain });",
        ),
        cookies,
        COOKIES,
    )
    # 验证页：真实 passport 地址命中，近似路径不误判。
    checked += _check_verification_urls(security)
    # 反向断言：验证页判定必须失败关闭；Cookie 只能来自官方登录域。
    if "catch { return true; }" not in security:
        raise ValueError(f"{SECURITY} 的验证页判定必须失败关闭")
    if "LOGIN_DOMAINS.has(domain)" not in cookies:
        raise ValueError(f"{COOKIES} 必须只接受官方登录域")
    return checked + 2


def main() -> int:
    try:
        checked = check_login_security()
    except ValueError as error:
        print(f"平台登录安全核对失败，{error}", file=sys.stderr)
        return 2
    print(f"平台登录安全一致：{checked} 项域名、Cookie 与回执防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
