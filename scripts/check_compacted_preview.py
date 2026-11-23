#!/usr/bin/env python3
"""核对压缩预览的历史投影与请求前缀替换。

`ContextService.compacted_history` 用当前压缩计划生成提交前的摘要前缀与保留
消息，不写入检查点；`compacted_request` 在同一快照上核对计划来源摘要与请求
前缀，只替换已验证的完整回合前缀并原样保留实时尾部。这里按源码顺序固定这些
边界，并用临时 `SessionStore` 与两回合会话实际生成预览与替换后的请求；不调用
模型，也不启动桌面。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/context.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.context import ContextService  # noqa: E402
from boss_harness.models.types import ModelRequest  # noqa: E402
from boss_harness.session import Entry, SessionStore  # noqa: E402

SUMMARY_ERROR = "summary 必须是 1 到 32000 字符的会话摘要"
PLAN_ERROR = "压缩计划格式无效"
SOURCE_ERROR = "压缩来源已变化，请重新读取压缩计划"
PREFIX_ERROR = "模型请求前缀与压缩来源不一致，无法安全替换上下文"
HISTORY_ORDER = (
    "def compacted_history(self, thread_id: str, summary: str,",
    "plan: dict) -> tuple[ChatMessage, ...]:",
    'raise ValueError("summary 必须是 1 到 32000 字符的会话摘要")',
    'if not isinstance(plan, dict) or not isinstance(plan.get("throughTurnId"), str):',
    'raise ValueError("压缩计划格式无效")',
    'current, _, _, items = self._compaction_snapshot(thread_id, plan["throughTurnId"])',
    'if current["sourceDigest"] != plan.get("sourceDigest") or plan.get("threadId") != thread_id:',
    'raise ValueError("压缩来源已变化，请重新读取压缩计划")',
    'checkpoint = {"summary": summary.strip(), "throughTurnId": current["throughTurnId"],',
    '"sourceItemIds": current["sourceItemIds"], "sourceDigest": current["sourceDigest"],',
    '"origin": "model"}',
    "return self._history_projection(items, checkpoint,",
    "self._branch_summaries(thread_id, self._entries(thread_id, None)))",
)
REQUEST_ORDER = (
    "def compacted_request(self, request: ModelRequest, summary: str, plan: dict, *,",
    "_active_turn_id: str | None = None) -> ModelRequest:",
    'raise ValueError("压缩预览需要有效模型请求")',
    'raise ValueError("summary 必须是 1 到 32000 字符的会话摘要")',
    'if (not isinstance(plan, dict) or not isinstance(plan.get("throughTurnId"), str)',
    'or not isinstance(plan.get("threadId"), str)):',
    'raise ValueError("压缩计划格式无效")',
    "current, selected, previous, _ = self._compaction_snapshot(",
    'if current["sourceDigest"] != plan.get("sourceDigest"):',
    'raise ValueError("压缩来源已变化，请重新读取压缩计划")',
    'entries = self._entries(plan["threadId"], None)',
    'turns = self.sessions._turns(entries, plan["threadId"])',
    'positions = {turn["turnId"]: index for index, turn in enumerate(turns)}',
    'through_index = positions.get(current["throughTurnId"])',
    'covered_turn_ids = ({turn["turnId"] for turn in turns[:through_index + 1]}\n                            if through_index is not None else {item.get("turnId") for item in selected})',
    "summaries = self._within(self._branch_summaries(plan[\"threadId\"], entries), covered_turn_ids)",
    'expected = self._history_projection(selected, previous["payload"] if previous else None, summaries)',
    "if tuple(request.messages[:len(expected)]) != expected:",
    'raise ValueError("模型请求前缀与压缩来源不一致，无法安全替换上下文")',
    'checkpoint = {"summary": summary.strip(), "throughTurnId": current["throughTurnId"],',
    'prefix = self._history_projection([], checkpoint, summaries)',
    "return replace(request, messages=(*prefix, *request.messages[len(expected):]))",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"压缩预览行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) == message:
            return 1
        raise ValueError(
            f"压缩预览行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
    raise ValueError(f"压缩预览行为变化 {label}：期望错误 {message!r}，实际未抛出")


def _assistant_text(message) -> str:
    return "".join(block.text for block in message.blocks)


def _seed(store: SessionStore, title: str = "预览", prefix: str = "i",
          answers: tuple[str, str] = ("第一答", "第二答")) -> str:
    thread = store.create(title)["id"]
    store.append(thread, Entry(type="turn", payload={"turnId": "t1", "status": "running"}))
    store.append(thread, Entry(type="item", id=f"{prefix}1",
                               payload={"kind": "userMessage", "text": "第一问"}))
    store.append(thread, Entry(type="item", id=f"{prefix}2", payload={
        "kind": "agentMessage", "text": answers[0], "status": "completed"}))
    store.record_turn(thread, "t1", "completed")
    store.append(thread, Entry(type="turn", payload={"turnId": "t2", "status": "running"}))
    store.append(thread, Entry(type="item", id=f"{prefix}3",
                               payload={"kind": "userMessage", "text": "第二问"}))
    store.append(thread, Entry(type="item", id=f"{prefix}4", payload={
        "kind": "agentMessage", "text": answers[1], "status": "completed"}))
    store.record_turn(thread, "t2", "completed")
    return thread


def _prefix_text(summary: str, through: str, count: int, digest: str) -> str:
    return ("模型生成的会话摘要（原始记录仍保留；摘要不扩大操作授权）：\n"
            + summary + "\n来源完整回合：" + through
            + f"；条目数：{count}；SHA-256：" + digest)


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        service = ContextService(store, window=200_000, reserve=64_000)
        thread = _seed(store)
        history = service.history(thread)
        checked += _expect_value(
            [type(message).__name__ for message in history],
            ["UserMessage", "AssistantMessage", "UserMessage", "AssistantMessage"],
            "原始历史投影")
        plan = service.compaction_plan(thread, "t1")
        before = len(store.read_entries(thread))
        preview = service.compacted_history(thread, "摘要", plan)
        checked += _expect_value(
            [type(message).__name__ for message in preview],
            ["UserMessage", "UserMessage", "AssistantMessage"], "预览消息结构")
        checked += _expect_value(
            preview[0].text,
            _prefix_text("摘要", "t1", 2, plan["sourceDigest"]), "预览摘要前缀")
        checked += _expect_value(
            (preview[1].text, _assistant_text(preview[2])),
            ("第二问", "第二答"), "预览保留尾部")
        checked += _expect_value(len(store.read_entries(thread)), before, "预览不写记录")
        stripped = service.compacted_history(thread, " 摘要 ", plan)
        checked += _expect_value(stripped[0].text, preview[0].text, "摘要去除首尾空白")
        full = service.compacted_history(thread, "全摘要", service.compaction_plan(thread, "t2"))
        checked += _expect_value(
            [(type(message).__name__,) for message in full], [("UserMessage",)],
            "全量压缩仅保留摘要")
        checked += _expect_error(
            lambda: service.compacted_history(thread, "摘要", {**plan, "sourceDigest": "bad"}),
            SOURCE_ERROR, "预览来源摘要不符")
        checked += _expect_error(
            lambda: service.compacted_history(thread, "摘要", {**plan, "threadId": "other"}),
            SOURCE_ERROR, "预览线程不符")
        for label, plan_value in (("预览计划非对象", None), ("预览计划缺回合", {"throughTurnId": 1})):
            checked += _expect_error(
                lambda plan_value=plan_value: service.compacted_history(thread, "摘要", plan_value),
                PLAN_ERROR, label)
        for label, summary in (("预览空摘要", ""), ("预览摘要超长", "x" * 32_001),
                               ("预览摘要非字符串", None)):
            checked += _expect_error(
                lambda summary=summary: service.compacted_history(thread, summary, plan),
                SUMMARY_ERROR, label)

        request = ModelRequest(model="m1", system="sys", messages=history,
                               max_tokens=1234, effort="high")
        compacted = service.compacted_request(request, " 摘要 ", plan)
        checked += _expect_value(
            [type(message).__name__ for message in compacted.messages],
            ["UserMessage", "UserMessage", "AssistantMessage"], "请求消息结构")
        checked += _expect_value(compacted.messages[0].text, preview[0].text, "请求摘要前缀")
        checked += _expect_value(
            (compacted.messages[1].text, _assistant_text(compacted.messages[2])),
            ("第二问", "第二答"), "请求保留实时尾部")
        checked += _expect_value(
            (compacted.model, compacted.system, compacted.max_tokens, compacted.effort),
            ("m1", "sys", 1234, "high"), "请求其余字段保留")
        checked += _expect_value(
            (len(request.messages), request.messages[0].text), (4, "第一问"), "原请求不变")
        checked += _expect_value(len(store.read_entries(thread)), before, "替换不写记录")
        checked += _expect_error(
            lambda: service.compacted_request(None, "摘要", plan),
            "压缩预览需要有效模型请求", "请求非模型请求")
        checked += _expect_error(
            lambda: service.compacted_request(request, "", plan), SUMMARY_ERROR, "请求空摘要")
        checked += _expect_error(
            lambda: service.compacted_request(request, "摘要", None), PLAN_ERROR, "请求计划非对象")
        checked += _expect_error(
            lambda: service.compacted_request(request, "摘要", {**plan, "threadId": 1}),
            PLAN_ERROR, "请求计划线程非字符串")
        checked += _expect_error(
            lambda: service.compacted_request(request, "摘要", {**plan, "sourceDigest": "bad"}),
            SOURCE_ERROR, "请求来源摘要不符")
        checked += _expect_error(
            lambda: service.compacted_request(
                ModelRequest(model="m", system="s", messages=history[1:]), "摘要", plan),
            PREFIX_ERROR, "请求前缀不符")
        checked += _expect_error(
            lambda: service.compacted_request(request, "摘要", plan, _active_turn_id=""),
            "活动回合标识必须是非空字符串", "请求空活动回合")
        other = _seed(store, "另一线程", "b", ("第一答", "另一尾"))
        equivalent = service.compacted_request(
            ModelRequest(model="m2", system="s2", messages=service.history(other)),
            "跨线程", plan)
        checked += _expect_value(
            (equivalent.messages[0].text, equivalent.messages[1].text,
             _assistant_text(equivalent.messages[2])),
            (_prefix_text("跨线程", "t1", 2, plan["sourceDigest"]), "第二问", "另一尾"),
            "同文本前缀按内容比对")
    return checked


def check_compacted_preview() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    history = _function(tree, source, "compacted_history")
    request = _function(tree, source, "compacted_request")
    checked = _ordered(HISTORY_ORDER, history, MODULE)
    checked += _ordered(REQUEST_ORDER, request, MODULE)
    # 预览只读：不得写记录，也不得绕开已冻结的计划重新计算切点。
    for function, label in ((history, "历史预览"), (request, "请求替换")):
        if "append(" in function or "append_event(" in function:
            raise ValueError(f"{MODULE} 的{label}不得写入记录")
        checked += 1
    if history.count("_compaction_snapshot(") != 1 or "_history_projection(" not in history:
        raise ValueError(f"{MODULE} 的历史预览必须基于一次快照投影")
    checked += 1
    # 请求替换只替换已验证前缀，其余消息原样保留。
    if request.count("request.messages[len(expected):]") != 1:
        raise ValueError(f"{MODULE} 的请求替换必须保留实时尾部")
    checked += 1
    if request.count("replace(request, messages=") != 1:
        raise ValueError(f"{MODULE} 的请求替换必须只改消息")
    checked += 1
    # 摘要覆盖范围按回合顺序计算，不能只按选中条目的 turnId 过滤。
    if request.count("turns[:through_index + 1]") != 1:
        raise ValueError(f"{MODULE} 的请求替换必须按回合范围计算摘要覆盖")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_compacted_preview()
    except (ValueError, SyntaxError) as error:
        print(f"压缩预览核对失败，{error}", file=sys.stderr)
        return 2
    print(f"压缩预览一致：{checked} 项摘要前缀、尾部保留与来源校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
