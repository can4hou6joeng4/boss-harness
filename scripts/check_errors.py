#!/usr/bin/env python3
"""核对模型错误的溢出分类、重试提示与传输诊断边界。

errors.py 是可信 provider 错误边界：只有精确的 OpenAI code、有界 llama.cpp /
LiteLLM 文本与 Anthropic 带数字的 prompt 拒绝才算上下文溢出；配额耗尽不可重试，
未知 429 保持未知；传输诊断只输出固定标签与白名单 errno。任一放宽都会把普通
失败误判为可恢复溢出，或把供应商原文带进诊断，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/errors.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

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


def check_errors() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
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
    return checked + 1


def main() -> int:
    try:
        checked = check_errors()
    except ValueError as error:
        print(f"模型错误分类核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型错误分类一致：{checked} 项溢出、重试与传输防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
