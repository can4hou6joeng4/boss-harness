#!/usr/bin/env python3
"""核对 Node 宿主的连接代际、重连预算与审批路由边界。

`packages/app-client/src/host.ts` 管理每个 host 的进程代际：初始化握手、断开后
的有限自动重连、显式重连的新恢复预算，以及审批服务器请求的截止与撤销。
这里固定：代际归属判定、断开只由失败传输触发、初始化回执的形状校验、
审批裁决的类型与代际检查、持久审批释放客户端待答槽位、期限默认值与
损坏值的处理、重连次数与退避上限、关闭后不再重连。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HOST = "packages/app-client/src/host.ts"

STATE_FRAGMENTS = (
    'export type HarnessConnectionState = "cold" | "starting" | "initializing" | "ready" | "disconnected" | "stopped";',
    "willRetry: this.#state === \"disconnected\" && this.options.supportsReconnect === true &&",
    "retry !== undefined && this.#reconnectAttempt < retry.maxAttempts,",
    "running: this.#state === \"ready\", reconnectAttempt: this.#reconnectAttempt,",
    "startupFailed: this.#startupFailed, wasReady: this.#wasReady,",
)
READY_FRAGMENTS = (
    'if (this.#state === "stopped") return Promise.reject(new Error("harness host has stopped"));',
    'if (this.#state === "ready" && this.#initialized) return Promise.resolve(this.#initialized);',
    "if (this.#connecting) return this.#connecting;",
    "this.#clearRetry();",
    "if (this.#retiring) await this.#retiring;",
    'if (this.#connecting !== flight || this.#state === "stopped") throw new Error("harness connection superseded");',
    "generation = ++this.#generation;",
    "if (!this.#isCurrent(connection, generation)) return;",
    'if (notification.method === "harness/disconnected") {',
    "if (!connection.exited) return;",
    "this.#disconnected(connection, generation,",
    "this.#expireFinishedApprovals(notification, connection);",
    'this.#setState("starting");',
    'this.#setState("initializing");',
    'const response = await connection.request<InitializeResponse>("initialize", {',
    'capabilities: { experimentalApi: false, bidirectionalRequests: true },',
    'if (!object(response) || typeof response.serverName !== "string" || typeof response.protocolVersion !== "string") {',
    'throw new Error("invalid harness initialize response");',
    'connection.notify("initialized");',
    "this.#startupFailed = false;",
    "this.#wasReady = true;",
    'this.#setState("ready");',
    '"harness initialization failed"',
    "if (this.#state === \"disconnected\") this.#scheduleReconnect();",
)
REQUEST_FRAGMENTS = (
    "if (!client || this.#state !== \"ready\") throw new Error(\"harness connection changed before request\");",
    'if (method === "approval/respond" && object(params) && typeof params.approvalId === "string") {',
    'if (typeof params.approved !== "boolean") throw new Error("approval decision must be a boolean");',
    'if (route.generation !== this.#generation) throw new Error("approval belongs to a previous connection");',
    "if (this.#initialized?.capabilities?.durableApprovals !== true) {",
    "client.respond(route.requestId, { approved: params.approved });",
    "const result = await client.request<T>(method, params);",
    "client.forgetServerRequest(route.requestId);",
    'if (this.#initialized?.capabilities?.durableApprovals !== true &&\n          this.#initialized?.protocolVersion !== "0.1.0") throw new Error("approval is no longer pending");',
)
LIFECYCLE_FRAGMENTS = (
    "if (this.#restarting) return this.#restarting;",
    "this.#generation += 1;",
    "this.#clearApprovals();",
    "this.#reconnectAttempt = 0;",
    "this.#startupFailed = false;",
    'this.#setState("disconnected");',
    "if (this.#state === \"stopped\") return;",
    'this.#setState("stopped");',
    "return this.#client === client && this.#generation === generation && this.#state !== \"stopped\";",
    "this.#startupFailed = this.#initialized === undefined;",
    'outcome: "unknown", automaticReplay: false,',
    "if (!this.#connecting) this.#scheduleReconnect();",
    "client.dispose();",
    "return this.#retiring ?? Promise.resolve();",
)
RECONNECT_FRAGMENTS = (
    "if (!this.options.supportsReconnect || !retry || this.#state !== \"disconnected\" || this.#retryTimer ||\n      this.#reconnectAttempt >= retry.maxAttempts) return;",
    "Math.min((retry.initialDelayMs ?? 500) * 2 ** this.#reconnectAttempt, retry.maxDelayMs ?? 10_000)",
    "this.#reconnectAttempt += 1;",
    "this.#retryTimer.unref();",
    "this.#broadcastStatus();",
)
APPROVAL_FRAGMENTS = (
    'if (request.method !== "item/tool/requestApproval") {',
    'client.respondError(request.id, { code: -32601, message: "Method not found" }); return;',
    'typeof params.consequential !== "boolean" || this.#approvals.has(params.approvalId)) {',
    'client.respondError(request.id, { code: -32602, message: "Invalid approval request" }); return;',
    "const configuredTimeout = this.#initialized?.approval?.timeoutSeconds;",
    "configuredTimeout > 0 ? configuredTimeout : 300;",
    "let deadline = Date.now() + timeoutSeconds * 1_000;",
    "if (typeof params.deadline === \"string\") {",
    "if (Number.isFinite(parsed)) deadline = parsed;",
    "deadline = params.deadline > 1e12 ? params.deadline : params.deadline * 1_000;",
    'client.respondError(request.id, { code: -32001, message: "Approval expired" }); return;',
    "Math.min(deadline - Date.now(), 2_147_483_647)",
    "timer.unref();",
    'this.#emit({ jsonrpc: "2.0", method: "approval/requested", params });',
    'const finishedTurn = typeof params.status === "string" &&',
    '["completed", "interrupted", "blocked", "error"].includes(params.status);',
    'const completedTurn = notification.method === "thread/updated" && params.threadId === route.threadId &&',
    "(params.threadId === undefined || params.threadId === route.threadId)",
    'const completedToolCall = notification.method === "toolCall/completed" &&',
    'const decidedApproval = notification.method === "approval/decided" &&',
    'client.respondError(route.requestId, { code: -32001, message: "Approval no longer active" });',
)
MANAGER_FRAGMENTS = (
    "if (this.#hosts.has(options.hostId)) throw new Error(\"harness host already registered\");",
    'if (!host) throw new Error("unknown harness host");',
    "list(): HarnessConnectionStatus[] { return [...this.#hosts.values()].map((host) => host.status()); }",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_host_connection() -> int:
    source = _read(HOST)
    checked = 0
    for fragments in (STATE_FRAGMENTS, READY_FRAGMENTS, REQUEST_FRAGMENTS,
                      LIFECYCLE_FRAGMENTS, RECONNECT_FRAGMENTS, APPROVAL_FRAGMENTS,
                      MANAGER_FRAGMENTS):
        checked += _expect(fragments, source, HOST)
    # 反向断言：内核同名通知不得被当成断开，状态不得用 String() 宽松归一化。
    if "String(params.status)" in source:
        raise ValueError(f"{HOST} 不得把畸形状态宽松转成合法值")
    if "automaticReplay: true" in source:
        raise ValueError(f"{HOST} 不得自动重放未确认的请求")
    if "this.#approvals.clear();" not in source:
        raise ValueError(f"{HOST} 必须清理审批路由")
    return checked + 1


def main() -> int:
    try:
        checked = check_host_connection()
    except ValueError as error:
        print(f"宿主连接核对失败，{error}", file=sys.stderr)
        return 2
    print(f"宿主连接一致：{checked} 项代际、重连与审批防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
