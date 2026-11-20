#!/usr/bin/env python3
"""核对实时工具事件映射的终态字段、恢复建议与大结果投影。

`toolCall/completed` 是工具卡的终态：内核没带的字段必须清掉，否则新内核的启动态或
上一次的错误码、恢复建议会残留到结束。错误码与恢复建议只接受字符串，实时结果与
重新读取的历史使用相同字段。大结果按内联、引用、省略三路投影，界面据此决定展示。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EVENTS = "apps/desktop/src/renderer/src/data/harnessEvents.ts"

EVENT_FRAGMENTS = (
    "resultSummary?: string; error?: { code?: string; message?: string; recovery_action?: string };",
    "const errorCode = itemText(params.error?.code);",
    "const recoveryAction = itemText(params.error?.recovery_action);",
    "const durationMs = toolDurationMs(params.durationMs);",
    "result: itemText(params.resultSummary) ?? itemText(params.error?.message) ?? status ?? \"已结束\" };",
    "else delete toolUse.status;",
    "else delete toolUse.executionState;",
    "else delete toolUse.errorCode;",
    "else delete toolUse.recoveryAction;",
    "else delete toolUse.durationMs;",
    "if (params.result) item = { ...item, toolUse: { ...item.toolUse!, resultRef: undefined, output: JSON.stringify(params.result, null, 2) } };",
    "else if (resultRef) item = { ...item, toolUse: { ...item.toolUse!, resultRef, output: undefined } };",
    'else if (params.resultOmitted) item = { ...item, toolUse: { ...item.toolUse!, resultRef: undefined, output: "结果较大，实时详情已省略；完整结果已保存到会话历史。" } };',
    'case "pending_approval": return "等待审批";',
    'case "queued": return "排队中";',
    'case "not_approved": return "未获批准";',
    'default: return "正在执行";',
    'if (event.method !== "approval/requested" || !remembered) return null;',
    "if (approvalConsequential(params.consequential)) return null;",
    "return approvalId && toolName && remembered.has(toolName) ? { approvalId, toolName } : null;",
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


def check_harness_events() -> int:
    events = _read(EVENTS)
    checked = _expect(EVENT_FRAGMENTS, events, EVENTS)
    # 完成事件：先读字段，再逐项写入终态；错误码与恢复建议都以字符串为唯一来源。
    checked += _ordered(
        (
            "const status = toolStatus(params.status);",
            "const errorCode = itemText(params.error?.code);",
            "const recoveryAction = itemText(params.error?.recovery_action);",
            "const durationMs = toolDurationMs(params.durationMs);",
            "if (status) toolUse.status = status;",
            "if (executionState) toolUse.executionState = executionState;",
            "if (errorCode) toolUse.errorCode = errorCode;",
            "if (recoveryAction !== undefined) toolUse.recoveryAction = recoveryAction;",
            "if (durationMs !== undefined) toolUse.durationMs = durationMs;",
            "if (params.result) item = { ...item,",
            "else if (resultRef) item = { ...item,",
            "else if (params.resultOmitted) item = { ...item,",
        ),
        events,
        EVENTS,
    )
    # 反向断言：恢复建议不得直接透传未校验字段，也不得只写不清。
    if "toolUse.recoveryAction = params.error?.recovery_action" in events:
        raise ValueError(f"{EVENTS} 不得跳过字符串校验写入恢复建议")
    if "if (errorCode) toolUse.errorCode = errorCode; else delete toolUse.errorCode;" not in events:
        raise ValueError(f"{EVENTS} 的错误码必须在缺失时清除旧值")
    if "if (recoveryAction !== undefined) toolUse.recoveryAction = recoveryAction; else delete toolUse.recoveryAction;" not in events:
        raise ValueError(f"{EVENTS} 的恢复建议必须在缺失时清除旧值")
    if "approvalConsequential(params.consequential) ?" in events:
        raise ValueError(f"{EVENTS} 的自动批准不得省略高风险判定")
    return checked + 1


def main() -> int:
    try:
        checked = check_harness_events()
    except ValueError as error:
        print(f"实时工具事件映射核对失败，{error}", file=sys.stderr)
        return 2
    print(f"实时工具事件映射一致：{checked} 项终态清理、恢复建议与大结果投影")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
