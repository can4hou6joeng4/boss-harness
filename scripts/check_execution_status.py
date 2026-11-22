#!/usr/bin/env python3
"""核对工具执行状态标签的只读派生边界，成功时输出核对项数量。

`tool_execution_status` 为上下文摘要与会话导出派生执行标签：状态优先取
`executionState`，空串时回退 `status`；非字符串、空串与超过 40 字符的损坏值
一律置 None 并标注「状态不明，不得视为已执行」。写工具 `boss_hr_greet` 或带
`approval` 字段的条目按外部写操作处理，`outcome_unknown` 在写操作上使用
「结果未知，需核对」。`executed` 只有完成态为真、拒绝与未执行态为假，其余
为未知。`_annotate_tool_execution` 只对工具调用派生新对象，不写回输入。
本脚本扫描源码并直接调用这两个函数，不读写会话、不启动子进程、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = "harness/src/boss_harness/context.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.context import (  # noqa: E402
    _EXECUTION_LABELS,
    _WRITE_TOOLS,
    _annotate_tool_execution,
    tool_execution_status,
)

LABELS = {
    "completed": "已执行成功",
    "failed": "执行失败",
    "not_approved": "用户拒绝，未执行",
    "not_executed": "未执行",
    "outcome_unknown": "已中断或结果未知，需核对",
    "running": "进行中（导出时尚未结束）",
}
UNKNOWN = "状态不明，不得视为已执行"
FRAGMENTS = (
    "def tool_execution_status(item: dict[str, Any]) -> dict[str, Any]:",
    'state = item.get("executionState") or item.get("status")',
    "if not isinstance(state, str) or not state or len(state) > 40:",
    "state = None",
    'write = _is_one_of(item.get("toolName"), _WRITE_TOOLS) or "approval" in item',
    'label = (_EXECUTION_LABELS.get(state, "状态不明，不得视为已执行")',
    'if write and state == "outcome_unknown":',
    'label = "结果未知，需核对"',
    'executed = (True if state == "completed" else',
    'return {"state": state, "label": label, "externalWrite": write, "executed": executed}',
    "def _annotate_tool_execution(item: dict[str, Any]) -> dict[str, Any]:",
    'if item.get("kind") != "toolCall":',
    "return item",
    'return {**item, "summaryExecutionStatus": tool_execution_status(item)}',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"工具执行状态行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _read_status(state: str | None, *, tool: str = "boss_list_jobs") -> dict:
    item = {"toolName": tool}
    if state is not None:
        item["status"] = state
    return tool_execution_status(item)


def _behavior_checks() -> int:
    checked = 0
    expected_executed = {
        "completed": True,
        "failed": None,
        "not_approved": False,
        "not_executed": False,
        "outcome_unknown": None,
        "running": None,
    }
    for state, label in LABELS.items():
        checked += _expect_value(
            _read_status(state),
            {"state": state, "label": label, "externalWrite": False,
             "executed": expected_executed[state]}, f"读工具 {state}")
    checked += _expect_value(
        _read_status("outcome_unknown", tool="boss_hr_greet"),
        {"state": "outcome_unknown", "label": "结果未知，需核对",
         "externalWrite": True, "executed": None}, "写工具未知结局")
    checked += _expect_value(
        _read_status("completed", tool="boss_hr_greet"),
        {"state": "completed", "label": "已执行成功", "externalWrite": True,
         "executed": True}, "写工具完成")
    checked += _expect_value(
        tool_execution_status({"toolName": "boss_list_jobs", "approval": {}}),
        {"state": None, "label": UNKNOWN, "externalWrite": True, "executed": None},
        "审批字段按写操作")
    for label, item in (
        ("状态缺失", {"toolName": "boss_list_jobs"}),
        ("状态为空串", {"toolName": "boss_list_jobs", "status": ""}),
        ("状态非字符串", {"toolName": "boss_list_jobs", "status": 3}),
        ("状态为列表", {"toolName": "boss_list_jobs", "status": ["completed"]}),
        ("状态超长", {"toolName": "boss_list_jobs", "status": "s" * 41}),
    ):
        checked += _expect_value(
            tool_execution_status(item),
            {"state": None, "label": UNKNOWN, "externalWrite": False, "executed": None},
            label)
    checked += _expect_value(
        _read_status("s" * 40),
        {"state": "s" * 40, "label": UNKNOWN, "externalWrite": False, "executed": None},
        "状态恰好 40 字符保留")
    checked += _expect_value(
        tool_execution_status({"toolName": "boss_list_jobs", "status": "failed",
                               "executionState": "completed"}),
        {"state": "completed", "label": "已执行成功", "externalWrite": False,
         "executed": True}, "执行态优先")
    checked += _expect_value(
        tool_execution_status({"toolName": "boss_list_jobs", "status": "failed",
                               "executionState": ""}),
        {"state": "failed", "label": "执行失败", "externalWrite": False, "executed": None},
        "执行态空串回退")
    checked += _expect_value(
        tool_execution_status({"toolName": ["boss_hr_greet"], "status": "outcome_unknown"}),
        {"state": "outcome_unknown", "label": "已中断或结果未知，需核对",
         "externalWrite": False, "executed": None}, "工具名非字符串")

    plain = {"kind": "message", "status": "completed"}
    checked += _expect_value(_annotate_tool_execution(plain) is plain, True,
                             "非工具调用原样返回")
    call = {"kind": "toolCall", "id": "call-x", "toolName": "boss_hr_greet",
            "status": "outcome_unknown"}
    annotated = _annotate_tool_execution(call)
    checked += _expect_value(
        annotated,
        {**call, "summaryExecutionStatus": {"state": "outcome_unknown",
                                            "label": "结果未知，需核对",
                                            "externalWrite": True, "executed": None}},
        "工具调用派生标注")
    checked += _expect_value("summaryExecutionStatus" in call, False, "不改写输入条目")
    return checked


def check_execution_status() -> int:
    source = _read(CONTEXT)
    checked = _expect(FRAGMENTS, source, CONTEXT)
    if _EXECUTION_LABELS != LABELS:
        raise ValueError(
            f"{CONTEXT} 的执行标签映射变化：期望 {LABELS!r}，实际 {_EXECUTION_LABELS!r}")
    checked += 1
    if _WRITE_TOOLS != frozenset({"boss_hr_greet"}):
        raise ValueError(f"{CONTEXT} 的写工具集合必须只有 boss_hr_greet")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_execution_status()
    except ValueError as error:
        print(f"工具执行状态边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具执行状态一致：{checked} 项标签、写操作与三态校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
