#!/usr/bin/env python3
"""核对条目正文的传输降级与分页边界。

损坏记录里的孤立代理项、非有限浮点与超深结构必须降级为可传输值，否则整次
响应会变成 RESPONSE_INVALID；分页游标绑定线程、条目、字段、摘要与快照，避免
跨版本拼接。阈值或归属判定被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/item_content.py"
DESKTOP_GUIDE = "docs/DESKTOP_GUIDE.md"

CONSTANT_FRAGMENTS = (
    "INLINE_ITEM_CONTENT_BYTES = 64 * 1024",
    "DEFAULT_ITEM_CONTENT_CHARS = 16_384",
    "MAX_ITEM_CONTENT_CHARS = 32_768",
    "_WIRE_MAX_DEPTH = 64",
    '_WIRE_DEPTH_PLACEHOLDER = "[嵌套层级超出显示上限]"',
)
WIRE_FRAGMENTS = (
    "_REPLACEMENT = \"�\"",
    'if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):',
    "_REPLACEMENT if 0xD800 <= ord(char) <= 0xDFFF else char",
    "if isinstance(value, float) and not math.isfinite(value):",
    "if _depth > _WIRE_MAX_DEPTH:",
    "return _WIRE_DEPTH_PLACEHOLDER",
)
REFERENCE_FRAGMENTS = (
    "for offset in range(0, len(text), 16_384):",
    'encoded = wire_text(text[offset:offset + 16_384]).encode("utf-8")',
    "if len(text) <= INLINE_ITEM_CONTENT_BYTES and _utf8_size(text) <= INLINE_ITEM_CONTENT_BYTES:",
    'projected[part + "Omitted"] = True',
    'projected[part + "Ref"] = item_content_reference(',
)
READ_FRAGMENTS = (
    "if type(limit) is not int or not 1 <= limit <= MAX_ITEM_CONTENT_CHARS:",
    're.fullmatch(r"[a-f0-9]{64}", sha256)',
    're.fullmatch(r"[a-f0-9]{32}", snapshot_id)',
    'not cursor.startswith("ic1_") or len(cursor) > 2048',
    "value[:5] != expected",
    "not 0 <= value[5] < len(text)",
    '"nextCursor": next_cursor',
    '"STALE_CONTENT"',
)
DOC_FRAGMENTS = (
    (DESKTOP_GUIDE, "超过 64 KiB 的会话正文或思考字段"),
    (DESKTOP_GUIDE, "STALE_CONTENT"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_item_content() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(WIRE_FRAGMENTS, module, MODULE)
    checked += _expect(REFERENCE_FRAGMENTS, module, MODULE)
    checked += _expect(READ_FRAGMENTS, module, MODULE)
    # 内联正文必须先按替换后的文本写出，避免孤立代理项进入响应帧。
    if 'projected[part] = wire_text(text)' not in module:
        raise ValueError(f"{MODULE} 的内联正文必须经过 wire_text")
    # 分页游标只能由归属五元组与 offset 组成；多写字段会让旧客户端无法校验。
    if "payload = [thread_id, str(item[\"id\"]), part, sha256, snapshot_id, end]" not in module:
        raise ValueError(f"{MODULE} 的分页游标必须绑定线程、条目、字段、摘要与快照")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 2


def main() -> int:
    try:
        checked = check_item_content()
    except ValueError as error:
        print(f"条目正文核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目正文一致：{checked} 项降级、分页与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
