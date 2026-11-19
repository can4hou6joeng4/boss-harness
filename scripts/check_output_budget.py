#!/usr/bin/env python3
"""核对模型输出的字节预算、有界错误与 UTF-8 分块。

output_budget.py 在分配前限制保留的文本、思考与工具参数：先按码点预检再编码，
超限抛固定异常；工具参数按紧凑 JSON 逐字符计费；诊断错误不拆开 UTF-8 字符。
任一放宽都会让超限值进入内存或持久记录，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/output_budget.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

CONSTANT_FRAGMENTS = (
    "MAX_TOOL_ARGUMENT_BYTES = 1024 * 1024\n",
    "MAX_RESPONSE_TOOL_ARGUMENT_BYTES = 1024 * 1024\n",
    "MAX_RESPONSE_TEXT_BYTES = 1024 * 1024\n",
)
UTF8_FRAGMENTS = (
    # 先按码点数预检，避免为明显超限的字符串分配编码结果。
    "if len(value) > remaining:",
    'size = len(value.encode("utf-8"))',
    "except UnicodeEncodeError:",
    'raise ValueError("模型输出包含非法 Unicode") from None',
    "if size > remaining:",
)
TOOL_BUDGET_FRAGMENTS = (
    "current = self._tool_bytes.get(index, 0)",
    "delta = utf8_size_at_most(value, MAX_TOOL_ARGUMENT_BYTES - current)",
    "if delta > MAX_RESPONSE_TOOL_ARGUMENT_BYTES - self._response_bytes:",
    'raise OutputBudgetExceeded("本轮工具参数超过总字节上限")',
    "self._tool_bytes[index] = current + delta",
    "self._response_bytes += delta",
)
SNAPSHOT_FRAGMENTS = (
    "remaining = min(MAX_TOOL_ARGUMENT_BYTES - self._tool_bytes.get(index, 0),",
    "nodes = 0",
    "def account(amount: int) -> None:",
    "nonlocal remaining",
    "if remaining < 0:",
    'raise OutputBudgetExceeded("工具参数超过本地字节上限")',
    "def string(text: str) -> None:",
    "for character in text:",
    "code = ord(character)",
    'if character in (\'"\', "\\\\", "\\b", "\\t", "\\n", "\\f", "\\r"):',
    "elif 0xD800 <= code <= 0xDFFF:",
    'raise ValueError("工具参数包含非法 Unicode")',
    "def visit(item: object, depth: int = 0) -> None:",
    "nodes += 1",
    "if depth > 64 or nodes > 32768:",
    'raise ValueError("工具参数结构超过本地上限")',
    "if type(item) is str:",
    "elif item is None or type(item) is bool:",
    "elif type(item) is int:",
    "if item.bit_length() > max(remaining, 0) * 4:",
    "elif type(item) is float and math.isfinite(item):",
    "elif type(item) is dict:",
    'if type(key) is not str:',
    'raise ValueError("工具参数对象键不是文本")',
    "elif type(item) is list:",
    'raise ValueError("工具参数不是 JSON 值")',
    "visit(value)",
    'encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)',
    "self.account(index, encoded)",
    "return encoded",
    "size = utf8_size_at_most(authoritative, MAX_TOOL_ARGUMENT_BYTES)",
    "if size > MAX_RESPONSE_TOOL_ARGUMENT_BYTES - (self._response_bytes - current):",
    "self._tool_bytes[index] = max(current, size)",
)
TEXT_BUDGET_FRAGMENTS = (
    "def size(value: str, remaining: int = MAX_RESPONSE_TEXT_BYTES) -> int:",
    'scope="模型文本与思考输出超过本地 UTF-8 字节上限")',
    "size = self.size(fragment, MAX_RESPONSE_TEXT_BYTES - self._response_bytes)",
    "separator_bytes = self.size(separator)",
    "size += self.size(part, MAX_RESPONSE_TEXT_BYTES - size)",
    "return separator.join(parts)",
    "delta = max(0, size - current)",
    "if delta > MAX_RESPONSE_TEXT_BYTES - self._response_bytes:",
    'raise OutputBudgetExceeded("模型文本与思考输出超过本地 UTF-8 字节上限")',
    "self._response_bytes = max(self._response_bytes, size)",
)
ERROR_FRAGMENTS = (
    "if len(prefix) + len(detail) <= maximum:",
    'if len(value.encode("utf-8")) <= maximum:',
    'suffix = "…"',
    'char = "\\ufffd"',
    "if size + char_size > maximum - len(suffix.encode(\"utf-8\")):",
    'return "".join(out) + suffix',
)
CHUNK_FRAGMENTS = (
    "if maximum < 4:",
    'raise ValueError("UTF-8 分块上限至少为 4 字节")',
    "if parts and size + width > maximum:",
    "yield \"\".join(parts)",
    "parts, size = [], 0",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "文本与思考另按每次响应合计 1 MiB 原始 UTF-8 字节限制，增量和权威终态都在缓冲、事件持久化及通知前检查。"),
    (TECHNICAL_REFERENCE, "增量事件拆为最多 32 KiB UTF-8，以便事件分页恢复"),
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


def check_output_budget() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(UTF8_FRAGMENTS, module, MODULE)
    checked += _expect(TOOL_BUDGET_FRAGMENTS, module, MODULE)
    checked += _expect(SNAPSHOT_FRAGMENTS, module, MODULE)
    checked += _expect(TEXT_BUDGET_FRAGMENTS, module, MODULE)
    checked += _expect(ERROR_FRAGMENTS, module, MODULE)
    checked += _expect(CHUNK_FRAGMENTS, module, MODULE)
    # 尺寸判定：码点预检 → 编码 → 字节上限。
    checked += _ordered(
        (
            "if len(value) > remaining:",
            'size = len(value.encode("utf-8"))',
            "if size > remaining:",
        ),
        module,
        MODULE,
    )
    # 快照：先算剩余额度 → 遍历 → 紧凑编码 → 记账。
    checked += _ordered(
        (
            "remaining = min(MAX_TOOL_ARGUMENT_BYTES - self._tool_bytes.get(index, 0),",
            "visit(value)",
            'encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)',
            "self.account(index, encoded)",
            "return encoded",
        ),
        module,
        MODULE,
    )
    # 分块：上限校验 → 逐字符累计 → 超限先产出 → 末尾残块。
    checked += _ordered(
        (
            "if maximum < 4:",
            "for char in value:",
            "if parts and size + width > maximum:",
            "yield \"\".join(parts)",
            "if parts:",
        ),
        module,
        MODULE,
    )
    # 序列化必须保留非 ASCII 并拒绝 NaN。
    if "allow_nan=True" in module:
        raise ValueError(f"{MODULE} 不得序列化非有限数值")
    if "ensure_ascii=True" in module:
        raise ValueError(f"{MODULE} 必须保留非 ASCII 字符")
    if "json.dumps(value)" in module:
        raise ValueError(f"{MODULE} 的紧凑编码必须显式给出选项")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_output_budget()
    except ValueError as error:
        print(f"模型输出预算核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型输出预算一致：{checked} 项字节、错误与分块防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
