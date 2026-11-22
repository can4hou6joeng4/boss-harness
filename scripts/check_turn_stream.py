#!/usr/bin/env python3
"""核对回合循环与流式事件收尾边界。

`agent.py` 的 `run()` 与 `_stream_round()` 决定一个回合如何消费模型流、
何时重试上下文恢复、如何持久化工具批次与终态。这里固定回合状态词汇、
请求预算与偏移校验、工具批次上限先于长度截断、续接签名失败与截断都
不执行工具、重试事件成对且早于回合终态、输出预算与用量条目的资格判定、
错误与中断的归一化，以及摘要与模型结果的有界输出。行为检查直接调用
`summarize_result` 与 `tool_source`，核对摘要拼写、截断、脱敏与来源字段。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/agent.py"

CONSTANT_FRAGMENTS = (
    "MAX_TOOL_ROUNDS = DEFAULT_MAX_MODEL_REQUESTS",
    "DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300.0",
    'N_TURN_STARTED = "turn/started"',
    'N_AGENT_MESSAGE_DELTA = "agentMessage/delta"',
    'N_AGENT_THINKING_DELTA = "agentThinking/delta"',
    'N_MODEL_RETRY_STARTED = "model/retryStarted"',
    'N_MODEL_RETRY_ENDED = "model/retryEnded"',
    'N_ITEM_STARTED = "item/started"',
    'N_ITEM_COMPLETED = "item/completed"',
    'N_TOOL_CALL_STARTED = "toolCall/started"',
    'N_TOOL_CALL_EXECUTING = "toolCall/executing"',
    'N_TOOL_CALL_COMPLETED = "toolCall/completed"',
    'N_APPROVAL_REQUESTED = "approval/requested"',
    'N_THREAD_UPDATED = "thread/updated"',
    'N_SESSION_ERROR = "session/error"',
)
RUN_FRAGMENTS = (
    "max_model_requests = model_request_limit(self.max_model_requests)",
    "recovery_budget = ModelRecoveryBudget()",
    "loop_guard = LoopGuard()",
    'if type(self.request_offset) is not int or not 0 <= self.request_offset <= max_model_requests:\n                raise ValueError("模型续接请求偏移超出配置上限")',
    "for _round in range(self.request_offset, max_model_requests):",
    'if staged[0]:\n                        loop_guard.reset()',
    "if self.context_check is not None:\n                    self.context_check(messages, self.system_prompt)",
    "recovery_budget=recovery_budget,",
    'code": "CONTEXT_BUDGET_EXCEEDED"',
    'purpose="turn", request_index=_round, cancel_event=self._cancel,',
    "if self.request_preparer is not None:\n                    for commit in commits:\n                        commit()",
    "if len(calls) > MAX_TOOL_BATCH_CALLS:",
    'code": "TOOL_BATCH_LIMIT"',
    'message = "Anthropic 工具续接签名超过内核保存预算；本响应中的工具未执行。"',
    'code": "PROVIDER_CONTINUATION_TOO_LARGE"',
    'code = "MODEL_OUTPUT_TRUNCATED"',
    "请检查请求并调整输出上限后，明确发起新回合；不会自动重试。",
    "if self.stage_steering is not None and _round + 1 < max_model_requests:",
    "self.sessions.record_tool_batch(\n                    thread_id, self.turn_id, tool_batch_id, [call.id for call in calls], \"started\",",
    "except _ParallelUnavailable:",
    "results = []",
    "不要自动重试。",
    "if len(results) == len(calls):",
    "recovery_budget.consume_retry(self._cancel)",
    "（共享模型恢复次数已用尽，未启动自动上下文恢复）",
    '"outputObserved": self.last_stream_output_observed',
    "details[\"errorInfo\"] = self.last_stream_error.event_payload()",
)
STREAM_FRAGMENTS = (
    "self.last_stream_error = None",
    "self.last_stream_recoverable = False",
    "self.last_stream_output_observed = False",
    "def ensure_entry() -> Entry:",
    'self.notify(N_ITEM_STARTED, {"threadId": thread_id, "itemId": entry.id, "kind": "agentMessage"})',
    "if retry_pending is None:\n                return",
    'payload = {"threadId": thread_id, "turnId": self.turn_id, "attempt": attempt,',
    'payload["reason"] = "aborted" if reason == "aborted" else "error"',
    "if event.type == \"retry_start\":",
    'if event.type.startswith(("text_", "thinking_", "toolcall_")):',
    'output_budget.account(("thinking", event.content_index), event.delta)',
    'output_budget.account(("text", event.content_index), event.delta)',
    'output_budget.reconcile(("thinking", event.content_index), event.text)',
    'output_budget.reconcile(("text", event.content_index), event.text)',
    "output_budget.reconcile_response(final_parts)",
    "output_observed = output_observed or bool(assistant and assistant.blocks)",
    "error = self.safe_error(event.error or \"未知错误\")",
    "if isinstance(info, ModelErrorInfo) and info.provider == self.config.provider:",
    "error = f\"{error}（传输诊断：{diagnostic}）\"",
    "if self.cancelled():\n                interrupted = True\n            else:\n                error = self.safe_error(exc)",
    "close = getattr(stream, \"close\", None)",
    "end_retry(retry_pending, \"aborted\" if stopped else \"error\", \"\" if stopped else (error or \"\"))",
    "interrupted = interrupted or self.cancelled() or (assistant is not None and assistant.stop_reason == \"aborted\")",
    'error = "模型流未返回完成事件，请重试"',
    'error = "模型返回失败状态"',
    'self.last_stream_error.code == "CONTEXT_OVERFLOW")',
    '"outputObserved": output_observed, "contextRecoveryEligible": self.last_stream_recoverable',
    'and assistant.stop_reason not in {"aborted", "error"}',
    'usage_entry["messageCount"] = len(request.messages)',
    '"status": "failed" if interrupted or error or truncated else "completed",',
    'payload["toolBatchId"] = tool_batch_id',
    'self.notify(N_ITEM_COMPLETED, {"threadId": thread_id, "itemId": entry.id, **payload})',
)
SUMMARY_FRAGMENTS = (
    "def summarize_result(result: ToolResult, limit: int = 4000) -> str:",
    'body = json.dumps(result.data, ensure_ascii=False)',
    'page = "" if result.pagination is None else " pagination=" + json.dumps(result.pagination, ensure_ascii=False)',
    'return f"ok=true command={result.command}{page} data={body}"[:limit]',
    'code = (result.error or {}).get("code", "UNKNOWN")',
    'return redact_secrets(f"ok=false command={result.command} code={code} message={message} recovery={recovery}")[:limit]',
    "def model_result(result: ToolResult, *, source: dict | None = None, item_id: str | None = None,",
    "max_bytes: int = DEFAULT_MODEL_TOOL_RESULT_BYTES,",
    "return model_result_content(payload, item_id, source=source, max_bytes=max_bytes,",
    "def tool_source(thread_id: str, entry: Entry, name: str) -> dict:",
    '"queriedAt": entry.timestamp}',
)


sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.agent import summarize_result, tool_source  # noqa: E402
from boss_harness.toolkit import ToolResult  # noqa: E402


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"回合流行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


class _Unserializable:
    def __str__(self) -> str:
        return "weird"


class _Entry:
    id = "item-1"
    timestamp = "2026-11-23T00:00:00Z"


def _behavior_checks() -> int:
    checked = 0
    # 成功结果：分页信息位于数据之前，避免截断页掩盖分页事实。
    checked += _expect_value(
        summarize_result(ToolResult(ok=True, command="search 北京", data={"rows": [1]})),
        'ok=true command=search 北京 data={"rows": [1]}', "成功结果拼写")
    paged = summarize_result(ToolResult(ok=True, command="search 北京", data={"rows": [1]},
                                        pagination={"page": 2}))
    checked += _expect_value(
        paged,
        'ok=true command=search 北京 pagination={"page": 2} data={"rows": [1]}', "分页位置")
    # 结果按插入顺序输出原样非 ASCII，不可序列化数据降级为文本。
    checked += _expect_value(
        summarize_result(ToolResult(ok=True, command="c", data="中文")),
        'ok=true command=c data="中文"', "非 ASCII 数据")
    checked += _expect_value(
        summarize_result(ToolResult(ok=True, command="c", data=_Unserializable())),
        'ok=true command=c data=weird', "不可序列化数据")
    # 成功与失败都受 limit 约束。
    checked += _expect_value(
        summarize_result(ToolResult(ok=True, command="search 北京", data={"rows": [1]}), limit=20),
        'ok=true command=sear', "成功结果截断")
    # 失败结果：缺省字段与脱敏。
    checked += _expect_value(
        summarize_result(ToolResult(ok=False, command="greet")),
        "ok=false command=greet code=UNKNOWN message= recovery=", "错误字段缺省")
    checked += _expect_value(
        summarize_result(ToolResult(ok=False, command="greet", error={
            "code": "RISK", "message": "被限制", "recovery_action": "稍后重试"})),
        "ok=false command=greet code=RISK message=被限制 recovery=稍后重试", "错误字段拼写")
    checked += _expect_value(
        summarize_result(ToolResult(ok=False, command="greet", error={
            "code": "X", "message": "Authorization: Bearer abcdef123456"})),
        "ok=false command=greet code=X message=Authorization: Bearer <redacted> recovery=",
        "凭据脱敏")
    checked += _expect_value(
        summarize_result(ToolResult(ok=False, command="greet", error={
            "code": "RISK", "message": "被限制", "recovery_action": "稍后重试"}), limit=10),
        "ok=false c", "错误结果截断")
    # 来源字段固定形状，不随条目其他字段变化。
    checked += _expect_value(
        tool_source("thread-1", _Entry(), "boss_search"),
        {"ref": "tool:thread-1:item-1", "tool": "boss_search",
         "queriedAt": "2026-11-23T00:00:00Z"}, "工具来源")
    return checked


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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_turn_stream() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, RUN_FRAGMENTS, STREAM_FRAGMENTS, SUMMARY_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 批次上限必须先于长度截断与续接处理。
    checked += _ordered(
        (
            "if len(calls) > MAX_TOOL_BATCH_CALLS:",
            'if calls and self.config.provider == "anthropic":',
            'if assistant.stop_reason == "length":',
        ),
        module,
        MODULE,
    )
    # 反向断言：不得把未确认结果标成完成、不得让截断响应执行工具、不得回显原始异常。
    if '"status": "completed" if interrupted' in module:
        raise ValueError(f"{MODULE} 的终态必须在中断 / 错误 / 截断时为 failed")
    if "redact_secrets(str(exc))" in module:
        raise ValueError(f"{MODULE} 的错误文本必须经 safe_error 收敛")
    if "do_not_retry" in module:
        raise ValueError(f"{MODULE} 不得引入未定义的恢复标记")
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_turn_stream()
    except ValueError as error:
        print(f"回合循环核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合循环一致：{checked} 项回合、流式、终态防护与结果摘要校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
