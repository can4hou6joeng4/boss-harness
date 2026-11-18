#!/usr/bin/env python3
"""核对附件读取分页与存储配额边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
APPLICATION = "harness/src/boss_harness/application.py"
EXPECTED_CONSTANTS = {
    "DEFAULT_ATTACHMENT_STORAGE_BYTES": 512 * 1024 * 1024,
    "DEFAULT_ATTACHMENT_STORAGE_OBJECTS": 4096,
    "_MAX_ATTACHMENT_STORAGE_LIMIT": 2**63 - 1,
    "DEFAULT_READ_CHARS": 16_384,
    "MAX_READ_CHARS": 32_768,
}
RESOURCE_FRAGMENTS = (
    'MAX_STORAGE_BYTES_ENV = "BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_BYTES"',
    'MAX_STORAGE_OBJECTS_ENV = "BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_OBJECTS"',
    "limit: int = DEFAULT_READ_CHARS",
    "if type(limit) is not int or not 1 <= limit <= self.MAX_READ_CHARS:",
)
APPLICATION_FRAGMENTS = (
    'if set(params) - {"threadId", "attachmentId", "cursor", "limit", "sha256"}:',
    'limit=params.get("limit", AttachmentStore.DEFAULT_READ_CHARS),',
    "if wire_size(result) > MAX_PAGE_BYTES:",
    '"code": "RESPONSE_TOO_LARGE"',
    '"recoveryMethod": "attachment/read"',
    '"suggestedLimit": AttachmentStore.DEFAULT_READ_CHARS',
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
    if isinstance(node, ast.BinOp):
        left = _int_expression(node.left, values, seen)
        right = _int_expression(node.right, values, seen)
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub) and left > right:
            return left - right
        if isinstance(node.op, ast.Pow) and left <= 1024 and right <= 64:
            return left**right
        raise ValueError("附件常量必须是正整数表达式")
    if isinstance(node, ast.Name) and node.id not in seen and node.id in values:
        return _int_expression(values[node.id], values, seen | {node.id})
    raise ValueError("附件常量必须是正整数表达式")


def check_attachments() -> tuple[int, int]:
    try:
        values = _assigned(ast.parse(_read(RESOURCES)))
    except SyntaxError:
        raise ValueError(f"无法解析 {RESOURCES}") from None
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in values:
            raise ValueError(f"resources.py 缺少附件常量 {name}")
        try:
            actual = _int_expression(values[name], values)
        except ValueError:
            raise ValueError(f"resources.py 的 {name} 必须是正整数表达式") from None
        if actual != expected:
            raise ValueError(f"resources.py 的 {name} 必须是 {expected}，实际为 {actual}")
    if EXPECTED_CONSTANTS["DEFAULT_ATTACHMENT_STORAGE_BYTES"] > EXPECTED_CONSTANTS["_MAX_ATTACHMENT_STORAGE_LIMIT"]:
        raise ValueError("附件存储字节默认值不得超过上限")
    if EXPECTED_CONSTANTS["DEFAULT_ATTACHMENT_STORAGE_OBJECTS"] > EXPECTED_CONSTANTS["_MAX_ATTACHMENT_STORAGE_LIMIT"]:
        raise ValueError("附件存储对象默认值不得超过上限")
    if EXPECTED_CONSTANTS["DEFAULT_READ_CHARS"] > EXPECTED_CONSTANTS["MAX_READ_CHARS"]:
        raise ValueError("附件默认分段不得超过最大分段")
    resources = _read(RESOURCES)
    application = _read(APPLICATION)
    missing = [fragment for fragment in RESOURCE_FRAGMENTS if fragment not in resources]
    if missing:
        raise ValueError("resources.py 的附件边界缺少：" + "、".join(missing))
    missing = [fragment for fragment in APPLICATION_FRAGMENTS if fragment not in application]
    if missing:
        raise ValueError("application.py 的附件边界缺少：" + "、".join(missing))
    return len(EXPECTED_CONSTANTS), len(RESOURCE_FRAGMENTS) + len(APPLICATION_FRAGMENTS)


def main() -> int:
    try:
        constants, guards = check_attachments()
    except ValueError as error:
        print(f"附件边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件边界一致：{constants} 个常量、{guards} 项读取 / 存储防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
