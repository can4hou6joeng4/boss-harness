#!/usr/bin/env python3
"""核对附件读取分页、存储配额与删除清理边界，成功时输出核对项数量。

常量与源码片段固定读取分段、存储默认值与删除流程的形状；再用临时目录、合成
会话 JSONL 与附件对象构造真实 `SessionStore`，实际执行删除后的附件清理，
覆盖共享引用扫描、待删除会话跳过、缺失对象与不可信输入的 fail closed 文案。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"
APPLICATION = "harness/src/boss_harness/application.py"
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import SessionStore  # noqa: E402

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
    'raise ValueError("附件清理候选摘要格式无效")',
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


_THREAD = "aaaaaaaaaaaa"
_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def _digest(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _header(thread_id: str) -> dict:
    return {"type": "session", "version": 2, "id": thread_id,
            "sessionId": f"sess-{thread_id}", "title": "会话", "createdAt": _TIMESTAMP,
            "archived": False}


def _attachment(entry_id: str, value: object) -> dict:
    return {"type": "attachment", "id": entry_id, "parentId": None,
            "timestamp": _TIMESTAMP,
            "payload": {"digest": value, "name": "notes.txt", "bytes": 1,
                        "mediaType": "text/plain; charset=utf-8"}}


def _write_session(sessions: Path, thread_id: str, rows: list[dict], *,
                   tail: str = "") -> Path:
    path = sessions / f"{thread_id}.jsonl"
    lines = [json.dumps(value, ensure_ascii=False) for value in [_header(thread_id), *rows]]
    path.write_text("\n".join(lines) + "\n" + tail, encoding="utf-8")
    return path


def _write_marker(sessions: Path, thread_id: str, digests: list[str]) -> Path:
    path = sessions / f".delete-{thread_id}.json"
    path.write_text(json.dumps({"version": 1, "threadId": thread_id,
                                "attachmentDigests": digests, "eventId": "0" * 32}) + "\n",
                    encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _build(base: Path, name: str) -> tuple[SessionStore, Path, Path]:
    root = base / name
    sessions = root / "sessions"
    sessions.mkdir(parents=True, mode=0o700)
    attachments = root / "attachments"
    attachments.mkdir(mode=0o700)
    return SessionStore(sessions), sessions, attachments


def _object(attachments: Path, value: str, *, mode: int = 0o600) -> Path:
    path = attachments / value
    path.write_text("payload", encoding="utf-8")
    os.chmod(path, mode)
    return path


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"附件清理行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _no_error(call, label: str) -> int:
    try:
        call()
    except Exception as error:
        raise ValueError(
            f"附件清理行为变化 {label}：未预期 {type(error).__name__}: {error}") from None
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"附件清理行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"附件清理行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"附件清理行为变化 {label}：未抛出错误")


def _behavior_checks() -> int:
    checked = 0
    corrupt = "会话记录损坏，无法确认共享附件引用"
    untrusted_session = "会话文件不可信，无法确认共享附件引用"
    untrusted_object = "附件文件不可信，清理已暂停"
    untrusted_root = "附件目录不可信，清理已暂停"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        # 共享引用保留，未引用对象与缺失对象按候选清单处理。
        store, sessions, attachments = _build(base, "shared")
        keep, drop, missing = _digest("keep"), _digest("drop"), _digest("missing")
        _write_session(sessions, _THREAD, [_attachment("a1", keep)])
        keep_path = _object(attachments, keep)
        drop_path = _object(attachments, drop)
        store._purge_unreferenced_attachments([keep, drop, missing])
        checked += _expect_value(keep_path.exists(), True, "共享引用保留")
        checked += _expect_value(drop_path.exists(), False, "未引用对象删除")
        _write_session(sessions, "bbbbbbbbbbbb", [_attachment("b1", keep)])
        store._purge_unreferenced_attachments([keep])
        checked += _expect_value(keep_path.exists(), True, "多会话引用保留")
        first_drop, second_drop = _digest("first-drop"), _digest("second-drop")
        first_path = _object(attachments, first_drop)
        second_path = _object(attachments, second_drop)
        store._purge_unreferenced_attachments([first_drop, second_drop])
        checked += _expect_value((first_path.exists(), second_path.exists()), (False, False),
                                 "多候选全部删除")

        # 其他会话的删除标记不影响本会话引用；CRLF 日志与重复引用同样保留对象。
        store, sessions, attachments = _build(base, "marker-other")
        marker_keep = _digest("marker-keep")
        _write_session(sessions, "bbbbbbbbbbbb", [_attachment("b1", marker_keep)])
        marker_keep_path = _object(attachments, marker_keep)
        _write_marker(sessions, "cccccccccccc", [])
        _write_session(sessions, "dddddddddddd", [])
        store._purge_unreferenced_attachments([marker_keep])
        checked += _expect_value(marker_keep_path.exists(), True, "其他会话标记不影响引用")
        store, sessions, attachments = _build(base, "crlf")
        crlf_keep = _digest("crlf-keep")
        path = sessions / f"{_THREAD}.jsonl"
        lines = [json.dumps(_header(_THREAD)),
                 json.dumps(_attachment("a1", crlf_keep)),
                 json.dumps(_attachment("a2", crlf_keep))]
        path.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
        crlf_path = _object(attachments, crlf_keep)
        store._purge_unreferenced_attachments([crlf_keep])
        checked += _expect_value(crlf_path.exists(), True, "CRLF 与重复引用保留")

        # 大写摘要不匹配合法格式，不构成引用。
        store, sessions, attachments = _build(base, "uppercase")
        upper = _digest("upper")
        _write_session(sessions, _THREAD, [_attachment("a1", upper.upper())])
        upper_path = _object(attachments, upper)
        store._purge_unreferenced_attachments([upper])
        checked += _expect_value(upper_path.exists(), False, "大写摘要不算引用")

        # 只有格式合法摘要的附件记录才算引用；空行跳过。
        store, sessions, attachments = _build(base, "shapes")
        only = _digest("only")
        _write_session(sessions, _THREAD, [
            {"type": "item", "id": "i1", "parentId": None, "timestamp": _TIMESTAMP,
             "payload": {"kind": "message", "digest": only}},
            {"type": "attachment", "id": "a0", "parentId": None, "timestamp": _TIMESTAMP,
             "payload": {}},
            _attachment("a1", "not-a-digest"),
            _attachment("a2", 123),
        ], tail="\n")
        only_path = _object(attachments, only)
        store._purge_unreferenced_attachments([only])
        checked += _expect_value(only_path.exists(), False, "非附件记录不算引用")

        # 待删除会话被跳过：其引用不阻塞其他删除，会话文件与标记保留。
        store, sessions, attachments = _build(base, "pending")
        shared = _digest("shared")
        _write_session(sessions, "bbbbbbbbbbbb", [_attachment("b1", shared)])
        shared_path = _object(attachments, shared)
        marker = _write_marker(sessions, "bbbbbbbbbbbb", [shared])
        store._purge_unreferenced_attachments([shared])
        checked += _expect_value(shared_path.exists(), False, "待删除会话引用不阻塞清理")
        checked += _expect_value((sessions / "bbbbbbbbbbbb.jsonl").exists(), True,
                                 "待删除会话文件保留")
        checked += _expect_value(marker.exists(), True, "删除标记保留")

        # 损坏会话与非法载荷 fail closed。
        store, sessions, attachments = _build(base, "corrupt")
        path = sessions / "cccccccccccc.jsonl"
        path.write_text(json.dumps(_header("cccccccccccc")) + "\n{broken\n", encoding="utf-8")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]), corrupt, "损坏会话")
        store, sessions, attachments = _build(base, "payload")
        path = sessions / "cccccccccccc.jsonl"
        path.write_text(json.dumps(_header("cccccccccccc")) + "\n" + json.dumps(
            {"type": "attachment", "id": "x", "parentId": None,
             "timestamp": _TIMESTAMP, "payload": "bad"}) + "\n", encoding="utf-8")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]), corrupt, "载荷非对象")

        # 会话文件拒绝符号链接与硬链接。
        store, sessions, attachments = _build(base, "symlink-session")
        real = _write_session(sessions, "dddddddddddd", [])
        os.symlink(real, sessions / "eeeeeeeeeeee.jsonl")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]),
            untrusted_session, "符号链接会话")
        store, sessions, attachments = _build(base, "hardlink-session")
        real = _write_session(sessions, "dddddddddddd", [])
        os.link(real, sessions / "eeeeeeeeeeee.jsonl")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]),
            untrusted_session, "硬链接会话")

        # 附件对象拒绝符号链接、硬链接与目录。
        store, sessions, attachments = _build(base, "symlink-object")
        _write_session(sessions, _THREAD, [])
        target = _object(attachments, _digest("keep"))
        os.symlink(target, attachments / _digest("drop"))
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("drop")]),
            untrusted_object, "符号链接附件")
        store, sessions, attachments = _build(base, "hardlink-object")
        _write_session(sessions, _THREAD, [])
        first = _object(attachments, _digest("one"))
        os.link(first, attachments / _digest("two"))
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("two")]),
            untrusted_object, "硬链接附件")
        store, sessions, attachments = _build(base, "directory-object")
        _write_session(sessions, _THREAD, [])
        (attachments / _digest("dir")).mkdir()
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("dir")]),
            untrusted_object, "目录附件")

        # 附件根拒绝普通文件与符号链接。
        store, sessions, attachments = _build(base, "root-file")
        _write_session(sessions, _THREAD, [])
        attachments.rmdir()
        attachments.write_text("x", encoding="utf-8")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]),
            untrusted_root, "附件根是文件")
        store, sessions, attachments = _build(base, "root-link")
        _write_session(sessions, _THREAD, [])
        link = attachments.parent / "attachments-link"
        os.symlink(attachments, link)
        store.attachments_root = link
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]),
            untrusted_root, "附件根符号链接")

        # 候选摘要格式在扫描前收敛：越界、绝对路径与非摘要值被拒绝。
        store, sessions, attachments = _build(base, "guards")
        _write_session(sessions, _THREAD, [])
        state = sessions.parent / "state.sqlite3"
        message = "附件清理候选摘要格式无效"
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments(["../state.sqlite3"]),
            message, "相对越界候选")
        checked += _expect_value(state.exists(), True, "状态文件不受影响")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments([str(state)]),
            message, "绝对路径候选")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments([_digest("upper").upper()]),
            message, "大写候选")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments(["a" * 63]), message, "短摘要候选")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments([123]), message, "非字符串候选")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments([["x"]]), message, "不可哈希候选")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments(None), message, "非序列候选")
        checked += _expect_error(
            lambda: store._purge_unreferenced_attachments(["../state.sqlite3"]),
            message, "内部入口同样拒绝")

        # 静默路径：空候选不扫描、附件目录缺失、重复候选与宽松权限对象。
        store, sessions, attachments = _build(base, "empty-candidates")
        (sessions / "cccccccccccc.jsonl").write_text("bad\n", encoding="utf-8")
        checked += _no_error(
            lambda: store._purge_unreferenced_attachments([]), "空候选不扫描")
        store, sessions, attachments = _build(base, "missing-root")
        _write_session(sessions, _THREAD, [])
        attachments.rmdir()
        checked += _no_error(
            lambda: store._purge_unreferenced_attachments([_digest("x")]), "缺失附件目录")
        store, sessions, attachments = _build(base, "duplicates")
        _write_session(sessions, _THREAD, [])
        duplicate = _digest("duplicate")
        duplicate_path = _object(attachments, duplicate)
        store._purge_unreferenced_attachments([duplicate, duplicate])
        checked += _expect_value(duplicate_path.exists(), False, "重复候选只清理一次")
        store, sessions, attachments = _build(base, "permissions")
        _write_session(sessions, _THREAD, [])
        loose = _object(attachments, _digest("loose"), mode=0o644)
        store._purge_unreferenced_attachments([_digest("loose")])
        checked += _expect_value(loose.exists(), False, "宽松权限对象可清理")

        # 公开包装委托清理并原样抛出不可信错误。
        store, sessions, attachments = _build(base, "public")
        _write_session(sessions, _THREAD, [])
        public = _object(attachments, _digest("public"))
        store.cleanup_unreferenced_attachments([_digest("public")])
        checked += _expect_value(public.exists(), False, "公开清理删除未引用对象")
        checked += _no_error(lambda: store.cleanup_unreferenced_attachments([]), "公开空清理")
        store, sessions, attachments = _build(base, "public-error")
        _write_session(sessions, _THREAD, [])
        attachments.rmdir()
        attachments.write_text("x", encoding="utf-8")
        checked += _expect_error(
            lambda: store.cleanup_unreferenced_attachments([_digest("x")]),
            untrusted_root, "公开清理错误传播")
    return checked


def main() -> int:
    try:
        constants, guards = check_attachments()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"附件边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件边界一致：{constants} 个常量、{guards} 项读取 / 存储 / 删除防护、"
          f"{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
