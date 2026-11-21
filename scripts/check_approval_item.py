#!/usr/bin/env python3
"""核对审批条目的展示、归属与状态校验口径。

`_valid_approval_item` 决定一条 toolCall 记录能否进入审批索引、`approval/list`
与持久计数：kind 必须是 toolCall，approval 必须是对象，decision 只能是
approve / deny / expired，approvalId 必须是 32 位小写十六进制事件 id，
turnId 必须符合标识符格式，展示用工具名与条目 id 去空白后非空且不超过
200 字符，params 必须与 toolArguments 完全一致，status / executionState
组合随 decision 收紧，deadline 必须是有限正数，description 不超过 1000
字符，paramsDigest 必须与参数摘要一致。这里按源码顺序固定这些边界，避免
重构放宽后铃铛总数与通知面板对不上，或让结构不完整的审批串进列表，并构造
条目直接调用校验函数核对展示、状态与摘要边界。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore, approval_parameters_digest  # noqa: E402

# 校验顺序：读取审批与参数 → 展示字段去空白 → 结构、格式与一致性 → 状态组合
# 随 decision 收紧 → 截止时间 → 描述 → 参数摘要。
VALID_ORDER = (
    "def _valid_approval_item(item: dict, *, pending_only: bool) -> bool:",
    'approval = item.get("approval")',
    'arguments = item.get("toolArguments")',
    'decision = approval.get("decision") if isinstance(approval, dict) else None',
    'tool_name = approval.get("toolName") if isinstance(approval, dict) else None',
    'visible_name = tool_name.strip() if isinstance(tool_name, str) else ""',
    'item_id = item.get("id")',
    'visible_item_id = item_id.strip() if isinstance(item_id, str) else ""',
    'if (item.get("kind") != "toolCall" or not isinstance(approval, dict)',
    'decision not in {"approve", "deny", "expired"}',
    'not isinstance(approval.get("approvalId"), str)',
    'not _EVENT_ID.fullmatch(approval["approvalId"])',
    "or not visible_name",
    "or len(visible_name) > _APPROVAL_VIEW_FIELD_CHARS",
    "or not visible_item_id",
    "or len(visible_item_id) > _APPROVAL_VIEW_FIELD_CHARS",
    'or tool_name != item.get("toolName")',
    'or not isinstance(item.get("turnId"), str)',
    'or not _IDENTIFIER.fullmatch(item["turnId"])',
    'or type(arguments) is not dict or approval.get("params") != arguments):',
    'status, execution_state = item.get("status"), item.get("executionState")',
    "if not isinstance(status, str) or not isinstance(execution_state, str):",
    "if pending_only or decision is None:",
    'if status != "running" or execution_state != "pending_approval":',
    'elif decision == "approve":',
    'status not in {"running", "failed", "completed"}',
    '"approved", "executing", "completed", "failed", "not_executed", "outcome_unknown"',
    'elif decision == "deny":',
    'if status not in {"running", "failed"} or execution_state != "not_approved":',
    'elif status not in {"running", "failed"} or execution_state != "not_executed":',
    'deadline = approval.get("deadline")',
    "type(deadline) in {int, float} and math.isfinite(float(deadline))",
    "and deadline > 0)",
    "except (OverflowError, TypeError, ValueError):",
    "if not deadline_valid:",
    'description = approval.get("description")',
    "if not isinstance(description, str) or len(description) > 1_000:",
    "digest = approval_parameters_digest(arguments)",
    "except ValueError:",
    'return approval.get("paramsDigest") == digest',
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


def _expect_value(actual: bool, expected: bool, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"审批条目行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _item(**overrides) -> dict:
    arguments = overrides.pop("arguments", {"a": 1})
    try:
        digest = approval_parameters_digest(arguments)
    except ValueError:
        digest = "0" * 64
    approval = {
        "approvalId": "a" * 32,
        "toolName": "boss_hr_greet",
        "description": "需要你批准后才会执行",
        "params": arguments,
        "paramsDigest": digest,
        "consequential": True,
        "deadline": 1000.0,
        "decision": None,
    }
    approval.update(overrides.pop("approval", {}))
    item = {
        "id": "item-1",
        "kind": "toolCall",
        "toolName": "boss_hr_greet",
        "turnId": "turn-a",
        "toolArguments": arguments,
        "status": "running",
        "executionState": "pending_approval",
        "approval": approval,
    }
    item.update(overrides)
    return item


def _valid(item: dict, pending_only: bool = False) -> bool:
    return SessionStore._valid_approval_item(item, pending_only=pending_only)


def _behavior_checks() -> int:
    checked = _expect_value(_valid(_item()), True, "合法待审批")
    checked += _expect_value(_valid(_item(), pending_only=True), True, "待审批模式")
    checked += _expect_value(_valid(_item(kind="message")), False, "kind 限制")
    checked += _expect_value(
        _valid(_item(approval={"decision": 1})), False, "decision 类型")
    checked += _expect_value(
        _valid(_item(approval={"decision": "maybe"})), False, "decision 取值")
    checked += _expect_value(
        _valid(_item(approval={"approvalId": 123})), False, "approvalId 类型")
    checked += _expect_value(
        _valid(_item(approval={"approvalId": "a" * 31})), False, "approvalId 长度")
    checked += _expect_value(
        _valid(_item(approval={"approvalId": "A" * 32})), False, "approvalId 小写")
    checked += _expect_value(
        _valid(_item(approval={"approvalId": "g" * 32})), False,
        "approvalId 十六进制")
    checked += _expect_value(
        _valid(_item(approval={"toolName": "   "}, toolName="   ")), False,
        "工具名空白")
    checked += _expect_value(
        _valid(_item(approval={"toolName": "n" * 201}, toolName="n" * 201)), False,
        "工具名上限")
    checked += _expect_value(
        _valid(_item(approval={"toolName": "n" * 200}, toolName="n" * 200)), True,
        "工具名边界")
    checked += _expect_value(
        _valid(_item(approval={"toolName": " boss "}, toolName=" boss ")), True,
        "工具名去空白")
    checked += _expect_value(_valid(_item(id="   ")), False, "条目 id 空白")
    checked += _expect_value(_valid(_item(id="i" * 201)), False, "条目 id 上限")
    checked += _expect_value(_valid(_item(id=" item ")), True, "条目 id 去空白")
    checked += _expect_value(
        _valid(_item(toolName="boss_hr_greet_2")), False, "工具名一致")
    checked += _expect_value(_valid(_item(turnId="bad id!")), False, "回合号标识符")
    checked += _expect_value(_valid(_item(arguments=[1])), False, "参数类型")
    checked += _expect_value(
        _valid(_item(arguments={"a": 1}, approval={"params": {"a": 2}})), False,
        "参数一致")
    checked += _expect_value(_valid(_item(status=1)), False, "状态类型")
    checked += _expect_value(_valid(_item(executionState=1)), False, "执行态类型")
    checked += _expect_value(_valid(_item(status="completed")), False, "待审批状态")
    checked += _expect_value(
        _valid(_item(executionState="approved")), False, "待审批执行态")
    checked += _expect_value(
        _valid(_item(approval={"decision": "approve"}, status="completed",
                     executionState="completed"), pending_only=True), False,
        "待审批模式收紧")
    checked += _expect_value(
        _valid(_item(approval={"decision": "approve"}, status="completed",
                     executionState="completed")), True, "批准完成")
    checked += _expect_value(
        _valid(_item(approval={"decision": "approve"}, status="failed",
                     executionState="outcome_unknown")), True, "批准结果未知")
    checked += _expect_value(
        _valid(_item(approval={"decision": "approve"},
                     executionState="not_approved")), False, "批准执行态")
    checked += _expect_value(
        _valid(_item(approval={"decision": "deny"}, status="failed",
                     executionState="not_approved")), True, "拒绝失败")
    checked += _expect_value(
        _valid(_item(approval={"decision": "deny"}, executionState="not_executed")),
        False, "拒绝执行态")
    checked += _expect_value(
        _valid(_item(approval={"decision": "expired"}, executionState="not_executed")),
        True, "过期未执行")
    checked += _expect_value(
        _valid(_item(approval={"decision": "expired"}, executionState="not_approved")),
        False, "过期执行态")
    for label, deadline in (
        ("截止时间为零", 0),
        ("截止时间为负", -1.0),
        ("截止时间为 NaN", float("nan")),
        ("截止时间为无穷", float("inf")),
        ("截止时间为字符串", "1000"),
        ("截止时间为布尔", True),
    ):
        checked += _expect_value(
            _valid(_item(approval={"deadline": deadline})), False, label)
    checked += _expect_value(
        _valid(_item(approval={"description": 1})), False, "描述类型")
    checked += _expect_value(
        _valid(_item(approval={"description": "d" * 1001})), False, "描述上限")
    checked += _expect_value(
        _valid(_item(approval={"description": "d" * 1000})), True, "描述边界")
    checked += _expect_value(
        _valid(_item(approval={"paramsDigest": "0" * 64})), False, "摘要不匹配")
    checked += _expect_value(
        _valid(_item(arguments={"v": float("nan")})), False, "参数不可规范化")
    return checked


def check_approval_item() -> int:
    source = _read(SESSION)
    start = source.index("def _valid_approval_item(")
    end = source.find("\n    def ", start + 1)
    valid = source[start:] if end < 0 else source[start:end]
    checked = _ordered(VALID_ORDER, valid, SESSION)
    # 九处拒绝分支：结构、状态类型、四类状态组合、截止时间、描述与摘要。
    if valid.count("return False") != 9:
        raise ValueError(f"{SESSION} 的审批校验必须保留九处拒绝分支")
    checked += 1
    # 展示字段上限只作用于去空白后的工具名与条目 id。
    if valid.count("_APPROVAL_VIEW_FIELD_CHARS") != 2:
        raise ValueError(f"{SESSION} 的展示字段上限必须同时覆盖工具名与条目 id")
    checked += 1
    # 参数必须来自 toolArguments，且只与 params 比对一次、只计算一次摘要。
    if valid.count('approval.get("params")') != 1:
        raise ValueError(f"{SESSION} 的审批参数必须与 toolArguments 比对一次")
    checked += 1
    if valid.count("paramsDigest") != 1:
        raise ValueError(f"{SESSION} 的审批必须只比对一次参数摘要")
    checked += 1
    # dict 子类也不能持有审批参数，必须用精确类型判断。
    if "isinstance(arguments, dict)" in valid:
        raise ValueError(f"{SESSION} 的审批参数必须用精确 dict 类型判断")
    checked += 1
    # 截止时间必须是有限正数，零值不能算有效。
    if valid.count("math.isfinite(float(deadline))") != 1:
        raise ValueError(f"{SESSION} 的审批截止时间必须校验有限性")
    checked += 1
    if "deadline >= 0" in valid:
        raise ValueError(f"{SESSION} 的审批截止时间必须严格大于零")
    checked += 1
    # 调用点必须以关键字传入 pending_only，避免布尔位置参数被交换。
    if source.count("self._valid_approval_item(item, pending_only=") != 5:
        raise ValueError(f"{SESSION} 的审批校验缺少关键字调用点")
    checked += 1
    if source.count("self._valid_approval_item(") != 5:
        raise ValueError(f"{SESSION} 的审批校验存在位置参数调用")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_approval_item()
    except ValueError as error:
        print(f"审批条目校验失败，{error}", file=sys.stderr)
        return 2
    print(f"审批条目一致：{checked} 项展示、状态、参数摘要与行为校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
