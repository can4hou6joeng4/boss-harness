#!/usr/bin/env python3
"""核对队列新增、编辑、状态转移与暂停结算口径。

`TurnQueue` 是持久队列的状态机：新增时校验 kind、正文、客户端幂等 id、技能
列表与容量上限；编辑只改排队项正文并按替换后的字节重算上限；转移表禁止
已投递项回退；领取 steering 时必须匹配当前回合；暂停来源按 kind 优先，
结算只处理排队 / 投递中的项，并在一次 `append_many` 后清理作用域。这里按
源码顺序固定这些边界。行为检查在临时会话存储上直接调用 `TurnQueue`，避免
去重、上限或状态机被重构放宽。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "harness/src/boss_harness/runtime.py"

USAGE_ORDER = (
    "def _pending_usage(items: list[dict]) -> tuple[int, int]:",
    'pending = [item for item in items if item.get("status") in {"queued", "delivering"}]',
    'total_bytes = sum(len(item["input"].encode("utf-8")) for item in pending)',
    "return len(pending), total_bytes",
)
ADD_ORDER = (
    'def add(self, thread_id: str, text: str, *, kind: str = "followUp", turn_id: str | None = None,',
    "client_id: str | None = None, skill_ids: list[str] | None = None,",
    "auto_compaction: dict | None = None) -> dict:",
    'if kind not in {"steering", "followUp"}:',
    'raise ValueError("kind 必须是 steering 或 followUp")',
    "if not isinstance(text, str) or not text.strip() or len(text) > MAX_QUEUE_INPUT_CHARS:",
    'raise ValueError("队列 input 必须是 1 到 100000 字符")',
    'if client_id is not None and (not isinstance(client_id, str) or not re.fullmatch(',
    'raise ValueError("clientUserMessageId 格式无效")',
    "if skill_ids is None:",
    "skill_ids = []",
    "if not isinstance(skill_ids, list) or len(skill_ids) > 10 or not all(",
    "isinstance(item, str) and item for item in skill_ids):",
    'raise ValueError("skillIds 必须是最多 10 项的非空字符串数组")',
    "skill_ids = list(dict.fromkeys(skill_ids))",
    'if kind == "steering" and skill_ids:',
    'raise ValueError("转向消息不支持技能")',
    "with self.lock:",
    "self.settle_pauses(thread_id)",
    "items = self.list(thread_id)",
    "for item in items:",
    'if client_id and item.get("clientUserMessageId") == client_id:',
    'if item["input"] != text or item["kind"] != kind or (item.get("skillIds") or []) != skill_ids:',
    'raise ValueError("clientUserMessageId 已用于不同输入或技能组合")',
    'if auto_compaction is not None and item.get("autoCompaction") != auto_compaction:',
    'raise ValueError("clientUserMessageId 已用于不同自动压缩覆盖")',
    "return item",
    "pending_items, pending_bytes = self._pending_usage(items)",
    'input_bytes = len(text.encode("utf-8"))',
    "if (pending_items >= MAX_PENDING_QUEUE_ITEMS",
    "or pending_bytes + input_bytes > MAX_PENDING_QUEUE_INPUT_BYTES):",
    'raise RpcError(-32005, "会话待处理队列已达到内核资源上限",',
    '"code": "QUEUE_LIMIT", "maxItems": MAX_PENDING_QUEUE_ITEMS,',
    '"maxInputBytes": MAX_PENDING_QUEUE_INPUT_BYTES})',
    'return self._save(thread_id, {"id": uuid.uuid4().hex, "kind": kind,',
    '"input": text, "status": "queued", "expectedTurnId": turn_id,',
    '"clientUserMessageId": client_id, "skillIds": skill_ids,',
    '**({"autoCompaction": auto_compaction} if auto_compaction is not None else {})})',
)
UPDATE_ORDER = (
    "def update_input(self, thread_id: str, queue_id: str, text: str) -> dict:",
    "if not isinstance(text, str) or not text.strip() or len(text) > MAX_QUEUE_INPUT_CHARS:",
    "with self.lock:",
    "self.settle_pauses(thread_id)",
    "items = self.list(thread_id)",
    'item = next((q for q in items if q["id"] == queue_id), None)',
    "if item is None:",
    'raise ValueError("队列项不存在")',
    'if item.get("status") != "queued":',
    'raise ValueError("只有排队中的消息可以编辑")',
    "_, pending_bytes = self._pending_usage(items)",
    'pending_bytes += len(text.encode("utf-8")) - len(item["input"].encode("utf-8"))',
    "if pending_bytes > MAX_PENDING_QUEUE_INPUT_BYTES:",
    'raise RpcError(-32005, "会话待处理队列已达到内核资源上限",',
    'if item["input"] == text:',
    "return item",
    'return self._save(thread_id, {**item, "input": text})',
)
TRANSITION_ORDER = (
    "def transition(self, thread_id: str, queue_id: str, status: str) -> dict:",
    "with self.lock:",
    "self.settle_pauses(thread_id)",
    'item = next((q for q in self.list(thread_id) if q["id"] == queue_id), None)',
    "if item is None:",
    'allowed = {"queued": {"delivering", "delivered", "paused", "cancelled"},',
    '"delivering": {"delivered", "paused"}, "paused": {"cancelled"}}',
    'if status not in allowed.get(item["status"], set()):',
    'raise ValueError("队列项已投递或状态不允许此操作")',
    'return self._save(thread_id, {**item, "status": status})',
)
CLAIM_ORDER = (
    "def claim(self, thread_id: str, kind: str, turn_id: str | None = None) -> dict | None:",
    "with self.lock:",
    "self.settle_pauses(thread_id)",
    'item = next((q for q in self.list(thread_id) if q["kind"] == kind and q["status"] == "queued"',
    'and (kind != "steering"',
    'or (isinstance(q.get("expectedTurnId"), str)',
    'and q["expectedTurnId"] == turn_id))), None)',
    'return self.transition(thread_id, item["id"], "delivering") if item else None',
)
PAUSE_ORDER = (
    "def pause(self, thread_id: str, *, kind: str | None = None,",
    "reason: str | None = None) -> list[str]:",
    "with self.lock:",
    "scopes = self._pending_pauses.setdefault(thread_id, {})",
    "if reason is not None or kind not in scopes:",
    "scopes[kind] = reason",
    "return self.settle_pauses(thread_id)",
)
SETTLE_ORDER = (
    "def settle_pauses(self, thread_id: str, *, maximum_session_bytes: int | None = None) -> list[str]:",
    "with self.lock:",
    "scopes = self._pending_pauses.get(thread_id)",
    "if not scopes:",
    "return []",
    "updates = []",
    "for item in self.list(thread_id):",
    'if item["status"] not in {"queued", "delivering"}:',
    "continue",
    'if item["kind"] in scopes:',
    'reason = scopes[item["kind"]]',
    "elif None in scopes:",
    "reason = scopes[None]",
    "else:",
    "continue",
    'payload = {**item, "status": "paused"}',
    "if reason is not None:",
    'payload["pausedReason"] = reason',
    'updates.append(Entry(type="queue", payload=payload))',
    "self.sessions.append_many(thread_id, updates, maximum_bytes=maximum_session_bytes)",
    "self._pending_pauses.pop(thread_id, None)",
    'return [entry.payload["id"] for entry in updates]',
)


sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.rpc import RpcError  # noqa: E402
from boss_harness.runtime import (  # noqa: E402
    MAX_PENDING_QUEUE_INPUT_BYTES,
    MAX_PENDING_QUEUE_ITEMS,
    TurnQueue,
)
from boss_harness.session import SessionStore  # noqa: E402


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"队列状态行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) == message:
            return 1
        raise ValueError(
            f"队列状态行为变化 {label}：错误文案 {str(error)!r} 不等于 {message!r}") from None
    raise ValueError(f"队列状态行为变化 {label}：没有抛出 ValueError")


def _expect_limit(call, label: str) -> int:
    try:
        call()
    except RpcError as error:
        if (error.code, error.data) == (-32005, {
                "code": "QUEUE_LIMIT", "maxItems": MAX_PENDING_QUEUE_ITEMS,
                "maxInputBytes": MAX_PENDING_QUEUE_INPUT_BYTES}):
            return 1
        raise ValueError(f"队列状态行为变化 {label}：超限信息变化 {error.code} {error.data!r}") from None
    raise ValueError(f"队列状态行为变化 {label}：没有抛出 RpcError")


def _behavior_checks() -> int:
    checked = 0
    # 静态统计只覆盖排队与投递中，字节数按 UTF-8。
    checked += _expect_value(
        TurnQueue._pending_usage([
            {"status": "queued", "input": "中"}, {"status": "delivering", "input": "ab"},
            {"status": "paused", "input": "x"}, {"status": "delivered", "input": "x"}]),
        (2, 5), "待处理统计")
    with TemporaryDirectory() as directory:
        store = SessionStore(Path(directory) / "sessions")
        queue = TurnQueue(store)

        def thread() -> str:
            return store.create("t")["id"]

        # 新增：技能去重保序，转向消息拒绝技能，重复客户端 id 只接受同一输入。
        added_thread = thread()
        item = queue.add(added_thread, "hello", client_id="c1", skill_ids=["b", "a", "a"])
        checked += _expect_value(
            (item["kind"], item["status"], item["expectedTurnId"],
             item["clientUserMessageId"], item["skillIds"]),
            ("followUp", "queued", None, "c1", ["b", "a"]), "新增字段")
        checked += _expect_value(
            queue.add(added_thread, "hello", client_id="c1", skill_ids=["b", "a"])["id"],
            item["id"], "客户端幂等")
        checked += _expect_value(len(queue.list(added_thread)), 1, "幂等不重复入队")
        checked += _expect_error(
            lambda: queue.add(added_thread, "other", client_id="c1"),
            "clientUserMessageId 已用于不同输入或技能组合", "客户端 id 冲突")
        checked += _expect_error(
            lambda: queue.add(added_thread, "x", kind="steering", skill_ids=["a"]),
            "转向消息不支持技能", "转向消息拒绝技能")
        checked += _expect_error(
            lambda: queue.add(added_thread, "x", kind="nope"),
            "kind 必须是 steering 或 followUp", "非法 kind")
        checked += _expect_error(
            lambda: queue.add(added_thread, "  "),
            "队列 input 必须是 1 到 100000 字符", "空白输入")
        checked += _expect_error(
            lambda: queue.add(added_thread, "x", skill_ids=[str(index) for index in range(11)]),
            "skillIds 必须是最多 10 项的非空字符串数组", "技能数量上限")
        checked += _expect_error(
            lambda: queue.add(added_thread, "x", skill_ids=["a", ""]),
            "skillIds 必须是最多 10 项的非空字符串数组", "技能空字符串")

        # 编辑：只改正文并保留条目身份；已投递项与不存在的条目都拒绝。
        updated = queue.update_input(added_thread, item["id"], "changed")
        checked += _expect_value(
            (updated["id"], updated["input"], updated["status"]),
            (item["id"], "changed", "queued"), "编辑正文")
        checked += _expect_value(queue.update_input(added_thread, item["id"], "changed")["id"],
                                 item["id"], "同文编辑")
        checked += _expect_error(
            lambda: queue.update_input(added_thread, "missing", "x"),
            "队列项不存在", "编辑不存在项")

        # 转移表：排队可投递、投递中可完成，已投递不可回退，暂停不可继续投递。
        queue.transition(added_thread, item["id"], "delivering")
        checked += _expect_error(
            lambda: queue.update_input(added_thread, item["id"], "x"),
            "只有排队中的消息可以编辑", "投递中不可编辑")
        queue.transition(added_thread, item["id"], "delivered")
        checked += _expect_error(
            lambda: queue.transition(added_thread, item["id"], "queued"),
            "队列项已投递或状态不允许此操作", "已投递不可回退")
        paused_item = queue.add(added_thread, "pause me")
        queue.transition(added_thread, paused_item["id"], "paused")
        checked += _expect_error(
            lambda: queue.transition(added_thread, paused_item["id"], "delivering"),
            "队列项已投递或状态不允许此操作", "暂停不可投递")
        checked += _expect_value(
            queue.transition(added_thread, paused_item["id"], "cancelled")["status"],
            "cancelled", "暂停可取消")

        # 领取：steering 必须匹配回合，重复领取返回空；followUp 不受回合限制。
        claim_thread = thread()
        steering = queue.add(claim_thread, "steer", kind="steering", turn_id="turn-1")
        follow = queue.add(claim_thread, "follow", turn_id="turn-9")
        checked += _expect_value(queue.claim(claim_thread, "steering", "turn-2"), None,
                                 "回合不匹配不领取")
        checked += _expect_value(
            (queue.claim(claim_thread, "steering", "turn-1") or {}).get("id"),
            steering["id"], "回合匹配领取")
        checked += _expect_value(queue.claim(claim_thread, "steering", "turn-1"), None,
                                 "已领取不再返回")
        checked += _expect_value(
            (queue.claim(claim_thread, "followUp", "other") or {}).get("id"),
            follow["id"], "followUp 忽略回合")

        # 暂停结算：具体来源优先只作用于同类排队项，无来源兜底处理其余活动项，
        # 已暂停项保留原原因；作用域在一次结算后清理，新项不受旧暂停影响。
        pause_thread = thread()
        first = queue.add(pause_thread, "a", kind="followUp")
        steering_item = queue.add(pause_thread, "b", kind="steering", turn_id="t1")
        checked += _expect_value(
            queue.pause(pause_thread, kind="followUp", reason="network"), [first["id"]],
            "按 kind 暂停")
        states = {q["id"]: (q["status"], q.get("pausedReason")) for q in queue.list(pause_thread)}
        checked += _expect_value(
            (states[first["id"]], states[steering_item["id"]]),
            (("paused", "network"), ("queued", None)), "暂停作用范围")
        later = queue.add(pause_thread, "c", kind="followUp")
        checked += _expect_value(later["status"], "queued", "结算后作用域清理")
        checked += _expect_value(
            sorted(queue.pause(pause_thread, reason=None)),
            sorted([later["id"], steering_item["id"]]), "无来源暂停其余活动项")
        states = {q["id"]: (q["status"], q.get("pausedReason")) for q in queue.list(pause_thread)}
        checked += _expect_value(
            (states[first["id"]], states[later["id"]], states[steering_item["id"]]),
            (("paused", "network"), ("paused", None), ("paused", None)), "已暂停原因保留")
        checked += _expect_value(queue.pause(pause_thread), [], "无活动项结算为空")

        # 容量：第 129 个待处理项触发 QUEUE_LIMIT，已结算的暂停项不计入。
        limit_thread = thread()
        for index in range(MAX_PENDING_QUEUE_ITEMS):
            queue.add(limit_thread, f"item-{index}")
        checked += _expect_limit(lambda: queue.add(limit_thread, "one more"), "条目上限")
        queue.pause(limit_thread, reason=None)
        checked += _expect_value(queue.add(limit_thread, "after pause")["status"], "queued",
                                 "暂停项不占容量")
    return checked


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TurnQueue":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 TurnQueue.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_queue_state() -> int:
    source = _read(RUNTIME)
    tree = ast.parse(source)
    usage = _method(tree, source, "_pending_usage")
    add = _method(tree, source, "add")
    update = _method(tree, source, "update_input")
    transition = _method(tree, source, "transition")
    claim = _method(tree, source, "claim")
    pause = _method(tree, source, "pause")
    settle = _method(tree, source, "settle_pauses")
    checked = _ordered(USAGE_ORDER, usage, RUNTIME)
    checked += _ordered(ADD_ORDER, add, RUNTIME)
    checked += _ordered(UPDATE_ORDER, update, RUNTIME)
    checked += _ordered(TRANSITION_ORDER, transition, RUNTIME)
    checked += _ordered(CLAIM_ORDER, claim, RUNTIME)
    checked += _ordered(PAUSE_ORDER, pause, RUNTIME)
    checked += _ordered(SETTLE_ORDER, settle, RUNTIME)
    # 待处理统计只覆盖排队与投递中两项。
    if usage.count('{"queued", "delivering"}') != 1:
        raise ValueError(f"{RUNTIME} 的待处理统计必须只覆盖 queued 与 delivering")
    checked += 1
    # 新增：技能先去重再检查转向限制，客户端 id 正则必须锚定 1–128。
    if add.count("list(dict.fromkeys(skill_ids))") != 1:
        raise ValueError(f"{RUNTIME} 的技能列表必须去重后再校验")
    checked += 1
    if add.count(r're.fullmatch(r"[A-Za-z0-9_-]{1,128}", client_id)') != 1:
        raise ValueError(f"{RUNTIME} 的客户端消息 id 必须是 1–128 位受限字符")
    checked += 1
    if add.count('raise ValueError("转向消息不支持技能")') != 1:
        raise ValueError(f"{RUNTIME} 的转向消息不得携带技能")
    checked += 1
    # 容量：条目数用 >=，字节数用 >，超限统一 QUEUE_LIMIT。
    if add.count("pending_items >= MAX_PENDING_QUEUE_ITEMS") != 1:
        raise ValueError(f"{RUNTIME} 的待处理条目上限必须包含等于")
    checked += 1
    if add.count("pending_bytes + input_bytes > MAX_PENDING_QUEUE_INPUT_BYTES") != 1:
        raise ValueError(f"{RUNTIME} 的待处理字节上限必须严格大于")
    checked += 1
    if add.count('"code": "QUEUE_LIMIT"') != 1:
        raise ValueError(f"{RUNTIME} 的队列超限必须使用 QUEUE_LIMIT")
    checked += 1
    # 幂等：同一客户端 id 只允许完全相同的输入、类型、技能与自动压缩覆盖。
    if add.count('item["input"] != text or item["kind"] != kind or (item.get("skillIds") or []) != skill_ids') != 1:
        raise ValueError(f"{RUNTIME} 的客户端消息幂等必须比对输入、类型与技能")
    checked += 1
    if add.count('item.get("autoCompaction") != auto_compaction') != 1:
        raise ValueError(f"{RUNTIME} 的客户端消息幂等必须比对自动压缩覆盖")
    checked += 1
    # 编辑：按替换字节重算上限，且只改正文。
    if update.count("len(text.encode(\"utf-8\")) - len(item[\"input\"].encode(\"utf-8\"))") != 1:
        raise ValueError(f"{RUNTIME} 的队列编辑必须按替换字节重算上限")
    checked += 1
    if update.count('{**item, "input": text}') != 1 or '{**item, "status"' in update:
        raise ValueError(f"{RUNTIME} 的队列编辑只能替换正文")
    checked += 1
    # 转移表固定：投递中不可回到排队，已暂停不可继续投递。
    if transition.count('"delivering": {"delivered", "paused"}') != 1:
        raise ValueError(f"{RUNTIME} 的投递中状态只能转为已投递或暂停")
    checked += 1
    if transition.count('"paused": {"cancelled"}') != 1:
        raise ValueError(f"{RUNTIME} 的暂停状态只能取消")
    checked += 1
    if transition.count('"queued": {"delivering", "delivered", "paused", "cancelled"}') != 1:
        raise ValueError(f"{RUNTIME} 的排队状态转移表变化")
    checked += 1
    # 领取：只有 steering 需要匹配回合，且必须是字符串比较。
    if claim.count('isinstance(q.get("expectedTurnId"), str)') != 1:
        raise ValueError(f"{RUNTIME} 的 steering 领取必须要求字符串回合 id")
    checked += 1
    if claim.count('q["expectedTurnId"] == turn_id') != 1:
        raise ValueError(f"{RUNTIME} 的 steering 领取必须匹配当前回合")
    checked += 1
    # 暂停：具体来源优先，无来源暂停不能覆盖已有原因。
    if pause.count("if reason is not None or kind not in scopes:") != 1:
        raise ValueError(f"{RUNTIME} 的暂停必须保留已有的具体来源")
    checked += 1
    # 结算：kind 来源优先于无来源兜底，pausedReason 只在有原因时写入。
    if settle.count('if item["kind"] in scopes:') != 1 or settle.count("elif None in scopes:") != 1:
        raise ValueError(f"{RUNTIME} 的暂停结算必须按 kind 优先")
    checked += 1
    if settle.count("if reason is not None:") != 1:
        raise ValueError(f"{RUNTIME} 的 pausedReason 只在有原因时写入")
    checked += 1
    if settle.count('self.sessions.append_many(thread_id, updates, maximum_bytes=maximum_session_bytes)') != 1:
        raise ValueError(f"{RUNTIME} 的暂停结算必须一次写回")
    checked += 1
    if settle.count("self._pending_pauses.pop(thread_id, None)") != 1:
        raise ValueError(f"{RUNTIME} 的暂停作用域必须在写回后清理")
    checked += 1
    if settle.count('return [entry.payload["id"] for entry in updates]') != 1:
        raise ValueError(f"{RUNTIME} 的暂停结算必须返回实际暂停的 id")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_queue_state()
    except (ValueError, SyntaxError) as error:
        print(f"队列状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列状态一致：{checked} 项新增、编辑、转移、暂停与行为校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
