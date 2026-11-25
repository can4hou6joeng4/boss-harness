#!/usr/bin/env python3
"""核对 Node 侧进程传输客户端的帧、队列与关闭边界。

`packages/app-client/src/index.ts` 启动内核子进程并按 LF 分帧读写 JSON-RPC。
这里固定：禁止 shell、stdout / stderr / stdin 三条管道、8 MiB 单帧与 16 MiB
输入队列上限、UTF-8 严格解码、回包必须恰有 result 或 error、服务器请求
256 条待答上限、关闭先 stdin.end → SIGTERM → SIGKILL，以及诊断信息不带
帧内容。任一放宽都会让外壳对坏帧、超限或崩溃的处理失真。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CLIENT = "packages/app-client/src/index.ts"

SPAWN_FRAGMENTS = (
    "const GRACEFUL_CLOSE_TIMEOUT_MS = 2_500;",
    "const FORCE_KILL_TIMEOUT_MS = 1_000;",
    'return typeof value === "string" || (typeof value === "number" && Number.isSafeInteger(value));',
    'const code = typeof value?.code === "string" ? value.code : "";',
    'if (code && message && !message.includes(code)) return `${code}: ${message}`;',
    'return code || message || "unknown error";',
    'if (this.#child || this.#failure) throw new Error("harness client cannot be started twice");',
    "shell: false,",
    'stdio: ["pipe", "pipe", "pipe"],',
    'child.stdout.on("data", (chunk: Buffer) => this.#read(chunk));',
    'child.stderr.on("data", () => this.#diagnostic("backend diagnostic received"));',
    "check Python and dependencies",
    'child.stdin.on("drain", () => { this.#waitingForDrain = false; this.#flush(); });',
    'child.on("close", (code, signal) => {',
    "this.#resolveClosed?.(); this.#resolveClosed = null;",
)
REQUEST_FRAGMENTS = (
    "}, this.options.requestTimeoutMs ?? 30_000);",
    "timer.unref();",
    "this.#removeQueued(id);",
    "; outcome unknown, do not retry automatically`",
    'reject(error instanceof Error ? error : new Error("could not serialize harness request"));',
    'if (!this.#incoming.has(response.id)) throw new Error("server request is no longer pending");',
    "this.#enqueue(response);\n    this.#incoming.delete(response.id);",
    "this.#incoming.delete(id);",
)
FRAME_FRAGMENTS = (
    "const frame = `${JSON.stringify(payload)}\\n`;",
    "const bytes = Buffer.byteLength(frame);",
    'if (bytes > (this.options.maxFrameBytes ?? 8 * 1024 * 1024)) throw new Error("harness frame exceeds byte limit");',
    "if (this.#queuedBytes + bytes > (this.options.maxQueuedBytes ?? 16 * 1024 * 1024)) {",
    'throw new Error("harness input queue exceeds byte limit");',
    "this.#outgoing.push({ frame, bytes, id });",
    "this.#queuedBytes += bytes;",
    'if (!child.stdin.write(record.frame)) { this.#waitingForDrain = true; return; }',
    "harness input pipe closed (${spawnErrorDetail(error)})",
    "while ((end = this.#buffer.indexOf(10)) >= 0) {",
    "if (end > (this.options.maxFrameBytes ?? 8 * 1024 * 1024)) { this.#oversized(); return; }",
    'decoded = new TextDecoder("utf-8", { fatal: true }).decode(line);',
    'catch { this.#diagnostic("invalid UTF-8 protocol frame"); continue; }',
    "if (this.#buffer.length > (this.options.maxFrameBytes ?? 8 * 1024 * 1024)) this.#oversized();",
    'this.#fail(new Error("harness output frame exceeds byte limit"));\n    this.dispose();',
)
FAIL_FRAGMENTS = (
    "if (this.#failure) return;",
    "for (const pending of this.#pending.values()) { clearTimeout(pending.timer); pending.reject(reason); }",
    "this.#pending.clear(); this.#incoming.clear(); this.#outgoing = []; this.#queuedBytes = 0;",
    "this.#buffer = Buffer.alloc(0);",
    'this.#emit({ jsonrpc: "2.0", method: "harness/disconnected", params: { message: reason.message } });',
    'else process.stderr.write(`[harness] ${message}\\n`);',
    "child.stdin.end();",
    'child.kill("SIGTERM");',
    "if (child.exitCode === null && child.signalCode === null) {",
    'this.#diagnostic("harness did not stop after SIGTERM; sent SIGKILL");',
    '            child.kill("SIGKILL");',
)
LINE_FRAGMENTS = (
    'if (message.jsonrpc !== "2.0") return;',
    'if ("id" in message && validId(message.id) && !("method" in message)) {',
    'if (("result" in message) === ("error" in message)) {',
    'pending.reject(new HarnessRpcError({ code: -32603, message: "invalid harness response frame" }));',
    'typeof (message.error as JsonRpcError).code !== "number"',
    'pending.reject(new HarnessRpcError({ code: -32603, message: "invalid harness error frame" }));',
    "if (message.error) pending.reject(new HarnessRpcError(message.error as JsonRpcError));",
    "else pending.resolve(message.result);",
    'if (!("id" in message)) { this.#emit(value as JsonRpcNotification); return; }',
    "if (!validId(message.id) || this.#incoming.has(message.id)) return;",
    'if (this.#incoming.size >= 256) { this.#fail(new Error("too many pending server requests")); this.dispose(); return; }',
    'this.#rejectServerRequest(request.id, { code: -32601, message: "Method not found" }); return;',
    'this.#rejectServerRequest(request.id, { code: -32603, message: "Client request handler failed" });',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_client_transport() -> int:
    source = _read(CLIENT)
    checked = 0
    for fragments in (SPAWN_FRAGMENTS, REQUEST_FRAGMENTS, FRAME_FRAGMENTS,
                      FAIL_FRAGMENTS, LINE_FRAGMENTS):
        checked += _expect(fragments, source, CLIENT)
    # 反向断言：不得启用 shell、不得把帧内容写进诊断、不得直接打印未分类消息。
    for forbidden in ("shell: true", 'stdio: ["inherit"', "console.log(", "console.error("):
        if forbidden in source:
            raise ValueError(f"{CLIENT} 不得包含 {forbidden}")
    if 'this.#diagnostic("invalid protocol frame");' not in source:
        raise ValueError(f"{CLIENT} 的坏帧诊断必须是不带内容的固定文本")
    if "harness request timed out" not in source or "do not retry automatically" not in source:
        raise ValueError(f"{CLIENT} 的超时必须提示结果未知且不自动重试")
    return checked + 1


def main() -> int:
    try:
        checked = check_client_transport()
    except ValueError as error:
        print(f"进程传输客户端核对失败，{error}", file=sys.stderr)
        return 2
    print(f"进程传输客户端一致：{checked} 项分帧、队列与关闭防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
