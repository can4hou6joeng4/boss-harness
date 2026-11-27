#!/usr/bin/env python3
"""运行时核对登录面板状态机：广播、回执、锁与按会话可见性。

`usePlatformLogin.ts` 把主进程广播、初始状态读取、`open` / `cancel` 回执与
界面可见性编排在一起。这里把真实模块复制到临时目录，`react` 替换为可重复
渲染的最小 hook 运行时桩，`./harnessBridge` 替换为桩，`window.boss`、
`requestAnimationFrame` 与 `document` 用可控桩，由 Node 直接加载真实模块，
核对迟到回执丢弃、卸载退订、`open` / `cancel` 的锁与失败回落，以及
`show` / `visibleIn` 的分支。结构侧另核对主进程截止与取消回执的终态优先：
超时、保存失败、连接中断与回执无法识别都允许内核终态收敛界面；
登录入口在归属会话已删除时先取消旧 attempt。主进程行为侧把真实
`platformLogin.ts` 复制到临时目录，替换 Electron、协议、安全与登录依赖为桩，
由 Node 加载真实类，覆盖截止警告、四种终态与启动失败分界。文档侧核对技术参考的计数，
以及桌面指南的平台登录入口、安全验证、五分钟等待、保存终态与隔离边界。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
GUIDE = "docs/DESKTOP_GUIDE.md"
SOURCE = "apps/desktop/src/renderer/src/data/usePlatformLogin.ts"
STATE = "apps/desktop/src/renderer/src/data/platformLoginState.ts"
MAIN = "apps/desktop/src/main/platformLogin.ts"
SHELL = "apps/desktop/src/renderer/src/shell/AppShell.tsx"

EXPECTED = 38
MAIN_EXPECTED = 9

#: 桌面指南必须保留的稳定事实：用户入口、安全验证、等待上限、保存终态与隔离边界。
GUIDE_FRAGMENTS = (
    "## 平台登录",
    "passport 安全验证页时，应用暂停连接",
    "等待仍从开始起最多保留五分钟",
    "只有内核回执成功才显示「BOSS 直聘已连接」",
    "只允许 HTTPS 的官方 `zhipin.com` 与子域名",
    "候选人功能需要招聘者身份",
)

#: 主进程截止：保存阶段超时保留警告。
DEADLINE_ORDER = (
    'const saving = this.status.state === "saving";',
    "this.cancel();",
    "summary: saving",
    '"等待已超过五分钟，保存已停止，登录态可能已更新，请手动检查后再重新登录"',
)
#: 主进程取消：取消回执的终态优先，不把已保存的登录显示成未知或已取消。
CANCEL_ORDER = (
    "const generation = this.generation;",
    'const settled = this.status.state === "cancelled"',
    "if (!settled) return;",
    'if (result.state === "succeeded" || result.state === "failed") this.update(result);',
)
#: 这些保存未知结果的失败码都允许取消回执带回内核终态。
TERMINAL_CODES = (
    "LOGIN_TIMEOUT", "LOGIN_SAVE_FAILED", "LOGIN_CONNECTION_LOST", "LOGIN_READBACK_INVALID",
)
#: 登录入口：归属会话已删除时先取消旧 attempt，再选择目标会话。
SHELL_ORDER = (
    'const activeLogin = ["opening", "waiting", "saving"].includes(login.status.state);',
    "if (activeLogin && !owner && props.sessionsLoaded === true && login.status.threadId) {",
    "await login.cancel(login.status.threadId);",
    "const target = owner ?? (!props.isHomeView ? props.activeSession : null)",
)

REACT_STUB = """\
export interface Slot {
  value: unknown;
}

export const slots: Slot[] = [];
export let effectCleanup: (() => void) | undefined;
let renderIndex = 0;
let mounted = false;

export function beginRender(): void {
  renderIndex = 0;
}

