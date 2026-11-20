#!/usr/bin/env python3
"""核对暂停队列项的重试条件与原因文案。

重新排队会用持久化的完整输入创建新请求：只有未关联既有请求、输入没有
进入会话的 `followUp` 才能重试。归档、回合未完成与摘要失败各有三档文案，
顺序固定为「去重 → 输入已写入 → 可重试」；转向消息与未知原因单独处理，
未知原因不得声称可以重新排队。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RETRY = "apps/desktop/src/renderer/src/data/queueRetry.ts"

FRAGMENTS = (
    'import type { QueueItem } from "@boss-harness/protocol";',
    "export function queueItemRetryable(item: QueueItem): boolean {",
    'if (item.kind !== "followUp" || item.status !== "paused" || item.deduplicated === true) return false;',
    'if (item.failureCode === "TURN_START_FAILED") return item.inputPersisted === false;',
    'if (item.pausedReason === "COMPACTION_FAILED" || item.pausedReason === "THREAD_ARCHIVED"',
    '|| item.pausedReason === "TURN_NOT_COMPLETED") {',
    "return item.inputPersisted !== true;",
    "export function queuePauseReasonText(item: QueueItem): string | null {",
    'if (item.status !== "paused") return null;',
    'if (item.kind === "steering") {',
    'return "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。";',
    'if (item.kind !== "followUp") return null;',
    'if (item.pausedReason === "THREAD_ARCHIVED") {',
    'if (item.deduplicated === true) return "会话归档时暂停，不会自动投递；该输入已关联既有请求，请核对后决定是否撤回。";',
    'if (item.inputPersisted === true) return "会话归档时暂停，不会自动投递；输入已写入会话，请核对后决定是否撤回。";',
    'return "会话归档时暂停，不会自动投递；恢复会话后可重新排队或撤回。";',
    'if (item.pausedReason === "TURN_NOT_COMPLETED") {',
    'if (item.deduplicated === true) return "上一个回合未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";',
    'if (item.inputPersisted === true) return "上一个回合未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";',
    'return "上一个回合未完成，已暂停且不会自动投递；可重新排队或撤回。";',
    'if (item.pausedReason === "COMPACTION_FAILED") {',
    'if (item.deduplicated === true) return "摘要未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";',
    'if (item.inputPersisted === true) return "摘要未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";',
    'return "摘要未完成，已暂停；可重新排队或撤回。";',
    'if (item.failureCode === "TURN_START_FAILED" || item.deduplicated === true) return null;',
    'if (item.inputPersisted === true) return "已暂停且不会自动投递；输入已写入会话，请核对后决定是否撤回。";',
    'return "已暂停且不会自动投递；当前不支持直接重新排队，请核对后决定是否撤回或作为新消息提交。";',
)

ORDERED = (
    # 重试条件：类型、状态、去重、启动失败与三类暂停原因。
    (
        "export function queueItemRetryable(item: QueueItem): boolean {",
        'if (item.kind !== "followUp" || item.status !== "paused" || item.deduplicated === true) return false;',
        'if (item.failureCode === "TURN_START_FAILED") return item.inputPersisted === false;',
        'if (item.pausedReason === "COMPACTION_FAILED" || item.pausedReason === "THREAD_ARCHIVED"',
        '|| item.pausedReason === "TURN_NOT_COMPLETED") {',
        "return item.inputPersisted !== true;",
    ),
    # 文案入口：非暂停、转向消息、非 followUp 依次早退。
    (
        "export function queuePauseReasonText(item: QueueItem): string | null {",
        'if (item.status !== "paused") return null;',
        'if (item.kind === "steering") {',
        'return "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。";',
        'if (item.kind !== "followUp") return null;',
    ),
    # 归档：去重、输入已写入、可重新排队。
    (
        'if (item.pausedReason === "THREAD_ARCHIVED") {',
        'if (item.deduplicated === true) return "会话归档时暂停，不会自动投递；该输入已关联既有请求，请核对后决定是否撤回。";',
        'if (item.inputPersisted === true) return "会话归档时暂停，不会自动投递；输入已写入会话，请核对后决定是否撤回。";',
        'return "会话归档时暂停，不会自动投递；恢复会话后可重新排队或撤回。";',
    ),
    # 回合未完成：同样的三档顺序。
    (
        'if (item.pausedReason === "TURN_NOT_COMPLETED") {',
        'if (item.deduplicated === true) return "上一个回合未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";',
        'if (item.inputPersisted === true) return "上一个回合未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";',
        'return "上一个回合未完成，已暂停且不会自动投递；可重新排队或撤回。";',
    ),
    # 摘要失败：同样的三档顺序。
    (
        'if (item.pausedReason === "COMPACTION_FAILED") {',
        'if (item.deduplicated === true) return "摘要未完成，已暂停；该输入已关联既有请求，请核对后决定是否撤回。";',
        'if (item.inputPersisted === true) return "摘要未完成，已暂停；输入已写入会话，请核对后决定是否撤回。";',
        'return "摘要未完成，已暂停；可重新排队或撤回。";',
    ),
    # 通用出口：启动失败与去重不再重复提示；未知原因不声称可重新排队。
    (
        'if (item.failureCode === "TURN_START_FAILED" || item.deduplicated === true) return null;',
        'if (item.inputPersisted === true) return "已暂停且不会自动投递；输入已写入会话，请核对后决定是否撤回。";',
        'return "已暂停且不会自动投递；当前不支持直接重新排队，请核对后决定是否撤回或作为新消息提交。";',
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


def check_queue_retry() -> int:
    source = _read(RETRY)
    checked = 0
    checked += _expect(FRAGMENTS, source, RETRY)
    for group in ORDERED:
        checked += _ordered(group, source, RETRY)
    # 反向断言：去重与输入已写入必须在各分支最先拦截；
    # TURN_START_FAILED 只出现在重试判定与通用出口。
    if source.count("item.deduplicated === true") != 5:
        raise ValueError(f"{RETRY} 的去重项必须在重试与三条暂停文案中最先拦截")
    if source.count("item.inputPersisted === true") != 4:
        raise ValueError(f"{RETRY} 的输入已写入必须在三条文案与通用出口分别处理")
    if source.count('"TURN_START_FAILED"') != 2:
        raise ValueError(f"{RETRY} 的启动失败只出现在重试判定与通用出口")
    return checked + 3


def main() -> int:
    try:
        checked = check_queue_retry()
    except ValueError as error:
        print(f"队列重试核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列重试一致：{checked} 项条件与原因文案")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
