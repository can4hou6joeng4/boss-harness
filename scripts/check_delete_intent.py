#!/usr/bin/env python3
"""对照会话删除标记的校验、原子发布与重启恢复。

`.delete-<threadId>.json` 标记是「会话删除后暂不可操作」的持久边界：
`_read_delete_intent` 校验文件名、大小、JSON 形状与四个字段；`_write_delete_intent`
用独占临时文件加硬链接发布，已存在时读回而不覆盖；`_pending_deletion_ids`
只按名称列出阻塞会话；`_recover_deletions` 在启动时完成合法标记、保留损坏标记。
本脚本在临时目录构造 `SessionStore` 做行为对照，覆盖标记名过滤、大小边界、
摘要归一、损坏标记不覆盖、重开收紧权限与恢复隔离，并扫描源码固定这条链路；
它不访问网络、模型、招聘平台或用户状态目录。
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import MAX_DELETE_INTENT_BYTES, SessionStore  # noqa: E402

READ_ORDER = (
    "def _read_delete_intent(self, path: Path) -> dict[str, Any]:",
    "match = _DELETE_INTENT.fullmatch(path.name)",
    "if match is None:",
    'raise ValueError("会话删除标记名称无效")',
    'raw = _read_bounded_file(path, maximum=MAX_DELETE_INTENT_BYTES, label="会话删除标记")',
    'value = json.loads(raw.decode("utf-8"))',
    "except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):",
    'raise ValueError("会话删除标记损坏，会话暂不可操作") from None',
    "thread_id = match.group(1)",
    'if (not isinstance(value, dict) or set(value) != {"version", "threadId", "attachmentDigests", "eventId"}',
    'or value.get("version") != 1 or value.get("threadId") != thread_id',
    'or not isinstance(value.get("attachmentDigests"), list)',
    'or any(not isinstance(item, str) or not _ATTACHMENT_DIGEST.fullmatch(item)',
    'for item in value["attachmentDigests"])',
    'or not isinstance(value.get("eventId"), str)',
    'or not _EVENT_ID.fullmatch(value["eventId"])):',
    'raise ValueError("会话删除标记损坏，会话暂不可操作")',
    'value["attachmentDigests"] = sorted(set(value["attachmentDigests"]))',
    "return value",
)
WRITE_ORDER = (
    "def _write_delete_intent(self, thread_id: str, entries: list[dict]) -> dict[str, Any]:",
    "path = self._delete_intent_path(thread_id)",
    "if path.exists():",
    "return self._read_delete_intent(path)",
    'digests = sorted({entry.get("payload", {}).get("digest") for entry in entries',
    'if entry.get("type") == "attachment"',
    'and isinstance(entry.get("payload", {}).get("digest"), str)',
    'and _ATTACHMENT_DIGEST.fullmatch(entry["payload"]["digest"])})',
    'intent = {"version": 1, "threadId": thread_id,',
    '"attachmentDigests": digests, "eventId": uuid.uuid4().hex}',
    'temporary = self.root / f".delete-{thread_id}.{uuid.uuid4().hex}.tmp"',
    "descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)",
    'with os.fdopen(descriptor, "wb") as handle:',
    'handle.write((_json(intent) + "\\n").encode("utf-8"))',
    "handle.flush()",
    "os.fsync(handle.fileno())",
    "os.link(temporary, path)",
    "temporary.unlink(missing_ok=True)",
    "_fsync_directory(self.root)",
    "return intent",
)
PENDING_ORDER = (
    "def _pending_deletion_ids(self) -> set[str]:",
    "pending: set[str] = set()",
    'for path in self.root.glob(".delete-*.json"):',
    "match = _DELETE_INTENT.fullmatch(path.name)",
    "if match is None:",
    "path.lstat()",
    "except FileNotFoundError:",
    "except OSError:",
    "pending.add(match.group(1))",
    "return pending",
)
RECOVER_ORDER = (
    "def _recover_deletions(self) -> None:",
    'for path in sorted(self.root.glob(".delete-*.json")):',
    "intent = self._read_delete_intent(path)",
    "except FileNotFoundError:",
    "except ValueError:",
    "self._finish_deletion(intent)",
    "except (OSError, ValueError):",
)
MISSING = "会话删除标记损坏，会话暂不可操作"


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _marker(thread_id: str, *, version: int = 1, digests: object = None,
            event_id: str = "b" * 32, extra: dict | None = None) -> bytes:
    value = {"version": version, "threadId": thread_id,
             "attachmentDigests": digests if digests is not None else ["a" * 64],
             "eventId": event_id}
    if extra:
        value.update(extra)
    return (json.dumps(value) + "\n").encode("utf-8")


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def check_delete_intent() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    read = _method(tree, source, "SessionStore", "_read_delete_intent")
    write = _method(tree, source, "SessionStore", "_write_delete_intent")
    pending = _method(tree, source, "SessionStore", "_pending_deletion_ids")
    recover = _method(tree, source, "SessionStore", "_recover_deletions")
    checked = _ordered(READ_ORDER, read, SESSION)
    checked += _ordered(WRITE_ORDER, write, SESSION)
    checked += _ordered(PENDING_ORDER, pending, SESSION)
    checked += _ordered(RECOVER_ORDER, recover, SESSION)
    # 读取一次、严格四键、摘要排序去重。
    if read.count("json.loads") != 1 or read.count("MAX_DELETE_INTENT_BYTES") != 1:
        raise ValueError(f"{SESSION} 的删除标记必须一次有界解码")
    checked += 1
    if read.count('raise ValueError("会话删除标记损坏，会话暂不可操作")') != 2:
        raise ValueError(f"{SESSION} 的删除标记必须在解码与形状两处拒绝")
    checked += 1
    if read.count("sorted(set(") != 1:
        raise ValueError(f"{SESSION} 的删除标记摘要必须排序去重")
    checked += 1
    # 写入用独占临时文件与硬链接，不能用覆盖式发布。
    if write.count("os.link") != 1 or "os.replace" in write:
        raise ValueError(f"{SESSION} 的删除标记必须硬链接发布且不覆盖")
    checked += 1
    if write.count("O_EXCL") != 1 or write.count("os.fsync") != 1:
        raise ValueError(f"{SESSION} 的删除标记临时文件必须独占且落盘")
    checked += 1
    if write.count("temporary.unlink(missing_ok=True)") != 1:
        raise ValueError(f"{SESSION} 的删除标记临时文件必须清理")
    checked += 1
    if write.rindex("_fsync_directory(self.root)") < write.index("temporary.unlink(missing_ok=True)"):
        raise ValueError(f"{SESSION} 的删除标记必须在清理后刷新目录")
    checked += 1
    # 列出阻塞会话只按名称，不读取标记内容。
    if "json.loads" in pending or "read_text" in pending:
        raise ValueError(f"{SESSION} 的阻塞列表不得读取标记内容")
    checked += 1
    if pending.count("continue") != 2:
        raise ValueError(f"{SESSION} 的阻塞列表必须跳过无效与消失的标记")
    checked += 1
    # 恢复时保留损坏标记，并让单个失败不阻塞启动。
    if recover.count("continue") != 3:
        raise ValueError(f"{SESSION} 的删除恢复必须保留损坏标记并继续")
    checked += 1
    if recover.index("self._finish_deletion(intent)") < recover.index("except ValueError:"):
        raise ValueError(f"{SESSION} 的删除恢复必须先读取再完成")
    checked += 1
    # 初始化时收紧状态目录中的删除标记权限。
    if '*self.root.glob(".delete-*.json"),' not in source:
        raise ValueError(f"{SESSION} 的初始化必须收紧删除标记权限")
    checked += 1
    # 完成删除时才移除标记，且先收紧权限再删除并刷新目录。
    finish = _method(tree, source, "SessionStore", "_finish_deletion")
    ordered = (
        "intent_path = self._delete_intent_path(thread_id)",
        "if intent_path.exists():",
        "restrict_private_file(intent_path)",
        "intent_path.unlink()",
        "_fsync_directory(self.root)",
    )
    checked += _ordered(ordered, finish, SESSION)
    # 行为：写入、读回、阻塞与临时文件。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        store = SessionStore(root)
        try:
            thread_id = "0123456789ab"
            other = "fedcba987654"
            (root / f"{thread_id}.jsonl").write_text("{}\n", encoding="utf-8")
            (root / f"{other}.jsonl").write_text("{}\n", encoding="utf-8")
            first, last = "a" * 64, "c" * 64
            entries = [
                {"type": "attachment", "payload": {"digest": first}},
                {"type": "attachment", "payload": {"digest": first}},
                {"type": "attachment", "payload": {"digest": "BAD"}},
                {"type": "user", "payload": {"digest": "b" * 64}},
                {"type": "attachment", "payload": {"digest": last}},
            ]
            intent = store._write_delete_intent(thread_id, entries)
            if set(intent) != {"version", "threadId", "attachmentDigests", "eventId"}:
                raise ValueError("删除标记必须只含四个字段")
            checked += 1
            if intent["version"] != 1 or intent["threadId"] != thread_id:
                raise ValueError("删除标记的版本或会话不符")
            checked += 1
            if intent["attachmentDigests"] != sorted({first, last}):
                raise ValueError("删除标记的摘要必须去重排序并忽略非法项")
            checked += 1
            event_id = intent["eventId"]
            if len(event_id) != 32 or any(char not in "0123456789abcdef" for char in event_id):
                raise ValueError("删除标记的事件编号必须是 32 位十六进制")
            checked += 1
            marker = store._delete_intent_path(thread_id)
            if marker.name != f".delete-{thread_id}.json" or not marker.exists():
                raise ValueError("删除标记的文件名或落盘位置变化")
            checked += 1
            if stat.S_IMODE(marker.stat().st_mode) != 0o600:
                raise ValueError("删除标记必须是 0600 私有文件")
            checked += 1
            if not store.has_pending_deletion(thread_id) or store.has_pending_deletion(other):
                raise ValueError("删除标记必须只阻塞对应会话")
            checked += 1
            ids = store._pending_deletion_ids()
            if thread_id not in ids or other in ids:
                raise ValueError("阻塞列表必须只来自删除标记名称")
            checked += 1
            if store._write_delete_intent(thread_id, []) != intent:
                raise ValueError("已存在的删除标记必须读回而不覆盖")
            checked += 1
            if store._read_delete_intent(marker) != intent:
                raise ValueError("删除标记读回必须与写入一致")
            checked += 1
            leftovers = [path.name for path in root.iterdir() if path.name.endswith(".tmp")]
            if leftovers:
                raise ValueError(f"删除标记不得残留临时文件：{leftovers}")
            checked += 1
        finally:
            store.close()
        # 合法标记在重启时完成删除，其他会话保留。
        restarted = SessionStore(root)
        try:
            if (root / f"{thread_id}.jsonl").exists() or marker.exists():
                raise ValueError("重启后合法删除标记必须完成删除")
            checked += 1
            if restarted.has_pending_deletion(thread_id):
                raise ValueError("完成删除后不得继续阻塞会话")
            checked += 1
            if not (root / f"{other}.jsonl").exists():
                raise ValueError("删除一个会话不得影响其他会话")
            checked += 1
        finally:
            restarted.close()
    # 损坏标记在重启后保留并继续阻塞。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        store = SessionStore(root)
        thread_id = "0123456789ac"
        try:
            (root / f"{thread_id}.jsonl").write_text("{}\n", encoding="utf-8")
            marker = store._delete_intent_path(thread_id)
            marker.write_bytes(b"{}")
        finally:
            store.close()
        restarted = SessionStore(root)
        try:
            if not marker.exists() or not restarted.has_pending_deletion(thread_id):
                raise ValueError("损坏的删除标记必须保留并继续阻塞")
            checked += 1
            if thread_id not in restarted._pending_deletion_ids():
                raise ValueError("损坏的删除标记仍必须出现在阻塞列表")
            checked += 1
            damaged = (
                ("非 JSON", b"not json\n"),
                ("非对象", b"[]\n"),
                ("空对象", b"{}\n"),
                ("版本不符", _marker(thread_id, version=2)),
                ("会话不符", _marker("fedcba987654")),
                ("额外字段", _marker(thread_id, extra={"extra": True})),
                ("摘要非列表", _marker(thread_id, digests="a" * 64)),
                ("摘要非法", _marker(thread_id, digests=["BAD"])),
                ("事件编号非法", _marker(thread_id, event_id="xyz")),
                ("超过大小限制", b" " * (1024 * 1024 + 1)),
            )
            for label, payload in damaged:
                marker.write_bytes(payload)
                _expect_error(lambda path=marker: restarted._read_delete_intent(path), MISSING, label)
                checked += 1
            bad_name = root / ".delete-zzz.json"
            bad_name.write_bytes(_marker(thread_id))
            _expect_error(lambda: restarted._read_delete_intent(bad_name),
                          "会话删除标记名称无效", "文件名非法")
            checked += 1
            try:
                restarted._read_delete_intent(root / ".delete-aaaaaaaaaaaa.json")
            except FileNotFoundError:
                checked += 1
            else:
                raise ValueError("不存在的删除标记必须抛 FileNotFoundError")
            _expect_error(lambda: restarted._delete_intent_path("ZZZ"),
                          "threadId 格式无效", "非法会话编号")
            checked += 1
        finally:
            restarted.close()
    # 行为：标记名称过滤、大小边界、摘要归一与损坏标记不覆盖。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        store = SessionStore(root)
        try:
            thread_id = "0123456789ad"
            marker = store._delete_intent_path(thread_id)
            marker.write_bytes(_marker(thread_id, digests=["c" * 64, "a" * 64, "a" * 64]))
            invalid_name = root / ".delete-zzz.json"
            invalid_name.write_bytes(_marker(thread_id))
            ids = store._pending_deletion_ids()
            if thread_id not in ids or "zzz" in ids:
                raise ValueError("阻塞列表必须忽略非法名称并保留合法标记")
            checked += 1
            intent = store._read_delete_intent(marker)
            if intent["attachmentDigests"] != ["a" * 64, "c" * 64]:
                raise ValueError("读回摘要必须排序去重")
            checked += 1
            payload = _marker(thread_id)
            marker.write_bytes(payload + b" " * (MAX_DELETE_INTENT_BYTES - len(payload)))
            if store._read_delete_intent(marker)["threadId"] != thread_id:
                raise ValueError("恰好达到大小上限的标记必须可读")
            checked += 1
            marker.write_bytes(payload + b" " * (MAX_DELETE_INTENT_BYTES - len(payload) + 1))
            _expect_error(lambda: store._read_delete_intent(marker), MISSING, "超出大小限制")
            checked += 1
            marker.write_bytes(b"{}\n")
            before = marker.read_bytes()
            _expect_error(lambda: store._write_delete_intent(thread_id, []), MISSING, "损坏标记覆盖")
            checked += 1
            if marker.read_bytes() != before:
                raise ValueError("损坏标记被拒绝时不得改写")
            checked += 1
        finally:
            store.close()
    # 行为：重开存储时收紧未读取的标记权限。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        thread_id = "0123456789ae"
        store = SessionStore(root)
        try:
            marker = root / ".delete-zzz.json"
            marker.write_bytes(b"{}\n")
            marker.chmod(0o644)
        finally:
            store.close()
        restarted = SessionStore(root)
        try:
            if stat.S_IMODE(marker.stat().st_mode) != 0o600:
                raise ValueError("重开存储必须收紧未读取的标记权限")
            checked += 1
            if "zzz" in restarted._pending_deletion_ids() or restarted.has_pending_deletion(thread_id):
                raise ValueError("名称非法的标记不得进入阻塞列表")
            checked += 1
        finally:
            restarted.close()
    # 行为：单个删除失败不得阻断其他标记完成。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        blocked = "0123456789af"
        cleared = "fedcba987655"
        store = SessionStore(root)
        try:
            (root / f"{blocked}.jsonl").write_text("{}\n", encoding="utf-8")
            (root / f"{cleared}.jsonl").write_text("{}\n", encoding="utf-8")
            blocked_marker = store._delete_intent_path(blocked)
            cleared_marker = store._delete_intent_path(cleared)
            blocked_marker.write_bytes(_marker(blocked, event_id="a" * 32))
            cleared_marker.write_bytes(_marker(cleared, event_id="c" * 32))
        finally:
            store.close()
        (root / f"{blocked}.jsonl").unlink()
        link_target = Path(temporary) / "blocked-backup.jsonl"
        link_target.write_text("{}\n", encoding="utf-8")
        os.link(link_target, root / f"{blocked}.jsonl")
        restarted = SessionStore(root)
        try:
            if not blocked_marker.exists():
                raise ValueError("无法完成的删除标记必须保留")
            checked += 1
            if (root / f"{blocked}.jsonl").stat().st_nlink != 2:
                raise ValueError("无法完成的删除不得改动目标")
            checked += 1
            if cleared_marker.exists() or (root / f"{cleared}.jsonl").exists():
                raise ValueError("其他合法标记必须继续完成删除")
            checked += 1
            if not restarted.has_pending_deletion(blocked) or restarted.has_pending_deletion(cleared):
                raise ValueError("恢复隔离后阻塞状态必须只保留失败会话")
            checked += 1
        finally:
            restarted.close()
    return checked


def main() -> int:
    try:
        checked = check_delete_intent()
    except (ValueError, SyntaxError) as error:
        print(f"删除标记核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除标记一致：{checked} 项校验、原子发布与恢复校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
