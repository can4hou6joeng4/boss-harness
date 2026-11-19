#!/usr/bin/env python3
"""核对渲染层失败恢复与静态诊断页边界。

主窗口隐藏创建、等 `ready-to-show` 才显示，渲染层加载失败时必须主动显示窗口并留下
原因。崩溃恢复只在滚动窗口内有限次重载，超出预算改为无脚本、无外链的静态页；诊断
文本先做代理对修复、截断与 HTML 转义，再放进 data URL。被新导航取代的旧加载以
`ERR_ABORTED` 失败，不能当成界面加载失败报告。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = "apps/desktop/src/main/rendererRecovery.ts"
LOAD = "apps/desktop/src/main/rendererLoadFailure.ts"
PAGE = "apps/desktop/src/main/rendererFailure.ts"
WINDOW = "apps/desktop/src/main/window.ts"

RECOVERY_FRAGMENTS = (
    "export const RENDERER_CRASH_RELOAD_LIMIT = 2;",
    "export const RENDERER_CRASH_WINDOW_MS = 120_000;",
    '"abnormal-exit": "异常退出",',
    'killed: "被终止",',
    'crashed: "崩溃",',
    'oom: "内存不足",',
    '"launch-failed": "启动失败",',
    '"integrity-failure": "完整性校验失败",',
    'if (typeof reason !== "string" || !reason.trim()) return "未知原因";',
    "const known = Object.prototype.hasOwnProperty.call(REASON_LABELS, reason) ? REASON_LABELS[reason] : undefined;",
    "return known ?? reason;",
    'const rawReason = typeof details?.reason === "string" ? details.reason.trim() : "";',
    'const reason = rawReason || "unknown";',
    'const label = rawReason ? rendererGoneReasonLabel(rawReason) : "未知原因";',
    'const code = typeof details?.exitCode === "number" && Number.isSafeInteger(details.exitCode)',
    '? `，退出码 ${details.exitCode}` : "";',
    "return `${label}（${reason}${code}）`;",
    'const maxReloads = typeof options.maxReloads === "number" && Number.isSafeInteger(options.maxReloads) && options.maxReloads >= 0',
    "? options.maxReloads : RENDERER_CRASH_RELOAD_LIMIT;",
    'const windowMs = typeof options.windowMs === "number" && Number.isFinite(options.windowMs) && options.windowMs > 0',
    "? options.windowMs : RENDERER_CRASH_WINDOW_MS;",
    'const clock = typeof now === "number" && Number.isFinite(now) ? now : 0;',
    'previousReloads.filter(item => typeof item === "number" && Number.isFinite(item)',
    "&& item <= clock && item > clock - windowMs)",
    'if (!details || details.reason === "clean-exit") return { action: "ignore", reloads };',
    'if (reloads.length < maxReloads) return { action: "reload", reloads: [...reloads, clock] };',
    'message: `界面进程连续异常退出：${rendererGoneSummary(details)}；已自动重载 ${maxReloads} 次仍未恢复。`,',
)
LOAD_FRAGMENTS = (
    "export const NAVIGATION_ABORTED_ERRNO = -3;",
    'if (typeof error !== "object" || error === null) return false;',
    "const failure = error as NavigationFailure;",
    'return failure.errno === NAVIGATION_ABORTED_ERRNO || failure.code === "ERR_ABORTED";',
    "return isCurrent && !isAbortedNavigation(error);",
)
PAGE_FRAGMENTS = (
    'heading: "界面未能加载",',
    'hint: "正式构建请重新运行 npm run build；开发模式请确认渲染进程开发服务器已启动后重启应用。",',
    'heading: "界面进程已停止",',
    'hint: "会话与回合记录保存在本地内核，重新打开应用后可继续。若反复出现，请记录上面的原因并向项目反馈。",',
    "const LONE_SURROGATE = /[\\uD800-\\uDBFF](?![\\uDC00-\\uDFFF])|(?<![\\uD800-\\uDBFF])[\\uDC00-\\uDFFF]/g;",
    'return text.replace(LONE_SURROGATE, "�");',
    'const detail = wellFormed(safeSlice(input.detail.trim(), 300)) || "未知原因";',
    "&amp;",
    "&lt;",
    "&gt;",
    "&quot;",
    "&#39;",
    "<title>${escape(input.heading)}</title>",
    '<h1 style="margin:0 0 12px;font-size:18px">${escape(input.heading)}</h1>',
    "escape(detail)",
    "escape(input.hint)",
    "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
    "return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;",
)
WINDOW_FRAGMENTS = (
    "const reportFailure = (cause: string): void => {",
    "if (failureReported || window.isDestroyed() || window.webContents.isDestroyed()) return;",
    "failureReported = true;",
    'console.error("renderer load failed", cause);',
    "void window.loadURL(rendererFailurePage(cause))",
    "if (!window.isVisible()) window.show();",
    "if (!mainFrame || errorCode === -3) return;",
    "const load = devUrl ? window.loadURL(devUrl) : window.loadFile(entryFile);",
    "activeLoad = load;",
    "const showCrashPage = (cause: string): void => {",
    "activeLoad = null;",
    "void window.loadURL(rendererCrashPage(cause))",
    'window.webContents.on("render-process-gone", (_event, details) => {',
    "const decision = decideRendererRecovery(details, crashReloads, Date.now());",
    "crashReloads = decision.reloads;",
    'if (decision.action === "ignore" || window.isDestroyed() || window.webContents.isDestroyed()) return;',
    'if (decision.action === "reload") {',
    "if (!shouldReportLoadFailure(error, activeLoad === load)) return;",
    "showCrashPage(`界面进程异常退出：${rendererGoneSummary(details)}；自动重载失败：${reason(error)}`);",
    "const cause = decision.message ?? `界面进程异常退出：${rendererGoneSummary(details)}。`;",
    'console.error("renderer process gone; recovery exhausted", cause);',
    "const initialLoad = loadRenderer();",
    "if (!shouldReportLoadFailure(error, activeLoad === initialLoad)) return;",
    "reportFailure(`${devUrl ?? entryFile}：${reason(error)}`);",
)


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


def check_renderer_recovery() -> int:
    recovery = _read(RECOVERY)
    load = _read(LOAD)
    page = _read(PAGE)
    window = _read(WINDOW)
    checked = 0
    checked += _expect(RECOVERY_FRAGMENTS, recovery, RECOVERY)
    checked += _expect(LOAD_FRAGMENTS, load, LOAD)
    checked += _expect(PAGE_FRAGMENTS, page, PAGE)
    checked += _expect(WINDOW_FRAGMENTS, window, WINDOW)
    # 恢复预算：参数逐项校验，滚动窗口过滤后再决定忽略 / 重载 / 报告。
    checked += _ordered(
        (
            "const maxReloads = typeof options.maxReloads",
            "const windowMs = typeof options.windowMs",
            "const clock = typeof now === \"number\"",
            "previousReloads.filter(item => typeof item === \"number\"",
            'if (!details || details.reason === "clean-exit") return { action: "ignore", reloads };',
            "if (reloads.length < maxReloads) return { action: \"reload\", reloads: [...reloads, clock] };",
            'action: "report",',
        ),
        recovery,
        RECOVERY,
    )
    # 加载失败：先判定当前导航，再显示窗口并留下固定诊断页。
    checked += _ordered(
        (
            "const reportFailure = (cause: string): void => {",
            "if (failureReported || window.isDestroyed() || window.webContents.isDestroyed()) return;",
            "failureReported = true;",
            "void window.loadURL(rendererFailurePage(cause))",
            "if (!window.isVisible()) window.show();",
        ),
        window,
        WINDOW,
    )
    # 崩溃：决策 → 保存预算 → 忽略退出 → 重载或诊断页。
    checked += _ordered(
        (
            'window.webContents.on("render-process-gone", (_event, details) => {',
            "const decision = decideRendererRecovery(details, crashReloads, Date.now());",
            "crashReloads = decision.reloads;",
            'if (decision.action === "ignore" || window.isDestroyed() || window.webContents.isDestroyed()) return;',
            'if (decision.action === "reload") {',
            "if (!shouldReportLoadFailure(error, activeLoad === load)) return;",
            "const cause = decision.message ??",
            "showCrashPage(cause);",
        ),
        window,
        WINDOW,
    )
    # 反向断言：诊断页不得含脚本或外链，已知原因查表不得走原型链。
    for forbidden in ("<script", "src=", "http://", "https://"):
        if forbidden in page:
            raise ValueError(f"{PAGE} 的诊断页不得包含 {forbidden}")
    if "reason in REASON_LABELS" in recovery:
        raise ValueError(f"{RECOVERY} 的已知原因查表不得使用 in 运算符")
    return checked + 1


def main() -> int:
    try:
        checked = check_renderer_recovery()
    except ValueError as error:
        print(f"渲染层恢复边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"渲染层恢复边界一致：{checked} 项预算、诊断页与导航防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
