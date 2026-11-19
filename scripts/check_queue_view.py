#!/usr/bin/env python3
"""核对队列读取投影的上限、优先级与字段白名单。

queue_view.py 决定 thread/read、thread/resume（含快照）与 queue/list 的读取
体积：待处理项最多 200、已终结窗口 50、正文预览 600 字符，并暂停优先。上限、
白名单或分类计数来源被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/queue_view.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

CONSTANT_FRAGMENTS = (
    # 数值常量按整行锚定：200 改成 2000 之类的后缀扩展不能因前缀相同而通过。
    "MAX_QUEUE_VIEW_ITEMS = 200\n",
    "MAX_QUEUE_VIEW_TERMINAL_ITEMS = 50\n",
    "MAX_QUEUE_VIEW_INPUT_CHARS = 600\n",
    "MAX_QUEUE_SKILL_IDS = 10\n",
    "_MAX_QUEUE_ID_CHARS = 200\n",
    "_MAX_QUEUE_VIEW_STRING_CHARS = 200\n",
    "_MAX_SAFE_INTEGER = 2 ** 53 - 1\n",
    'QUEUE_KINDS = frozenset({"steering", "followUp"})\n',
    '_QUEUE_PAUSE_REASONS = frozenset({"COMPACTION_FAILED", "THREAD_ARCHIVED", "TURN_NOT_COMPLETED"})\n',
    "_QUEUE_VIEW_FIELDS = frozenset({",
    # 白名单必须逐个声明：整份透传会让未知字段进入响应并放大读取体积。
    '"id", "kind", "input", "status", "expectedTurnId", "clientUserMessageId",',
    '"skillIds", "autoCompaction", "failureCode", "pausedReason",',
    '"executionStarted", "turnId", "inputPersisted", "deduplicated", "inputTruncated",',
)
RECORD_FRAGMENTS = (
    'isinstance(value.get("kind"), str) and value["kind"] in QUEUE_KINDS',
    'isinstance(value.get("status"), str) and value["status"] in QUEUE_STATUSES',
    "0 < len(value[\"id\"]) <= _MAX_QUEUE_ID_CHARS",
    'json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")',
    # 孤立代理项先按 wire_text 约定降级；NaN 或过深嵌套仍按坏记录跳过。
    "except UnicodeEncodeError:",
    "value = wire_value(value)",
    "except (TypeError, ValueError, RecursionError):",
)
VIEW_FRAGMENTS = (
    "value = {key: record[key] for key in _QUEUE_VIEW_FIELDS if key in record}",
    "not isinstance(value[key], str) or len(value[key]) > _MAX_QUEUE_VIEW_STRING_CHARS):",
    'value["skillIds"] = list(dict.fromkeys(ids))',
    'if "failureCode" in value and value["failureCode"] != "TURN_START_FAILED":',
    "or paused_reason not in _QUEUE_PAUSE_REASONS",
    'if "executionStarted" in value and value["executionStarted"] is not False:',
    "if key in value and type(value[key]) is not bool:",
    "if type(item) is int and 0 <= item <= _MAX_SAFE_INTEGER:",
)
PROJECT_FRAGMENTS = (
    # 暂停项先占名额，排队 / 投递中项用剩余名额，最后才是已终结窗口。
    "kept_paused = paused[-MAX_QUEUE_VIEW_ITEMS:]",
    "pending_room = max(0, MAX_QUEUE_VIEW_ITEMS - len(kept_paused))",
    "terminal_room = max(0, min(MAX_QUEUE_VIEW_TERMINAL_ITEMS,",
    "kept_terminal = terminal[-terminal_room:] if terminal_room else []",
    'value["inputTruncated"] = True',
    '"truncated": len(visible) < total,',
    "active = max(0, min(active, total))",
    # 调用方传入的持久分类不能改由有界子集重算，否则截断时计数偏小。
    'status_counts = {"queued": counts["queued"], "delivering": counts["delivering"],',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "待处理项单次最多 200 项，名额允许时另返回最近 50 个已终结项"),
    (TECHNICAL_REFERENCE, "正文预览截断为 600 字符并标 `inputTruncated`"),
    (USER_GUIDE, "待处理项单次最多 200 项"),
    (USER_GUIDE, "正文预览最多 600 字符并标注截断"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_queue_view() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(RECORD_FRAGMENTS, module, MODULE)
    checked += _expect(VIEW_FRAGMENTS, module, MODULE)
    checked += _expect(PROJECT_FRAGMENTS, module, MODULE)
    checked += _ordered(
        (
            "kept_paused = paused[-MAX_QUEUE_VIEW_ITEMS:]",
            "kept_pending = pending[-pending_room:] if pending_room else []",
            "kept_terminal = terminal[-terminal_room:] if terminal_room else []",
        ),
        module,
        MODULE,
    )
    # 投影只能按白名单逐字段取值；整份记录透传会把未知字段带进响应。
    if "dict(record)" in module or "**record" in module:
        raise ValueError(f"{MODULE} 不能整份透传持久记录")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_queue_view()
    except ValueError as error:
        print(f"队列读取投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列读取投影一致：{checked} 项上限、白名单与截断防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
