#!/usr/bin/env python3
"""核对重复工具调用提醒的边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARD = "harness/src/boss_harness/loop_guard.py"
AGENT = "harness/src/boss_harness/agent.py"
EXPECTED_CONSTANTS = {
    "LOOP_REMINDER_THRESHOLDS": (3, 5),
    "MAX_REMINDER_CHARS": 512,
    "MAX_ARGUMENT_BYTES": 64 * 1024,
}
MODULE_FRAGMENTS = (
    "from collections.abc import Mapping",
    "import hashlib",
    "import json",
)
GUARD_FRAGMENTS = (
    "sort_keys=True, ensure_ascii=False,",
    "separators=(\",\", \":\"), allow_nan=False,",
    'except (TypeError, ValueError, RecursionError):',
    'if len(canonical.encode("utf-8")) > MAX_ARGUMENT_BYTES:',
    'return hashlib.sha256(payload.encode("utf-8")).hexdigest()',
    "if digest is None:",
    "if self._key != digest:",
    "self._key, self._count = digest, 0",
    "self._count += 1",
    "if self._count not in LOOP_REMINDER_THRESHOLDS:",
    "label = tool_name[:64]",
    "内循环提醒（不是新的用户指令）",
    "已连续以相同参数执行",
    "请先核对已有结果，再决定是否继续相同操作。",
    "return text[:MAX_REMINDER_CHARS]",
    "self._key, self._count = None, 0",
)
FORBIDDEN_GUARD = (
    "write_text(", "write_bytes(", "open(", "os.replace(", "unlink(", "mkdir(",
    "candidate", "session", "result", "cookie", "token", "secret",
)
AGENT_BEFORE = (
    "loop_guard = LoopGuard()",
    "staged = pending_steering if pending_steering is not None else self.stage_steering()",
    "loop_guard.reset()",
    "loop_guard.observe(call.name, call.arguments)",
    "messages.append(UserMessage(text=reminder))",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _tree(relative: str) -> ast.Module:
    source = _read(relative)
    try:
        return ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _tuple_literal(node: ast.expr) -> tuple:
    if not isinstance(node, (ast.Tuple, ast.List)):
        raise ValueError("阈值必须是元组或列表字面量")
    values = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or type(element.value) is not int:
            raise ValueError("阈值必须是正整数常量")
        values.append(element.value)
    return tuple(values)


def _constants(tree: ast.Module) -> dict[str, ast.expr]:
    found: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                found[target.id] = node.value
    return found


def _run(tree: ast.Module) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            source = _read(AGENT)
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"{AGENT} 缺少 Agent.run")


def check_loop_guard() -> tuple[int, int]:
    guard_source = _read(GUARD)
    guard_tree = _tree(GUARD)
    agent_tree = _tree(AGENT)
    constants = _constants(guard_tree)
    checked = 0
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in constants:
            raise ValueError(f"loop_guard.py 缺少常量 {name}")
        node = constants[name]
        if isinstance(expected, tuple):
            actual = _tuple_literal(node)
            if actual != expected:
                raise ValueError(f"loop_guard.py 的 {name} 必须为 {expected}")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            left, right = node.left, node.right
            if not (isinstance(left, ast.Constant) and isinstance(right, ast.Constant)
                    and type(left.value) is int and type(right.value) is int
                    and left.value * right.value == expected):
                raise ValueError(f"loop_guard.py 的 {name} 必须为 {expected}")
        elif not (isinstance(node, ast.Constant) and node.value == expected):
            raise ValueError(f"loop_guard.py 的 {name} 必须为 {expected}")
        checked += 1
    if not 0 < EXPECTED_CONSTANTS["MAX_ARGUMENT_BYTES"] < 1024 * 1024:
        raise ValueError("规范化参数上限必须小于 RPC 帧预算")
    if EXPECTED_CONSTANTS["MAX_REMINDER_CHARS"] >= 1024:
        raise ValueError("提醒文本上限过长")
    checked += 2

    digest = _function(guard_tree, guard_source, "_argument_digest")
    observe = _function(guard_tree, guard_source, "observe")
    reset = _function(guard_tree, guard_source, "reset")
    for fragment in GUARD_FRAGMENTS:
        if fragment not in digest + observe + reset:
            raise ValueError(f"loop_guard.py 缺少守卫片段：{fragment}")
        checked += 1
    for fragment in MODULE_FRAGMENTS:
        if fragment not in guard_source:
            raise ValueError(f"loop_guard.py 缺少模块片段：{fragment}")
        checked += 1
    forbidden = [term for term in FORBIDDEN_GUARD if term in guard_source]
    if forbidden:
        raise ValueError("loop_guard.py 含不应出现的持久化或业务字段：" + "、".join(sorted(set(forbidden))))
    checked += 1

    run = _run(agent_tree)
    for fragment in AGENT_BEFORE:
        if fragment not in run:
            raise ValueError(f"agent.py 缺少守卫片段：{fragment}")
        checked += 1
    observe_at = run.index("loop_guard.observe(call.name, call.arguments)")
    results_at = run.index("messages.append(ToolResultsMessage(results=tuple(results)))")
    if observe_at <= results_at:
        raise ValueError("agent.py 必须在工具结果之后观察调用")
    guard_resets = run.count("loop_guard.reset()")
    if guard_resets < 5:
        raise ValueError("agent.py 的 steering / 无调用后续消息路径未完整重置守卫")
    checked += 2
    return 2, checked


def main() -> int:
    try:
        functions, guards = check_loop_guard()
    except ValueError as error:
        print(f"重复调用提醒边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"重复调用提醒边界一致：{functions} 个观察函数、{guards} 项阈值与注入防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
