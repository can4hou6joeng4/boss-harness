#!/usr/bin/env python3
"""核对任务队列的状态与暂停原因文案。

列表与完整输入窗口共用状态文案：暂停项按内核记录的具体来源显示，关联去重
项说明输入已进入既有回合，其余沿用通用标签。结构侧固定分支顺序、暂停说明的
前置空判定与 `retryAvailable` 的适用范围；行为侧把真实 `queueStatus.ts` 与
`queueRetry.ts` 复制到临时目录、改写类型导入，由 Node 驱动标签、说明与原因文案，
避免更宽泛的原因覆盖具体原因，或给用户错误的下一步暗示。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
STATUS = "apps/desktop/src/renderer/src/data/queueStatus.ts"
RETRY = "apps/desktop/src/renderer/src/data/queueRetry.ts"

EXPECTED = 29

NODE_SCRIPT = """\
import { queuePauseDetail, queueStatusLabel } from "./queueStatus.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

expect("排队标签", queueStatusLabel({ status: "queued" }) === "排队中");
expect("投递标签", queueStatusLabel({ status: "delivering" }) === "正在投递");
expect("已投递标签", queueStatusLabel({ status: "delivered" }) === "已投递");
expect("暂停标签", queueStatusLabel({ status: "paused" }) === "已暂停");
expect("撤回标签", queueStatusLabel({ status: "cancelled" }) === "已撤回");
expect(
  "启动失败优先于暂停原因",
  queueStatusLabel({
    status: "paused",
    failureCode: "TURN_START_FAILED",
    pausedReason: "THREAD_ARCHIVED",
  }) === "启动失败，未执行",
);
expect(
  "摘要失败标签",
  queueStatusLabel({ status: "paused", pausedReason: "COMPACTION_FAILED" }) === "摘要失败，已暂停",
);
expect(
  "归档标签",
  queueStatusLabel({ status: "paused", pausedReason: "THREAD_ARCHIVED" }) === "归档时暂停",
);
expect(
  "回合未完成标签",
  queueStatusLabel({ status: "paused", pausedReason: "TURN_NOT_COMPLETED" }) === "回合未完成，已暂停",
);
expect(
  "关联去重标签",
  queueStatusLabel({ status: "delivered", deduplicated: true }) === "已关联已有回合",
);
expect(
  "非投递去重不影响标签",
  queueStatusLabel({ status: "queued", deduplicated: true }) === "排队中",
);
expect(
  "未知暂停原因用通用标签",
  queueStatusLabel({ status: "paused", pausedReason: "UNKNOWN" }) === "已暂停",
);

