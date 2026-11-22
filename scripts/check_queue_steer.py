#!/usr/bin/env python3
"""核对 queue/steer 的内核、协议与桌面边界，成功时输出核对项数量。

除源码与桌面片段扫描外，脚本在临时目录构造 `SessionStore` 与 `TurnQueue`，
核对 `promote_to_steering` 的成功输出（保留 id / 输入、清空技能、透传客户端
消息标识）与六类拒绝：状态非排队中、类型非 followUp、带技能、带自动压缩
覆盖、`expectedTurnId` 非空且不超过 128 字符、队列项不存在。
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.runtime import TurnQueue  # noqa: E402
from boss_harness.session import SessionStore  # noqa: E402

RUNTIME = "harness/src/boss_harness/runtime.py"
APPLICATION = "harness/src/boss_harness/application.py"
PROTOCOL = "packages/protocol/src/index.ts"
SECURITY = "apps/desktop/src/main/security.ts"
RPC_ERRORS = "apps/desktop/src/main/rpcErrors.ts"
BRIDGE = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
PANEL = "apps/desktop/src/renderer/src/shell/QueuePanel.tsx"

RUNTIME_FRAGMENTS = (
    'if item.get("status") != "queued":',
    'if item.get("kind") != "followUp":',
    'if item.get("skillIds"):',
    'if item.get("autoCompaction") is not None:',
    '"kind": "steering", "input": item["input"],',
    '"status": "queued", "expectedTurnId": turn_id, "skillIds": []',
    'return self._save(thread_id, promoted)',
)
APPLICATION_FRAGMENTS = (
    'job = self.runtimes.active.get(thread_id)',
    'if job is None or job["turnId"] != expected or job["cancel"].is_set():',
    '{"code": "STEER_UNAVAILABLE"}',
    'item = self.queue.promote_to_steering(thread_id, queue_id, expected)',
    'raise RpcError(-32004, str(exc), {"code": "STEER_UNAVAILABLE"}) from None',
)
PROTOCOL_FRAGMENTS = (
    "queueSteer?: boolean;",
    'queueSteer: "queue/steer",',
    "export interface QueueSteerParams { threadId: string; queueId: string; expectedTurnId: string }",
)
SECURITY_FRAGMENTS = (
    '"queue/steer"',
    'if (payload.method === "queue/steer") {',
    'const allowed = new Set(["threadId", "queueId", "expectedTurnId"]);',
    '!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(params.expectedTurnId)',
)
BRIDGE_FRAGMENTS = (
    "ClientMethods.queueSteer",
    "export async function steerQueuedItem(params: QueueSteerParams)",
)
PANEL_FRAGMENTS = (
    "pendingSteerId",
    "转为当前回合",
    "steerBlockedReason",
)
METHOD_ALLOWLISTS = ("RENDERER_METHODS", "THREAD_METHODS")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function_source(relative: str, name: str) -> str:
    try:
        tree = ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(_read(relative), node) or ""
    raise ValueError(f"{relative} 缺少函数 {name}")


def _missing(fragments: tuple[str, ...], text: str) -> list[str]:
    return [fragment for fragment in fragments if fragment not in text]


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = _missing(fragments, text)
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"转向提升行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"转向提升行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"转向提升行为变化 {label}：期望 ValueError")


def _behavior_checks() -> int:
    checked = 0
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            queue = TurnQueue(store)
            thread = store.create("队列")["id"]
            item = queue.add(thread, "补充说明", client_id="c-1")
            promoted = queue.promote_to_steering(thread, item["id"], "turn-1")
            checked += _expect_value(promoted.get("id"), item["id"], "保留 id")
            checked += _expect_value(promoted.get("kind"), "steering", "提升类型")
            checked += _expect_value(promoted.get("status"), "queued", "提升状态")
            checked += _expect_value(promoted.get("input"), "补充说明", "保留输入")
            checked += _expect_value(promoted.get("expectedTurnId"), "turn-1", "目标回合")
            checked += _expect_value(promoted.get("skillIds"), [], "清空技能")
            checked += _expect_value(
                promoted.get("clientUserMessageId"), "c-1", "透传客户端消息")
            checked += _expect_value(queue.list(thread), [promoted], "列表即提升结果")
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, item["id"], "turn-2"),
                "只有后续回合消息可以转为当前回合", "重复提升")

            second = queue.add(thread, "另一条")
            queue.transition(thread, second["id"], "delivering")
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, second["id"], "turn-1"),
                "只有排队中的消息可以转为当前回合", "状态非排队")

            steering = queue.add(thread, "转向", kind="steering")
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, steering["id"], "turn-1"),
                "只有后续回合消息可以转为当前回合", "类型非 followUp")

            skilled = queue.add(thread, "带技能", skill_ids=["s1"])
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, skilled["id"], "turn-1"),
                "带技能的消息不能转为当前回合", "带技能")

            compacted = queue.add(thread, "带压缩", auto_compaction={"enabled": True})
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, compacted["id"], "turn-1"),
                "带自动压缩覆盖的消息不能转为当前回合", "带自动压缩")

            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, item["id"], ""),
                "expectedTurnId 格式无效", "空回合")
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, item["id"], "t" * 129),
                "expectedTurnId 格式无效", "超长回合")
            checked += _expect_error(
                lambda: queue.promote_to_steering(thread, "f" * 32, "turn-1"),
                "队列项不存在", "未知队列项")

            long_turn = queue.add(thread, "长回合")
            bounded = queue.promote_to_steering(thread, long_turn["id"], "t" * 128)
            checked += _expect_value(
                bounded.get("expectedTurnId"), "t" * 128, "128 字符回合")
        finally:
            store.close()
    return checked


def check_queue_steer() -> tuple[int, int]:
    checked = 0
    runtime = _function_source(RUNTIME, "promote_to_steering")
    checked += _expect(RUNTIME_FRAGMENTS, runtime, "TurnQueue.promote_to_steering")
    application = _function_source(APPLICATION, "on_queue_steer")
    checked += _expect(APPLICATION_FRAGMENTS, application, "ApplicationService.on_queue_steer")
    initialize = _function_source(APPLICATION, "on_initialize")
    if '"queueSteer": True,' not in initialize:
        raise ValueError("on_initialize 未声明 queueSteer 能力")

    protocol = _read(PROTOCOL)
    checked += _expect(PROTOCOL_FRAGMENTS, protocol, "协议 queue/steer 定义")
    security = _read(SECURITY)
    checked += _expect(SECURITY_FRAGMENTS, security, "主进程 queue/steer 校验")
    for allowlist in METHOD_ALLOWLISTS:
        match = re.search(rf"\b{allowlist}\s*=\s*new Set\(\[([^\]]*)\]", security, re.DOTALL)
        if match is None:
            raise ValueError(f"security.ts 缺少 {allowlist}")
        if '"queue/steer"' not in match.group(1):
            raise ValueError(f"security.ts 的 {allowlist} 缺少 queue/steer")
        checked += 1
    if '"queue/steer"' not in _read(RPC_ERRORS):
        raise ValueError("rpcErrors.ts 未保留 queue/steer 的 RPC 错误")
    checked += 1

    bridge = _read(BRIDGE)
    checked += _expect(BRIDGE_FRAGMENTS, bridge, "渲染层 steerQueuedItem")
    panel = _read(PANEL)
    checked += _expect(PANEL_FRAGMENTS, panel, "队列面板转向操作")
    if "pendingSteerId" not in _read("apps/desktop/src/renderer/src/data/queueActionState.ts"):
        raise ValueError("队列动作状态缺少 pendingSteerId")
    checked += 1
    return 2, checked + _behavior_checks()


def main() -> int:
    try:
        functions, guards = check_queue_steer()
    except ValueError as error:
        print(f"queue/steer 边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"queue/steer 边界一致：{functions} 个内核函数、{guards} 项状态机、桌面防护与行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
