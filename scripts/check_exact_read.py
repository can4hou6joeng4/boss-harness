#!/usr/bin/env python3
"""对照会话日志精确读取原语 `_read_exactly_at` 的定位、短读与拼接边界。

`_read_exactly_at` 先把描述符定位到给定偏移，再循环读取直到取满请求长度；
任何不足都抛「会话日志读取不完整」，绝不返回部分数据。偏移固定用 `SEEK_SET`
语义，因此同一描述符上的多次调用互不影响。快照校验、事件重写与检查点发布
都依赖这一原语按「偏移 + 长度」精确取数。本脚本直接打开临时文件做行为对照，
不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import _read_exactly_at  # noqa: E402

CHECK_ORDER = (
    "def _read_exactly_at(descriptor: int, offset: int, length: int) -> bytes:",
    "chunks: list[bytes] = []",
    "os.lseek(descriptor, offset, os.SEEK_SET)",
    "while length:",
    "chunk = os.read(descriptor, length)",
    "if not chunk:",
    'raise OSError("会话日志读取不完整")',
    "chunks.append(chunk)",
    "length -= len(chunk)",
    'return b"".join(chunks)',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少顶层函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect(value, expected, label: str) -> None:
    if value != expected:
        raise ValueError(f"{label} 读取结果变化：期望 {expected!r}，实际 {value!r}")


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except OSError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def _read_raw(path: Path, offset: int, length: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        return _read_exactly_at(descriptor, offset, length)
    finally:
        os.close(descriptor)


def _read_ok(path: Path, offset: int, length: int) -> bytes:
    try:
        return _read_raw(path, offset, length)
    except OSError as error:
        raise ValueError(f"精确读取意外失败：{error}") from None


def check_exact_read() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    function = _function(tree, source, "_read_exactly_at")
    checked = _ordered(CHECK_ORDER, function, SESSION)
    for fragment in ("os.lseek(descriptor, offset, os.SEEK_SET)",
                     "os.read(descriptor, length)",
                     "while length:",
                     "if not chunk:",
                     "chunks.append(chunk)",
                     "length -= len(chunk)",
                     'return b"".join(chunks)'):
        if function.count(fragment) != 1:
            raise ValueError(f"{SESSION} 的精确读取必须恰好一处：{fragment}")
        checked += 1
    if function.count('raise OSError("会话日志读取不完整")') != 1:
        raise ValueError(f"{SESSION} 的短读必须恰好一处固定原因")
    checked += 1
    if function.count("return ") != 1:
        raise ValueError(f"{SESSION} 的精确读取只能在拼接后返回一次")
    checked += 1
    if "os.pread" in function or "ftruncate" in function or "os.write" in function:
        raise ValueError(f"{SESSION} 的精确读取不得预读或改写文件")
    checked += 1
    data = b"0123456789\nabcdefghij\n"
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "log.jsonl"
        path.write_bytes(data)
        empty = Path(temporary) / "empty.jsonl"
        empty.write_bytes(b"")
        _expect(_read_ok(path, 2, 5), b"23456", "中段读取")
        checked += 1
        _expect(_read_ok(path, 8, 6), b"89\nabc", "跨换行读取")
        checked += 1
        _expect(_read_ok(path, 0, len(data)), data, "整文件读取")
        checked += 1
        _expect(_read_ok(path, len(data), 0), b"", "末尾零长度")
        checked += 1
        _expect(_read_ok(path, 100, 0), b"", "越界零长度")
        checked += 1
        _expect(_read_ok(path, 0, 0), b"", "开头零长度")
        checked += 1
        _expect(_read_ok(empty, 0, 0), b"", "空文件零长度")
        checked += 1
        # 读取后描述符位置落在 offset + length。
        descriptor = os.open(path, os.O_RDONLY)
        try:
            _read_exactly_at(descriptor, 3, 4)
            if os.lseek(descriptor, 0, os.SEEK_CUR) != 7:
                raise ValueError("精确读取后文件位置必须落在 offset + length")
            checked += 1
        finally:
            os.close(descriptor)
        # 同一描述符上的多次调用按各自偏移重新定位。
        descriptor = os.open(path, os.O_RDONLY)
        try:
            first = _read_exactly_at(descriptor, 5, 2)
            second = _read_exactly_at(descriptor, 0, 2)
        finally:
            os.close(descriptor)
        _expect(first, b"56", "首次读取")
        checked += 1
        _expect(second, b"01", "再次读取复位")
        checked += 1
        # 不足的读取必须整体失败，不返回部分数据。
        for label, target, offset, length in (
            ("末尾越界", path, len(data), 1),
            ("远端越界", path, 100, 1),
            ("长度超出剩余", path, 5, 100),
            ("空文件读取", empty, 0, 1),
        ):
            _expect_error(lambda target=target, offset=offset, length=length:
                          _read_raw(target, offset, length),
                          "会话日志读取不完整", label)
            checked += 1
        # 失败后描述符仍可用，读取路径不关闭调用方的描述符。
        descriptor = os.open(path, os.O_RDONLY)
        try:
            try:
                _read_exactly_at(descriptor, len(data), 1)
            except OSError:
                pass
            _expect(_read_exactly_at(descriptor, 0, 3), b"012", "失败后复用")
            checked += 1
        finally:
            os.close(descriptor)
    return checked


def main() -> int:
    try:
        checked = check_exact_read()
    except (ValueError, SyntaxError) as error:
        print(f"精确读取核对失败，{error}", file=sys.stderr)
        return 2
    print(f"精确读取一致：{checked} 项定位、短读与拼接边界校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
