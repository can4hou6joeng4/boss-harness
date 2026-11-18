#!/usr/bin/env python3
"""核对工具结果分页、内容寻址与引用恢复边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOL_RESULTS = "harness/src/boss_harness/tool_results.py"
APPLICATION = "harness/src/boss_harness/application.py"
MODEL_TOOLS = "harness/src/boss_harness/model_tools.py"
RPC = "harness/src/boss_harness/rpc.py"
EXPECTED_CONSTANTS = {
    "MAX_INLINE_TOOL_RESULT_BYTES": 64 * 1024,
    "MAX_PAGE_BYTES": 1024 * 1024,
    "DEFAULT_RESULT_CHARS": 16_384,
    "MAX_RESULT_CHARS": 32_768,
    "MODEL_RESULT_READ_CHARS": 8_192,
}
TOOL_RESULTS_FRAGMENTS = (
    'if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:',
    're.fullmatch(r"[a-f0-9]{64}", sha256) is None',
    '"code": "STALE_RESULT", "currentRef": reference',
    'not cursor.startswith("tr1_") or len(cursor) > 2048',
    'value[:3] != [thread_id, item_id, reference["sha256"]]',
    'or type(value[3]) is not int or not 0 <= value[3] < len(text)',
    'if len(text.encode("utf-8", "surrogatepass")) > MAX_INLINE_TOOL_RESULT_BYTES:',
    '"nextCursor": _cursor(reference, end) if end < len(text) else None',
)
APPLICATION_FRAGMENTS = (
    'if set(params) - {"threadId", "itemId", "sha256", "cursor", "limit"}:',
    'if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):',
)
MODEL_TOOLS_FRAGMENTS = (
    '"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},',
    '"additionalProperties": False,',
    'limit=arguments.get("limit", MODEL_RESULT_READ_CHARS))',
    'error["currentRef"] = current_ref',
    '"code": code if isinstance(code, str) else "RESULT_READ_FAILED",',
)
RPC_DEFAULT = re.compile(
    r'def on_tool_result_read\(.*?return read_result_chunk\(.*?limit=params\.get\("limit",\s*([\d_]+)\)',
    re.DOTALL,
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    values: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value
    return values


def _int_expression(node: ast.expr, values: dict[str, ast.expr],
                    seen: frozenset[str] = frozenset()) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_expression(node.left, values, seen) * _int_expression(node.right, values, seen)
    if isinstance(node, ast.Name) and node.id not in seen and node.id in values:
        return _int_expression(values[node.id], values, seen | {node.id})
    raise ValueError("工具结果常量必须是正整数乘积表达式")


def _frame_limit() -> int:
    try:
        tree = ast.parse(_read(RPC))
    except SyntaxError:
        raise ValueError(f"无法解析 {RPC}") from None
    values = _assigned(tree)
    if "MAX_FRAME_BYTES" not in values:
        raise ValueError(f"{RPC} 缺少 MAX_FRAME_BYTES")
    return _int_expression(values["MAX_FRAME_BYTES"], values)


def _missing(fragments: tuple[str, ...], text: str) -> list[str]:
    return [fragment for fragment in fragments if fragment not in text]


def check_tool_results() -> tuple[int, int]:
    try:
        values = _assigned(ast.parse(_read(TOOL_RESULTS)))
    except SyntaxError:
        raise ValueError(f"无法解析 {TOOL_RESULTS}") from None
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in values:
            raise ValueError(f"tool_results.py 缺少常量 {name}")
        try:
            actual = _int_expression(values[name], values)
        except ValueError:
            raise ValueError(f"tool_results.py 的 {name} 必须是正整数乘积表达式") from None
        if actual != expected:
            raise ValueError(f"tool_results.py 的 {name} 必须是 {expected}，实际为 {actual}")
    if not 0 < EXPECTED_CONSTANTS["MODEL_RESULT_READ_CHARS"] <= EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"]:
        raise ValueError("模型读取上限不得超过 RPC 默认分段")
    if EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"] > EXPECTED_CONSTANTS["MAX_RESULT_CHARS"]:
        raise ValueError("RPC 默认分段不得超过最大分段")
    if EXPECTED_CONSTANTS["MAX_INLINE_TOOL_RESULT_BYTES"] >= EXPECTED_CONSTANTS["MAX_PAGE_BYTES"]:
        raise ValueError("内联结果上限必须小于单页预算")
    if EXPECTED_CONSTANTS["MAX_PAGE_BYTES"] >= _frame_limit():
        raise ValueError("工具结果单页预算必须小于 JSON-RPC 帧上限")

    tool_results = _read(TOOL_RESULTS)
    application = _read(APPLICATION)
    model_tools = _read(MODEL_TOOLS)
    missing = _missing(TOOL_RESULTS_FRAGMENTS, tool_results)
    if missing:
        raise ValueError("tool_results.py 的分页与引用边界缺少：" + "、".join(missing))
    missing = _missing(APPLICATION_FRAGMENTS, application)
    if missing:
        raise ValueError("application.py 的工具结果读取边界缺少：" + "、".join(missing))
    missing = _missing(MODEL_TOOLS_FRAGMENTS, model_tools)
    if missing:
        raise ValueError("model_tools.py 的模型读取边界缺少：" + "、".join(missing))

    defaults = RPC_DEFAULT.findall(application)
    if len(defaults) != 1:
        raise ValueError("application.py 的工具结果 RPC 默认分段必须唯一")
    if int(defaults[0].replace("_", "")) != EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"]:
        raise ValueError("工具结果 RPC 默认分段与 DEFAULT_RESULT_CHARS 不一致")
    if tool_results.count('if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:') < 2:
        raise ValueError("两条工具结果读取路径都必须校验 limit")
    if model_tools.count('"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},') != 2:
        raise ValueError("模型读取 schema 与工具描述必须一致使用 MODEL_RESULT_READ_CHARS")

    guards = (len(TOOL_RESULTS_FRAGMENTS) + len(APPLICATION_FRAGMENTS)
              + len(MODEL_TOOLS_FRAGMENTS) + 3)
    return len(EXPECTED_CONSTANTS), guards


def main() -> int:
    try:
        constants, guards = check_tool_results()
    except ValueError as error:
        print(f"工具结果边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具结果边界一致：{constants} 个常量、{guards} 项分页与引用防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
