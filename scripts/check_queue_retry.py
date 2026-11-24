#!/usr/bin/env python3
"""核对暂停队列项的重试条件与原因文案。

重新排队会用持久化的完整输入创建新请求：只有未关联既有请求、输入没有
进入会话的 `followUp` 才能重试。归档、回合未完成与摘要失败各有三档文案，
顺序固定为「去重 → 输入已写入 → 可重试」；转向消息与未知原因单独处理，
未知原因不得声称可以重新排队。结构侧固定判定顺序与文案分档；行为侧把真实
模块复制到临时目录，由 Node 直接加载 `queueItemRetryable` 与
`queuePauseReasonText` 驱动组合矩阵。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
RETRY = "apps/desktop/src/renderer/src/data/queueRetry.ts"

EXPECTED = 30

NODE_SCRIPT = """\
import { queueItemRetryable, queuePauseReasonText } from "./queueRetry.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const item = (patch: Record<string, unknown> = {}): any => ({ kind: "followUp", status: "paused", ...patch });

expect("转向消息不可重试", queueItemRetryable(item({ kind: "steering" })) === false);
expect("非暂停不可重试", queueItemRetryable(item({ status: "running" })) === false);
expect("缺少暂停原因不可重试", queueItemRetryable(item()) === false);
expect("已去重不可重试", queueItemRetryable(item({ pausedReason: "COMPACTION_FAILED", deduplicated: true })) === false);
expect("启动失败且未写入可重试", queueItemRetryable(item({ failureCode: "TURN_START_FAILED", inputPersisted: false })) === true);
expect("启动失败且已写入不可重试", queueItemRetryable(item({ failureCode: "TURN_START_FAILED", inputPersisted: true })) === false);
expect("启动失败且未确认不可重试", queueItemRetryable(item({ failureCode: "TURN_START_FAILED" })) === false);
expect("摘要失败且未写入可重试", queueItemRetryable(item({ pausedReason: "COMPACTION_FAILED" })) === true);
expect("摘要失败且已写入不可重试", queueItemRetryable(item({ pausedReason: "COMPACTION_FAILED", inputPersisted: true })) === false);
expect("归档且未写入可重试", queueItemRetryable(item({ pausedReason: "THREAD_ARCHIVED" })) === true);
expect("归档且已写入不可重试", queueItemRetryable(item({ pausedReason: "THREAD_ARCHIVED", inputPersisted: true })) === false);
expect("回合未完成且未写入可重试", queueItemRetryable(item({ pausedReason: "TURN_NOT_COMPLETED" })) === true);
expect("回合未完成且已写入不可重试", queueItemRetryable(item({ pausedReason: "TURN_NOT_COMPLETED", inputPersisted: true })) === false);
expect("未知暂停原因不可重试", queueItemRetryable(item({ pausedReason: "UNKNOWN" })) === false);

expect("非暂停无文案", queuePauseReasonText(item({ status: "running" })) === null);
expect(
  "转向消息文案",
  queuePauseReasonText(item({ kind: "steering" })) === "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。",
);
expect("其他类型无文案", queuePauseReasonText(item({ kind: "userMessage" })) === null);
const archivedDedup = queuePauseReasonText(item({ pausedReason: "THREAD_ARCHIVED", deduplicated: true }));
expect("归档去重文案", archivedDedup !== null && archivedDedup.includes("已关联既有请求"));
const archivedPersisted = queuePauseReasonText(item({ pausedReason: "THREAD_ARCHIVED", inputPersisted: true }));
expect("归档已写入文案", archivedPersisted !== null && archivedPersisted.includes("输入已写入会话"));
const archivedPlain = queuePauseReasonText(item({ pausedReason: "THREAD_ARCHIVED" }));
expect("归档可重新排队文案", archivedPlain !== null && archivedPlain.includes("可重新排队"));
const notCompletedDedup = queuePauseReasonText(item({ pausedReason: "TURN_NOT_COMPLETED", deduplicated: true }));
expect("回合未完成去重文案", notCompletedDedup !== null && notCompletedDedup.includes("已关联既有请求"));
const notCompletedPersisted = queuePauseReasonText(item({ pausedReason: "TURN_NOT_COMPLETED", inputPersisted: true }));
expect("回合未完成已写入文案", notCompletedPersisted !== null && notCompletedPersisted.includes("输入已写入会话"));
const notCompletedPlain = queuePauseReasonText(item({ pausedReason: "TURN_NOT_COMPLETED" }));
expect("回合未完成可重新排队文案", notCompletedPlain !== null && notCompletedPlain.includes("可重新排队"));
const compactionDedup = queuePauseReasonText(item({ pausedReason: "COMPACTION_FAILED", deduplicated: true }));
expect("摘要失败去重文案", compactionDedup !== null && compactionDedup.includes("已关联既有请求"));
const compactionPersisted = queuePauseReasonText(item({ pausedReason: "COMPACTION_FAILED", inputPersisted: true }));
expect("摘要失败已写入文案", compactionPersisted !== null && compactionPersisted.includes("输入已写入会话"));
const compactionPlain = queuePauseReasonText(item({ pausedReason: "COMPACTION_FAILED" }));
expect("摘要失败可重新排队文案", compactionPlain !== null && compactionPlain.includes("可重新排队"));
expect("启动失败无重复文案", queuePauseReasonText(item({ failureCode: "TURN_START_FAILED" })) === null);
expect("未知原因去重无文案", queuePauseReasonText(item({ pausedReason: "UNKNOWN", deduplicated: true })) === null);
const unknownPersisted = queuePauseReasonText(item({ pausedReason: "UNKNOWN", inputPersisted: true }));
expect("未知原因已写入文案", unknownPersisted !== null && unknownPersisted.includes("输入已写入会话"));
const unknownPlain = queuePauseReasonText(item({ pausedReason: "UNKNOWN" }));
expect("未知原因不支持重排文案", unknownPlain !== null && unknownPlain.includes("不支持直接重新排队"));

console.log(`PASS ${passed}`);
"""

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


def _check_structure(source: str) -> int:
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


def _check_behaviors() -> int:
    source = _read(RETRY)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "queueRetry.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("队列重试行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"队列重试行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_retry.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_retry.py")
    if "共 56 项结构、30 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_retry.py 检查 56 项结构、30 项行为")
    return 2


def check_queue_retry() -> tuple[int, int]:
    source = _read(RETRY)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_retry()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"队列重试核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列重试一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
