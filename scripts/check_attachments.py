#!/usr/bin/env python3
"""核对附件读取分页与存储配额边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
APPLICATION = "harness/src/boss_harness/application.py"
SESSION = "harness/src/boss_harness/session.py"
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
# 删除会话后的附件清理：共享内容寻址附件必须先扫描全部会话引用，再 fail closed 清理。
SESSION_FRAGMENTS = (
    'candidates = set(digests)',
    'for session_path in self.root.glob("*.jsonl"):',
    'if session_path.stem in self._pending_deletion_ids():',
    'referenced.add(digest)',
    'for digest in candidates - referenced:',
    'raise ValueError("附件目录不可信，清理已暂停")',
    'raise ValueError("会话文件不可信，无法确认共享附件引用")',
    'raise ValueError("附件文件不可信，清理已暂停")',
    'restrict_private_file(session_path)',
    'restrict_private_file(path)',
)
FINISH_ORDER = (
    "def _finish_deletion(",
    "self._remove_thread_files(thread_id)",
    'self._purge_unreferenced_attachments(intent["attachmentDigests"])',
)
PURGE_ORDER = (
    "def _purge_unreferenced_attachments(",
    'self.root.glob("*.jsonl")',
    "for digest in candidates - referenced:",
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


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _section(text: str, start_marker: str) -> str:
    start = text.index(start_marker)
    end = text.find("\n    def ", start + 1)
    return text[start:] if end < 0 else text[start:end]


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
    session = _read(SESSION)
    missing = [fragment for fragment in SESSION_FRAGMENTS if fragment not in session]
    if missing:
        raise ValueError("session.py 的附件清理边界缺少：" + "、".join(missing))
    finish = _section(session, "def _finish_deletion(")
    purge = _section(session, "def _purge_unreferenced_attachments(")
    guards = (len(RESOURCE_FRAGMENTS) + len(APPLICATION_FRAGMENTS)
              + len(SESSION_FRAGMENTS) + _ordered(FINISH_ORDER, finish, SESSION)
              + _ordered(PURGE_ORDER, purge, SESSION))
    # 删除集合只能是「候选减引用」：整份 candidates 删除会破坏共享附件的其他会话。
    if "for digest in candidates:" in purge:
        raise ValueError("session.py 的附件清理不得删除全部候选")
    if "if not candidates:" not in purge or "return" not in purge.split("if not candidates:", 1)[1][:80]:
        raise ValueError("session.py 的附件清理必须在候选为空时提前返回")
    # 会话文件与附件文件都必须拒绝硬链接：清理函数内两处单链接检查各出现一次。
    if purge.count("original.st_nlink != 1") != 2:
        raise ValueError("session.py 的附件清理必须在会话文件与附件文件上各做一次单链接检查")
    guards += 3
    return len(EXPECTED_CONSTANTS), guards


def main() -> int:
    try:
        constants, guards = check_attachments()
    except ValueError as error:
        print(f"附件边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件边界一致：{constants} 个常量、{guards} 项读取 / 存储 / 删除防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
