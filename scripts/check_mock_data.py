#!/usr/bin/env python3
"""核对桌面仿真数据卡片的字段契约。

`mockData.ts` 为首页策略域、模型选择、项目会话、工具卡、审批卡与目标状态提供演示
数据。这里静态核对模块契约，并由 Node 直接加载真实模块，覆盖列表完整性、会话
归属、差异明细合计、卡片引用关系与仿真审批不得携带内核 id 等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/mockData.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { QueueStatusCounts, ThreadItem, ToolResultReference, TurnStatus, TurnTaskResumePolicy } from "@boss-harness/protocol";',
    'export type ConversationMode = "plan" | "ask" | "agent";',
    'export type EffortLevel = "Auto" | "Max" | "High" | "Medium" | "Low" | "Off";',
    "export const STRATEGY_DOMAINS: StrategyDomain[] = [",
    "export const MODEL_OPTIONS: ModelOption[] = [",
    "export const MOCK_PROJECT_FOLDERS: ProjectFolder[] = [",
    'toolPolicy?: "readOnly" | "approval";',
    'status: "idle" | "running" | "completed" | "interrupted";',
    'decision?: "approve" | "deny" | "expired";',
    "consequential?: boolean;",
    "approvalId?: string;",
    "export const MOCK_DIFF_DATA = {",
    "export const MOCK_CONVERSATION_THREAD: MessageItem[] = [",
    "export const MOCK_GOAL_STATE: GoalState = {",
    "paused: boolean;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const m = await import(pathToFileURL(process.argv[1]).href);
const ids = (xs) => xs.map((x) => x.id);
const nonempty = (x) => typeof x === "string" && x.trim().length > 0;
const domainFieldsOk = m.STRATEGY_DOMAINS.every((d) =>
  nonempty(d.id) && nonempty(d.name) && nonempty(d.badge) && nonempty(d.desc) &&
  nonempty(d.defaultPrompt) && typeof d.icon === "string");
const modelFieldsOk = m.MODEL_OPTIONS.every((o) =>
  nonempty(o.id) && nonempty(o.name) && nonempty(o.provider));
const statuses = new Set(["idle", "running", "completed", "interrupted"]);
const foldersOk = m.MOCK_PROJECT_FOLDERS.every((f) =>
  nonempty(f.id) && nonempty(f.name) && Array.isArray(f.sessions) && f.sessions.length > 0 &&
  f.sessions.every((s) =>
    s.projectId === f.id && statuses.has(s.status) && nonempty(s.id) &&
    nonempty(s.title) && nonempty(s.timeAgo)));
const diffFiles = [...m.MOCK_DIFF_DATA.initialFiles, ...m.MOCK_DIFF_DATA.extraFiles];
const diffFieldsOk = diffFiles.every((f) => nonempty(f.name) &&
  Number.isFinite(f.additions) && Number.isFinite(f.deletions) &&
  f.additions >= 0 && f.deletions >= 0);
const diffTotalsOk =
  m.MOCK_DIFF_DATA.fileCount === diffFiles.length &&
  m.MOCK_DIFF_DATA.additions === diffFiles.reduce((n, f) => n + f.additions, 0) &&
  m.MOCK_DIFF_DATA.deletions === diffFiles.reduce((n, f) => n + f.deletions, 0);
const roles = m.MOCK_CONVERSATION_THREAD.map((x) => x.role);
const threadShapeOk = ids(m.MOCK_CONVERSATION_THREAD).join(",") === "msg-1,msg-2,msg-3,msg-4" &&
  roles.join(",") === "user,agent,agent,agent" &&
  m.MOCK_CONVERSATION_THREAD.every((x) => nonempty(x.id));
const [user, plan, tool, approval] = m.MOCK_CONVERSATION_THREAD;
const planCardOk = plan?.plan?.status === "approved" && nonempty(plan.plan.content) &&
  plan.plan.options?.length === 2 &&
  plan.plan.options.every((o) => nonempty(o.id) && nonempty(o.label) && nonempty(o.desc)) &&
  plan.plan.selectedOption === "opt-1";
const toolCardOk = nonempty(tool?.toolUse?.name) && nonempty(tool?.toolUse?.input) &&
  nonempty(tool?.toolUse?.result) && tool?.question?.answered === true &&
  tool?.question?.options?.length === 3;
const approvalCardOk = nonempty(approval?.approval?.toolName) &&
  approval?.approval?.consequential === true &&
  approval?.approval?.approvalId === undefined &&
  nonempty(approval?.approval?.description) &&
  typeof approval.approval.params === "object" && approval.approval.params !== null;
const diffRefOk = approval?.showDiffCard === true && approval?.diffSummary === m.MOCK_DIFF_DATA;
const goal = m.MOCK_GOAL_STATE;
const goalShapeOk = goal.active === false && goal.paused === false &&
  nonempty(goal.title) && Number.isFinite(goal.currentTurn) &&
  Number.isFinite(goal.maxTurns) && Number.isFinite(goal.elapsedSeconds) &&
  Number.isFinite(goal.budgetRemaining);
const goalBoundsOk = goal.currentTurn >= 0 && goal.currentTurn <= goal.maxTurns &&
  goal.elapsedSeconds >= 0 && goal.budgetRemaining >= 0;
const promptHintOk = m.STRATEGY_DOMAINS.every((d) => d.defaultPrompt.endsWith("："));
const dump = JSON.stringify([m.STRATEGY_DOMAINS, m.MODEL_OPTIONS, m.MOCK_PROJECT_FOLDERS,
  m.MOCK_DIFF_DATA, m.MOCK_CONVERSATION_THREAD, m.MOCK_GOAL_STATE]);
const noEchoKeys = !/"(?:token|cookie|password|secret|apiKey)"/i.test(dump);
const cases = [
  ids(m.STRATEGY_DOMAINS).join(",") === "precision-match,compliance-gate,batch-outreach,pipeline-insights",
  domainFieldsOk,
  ids(m.MODEL_OPTIONS).join(",") === "deepseek-v4,deepseek-v3,claude-3-5-sonnet,gpt-4o",
  modelFieldsOk,
  ids(m.MOCK_PROJECT_FOLDERS).join(",") === "proj-core-rd,proj-pool,proj-campus",
  foldersOk,
  diffFieldsOk,
  diffTotalsOk,
  threadShapeOk,
  planCardOk,
  toolCardOk,
  approvalCardOk,
  diffRefOk,
  goalShapeOk,
  goalBoundsOk,
  promptHintOk,
  noEchoKeys,
];
process.stdout.write(JSON.stringify({ cases }));
"""

EXPECTED_CASES = (True,) * 17
LABELS = {"cases": "用例"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 仿真数据试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 仿真数据试算失败，请核对 Node.js 24+ 与 mockData.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的仿真数据结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"仿真数据{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"仿真数据{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_mock_data.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_mock_data.py")
    if "共 15 项结构、17 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_mock_data.py 检查 15 项结构、17 项行为")
    return 2


def check_mock_data() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_mock_data()
    except (OSError, ValueError) as error:
        print(f"仿真数据卡片契约核对失败，{error}", file=sys.stderr)
        return 2
    print(f"仿真数据卡片契约一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
