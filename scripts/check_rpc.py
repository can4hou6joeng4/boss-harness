#!/usr/bin/env python3
"""核对 JSON-RPC 帧解析、错误脱敏与响应降级边界。

rpc.py 是进程边界：帧必须在派发前严格解码，OSError 不得回显本机路径，异常消息
经凭据脱敏后才进入 stderr 与响应，编码失败不得重跑 handler。任一放宽都会把
本机信息写进协议帧或让一帧坏请求退出内核，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/rpc.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

CONSTANT_FRAGMENTS = (
    "MAX_FRAME_BYTES = 8 * 1024 * 1024\n",
    "MAX_JSON_DEPTH = 64\n",
    "Handler = Callable[[dict[str, Any] | None], Any]\n",
)
REASON_FRAGMENTS = (
    # 错误文本只保留可行动原因：带文件名的 OSError 不回显本机路径。
    'if isinstance(exc, OSError) and exc.filename is not None:',
    'name = errno.errorcode.get(exc.errno) if exc.errno is not None else None',
    'reason = _OS_ERROR_REASONS.get(exc.errno, "本地文件操作失败")',
    'return f"{reason}{suffix}，操作未完成。"',
    "return str(exc)",
)
JSON_FRAGMENTS = (
    "def _reject_json_constant(_: str) -> None:",
    "raise ValueError(\"JSON 数值必须有限\")",
    "if not math.isfinite(parsed):",
    "def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:",
    "raise ValueError(\"JSON 对象包含重复键\")",
    "if depth > MAX_JSON_DEPTH:",
    "if any(0xD800 <= ord(char) <= 0xDFFF for char in value):",
    "reconfigure(encoding=\"utf-8\", errors=\"surrogateescape\")",
    "except (AttributeError, OSError, ValueError):",
    "value = json.loads(raw, object_pairs_hook=_unique_json_object,",
    "parse_constant=_reject_json_constant,",
    "parse_float=_finite_json_float)",
    "except (json.JSONDecodeError, ValueError, RecursionError):",
    "raise ValueError(\"无效的 JSON 帧\") from None",
)
ERROR_FRAGMENTS = (
    "class RpcError(Exception):",
    "self.code, self.data = code, data",
    "class FrameTooLargeError(ValueError):",
)
SERVER_FRAGMENTS = (
    "self._write_lock = threading.Lock()",
    "self._pending_lock = threading.Lock()",
    "self._pending: dict[str, tuple[Future, threading.Timer]] = {}",
    "self._closed = False",
    "self.opt_out_notifications: frozenset[str] = frozenset()",
    "self.before_dispatch: Callable[[str], None] | None = None",
)
REQUEST_FRAGMENTS = (
    "if method in self.opt_out_notifications:",
    'request_id = "server-" + uuid.uuid4().hex',
    "timer.daemon = True",
    "if self._closed:",
    'raise ConnectionError("连接已关闭")',
    "self._pending[request_id] = (future, timer)",
    "self.cancel_request(request_id, exc)",
    # 计时器启动失败必须 fail closed：不留等待者，也不放行无期限审批。
    'self.cancel_request(request_id, TimeoutError("客户端请求计时器未能启动"))',
    "if not future.done():",
    'future.set_exception(error or ConnectionError("请求已取消"))',
    'self.cancel_request(request_id, ConnectionError("客户端连接已断开"))',
)
WRITE_FRAGMENTS = (
    'encoded = json.dumps(frame, ensure_ascii=False, allow_nan=False) + "\\n"',
    'raw = encoded.encode("utf-8")',
    "if len(raw) > MAX_FRAME_BYTES:",
    'raise FrameTooLargeError("协议帧超过大小限制")',
    'buffer = getattr(self._out, "buffer", None)',
    "buffer.write(raw)",
    "buffer.flush()",
    "self._out.write(encoded)",
)
RESPONSE_FRAGMENTS = (
    '"code": "RESPONSE_TOO_LARGE"',
    "self.respond_error(request_id, -32010, message, data)",
    "self.respond_error(None, -32010, message, data)",
    '"code": "RESPONSE_INVALID"',
    "self.respond_error(request_id, -32603, message, data)",
    "self.respond_error(None, -32603, message, data)",
    "except (FrameTooLargeError, UnicodeEncodeError):",
)
SERVE_FRAGMENTS = (
    "    def serve_forever(self) -> None:\n        _enable_surrogateescape_stdin()",
    "raw = sys.stdin.readline(MAX_FRAME_BYTES + 1)",
    "except UnicodeDecodeError:",
    'self._protocol_error(-32700, "无效的 JSON 帧")',
    'encoded = raw.encode("utf-8", errors="surrogateescape")',
    'self._protocol_error(-32600, "协议帧过大或缺少 LF 终止符")',
    'raw = encoded.decode("utf-8")',
    "if not raw.strip():",
    "message = _decode_json_frame(raw)",
    "self._dispatch(message)",
    "self.close()",
)
RECEIVE_FRAGMENTS = (
    'if not isinstance(request_id, str) or ("result" in message) == ("error" in message):',
    "pending = self._pending.pop(request_id, None)",
    "timer.cancel()",
    "if future.done():",
    'future.set_exception(RpcError(-32001, "客户端未完成请求", message["error"]))',
    "future.set_result(message[\"result\"])",
)
DISPATCH_FRAGMENTS = (
    'if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":',
    'self.respond_error(None, -32600, "无效的 JSON-RPC 请求")',
    'if "method" not in message and "id" in message:',
    "self._receive_response(message)",
    'if not isinstance(method, str) or (has_id and type(request_id) not in (str, int)):',
    'self.respond_error(None, -32600, "请求 method 或 id 无效")',
    'if message.get("params") is not None and not isinstance(message["params"], dict):',
    'self.respond_error(request_id, -32602, "params 必须是对象")',
    'self.respond_error(None, -32602, "params 必须是对象")',
    'raise RpcError(-32601, "未知方法")',
    "result = handler(message.get(\"params\"))",
    "safe_message = redact_secrets(describe_failure(exc))",
    "code = exc.code if isinstance(exc, RpcError) else (-32602 if isinstance(exc, ValueError) else -32603)",
    "except FrameTooLargeError:",
    "self._respond_too_large(request_id)",
    "except (RecursionError, TypeError, UnicodeEncodeError, ValueError):",
    "self._respond_invalid(request_id)",
    "self.respond(request_id, result)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "无效 JSON、坏 UTF-8、重复键、非有限数值或超深结构返回 `-32700` 协议错误，并继续读取后续完整帧"),
    (TECHNICAL_REFERENCE, "handler 可能已经产生外部或持久副作用，响应编码失败时不能重跑"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_rpc() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(REASON_FRAGMENTS, module, MODULE)
    checked += _expect(JSON_FRAGMENTS, module, MODULE)
    checked += _expect(ERROR_FRAGMENTS, module, MODULE)
    checked += _expect(SERVER_FRAGMENTS, module, MODULE)
    checked += _expect(REQUEST_FRAGMENTS, module, MODULE)
    checked += _expect(WRITE_FRAGMENTS, module, MODULE)
    checked += _expect(RESPONSE_FRAGMENTS, module, MODULE)
    checked += _expect(SERVE_FRAGMENTS, module, MODULE)
    checked += _expect(RECEIVE_FRAGMENTS, module, MODULE)
    checked += _expect(DISPATCH_FRAGMENTS, module, MODULE)
    # 帧解析：钩子全部就位后才解码并统一收敛为固定错误。
    checked += _ordered(
        (
            "object_pairs_hook=_unique_json_object,",
            "parse_constant=_reject_json_constant,",
            "parse_float=_finite_json_float)",
            "_validate_json_value(value)",
            "except (json.JSONDecodeError, ValueError, RecursionError):",
        ),
        module,
        MODULE,
    )
    # 写出顺序：编码 → 编码字节 → 帧上限 → 持锁 → 关闭检查 → 写入。
    checked += _ordered(
        (
            'encoded = json.dumps(frame, ensure_ascii=False, allow_nan=False) + "\\n"',
            'raw = encoded.encode("utf-8")',
            "if len(raw) > MAX_FRAME_BYTES:",
            "with self._write_lock:\n            if self._closed:\n                raise ConnectionError(\"连接已关闭\")",
            "buffer.write(raw)",
        ),
        module,
        MODULE,
    )
    # 读取循环：先重配置 → 有界 readline → framing → 严格解码 → JSON 解析 → 派发。
    checked += _ordered(
        (
            "    def serve_forever(self) -> None:\n        _enable_surrogateescape_stdin()",
            "raw = sys.stdin.readline(MAX_FRAME_BYTES + 1)",
            'encoded = raw.encode("utf-8", errors="surrogateescape")',
            "if len(encoded) > MAX_FRAME_BYTES or not raw.endswith(\"\\n\"):",
            'raw = encoded.decode("utf-8")',
            "message = _decode_json_frame(raw)",
            "self._dispatch(message)",
        ),
        module,
        MODULE,
    )
    # 唯一允许的 print 必须写 stderr；协议帧不得混入诊断。
    if module.count("print(") != module.count("file=sys.stderr"):
        raise ValueError(f"{MODULE} 的诊断只能写入 stderr")
    if "allow_nan=True" in module:
        raise ValueError(f"{MODULE} 不得写出非有限数值")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_rpc()
    except ValueError as error:
        print(f"JSON-RPC 传输核对失败，{error}", file=sys.stderr)
        return 2
    print(f"JSON-RPC 传输一致：{checked} 项帧、脱敏与降级防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
