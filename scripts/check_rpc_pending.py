#!/usr/bin/env python3
"""核对服务端发起请求的锁边界与响应降级顺序。

`JsonRpcServer.request` / `cancel_request` / `close` / `_receive_response` 管理
内核发起的客户端请求（审批等）。`pending` 注册必须在写出之前、`_write` 失败
必须取消并重抛、计时器启动失败必须 fail closed；`Future` 的完成与 `Timer`
的取消必须在 `_pending_lock` 之外触发，否则完成回调再次进入 server 会死锁；
`close` 在锁内取快照、锁外逐个取消。`_dispatch` 的错误帧与成功帧各自降级为
`RESPONSE_TOO_LARGE` / `RESPONSE_INVALID`，带 id 回退到无 id，且绝不重跑 handler。
这里按方法切片固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/rpc.py"

REQUEST_ORDER = (
    "def request(self, method: str, params: dict[str, Any], *, timeout: float = 300) -> ServerRequest:",
    'request_id = "server-" + uuid.uuid4().hex',
    "future: Future = Future()",
    "def expire() -> None:",
    'self.cancel_request(request_id, TimeoutError("客户端请求已过期"))',
    "timer = threading.Timer(timeout, expire)",
    "timer.daemon = True",
    "with self._pending_lock:",
    "if self._closed:",
    'raise ConnectionError("连接已关闭")',
    "self._pending[request_id] = (future, timer)",
    'self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})',
    "except Exception as exc:",
    "self.cancel_request(request_id, exc)",
    "timer.start()",
    "except Exception:",
    'self.cancel_request(request_id, TimeoutError("客户端请求计时器未能启动"))',
    "return ServerRequest(request_id, future)",
)
CANCEL_ORDER = (
    "def cancel_request(self, request_id: str, error: Exception | None = None) -> bool:",
    "with self._pending_lock:",
    "pending = self._pending.pop(request_id, None)",
    "if pending is None:",
    "return False",
    "future, timer = pending",
    "timer.cancel()",
    "if not future.done():",
    'future.set_exception(error or ConnectionError("请求已取消"))',
    "return True",
)
CLOSE_ORDER = (
    "def close(self) -> None:",
    "with self._pending_lock:",
    "self._closed = True",
    "ids = tuple(self._pending)",
    "for request_id in ids:",
    'self.cancel_request(request_id, ConnectionError("客户端连接已断开"))',
)
RECEIVE_ORDER = (
    "def _receive_response(self, message: dict[str, Any]) -> None:",
    'request_id = message.get("id")',
    'if not isinstance(request_id, str) or ("result" in message) == ("error" in message):',
    "return",
    "with self._pending_lock:",
    "pending = self._pending.pop(request_id, None)",
    "if pending is None:",
    "return",
    "future, timer = pending",
    "timer.cancel()",
    "if future.done():",
    "return",
    'if "error" in message:',
    'future.set_exception(RpcError(-32001, "客户端未完成请求", message["error"]))',
    'future.set_result(message["result"])',
)
TOO_LARGE_ORDER = (
    "def _respond_too_large(self, request_id: Any) -> None:",
    'message = "响应超过协议帧限制，请使用分页或结果分块读取"',
    'data = {"code": "RESPONSE_TOO_LARGE"}',
    "self.respond_error(request_id, -32010, message, data)",
    "except (FrameTooLargeError, UnicodeEncodeError):",
    "self.respond_error(None, -32010, message, data)",
)
INVALID_ORDER = (
    "def _respond_invalid(self, request_id: Any) -> None:",
    'message = "处理结果无法编码为有效的 JSON-RPC 响应"',
    'data = {"code": "RESPONSE_INVALID"}',
    "self.respond_error(request_id, -32603, message, data)",
    "except (FrameTooLargeError, UnicodeEncodeError):",
    "self.respond_error(None, -32603, message, data)",
    "except (FrameTooLargeError, UnicodeEncodeError):",
    "pass",
)
DISPATCH_ORDER = (
    "def _dispatch(self, message: Any) -> None:",
    'if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":',
    'self.respond_error(None, -32600, "无效的 JSON-RPC 请求")',
    'if "method" not in message and "id" in message:',
    "self._receive_response(message)",
    'if not isinstance(method, str) or (has_id and type(request_id) not in (str, int)):',
    'self.respond_error(None, -32600, "请求 method 或 id 无效")',
    'if message.get("params") is not None and not isinstance(message["params"], dict):',
    'self.respond_error(request_id, -32602, "params 必须是对象")',
    'self.respond_error(None, -32602, "params 必须是对象")',
    "if self.before_dispatch is not None:",
    "self.before_dispatch(method)",
    "if handler is None:",
    'raise RpcError(-32601, "未知方法")',
    'result = handler(message.get("params"))',
    "safe_message = redact_secrets(describe_failure(exc))",
    'print(f"[harness] {method}: {safe_message}", file=sys.stderr)',
    "code = exc.code if isinstance(exc, RpcError) else (-32602 if isinstance(exc, ValueError) else -32603)",
    "self.respond_error(request_id, code, safe_message, exc.data if isinstance(exc, RpcError) else None)",
    "self._respond_too_large(request_id)",
    "self._respond_invalid(request_id)",
    "self.respond(request_id, result)",
    "self._respond_too_large(request_id)",
    "self._respond_invalid(request_id)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "JsonRpcServer":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 JsonRpcServer.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_rpc_pending() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    request = _method(tree, source, "request")
    cancel = _method(tree, source, "cancel_request")
    close = _method(tree, source, "close")
    receive = _method(tree, source, "_receive_response")
    too_large = _method(tree, source, "_respond_too_large")
    invalid = _method(tree, source, "_respond_invalid")
    dispatch = _method(tree, source, "_dispatch")
    checked = _ordered(REQUEST_ORDER, request, MODULE)
    checked += _ordered(CANCEL_ORDER, cancel, MODULE)
    checked += _ordered(CLOSE_ORDER, close, MODULE)
    checked += _ordered(RECEIVE_ORDER, receive, MODULE)
    checked += _ordered(TOO_LARGE_ORDER, too_large, MODULE)
    checked += _ordered(INVALID_ORDER, invalid, MODULE)
    checked += _ordered(DISPATCH_ORDER, dispatch, MODULE)
    # 注册锁只覆盖关闭检查与 pending 登记；写出必须在锁外。
    if request.count("with self._pending_lock:") != 1:
        raise ValueError(f"{MODULE} 的 pending 注册必须只加一次锁")
    checked += 1
    if request.count('self._pending[request_id] = (future, timer)\n        try:') != 1:
        raise ValueError(f"{MODULE} 的写出不得在 pending 注册锁内")
    checked += 1
    if request.index("self._pending[request_id] = (future, timer)") > request.index("self._write("):
        raise ValueError(f"{MODULE} 的 pending 必须先登记再写出")
    checked += 1
    if request.count("self.cancel_request(request_id, exc)") != 1:
        raise ValueError(f"{MODULE} 的写出失败必须取消等待者")
    checked += 1
    if "\n            raise\n        try:" not in request:
        raise ValueError(f"{MODULE} 的写出失败必须重新抛出")
    checked += 1
    if request.count("timer.daemon = True") != 1 or request.index("timer.daemon = True") > request.index("timer.start()"):
        raise ValueError(f"{MODULE} 的计时器必须为守护线程并先设置后启动")
    checked += 1
    # 取消：锁内只 pop，Timer 与 Future 在锁外处理。
    if cancel.count("with self._pending_lock:") != 1:
        raise ValueError(f"{MODULE} 的取消必须只加一次锁")
    checked += 1
    if "            pending = self._pending.pop(request_id, None)\n        if pending is None:" not in cancel:
        raise ValueError(f"{MODULE} 的取消必须在锁内取出后离开锁")
    checked += 1
    if "\n        timer.cancel()" not in cancel or "\n        if not future.done():\n            future.set_exception" not in cancel:
        raise ValueError(f"{MODULE} 的取消必须在锁外结束计时器并完成 Future")
    checked += 1
    if cancel.count("future.set_exception(") != 1:
        raise ValueError(f"{MODULE} 的取消只能完成一次 Future")
    checked += 1
    # 关闭：锁内取快照，锁外逐个取消。
    if close.count("with self._pending_lock:") != 1:
        raise ValueError(f"{MODULE} 的关闭必须只加一次锁")
    checked += 1
    if "            self._closed = True\n            ids = tuple(self._pending)\n        for request_id in ids:\n            self.cancel_request" not in close:
        raise ValueError(f"{MODULE} 的关闭必须先取快照再锁外取消")
    checked += 1
    # 响应：锁内只 pop，计时器与 Future 在锁外处理。
    if receive.count("with self._pending_lock:") != 1:
        raise ValueError(f"{MODULE} 的响应接收必须只加一次锁")
    checked += 1
    if "\n        timer.cancel()" not in receive or "\n        if future.done():" not in receive:
        raise ValueError(f"{MODULE} 的响应接收必须在锁外结束计时器")
    checked += 1
    if receive.count("future.set_exception(") != 1 or receive.count("future.set_result(") != 1:
        raise ValueError(f"{MODULE} 的响应接收必须区分错误与结果")
    checked += 1
    if '"result" in message) == ("error" in message)' not in receive:
        raise ValueError(f"{MODULE} 的响应必须恰好携带 result 或 error 之一")
    checked += 1
    # 降级：带 id 失败后回退到无 id 的有界错误。
    if too_large.count("self.respond_error(None, -32010, message, data)") != 1:
        raise ValueError(f"{MODULE} 的 RESPONSE_TOO_LARGE 必须有无 id 回退")
    checked += 1
    if invalid.count("self.respond_error(None, -32603, message, data)") != 1 or invalid.count("pass") != 1:
        raise ValueError(f"{MODULE} 的 RESPONSE_INVALID 必须有二层回退")
    checked += 1
    # 派发：错误帧与成功帧各自降级，handler 只运行一次。
    if dispatch.count("self._respond_too_large(request_id)") != 2:
        raise ValueError(f"{MODULE} 的错误帧与成功帧都必须降级 RESPONSE_TOO_LARGE")
    checked += 1
    if dispatch.count("self._respond_invalid(request_id)") != 2:
        raise ValueError(f"{MODULE} 的错误帧与成功帧都必须降级 RESPONSE_INVALID")
    checked += 1
    if dispatch.count('result = handler(message.get("params"))') != 1:
        raise ValueError(f"{MODULE} 的 handler 只能运行一次")
    checked += 1
    if dispatch.count("if has_id:") != 3:
        raise ValueError(f"{MODULE} 的三条回复路径都只在有 id 时回复")
    checked += 1
    if dispatch.count("print(") != 1 or dispatch.index("print(") > dispatch.index("self.respond_error(request_id, code, safe_message"):
        raise ValueError(f"{MODULE} 的诊断必须在错误响应之前写入 stderr")
    checked += 1
    if dispatch.count("self._receive_response(message)") != 1:
        raise ValueError(f"{MODULE} 的响应消息必须先于方法分发处理")
    checked += 1
    # 服务端请求形状固定为 id + future 的冻结记录。
    if "@dataclass(frozen=True)\nclass ServerRequest:\n    id: str\n    future: Future" not in source:
        raise ValueError(f"{MODULE} 的 ServerRequest 必须是冻结的 id / future 记录")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_rpc_pending()
    except (ValueError, SyntaxError) as error:
        print(f"服务端请求核对失败，{error}", file=sys.stderr)
        return 2
    print(f"服务端请求一致：{checked} 项锁边界与响应降级校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
