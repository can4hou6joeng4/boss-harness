#!/usr/bin/env python3
"""核对会话日志的编码、严格解码与有界快照。

`session.py` 的 JSONL 是会话事实源。单行必须 UTF-8 有界并以换行结尾；解码必须
拒绝重复键、非有限数值、孤立代理项与损坏行；会话头只允许出现在第 1 行；
快照与追加共享同一单行上限，末尾中断的残段只丢弃不固化。检查固定源码结构，
并用临时文件与内存流执行编码、解码、有界读取与边界场景。
"""

from __future__ import annotations

import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import (  # noqa: E402
    _complete_record_limit,
    _decode_session_record,
    _encode_session_line,
    _iter_bounded_lines,
    _iter_bounded_raw_lines_from_handle,
    _truncate_partial_record_tail,
)

CONSTANT_FRAGMENTS = (
    "MAX_SESSION_LINE_BYTES = 32 * 1024 * 1024",
    '_THREAD_ID = re.compile(r"[a-f0-9]{12}\\Z")',
    '_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\\Z")',
    '_EVENT_ID = re.compile(r"[a-f0-9]{32}\\Z")',
    '_ATTACHMENT_DIGEST = re.compile(r"[a-f0-9]{64}\\Z")',
    "_EVENT_READ_CHUNK_BYTES = 64 * 1024",
    "_MAX_ENTRIES_CACHE_THREADS = 4",
    '_TERMINAL = frozenset({"completed", "interrupted", "blocked", "error"})',
)
ENCODE_FRAGMENTS = (
    'return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)',
    'encoded = _json(value).encode("utf-8")',
    "if len(encoded) > maximum:",
    'raise ValueError(f"{label}单行超过大小限制")',
    'return encoded + b"\\n"',
)
DECODE_FRAGMENTS = (
    "record = json.loads(text, object_pairs_hook=_unique_json_object,",
    "parse_constant=_reject_json_constant, parse_float=_finite_json_float)",
    "_validate_json_unicode(record)",
    'raise ValueError(f"{label}第 {line_number} 行损坏，读取已停止") from None',
    "if not isinstance(record, dict):",
    'raise ValueError(f"{label}第 {line_number} 行格式无效，读取已停止")',
    "def _reject_json_constant(_: str) -> None:",
    "if key in result:",
    "parsed = float(value)",
    "if not math.isfinite(parsed):",
    'current.encode("utf-8")',
    "except UnicodeEncodeError:",
    "raise ValueError from None",
)
RECORD_FRAGMENTS = (
    'if record.get("type") == "session":',
    "if line_number == 1:\n            return None",
    'raise ValueError(f"会话日志第 {line_number} 行出现重复会话头，读取已停止")',
    'parent_id = record.get("parentId")',
    'if (not isinstance(record.get("type"), str) or not isinstance(record.get("id"), str)',
    'or not isinstance(record.get("timestamp"), str)\n            or (parent_id is not None and not isinstance(parent_id, str))):',
    'payload = record.get("payload")',
    "if not isinstance(payload, dict):",
)
READ_FRAGMENTS = (
    'def _iter_bounded_raw_lines_from_handle(handle, *, maximum: int, label: str = "JSONL",',
    "if byte_limit is not None and (type(byte_limit) is not int or byte_limit < 0):",
    'raise ValueError("JSONL 快照长度无效")',
    "chunk = handle.read(_EVENT_READ_CHUNK_BYTES)",
    "chunk = handle.read(min(_EVENT_READ_CHUNK_BYTES, remaining))",
    'raise ValueError(f"{label}快照读取不完整")',
    "if len(pending) > maximum:",
    "if len(line) > maximum:",
    "if pending and len(pending) > maximum:",
    "def _complete_record_limit(handle: io.BufferedReader, size: int) -> int:",
    "window = min(size, MAX_SESSION_LINE_BYTES + 1)",
    'boundary = handle.read(window).rfind(b"\\n")',
    'raise ValueError("会话日志末尾缺少完整记录边界")',
    "return size - window + boundary + 1",
    "def _truncate_partial_record_tail(descriptor: int, start: int) -> int:",
    'os.ftruncate(descriptor, truncated)\n        os.fsync(descriptor)',
    "return truncated",
    "data = handle.read(maximum + 1)",
    "if len(data) > maximum:",
    'raise ValueError(f"{label}超过大小限制")',
)
SNAPSHOT_FRAGMENTS = (
    "def __iter__(self):",
    "self._source.seek(0)",
    "byte_limit=self._size",
    "universal_newlines=True, byte_limit=self._size",
    "if not raw_line.strip():",
    "data = _decode_session_record(raw_line, line_number=line_number)",
    "if data is not None:",
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
        raise ValueError(f"会话日志行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        return _expect_value(str(error), message, label)
    raise ValueError(f"会话日志应拒绝 {label}")


def _expect_rejected(call, label: str) -> int:
    try:
        call()
    except ValueError:
        return 1
    raise ValueError(f"会话日志应拒绝 {label}")


def _behavior_checks() -> int:
    encoded = _encode_session_line({"消息": "中文"})
    checked = _expect_value(b"\\u" in encoded, False, "编码保留原始 Unicode")
    checked += _expect_value(encoded, '{"消息":"中文"}\n'.encode("utf-8"), "编码紧凑与换行")
    sample = {"k": "v"}
    sample_line = _encode_session_line(sample)
    checked += _expect_value(
        _encode_session_line(sample, maximum=len(sample_line) - 1), sample_line, "编码字节上限接受"
    )
    checked += _expect_error(
        lambda: _encode_session_line(sample, maximum=len(sample_line) - 2),
        "会话日志单行超过大小限制", "编码字节上限拒绝",
    )
    checked += _expect_error(
        lambda: _encode_session_line(sample, maximum=0, label="演示"), "演示单行超过大小限制", "编码标签"
    )
    checked += _expect_rejected(lambda: _encode_session_line({"value": float("nan")}), "非有限值编码")

    checked += _expect_value(_decode_session_record('{"type":"session"}', line_number=1), None, "首行会话头忽略")
    record = _decode_session_record(
        '{"type":"item","id":"e1","timestamp":"t","payload":{},"parentId":null}', line_number=3
    )
    checked += _expect_value((record["type"], record["id"]), ("item", "e1"), "普通记录返回")
    checked += _expect_error(
        lambda: _decode_session_record('{"type":"session"}', line_number=2),
        "会话日志第 2 行出现重复会话头，读取已停止", "重复会话头",
    )
    checked += _expect_error(
        lambda: _decode_session_record('{"a":1,"a":2}', line_number=1),
        "会话日志第 1 行损坏，读取已停止", "重复键",
    )
    checked += _expect_error(
        lambda: _decode_session_record('{"value":NaN}', line_number=1),
        "会话日志第 1 行损坏，读取已停止", "NaN 常量",
    )
    checked += _expect_error(
        lambda: _decode_session_record('{"value":1e999}', line_number=1),
        "会话日志第 1 行损坏，读取已停止", "非有限浮点",
    )
    checked += _expect_error(
        lambda: _decode_session_record('{"value":"\\ud800"}', line_number=1),
        "会话日志第 1 行损坏，读取已停止", "孤立代理项",
    )
    checked += _expect_error(
        lambda: _decode_session_record("[1]", line_number=1),
        "会话日志第 1 行格式无效，读取已停止", "非对象顶层",
    )
    checked += _expect_error(
        lambda: _decode_session_record('{"type":"item"}', line_number=1),
        "会话日志第 1 行格式无效，读取已停止", "缺少字段",
    )
    checked += _expect_error(
        lambda: _decode_session_record(
            '{"type":"item","id":"e1","timestamp":"t","payload":{},"parentId":1}', line_number=1
        ),
        "会话日志第 1 行格式无效，读取已停止", "parentId 类型",
    )
    checked += _expect_error(
        lambda: _decode_session_record(
            '{"type":"item","id":"e1","timestamp":"t","payload":[]}', line_number=1
        ),
        "会话日志第 1 行格式无效，读取已停止", "payload 类型",
    )
    checked += _expect_error(
        lambda: _decode_session_record(
            '{"type":1,"id":"e1","timestamp":"t","payload":{}}', line_number=1
        ),
        "会话日志第 1 行格式无效，读取已停止", "type 类型",
    )
    checked += _expect_error(
        lambda: _decode_session_record(
            '{"type":"item","id":1,"timestamp":"t","payload":{}}', line_number=1
        ),
        "会话日志第 1 行格式无效，读取已停止", "id 类型",
    )
    checked += _expect_error(
        lambda: _decode_session_record(
            '{"type":"item","id":"e1","timestamp":1,"payload":{}}', line_number=1
        ),
        "会话日志第 1 行格式无效，读取已停止", "timestamp 类型",
    )

    with TemporaryDirectory() as directory:
        root = Path(directory)
        complete = root / "complete.jsonl"
        complete.write_bytes(b'{"a":1}\n{"b":2}\n')
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(io.BytesIO(complete.read_bytes()), maximum=1_024)),
            [b'{"a":1}', b'{"b":2}'], "完整行产出",
        )
        partial = root / "partial.jsonl"
        partial.write_bytes(b'{"a":1}\n{"b":')
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(io.BytesIO(partial.read_bytes()), maximum=1_024)),
            [b'{"a":1}'], "末尾残段丢弃",
        )
        checked += _expect_error(
            lambda: list(_iter_bounded_raw_lines_from_handle(io.BytesIO(b'{"a":1}\n'), maximum=5)),
            "JSONL单行超过大小限制", "单行超限",
        )
        checked += _expect_error(
            lambda: list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n' + b"x" * 10), maximum=8)),
            "JSONL单行超过大小限制", "残段超限",
        )
        checked += _expect_error(
            lambda: list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n'), maximum=1_024, byte_limit=True)),
            "JSONL 快照长度无效", "快照长度类型",
        )
        checked += _expect_error(
            lambda: list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n'), maximum=1_024, byte_limit=9)),
            "JSONL快照读取不完整", "快照长度不足",
        )
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n'), maximum=1_024, byte_limit=8)),
            [b'{"a":1}'], "快照长度恰等接受",
        )
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\r\n{"b":2}\r'), maximum=1_024, universal_newlines=True)),
            [b'{"a":1}', b'{"b":2}'], "CRLF 分隔",
        )
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n'), maximum=1_024, byte_limit=0)),
            [], "零长度快照",
        )
        checked += _expect_error(
            lambda: list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(b'{"a":1}\n'), maximum=1_024, byte_limit=-1)),
            "JSONL 快照长度无效", "负快照长度",
        )
        long_line = b'{"blob":"' + b"a" * 70_000 + b'"}\n'
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(io.BytesIO(long_line), maximum=100_000)),
            [long_line[:-1]], "跨块长行",
        )
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(
                io.BytesIO(long_line), maximum=100_000, byte_limit=len(long_line) - 10)),
            [], "快照残段丢弃",
        )
        checked += _expect_value(
            list(_iter_bounded_raw_lines_from_handle(io.BytesIO(b"a\rb\n"), maximum=1_024)),
            [b"a\rb"], "裸回车保留",
        )
        cjk = root / "cjk.jsonl"
        cjk.write_bytes('{"消息":"中文"}\n\n{"b":2}\n'.encode("utf-8"))
        checked += _expect_value(
            list(_iter_bounded_lines(cjk, maximum=1_024)),
            ['{"消息":"中文"}', "", '{"b":2}'], "UTF-8 文件与空行",
        )
        invalid = root / "invalid.jsonl"
        invalid.write_bytes(b"\xff\n")
        checked += _expect_error(
            lambda: list(_iter_bounded_lines(invalid, maximum=1_024)),
            "JSONL第 1 行不是有效 UTF-8，读取已停止", "非法 UTF-8",
        )

        checked += _expect_value(
            _complete_record_limit(io.BytesIO(b'{"a":1}\n'), 8), 8, "完整记录边界"
        )
        checked += _expect_value(_complete_record_limit(io.BytesIO(b"\n"), 1), 1, "首字节边界")
        checked += _expect_value(
            _complete_record_limit(io.BytesIO(b'{"a":1}\n{"b":'), 13), 8, "残段边界收敛"
        )
        checked += _expect_value(_complete_record_limit(io.BytesIO(b'{"a":1}'), 7), 0, "无换行边界归零")

        truncate = root / "truncate.jsonl"
        truncate.write_bytes(b'{"a":1}\n{"b":')
        with truncate.open("r+b") as handle:
            checked += _expect_value(
                _truncate_partial_record_tail(handle.fileno(), 13), 8, "截断残段长度"
            )
        checked += _expect_value(truncate.read_bytes(), b'{"a":1}\n', "截断残段内容")

        clean = root / "clean.jsonl"
        clean.write_bytes(b'{"a":1}\n')
        with clean.open("r+b") as handle:
            checked += _expect_value(
                _truncate_partial_record_tail(handle.fileno(), 8), 8, "完整记录不截断"
            )
        checked += _expect_value(clean.read_bytes(), b'{"a":1}\n', "完整记录保持不变")

        no_newline = root / "none.jsonl"
        no_newline.write_bytes(b'{"a":1}')
        with no_newline.open("r+b") as handle:
            checked += _expect_error(
                lambda: _truncate_partial_record_tail(handle.fileno(), 7),
                "会话日志末尾缺少完整记录边界", "无换行截断拒绝",
            )
    return checked


