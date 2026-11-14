import type { StartupCheckEntry, StartupDiagnosis } from "@boss-harness/protocol";

/**
 * 本地内核未连接时的提示。
 *
 * 断开有两种来源，处理方式不同：从未完成握手的是启动失败，原因在本机配置，要给出本地自检结论；
 * 曾经就绪后断开的可能留有结果未确认的对外操作，要提醒先核对平台状态。两者都要分开
 * 「仍在自动重试」与「已停止重试」，重试用尽后不能继续显示正在恢复。
 */

/** 提示所需的连接状态字段，取自主进程的连接状态或状态通知。 */
export interface ConnectionView {
  state: string;
  running: boolean;
  error?: string;
  startupFailed?: boolean;
  wasReady?: boolean;
  willRetry?: boolean;
  startupDiagnosis?: StartupDiagnosis;
}

export interface ConnectionNoticeParts {
  /** 断开来源，以及是否仍在自动重试。 */
  headline: string;
  /** 本地自检结论的摘要；自检未运行或尚未结束时为空。 */
  diagnosis: string;
  /** 自动恢复停止后的处理方式；仍在重试时为空。 */
  recovery: string;
}

export interface StartupCheckRow {
  key: string;
  title: string;
  status: StartupCheckEntry["status"];
  label: string;
  text: string;
  code: string;
}

const UNCONFIRMED = "结果未确认的对外操作请先核对平台状态。";
const NOT_CONNECTED = "本地内核未连接，可重新连接后恢复会话。";
const CHECK_TITLES = new Map([["model", "模型配置"], ["bossCli", "业务 CLI"], ["browserSource", "浏览器来源"], ["stateDirectory", "状态目录"], ["runtimeOptions", "运行参数"]]);
const STATUS_LABELS: Record<StartupCheckEntry["status"], string> = { ok: "通过", warning: "警告", error: "错误" };
const UNAVAILABLE: Record<Extract<StartupDiagnosis, { kind: "unavailable" }>["reason"], string> = {
  spawn: "未能启动 Python 解释器：请确认仓库根目录已创建 .venv，或 BOSS_HARNESS_PYTHON 指向可执行的 Python 3.10 及以上版本。",
  exit: "内核模块未能运行本地自检：请确认 Python 版本不低于 3.10，并已按安装步骤安装内核依赖。",
  timeout: "本地配置自检超时，未取得结论。",
  invalid: "本地配置自检的输出无法识别：请确认桌面与内核来自同一版本的源码。",
};

function checkEntryOf(value: unknown): StartupCheckEntry | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const { name, status, code, message, hint } = value as Record<string, unknown>;
  if (typeof name !== "string" || typeof code !== "string" || typeof message !== "string" || typeof hint !== "string") return null;
  if (status !== "ok" && status !== "warning" && status !== "error") return null;
  return { name, status, code, message, hint };
}

/** 主进程已按固定字段校验自检输出；这里只确认形状，畸形载荷按「没有结论」处理。 */
function diagnosisOf(value: unknown): StartupDiagnosis | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const raw = value as Record<string, unknown>;
  if (raw.kind === "unavailable") {
    const reason = raw.reason;
    return reason === "spawn" || reason === "exit" || reason === "timeout" || reason === "invalid"
      ? { kind: "unavailable", reason } : undefined;
  }
  if (raw.kind !== "report" || typeof raw.ok !== "boolean" || !Array.isArray(raw.checks)) return undefined;
  const checks: StartupCheckEntry[] = [];
  for (const item of raw.checks) {
    const entry = checkEntryOf(item);
    if (!entry) return undefined;
    checks.push(entry);
  }
  return { kind: "report", ok: raw.ok, checks };
}

/** 从连接状态或状态通知的载荷取出提示字段；没有连接状态的载荷（如状态读取失败）返回 null。 */
export function connectionViewOf(value: unknown): ConnectionView | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.state !== "string") return null;
  const view: ConnectionView = { state: raw.state, running: raw.running === true };
  if (typeof raw.error === "string" && raw.error) view.error = raw.error;
  if (typeof raw.startupFailed === "boolean") view.startupFailed = raw.startupFailed;
  if (typeof raw.wasReady === "boolean") view.wasReady = raw.wasReady;
  if (typeof raw.willRetry === "boolean") view.willRetry = raw.willRetry;
  const diagnosis = diagnosisOf(raw.startupDiagnosis);
  if (diagnosis) view.startupDiagnosis = diagnosis;
  return view;
}

/**
 * 启动中与握手中是自动重试的过渡状态：沿用上一份视图，提示不会随每次重试消失又出现；
 * 期间到达的自检结论仍然并入。返回原对象表示没有需要重新展示的变化。
 */
export function mergeConnectionView(previous: ConnectionView | null, next: ConnectionView | null): ConnectionView | null {
  if (!next) return previous;
  if (!previous || (next.state !== "starting" && next.state !== "initializing")) return next;
  return next.startupDiagnosis && !previous.startupDiagnosis
    ? { ...previous, startupDiagnosis: next.startupDiagnosis } : previous;
}

