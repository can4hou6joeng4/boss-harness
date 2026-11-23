#!/usr/bin/env python3
"""核对会话区本地消息与父级下发消息的合并规则。

`messageMerge.ts` 以新消息为准，只保留新数据尚未给出结果的本地操作：
审批卡已提交或已有结论时不能重新变成可提交，已回答的问题不能回退，
示例模式保存的计划正文与已选项不能被空数据覆盖；父级已移除的消息也不能
因为本地副本而复活。这里用 Node 直接调用真实 `mergeLocalMessageState`，
逐项核对上述分支。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MERGE = "apps/desktop/src/renderer/src/data/messageMerge.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

MERGE_FRAGMENTS = (
    "export function mergeLocalMessageState(incoming: MessageItem[], previous: MessageItem[]): MessageItem[] {",
    "if (!previous.length) return incoming;",
    "const localById = new Map(previous.map(message => [message.id, message]));",
    "return incoming.map(message => {",
    "return local ? mergeMessage(message, local) : message;",
    "approval && localApproval && approval.approvalId === localApproval.approvalId && approval.decision === undefined",
    "if (localApproval.decision !== undefined) {",
    "...(localApproval.remember !== undefined ? { remember: localApproval.remember } : {})",
    "} else if (localApproval.submitted === true) {",
    "merged = { ...merged, approval: { ...approval, submitted: true } };",
    "question && localQuestion && question.id === localQuestion.id",
    "&& question.answered !== true && localQuestion.answered === true",
    "merged = { ...merged, question: { ...question, answered: true, selected: localQuestion.selected } };",
    "plan && localPlan && plan.slug === localPlan.slug",
    'if (plan.status === "submitted" && localPlan.status !== "submitted") {',
    "merged = { ...merged, plan: { ...plan, status: localPlan.status, selectedOption: localPlan.selectedOption, content: localPlan.content } };",
    "} else if (plan.selectedOption === undefined && localPlan.selectedOption !== undefined) {",
    "merged = { ...merged, plan: { ...plan, selectedOption: localPlan.selectedOption } };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { mergeLocalMessageState } = await import(pathToFileURL(process.argv[1]).href);
const msg = (id, extra = {}) => ({ id, role: "agent", ...extra });
const decision = (approval) => (approval && approval.decision !== undefined ? approval.decision : "none");
const results = {
  approvals: [
    (() => {
      const incoming = [msg("m1")];
      return mergeLocalMessageState(incoming, []) === incoming;
    })(),
    (() => {
      const incoming = [msg("m1", { approval: { approvalId: "a1" } })];
      const local = [msg("m1", { approval: { approvalId: "a1", decision: "approve", remember: true } })];
      const approval = mergeLocalMessageState(incoming, local)[0].approval;
      return { decision: approval.decision, remember: approval.remember };
    })(),
    (() => {
      const incoming = [msg("m1", { approval: { approvalId: "a1", decision: "expired" } })];
      const local = [msg("m1", { approval: { approvalId: "a1", decision: "approve", remember: true } })];
      const approval = mergeLocalMessageState(incoming, local)[0].approval;
      return { decision: approval.decision, remember: approval.remember };
    })(),
    (() => {
      const incoming = [msg("m1", { approval: { approvalId: "a2" } })];
      const local = [msg("m1", { approval: { approvalId: "a1", decision: "deny" } })];
      return decision(mergeLocalMessageState(incoming, local)[0].approval);
    })(),
    (() => {
      const incoming = [msg("m1", { approval: { approvalId: "a1" } })];
      const local = [msg("m1", { approval: { approvalId: "a1", submitted: true } })];
      return mergeLocalMessageState(incoming, local)[0].approval.submitted === true;
    })(),
  ],
  questions: [
    (() => {
      const incoming = [msg("m1", { question: { id: "q1", answered: false } })];
      const local = [msg("m1", { question: { id: "q1", answered: true, selected: ["A"] } })];
      const question = mergeLocalMessageState(incoming, local)[0].question;
      return { answered: question.answered, selected: question.selected };
    })(),
    (() => {
      const incoming = [msg("m1", { question: { id: "q1", answered: true, selected: ["B"] } })];
      const local = [msg("m1", { question: { id: "q1", answered: true, selected: ["A"] } })];
      const question = mergeLocalMessageState(incoming, local)[0].question;
      return { answered: question.answered, selected: question.selected };
    })(),
    (() => {
      const incoming = [msg("m1", { question: { id: "q2" } })];
      const local = [msg("m1", { question: { id: "q1", answered: true } })];
      const question = mergeLocalMessageState(incoming, local)[0].question;
      return question.answered === true ? "answered" : "none";
    })(),
    (() => {
      const incoming = [msg("m1", { question: { id: "q1" } })];
      const local = [msg("m1", { question: { id: "q1" } })];
      const question = mergeLocalMessageState(incoming, local)[0].question;
      return question.answered === true ? "answered" : "none";
    })(),
  ],
  plans: [
    (() => {
      const incoming = [msg("m1", { plan: { slug: "p1", status: "submitted", content: "新正文" } })];
      const local = [msg("m1", { plan: { slug: "p1", status: "approved", selectedOption: "x", content: "本地正文" } })];
      const plan = mergeLocalMessageState(incoming, local)[0].plan;
      return { status: plan.status, selectedOption: plan.selectedOption, content: plan.content };
    })(),
    (() => {
      const incoming = [msg("m1", { plan: { slug: "p1", status: "submitted", content: "新正文" } })];
      const local = [msg("m1", { plan: { slug: "p1", status: "submitted", selectedOption: "x" } })];
      const plan = mergeLocalMessageState(incoming, local)[0].plan;
      return { status: plan.status, selectedOption: plan.selectedOption, content: plan.content };
    })(),
    (() => {
      const incoming = [msg("m1", { plan: { slug: "p1", status: "submitted", selectedOption: "y" } })];
      const local = [msg("m1", { plan: { slug: "p1", status: "submitted", selectedOption: "x" } })];
      const plan = mergeLocalMessageState(incoming, local)[0].plan;
      return { selectedOption: plan.selectedOption };
    })(),
    (() => {
      const incoming = [msg("m1", { plan: { slug: "p2", status: "submitted", content: "新正文" } })];
      const local = [msg("m1", { plan: { slug: "p1", status: "approved", selectedOption: "x", content: "本地正文" } })];
      const plan = mergeLocalMessageState(incoming, local)[0].plan;
      return {
        status: plan.status,
        selectedOption: plan.selectedOption === undefined ? "none" : plan.selectedOption,
        content: plan.content,
      };
    })(),
  ],
  mixed: [
    (() => {
      const incoming = [msg("keep")];
      const local = [msg("gone")];
      return mergeLocalMessageState(incoming, local).map((message) => message.id);
    })(),
    (() => {
      const incoming = [msg("b"), msg("a")];
      const local = [msg("a"), msg("b")];
      return mergeLocalMessageState(incoming, local).map((message) => message.id);
    })(),
    (() => {
      const incoming = [msg("m1", { content: "新" })];
      const local = [msg("m1", { content: "旧" })];
      return mergeLocalMessageState(incoming, local)[0].content;
    })(),
    (() => {
      const incoming = [msg("m1", { approval: { approvalId: "a1" } })];
      const local = [msg("m1")];
      return decision(mergeLocalMessageState(incoming, local)[0].approval);
    })(),
    (() => {
      const incoming = [msg("m1"), msg("m2")];
      const local = [msg("m1")];
      const merged = mergeLocalMessageState(incoming, local);
      return merged[1] === incoming[1];
    })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_APPROVALS = (
    True,
    {"decision": "approve", "remember": True},
    {"decision": "expired"},
    "none",
    True,
)
EXPECTED_QUESTIONS = (
    {"answered": True, "selected": ["A"]},
    {"answered": True, "selected": ["B"]},
    "none",
    "none",
)
EXPECTED_PLANS = (
    {"status": "approved", "selectedOption": "x", "content": "本地正文"},
    {"status": "submitted", "selectedOption": "x", "content": "新正文"},
    {"selectedOption": "y"},
    {"status": "submitted", "selectedOption": "none", "content": "新正文"},
)
EXPECTED_MIXED = (["keep"], ["b", "a"], "新", "none", True)


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
             str(ROOT / MERGE)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 消息合并试算失败，请核对 Node.js 24+ 与 messageMerge.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的消息合并结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回消息合并矩阵")
    for key in ("approvals", "questions", "plans", "mixed"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"消息合并{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"消息合并{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["approvals"], EXPECTED_APPROVALS, "审批")
    checked += _compare(payload["questions"], EXPECTED_QUESTIONS, "提问")
    checked += _compare(payload["plans"], EXPECTED_PLANS, "计划")
    checked += _compare(payload["mixed"], EXPECTED_MIXED, "混合")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_message_merge.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_message_merge.py")
    if "共 18 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_message_merge.py 检查 18 项结构、17 项行为")
    return 2


def check_message_merge() -> tuple[int, int]:
    structure = _expect(MERGE_FRAGMENTS, _read(MERGE), MERGE)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_message_merge()
    except (OSError, ValueError) as error:
        print(f"消息合并规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"消息合并规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
