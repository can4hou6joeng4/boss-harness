#!/usr/bin/env python3
"""核对审批回执文案、按钮可用性与拒绝后的刷新判定。

`approvalFailure.ts` 把回执未知说成「尚未确认」而不是未送达；审批卡按钮按
归档、缺少审批标识、已提交、等待回执的顺序判定不可用原因；明确拒绝按拒绝码
给出不同提示，自动批准路径复用同一组拒绝码但说明的是自动提交，已有结论时
不重新开放操作；只有回合已结束或审批记录已变更的拒绝码才重读会话，
`APPROVAL_BUSY` 不刷新。这里用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = "apps/desktop/src/renderer/src/data/approvalFailure.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

APPROVAL_FRAGMENTS = (
    'export function approvalUnconfirmedNotice(reason?: string, action: "审批" | "自动批准" = "审批"): string {',
    "return `${action}结果尚未确认${reason ? `（${reason}）` : \"\"}；请先核对审批与工具结果，不要直接重复提交。`;",
    'export type ApprovalBlockReason = "archived" | "submitted" | "selfPending" | "otherPending" | "missingId";',
    "export function approvalBlockReason(",
    'if (archived) return "archived";',
    'if (!input.simulateLocal && !input.approvalId) return "missingId";',
    'if (submitted) return "submitted";',
    "if (pendingMessageId === null) return null;",
    'return pendingMessageId === messageId ? "selfPending" : "otherPending";',
    "export function approvalRejectionNotice(code: string | undefined, reason: string): string {",
    "const detail = reason ? `：${reason}` : \"\";",
    "return `审批仍由活动回合持有${detail}；请先停止回合或等待它结束后再处理，不要反复提交。`;",
    "return `审批所属回合已结束或会话已归档，不再接受新的裁决${detail}；正在刷新会话状态。`;",
    "return `该审批已按相反决策处理${detail}；正在刷新会话状态。`;",
    "return `审批不存在或所属会话已删除${detail}；正在刷新会话状态。`;",
    "return `审批记录无效${detail}；正在刷新会话状态。`;",
    "return `审批记录重复，内核拒绝裁决${detail}；正在刷新会话状态。`;",
    "return `审批已失效，不再接受新的裁决${detail}；正在刷新会话状态。`;",
    "return `审批未被受理${detail || \"（可能已过期或状态已刷新）\"}；请刷新会话后再试。`;",
    "export function autoApprovalRejectionNotice(code: string | undefined, reason: string, decided: boolean): string {",
    "if (decided) {",
    "return `自动批准未被内核受理${detail}；该审批已有结论，界面未重新开放操作。审批结论不代表工具执行成功，请核对工具结果。`;",
    "return `自动批准未被内核受理${detail}；审批仍由活动回合持有，请先停止回合或等待它结束后再处理，不要反复提交。`;",
    "return `自动批准未被内核受理${detail}；审批所属回合已结束或会话已归档，已不再接受裁决，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail}；该审批已按相反决策处理，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail}；审批不存在或所属会话已删除，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail}；审批记录无效，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail}；审批记录重复，内核拒绝自动批准，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail}；审批已失效，不再接受裁决，正在刷新会话状态。`;",
    "return `自动批准未被内核受理${detail || \"（可能已过期）\"}；已显示本次审批供核对，请刷新会话后再处理。`;",
    "export function approvalRejectionRefreshes(code: string | undefined): boolean {",
    'return code === "APPROVAL_CLOSED" || code === "APPROVAL_CONFLICT"',
    '|| code === "APPROVAL_NOT_FOUND" || code === "APPROVAL_INVALID" || code === "APPROVAL_AMBIGUOUS"',
    '|| code === "APPROVAL_EXPIRED";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  approvalUnconfirmedNotice, approvalBlockReason, approvalRejectionNotice,
  autoApprovalRejectionNotice, approvalRejectionRefreshes,
} = await import(pathToFileURL(process.argv[1]).href);
const CODES = ["APPROVAL_BUSY", "APPROVAL_CLOSED", "APPROVAL_CONFLICT", "APPROVAL_NOT_FOUND",
  "APPROVAL_INVALID", "APPROVAL_AMBIGUOUS", "APPROVAL_EXPIRED", undefined, "OTHER"];
const real = { approvalId: "a1", simulateLocal: false };
const results = {
  unconfirmed: [
    approvalUnconfirmedNotice(),
    approvalUnconfirmedNotice("超时"),
    approvalUnconfirmedNotice(undefined, "自动批准"),
    approvalUnconfirmedNotice("超时", "自动批准"),
  ],
  block: [
    approvalBlockReason("m1", true, "m1", true, { simulateLocal: false }),
    approvalBlockReason("m1", false, null, false, { simulateLocal: false }),
    approvalBlockReason("m1", false, null, false, { approvalId: "", simulateLocal: false }),
    approvalBlockReason("m1", false, null, false, { simulateLocal: true }),
    approvalBlockReason("m1", true, null, false, { simulateLocal: false }),
    approvalBlockReason("m1", true, null, false, real),
    approvalBlockReason("m1", true, "m2", false, real),
    approvalBlockReason("m1", false, "m1", false, real),
    approvalBlockReason("m1", false, "m2", false, real),
    approvalBlockReason("m1", false, null, false, real),
  ],
  rejection: CODES.map(code => approvalRejectionNotice(code, "r")),
  rejectionBare: [
    approvalRejectionNotice("APPROVAL_BUSY", ""),
    approvalRejectionNotice("APPROVAL_CLOSED", ""),
    approvalRejectionNotice(undefined, ""),
  ],
  auto: CODES.map(code => autoApprovalRejectionNotice(code, "r", false)),
  autoEdge: [
    autoApprovalRejectionNotice("APPROVAL_BUSY", "r", true),
    autoApprovalRejectionNotice(undefined, "", true),
    autoApprovalRejectionNotice("APPROVAL_BUSY", "", false),
    autoApprovalRejectionNotice(undefined, "", false),
  ],
  refresh: CODES.map(code => approvalRejectionRefreshes(code)),
};
process.stdout.write(JSON.stringify(results));
"""