/** 只取退出码、信号或 errno：原始错误是英文内部文本，可能带本机路径，不直接展示。 */
function failureDetail(error: string | undefined): string {
  if (!error) return "";
  const exited = /^harness exited \(code=(-?\d+|null), signal=([A-Z][A-Z0-9]*|null)\)$/.exec(error);
  if (exited) {
    if (exited[1] !== "null") return `退出码 ${exited[1]}`;
    return exited[2] !== "null" ? `信号 ${exited[2]}` : "";
  }
  const spawn = /^harness failed to start \(([A-Z][A-Z0-9_]*)\b/.exec(error);
  return spawn ? `启动错误 ${spawn[1]}` : "";
}

function sentence(text: string): string {
  const trimmed = text.trim();
  return /[。！？；.!?;]$/.test(trimmed) ? trimmed : `${trimmed}。`;
}

function diagnosisSummary(diagnosis: StartupDiagnosis | undefined): string {
  if (!diagnosis) return "";
  if (diagnosis.kind === "unavailable") return UNAVAILABLE[diagnosis.reason];
  const errors = diagnosis.checks.filter(check => check.status === "error");
  // 自检通过而内核仍起不来：如实说明自检的范围，不把「未发现错误」说成「配置正确」。
  if (!errors.length) return "本地配置自检未发现错误；自检仅覆盖返回的检查项，请继续核对内核依赖、实际写入、磁盘空间、占用锁与其他运行参数。";
  return `自检发现：${errors.map(check => sentence(check.message) + sentence(check.hint)).join("")}`;
}

/**
 * 自动重试停止后的处理方式。解释器与环境变量在应用启动时确定，重新连接只会重新读取
 * 配置文件与已安装的依赖：处理方式要说清哪些改动必须重启应用。
 */
function startupRecovery(diagnosis: StartupDiagnosis | undefined): string {
  if (diagnosis?.kind === "unavailable" && diagnosis.reason === "spawn") return "解释器在应用启动时选定，处理后请重启应用。";
  if (diagnosis?.kind === "unavailable" && diagnosis.reason === "exit") return "安装依赖后可重新连接；更换解释器需重启应用。";
  return "修正配置文件或状态目录条件后可重新连接；环境变量改动需重启应用。";
}

/** 分段的连接提示；已连接、启动中或握手中返回 null。 */
export function connectionNoticeParts(view: ConnectionView | null | undefined): ConnectionNoticeParts | null {
  if (!view || view.running) return null;
  if (view.state === "stopped") return { headline: "本地内核已停止，请重启应用。", diagnosis: "", recovery: "" };
  if (view.state !== "disconnected") return null;
  // 缺少重试字段时无法判断来源：只说明未连接，不猜测是否仍在恢复。
  if (typeof view.willRetry !== "boolean") return { headline: NOT_CONNECTED, diagnosis: "", recovery: "" };
  const retrying = view.willRetry;
  if (view.startupFailed === true) {
    const detail = failureDetail(view.error);
    const cause = detail ? `（${detail}）` : "";
    const progress = retrying ? "正在自动重试" : "已停止自动重试";
    return {
      headline: view.wasReady === true
        ? `本地内核已断开，重新启动未成功${cause}，${progress}；${UNCONFIRMED}`
        : `本地内核未能完成启动${cause}，${progress}。`,
      diagnosis: diagnosisSummary(view.startupDiagnosis),
      recovery: retrying ? "" : startupRecovery(view.startupDiagnosis),
    };
  }
  if (view.wasReady === true) {
    return {
      headline: `本地内核已断开，${retrying ? "正在恢复连接" : "自动恢复已停止"}；${UNCONFIRMED}`,
      diagnosis: "",
      recovery: retrying ? "" : "可重新连接后恢复会话。",
    };
  }
  // 从未就绪且没有失败记录：只出现在显式重连刚发起、新进程尚未给出结果时。
  return { headline: retrying ? "正在重新连接本地内核。" : NOT_CONNECTED, diagnosis: "", recovery: "" };
}

/** 提示条文案：断开来源、自检摘要与处理方式连成一段；无需提示时为空串。 */
export function connectionNotice(view: ConnectionView | null | undefined): string {
  const parts = connectionNoticeParts(view);
  return parts ? `${parts.headline}${parts.diagnosis}${parts.recovery}` : "";
}

/** 设置页的自检明细：全部检查项及固定检查码；没有合规报告时为空。 */
export function startupCheckRows(diagnosis: StartupDiagnosis | undefined): StartupCheckRow[] {
  if (diagnosis?.kind !== "report") return [];
  return diagnosis.checks.map((check, index) => ({
    key: `${index}:${check.name}`,
    title: CHECK_TITLES.get(check.name) ?? check.name,
    status: check.status,
    label: STATUS_LABELS[check.status],
    text: `${sentence(check.message)}${sentence(check.hint)}`,
    code: check.code,
  }));
}
