#!/usr/bin/env python3
"""核对模型请求策略的拒绝投影与脱敏边界。

策略拒绝必须与 provider 错误区分，拒绝原因不得把凭据或原文写入会话；投影
字段、脱敏与 model_error 记录被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/request_policy.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

PAYLOAD_FRAGMENTS = (
    "MAX_UNIT_PREVIEW_CHARS = 1_000",
    '("purpose", "provider", "model", "requestIndex", "threadId", "turnId", "jobId")',
    '"errorInfo": {"source": "request_policy", "code": self.code}',
    '"outputObserved": False',
    '"contextRecoveryEligible": False',
    '"requestRejected": True',
)
PREVIEW_FRAGMENTS = (
    '"userText": redact_secrets(text[:MAX_UNIT_PREVIEW_CHARS])',
    '"toolNames": tool_names[:64]',
    "for message in messages if isinstance(message, AssistantMessage)",
    "for message in messages if isinstance(message, ToolResultsMessage)",
)
TRANSFORM_FRAGMENTS = (
    "if len(units) < 2:",
    "offset = max(0, len(units) - MAX_CONTEXT_UNITS)",
    "if outcome is None or (cancel_event is not None and cancel_event.is_set()):",
    "dropped = set(outcome)",
    "return replace(request, messages=messages)",
)
IDENTITY_FRAGMENTS = (
    "request = replace(request, task_context=task)",
    "if hooks is None or (cancel_event is not None and cancel_event.is_set()):",
    'if task.purpose == "turn" and hooks.transforms_context:',
    "decision = hooks.before_request(context, cancel_event=cancel_event)",
    "if decision is not None and not decision.allow:",
)
RECORD_FRAGMENTS = (
    "if not error.recorded:",
    'sessions.append(thread_id, Entry(type="model_error", payload=error.payload()))',
    "error.recorded = True",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "`requestRejected=true` 区分策略拒绝"),
    (TECHNICAL_REFERENCE, "取消优先于拒绝"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_request_policy() -> int:
    module = _read(MODULE)
    checked = _expect(PAYLOAD_FRAGMENTS, module, MODULE)
    checked += _expect(PREVIEW_FRAGMENTS, module, MODULE)
    checked += _expect(TRANSFORM_FRAGMENTS, module, MODULE)
    checked += _expect(IDENTITY_FRAGMENTS, module, MODULE)
    checked += _expect(RECORD_FRAGMENTS, module, MODULE)
    # 两条拒绝路径都必须先脱敏再抛出；直接使用原始消息会让凭据进入会话。
    rejects = module.count("raise ModelRequestRejected(")
    redacted = module.count("redact_secrets(outcome.message") + module.count("redact_secrets(decision.message")
    if rejects != 2 or redacted != 2:
        raise ValueError(f"{MODULE} 的两处策略拒绝必须各自经过 redact_secrets")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_request_policy()
    except ValueError as error:
        print(f"请求策略核对失败，{error}", file=sys.stderr)
        return 2
    print(f"请求策略一致：{checked} 项投影、脱敏与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