expect(
  "非暂停无说明",
  queuePauseDetail({ status: "queued" }, true) === null
    && queuePauseDetail({ status: "delivered" }, true) === null,
);
expect(
  "启动失败已写入",
  queuePauseDetail(
    { status: "paused", failureCode: "TURN_START_FAILED", inputPersisted: true },
    true,
  ) === "输入已保留在当前会话，核对后可发起新任务。",
);
expect(
  "启动失败未写入可重试",
  queuePauseDetail(
    { status: "paused", failureCode: "TURN_START_FAILED", inputPersisted: false },
    true,
  ) === "输入尚未写入当前会话，可直接重新排队。",
);
expect(
  "启动失败未写入不可重试",
  queuePauseDetail(
    { status: "paused", failureCode: "TURN_START_FAILED", inputPersisted: false },
    false,
  ) === "输入尚未写入当前会话，核对后可发起新任务。",
);
expect(
  "启动失败状态未知",
  queuePauseDetail({ status: "paused", failureCode: "TURN_START_FAILED" }, true)
    === "请先核对当前会话，再决定是否发起新任务。",
);
expect(
  "关联去重说明",
  queuePauseDetail({ status: "paused", kind: "followUp", deduplicated: true }, true)
    === "已暂停且不会自动投递；该输入已关联旧请求，请核对当前会话后决定是否撤回或发起新任务。",
);
expect(
  "转向消息说明",
  queuePauseDetail({ status: "paused", kind: "steering" }, true)
    === "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。",
);
expect(
  "转向消息优先于去重",
  queuePauseDetail({ status: "paused", kind: "steering", deduplicated: true }, true)
    === "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。",
);
expect(
  "归档已关联说明",
  queuePauseDetail(
    { status: "paused", kind: "followUp", pausedReason: "THREAD_ARCHIVED", deduplicated: true },
    true,
  ) === "会话归档时暂停，不会自动投递；该输入已关联既有请求，请核对后决定是否撤回。",
);
expect(
  "归档已写入说明",
  queuePauseDetail(
    { status: "paused", kind: "followUp", pausedReason: "THREAD_ARCHIVED", inputPersisted: true },
    true,
  ) === "会话归档时暂停，不会自动投递；输入已写入会话，请核对后决定是否撤回。",
);
expect(
  "归档默认说明",
  queuePauseDetail({ status: "paused", kind: "followUp", pausedReason: "THREAD_ARCHIVED" }, true)
    === "会话归档时暂停，不会自动投递；恢复会话后可重新排队或撤回。",
);
expect(
  "回合未完成默认说明",
  queuePauseDetail({ status: "paused", kind: "followUp", pausedReason: "TURN_NOT_COMPLETED" }, true)
    === "上一个回合未完成，已暂停且不会自动投递；可重新排队或撤回。",
);
expect(
  "摘要失败默认说明",
  queuePauseDetail({ status: "paused", kind: "followUp", pausedReason: "COMPACTION_FAILED" }, true)
    === "摘要未完成，已暂停；可重新排队或撤回。",
);
expect(
  "启动失败不再重复原因",
  queuePauseDetail(
    { status: "paused", kind: "followUp", failureCode: "TURN_START_FAILED", inputPersisted: true },
    true,
  ) === "输入已保留在当前会话，核对后可发起新任务。",
);
expect(
  "已写入未知原因说明",
  queuePauseDetail({ status: "paused", kind: "followUp", inputPersisted: true }, true)
    === "已暂停且不会自动投递；输入已写入会话，请核对后决定是否撤回。",
);
expect(
  "未知原因默认说明",
  queuePauseDetail({ status: "paused", kind: "followUp" }, true)
    === "已暂停且不会自动投递；当前不支持直接重新排队，请核对后决定是否撤回或作为新消息提交。",
);
expect(
  "去重非 followUp 走原因文案",
  queuePauseDetail({ status: "paused", kind: "steering", deduplicated: true }, false)
    === "转向消息只对原回合有效，已暂停且不会自动投递；请撤回，或作为新消息提交。",
);

console.log(`PASS ${passed}`);
"""

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
        'if (item.failureCode === "TURN_START_FAILED") {',
        "if (item.inputPersisted === true)",
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


def _rewrite_status(source: str) -> str:
    rewritten = source.replace(
        'import type { QueueItem } from "@boss-harness/protocol";',
        "type QueueItem = {\n"
        '  status: "queued" | "delivering" | "delivered" | "paused" | "cancelled";\n'
        "  failureCode?: string;\n"
        "  pausedReason?: string;\n"
        "  inputPersisted?: boolean;\n"
        "  deduplicated?: boolean;\n"
        "  kind?: string;\n"
        "};",
    )
    rewritten = rewritten.replace(
        'import { queuePauseReasonText } from "./queueRetry";',
        'import { queuePauseReasonText } from "./queueRetry.ts";',
    )
    if "@boss-harness/protocol" in rewritten or 'from "./queueRetry"' in rewritten:
        raise ValueError(f"{STATUS} 的导入结构已变化，需要更新改写")
    return rewritten


def _rewrite_retry(source: str) -> str:
    rewritten = source.replace(
        'import type { QueueItem } from "@boss-harness/protocol";',
        "type QueueItem = {\n"
        '  status: "queued" | "delivering" | "delivered" | "paused" | "cancelled";\n'
        "  failureCode?: string;\n"
        "  pausedReason?: string;\n"
        "  inputPersisted?: boolean;\n"
        "  deduplicated?: boolean;\n"
        "  kind?: string;\n"
        "};",
    )
    if "@boss-harness/protocol" in rewritten:
        raise ValueError(f"{RETRY} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
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


def _check_behaviors() -> int:
    status = _read(STATUS)
    retry = _read(RETRY)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "queueRetry.ts").write_text(_rewrite_retry(retry), encoding="utf-8")
        (folder / "queueStatus.ts").write_text(_rewrite_status(status), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("队列状态行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"队列状态行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_status.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_status.py")
    if "共 44 项结构、29 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_status.py 检查 43 项结构、27 项行为")
    return 2


def check_queue_status() -> tuple[int, int]:
    source = _read(STATUS)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_status()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"队列状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列状态一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
