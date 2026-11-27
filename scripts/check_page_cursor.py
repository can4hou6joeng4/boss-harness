#!/usr/bin/env python3
"""核对分页游标的编码与解码边界。

`_page_cursor` / `_read_page_cursor` 是会话列表、分支列表等所有分页读取共用的
游标编解码：游标必须带 `p1_` 前缀、长度受限、经共享 urlsafe base64 解码器严格解码，载荷必须
恰好包含 `kind` / `scope` / `key` 且与本次查询完全一致，`key` 必须是列表；解码
失败（含深层嵌套触发的递归错误）统一报「游标无效」，范围不符单独报错。这里固定
这些规则，避免重构后游标跨查询复用、接受额外字段或被篡改输入打崩，并直接调用
编码与解码函数核对往返与错误收敛。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
ITEM_CONTENT = "harness/src/boss_harness/item_content.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import _page_cursor, _read_page_cursor  # noqa: E402

# 编码：固定三个字段 → p1_ 前缀 → urlsafe base64 去掉补齐符。
ENCODE_ORDER = (
    "def _page_cursor(kind: str, scope: dict, key: list) -> str:",
    'payload = _json({"kind": kind, "scope": scope, "key": key}).encode()',
    'return "p1_" + base64.urlsafe_b64encode(payload).decode().rstrip("=")',
)
# 解码：空游标 → 前缀与长度 → 严格 base64 → JSON → 四类异常统一报无效 →
# 字段集合 / 类型 / 范围匹配 → 返回 key。
DECODE_ORDER = (
    "def _read_page_cursor(cursor: str | None, kind: str, scope: dict) -> list | None:",
    "if cursor is None:",
    "return None",
    'if not isinstance(cursor, str) or not cursor.startswith("p1_") or len(cursor) > 4096:',
    'raise ValueError("分页游标无效")',
    "encoded = cursor[3:]",
    'raw = decode_cursor_base64(encoded)',
    "payload = json.loads(raw)",
    "except (ValueError, UnicodeDecodeError, binascii.Error, RecursionError):",
    'raise ValueError("分页游标无效") from None',
    'if (not isinstance(payload, dict) or set(payload) != {"kind", "scope", "key"}',
    'or payload["kind"] != kind or payload["scope"] != scope',
    'or not isinstance(payload["key"], list)):',
    'raise ValueError("分页游标与查询范围不匹配")',
    'return payload["key"]',
)
# 共享解码：游标生成时省略填充，解码器固定字符集与填充规则后统一补齐。
HELPER_ORDER = (
    "def decode_cursor_base64(encoded: str) -> bytes:",
    "_CURSOR_B64.fullmatch(encoded)",
    "data = encoded.rstrip(\"=\")",
    "padding = len(encoded) - len(data)",
    "required = (-len(data)) % 4",
    "if len(data) % 4 == 1 or padding not in (0, required):",
    'return base64.b64decode((data + "=" * required).encode("ascii"), altchars=b"-_", validate=True)',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _function(source: str, marker: str) -> str:
    start = source.index(marker)
    end = source.find("\n\ndef ", start + 1)
    return source[start:] if end < 0 else source[start:end]


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"分页游标行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"分页游标行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"分页游标行为变化 {label}：期望 ValueError")


def _raw_cursor(text: str) -> str:
    return "p1_" + base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _payload_cursor(payload: object) -> str:
    return _raw_cursor(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _behavior_checks() -> int:
    invalid = "分页游标无效"
    mismatch = "分页游标与查询范围不匹配"
    scope = {"session": "abc", "b": 2}
    key = ["k", 2, {"n": "值"}]
    cursor = _page_cursor("sessions", scope, key)
    checked = _expect_value(cursor.startswith("p1_"), True, "前缀")
    checked += _expect_value("=" in cursor, False, "无补齐符")
    checked += _expect_value(
        _read_page_cursor(cursor, "sessions", scope), key, "往返")
    checked += _expect_value(
        _read_page_cursor(cursor, "sessions", {"b": 2, "session": "abc"}), key,
        "范围键序无关")
    checked += _expect_value(
        _read_page_cursor(None, "sessions", scope), None, "空游标")
    checked += _expect_error(
        lambda: _read_page_cursor("", "sessions", scope), invalid, "空字符串")
    checked += _expect_error(
        lambda: _read_page_cursor(123, "sessions", scope), invalid, "非字符串")
    checked += _expect_error(
        lambda: _read_page_cursor("p0_" + cursor[3:], "sessions", scope), invalid,
        "错误前缀")
    checked += _expect_error(
        lambda: _read_page_cursor(cursor, "branches", scope), mismatch, "kind 不符")
    checked += _expect_error(
        lambda: _read_page_cursor(cursor, "SESSIONS", scope), mismatch, "kind 大小写")
    checked += _expect_error(
        lambda: _read_page_cursor(cursor, "sessions", {"session": "other"}),
        mismatch, "scope 不符")
    checked += _expect_error(
        lambda: _read_page_cursor("p1_!!!!", "sessions", scope), invalid,
        "非法 base64")
    checked += _expect_error(
        lambda: _read_page_cursor(_raw_cursor("{not json"), "sessions", scope),
        invalid, "坏 JSON")
    checked += _expect_error(
        lambda: _read_page_cursor(_payload_cursor([1]), "sessions", scope), mismatch,
        "顶层非对象")
    checked += _expect_error(
        lambda: _read_page_cursor(
            _payload_cursor({"kind": "sessions", "scope": scope}), "sessions", scope),
        mismatch, "缺 key")
    checked += _expect_error(
        lambda: _read_page_cursor(
            _payload_cursor({"kind": "sessions", "scope": scope, "key": [],
                             "extra": 1}), "sessions", scope),
        mismatch, "额外字段")
    checked += _expect_error(
        lambda: _read_page_cursor(
            _payload_cursor({"kind": "sessions", "scope": scope, "key": {}}),
            "sessions", scope),
        mismatch, "key 非列表")
    deep = "[" * 600 + "]" * 600
    checked += _expect_error(
        lambda: _read_page_cursor(_raw_cursor(deep), "sessions", scope), mismatch,
        "深层嵌套非对象")
    long_payload = json.dumps(
        {"kind": "sessions", "scope": scope, "key": [1]},
        ensure_ascii=False, separators=(",", ":")) + " " * 5000
    checked += _expect_error(
        lambda: _read_page_cursor(_raw_cursor(long_payload), "sessions", scope),
        invalid, "超长游标")
    # 共享解码器固定填充规则：规范补齐可接受，填充不足、多余填充、只有填充、非法
    # 长度与标准字母表在各版本上一致拒绝。
    padded = _payload_cursor({"kind": "sessions", "scope": scope, "key": [1]})
    checked += _expect_value(
        _read_page_cursor(padded + "==", "sessions", scope), [1], "规范补齐")
    checked += _expect_error(
        lambda: _read_page_cursor(padded + "=", "sessions", scope), invalid, "填充不足")
    checked += _expect_error(
        lambda: _read_page_cursor(padded + "===", "sessions", scope), invalid, "多余填充")
    checked += _expect_error(
        lambda: _read_page_cursor("p1_=", "sessions", scope), invalid, "只有填充")
    checked += _expect_error(
        lambda: _read_page_cursor("p1_A", "sessions", scope), invalid, "非法长度")
    checked += _expect_error(
        lambda: _read_page_cursor("p1_+w", "sessions", scope), invalid, "标准字母表")
    return checked


def check_page_cursor() -> int:
    source = _read(SESSION)
    helper = _function(_read(ITEM_CONTENT), "def decode_cursor_base64(")
    encode = _function(source, "def _page_cursor(")
    decode = _function(source, "def _read_page_cursor(")
    checked = _ordered(ENCODE_ORDER, encode, SESSION)
    checked += _ordered(DECODE_ORDER, decode, SESSION)
    checked += _ordered(HELPER_ORDER, helper, ITEM_CONTENT)
    # 严格 base64：调用点必须复用共享解码，不得自行调用宽松解码。
    if "decode_cursor_base64(encoded)" not in decode:
        raise ValueError(f"{SESSION} 的游标解码必须复用共享 urlsafe base64 解码")
    checked += 1
    if "validate=True" not in helper or 'altchars=b"-_"' not in helper:
        raise ValueError(f"{ITEM_CONTENT} 的游标解码必须使用严格 urlsafe base64")
    checked += 1
    # 四类异常必须统一收敛为游标无效，不能让内部异常逃逸成 -32603。
    for error in ("ValueError", "UnicodeDecodeError", "binascii.Error", "RecursionError"):
        if error not in decode:
            raise ValueError(f"{SESSION} 的游标解码必须捕获 {error}")
        checked += 1
    # 前缀与长度、字段集合与范围两类校验必须各自唯一。
    if decode.count('raise ValueError("分页游标无效")') != 2:
        raise ValueError(f"{SESSION} 的无效游标必须在两处统一报错")
    checked += 1
    if decode.count('raise ValueError("分页游标与查询范围不匹配")') != 1:
        raise ValueError(f"{SESSION} 的范围不符必须单独报错")
    checked += 1
    # 编码只写三个字段，不得带入额外键。
    if encode.count('{"kind": kind, "scope": scope, "key": key}') != 1:
        raise ValueError(f"{SESSION} 的游标编码必须恰好包含 kind / scope / key")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_page_cursor()
    except ValueError as error:
        print(f"分页游标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分页游标一致：{checked} 项编码、严格解码、范围校验与行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