export function reset(): void {
  slots.length = 0;
  renderIndex = 0;
  mounted = false;
  effectCleanup = undefined;
}

export function useState<T>(init: T | (() => T)): [T, (next: T | ((prev: T) => T)) => void] {
  const index = renderIndex++;
  if (!slots[index]) {
    slots[index] = { value: typeof init === "function" ? (init as () => T)() : init };
  }
  const slot = slots[index];
  const set = (next: T | ((prev: T) => T)) => {
    slot.value = typeof next === "function" ? (next as (prev: T) => T)(slot.value) : next;
  };
  return [slot.value as T, set];
}

export function useRef<T>(initial: T): { current: T } {
  const index = renderIndex++;
  if (!slots[index]) {
    slots[index] = { value: { current: initial } };
  }
  return slots[index].value as { current: T };
}

export function useEffect(run: () => void | (() => void)): void {
  if (mounted) return;
  mounted = true;
  const cleanup = run();
  effectCleanup = typeof cleanup === "function" ? cleanup : undefined;
}
"""

BRIDGE_STUB = """\
export function harnessErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
"""

NODE_SCRIPT = """\
import { usePlatformLogin } from "./usePlatformLogin.ts";
import { beginRender, effectCleanup, reset } from "./reactStub.ts";

interface StatusLike {
  state: string;
  summary: string;
  threadId?: string;
  browserId?: string;
}
interface View {
  status: StatusLike;
  panelThreadId: string | null;
  choiceThreadId: string | null;
  busy: boolean;
  error: { threadId: string; message: string } | null;
  expanded: boolean;
  open: (threadId: string) => Promise<void>;
  cancel: (threadId: string) => Promise<void>;
  show: (threadId: string) => void;
  dismiss: (threadId: string) => void;
  toggleExpanded: () => void;
  hideForLater: () => void;
  closePanel: () => void;
  visibleIn: (threadId: string) => boolean;
}
interface Deferred {
  promise: Promise<unknown>;
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}
interface BossHandles {
  calls: Array<{ method: string; payload?: unknown }>;
  pending: Deferred[];
  emit: (raw: unknown) => void;
  unsubscribeCount: () => number;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

function deferred(): Deferred {
  let resolve!: (value: unknown) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

let focused = 0;
(globalThis as { requestAnimationFrame?: unknown }).requestAnimationFrame =
  (callback: () => void) => { callback(); };
(globalThis as { document?: unknown }).document = {
  querySelector: () => ({ focus: () => { focused += 1; } }),
};

function installBoss(): BossHandles {
  const calls: Array<{ method: string; payload?: unknown }> = [];
  const pending: Deferred[] = [];
  let handler: ((raw: unknown) => void) | undefined;
  let unsubscribed = 0;
  (globalThis as { window?: unknown }).window = {
    boss: {
      onPlatformLogin(callback: (raw: unknown) => void) {
        handler = callback;
        return () => { unsubscribed += 1; };
      },
      platformLogin(method: string, payload?: unknown) {
        calls.push({ method, payload });
        const next = deferred();
        pending.push(next);
        return next.promise;
      },
    },
  };
  return {
    calls,
    pending,
    emit: (raw: unknown) => { handler?.(raw); },
    unsubscribeCount: () => unsubscribed,
  };
}

const flush = () => new Promise<void>(resolve => setTimeout(resolve, 0));
const render = (): View => { beginRender(); return usePlatformLogin() as unknown as View; };
const unmount = (): void => { effectCleanup?.(); };

async function run(): Promise<void> {
  reset();
  (globalThis as { window?: unknown }).window = {};
  let view = render();
  expect("无 boss 时保持初始空闲", view.status.state === "idle" && view.status.summary === "尚未开始登录");
  expect("无 boss 时面板与选择为空", view.panelThreadId === null && view.choiceThreadId === null);
  expect("无 boss 时默认字段", view.busy === false && view.error === null && view.expanded === false);

  reset();
  let boss = installBoss();
  view = render();
  expect("挂载后订阅并读取一次状态", boss.calls.length === 1 && boss.calls[0].method === "status");
  boss.pending[0].resolve({ state: "idle", summary: "读取成功" });
  await flush();
  view = render();
  expect("初始回执更新状态", view.status.summary === "读取成功");

  reset();
  boss = installBoss();
  view = render();
  boss.pending[0].resolve({ state: "未知状态" });
  await flush();
  view = render();
  view.show("t1");
  view = render();
  expect(
    "非法初始回执经展示提示",
    view.error !== null && view.error.message.includes("无法读取上一次登录状态：回执无法识别") && view.error.message.includes("若此前已发起过登录"),
  );

  reset();
  boss = installBoss();
  view = render();
  boss.pending[0].reject(new Error("boom"));
  await flush();
  view = render();
  view.show("t1");
  view = render();
  expect(
    "初始读取失败经展示提示",
    view.error !== null && view.error.message.includes("无法读取上一次登录状态：boom"),
  );

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  view = render();
  expect("合法广播更新状态", view.status.threadId === "t1" && view.status.summary === "等待扫码");
  boss.emit({ state: "无此状态" });
  view = render();
  expect("非法广播保留上一次状态", view.status.threadId === "t1" && view.status.summary === "等待扫码");
  view.show("t1");
  view = render();
  expect("非法广播经展示提示", view.error !== null && view.error.message.includes("登录状态更新无法识别"));

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1" });
  boss.pending[0].resolve({ state: "idle", summary: "旧回执" });
  await flush();
  view = render();
  expect("迟到的初始回执被丢弃", view.status.summary === "等待扫码");

  reset();
  boss = installBoss();
  view = render();
  unmount();
  expect("卸载时退订", boss.unsubscribeCount() === 1);
  boss.emit({ state: "waiting", summary: "卸载后", threadId: "t1" });
  view = render();
  expect("卸载后广播不再更新状态", view.status.state === "idle");

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1" });
  view = render();
  view.show("t1");
  view = render();
  expect("show 对活跃会话打开面板", view.panelThreadId === "t1" && view.choiceThreadId === null);
  view.show("t2");
  view = render();
  expect("show 对其他会话进入选择", view.choiceThreadId === "t2" && view.panelThreadId === "t1");

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1" });
  view = render();
  view.show("t1");
  view = render();
  view.dismiss("t1");
  view = render();
  expect("dismiss 后不再可见", view.visibleIn("t1") === false && view.panelThreadId === null);
  view.show("t1");
  view = render();
  expect("show 清除该会话的隐藏记录", view.visibleIn("t1") === true);

  reset();
  boss = installBoss();
  view = render();
  const opening = view.open("t1");
  view = render();
  expect("open 立即持锁并打开面板", view.busy === true && view.panelThreadId === "t1" && boss.calls.length === 2);
  const duplicate = view.open("t1");
  expect("open 期间重复调用被忽略", boss.calls.length === 2);
  boss.pending[1].resolve({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  await opening;
  await duplicate;
  view = render();
  expect("open 成功更新状态并解锁", view.status.summary === "等待扫码" && view.busy === false);

  reset();
  boss = installBoss();
  view = render();
  const rejected = view.open("t1");
  boss.pending[1].resolve({ state: "无此状态" });
  await rejected;
  view = render();
  expect(
    "open 非法回执回落失败态",
    view.status.state === "failed" && view.panelThreadId === null && view.error !== null
      && view.error.message.includes("无法启动登录：登录状态回执无法识别"),
  );

  reset();
  boss = installBoss();
  view = render();
  const failing = view.open("t1");
  boss.pending[1].reject(new Error("boom"));
  await failing;
  view = render();
  expect(
    "open 失败保留可读原因",
    view.status.state === "failed" && view.error !== null && view.error.message.includes("无法启动登录：boom"),
  );

  reset();
  boss = installBoss();
  view = render();
  const ownedElsewhere = view.open("t2");
  boss.pending[1].reject(new Error("another thread owns this login"));
  await ownedElsewhere;
  view = render();
  expect(
    "另一会话占用登录时指向该会话",
    view.error !== null && view.error.message.includes("已有另一个会话在等待登录")
      && !view.error.message.includes("请检查本机连接后重试"),
  );

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  view = render();
  const active = view.open("t1");
  await active;
  view = render();
  expect("已活跃会话不重复发起登录", boss.calls.length === 1 && view.panelThreadId === "t1");

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1" });
  view = render();
  await view.cancel("t1");
  expect("缺少 browserId 时不取消", boss.calls.length === 1);

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  view = render();
  view.show("t1");
  view = render();
  const beforeCancelFocus = focused;
  const cancelling = view.cancel("t1");
  view = render();
  expect("cancel 立即持锁", view.busy === true);
  boss.pending[1].resolve({ state: "cancelled", summary: "已取消" });
  await cancelling;
  view = render();
  expect("cancel 成功更新并清面板", view.status.state === "cancelled" && view.panelThreadId === null && view.busy === false);
  expect("cancel 成功回到输入框", focused === beforeCancelFocus + 1);

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  view = render();
  const badCancel = view.cancel("t1");
  boss.pending[1].resolve({ state: "无此状态" });
  await badCancel;
  view = render();
  expect(
    "cancel 非法回执提示未确认",
    view.error !== null && view.error.message.includes("取消结果未确认：取消回执无法识别"),
  );

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1", browserId: "b1" });
  view = render();
  const failedCancel = view.cancel("t1");
  boss.pending[1].reject(new Error("boom"));
  await failedCancel;
  view = render();
  expect(
    "cancel 失败保留可读原因",
    view.error !== null && view.error.message.includes("取消结果未确认：boom"),
  );

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "idle", summary: "空闲" });
  view = render();
  expect("空闲状态不可见", view.visibleIn("t1") === false);
  view.show("t1");
  view = render();
  expect("选择中的会话可见", view.visibleIn("t1") === true);

  reset();
  boss = installBoss();
  view = render();
  boss.pending[0].resolve({ state: "无此状态" });
  await flush();
  view = render();
  view.show("t2");
  view = render();
  expect("有错误的会话可见", view.visibleIn("t2") === true && view.visibleIn("t1") === false);

  reset();
  boss = installBoss();
  view = render();
  expect("展开默认关闭", view.expanded === false);
  view.toggleExpanded();
  view = render();
  expect("展开可切换", view.expanded === true);
  view.toggleExpanded();
  view = render();
  expect("展开可关闭", view.expanded === false);

  reset();
  boss = installBoss();
  view = render();
  boss.emit({ state: "waiting", summary: "等待扫码", threadId: "t1" });
  view = render();
  view.show("t1");
  view = render();
  view.hideForLater();
  view = render();
  expect("稍后处理关闭面板", view.panelThreadId === null);
  view.show("t1");
  view = render();
  const beforeClose = focused;
  view.closePanel();
  view = render();
  expect("关闭面板并聚焦", view.panelThreadId === null && focused === beforeClose + 1);

  console.log(`PASS ${passed}`);
}

await run();
"""

ELECTRON_STUB = """\
export class BrowserWindow {}
export class WebContentsView {}
export type Session = unknown;
export const session = { fromPartition: () => { throw new Error("not used"); } };
"""

PROTOCOL_STUB = """\
export type PlatformLoginStatus = any;
export type PlatformLoginContext = any;
export const ClientMethods = {
  platformLoginStart: "platform/login/start",
  platformLoginCancel: "platform/login/cancel",
  platformLoginComplete: "platform/login/complete",
  platformLoginRead: "platform/login/read",
};
"""

SECURITY_STUB = """\
export const isLoginVerificationUrl = () => false;
export const isOfficialLoginUrl = () => true;
export const loginCaptureReadiness = () => ({ ready: false, phase: "scan", summary: "", identity: "unknown" });
export const loginViewBounds = () => null;
"""

LOGIN_FAILURE_STUB = """\
export const loginFailureDetail = (error: any) => ({ message: String(error?.message ?? error) });
export const loginViewGoneSummary = () => "gone";
"""

LOGIN_COOKIES_STUB = """\
export const selectLoginCookies = () => ({ cookies: {}, superseded: 0 });
"""

LOGIN_ATTEMPT_STUB = """\
export function attemptIdOf(value: any) { return value && typeof value.id === "string" ? value.id : undefined; }
export function loginAttemptOf(value: any) {
  if (!value || typeof value.state !== "string") return null;
  return { id: value.id, state: value.state, summary: value.summary ?? "", code: value.code, phase: value.phase, identity: value.identity };
}
"""

MAIN_NODE_SCRIPT = """\
import { PlatformLogin } from "./platformLogin.ts";

const timers: Array<() => void> = [];
(globalThis as { setTimeout?: unknown }).setTimeout = (callback: () => void) => { timers.push(callback); return timers.length; };
(globalThis as { clearTimeout?: unknown }).clearTimeout = () => {};

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

function instance(state: string, code: string | undefined) {
  const pending: Array<{ resolve: (value: unknown) => void; reject: (error: unknown) => void }> = [];
  const request = () => new Promise((resolve, reject) => { pending.push({ resolve, reject }); });
  const login: any = new PlatformLogin(request, () => {});
  login.status = { state, code, summary: "保存结果未知，请检查本机登录态", threadId: "t1", browserId: "b1" };
  login.attempt = "attempt-1";
  login.generation = 10;
  return { login, pending };
}

async function cancelWith(state: string, code: string | undefined, reply: unknown) {
  const { login, pending } = instance(state, code);
  login.cancel();
  const sent = pending.length;
  if (sent > 0) pending[0]!.resolve(reply);
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  return { login, sent };
}

const deadlineCase = instance("saving", undefined);
deadlineCase.login.generation = 1;
deadlineCase.login.startDeadline(1);
const deadline = timers.pop();
if (!deadline) throw new Error("deadline timer missing");
deadline();
expect("保存阶段截止保留失败态", deadlineCase.login.status.state === "failed" && deadlineCase.login.status.code === "LOGIN_TIMEOUT");
expect("保存阶段截止保留保存警告", String(deadlineCase.login.status.summary).includes("保存已停止")
  && String(deadlineCase.login.status.summary).includes("等待已超过五分钟"));

for (const code of ["LOGIN_CONNECTION_LOST", "LOGIN_SAVE_FAILED", "LOGIN_READBACK_INVALID", "LOGIN_TIMEOUT"]) {
  const result = await cancelWith("failed", code, { id: "attempt-1", state: "succeeded", summary: "官方账号验证通过，登录态已保存" });
  expect(`${code} 收到成功回执后转为成功`, result.sent === 1 && result.login.status.state === "succeeded");
}

const openFailed = await cancelWith("failed", "LOGIN_OPEN_FAILED", { id: "attempt-1", state: "succeeded", summary: "不应采用" });
expect("启动失败不因取消回执改变", openFailed.sent === 1 && openFailed.login.status.state === "failed"
  && openFailed.login.status.code === "LOGIN_OPEN_FAILED");

const cancelled = await cancelWith("cancelled", undefined, { id: "attempt-1", state: "failed", code: "LOGIN_SAVE_FAILED", summary: "保存失败" });
expect("已取消收到失败回执后转为失败", cancelled.login.status.state === "failed" && cancelled.login.status.code === "LOGIN_SAVE_FAILED");

const mismatch = await cancelWith("failed", "LOGIN_CONNECTION_LOST", { id: "other", state: "succeeded", summary: "不应采用" });
expect("请求编号不匹配时保持原状态", mismatch.login.status.state === "failed" && mismatch.login.status.code === "LOGIN_CONNECTION_LOST");

console.log(`PASS ${passed}`);
"""

MAIN_IMPORT_REWRITES = (
    ('from "electron"', 'from "./electronStub.ts"'),
    ('from "@boss-harness/protocol"', 'from "./protocolStub.ts"'),
    ('from "./security"', 'from "./securityStub.ts"'),
    ('from "./loginFailure"', 'from "./loginFailureStub.ts"'),
    ('from "./loginCookies"', 'from "./loginCookiesStub.ts"'),
    ('from "./loginAttempt"', 'from "./loginAttemptStub.ts"'),
)
MAIN_CONSTRUCTOR = "  constructor(private request: Request, private publish: (status: PlatformLoginStatus) => void) {}"
MAIN_CONSTRUCTOR_REWRITE = """\
  private request: Request;
  private publish: (status: PlatformLoginStatus) => void;

  constructor(request: Request, publish: (status: PlatformLoginStatus) => void) {
    this.request = request;
    this.publish = publish;
  }"""

MAIN_STUBS = (
    ("electronStub.ts", ELECTRON_STUB),
    ("protocolStub.ts", PROTOCOL_STUB),
    ("securityStub.ts", SECURITY_STUB),
    ("loginFailureStub.ts", LOGIN_FAILURE_STUB),
    ("loginCookiesStub.ts", LOGIN_COOKIES_STUB),
    ("loginAttemptStub.ts", LOGIN_ATTEMPT_STUB),
)

FRAGMENTS = (
    'const [status, setStatus] = useState<PlatformLoginStatus>({ state: "idle", summary: "尚未开始登录" });',
    "const flight = useRef(false), revision = useRef(0);",
    "if (!window.boss) return;",
    "const initial = revision.current;",
    "const unsubscribe = window.boss.onPlatformLogin(raw => {",
    "revision.current += 1;",
    "if (!alive) return;",
    "setStatusError(\"登录状态更新无法识别，已保留上一次有效状态；请重新打开官方页面，或重新连接后再试。\");",
    "if (!alive || initial !== revision.current) return;",
    "return () => { alive = false; unsubscribe(); };",
    "const show = (threadId: string) => {",
    "const open = async (threadId: string) => {",
    "if (!window.boss || flight.current) return;",
    "if (status.threadId === threadId && loginActive(status)) return;",
    "setStatus(previous => fallbackLoginStatus(previous, threadId));",
    "const cancel = async (threadId: string) => {",
    "if (!window.boss || !status.browserId || status.threadId !== threadId || flight.current) return;",
    "visibleIn: (threadId: string) => choiceThreadId === threadId || error?.threadId === threadId || (!dismissed.includes(threadId) && status.threadId === threadId && status.state !== \"idle\"),",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _rewrite(source: str) -> str:
    rewritten = source.replace('from "react"', 'from "./reactStub.ts"')
    rewritten = rewritten.replace('from "./harnessBridge"', 'from "./harnessBridge.ts"')
    rewritten = rewritten.replace('from "./platformLoginState"', 'from "./platformLoginState.ts"')
    for expected in ("./reactStub.ts", "./harnessBridge.ts", "./platformLoginState.ts"):
        if f'from "{expected}"' not in rewritten:
            raise ValueError(f"{SOURCE} 的导入结构已变化，需要更新桩")
    return rewritten


def _rewrite_main(source: str) -> str:
    rewritten = source
    for old, new in MAIN_IMPORT_REWRITES:
        if old not in rewritten:
            raise ValueError(f"{MAIN} 的导入结构已变化，需要更新桩：{old}")
        rewritten = rewritten.replace(old, new)
    if MAIN_CONSTRUCTOR not in rewritten:
        raise ValueError(f"{MAIN} 的构造器结构已变化，需要更新桩")
    return rewritten.replace(MAIN_CONSTRUCTOR, MAIN_CONSTRUCTOR_REWRITE)


def _check_source(source: str) -> int:
    checked = _expect(FRAGMENTS, source, SOURCE)
    if source.index("revision.current += 1;") > source.index("if (!alive) return;"):
        raise ValueError(f"{SOURCE} 必须先自增 revision 再判断存活")
    if source.index("flight.current = true; setBusy(true);") > source.index(
        'window.boss.platformLogin("open"'
    ):
        raise ValueError(f"{SOURCE} 必须先持锁再发起登录")
    return checked + 2


def _check_order(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _check_behaviors() -> int:
    source = _read(SOURCE)
    state = _read(STATE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "usePlatformLogin.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "platformLoginState.ts").write_text(state, encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        (folder / "harnessBridge.ts").write_text(BRIDGE_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("登录面板行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"登录面板行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_main_behaviors() -> int:
    source = _read(MAIN)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "platformLogin.ts").write_text(_rewrite_main(source), encoding="utf-8")
        for name, content in MAIN_STUBS:
            (folder / name).write_text(content, encoding="utf-8")
        harness = folder / "mainHarness.ts"
        harness.write_text(MAIN_NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("主进程登录行为用例失败：" + detail[:400])
    if f"PASS {MAIN_EXPECTED}" not in result.stdout:
        raise ValueError(f"主进程登录行为用例数量不符：{result.stdout.strip()}")
    return MAIN_EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_platform_login.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_platform_login.py")
    if "共 33 项结构、38 项面板行为、9 项主进程行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_platform_login.py 检查 33 项结构、38 项面板行为、9 项主进程行为")
    guide = _read(GUIDE)
    missing = [fragment for fragment in GUIDE_FRAGMENTS if fragment not in guide]
    if missing:
        raise ValueError(f"{GUIDE} 缺少平台登录稳定事实：" + "、".join(missing))
    return 2


def _check_terminal_codes(main: str) -> int:
    start = main.find("const TERMINAL_CANCEL_CODES")
    end = main.find("]);", start)
    if start < 0 or end < 0:
        raise ValueError(f"{MAIN} 缺少取消终态失败码集合")
    block = main[start:end]
    missing = [code for code in TERMINAL_CODES if f'"{code}"' not in block]
    if missing:
        raise ValueError(f"{MAIN} 的取消终态失败码缺少：" + "、".join(missing))
    return 1


def _check_main(main: str) -> int:
    deadline = main.find("private startDeadline")
    cancel = main.find("cancel(): PlatformLoginStatus {")
    end = main.find("private closeBrowser", cancel)
    if deadline < 0 or cancel < 0 or end < 0:
        raise ValueError(f"{MAIN} 缺少截止、取消或收尾方法")
    checked = _check_order(DEADLINE_ORDER, main[deadline:cancel], MAIN)
    checked += _check_order(CANCEL_ORDER, main[cancel:end], MAIN)
    checked += _check_terminal_codes(main)
    return checked


def check_platform_login() -> tuple[int, int, int]:
    source = _read(SOURCE)
    main = _read(MAIN)
    shell = _read(SHELL)
    structure = _check_source(source) + _check_main(main) + _check_order(SHELL_ORDER, shell, SHELL)
    panel_behavior = _check_behaviors()
    main_behavior = _check_main_behaviors()
    _check_documentation()
    return structure, panel_behavior, main_behavior


def main() -> int:
    try:
        structure, panel_behavior, main_behavior = check_platform_login()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"登录面板状态机核对失败，{error}", file=sys.stderr)
        return 2
    print(f"登录面板状态机一致：{structure} 项结构、{panel_behavior} 项面板行为、{main_behavior} 项主进程行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
