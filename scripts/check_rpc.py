#!/usr/bin/env python3
"""核对 JSON-RPC 帧解析、错误脱敏与响应降级边界。

rpc.py 是进程边界：帧必须在派发前严格解码，OSError 不得回显本机路径，异常消息
经凭据脱敏后才进入 stderr 与响应，编码失败不得重跑 handler。任一放宽都会把
本机信息写进协议帧或让一帧坏请求退出内核，因此先静态固定，再用内存流与合成帧
实际执行帧解析、错误文案、派发与降级路径。
"""

from __future__ import annotations

import contextlib
import errno
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/rpc.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

import boss_harness.rpc as rpc_module  # noqa: E402

from boss_harness.rpc import (  # noqa: E402
    MAX_FRAME_BYTES,
    FrameTooLargeError,
    JsonRpcServer,
    RpcError,
    _decode_json_frame,
    describe_failure,
)

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"JSON-RPC 行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(action, message: str, label: str) -> int:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(
                f"JSON-RPC 行为变化 {label} 错误信息：期望包含 {message!r}，实际 {error}") from None
        return 1
    raise ValueError(f"JSON-RPC 行为变化 {label} 必须被拒绝")


def _expect_raises(action, kind, label: str):
    try:
        action()
    except kind as error:
        return error
    except Exception as error:
        raise ValueError(
            f"JSON-RPC 行为变化 {label} 异常类型：期望 {kind.__name__}，"
            f"实际 {type(error).__name__}: {error}") from None
    raise ValueError(f"JSON-RPC 行为变化 {label} 必须抛出 {kind.__name__}")


def _raising(error: Exception):
    def handler(params):
        raise error
    return handler


class _BinaryOut:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()
        self.text = 0

    def write(self, text: str) -> int:
        self.text += 1
        return len(text)

    def flush(self) -> None:
        pass


def _server() -> tuple[JsonRpcServer, io.StringIO]:
    server = JsonRpcServer()
    out = io.StringIO()
    server._out = out
    return server, out


def _frames(out: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in out.getvalue().splitlines() if line]


def _dispatch(server: JsonRpcServer, out: io.StringIO, frame: dict) -> list[dict]:
    with contextlib.redirect_stderr(io.StringIO()):
        server._dispatch(frame)
    return _frames(out)


