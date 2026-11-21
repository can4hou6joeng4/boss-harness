#!/usr/bin/env python3
"""核对队列计数的归并规则与列表元数据口径。

`_queue_status_counts` 按队列项 id 归并最新状态，只统计 `queued` / `delivering` /
`paused` 三个活动状态；`_index_thread` 把三项求和写入 `queueActiveItems`，并且只在
非零时写入 `queueCounts`、为零时清除。侧边栏角标与会话列表的「待你处理」都依赖
这两个字段，这里固定归并、过滤与元数据口径，避免重构后角标与队列面板对不上。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 归并顺序：只读 queue 条目 → 结构校验 → 按 id 覆盖为最新状态 → 三个计数键 →
# 只统计活动状态 → 累加。
COUNT_ORDER = (
    "def _queue_status_counts(entries: list[dict]) -> dict[str, int]:",
    'if entry.get("type") != "queue":',
    "record = queue_record(entry.get(\"payload\"))",
    "if record is not None:",
    'statuses[record["id"]] = record["status"]',
    'counts = {"queued": 0, "delivering": 0, "paused": 0}',
    "for status in statuses.values():",
    "if status in ACTIVE_QUEUE_STATUSES:",
    "counts[status] += 1",
    "return counts",
)
# 列表元数据：求和 → 非零写入 → 零值清除。
METADATA_ORDER = (
    "queue_counts = self._queue_status_counts(entries)",
    'metadata["queueActiveItems"] = sum(queue_counts.values())',
    'if metadata["queueActiveItems"]:',
    'metadata["queueCounts"] = queue_counts',
    'metadata.pop("queueCounts", None)',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_queue_counts() -> int:
    source = _read(SESSION)
    start = source.index("def _queue_status_counts(")
    end = source.find("\n    def ", start + 1)
    counts = source[start:] if end < 0 else source[start:end]
    checked = _ordered(COUNT_ORDER, counts, SESSION)
    checked += _ordered(METADATA_ORDER, source, SESSION)
    # 最新状态必须覆盖旧值，不能保留首个状态。
    if "statuses.setdefault(" in counts:
        raise ValueError(f"{SESSION} 的队列计数必须按 id 归并最新状态")
    checked += 1
    # 损坏记录不得覆盖有效状态：必须先经 queue_record 过滤。
    if counts.count('if record is not None:') != 1:
        raise ValueError(f"{SESSION} 的损坏队列记录必须跳过")
    checked += 1
    # 计数键必须恰好三个活动状态。
    if 'counts = {"queued": 0, "delivering": 0, "paused": 0}' not in counts:
        raise ValueError(f"{SESSION} 的队列计数键必须恰好是 queued / delivering / paused")
    checked += 1
    # 元数据只由三项求和，零值必须清除旧字段。
    if source.count('metadata["queueActiveItems"] = sum(queue_counts.values())') != 1:
        raise ValueError(f"{SESSION} 的 queueActiveItems 必须由三项计数求和")
    checked += 1
    if source.count('metadata.pop("queueCounts", None)') != 1:
        raise ValueError(f"{SESSION} 的零队列必须清除 queueCounts")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_queue_counts()
    except ValueError as error:
        print(f"队列计数核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列计数一致：{checked} 项归并、活动状态与列表元数据校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
