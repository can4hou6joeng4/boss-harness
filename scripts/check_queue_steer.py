#!/usr/bin/env python3
"""核对 queue/steer 的内核、协议与桌面边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
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
    return 2, checked


def main() -> int:
    try:
        functions, guards = check_queue_steer()
    except ValueError as error:
        print(f"queue/steer 边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"queue/steer 边界一致：{functions} 个内核函数、{guards} 项状态机与桌面防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