REFRESH = "；正在刷新会话状态。"
AUTO = "自动批准未被内核受理"
EXPECTED_UNCONFIRMED = (
    "审批结果尚未确认；请先核对审批与工具结果，不要直接重复提交。",
    "审批结果尚未确认（超时）；请先核对审批与工具结果，不要直接重复提交。",
    "自动批准结果尚未确认；请先核对审批与工具结果，不要直接重复提交。",
    "自动批准结果尚未确认（超时）；请先核对审批与工具结果，不要直接重复提交。",
)
EXPECTED_BLOCK = (
    "archived", "missingId", "missingId", None, "missingId",
    "submitted", "submitted", "selfPending", "otherPending", None,
)
EXPECTED_REJECTION = (
    "审批仍由活动回合持有：r；请先停止回合或等待它结束后再处理，不要反复提交。",
    "审批所属回合已结束或会话已归档，不再接受新的裁决：r" + REFRESH,
    "该审批已按相反决策处理：r" + REFRESH,
    "审批不存在或所属会话已删除：r" + REFRESH,
    "审批记录无效：r" + REFRESH,
    "审批记录重复，内核拒绝裁决：r" + REFRESH,
    "审批已失效，不再接受新的裁决：r" + REFRESH,
    "审批未被受理：r；请刷新会话后再试。",
    "审批未被受理：r；请刷新会话后再试。",
)
EXPECTED_REJECTION_BARE = (
    "审批仍由活动回合持有；请先停止回合或等待它结束后再处理，不要反复提交。",
    "审批所属回合已结束或会话已归档，不再接受新的裁决" + REFRESH,
    "审批未被受理（可能已过期或状态已刷新）；请刷新会话后再试。",
)
EXPECTED_AUTO = (
    AUTO + "：r；审批仍由活动回合持有，请先停止回合或等待它结束后再处理，不要反复提交。",
    AUTO + "：r；审批所属回合已结束或会话已归档，已不再接受裁决，正在刷新会话状态。",
    AUTO + "：r；该审批已按相反决策处理，正在刷新会话状态。",
    AUTO + "：r；审批不存在或所属会话已删除，正在刷新会话状态。",
    AUTO + "：r；审批记录无效，正在刷新会话状态。",
    AUTO + "：r；审批记录重复，内核拒绝自动批准，正在刷新会话状态。",
    AUTO + "：r；审批已失效，不再接受裁决，正在刷新会话状态。",
    AUTO + "：r；已显示本次审批供核对，请刷新会话后再处理。",
    AUTO + "：r；已显示本次审批供核对，请刷新会话后再处理。",
)
DECIDED = "；该审批已有结论，界面未重新开放操作。审批结论不代表工具执行成功，请核对工具结果。"
EXPECTED_AUTO_EDGE = (
    AUTO + "：r" + DECIDED,
    AUTO + DECIDED,
    AUTO + "；审批仍由活动回合持有，请先停止回合或等待它结束后再处理，不要反复提交。",
    AUTO + "（可能已过期）；已显示本次审批供核对，请刷新会话后再处理。",
)
EXPECTED_REFRESH = (False, True, True, True, True, True, True, False, False)


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
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / APPROVAL)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 审批回执试算失败，请核对 Node.js 24+ 与 approvalFailure.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的审批回执结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回审批回执矩阵")
    for key in ("unconfirmed", "block", "rejection", "rejectionBare", "auto", "autoEdge", "refresh"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"审批回执{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"审批回执{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["unconfirmed"], EXPECTED_UNCONFIRMED, "未确认文案")
    checked += _compare(payload["block"], EXPECTED_BLOCK, "按钮可用性")
    checked += _compare(payload["rejection"], EXPECTED_REJECTION, "拒绝文案")
    checked += _compare(payload["rejectionBare"], EXPECTED_REJECTION_BARE, "无原因拒绝文案")
    checked += _compare(payload["auto"], EXPECTED_AUTO, "自动批准拒绝文案")
    checked += _compare(payload["autoEdge"], EXPECTED_AUTO_EDGE, "自动批准边界")
    checked += _compare(payload["refresh"], EXPECTED_REFRESH, "刷新判定")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_approval_failure.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_approval_failure.py")
    if "共 34 项结构、48 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_approval_failure.py 检查 34 项结构、48 项行为")
    return 2


def check_approval_failure() -> tuple[int, int]:
    structure = _expect(APPROVAL_FRAGMENTS, _read(APPROVAL), APPROVAL)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_approval_failure()
    except (OSError, ValueError) as error:
        print(f"审批回执规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批回执规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
