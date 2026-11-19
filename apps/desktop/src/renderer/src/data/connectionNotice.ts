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
  /** 握手回执的模型线路；显式 none 启动时带进程级禁用标志。缺失表示尚未握手。 */
  modelBridge?: { provider: string; model: string; driven: boolean; modelCallsDisabled?: boolean };
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
const STATUS_ORDER: Record<StartupCheckEntry["status"], number> = { error: 0, warning: 1, ok: 2 };
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
export function startupDiagnosisOf(value: unknown): StartupDiagnosis | undefined {
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
  const version = typeof raw.version === "string" && raw.version ? raw.version : undefined;
  const protocolVersion = typeof raw.protocolVersion === "string" && raw.protocolVersion ? raw.protocolVersion : undefined;
  const pythonVersion = typeof raw.pythonVersion === "string" && raw.pythonVersion ? raw.pythonVersion : undefined;
  return {
    kind: "report", ok: raw.ok, checks,
    ...(version ? { version } : {}),
    ...(protocolVersion ? { protocolVersion } : {}),
    ...(pythonVersion ? { pythonVersion } : {}),
  };
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
  const diagnosis = startupDiagnosisOf(raw.startupDiagnosis);
  if (diagnosis) view.startupDiagnosis = diagnosis;
  const bridge = raw.modelBridge;
  if (bridge && typeof bridge === "object" && !Array.isArray(bridge)) {
    const record = bridge as Record<string, unknown>;
    // 与 harnessBridge 的握手解析同一上限：畸形字段按缺失处理，不用默认值冒充事实。
    if (typeof record.provider === "string" && record.provider.length <= 200
      && typeof record.model === "string" && record.model.length <= 200
      && typeof record.driven === "boolean") {
      view.modelBridge = { provider: record.provider, model: record.model, driven: record.driven,
        ...(record.modelCallsDisabled === true ? { modelCallsDisabled: true } : {}) };
    }
  }
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
  if (!errors.length) {
    // 警告不阻止启动，但仍可能是排查线索；只列已解析的报告字段，不新增诊断。
    const warnings = diagnosis.checks.filter(check => check.status === "warning");
    const notes = warnings.map(check =>
      `${CHECK_TITLES.get(check.name) ?? check.name}：${sentence(check.message)}（${check.code}）`).join("");
    const extra = notes ? `另有警告（可能不影响启动）：${notes}` : "";
    return `本地配置自检未发现错误；${extra}自检仅覆盖返回的检查项，请继续核对内核依赖、实际写入、磁盘空间、占用锁与其他运行参数。`;
  }
  return `自检发现：${errors.map(check =>
    `${CHECK_TITLES.get(check.name) ?? check.name}：${sentence(check.message)}${sentence(check.hint)}（${check.code}）`).join("")}`;
}

/**
 * 自动重试停止后的处理方式。解释器与环境变量在应用启动时确定，重新连接只会重新读取
 * 配置文件与已安装的依赖：处理方式要说清哪些改动必须重启应用。
 */
function startupRecovery(diagnosis: StartupDiagnosis | undefined): string {
  if (diagnosis?.kind === "unavailable" && diagnosis.reason === "spawn") return "解释器在应用启动时选定，处理后请重启应用。";
  if (diagnosis?.kind === "unavailable" && diagnosis.reason === "exit") return "安装依赖后可重新连接；更换解释器需重启应用。";
  // 自检没有错误项时，最可能的原因是解释器缺少内核依赖或失败发生在自检覆盖范围之外。
  if (diagnosis?.kind !== "report") return "修正配置文件或状态目录条件后可重新连接；环境变量改动需重启应用。";
  const errors = diagnosis.checks.filter(check => check.status === "error");
  if (!errors.length)
    return "核对内核依赖是否已安装，修正配置后可重新连接；环境变量改动需重启应用。";
  // 只有全部错误都指向缺少模型 SDK 时才把安装依赖作为唯一处理方式；混合错误要保留通用建议，
  // 逐条安装与修正提示仍由自检摘要列出。
  if (errors.every(check => check.code === "MODEL_SDK_UNAVAILABLE"))
    return "安装内核依赖后可重新连接；环境变量改动需重启应用。";
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

/** 设置页先列错误再列警告与通过项，同类项顺序不变；只排序展示行，不改原始报告。 */
export function startupCheckRows(diagnosis: StartupDiagnosis | undefined): StartupCheckRow[] {
  if (diagnosis?.kind !== "report") return [];
  return diagnosis.checks.map((check, index) => ({
    key: `${index}:${check.name}`,
    title: CHECK_TITLES.get(check.name) ?? check.name,
    status: check.status,
    label: STATUS_LABELS[check.status],
    text: `${sentence(check.message)}${sentence(check.hint)}`,
    code: check.code,
  })).sort((left, right) => STATUS_ORDER[left.status] - STATUS_ORDER[right.status]);
}

/** 报告版本行：只拼接报告实际携带的字段；没有合规报告时为空串。 */
export function startupReportMeta(diagnosis: StartupDiagnosis | undefined): string {
  if (diagnosis?.kind !== "report") return "";
  return [diagnosis.version ? `内核 ${diagnosis.version}` : "",
    diagnosis.protocolVersion ? `协议 ${diagnosis.protocolVersion}` : "",
    diagnosis.pythonVersion ? `Python ${diagnosis.pythonVersion}` : ""].filter(Boolean).join(" · ");
}

/** 桌面与内核协议不一致的提示；一致、缺少字段或没有报告时为空串。 */
export function startupProtocolMismatch(diagnosis: StartupDiagnosis | undefined, supported: string): string {
  const reported = diagnosis?.kind === "report" ? diagnosis.protocolVersion : undefined;
  return reported && reported !== supported
    ? `协议版本不一致：内核自检报告 ${reported}，桌面支持 ${supported}；请确认桌面与内核来自同一构建。`
    : "";
}

/** 自检未能给出报告时的固定说明；有合规报告时为空串。 */
export function startupUnavailableText(diagnosis: StartupDiagnosis | undefined): string {
  return diagnosis?.kind === "unavailable" ? UNAVAILABLE[diagnosis.reason] : "";
}

/**
 * 总体结论：与内核 `--format text` 的结论行同口径，供手动自检结果区与复制文本使用。
 * 没有合规报告时返回空串，不推测结论。
 */
export function startupConclusion(diagnosis: StartupDiagnosis | undefined): string {
  if (diagnosis?.kind !== "report") return "";
  const errors = diagnosis.checks.filter(check => check.status === "error").length;
  const warnings = diagnosis.checks.filter(check => check.status === "warning").length;
  if (errors) return `发现 ${errors} 个错误${warnings ? `、${warnings} 项警告` : ""}`;
  return warnings ? `通过，${warnings} 项警告` : "通过";
}

/**
 * 复制用纯文本：只汇总界面已展示的自检字段。
 * 不读取内核 stderr、异常原文、端点、凭据、本机路径或会话内容。
 */
export function startupDiagnostics(
  notice: ConnectionNoticeParts,
  diagnosis: StartupDiagnosis | undefined,
  meta: string,
  mismatch: string,
): string {
  const lines = ["BOSS Harness 启动自检", notice.headline];
  if (meta) lines.push(`自检报告：${meta}`);
  if (mismatch) lines.push(mismatch);
  if (notice.diagnosis) lines.push(notice.diagnosis);
  for (const row of startupCheckRows(diagnosis)) {
    lines.push(`- ${row.label} ${row.title}：${row.text}（${row.code}）`);
  }
  if (notice.recovery) lines.push(`处理建议：${notice.recovery}`);
  return lines.join("\n");
}
