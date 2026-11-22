#!/usr/bin/env python3
"""核对队列读取投影的上限、优先级与字段白名单。

queue_view.py 决定 thread/read、thread/resume（含快照）与 queue/list 的读取
体积：待处理项最多 200、已终结窗口 50、正文预览 600 字符，并暂停优先。检查固定
源码结构，并用临时合成记录执行跳过、字段收敛与配额场景。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/queue_view.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.queue_view import (  # noqa: E402
    project_queue,
    queue_record,
    queue_view_record,
)

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"队列读取投影行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _record(**overrides) -> dict:
    record = {"id": "q1", "kind": "steering", "status": "queued", "input": "消息"}
    record.update(overrides)
    return record


def _behavior_checks() -> int:
    record = _record()
    checked = _expect_value(queue_record(record), record, "合法记录")
    checked += _expect_value(queue_record(_record(kind="other")), None, "未知 kind")
    checked += _expect_value(queue_record({"id": "q1", "status": "queued", "input": "x"}), None, "缺少 kind")
    checked += _expect_value(queue_record(_record(status="other")), None, "未知状态")
    checked += _expect_value(queue_record(_record(id="a" * 200)) is not None, True, "id 上限接受")
    checked += _expect_value(queue_record(_record(id="a" * 201)), None, "id 超限")
    checked += _expect_value(queue_record(_record(input=5)), None, "输入非字符串")
    surrogate = queue_record(_record(input="甲\ud800乙"))
    checked += _expect_value(surrogate["input"], "甲�乙", "代理项降级")
    checked += _expect_value(queue_record(_record(extra=float("nan"))), None, "NaN 记录跳过")

    view = queue_view_record(queue_record({**_record(), "secret": "x", "turnId": "t1"}))
    checked += _expect_value(("secret" in view, view.get("turnId")), (False, "t1"), "白名单")
    checked += _expect_value(
        queue_view_record(_record(expectedTurnId=None)).get("expectedTurnId"), None, "可选空值保留"
    )
    checked += _expect_value(
        "expectedTurnId" in queue_view_record(_record(expectedTurnId=5)), False, "可选非字符串"
    )
    checked += _expect_value(
        "expectedTurnId" in queue_view_record(_record(expectedTurnId="a" * 201)), False, "可选超长"
    )
    checked += _expect_value("turnId" in queue_view_record(_record(turnId="a" * 201)), False, "turnId 超长")
    checked += _expect_value(
        queue_view_record(_record(skillIds=["a", "b", "a"]))["skillIds"], ["a", "b"], "技能去重"
    )
    checked += _expect_value(
        "skillIds" in queue_view_record(_record(skillIds=[f"s{index}" for index in range(11)])),
        False, "技能超限",
    )
    checked += _expect_value("skillIds" in queue_view_record(_record(skillIds="a")), False, "技能非列表")
    checked += _expect_value(
        "skillIds" in queue_view_record(_record(skillIds=["a", 5])), False, "技能非字符串项"
    )
    checked += _expect_value(
        queue_view_record(_record(autoCompaction={
            "enabled": True, "triggerPercent": 70, "keepRecentTokens": -1, "extra": 1,
        }))["autoCompaction"],
        {"enabled": True, "triggerPercent": 70}, "自动压缩清理",
    )
    checked += _expect_value(
        "autoCompaction" in queue_view_record(_record(autoCompaction="x")), False, "自动压缩非字典"
    )
    checked += _expect_value(
        queue_view_record(_record(autoCompaction={}))["autoCompaction"], {}, "自动压缩空字典"
    )
    checked += _expect_value(
        queue_view_record(_record(failureCode="TURN_START_FAILED"))["failureCode"],
        "TURN_START_FAILED", "失败码保留",
    )
    checked += _expect_value(
        "failureCode" in queue_view_record(_record(failureCode="OTHER")), False, "失败码丢弃"
    )
    checked += _expect_value(
        queue_view_record(_record(status="paused", pausedReason="THREAD_ARCHIVED"))["pausedReason"],
        "THREAD_ARCHIVED", "暂停来源保留",
    )
    checked += _expect_value(
        "pausedReason" in queue_view_record(_record(pausedReason="THREAD_ARCHIVED")), False, "非暂停来源丢弃"
    )
    checked += _expect_value(
        "pausedReason" in queue_view_record(_record(status="paused", pausedReason="OTHER")),
        False, "未知暂停来源丢弃",
    )
    checked += _expect_value(
        queue_view_record(_record(executionStarted=False)).get("executionStarted"), False, "执行标志保留"
    )
    checked += _expect_value(
        "executionStarted" in queue_view_record(_record(executionStarted=True)), False, "执行标志丢弃"
    )
    checked += _expect_value(
        queue_view_record(_record(inputPersisted=True, deduplicated=1, inputTruncated="yes")),
        {**queue_view_record(_record()), "inputPersisted": True}, "标志类型收敛",
    )

    truncated = project_queue([_record(input="x" * 601), _record(id="q2", input="x" * 600)])
    checked += _expect_value(
        (len(truncated["items"][0]["input"]), truncated["items"][0]["inputTruncated"]),
        (600, True), "输入截断",
    )
    checked += _expect_value(truncated["items"][1].get("inputTruncated"), None, "恰好上限不标截断")

    paused_items = [_record(id=f"p{index}", status="paused") for index in range(10)]
    pending_items = [_record(id=f"d{index}") for index in range(200)]
    prioritized = project_queue(pending_items + paused_items)
    statuses = [item["status"] for item in prioritized["items"]]
    checked += _expect_value(
        (len(prioritized["items"]), statuses.count("paused"), statuses.count("queued"),
         prioritized["activeItems"], prioritized["totalItems"], prioritized["truncated"]),
        (200, 10, 190, 210, 210, True), "暂停优先",
    )
    kept_ids = {item["id"] for item in prioritized["items"]}
    checked += _expect_value(
        ("d0" in kept_ids, "d9" in kept_ids, "d10" in kept_ids), (False, False, True), "暂停占位"
    )

    terminal = project_queue([_record(id=f"t{index}", status="delivered") for index in range(60)])
    checked += _expect_value(
        (len(terminal["items"]), terminal["items"][0]["id"], terminal["truncated"]),
        (50, "t10", True), "终结窗口",
    )
    filled = project_queue(
        [_record(id=f"d{index}") for index in range(200)]
        + [_record(id=f"t{index}", status="delivered") for index in range(5)]
    )
    checked += _expect_value(
        (len(filled["items"]), any(item["status"] == "delivered" for item in filled["items"])),
        (200, False), "终结名额挤占",
    )
    squeezed = project_queue(
        [_record(id=f"d{index}") for index in range(199)]
        + [_record(id=f"t{index}", status="delivered") for index in range(50)]
    )
    checked += _expect_value(
        [item["id"] for item in squeezed["items"] if item["status"] == "delivered"],
        ["t49"], "终结剩余名额",
    )

    mixed = project_queue([_record(), {"id": 1}, _record(id="q9", kind="other")])
    checked += _expect_value(
        (mixed["totalItems"], mixed["activeItems"], mixed["counts"], len(mixed["items"])),
        (1, 1, {"queued": 1, "delivering": 0, "paused": 0}, 1), "坏记录跳过",
    )
    explicit = project_queue(
        [_record()], total_items=1_000, active_items=2_000,
        counts={"queued": 900, "delivering": 50, "paused": 50},
    )
    checked += _expect_value(
        (explicit["totalItems"], explicit["activeItems"], explicit["counts"], explicit["truncated"]),
        (1_000, 1_000, {"queued": 900, "delivering": 50, "paused": 50}, True), "显式总数与计数",
    )
    classified = project_queue([
        _record(), _record(id="q2"), _record(id="q3", status="delivering"),
        _record(id="q4", status="paused"), _record(id="q5", status="cancelled"),
    ])
    checked += _expect_value(
        (classified["counts"], classified["activeItems"], classified["totalItems"],
         classified["truncated"]),
        ({"queued": 2, "delivering": 1, "paused": 1}, 4, 5, False), "默认分类",
    )
    ordered = project_queue([_record(id="a"), _record(id="b", status="paused"), _record(id="c")])
    checked += _expect_value(
        [item["id"] for item in ordered["items"]], ["a", "b", "c"], "顺序保留"
    )
    return checked


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
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"队列读取投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列读取投影一致：{checked} 项上限、白名单与截断防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
