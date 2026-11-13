import { spawn, type ChildProcess } from "node:child_process";
import type { StartupCheckEntry, StartupDiagnosis } from "@boss-harness/protocol";

/**
 * 内核启动失败后的本地自检：运行 `boss-harness --check`，只接受固定字段。
 *
 * 传输层不读取内核 stderr（可能带凭据、端点与本机路径），启动失败的原因改由这份自检给出。
 * 自检只解析本地配置：不调用模型、不执行业务 CLI、不访问招聘平台。
 */

/** 正常报告不足 2 KiB；超过上限即视为不合规，避免无界缓冲。 */
const MAX_REPORT_BYTES = 64 * 1024;
const MAX_CHECKS = 16;
const MAX_TEXT_LENGTH = 300;
const CHECK_TIMEOUT_MS = 10_000;
const NAME_PATTERN = /^[A-Za-z][A-Za-z0-9]{0,31}$/;
const CODE_PATTERN = /^[A-Z][A-Z0-9_]{1,63}$/;
/** 说明与建议只接受单行可见文本：控制字符与行分隔符一律视为不合规。 */
const CONTROL_PATTERN = /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/;

export interface StartupCheckTarget {
  command: string;
  args: string[];
  cwd?: string;
  env: NodeJS.ProcessEnv;
}

function plainText(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_TEXT_LENGTH
    && !CONTROL_PATTERN.test(value);
}

function checkEntry(value: unknown): StartupCheckEntry | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const { name, status, code, message, hint } = value as Record<string, unknown>;
  if (typeof name !== "string" || !NAME_PATTERN.test(name)) return null;
  if (status !== "ok" && status !== "warning" && status !== "error") return null;
  if (typeof code !== "string" || !CODE_PATTERN.test(code)) return null;
  if (!plainText(message) || !plainText(hint)) return null;
  return { name, status, code, message, hint };
}

/** 解析自检输出；任一字段不合规都整体作废，不展示部分可信的报告。 */
export function parseStartupReport(output: string): StartupDiagnosis | null {
  let parsed: unknown;
  try { parsed = JSON.parse(output); } catch { return null; }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const report = parsed as Record<string, unknown>;
  if (report.schemaVersion !== 1 || typeof report.ok !== "boolean" || !Array.isArray(report.checks)) return null;
  if (report.checks.length === 0 || report.checks.length > MAX_CHECKS) return null;
  const checks: StartupCheckEntry[] = [];
  for (const item of report.checks) {
    const entry = checkEntry(item);
    if (!entry || checks.some((known) => known.name === entry.name)) return null;
    checks.push(entry);
  }
  // `ok` 与检查项矛盾的报告不可信：不替内核猜哪一边正确。
  if (report.ok !== checks.every((entry) => entry.status !== "error")) return null;
  return { kind: "report", ok: report.ok, checks };
}

/**
 * 运行一次自检并返回结论；任何失败都归入固定原因，不抛出。
 * stdin 关闭、stderr 丢弃：异常文本不会进入主进程内存或日志。
 */
export function runStartupCheck(target: StartupCheckTarget, signal?: AbortSignal): Promise<StartupDiagnosis> {
  return new Promise((resolve) => {
    const chunks: Buffer[] = [];
    let size = 0;
    let child: ChildProcess | null = null;
    let done = false;
    const finish = (result: StartupDiagnosis): void => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", cancel);
      // 超时、取消或输出超限时进程可能仍在运行；自检只读，直接结束不留副作用。
      if (child && child.exitCode === null && child.signalCode === null) {
        try { child.kill("SIGKILL"); } catch { /* 进程已经退出。 */ }
      }
      resolve(result);
    };
    const cancel = (): void => finish({ kind: "unavailable", reason: "timeout" });
    const timer = setTimeout(cancel, CHECK_TIMEOUT_MS);
    if (signal?.aborted) { cancel(); return; }
    signal?.addEventListener("abort", cancel, { once: true });
    try {
      child = spawn(target.command, target.args, {
        cwd: target.cwd, env: target.env, stdio: ["ignore", "pipe", "ignore"], windowsHide: true,
      });
    } catch {
      finish({ kind: "unavailable", reason: "spawn" });
      return;
    }
    // 监听保持到进程结束：结论已定之后的进程错误也不能成为主进程的未处理异常。
    child.on("error", () => finish({ kind: "unavailable", reason: "spawn" }));
    child.stdout?.on("error", () => finish({ kind: "unavailable", reason: "invalid" }));
    child.stdout?.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > MAX_REPORT_BYTES) { finish({ kind: "unavailable", reason: "invalid" }); return; }
      chunks.push(chunk);
    });
    child.once("close", (code) => {
      let report: StartupDiagnosis | null = null;
      try {
        report = parseStartupReport(new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)));
      } catch { /* 非 UTF-8 输出按不合规处理。 */ }
      // 有错误项的合规报告以退出码 2 结束，仍然采用；没有合规报告时才按退出码区分原因。
      finish(report ?? { kind: "unavailable", reason: code === 0 ? "invalid" : "exit" });
    });
  });
}

interface Flight { controller: AbortController; done: Promise<void> }

/**
 * 一个失败周期内的自检结论：握手前失败时运行一次，连接恢复或显式重连后作废。
 * 结论只保存在主进程内存里，不写入磁盘。
 */
export class StartupDiagnostics {
  #run: (signal: AbortSignal) => Promise<StartupDiagnosis>;
  #changed: () => void;
  #result: StartupDiagnosis | null = null;
  #flight: Flight | null = null;

  constructor(run: (signal: AbortSignal) => Promise<StartupDiagnosis>, changed: () => void) {
    this.#run = run;
    this.#changed = changed;
  }

  get result(): StartupDiagnosis | null { return this.#result; }

  /** 自动重试期间的重复失败共用同一份结论：已有结论或自检在途时不再启动进程。 */
  request(): void {
    if (this.#result || this.#flight) return;
    const controller = new AbortController();
    const flight: Flight = { controller, done: Promise.resolve() };
    this.#flight = flight;
    flight.done = (async () => {
      let result: StartupDiagnosis;
      try { result = await this.#run(controller.signal); }
      catch { result = { kind: "unavailable", reason: "spawn" }; }
      // 期间发生过重连或恢复时，这份结论对应的已经是上一个失败周期。
      if (this.#flight !== flight) return;
      this.#flight = null;
      this.#result = result;
      try { this.#changed(); } catch { /* 通知窗口失败不影响结论保存。 */ }
    })();
  }

  /** 丢弃结论并结束在途自检。 */
  reset(): void {
    const flight = this.#flight;
    this.#result = null;
    this.#flight = null;
    flight?.controller.abort();
  }

  /** 在途自检结束后兑现；没有在途自检时立即兑现。 */
  settled(): Promise<void> { return this.#flight?.done ?? Promise.resolve(); }
}
