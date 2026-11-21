#!/usr/bin/env python3
"""核对分页游标的编码与解码边界。

`_page_cursor` / `_read_page_cursor` 是会话列表、分支列表等所有分页读取共用的
游标编解码：游标必须带 `p1_` 前缀、长度受限、urlsafe base64 严格解码，载荷必须
恰好包含 `kind` / `scope` / `key` 且与本次查询完全一致，`key` 必须是列表；解码
失败（含深层嵌套触发的递归错误）统一报「游标无效」，范围不符单独报错。这里固定
这些规则，避免重构后游标跨查询复用、接受额外字段或被篡改输入打崩。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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
    'raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)',
    "payload = json.loads(raw)",
    "except (ValueError, UnicodeDecodeError, binascii.Error, RecursionError):",
    'raise ValueError("分页游标无效") from None',
    'if (not isinstance(payload, dict) or set(payload) != {"kind", "scope", "key"}',
    'or payload["kind"] != kind or payload["scope"] != scope',
    'or not isinstance(payload["key"], list)):',
    'raise ValueError("分页游标与查询范围不匹配")',
    'return payload["key"]',
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


def check_page_cursor() -> int:
    source = _read(SESSION)
    encode = _function(source, "def _page_cursor(")
    decode = _function(source, "def _read_page_cursor(")
    checked = _ordered(ENCODE_ORDER, encode, SESSION)
    checked += _ordered(DECODE_ORDER, decode, SESSION)
    # 严格 base64：必须拒绝非法字符并自行补齐，不能依赖宽松解码。
    if "validate=True" not in decode or 'altchars=b"-_"' not in decode:
        raise ValueError(f"{SESSION} 的游标解码必须使用严格 urlsafe base64")
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
    return checked


def main() -> int:
    try:
        checked = check_page_cursor()
    except ValueError as error:
        print(f"分页游标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分页游标一致：{checked} 项编码、严格解码与范围校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
