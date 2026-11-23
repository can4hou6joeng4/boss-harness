#!/usr/bin/env python3
"""核对任务核对回执的校验、标签与只读展示。

`taskCheck.ts` 把 `task/read` 的内核回执转成 cockpit 的只读核对文案：响应必须
字段完整且落在白名单内，任何异常都整体拒绝；队列取消与回合取消分开表述；
关联清单最多展开八条，超限与截断分别提示；只有带 `TASK_NOT_FOUND` 的 RPC
拒绝才给出「不在持久记录」的结论。这里用 Node 在临时目录加载真实模块并改写
错误文案导入，逐项核对这些行为。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/taskCheck.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'const TASK_KINDS: ReadonlySet<string> = new Set(["turn", "queue", "compaction"]);',
    'const OWNERSHIPS: ReadonlySet<string> = new Set(["root", "resolved", "unassigned", "unresolved", "conflict", "independent"]);',
    'const RELATION_OWNERSHIPS: ReadonlySet<string> = new Set(["resolved", "unresolved", "conflict"]);',
    'const RECOVERY_POLICIES: ReadonlySet<string> = new Set(["process_owned", "manual_review", "queue_pending", "closed"]);',
    '"input_queue", "steering_input", "queue_candidate", "delivered_as", "targets",',
    '"turn_candidate", "summary_child", "summary_candidate", "owner_turn",',
    'const PHASES: ReadonlySet<string> = new Set(["admission", "prepare", "model_request", "tool_execution", "finish"]);',
    'const PHASE_STATUSES: ReadonlySet<string> = new Set(["running", "completed", "interrupted", "blocked", "error"]);',
    "const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;",
    "const THREAD_PATTERN = /^[A-Za-z0-9_-]{1,200}$/;",
    "const MAX_RELATIONS = 256;",
    "const MAX_STATUS = 100;",
    "const MAX_REASON = 200;",
    'root: "根任务",',
    'resolved: "已解析",',
    'unassigned: "未分配",',
    'unresolved: "未解析",',
    'conflict: "冲突",',
    'independent: "独立",',
    'running: "运行中",',
    'completed: "已完成",',
    'interrupted: "已中断",',
    'blocked: "已阻断",',
    'error: "已失败",',
    'queued: "排队中",',
    'delivering: "正在投递",',
    'delivered: "已投递",',
    'paused: "已暂停",',
    'cancelled: "已取消",',
    'failed: "已失败",',
    'conflict: "记录冲突",',
    'unknown: "未知",',
    'model_request: "模型请求",',
    'tool_execution: "工具执行",',
    'compaction: "摘要",',
    'process_owned: "当前进程持有；退出后不自动重放",',
    'manual_review: "人工复核；不自动恢复",',
    'queue_pending: "队列待投递",',
    'closed: "已关闭；无需恢复",',
    'input_queue: "来源队列",',
    'steering_input: "转向输入",',
    'queue_candidate: "候选队列",',
    'delivered_as: "已投递为",',
    'targets: "指向",',
    'turn_candidate: "候选回合",',
    'summary_child: "摘要子任务",',
    'summary_candidate: "候选摘要",',
    'owner_turn: "归属回合",',
    "Object.prototype.hasOwnProperty.call(labels, value) ? labels[value] : undefined",
    'return known ?? `「${value}」`;',
    'if (status === "cancelled" && kind === "queue") return "已撤回";',
    'const restarts = restartLimit === 0 ? "不自动重启" : `自动重启上限 ${restartLimit} 次`;',
    'return `第 ${attempt} 次尝试 · ${restarts}`;',
    'return Boolean(value) && typeof value === "object" && !Array.isArray(value);',
    "return text.length > 0 && text.length <= maximum ? text : null;",
    'typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;',
    'const kind: TaskKind | null = owner.kind === "turn" ? "turn"',
    ': owner.kind === "manualCompaction" || owner.kind === "automaticCompaction" ? "compaction" : null;',
    "if (!kind || !THREAD_PATTERN.test(owner.threadId) || !ID_PATTERN.test(owner.id)) return null;",
    "return { threadId: owner.threadId, kind, id: owner.id };",
    "if (!record(value) || typeof value.kind !== \"string\" || !TASK_KINDS.has(value.kind)",
    "|| typeof value.id !== \"string\" || !ID_PATTERN.test(value.id)) return null;",
    "if (!record(value) || typeof value.relation !== \"string\" || !RELATIONS.has(value.relation)",
    '|| typeof value.ownership !== "string" || !RELATION_OWNERSHIPS.has(value.ownership)) return null;',
    'const invalid = (): Error => new Error("任务核对响应无法识别");',
    "if (!record(value) || !record(value.task)) throw invalid();",
    "if (!locator || locator.kind !== params.kind || locator.id !== params.id) throw invalid();",
    "if (raw.threadId !== params.threadId) throw invalid();",
    "const status = boundedText(raw.status, MAX_STATUS);",
    'if (status === null || typeof raw.ownership !== "string" || !OWNERSHIPS.has(raw.ownership)',
    '|| typeof raw.runtimeOwned !== "boolean"',
    '|| typeof raw.recoveryPolicy !== "string" || !RECOVERY_POLICIES.has(raw.recoveryPolicy)) throw invalid();',
    "if (!record(raw.phase) || typeof raw.phase.name !== \"string\" || !PHASES.has(raw.phase.name)",
    '|| typeof raw.phase.status !== "string" || !PHASE_STATUSES.has(raw.phase.status)) throw invalid();',
    "if (attempt === null || restartLimit === null) throw invalid();",
    "if (reason === null) throw invalid();",
    "if (!Array.isArray(raw.relations) || raw.relations.length > MAX_RELATIONS) throw invalid();",
    "if (!relation) throw invalid();",
    "if (typeof raw.relationsTruncated !== \"boolean\") throw invalid();",
    'if (!record(raw.historyWindow) || raw.historyWindow.checkpointRelations !== "durable") throw invalid();',
    "if (terminalCompactions === null) throw invalid();",
    "if (task.relations.length === 0) lines.push(\"已验证关联：无\");",
    "const shown = task.relations.slice(0, 8);",
    "lines.push(`其余 ${task.relations.length - shown.length} 项关联未展开；核对不改变任务状态。`);",
    'if (task.relationsTruncated) lines.push("关联已由内核按上限截断，清单不完整。");',
    "if (task.historyWindow) lines.push(`历史窗口：最近 ${task.historyWindow.terminalCompactions} 个摘要终态；检查点关联持久化。`);",
    'if (code === "TASK_NOT_FOUND") {',
    'return "该任务不在持久记录中（可能已清理，或不属于此会话；TASK_NOT_FOUND）；核对不会恢复或重放任务。";',
)

STUB = r"""
export function harnessErrorText(error) {
  if (error && typeof error === "object" && error.rpcError === true) {
    const data = error.data && typeof error.data === "object" ? error.data : null;
    const code = data && typeof data.code === "string" ? data.code : "";
    return code ? `RPC ${code}` : "RPC 错误";
  }
  return "本地错误";
}
"""

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  labeledValue, taskStatusLabel, taskPhaseLabel, taskPhaseStatusLabel, taskAttemptText,
  taskLocatorForOwner, parseTaskRead, taskCheckLines, taskCheckErrorText,
} = await import(pathToFileURL(process.argv[1]).href);
const params = { threadId: "th-1", kind: "turn", id: "t-1" };
const base = () => ({
  locator: { kind: "turn", id: "t-1" },
  threadId: "th-1",
  status: "running",
  ownership: "root",
  runtimeOwned: true,
  recoveryPolicy: "process_owned",
  relations: [],
});
const owner = (over = {}) => ({
  kind: "turn", id: "t-1", threadId: "th-1", state: "active", ageSeconds: 1,
  cancelRequested: false, abortPending: false, phase: null, phaseStatus: null, ...over,
});
const view = task => JSON.stringify({
  locator: task.locator, threadId: task.threadId, status: task.status,
  ownership: task.ownership, runtimeOwned: task.runtimeOwned,
  recoveryPolicy: task.recoveryPolicy, phase: task.phase ?? null,
  relations: task.relations, relationsTruncated: task.relationsTruncated ?? null,
  historyWindow: task.historyWindow ?? null,
});
const captured = fn => {
  try { return "ok:" + fn(); } catch (error) { return "err:" + (error?.message ?? String(error)); }
};
const parse = (task, over = {}) => captured(() => view(parseTaskRead({ task }, { ...params, ...over })));
const parseValue = (value, over = {}) => captured(() => view(parseTaskRead(value, { ...params, ...over })));
const labels = { known: "已知", "": "空标签" };
const invalidMessage = "err:任务核对响应无法识别";
const phase = (over = {}) => ({
  name: "model_request", status: "running", attempt: 1, restartLimit: 0, ...over,
});
const relation = (over = {}) => ({ relation: "input_queue", ownership: "resolved", ...over });
const result = {
  labels: [
    labeledValue(labels, "known"),
    labeledValue(labels, "missing"),
    labeledValue(labels, "constructor"),
    labeledValue(labels, "__proto__"),
    labeledValue(labels, "toString"),
    taskStatusLabel("cancelled"),
    taskStatusLabel("cancelled", "queue"),
    taskStatusLabel("cancelled", "compaction"),
    taskStatusLabel("future", "queue"),
    taskPhaseLabel("compaction"),
    taskPhaseLabel("future"),
    taskPhaseStatusLabel("cancelled"),
    taskPhaseStatusLabel("running"),
    taskAttemptText(0, 0),
    taskAttemptText(2, 3),
  ],
  locators: [
    taskLocatorForOwner(owner()),
    taskLocatorForOwner(owner({ kind: "manualCompaction", id: "c-1" })),
    taskLocatorForOwner(owner({ kind: "automaticCompaction", id: "c-1", state: "cleanup" })),
    taskLocatorForOwner(owner({ kind: "queue", id: "q-1" })),
    taskLocatorForOwner(owner({ threadId: "th/1" })),
    taskLocatorForOwner(owner({ threadId: "" })),
    taskLocatorForOwner(owner({ id: "-bad" })),
    taskLocatorForOwner(owner({ id: "bad.id" })),
    taskLocatorForOwner(owner({ id: "a".repeat(129) })),
    taskLocatorForOwner(owner({ threadId: "t".repeat(201) })),
    taskLocatorForOwner(owner({ id: "a".repeat(128), threadId: "t".repeat(200) })),
  ],
  parse: [
    parseValue(null),
    parseValue({}),
    parseValue({ task: [] }),
    parse(base()),
    parse({ ...base(), locator: { kind: "queue", id: "t-1" } }),
    parse({ ...base(), locator: { kind: "turn", id: "other" } }),
    parse({ ...base(), locator: { kind: "turn", id: "-bad" } }),
    parse({ ...base(), threadId: "th-2" }),
    parse({ ...base(), status: "  running  " }),
    parse({ ...base(), status: "   " }),
    parse({ ...base(), status: 1 }),
    parse({ ...base(), status: "s".repeat(101) }),
    parse({ ...base(), ownership: "owner" }),
    parse({ ...base(), runtimeOwned: "yes" }),
    parse({ ...base(), recoveryPolicy: "restart" }),
    parse({ ...base(), phase: null }),
    parse({ ...base(), phase: {} }),
    parse({ ...base(), phase: phase() }),
    parse({ ...base(), phase: phase({ name: "queue", status: "running" }) }),
    parse({ ...base(), phase: phase({ status: "queued" }) }),
    parse({ ...base(), phase: phase({ attempt: -1 }) }),
    parse({ ...base(), phase: phase({ restartLimit: 1.5 }) }),
    parse({ ...base(), phase: phase({ recoveryReason: "  原因  " }) }),
    parse({ ...base(), phase: phase({ recoveryReason: "r".repeat(201) }) }),
    parse({ ...base(), relations: null }),
    parse({ ...base(), relations: Array(257).fill(relation()) }),
    parse({ ...base(), relations:Array.from({ length: 256 }, () => relation()) }),
    parse({ ...base(), relations: [relation({ relation: "other" })] }),
    parse({ ...base(), relations: [relation({ ownership: "root" })] }),
    parse({ ...base(), relations: [relation({ task: { kind: "turn", id: "t-2" } })] }),
    parse({ ...base(), relations: [relation({ task: { kind: "queue", id: "-bad" } })] }),
    parse({ ...base(), relationsTruncated: "yes" }),
    parse({ ...base(), relationsTruncated: false }),
    parse({ ...base(), historyWindow: { checkpointRelations: "volatile", terminalCompactions: 1 } }),
    parse({ ...base(), historyWindow: { checkpointRelations: "durable", terminalCompactions: -1 } }),
    parse({ ...base(), historyWindow: { checkpointRelations: "durable", terminalCompactions: 2 } }),
    parse({ ...base(), extra: "ignored" }),
    captured(() => view(parseTaskRead({ task: base() }, { ...params, kind: "compaction" }))),
  ],
  lines: [
    taskCheckLines(base()),
    taskCheckLines({ ...base(), status: "cancelled", locator: { kind: "queue", id: "q-1" } }),
    taskCheckLines({ ...base(), status: "future", ownership: "conflict", recoveryPolicy: "manual_review", runtimeOwned: false }),
    taskCheckLines({ ...base(), phase: phase({ recoveryReason: "上下文溢出" }) }),
    taskCheckLines({ ...base(), relations: [relation()] }),
    taskCheckLines({ ...base(), relations: [relation({ relation: "owner_turn", ownership: "conflict", task: { kind: "turn", id: "t-2" } })] }),
    taskCheckLines({ ...base(), relations: Array.from({ length: 9 }, (_, index) => relation({ task: { kind: "turn", id: `t-${index + 2}` } })) }),
    taskCheckLines({ ...base(), relations: [relation()], relationsTruncated: true }),
    taskCheckLines({ ...base(), historyWindow: { checkpointRelations: "durable", terminalCompactions: 3 } }),
  ],
  errors: [
    taskCheckErrorText({ rpcError: true, data: { code: "TASK_NOT_FOUND" } }),
    taskCheckErrorText({ rpcError: false, data: { code: "TASK_NOT_FOUND" } }),
    taskCheckErrorText({ rpcError: true }),
    taskCheckErrorText({ rpcError: true, data: { code: "OTHER" } }),
    taskCheckErrorText({ rpcError: true, data: { code: 42 } }),
    taskCheckErrorText(null),
    taskCheckErrorText(new Error("boom")),
    taskCheckErrorText("boom"),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_LABELS = (
    "已知", "「missing」", "「constructor」", "「__proto__」", "「toString」",
    "已取消", "已撤回", "已取消", "「future」", "摘要", "「future」", "已取消", "运行中",
    "第 0 次尝试 · 不自动重启", "第 2 次尝试 · 自动重启上限 3 次",
)
EXPECTED_LOCATORS = (
    {"threadId": "th-1", "kind": "turn", "id": "t-1"},
    {"threadId": "th-1", "kind": "compaction", "id": "c-1"},
    {"threadId": "th-1", "kind": "compaction", "id": "c-1"},
    None, None, None, None, None, None, None,
    {"threadId": "t" * 200, "kind": "turn", "id": "a" * 128},
)
MINIMAL = (
    '{"locator":{"kind":"turn","id":"t-1"},"threadId":"th-1","status":"running",'
    '"ownership":"root","runtimeOwned":true,"recoveryPolicy":"process_owned",'
    '"phase":null,"relations":[],"relationsTruncated":null,"historyWindow":null}'
)
PHASE_VIEW = (
    '"phase":{"name":"model_request","status":"running","attempt":1,'
    '"restartLimit":0}'
)
RELATION_VIEW = (
    '{"relation":"input_queue","ownership":"resolved"}'
)
INVALID = "err:任务核对响应无法识别"
EXPECTED_PARSE = (
    INVALID,
    INVALID,
    INVALID,
    "ok:" + MINIMAL,
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"status":"running"', '"status":"running"'),
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"phase":null', PHASE_VIEW),
    INVALID,
    INVALID,
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"phase":null', PHASE_VIEW[:-1] + ',"recoveryReason":"原因"}'),
    INVALID,
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"relations":[]', '"relations":[' + ",".join([RELATION_VIEW] * 256) + "]"),
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"relations":[]', '"relations":[{"relation":"input_queue","ownership":"resolved","task":{"kind":"turn","id":"t-2"}}]'),
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"relationsTruncated":null', '"relationsTruncated":false'),
    INVALID,
    INVALID,
    "ok:" + MINIMAL.replace('"historyWindow":null', '"historyWindow":{"terminalCompactions":2,"checkpointRelations":"durable"}'),
    "ok:" + MINIMAL,
    INVALID,
)
NOT_FOUND = "该任务不在持久记录中（可能已清理，或不属于此会话；TASK_NOT_FOUND）；核对不会恢复或重放任务。"
EXPECTED_LINES = (
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "已验证关联：无",
    ],
    [
        "持久状态：已撤回 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "已验证关联：无",
    ],
    [
        "持久状态：「future」 · 归属：冲突",
        "执行 owner：当前进程未持有 · 恢复策略：人工复核；不自动恢复",
        "已验证关联：无",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "任务阶段：模型请求 · 运行中 · 第 1 次尝试 · 不自动重启 · 恢复原因 上下文溢出",
        "已验证关联：无",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "关联：来源队列 · 已解析",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "关联：归属回合 · 冲突 · turn/t-2",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "关联：来源队列 · 已解析 · turn/t-2",
        "关联：来源队列 · 已解析 · turn/t-3",
        "关联：来源队列 · 已解析 · turn/t-4",
        "关联：来源队列 · 已解析 · turn/t-5",
        "关联：来源队列 · 已解析 · turn/t-6",
        "关联：来源队列 · 已解析 · turn/t-7",
        "关联：来源队列 · 已解析 · turn/t-8",
        "关联：来源队列 · 已解析 · turn/t-9",
        "其余 1 项关联未展开；核对不改变任务状态。",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "关联：来源队列 · 已解析",
        "关联已由内核按上限截断，清单不完整。",
    ],
    [
        "持久状态：运行中 · 归属：根任务",
        "执行 owner：当前进程持有 · 恢复策略：当前进程持有；退出后不自动重放",
        "已验证关联：无",
        "历史窗口：最近 3 个摘要终态；检查点关联持久化。",
    ],
)
EXPECTED_ERRORS = (
    NOT_FOUND, "本地错误", "RPC 错误", "RPC OTHER", "RPC 错误",
    "本地错误", "本地错误", "本地错误",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "taskCheck.ts"
        stub = Path(directory) / "harnessBridge.mjs"
        source = _read(TARGET).replace(
            'from "./harnessBridge"',
            f'from "{stub.as_uri()}"',
        )
        target.write_text(source, encoding="utf-8")
        stub.write_text(STUB, encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 任务核对试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 任务核对试算失败，请核对 Node.js 24+ 与 taskCheck.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的任务核对结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回任务核对矩阵")
    for key in ("labels", "locators", "parse", "lines", "errors"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"任务核对{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"任务核对{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["labels"], EXPECTED_LABELS, "文案")
    checked += _compare(payload["locators"], EXPECTED_LOCATORS, "owner 映射")
    checked += _compare(payload["parse"], EXPECTED_PARSE, "响应校验")
    checked += _compare(payload["lines"], EXPECTED_LINES, "展示行")
    checked += _compare(payload["errors"], EXPECTED_ERRORS, "失败文案")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_task_check.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_task_check.py")
    if "共 88 项结构、81 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_task_check.py 检查 88 项结构、81 项行为")
    return 2


def check_task_check() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_task_check()
    except (OSError, ValueError) as error:
        print(f"任务核对规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"任务核对规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
