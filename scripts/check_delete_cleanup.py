#!/usr/bin/env python3
"""对照删除会话时私有临时文件与会话文件的清理边界。

`_remove_private_temporaries` 只删除当前用户拥有的普通文件：硬链接计数为 2
时必须能确认目标文件也是同一 inode 的私有普通文件（独占临时文件的正常形态），
其余链接计数一律暂停；删除前收紧权限，删除后刷新目录。`_remove_thread_files`
先清理会话临时文件、删除标记临时文件与事件日志临时文件三类残留，再删除会话
主体；主体必须是链接计数为 1 的私有普通文件，缺失则直接返回。本脚本在临时
目录构造 `SessionStore` 做行为对照并扫描源码；不访问网络、模型或招聘平台。
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
from boss_harness.session import SessionStore  # noqa: E402

TEMPORARIES_ORDER = (
    "def _remove_private_temporaries(self, paths: list[Path], target: Path) -> None:",
    'current_uid = getattr(os, "getuid", lambda: -1)()',
    "for path in paths:",
    "original = path.lstat()",
    "except FileNotFoundError:",
    "continue",
    "if not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid:",
    'raise ValueError("会话删除遇到非私有普通文件，清理已暂停")',
    "if original.st_nlink == 2:",
    "target_stat = target.lstat()",
    "target_stat = None",
    "if (target_stat is None or not stat.S_ISREG(target_stat.st_mode)",
    "or target_stat.st_uid != current_uid or target_stat.st_nlink != 2",
    "or (original.st_dev, original.st_ino) != (target_stat.st_dev, target_stat.st_ino)):",
    'raise ValueError("会话删除遇到无法确认的硬链接临时文件，清理已暂停")',
    "elif original.st_nlink != 1:",
    'raise ValueError("会话删除遇到非私有普通文件，清理已暂停")',
    "restrict_private_file(path)",
    "path.unlink()",
    "if paths:",
    "_fsync_directory(paths[0].parent)",
)
THREAD_FILES_ORDER = (
    "def _remove_thread_files(self, thread_id: str) -> None:",
    "session_path = self.path_for(thread_id)",
    'self._remove_private_temporaries(list(self.root.glob(f".{thread_id}.jsonl.*.tmp")), session_path)',
    'self._remove_private_temporaries(list(self.root.glob(f".delete-{thread_id}.*.tmp")),',
    'list(self.root.parent.glob(f".events.jsonl.delete-{thread_id}.*.tmp")), self.events_path)',
    "original = session_path.lstat()",
    "except FileNotFoundError:",
    "return",
    "if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1 or original.st_uid != current_uid):",
    'raise ValueError("会话删除遇到非私有普通文件，清理已暂停")',
    "restrict_private_file(session_path)",
    "session_path.unlink()",
    "_fsync_directory(self.root)",
)


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


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def _temp(root: Path, thread_id: str, suffix: str) -> Path:
    return root / f".{thread_id}.jsonl.{suffix}.tmp"


def check_delete_cleanup() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    temporaries = _method(tree, source, "SessionStore", "_remove_private_temporaries")
    thread_files = _method(tree, source, "SessionStore", "_remove_thread_files")
    checked = _ordered(TEMPORARIES_ORDER, temporaries, SESSION)
    checked += _ordered(THREAD_FILES_ORDER, thread_files, SESSION)
    # 非私有拒绝在临时清理里恰好两处，主体检查另有一处。
    if temporaries.count('raise ValueError("会话删除遇到非私有普通文件，清理已暂停")') != 2:
        raise ValueError(f"{SESSION} 的临时清理必须有两处非私有拒绝")
    checked += 1
    if thread_files.count('raise ValueError("会话删除遇到非私有普通文件，清理已暂停")') != 1:
        raise ValueError(f"{SESSION} 的主体清理必须恰好一处非私有拒绝")
    checked += 1
    if temporaries.count('raise ValueError("会话删除遇到无法确认的硬链接临时文件，清理已暂停")') != 1:
        raise ValueError(f"{SESSION} 的硬链接临时文件必须恰好一处拒绝")
    checked += 1
    if temporaries.count("original.st_nlink == 2") != 1:
        raise ValueError(f"{SESSION} 的临时清理只对链接计数为 2 的文件确认目标")
    checked += 1
    # 三类临时文件各清理一次，且都先于会话主体删除。
    for pattern in ('f".{thread_id}.jsonl.*.tmp"', 'f".delete-{thread_id}.*.tmp"',
                    'f".events.jsonl.delete-{thread_id}.*.tmp"'):
        if thread_files.count(pattern) != 1:
            raise ValueError(f"{SESSION} 的临时清理必须恰好覆盖：{pattern}")
        checked += 1
    if thread_files.index("original = session_path.lstat()") < thread_files.index('f".{thread_id}.jsonl.*.tmp"'):
        raise ValueError(f"{SESSION} 的临时文件必须先于会话主体清理")
    checked += 1
    if thread_files.count("_fsync_directory(self.root)") != 1:
        raise ValueError(f"{SESSION} 的会话主体删除必须刷新目录")
    checked += 1
    # 行为：临时文件的普通、缺失与硬链接形态。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("清理")["id"]
            target = store.root / "target.bin"
            target.write_bytes(b"x")
            plain = _temp(store.root, thread_id, "plain")
            plain.write_bytes(b"x")
            store._remove_private_temporaries([plain], target)
            if plain.exists():
                raise ValueError("普通临时文件必须被删除")
            checked += 1
            missing = _temp(store.root, thread_id, "missing")
            store._remove_private_temporaries([missing], target)
            checked += 1
            shared = _temp(store.root, thread_id, "shared")
            os.link(target, shared)
            store._remove_private_temporaries([shared], target)
            if shared.exists() or not target.exists():
                raise ValueError("独占临时文件必须删除且保留目标")
            checked += 1
            if (target.stat().st_mode & 0o777) != 0o600:
                raise ValueError("硬链接目标必须随临时文件一并收紧权限")
            checked += 1
        finally:
            store.close()
    # 行为：临时文件的拒绝形态。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("拒绝")["id"]
            target = store.root / "target.bin"
            target.write_bytes(b"x")
            orphan = _temp(store.root, thread_id, "orphan")
            other = store.root / "other.bin"
            other.write_bytes(b"y")
            os.link(other, orphan)
            _expect_error(lambda: store._remove_private_temporaries([orphan], target),
                          "会话删除遇到无法确认的硬链接临时文件，清理已暂停", "目标缺失")
            checked += 1
            if not orphan.exists():
                raise ValueError("被拒绝的临时文件不得被删除")
            checked += 1
            another = store.root / "another.bin"
            another.write_bytes(b"w")
            different = _temp(store.root, thread_id, "different")
            os.link(another, different)
            _expect_error(lambda: store._remove_private_temporaries([different], other),
                          "会话删除遇到无法确认的硬链接临时文件，清理已暂停", "目标不同 inode")
            checked += 1
            triple = _temp(store.root, thread_id, "triple")
            first = store.root / "first.bin"
            second = store.root / "second.bin"
            first.write_bytes(b"1")
            os.link(first, second)
            os.link(first, triple)
            _expect_error(lambda: store._remove_private_temporaries([triple], first),
                          "会话删除遇到非私有普通文件，清理已暂停", "三重链接")
            checked += 1
            link = _temp(store.root, thread_id, "link")
            link.symlink_to(other)
            _expect_error(lambda: store._remove_private_temporaries([link], other),
                          "会话删除遇到非私有普通文件，清理已暂停", "符号链接")
            checked += 1
            directory = _temp(store.root, thread_id, "dir")
            directory.mkdir()
            _expect_error(lambda: store._remove_private_temporaries([directory], other),
                          "会话删除遇到非私有普通文件，清理已暂停", "目录")
            checked += 1
        finally:
            store.close()
    # 行为：会话主体的清理与三类临时文件。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("主体")["id"]
            session_path = store.path_for(thread_id)
            session_temp = _temp(store.root, thread_id, "session")
            session_temp.write_bytes(b"x")
            marker_temp = store.root / f".delete-{thread_id}.marker.tmp"
            marker_temp.write_bytes(b"x")
            event_temp = store.root.parent / f".events.jsonl.delete-{thread_id}.event.tmp"
            event_temp.write_bytes(b"x")
            store._remove_thread_files(thread_id)
            if session_path.exists():
                raise ValueError("会话主体必须被删除")
            checked += 1
            if session_temp.exists() or marker_temp.exists() or event_temp.exists():
                raise ValueError("三类临时文件都必须被清理")
            checked += 1
            store._remove_thread_files(thread_id)
            checked += 1
            missing_thread = "000000000000"
            store._remove_thread_files(missing_thread)
            checked += 1
            linked_id = store.create("硬链接")["id"]
            linked_path = store.path_for(linked_id)
            linked_other = store.root / "linked-other.bin"
            os.link(linked_path, linked_other)
            _expect_error(lambda: store._remove_thread_files(linked_id),
                          "会话删除遇到非私有普通文件，清理已暂停", "会话硬链接")
            checked += 1
            link_id = store.create("链接主体")["id"]
            link_path = store.path_for(link_id)
            link_target = store.root / "link-target.bin"
            link_target.write_bytes(b"z")
            link_path.unlink()
            link_path.symlink_to(link_target)
            _expect_error(lambda: store._remove_thread_files(link_id),
                          "会话删除遇到非私有普通文件，清理已暂停", "会话符号链接")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_delete_cleanup()
    except (ValueError, SyntaxError) as error:
        print(f"会话删除清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话删除清理一致：{checked} 项私有文件与链接边界校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
