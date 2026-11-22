#!/usr/bin/env python3
"""核对模型错误的溢出分类、重试提示与传输诊断边界。

errors.py 是可信 provider 错误边界：只有精确的 OpenAI code、有界 llama.cpp /
LiteLLM 文本与 Anthropic 带数字的 prompt 拒绝才算上下文溢出；配额耗尽不可重试，
未知 429 保持未知；传输诊断只输出固定标签与白名单 errno。任一放宽都会把普通
失败误判为可恢复溢出，或把供应商原文带进诊断，因此静态固定，并直接构造错误
载荷与异常链，对照溢出、重试与诊断的实际判定。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import errno
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/errors.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.errors import (  # noqa: E402
    _error_payload,
    _is_overflow_source,
    _is_zhipu_usage_limit,
    _llama_context_exhausted,
    _litellm_context_window_exceeded,
    _proxy_body_too_large,
    _retryable_hint,
    _safe_provider_code,
    _transport_diagnostics,
    _valid_source,
    anthropic_error_info,
    openai_error_info,
    transport_diagnostic,
)
from boss_harness.models.types import ModelErrorInfo  # noqa: E402

CONSTANT_FRAGMENTS = (
    r'_PROVIDER_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")',
    '_QUOTA_CODES = frozenset({"insufficient_quota", "billing_hard_limit_reached", "billing_error",',
    '"usage_limit_error", "credits_exhausted"})',
    '_TRANSIENT_CODES = frozenset({"rate_limit_exceeded", "rate_limit_error", "server_error",',
    '"service_unavailable_error", "overloaded_error"})',
    "_TRANSIENT_STATUSES = frozenset({408, 409, 500, 502, 503, 504})",
    "_MAX_LITELLM_ERROR_MESSAGE = 2048\n",
    "_MAX_PROXY_ERROR_MESSAGE = 512\n",
    r'r"prompt is too long:\s*([0-9]+) tokens\s*>\s*([0-9]+) maximum\.?"',
    r'r"context size has been exceeded\.?"',
    r'r"^litellm\.ContextWindowExceededError:.*?Context Window exceeded for given call\."',
    r'r".*?\bMax Input Tokens=([0-9]{1,12}),\s*Got=([0-9]{1,12})\b"',
    r'r"(?:request body|payload) too large\.?"',
)
PAYLOAD_FRAGMENTS = (
    'nested = _field(value, "error")',
    "return nested if nested is not None else value",
)
TRANSPORT_FRAGMENTS = (
    'for name in ("httpx", "httpx2"):',
    "classes.append(module.TransportError)",
    "if exc.name != name:",
    "SDK_TRANSPORT_ERRORS = _sdk_transport_errors()",
    "while current is not None and len(visited) < 8:",
    "for exception_type in type(current).__mro__:",
    "mapped = _TRANSPORT_CAUSE_BY_TYPE.get(exception_type.__name__)",
    "if code is None and isinstance(current, OSError):",
    "if isinstance(current, socket.gaierror):",
    "code = _TRANSPORT_SOCKET_CODES.get(error_number)",
    "error_name = errno.errorcode.get(error_number)",
    "if error_name in _TRANSPORT_ERRNO_CODES:",
    "linked = current.__cause__",
    "if linked is None and not current.__suppress_context__:",
    "linked = current.__context__",
    'cause = "unknown"',
    'return f"{label}（{info.transport_code}）"',
)
SOURCE_FRAGMENTS = (
    "def _valid_source(source: str, status_code: int | None) -> bool:",
    'if source == "http_error":',
    "return type(status_code) is int and 100 <= status_code <= 599",
    'if source == "stream_error":',
    "return status_code is None or (type(status_code) is int and status_code == 200)",
    'if source == "transport_error":',
    "return status_code is None",
)
CODE_FRAGMENTS = (
    "def _safe_provider_code(error: object) -> str | None:",
    'for field in ("code", "type"):',
    "if type(value) is str and _PROVIDER_CODE.fullmatch(value):",
    'if field == "code" and type(value) is int and value == 1308:',
    "return str(value)",
    "def _is_zhipu_usage_limit(error: object) -> bool:",
    'return (type(code) is str and code == "1308") or (type(code) is int and code == 1308)',
)
RETRY_FRAGMENTS = (
    "def _retryable_hint(error: object, status_code: int | None) -> bool | None:",
    "if _is_zhipu_usage_limit(error) or codes & _QUOTA_CODES:\n        return False",
    "if codes & _TRANSIENT_CODES or status_code in _TRANSIENT_STATUSES:\n        return True",
    "if status_code in {400, 401, 403}:\n        return False",
)
OVERFLOW_SOURCE_FRAGMENTS = (
    "def _is_overflow_source(source: str, status_code: int | None) -> bool:",
    "return type(status_code) is int and status_code == 400",
    'return source == "stream_error" and (status_code is None or status_code == 200)',
)
LLAMA_FRAGMENTS = (
    "def _llama_context_exhausted(error: object) -> bool:",
    "return (type(message) is str and len(message) <= 512\n",
    "            and _LLAMA_CONTEXT_EXHAUSTED.fullmatch(message.strip()) is not None)",
)
LITELLM_FRAGMENTS = (
    "def _litellm_context_window_exceeded(error: object) -> bool:",
    "if type(message) is not str or len(message) > _MAX_LITELLM_ERROR_MESSAGE:",
    "match = _LITELLM_CONTEXT_WINDOW.search(message)",
    "maximum, received = map(int, match.groups())",
    "return maximum > 0 and received > maximum",
)
PROXY_FRAGMENTS = (
    "def _proxy_body_too_large(error: object, *, source: str, status_code: int | None) -> bool:",
    'if source != "http_error" or status_code != 413:',
    "and _PROXY_BODY_TOO_LARGE.fullmatch(message.strip()) is not None)",
)
OPENAI_FRAGMENTS = (
    "def openai_error_info(error: object, *, source: ErrorSource,",
    'structured_overflow = type(raw_code) is str and raw_code == "context_length_exceeded"',
    "text_overflow = status_code in {400, 200} and _llama_context_exhausted(error)",
    'litellm_overflow = (source == "http_error" and status_code == 400',
    "proxy_body_overflow = _proxy_body_too_large(error, source=source, status_code=status_code)",
    "_is_overflow_source(source, status_code)",
    "and (structured_overflow or text_overflow or litellm_overflow)",
    ") or proxy_body_overflow",
    'code="CONTEXT_OVERFLOW" if overflow else None,',
    'transport_error) if source == "transport_error" else (None, None)',
    "retryable=retryable if retryable is not None else _retryable_hint(error, status_code)",
)
ANTHROPIC_FRAGMENTS = (
    "def anthropic_error_info(error: object, *, source: ErrorSource,",
    'and _field(payload, "type") == "invalid_request_error"',
    "and type(message) is str and len(message) <= 512):",
    "match = _ANTHROPIC_PROMPT_LIMIT.fullmatch(message.strip())",
    "actual, limit = map(int, match.groups())",
    "overflow = overflow or (limit > 0 and actual > limit)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "仅在 OpenAI 可信错误字段精确返回 `context_length_exceeded`"),
    (TECHNICAL_REFERENCE, "裸 HTTP 413、其他 413 消息、输出 `length`、限流、认证、连接错误、任意其他错误文字或超窗 usage 均不触发此恢复"),
    (TECHNICAL_REFERENCE, "错误记录不包含响应正文、请求、响应头或凭据"),
    (TECHNICAL_REFERENCE, "只有已知的临时限流/服务端错误才标记可重试，含义不明的 HTTP 429 保持未知"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型错误分类行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _chained(inner: BaseException) -> BaseException:
    outer = RuntimeError("outer")
    outer.__cause__ = inner
    return outer


def _suppressed(inner: BaseException) -> BaseException:
    outer = RuntimeError("outer")
    outer.__context__ = inner
    outer.__suppress_context__ = True
    return outer


def _deep_chain(depth: int) -> BaseException:
    error: BaseException = RuntimeError("leaf")
    for _ in range(depth - 1):
        error = _chained(error)
    return error


def _behavior_checks() -> int:
    checked = 0
    # 来源校验：HTTP 需 100–599 整数，流错误只允许缺失或 200，传输错误不得带状态码。
    for source, status, expected in (
        ("http_error", 400, True),
        ("http_error", 100, True),
        ("http_error", 599, True),
        ("http_error", 99, False),
        ("http_error", 600, False),
        ("http_error", None, False),
        ("http_error", "400", False),
        ("http_error", True, False),
        ("stream_error", None, True),
        ("stream_error", 200, True),
        ("stream_error", 201, False),
        ("transport_error", None, True),
        ("transport_error", 400, False),
        ("other", 400, False),
    ):
        checked += _expect_value(_valid_source(source, status), expected,
                                 f"来源 {source}/{status!r}")

    # provider code：code / type 依次取第一个白名单值，智谱整数 1308 单独放行。
    checked += _expect_value(_safe_provider_code({"code": "context_length_exceeded"}),
                             "context_length_exceeded", "provider code")
    checked += _expect_value(_safe_provider_code({"type": "rate_limit_error"}),
                             "rate_limit_error", "type 回退")
    checked += _expect_value(_safe_provider_code({"code": "bad code", "type": "server_error"}),
                             "server_error", "非法 code 回退")
    checked += _expect_value(_safe_provider_code({"code": "x" * 129, "type": "server_error"}),
                             "server_error", "超长 code 回退")
    checked += _expect_value(_safe_provider_code({"code": ".bad", "type": "server_error"}),
                             "server_error", "首字符非法回退")
    checked += _expect_value(_safe_provider_code({"code": 1308}), "1308", "智谱整数 code")
    checked += _expect_value(_safe_provider_code({"code": 1309}), None, "其他整数 code")
    checked += _expect_value(_safe_provider_code({"code": True}), None, "布尔 code")
    checked += _expect_value(_safe_provider_code({"error": {"code": "insufficient_quota"}}),
                             "insufficient_quota", "嵌套 error")
    checked += _expect_value(_safe_provider_code(SimpleNamespace(code="server_error")),
                             "server_error", "属性载荷")

    # 智谱 1308：字符串或整数且不夹带空白，浮点不算。
    for payload, expected in (
        ({"code": "1308"}, True),
        ({"code": 1308}, True),
        ({"code": "1308 "}, False),
        ({"code": 1308.0}, False),
        ({"error": {"code": 1308}}, True),
    ):
        checked += _expect_value(_is_zhipu_usage_limit(payload), expected,
                                 f"智谱配额 {payload!r}")

    # 重试提示：配额优先于临时错误，已知临时状态可重试，400/401/403 拒绝，裸 429 未知。
    for payload, status, expected in (
        ({"code": "insufficient_quota"}, 500, False),
        ({"code": 1308}, 500, False),
        ({"code": "server_error"}, 400, True),
        ({}, 500, True),
        ({}, 403, False),
        ({}, 429, None),
        ({}, 404, None),
        ({"code": "insufficient_quota", "type": "server_error"}, 500, False),
    ):
        checked += _expect_value(_retryable_hint(payload, status), expected,
                                 f"重试提示 {payload!r}/{status}")

    # 溢出来源：HTTP 仅 400，流错误缺失或 200，传输错误永不。
    for source, status, expected in (
        ("http_error", 400, True),
        ("http_error", 401, False),
        ("http_error", None, False),
        ("stream_error", None, True),
        ("stream_error", 200, True),
        ("stream_error", 201, False),
        ("transport_error", None, False),
    ):
        checked += _expect_value(_is_overflow_source(source, status), expected,
                                 f"溢出来源 {source}/{status!r}")

    # llama 文本：去掉首尾空白后完整匹配，限 512 字符且必须有界。
    for payload, expected in (
        ({"message": "Context size has been exceeded."}, True),
        ({"message": "  context size has been exceeded  "}, True),
        ({"message": "context size has been exceeded twice"}, False),
        ({"message": "context size has been exceeded." + " " * 490}, False),
        ({"message": 1}, False),
        ({"error": {"message": "context size has been exceeded"}}, True),
    ):
        checked += _expect_value(_llama_context_exhausted(payload), expected,
                                 f"llama 溢出 {payload!r}")

    # LiteLLM：长度上限、跨行匹配、最大值为正且收到值更大。
    litellm = ("litellm.ContextWindowExceededError: boom Context Window exceeded for given "
               "call. Max Input Tokens=8192, Got=9000")
    for message, expected in (
        (litellm, True),
        (litellm.replace("Got=9000", "Got=8192"), False),
        (litellm.replace("Tokens=8192", "Tokens=0").replace("Got=9000", "Got=1"), False),
        (litellm.replace(" Max Input", "\nMax Input"), True),
        (litellm.replace("Tokens=8192", "Tokens=1234567890123"), False),
        ("x" * 2049 + litellm, False),
    ):
        checked += _expect_value(_litellm_context_window_exceeded({"message": message}),
                                 expected, f"LiteLLM {message[:24]!r}")

    # 代理 413：仅 HTTP 413、完整匹配且不超过 512 字符。
    for payload, source, status, expected in (
        ({"message": "request body too large"}, "http_error", 413, True),
        ({"message": "Payload too large."}, "http_error", 413, True),
        ({"message": "  request body too large  "}, "http_error", 413, True),
        ({"message": "request body too large"}, "stream_error", 413, False),
        ({"message": "request body too large"}, "http_error", 400, False),
        ({"message": "request body too large now"}, "http_error", 413, False),
        ({"message": "request body too large" + "!" * 500}, "http_error", 413, False),
    ):
        checked += _expect_value(
            _proxy_body_too_large(payload, source=source, status_code=status), expected,
            f"代理 413 {payload!r}/{source}/{status}")

    # OpenAI 组合：结构化 / llama / LiteLLM / 代理 413，显式 retryable 覆盖提示。
    checked += _expect_value(openai_error_info({}, source="http_error"), None, "无状态码")
    checked += _expect_value(
        openai_error_info({}, source="transport_error", status_code=400), None,
        "传输带状态码")
    structured = openai_error_info({"code": "context_length_exceeded"},
                                   source="http_error", status_code=400)
    checked += _expect_value(
        (structured.provider, structured.source, structured.code, structured.status_code,
         structured.retryable),
        ("openai", "http_error", "CONTEXT_OVERFLOW", 400, False), "结构化溢出")
    checked += _expect_value(
        openai_error_info({"code": "context_length_exceeded"}, source="stream_error",
                          status_code=200).code, "CONTEXT_OVERFLOW", "流式结构化溢出")
    checked += _expect_value(
        openai_error_info({"code": "invalid_request_error"}, source="http_error",
                          status_code=400).code, None, "普通 400")
    checked += _expect_value(
        openai_error_info({"message": "context size has been exceeded"}, source="http_error",
                          status_code=400).code, "CONTEXT_OVERFLOW", "llama 文本溢出")
    checked += _expect_value(
        openai_error_info({"message": "context size has been exceeded"}, source="http_error",
                          status_code=500).code, None, "llama 仅 400")
    checked += _expect_value(
        openai_error_info({"message": litellm}, source="http_error", status_code=400).code,
        "CONTEXT_OVERFLOW", "LiteLLM 溢出")
    checked += _expect_value(
        openai_error_info({"message": litellm}, source="stream_error", status_code=200).code,
        None, "LiteLLM 仅 HTTP")
    checked += _expect_value(
        openai_error_info({"message": "payload too large"}, source="http_error",
                          status_code=413).code, "CONTEXT_OVERFLOW", "代理 413 溢出")
    checked += _expect_value(
        openai_error_info({"code": "insufficient_quota"}, source="http_error",
                          status_code=500, retryable=True).retryable, True, "显式放行重试")
    checked += _expect_value(
        openai_error_info({"code": "server_error"}, source="http_error",
                          status_code=500, retryable=False).retryable, False, "显式禁止重试")
    refused = openai_error_info({}, source="transport_error",
                                transport_error=ConnectionRefusedError(errno.ECONNREFUSED, "x"))
    checked += _expect_value((refused.transport_cause, refused.transport_code),
                             ("connect_error", "ECONNREFUSED"), "OpenAI 传输诊断")
    checked += _expect_value(transport_diagnostic(refused),
                             "连接建立失败（ECONNREFUSED）", "固定诊断文案")
    checked += _expect_value(
        openai_error_info({}, source="transport_error").transport_cause, None, "无传输异常")

    # Anthropic 组合：仅 invalid_request_error 的数字 prompt 拒绝算溢出，代理 413 同样生效。
    prompt = "prompt is too long: 210000 tokens > 200000 maximum."
    info = anthropic_error_info({"type": "invalid_request_error", "message": prompt},
                                source="http_error", status_code=400)
    checked += _expect_value(
        (info.provider, info.code, info.status_code, info.retryable),
        ("anthropic", "CONTEXT_OVERFLOW", 400, False), "Anthropic 溢出")
    checked += _expect_value(
        anthropic_error_info(
            {"type": "invalid_request_error",
             "message": "prompt is too long: 200000 tokens > 200000 maximum"},
            source="http_error", status_code=400).code, None, "达到上限不放行")
    checked += _expect_value(
        anthropic_error_info(
            {"type": "invalid_request_error",
             "message": "prompt is too long: 1 tokens > 0 maximum"},
            source="http_error", status_code=400).code, None, "零上限不放行")
    checked += _expect_value(
        anthropic_error_info({"type": "rate_limit_error", "message": prompt},
                             source="http_error", status_code=400).code, None, "类型不符")
    checked += _expect_value(
        anthropic_error_info({"type": "invalid_request_error", "message": prompt + " " * 500},
                             source="http_error", status_code=400).code, None, "超长消息")
    checked += _expect_value(
        anthropic_error_info({"message": "request body too large"}, source="http_error",
                             status_code=413).code, "CONTEXT_OVERFLOW", "Anthropic 代理 413")
    checked += _expect_value(
        anthropic_error_info({"type": "invalid_request_error", "message": prompt},
                             source="stream_error", status_code=None).code,
        "CONTEXT_OVERFLOW", "流式 Anthropic 溢出")
    checked += _expect_value(
        anthropic_error_info({"type": "invalid_request_error", "message": prompt},
                             source="http_error", status_code=400, retryable=True).retryable,
        True, "Anthropic 显式重试")
    reset = anthropic_error_info({}, source="transport_error",
                                 transport_error=ConnectionResetError(errno.ECONNRESET, "x"))
    checked += _expect_value((reset.transport_cause, reset.transport_code),
                             ("connection_error", "ECONNRESET"), "Anthropic 传输诊断")

    # 传输链：类型映射、白名单 errno、DNS 独立命名空间、因果链与抑制上下文。
    checked += _expect_value(_transport_diagnostics(None), (None, None), "无异常")
    checked += _expect_value(
        _transport_diagnostics(ConnectionRefusedError(errno.ECONNREFUSED, "x")),
        ("connect_error", "ECONNREFUSED"), "连接拒绝")
    checked += _expect_value(_transport_diagnostics(OSError(errno.ENOENT, "x")),
                             ("os_error", None), "非白名单 errno")
    checked += _expect_value(
        _transport_diagnostics(socket.gaierror(socket.EAI_NONAME, "x")),
        ("dns_error", "EAI_NONAME"), "DNS 命名空间")
    inner = ConnectionResetError(errno.ECONNRESET, "reset")
    checked += _expect_value(_transport_diagnostics(_chained(inner)),
                             ("connection_error", "ECONNRESET"), "因果链")
    checked += _expect_value(_transport_diagnostics(_suppressed(inner)), (None, None),
                             "抑制上下文")
    checked += _expect_value(_transport_diagnostics(_deep_chain(9)), ("unknown", None),
                             "过深因果链")
    looped = RuntimeError("loop")
    looped.__cause__ = looped
    checked += _expect_value(_transport_diagnostics(looped), (None, None), "自引用因果链")

    # 固定诊断：未知与缺失不输出成因，已知成因使用固定中文标签。
    checked += _expect_value(
        transport_diagnostic(ModelErrorInfo(provider="openai", source="transport_error")),
        None, "无诊断")
    checked += _expect_value(
        transport_diagnostic(ModelErrorInfo(provider="openai", source="transport_error",
                                            transport_cause="unknown")),
        "传输原因未识别", "未知诊断")
    checked += _expect_value(
        transport_diagnostic(ModelErrorInfo(provider="openai", source="transport_error",
                                            transport_cause="timeout")),
        "传输超时", "超时诊断")
    return checked


def _payload_checks() -> int:
    # 载荷投影：只有 error 为 None 时回退外层；假值与非字典载体都原样保留。
    checked = _expect_value(_error_payload({"error": {"code": "x"}}), {"code": "x"}, "嵌套字典")
    checked += _expect_value(
        _error_payload(SimpleNamespace(error=SimpleNamespace(code="x"))).code, "x", "嵌套对象")
    checked += _expect_value(_error_payload({"code": "x"}), {"code": "x"}, "扁平字典")
    flat = {"error": None, "code": "c"}
    checked += _expect_value(_error_payload(flat) is flat, True, "None 回退外层")
    checked += _expect_value(_error_payload({"error": 0}), 0, "零载荷")
    checked += _expect_value(_error_payload({"error": ""}), "", "空串载荷")
    checked += _expect_value((_error_payload("boom"), _error_payload(5), _error_payload(None)),
                             ("boom", 5, None), "标量与 None")
    return checked


def check_errors() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(PAYLOAD_FRAGMENTS, module, MODULE)
    checked += _expect(TRANSPORT_FRAGMENTS, module, MODULE)
    checked += _expect(SOURCE_FRAGMENTS, module, MODULE)
    checked += _expect(CODE_FRAGMENTS, module, MODULE)
    checked += _expect(RETRY_FRAGMENTS, module, MODULE)
    checked += _expect(OVERFLOW_SOURCE_FRAGMENTS, module, MODULE)
    checked += _expect(LLAMA_FRAGMENTS, module, MODULE)
    checked += _expect(LITELLM_FRAGMENTS, module, MODULE)
    checked += _expect(PROXY_FRAGMENTS, module, MODULE)
    checked += _expect(OPENAI_FRAGMENTS, module, MODULE)
    checked += _expect(ANTHROPIC_FRAGMENTS, module, MODULE)
    # 传输链：逐层身份去重 → 类型映射 → 白名单 errno → 因果链。
    checked += _ordered(
        (
            "if identity in visited:",
            "mapped = _TRANSPORT_CAUSE_BY_TYPE.get(exception_type.__name__)",
            "if error_name in _TRANSPORT_ERRNO_CODES:",
            "linked = current.__cause__",
        ),
        module,
        MODULE,
    )
    # LiteLLM：长度上限 → 匹配 → 数字比较。
    checked += _ordered(
        (
            "if type(message) is not str or len(message) > _MAX_LITELLM_ERROR_MESSAGE:",
            "match = _LITELLM_CONTEXT_WINDOW.search(message)",
            "maximum, received = map(int, match.groups())",
            "return maximum > 0 and received > maximum",
        ),
        module,
        MODULE,
    )
    # OpenAI 溢出：结构化 → llama → LiteLLM → 代理 413 → 组合。
    checked += _ordered(
        (
            "structured_overflow = type(raw_code) is str",
            "text_overflow = status_code in {400, 200}",
            "litellm_overflow = (source ==",
            "proxy_body_overflow = _proxy_body_too_large(",
            "and (structured_overflow or text_overflow or litellm_overflow)",
        ),
        module,
        MODULE,
    )
    # Anthropic 溢出：类型精确 → 有界文本 → 完整匹配 → 数字比较。
    checked += _ordered(
        (
            'and _field(payload, "type") == "invalid_request_error"',
            "and type(message) is str and len(message) <= 512):",
            "match = _ANTHROPIC_PROMPT_LIMIT.fullmatch(message.strip())",
            "overflow = overflow or (limit > 0 and actual > limit)",
        ),
        module,
        MODULE,
    )
    # 反向断言：精确匹配、有界 413 与不泄露原文。
    if "isinstance(raw_code, str)" in module:
        raise ValueError(f"{MODULE} 的结构化溢出必须使用精确类型判定")
    if "_LLAMA_CONTEXT_EXHAUSTED.search(" in module:
        raise ValueError(f"{MODULE} 的 llama 文本必须完整匹配")
    if "_ANTHROPIC_PROMPT_LIMIT.search(" in module:
        raise ValueError(f"{MODULE} 的 Anthropic 文本必须完整匹配")
    if "status_code != 413" not in module:
        raise ValueError(f"{MODULE} 的代理 413 分类必须锁定状态码")
    if "str(error)" in module or "repr(error)" in module:
        raise ValueError(f"{MODULE} 不得把异常原文写入诊断")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks() + _payload_checks()


def main() -> int:
    try:
        checked = check_errors()
    except (ValueError, OSError) as error:
        print(f"模型错误分类核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型错误分类一致：{checked} 项溢出、重试与传输校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
