#!/usr/bin/env python3
"""核对请求身份的校验、去重与冲突边界。

clientUserMessageId 决定重试是关联原请求还是新增输入，也决定转向与直接发送的
类型冲突；持久队列与回合记录不可信。正则、链接收敛或冲突判定被删改不会触发
构建失败，因此用静态检查固定这些边界；并用临时合成队列、输入与回合记录实际
执行编号校验、身份解析与回执投影。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/request_identity.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.request_identity import (  # noqa: E402
    RequestIdentity,
    resolve_request,
    valid_client_id,
)
from boss_harness.rpc import RpcError  # noqa: E402
from boss_harness.session import Entry, SessionStore  # noqa: E402

ID_FRAGMENTS = (
    '_CLIENT_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")',
    "return value if isinstance(value, str) and _CLIENT_ID.fullmatch(value) else None",
    'raise ValueError("clientUserMessageId 格式无效")',
)
LINK_FRAGMENTS = (
    "def _linked_queue_id(item: dict) -> str | None:",
    "return value if isinstance(value, str) else None",
    "def _linked_turn_id(queue: dict) -> str | None:",
    "return value if isinstance(value, str) and value else None",
    # 链接只在持久记录里解析；两轮收敛把队列、输入与回合连成同一身份。
    "for _ in range(2):",
    'record = queue_record(entry.get("payload"))',
    'if key == queue_id or (client_id is not None and item.get("clientUserMessageId") == client_id)}',
)
CONFLICT_FRAGMENTS = (
    '_reject("CLIENT_REQUEST_CONFLICT", "请求编号已用于转向消息，不能改为直接或后续任务")',
    '_reject("CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入")',
    '_reject("CLIENT_REQUEST_AMBIGUOUS", "请求编号对应多条历史身份，请先核对会话")',
    '_reject("REQUEST_REQUIRES_REVIEW", "旧请求对应多条原始输入，请先核对会话")',
    'digest = hashlib.sha256(text.encode("utf-8")).hexdigest()',
)
FACT_FRAGMENTS = (
    'if len(persistence_facts) > 1 or (start_failed and turn is not None and turn.get("status") == "completed"):',
    "if client_id is None and queue_id is None:",
    "return RequestIdentity()",
    'failureCode="TURN_START_FAILED"',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "相同编号的不同输入、steering 类型冲突或历史身份歧义会明确拒绝"),
    (USER_GUIDE, "相同 `clientUserMessageId` 会关联原请求，输入已接受不表示回合已成功"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"请求身份行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_value_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"请求身份行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"请求身份行为变化 {label}：期望错误 {message!r}，实际未抛出")


def _expect_rejected(call, code: str, message: str, label: str) -> int:
    try:
        call()
    except RpcError as error:
        data = error.data if isinstance(error.data, dict) else {}
        if error.code != -32004 or data.get("code") != code or str(error) != message:
            raise ValueError(
                f"请求身份行为变化 {label}：期望 {code} / {message!r}，"
                f"实际 {data.get('code')!r} / {str(error)!r}") from None
        return 1
    except ValueError as error:
        raise ValueError(
            f"请求身份行为变化 {label}：期望 {code}，实际 ValueError {str(error)!r}") from None
    raise ValueError(f"请求身份行为变化 {label}：期望 {code}，实际未抛出")


def _add_queue(store: SessionStore, thread_id: str, queue_id: str, *, text: str = "你好",
               client_id: str | None = None, kind: str = "followUp",
               status: str = "queued", **extra) -> None:
    payload = {"id": queue_id, "kind": kind, "status": status, "input": text, **extra}
    if client_id is not None:
        payload["clientUserMessageId"] = client_id
    store.append(thread_id, Entry(type="queue", payload=payload))


def _add_turn(store: SessionStore, thread_id: str, turn_id: str, *, text: str | None = None,
              client_id: str | None = None, status: str = "running", **extra) -> None:
    payload = {"turnId": turn_id, "status": status, **extra}
    if text is not None:
        payload["requestInputDigest"] = _digest(text)
    if client_id is not None:
        payload["clientUserMessageId"] = client_id
    store.append(thread_id, Entry(type="turn", payload=payload))


def _add_user(store: SessionStore, thread_id: str, item_id: str, *, text: str = "你好",
              client_id: str | None = None, **extra) -> None:
    payload = {"kind": "userMessage", "text": text, **extra}
    if client_id is not None:
        payload["clientUserMessageId"] = client_id
    store.append(thread_id, Entry(type="item", id=item_id, payload=payload))


def _behavior_checks() -> int:
    checked = 0
    # 编号整串匹配、长度与字符边界；子串匹配会把带空格的字符串误当成合法编号。
    for value, expected in (
        ("a", "a"), ("A-z_0-9", "A-z_0-9"), ("x" * 128, "x" * 128),
        ("x" * 129, None), ("", None), ("a b", None), ("中文", None),
        (123, None), (None, None), (True, None), ("a.b", None),
    ):
        checked += _expect_value(valid_client_id(value), expected,
                                 f"编号校验 {str(value)[:12]!r}")

    # 回执只投影回合、去重标记与持久事实。
    checked += _expect_value_error(RequestIdentity().receipt, "请求尚未关联回合", "空身份回执")
    checked += _expect_value(RequestIdentity(turn={"turnId": "t1"}).receipt(),
                             {"turnId": "t1", "deduplicated": True, "status": "paused"},
                             "未确认落盘回执")
    checked += _expect_value(RequestIdentity(turn={"turnId": "t1"}, input_persisted=False).receipt(),
                             {"turnId": "t1", "deduplicated": True, "status": "paused",
                              "inputPersisted": False}, "未落盘回执")
    checked += _expect_value(RequestIdentity(turn={"turnId": "t1"}, input_persisted=True).receipt(),
                             {"turnId": "t1", "deduplicated": True, "status": "delivered",
                              "inputPersisted": True}, "已落盘回执")
    checked += _expect_value(RequestIdentity(turn={"turnId": "t1"}, start_failed=True).receipt(),
                             {"turnId": "t1", "deduplicated": True, "status": "paused",
                              "failureCode": "TURN_START_FAILED", "executionStarted": False},
                             "启动失败回执")

    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")

        def new_thread() -> str:
            return store.create("身份")["id"]

        thread = new_thread()
        checked += _expect_value(resolve_request(store, thread, None, "你好"),
                                 RequestIdentity(), "空身份短路")
        checked += _expect_value_error(lambda: resolve_request(store, thread, "坏 编号", "你好"),
                                       "clientUserMessageId 格式无效", "非法编号拒绝")
        checked += _expect_value(resolve_request(store, thread, "c0", "你好"),
                                 RequestIdentity(), "无匹配空身份")

        _add_queue(store, thread, "q1", client_id="c1", inputPersisted=True)
        identity = resolve_request(store, thread, "c1", "你好")
        checked += _expect_value(identity.queue["id"], "q1", "队列编号匹配")
        checked += _expect_value(identity.input_persisted, True, "队列落盘事实")
        checked += _expect_value_error(identity.receipt, "请求尚未关联回合", "队列回执缺回合")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c1", "不同"),
                                    "CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入",
                                    "队列输入冲突")
        checked += _expect_value(resolve_request(store, thread, "queue-q1", "你好"),
                                 RequestIdentity(), "外部编号不能认领队列")
        checked += _expect_value(
            resolve_request(store, thread, None, "你好", queue_id="q1").queue["id"],
            "q1", "内部队列关联")
        checked += _expect_rejected(
            lambda: resolve_request(store, thread, None, "不同", queue_id="q1"),
            "CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入", "内部关联输入冲突")
        _add_queue(store, thread, "q2", client_id="c2", kind="steering")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c2", "你好"),
                                    "CLIENT_REQUEST_CONFLICT",
                                    "请求编号已用于转向消息，不能改为直接或后续任务",
                                    "转向队列冲突")
        _add_queue(store, thread, "q3", client_id="other")
        checked += _expect_rejected(
            lambda: resolve_request(store, thread, "c3", "你好", queue_id="q3"),
            "CLIENT_REQUEST_CONFLICT", "请求编号与既有队列关联不一致", "队列身份不一致")
        _add_queue(store, thread, "q4", client_id="x" * 200)
        checked += _expect_value(
            resolve_request(store, thread, None, "你好", queue_id="q4").queue["id"],
            "q4", "损坏存储编号按缺失")
        store.append(thread, Entry(type="queue", payload={
            "id": "q5", "kind": "unknown", "status": "queued", "input": "你好"}))
        checked += _expect_value(resolve_request(store, thread, None, "你好", queue_id="q5"),
                                 RequestIdentity(), "损坏队列跳过")

        thread = new_thread()
        _add_user(store, thread, "u1", client_id="c1", turnId="t1")
        _add_turn(store, thread, "t1", text="你好", client_id="c1")
        identity = resolve_request(store, thread, "c1", "你好")
        checked += _expect_value((identity.user["id"], identity.turn["turnId"]),
                                 ("u1", "t1"), "输入与回合匹配")
        checked += _expect_value(identity.receipt(),
                                 {"turnId": "t1", "deduplicated": True, "status": "delivered",
                                  "inputPersisted": True}, "匹配回执")
        _add_user(store, thread, "u2", client_id="c2", turnId="t2", text="不同")
        _add_turn(store, thread, "t2", text="你好", client_id="c2")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c2", "你好"),
                                    "CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入",
                                    "输入正文冲突")
        _add_user(store, thread, "u3", client_id="c3", turnId="t3")
        _add_turn(store, thread, "t3", text="不同", client_id="c3")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c3", "你好"),
                                    "CLIENT_REQUEST_CONFLICT", "clientUserMessageId 已用于不同输入",
                                    "回合摘要冲突")
        _add_user(store, thread, "u4", client_id="c4", turnId="t4")
        _add_turn(store, thread, "t4", text="你好", client_id="other")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c4", "你好"),
                                    "CLIENT_REQUEST_CONFLICT", "请求编号与既有回合身份不一致",
                                    "回合身份不一致")
        _add_user(store, thread, "u5", client_id="c5", turnId="t5", source="steering")
        _add_turn(store, thread, "t5", text="你好", client_id="c5")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c5", "你好"),
                                    "CLIENT_REQUEST_CONFLICT",
                                    "请求编号已用于转向消息，不能改为直接或后续任务",
                                    "转向输入冲突")

        thread = new_thread()
        _add_queue(store, thread, "q6", text="继续", turnId="t6")
        _add_turn(store, thread, "t6", text="继续", queueId="q6")
        _add_user(store, thread, "u6", text="继续", queueId="q6", turnId="t6")
        identity = resolve_request(store, thread, None, "继续", queue_id="q6")
        checked += _expect_value(
            (identity.queue["id"], identity.turn["turnId"], identity.user["id"]),
            ("q6", "t6", "u6"), "两轮链接收敛")
        checked += _expect_value(identity.input_persisted, True, "收敛落盘事实")

        thread = new_thread()
        _add_queue(store, thread, "q7", text="再试")
        _add_turn(store, thread, "t7", text="再试", client_id="c7", queueId="q7")
        _add_user(store, thread, "u7", text="再试", queueId="q7", turnId="t7")
        identity = resolve_request(store, thread, "c7", "再试")
        checked += _expect_value((identity.queue["id"], identity.user["id"]), ("q7", "u7"),
                                 "回合链接收敛")

        thread = new_thread()
        _add_queue(store, thread, "q8", client_id="c8")
        _add_queue(store, thread, "q9", client_id="c8")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c8", "你好"),
                                    "CLIENT_REQUEST_AMBIGUOUS",
                                    "请求编号对应多条历史身份，请先核对会话", "重复队列歧义")
        _add_turn(store, thread, "t10", text="你好", client_id="c10")
        _add_turn(store, thread, "t11", text="你好", client_id="c10")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c10", "你好"),
                                    "CLIENT_REQUEST_AMBIGUOUS",
                                    "请求编号对应多条历史身份，请先核对会话", "重复回合歧义")
        _add_user(store, thread, "u12", client_id="c12", turnId="t12")
        _add_user(store, thread, "u13", client_id="c12", turnId="t12")
        _add_turn(store, thread, "t12", text="你好", client_id="c12")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c12", "你好"),
                                    "REQUEST_REQUIRES_REVIEW",
                                    "旧请求对应多条原始输入，请先核对会话", "重复输入复核")

        thread = new_thread()
        _add_turn(store, thread, "t13", client_id="c13")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c13", "你好"),
                                    "REQUEST_REQUIRES_REVIEW",
                                    "旧请求缺少可核对的回合或输入，请先核对会话", "缺输入复核")
        thread = new_thread()
        _add_user(store, thread, "u14", client_id="c14")
        checked += _expect_rejected(lambda: resolve_request(store, thread, "c14", "你好"),
                                    "REQUEST_REQUIRES_REVIEW",
                                    "旧请求缺少可核对的回合或输入，请先核对会话", "缺回合复核")

        thread = new_thread()
        _add_queue(store, thread, "q15", text="继续", turnId="t15", inputPersisted=False)
        _add_turn(store, thread, "t15", text="继续", queueId="q15", inputPersisted=True)
        checked += _expect_rejected(
            lambda: resolve_request(store, thread, None, "继续", queue_id="q15"),
            "REQUEST_REQUIRES_REVIEW", "旧请求的持久事实不一致，请先核对会话", "持久事实冲突")

        thread = new_thread()
        _add_queue(store, thread, "q16", text="继续", turnId="t16",
                   failureCode="TURN_START_FAILED", executionStarted=False)
        _add_turn(store, thread, "t16", text="继续", queueId="q16", status="completed")
        checked += _expect_rejected(
            lambda: resolve_request(store, thread, None, "继续", queue_id="q16"),
            "REQUEST_REQUIRES_REVIEW", "旧请求的持久事实不一致，请先核对会话", "失败后已完成复核")

        thread = new_thread()
        _add_queue(store, thread, "q17", text="继续", turnId="t17",
                   failureCode="TURN_START_FAILED", executionStarted=False)
        _add_turn(store, thread, "t17", text="继续", queueId="q17", inputPersisted=False)
        identity = resolve_request(store, thread, None, "继续", queue_id="q17")
        checked += _expect_value(identity.receipt(),
                                 {"turnId": "t17", "deduplicated": True, "status": "paused",
                                  "failureCode": "TURN_START_FAILED", "executionStarted": False,
                                  "inputPersisted": False}, "启动失败回执")
    return checked


def check_request_identity() -> int:
    module = _read(MODULE)
    checked = _expect(ID_FRAGMENTS, module, MODULE)
    checked += _expect(LINK_FRAGMENTS, module, MODULE)
    checked += _expect(CONFLICT_FRAGMENTS, module, MODULE)
    checked += _expect(FACT_FRAGMENTS, module, MODULE)
    # 身份必须整串匹配；子串匹配会把 queue-<id> 之类的字符串误当成客户端编号。
    if "_CLIENT_ID.search(" in module:
        raise ValueError(f"{MODULE} 的 clientUserMessageId 必须整串匹配")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_request_identity()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"请求身份核对失败，{error}", file=sys.stderr)
        return 2
    print(f"请求身份一致：{checked} 项校验、冲突与文档防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
