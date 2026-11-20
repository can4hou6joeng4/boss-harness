#!/usr/bin/env python3
"""核对任务队列的状态与暂停原因文案。

列表与完整输入窗口共用状态文案：暂停项按内核记录的具体来源显示，关联去重
项说明输入已进入既有回合，其余沿用通用标签。这里固定分支顺序、暂停说明的
前置空判定与 `retryAvailable` 的适用范围，避免更宽泛的原因覆盖具体原因，
或给用户错误的下一步暗示。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STATUS = "apps/desktop/src/renderer/src/data/queueStatus.ts"

FRAGMENTS = (
    'import type { QueueItem } from "@boss-harness/protocol";',
    'import { queuePauseReasonText } from "./queueRetry";',
    'const LABELS: Record<QueueItem["status"], string> = {',
    'queued: "排队中",',
    'delivering: "正在投递",',
    'delivered: "已投递",',
    'paused: "已暂停",',
    'cancelled: "已撤回",',
    "export function queueStatusLabel(item: QueueItem): string {",
    'if (item.status === "paused" && item.failureCode === "TURN_START_FAILED") return "启动失败，未执行";',
    'if (item.status === "paused" && item.pausedReason === "COMPACTION_FAILED") return "摘要失败，已暂停";',
    'if (item.status === "paused" && item.pausedReason === "THREAD_ARCHIVED") return "归档时暂停";',
    'if (item.status === "paused" && item.pausedReason === "TURN_NOT_COMPLETED") return "回合未完成，已暂停";',
    'if (item.status === "delivered" && item.deduplicated) return "已关联已有回合";',
    "return LABELS[item.status];",
    "export function queuePauseDetail(item: QueueItem, retryAvailable: boolean): string | null {",
    'if (item.status !== "paused") return null;',
    'if (item.failureCode === "TURN_START_FAILED") {',
    'if (item.inputPersisted === true) return "输入已保留在当前会话，核对后可发起新任务。";',
    "if (item.inputPersisted === false) {",
    'return retryAvailable ? "输入尚未写入当前会话，可直接重新排队。" : "输入尚未写入当前会话，核对后可发起新任务。";',
    'return "请先核对当前会话，再决定是否发起新任务。";',
    'if (item.deduplicated === true && item.kind === "followUp" && item.pausedReason === undefined) {',
    'return "已暂停且不会自动投递；该输入已关联旧请求，请核对当前会话后决定是否撤回或发起新任务。";',
    "return queuePauseReasonText(item);",
)

ORDERED = (
    # 标签：启动失败 → 摘要失败 → 归档 → 回合未完成 → 关联去重 → 通用标签。
    (
        "export function queueStatusLabel(item: QueueItem): string {",
        'if (item.status === "paused" && item.failureCode === "TURN_START_FAILED") return "启动失败，未执行";',
        'if (item.status === "paused" && item.pausedReason === "COMPACTION_FAILED") return "摘要失败，已暂停";',
        'if (item.status === "paused" && item.pausedReason === "THREAD_ARCHIVED") return "归档时暂停";',
        'if (item.status === "paused" && item.pausedReason === "TURN_NOT_COMPLETED") return "回合未完成，已暂停";',
        'if (item.status === "delivered" && item.deduplicated) return "已关联已有回合";',
        "return LABELS[item.status];",
    ),
    # 说明：非暂停先返回 null → 启动失败的三态 → 关联去重 → 其余按原因。
    (
        "export function queuePauseDetail(item: QueueItem, retryAvailable: boolean): string | null {",
        'if (item.status !== "paused") return null;',
        'if (item.inputPersisted === true)',
        "if (item.inputPersisted === false) {",
        'return retryAvailable ? "输入尚未写入当前会话，可直接重新排队。"',
        'return "请先核对当前会话，再决定是否发起新任务。";',
        'if (item.deduplicated === true && item.kind === "followUp" && item.pausedReason === undefined) {',
        "return queuePauseReasonText(item);",
    ),
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_queue_status() -> int:
    source = _read(STATUS)
    checked = 0
    checked += _expect(FRAGMENTS, source, STATUS)
    for group in ORDERED:
        checked += _ordered(group, source, STATUS)
    # 反向断言：非暂停项先返回 null；retryAvailable 只影响启动失败且未写入的分支。
    if 'if (item.status === "paused") return null;' in source:
        raise ValueError(f"{STATUS} 的非暂停项必须先返回 null，不能进入暂停说明")
    if "if (retryAvailable) return" in source:
        raise ValueError(f"{STATUS} 的 retryAvailable 只能作为未写入分支的措辞选择")
    if 'if (item.status === "paused") return "已暂停";' in source:
        raise ValueError(f"{STATUS} 的暂停标签不得覆盖具体来源")
    return checked + 3


def main() -> int:
    try:
        checked = check_queue_status()
    except ValueError as error:
        print(f"队列状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列状态一致：{checked} 项标签、暂停原因与操作暗示")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