def check_session_log() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, ENCODE_FRAGMENTS, DECODE_FRAGMENTS,
                      RECORD_FRAGMENTS, READ_FRAGMENTS, SNAPSHOT_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 编码：先转 UTF-8 再判上限，随后才补换行。
    checked += _ordered(
        (
            'encoded = _json(value).encode("utf-8")',
            "if len(encoded) > maximum:",
            'return encoded + b"\\n"',
        ),
        module,
        MODULE,
    )
    # 解码：钩子解析之后校验 Unicode，最后要求顶层是对象。
    checked += _ordered(
        (
            "parse_constant=_reject_json_constant, parse_float=_finite_json_float)",
            "_validate_json_unicode(record)",
            "if not isinstance(record, dict):",
        ),
        module,
        MODULE,
    )
    # 会话头只能出现在第 1 行，重复出现必须停止读取。
    checked += _ordered(
        (
            'if record.get("type") == "session":',
            "if line_number == 1:\n            return None",
            'raise ValueError(f"会话日志第 {line_number} 行出现重复会话头，读取已停止")',
        ),
        module,
        MODULE,
    )
    # 反向断言：末尾残段只能丢弃，不得作为记录产出；日志编码不得转义非 ASCII。
    if "yield pending" in module:
        raise ValueError(f"{MODULE} 不得把末尾残段当作完整记录")
    if "ensure_ascii=True" in module:
        raise ValueError(f"{MODULE} 的会话日志必须保留原始 Unicode")
    return checked + 3


def main() -> int:
    try:
        checked = check_session_log()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"会话日志核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话日志一致：{checked} 项编码、解码与快照防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