def _behavior_checks() -> int:
    checked = 0
    # 帧解析：严格 JSON 才进入派发。
    checked += _expect_value(
        _decode_json_frame('{"jsonrpc":"2.0","id":1,"method":"m","params":{"a":[1,true,null,"x"]}}'),
        {"jsonrpc": "2.0", "id": 1, "method": "m",
         "params": {"a": [1, True, None, "x"]}},
        "合法帧")
    for label, raw in (
            ("坏 JSON", '{"a":1'),
            ("重复键", '{"a":1,"a":2}'),
            ("NaN", '{"a":NaN}'),
            ("Infinity", '{"a":Infinity}'),
            ("负 Infinity", '{"a":-Infinity}'),
            ("非有限浮点", '{"a":1e999}'),
            ("孤立代理项", '{"a":"\\ud800"}'),
            ("尾随内容", '{"a":1} x')):
        checked += _expect_error(lambda raw=raw: _decode_json_frame(raw), "无效的 JSON 帧", label)
    checked += _expect_value(_decode_json_frame("[1,2]"), [1, 2], "顶层数组")
    checked += _expect_value(_decode_json_frame('{"a":"中文"}'), {"a": "中文"}, "非 ASCII 字符串")
    nested64 = '{"a":' * 64 + "1" + "}" * 64
    checked += _expect_value(_decode_json_frame(nested64), json.loads(nested64), "深度边界 64")
    nested65 = '{"a":' * 65 + "1" + "}" * 65
    checked += _expect_error(lambda: _decode_json_frame(nested65), "无效的 JSON 帧", "深度边界 65")
    # 错误文案：带文件名的 OSError 只保留原因，不回显本机路径。
    checked += _expect_value(
        describe_failure(OSError(errno.ENOENT, "x", "/private/tmp/secret.jsonl")),
        "本地文件或目录不存在（ENOENT），操作未完成。", "缺失路径脱敏")
    checked += _expect_value(
        describe_failure(OSError(errno.EACCES, "x", "/private/tmp/secret.jsonl")),
        "本地文件权限不足（EACCES），操作未完成。", "权限原因")
    checked += _expect_value(
        describe_failure(OSError(9999, "x", "/private/tmp/secret.jsonl")),
        "本地文件操作失败，操作未完成。", "未知 errno")
    checked += _expect_value(describe_failure(OSError("磁盘不可用")), "磁盘不可用", "无文件名 OSError")
    checked += _expect_value(describe_failure(ValueError("普通失败")), "普通失败", "普通异常")
    checked += _expect_value(
        "/private/tmp" in describe_failure(OSError(errno.ENOENT, "x", "/private/tmp/secret.jsonl")),
        False, "路径不回显")
    # 派发：固定错误码、分类与脱敏。
    server, out = _server()
    try:
        calls: list = []
        server.register("echo", lambda params: params)
        server.register("bad", _raising(ValueError("坏参数")))
        server.register("rpc", _raising(RpcError(1234, "自定义", {"k": 1})))
        server.register("secret", _raising(ValueError("token=sk-abcdef123456")))
        server.register("nan", lambda params: float("nan"))
        server.register("surrogate", lambda params: "\ud800")
        huge_calls: list = []
        server.register("huge", lambda params: huge_calls.append(params) or "x" * (MAX_FRAME_BYTES + 64))
        server.register("notjson", lambda params: object())
        server.register("big-error", _raising(ValueError("y" * (MAX_FRAME_BYTES + 64))))
        server.register("nan-data", _raising(RpcError(7, "带数据", float("nan"))))
        server.register("surrogate-error", _raising(ValueError("\ud800")))
        server.register("count", lambda params: calls.append(params) or float("nan"))
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": 1, "method": "echo", "params": {"a": 1}})
        checked += _expect_value(frames[-1], {"jsonrpc": "2.0", "id": 1, "result": {"a": 1}}, "请求响应")
        before = len(frames)
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "method": "echo", "params": {"a": 2}})
        checked += _expect_value(len(frames), before, "通知不响应")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "x", "method": "missing"})
        checked += _expect_value(frames[-1]["error"], {"code": -32601, "message": "未知方法"}, "未知方法")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "p", "method": "echo", "params": [1]})
        checked += _expect_value(
            frames[-1], {"jsonrpc": "2.0", "id": "p",
                         "error": {"code": -32602, "message": "params 必须是对象"}}, "非法 params")
        before = len(frames)
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "method": "echo", "params": [1]})
        checked += _expect_value(len(frames), before, "通知的非法 params 不响应")
        frames = _dispatch(server, out, {"id": 2, "method": "echo"})
        checked += _expect_value(
            frames[-1]["error"], {"code": -32600, "message": "无效的 JSON-RPC 请求"}, "无效版本")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": 3, "method": 1})
        checked += _expect_value(
            frames[-1]["error"], {"code": -32600, "message": "请求 method 或 id 无效"}, "非法 method")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": True, "method": "echo"})
        checked += _expect_value(
            frames[-1]["error"], {"code": -32600, "message": "请求 method 或 id 无效"}, "非法 id")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            server._dispatch({"jsonrpc": "2.0", "id": "b", "method": "bad", "params": {}})
            server._dispatch({"jsonrpc": "2.0", "id": "r", "method": "rpc", "params": {}})
            server._dispatch({"jsonrpc": "2.0", "id": "s", "method": "secret", "params": {}})
        frames = _frames(out)
        checked += _expect_value(
            frames[-3], {"jsonrpc": "2.0", "id": "b",
                         "error": {"code": -32602, "message": "坏参数"}}, "ValueError 分类")
        checked += _expect_value(
            frames[-2]["error"], {"code": 1234, "message": "自定义", "data": {"k": 1}}, "RpcError 编码")
        checked += _expect_value(
            frames[-1]["error"], {"code": -32602, "message": "token=<redacted>"}, "响应脱敏")
        errors = err.getvalue()
        checked += _expect_value("[harness] bad: 坏参数" in errors, True, "stderr 诊断")
        checked += _expect_value("sk-abcdef123456" in errors, False, "stderr 脱敏")
        seen: list[str] = []
        server.before_dispatch = seen.append
        _dispatch(server, out, {"jsonrpc": "2.0", "id": 4, "method": "echo", "params": {}})
        checked += _expect_value(seen, ["echo"], "派发前置回调")
        server.before_dispatch = _raising(RuntimeError("前置失败"))
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": 5, "method": "echo", "params": {}})
        checked += _expect_value(
            frames[-1]["error"], {"code": -32603, "message": "前置失败"}, "前置失败分类")
        server.before_dispatch = None
        # 降级：handler 已执行，结果无法编码时不重跑。
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "n", "method": "nan", "params": {}})
        checked += _expect_value(
            frames[-1]["error"],
            {"code": -32603, "message": "处理结果无法编码为有效的 JSON-RPC 响应",
             "data": {"code": "RESPONSE_INVALID"}}, "NaN 结果降级")
        for label, method in (("代理项结果降级", "surrogate"), ("不可序列化结果降级", "notjson")):
            frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": method, "method": method, "params": {}})
            checked += _expect_value(frames[-1]["error"]["data"], {"code": "RESPONSE_INVALID"}, label)
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "h", "method": "huge", "params": {}})
        checked += _expect_value(
            frames[-1]["error"],
            {"code": -32010, "message": "响应超过协议帧限制，请使用分页或结果分块读取",
             "data": {"code": "RESPONSE_TOO_LARGE"}}, "超大结果降级")
        checked += _expect_value(huge_calls, [{}], "超大结果不重跑")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "big", "method": "big-error", "params": {}})
        checked += _expect_value(
            frames[-1]["error"]["data"], {"code": "RESPONSE_TOO_LARGE"}, "超大错误降级")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "nd", "method": "nan-data", "params": {}})
        checked += _expect_value(frames[-1]["error"]["data"], {"code": "RESPONSE_INVALID"}, "非法 data 降级")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "se", "method": "surrogate-error", "params": {}})
        checked += _expect_value(frames[-1]["error"]["data"], {"code": "RESPONSE_INVALID"}, "代理项错误降级")
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": "c", "method": "count", "params": {}})
        checked += _expect_value(frames[-1]["error"]["data"], {"code": "RESPONSE_INVALID"}, "计数降级")
        checked += _expect_value(calls, [{}], "handler 只执行一次")
        huge_id = "x" * (MAX_FRAME_BYTES + 64)
        frames = _dispatch(server, out, {"jsonrpc": "2.0", "id": huge_id, "method": "echo", "params": {}})
        checked += _expect_value(frames[-1]["id"], None, "超大 id 回退")
        checked += _expect_value(
            frames[-1]["error"]["data"], {"code": "RESPONSE_TOO_LARGE"}, "超大 id 错误码")
    finally:
        server.close()
    # 写出：字节流优先、通知白名单、超限与关闭。
    server, out = _server()
    try:
        server.register("echo", lambda params: params)
        binary = _BinaryOut()
        server._out = binary
        with contextlib.redirect_stderr(io.StringIO()):
            server._dispatch({"jsonrpc": "2.0", "id": 1, "method": "echo", "params": {"中": 1}})
        raw = binary.buffer.getvalue()
        checked += _expect_value(raw.endswith(b"\n"), True, "字节帧换行")
        checked += _expect_value(
            json.loads(raw.decode("utf-8")),
            {"jsonrpc": "2.0", "id": 1, "result": {"中": 1}}, "字节帧 UTF-8")
        checked += _expect_value(binary.text, 0, "字节流优先")
        server._out = out
        server.opt_out_notifications = frozenset({"quiet"})
        server.notify("quiet", {"a": 1})
        checked += _expect_value(len(_frames(out)), 0, "白名单通知不写出")
        server.notify("loud", {"a": 2})
        server.notify("empty")
        frames = _frames(out)
        checked += _expect_value(
            frames[0], {"jsonrpc": "2.0", "method": "loud", "params": {"a": 2}}, "通知帧")
        checked += _expect_value(frames[1], {"jsonrpc": "2.0", "method": "empty"}, "无参数通知")
        _expect_raises(
            lambda: server._write({"jsonrpc": "2.0", "id": 1,
                                   "result": "x" * (MAX_FRAME_BYTES + 64)}),
            FrameTooLargeError, "超大帧")
        checked += 1
        checked += _expect_value(len(_frames(out)), 2, "超大帧不写出")
        server.close()
        _expect_raises(lambda: server.respond(1, 1), ConnectionError, "关闭后写出")
        checked += 1
    finally:
        server.close()
    # 请求响应的关联、形状拒绝与关闭取消。
    server, out = _server()
    try:
        request = server.request("approval", {"ask": 1}, timeout=30)
        frames = _frames(out)
        checked += _expect_value(frames[0]["method"], "approval", "请求方法")
        checked += _expect_value(frames[0]["params"], {"ask": 1}, "请求参数")
        checked += _expect_value(frames[0]["id"].startswith("server-"), True, "请求编号前缀")
        _dispatch(server, out, {"jsonrpc": "2.0", "id": request.id, "result": {"ok": True}})
        checked += _expect_value(request.future.result(timeout=1), {"ok": True}, "响应关联")
        error_request = server.request("approval", {"ask": 2}, timeout=30)
        _dispatch(server, out, {"jsonrpc": "2.0", "id": error_request.id,
                                "error": {"code": 9, "message": "拒绝"}})
        error = _expect_raises(lambda: error_request.future.result(timeout=1), RpcError, "错误响应")
        checked += _expect_value(error.code, -32001, "错误响应码")
        checked += _expect_value(error.data, {"code": 9, "message": "拒绝"}, "错误响应数据")
        malformed = server.request("approval", {"ask": 3}, timeout=30)
        _dispatch(server, out, {"jsonrpc": "2.0", "id": malformed.id, "result": 1, "error": {"code": 1}})
        checked += _expect_value(malformed.future.done(), False, "形状拒绝")
        checked += _expect_value(server.cancel_request(malformed.id), True, "取消在途请求")
        checked += _expect_value(
            str(malformed.future.exception(timeout=1)), "请求已取消", "取消异常")
        checked += _expect_value(server.cancel_request("server-missing"), False, "取消未知请求")
        pending = server.request("approval", {"ask": 4}, timeout=30)
        server.close()
        checked += _expect_value(
            str(pending.future.exception(timeout=1)), "客户端连接已断开", "关闭取消在途")
        _expect_raises(lambda: server.request("approval", {}, timeout=30), ConnectionError, "关闭后请求")
        checked += 1
    finally:
        server.close()
    # 计时器启动失败必须 fail closed：写出请求但不留等待者。
    server, out = _server()
    real_timer = rpc_module.threading.Timer

    class FailingTimer:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("计时器失败")

        def cancel(self) -> None:
            pass

    rpc_module.threading.Timer = FailingTimer
    try:
        failed = server.request("approval", {}, timeout=30)
    finally:
        rpc_module.threading.Timer = real_timer
    checked += _expect_value(len(_frames(out)), 1, "计时器失败仍写出请求")
    checked += _expect_value(
        str(failed.future.exception(timeout=1)), "客户端请求计时器未能启动", "计时器失败 fail closed")
    checked += _expect_value(server._pending, {}, "计时器失败不留等待者")
    server.close()
    # 读取循环：空行跳过、坏帧继续、缺 LF 有序停止。
    server, out = _server()
    server.register("echo", lambda params: params)
    saved_stdin, saved_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(
        '\nnot json\n{"jsonrpc":"2.0","id":1,"method":"echo","params":{"a":1}}\n{"partial":')
    sys.stdout = out
    try:
        server.serve_forever()
    finally:
        sys.stdin, sys.stdout = saved_stdin, saved_stdout
    frames = _frames(out)
    checked += _expect_value(frames[0]["error"], {"code": -32700, "message": "无效的 JSON 帧"}, "坏帧继续")
    checked += _expect_value(
        frames[1], {"jsonrpc": "2.0", "id": 1, "result": {"a": 1}}, "坏帧后继续派发")
    checked += _expect_value(
        frames[2]["error"], {"code": -32600, "message": "协议帧过大或缺少 LF 终止符"}, "缺 LF 有序停止")
    checked += _expect_value(server._closed, True, "读取结束后关闭")
    return checked


def main() -> int:
    try:
        checked = check_rpc()
        scenarios = _behavior_checks()
    except ValueError as error:
        print(f"JSON-RPC 传输核对失败，{error}", file=sys.stderr)
        return 2
    print(f"JSON-RPC 传输一致：{checked} 项帧、脱敏与降级防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
