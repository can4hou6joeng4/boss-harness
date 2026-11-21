#!/usr/bin/env python3
"""核对条目正文的传输降级与分页边界。

损坏记录里的孤立代理项、非有限浮点与超深结构必须降级为可传输值，否则整次
响应会变成 RESPONSE_INVALID；分页游标绑定线程、条目、字段、摘要与快照，避免
跨版本拼接。阈值或归属判定被删改不会触发构建失败，因此用静态检查固定，再用
行为对照覆盖降级、摘要、省略与游标归属。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/item_content.py"
DESKTOP_GUIDE = "docs/DESKTOP_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.item_content import (  # noqa: E402
    MAX_ITEM_CONTENT_CHARS,
    _WIRE_DEPTH_PLACEHOLDER,
    item_content_reference,
    project_item_content,
    read_item_content,
    wire_text,
    wire_value,
)
from boss_harness.rpc import RpcError  # noqa: E402

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"条目正文行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, error: type[BaseException], label: str) -> int:
    try:
        call()
    except error:
        return 1
    raise ValueError(f"条目正文行为变化 {label}：未抛出 {error.__name__}")


def _cursor(payload) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "ic1_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _behavior_checks() -> int:
    checked = 0
    # wire_text：无代理项时原样返回同一对象；孤立代理项替换为 U+FFFD 且长度不变。
    plain = "普通文本"
    checked += _expect_value(wire_text(plain) is plain, True, "普通文本原样")
    broken = "a\ud800b"
    checked += _expect_value((wire_text(broken), len(wire_text(broken))), ("a�b", 3),
                             "孤立代理项替换")
    checked += _expect_value(wire_text(chr(0xD83D) + chr(0xDE00)), "��",
                             "代理对逐项替换")

    # wire_value：递归清理字符串与键，深度与非有限浮点降级，其余容器原样。
    checked += _expect_value(wire_value({"k\ud800": ["x\ud800", 1, True, None, 2.5]}),
                             {"k�": ["x�", 1, True, None, 2.5]}, "递归清理")
    checked += _expect_value((wire_value(float("inf")), wire_value(float("nan"))), (None, None),
                             "非有限浮点降级")
    nested = "leaf"
    for _ in range(70):
        nested = [nested]
    probe = wire_value(nested)
    while isinstance(probe, list):
        probe = probe[0]
    checked += _expect_value(probe, _WIRE_DEPTH_PLACEHOLDER, "深度占位")
    checked += _expect_value(wire_value(("a",)), ("a",), "元组原样")

    # 引用：字段固定，摘要与字节按传输文本计，字符数按原文计，分块与整体一致。
    checked += _expect_value(
        item_content_reference("t", "i", "text", "abc"),
        {"threadId": "t", "itemId": "i", "part": "text", "encoding": "text",
         "sha256": hashlib.sha256(b"abc").hexdigest(), "byteLength": 3,
         "characterLength": 3}, "引用字段")
    checked += _expect_value(
        item_content_reference("t", "i", "text", "a", "s" * 32).get("snapshotId"), "s" * 32,
        "快照引用")
    reference = item_content_reference("t", "i", "text", "\ud800")
    checked += _expect_value((reference["byteLength"], reference["characterLength"]), (3, 1),
                             "代理项字节计")
    big = "x" * 40_000
    checked += _expect_value(item_content_reference("t", "i", "text", big)["sha256"],
                             hashlib.sha256(big.encode("utf-8")).hexdigest(), "分块摘要一致")
    checked += _expect_error(lambda: item_content_reference("t", "i", "other", "a"), ValueError,
                             "字段白名单")
    checked += _expect_error(lambda: item_content_reference("t", "i", "text", 1), ValueError,
                             "正文类型")

    # 投影：非正文条目原样复制；内联文本清理并清除旧引用；超长字段省略并附引用。
    operand = {"kind": "toolCall", "id": "x", "text": "raw\ud800"}
    projected = project_item_content("t", operand)
    checked += _expect_value((projected, projected is operand), (operand, False),
                             "非正文条目复制")
    short = {"kind": "agentMessage", "id": "m1", "text": "hi\ud800",
             "textOmitted": True, "textRef": {"stale": True}}
    projected = project_item_content("t", short)
    checked += _expect_value((projected["text"], "textOmitted" in projected,
                              "textRef" in projected), ("hi�", False, False),
                             "内联清理与旧引用清除")
    long_item = {"kind": "agentMessage", "id": "m2", "text": "x" * 70_000,
                 "thinking": "y" * 70_000}
    projected = project_item_content("t", long_item)
    checked += _expect_value(
        ("text" in projected, projected.get("textOmitted"), projected["textRef"]["byteLength"],
         "thinking" in projected, projected.get("thinkingOmitted")),
        (False, True, 70_000, False, True), "超长省略")

    # 读取：分页往返、末页游标为空，正文按传输文本清理。
    text = "abcdef"
    item = {"kind": "agentMessage", "id": "m3", "text": text, "thinking": text}
    reference = item_content_reference("t", "m3", "text", text)
    args = {"thread_id": "t", "item": item, "part": "text", "sha256": reference["sha256"]}
    page = read_item_content(**args, limit=2)
    checked += _expect_value((page["text"], page["offset"], page["nextCursor"] is not None,
                              page["contentRef"]["sha256"]),
                             ("ab", 0, True, reference["sha256"]), "首页")
    second = read_item_content(**args, limit=2, cursor=page["nextCursor"])
    checked += _expect_value((second["text"], second["offset"]), ("cd", 2), "续读")
    third = read_item_content(**args, limit=2, cursor=second["nextCursor"])
    checked += _expect_value((third["text"], third["nextCursor"]), ("ef", None), "末页")
    checked += _expect_value(read_item_content(**args, limit=10)["text"], text, "整页")
    dirty = {"kind": "agentMessage", "id": "m5", "text": broken}
    dirty_ref = item_content_reference("t", "m5", "text", broken)
    checked += _expect_value(
        read_item_content("t", dirty, part="text", sha256=dirty_ref["sha256"])["text"],
        "a�b", "读取清理")

    # limit 边界：非整数（含布尔）与越界拒绝，1 与上限接受。
    for value in (0, MAX_ITEM_CONTENT_CHARS + 1, True, 1.5):
        checked += _expect_error(lambda value=value: read_item_content(**args, limit=value),
                                 ValueError, f"limit 拒绝 {value!r}")
    checked += _expect_value(read_item_content(**args, limit=1)["text"], "a", "limit 下限")
    checked += _expect_value(read_item_content(**args, limit=MAX_ITEM_CONTENT_CHARS)["text"],
                             text, "limit 上限")

    # 归属与格式校验：条目类型、字段、摘要与快照格式。
    checked += _expect_error(
        lambda: read_item_content("t", {"kind": "toolCall", "id": "m", "text": "x"},
                                  part="text", sha256=reference["sha256"]),
        ValueError, "条目类型")
    checked += _expect_error(lambda: read_item_content(**dict(args, part="other")), ValueError,
                             "读取字段白名单")
    checked += _expect_error(
        lambda: read_item_content("t", {"kind": "agentMessage", "id": "m", "text": 1},
                                  part="text", sha256=reference["sha256"]),
        ValueError, "读取正文类型")
    for value in ("A" * 64, "a" * 63):
        checked += _expect_error(lambda value=value: read_item_content(**dict(args, sha256=value)),
                                 ValueError, f"摘要格式 {value[:4]}")
    for value in ("A" * 32, "z" * 32):
        checked += _expect_error(
            lambda value=value: read_item_content(**dict(args, snapshot_id=value)),
            ValueError, f"快照格式 {value[:4]}")
    checked += _expect_value(
        read_item_content(**dict(args, snapshot_id="a" * 32))["contentRef"]["snapshotId"],
        "a" * 32, "合法快照")

    # 过期引用：固定错误码与当前引用，便于客户端重新读取。
    try:
        read_item_content(**dict(args, sha256="0" * 64))
    except RpcError as error:
        stale = (error.code, error.data["code"], error.data["currentRef"]["sha256"])
    else:
        stale = None
    checked += _expect_value(stale, (-32011, "STALE_CONTENT", reference["sha256"]),
                             "过期引用")

    # 游标归属：绑定线程、条目、字段与摘要，格式错误与越界统一拒绝。
    good = _cursor(["t", "m3", "text", reference["sha256"], None, 1])
    checked += _expect_value(read_item_content(**args, limit=2, cursor=good)["offset"], 1,
                             "游标偏移")
    for label, cursor in (
        ("跨线程", _cursor(["other", "m3", "text", reference["sha256"], None, 1])),
        ("跨条目", _cursor(["t", "m4", "text", reference["sha256"], None, 1])),
        ("跨字段", _cursor(["t", "m3", "thinking", reference["sha256"], None, 1])),
        ("跨摘要", _cursor(["t", "m3", "text", "0" * 64, None, 1])),
        ("越界", _cursor(["t", "m3", "text", reference["sha256"], None, 6])),
        ("负数", _cursor(["t", "m3", "text", reference["sha256"], None, -1])),
        ("非整数", _cursor(["t", "m3", "text", reference["sha256"], None, "1"])),
        ("元素不足", _cursor(["t", "m3", "text", reference["sha256"], None])),
        ("前缀错误", "xx1_" + good[4:]),
        ("非法编码", "ic1_!!!not-base64"),
        ("超长", "ic1_" + "a" * 2100),
    ):
        checked += _expect_error(
            lambda cursor=cursor: read_item_content(**args, limit=2, cursor=cursor),
            ValueError, label)
    checked += _expect_error(
        lambda: read_item_content(**dict(args, part="thinking"), limit=2, cursor=good),
        ValueError, "游标跨字段读取")
    return checked


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
    checked += _behavior_checks()
    return checked + 2


def main() -> int:
    try:
        checked = check_item_content()
    except (ValueError, RpcError) as error:
        print(f"条目正文核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目正文一致：{checked} 项降级、分页与行为校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
