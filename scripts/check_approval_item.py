#!/usr/bin/env python3
"""核对审批条目的展示、归属与状态校验口径。

`_valid_approval_item` 决定一条 toolCall 记录能否进入审批索引、`approval/list`
与持久计数：kind 必须是 toolCall，approval 必须是对象，decision 只能是
approve / deny / expired，approvalId 必须是 32 位小写十六进制事件 id，
turnId 必须符合标识符格式，展示用工具名与条目 id 去空白后非空且不超过
200 字符，params 必须与 toolArguments 完全一致，status / executionState
组合随 decision 收紧，deadline 必须是有限正数，description 不超过 1000
字符，paramsDigest 必须与参数摘要一致。这里按源码顺序固定这些边界，避免
重构放宽后铃铛总数与通知面板对不上，或让结构不完整的审批串进列表。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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
    return checked


def main() -> int:
    try:
        checked = check_approval_item()
    except ValueError as error:
        print(f"审批条目校验失败，{error}", file=sys.stderr)
        return 2
    print(f"审批条目一致：{checked} 项展示、状态与参数摘要校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
