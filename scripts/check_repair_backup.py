#!/usr/bin/env python3
"""对照删除会话时修复备份的清理与清单重写口径。

`_purge_repair_backups` 遍历 `repairs/` 下递归发现的 `state.sqlite3`：目录与
数据库必须是当前用户拥有的私有形态，数据库版本不得高于 `SCHEMA_VERSION`，
在事务内删除该会话的 events / turns / threads 行后 `VACUUM` 并截断 WAL；
`-wal` / `-shm` sidecar 同样按私有普通文件校验并删除；存在清单时重写
`manifest.json`，过滤两个 sidecar 条目、按实际文件更新数据库条目的 bytes 与
sha256，以独占临时文件加替换发布并刷新目录。本脚本在临时目录构造
`SessionStore` 与备份目录做行为对照，不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.persistence import SCHEMA_VERSION  # noqa: E402
from boss_harness.session import SessionStore  # noqa: E402

PURGE_ORDER = (
    "def _purge_repair_backups(self, thread_id: str) -> None:",
    'repair_root = self.root.parent / "repairs"',
    "root_stat = repair_root.lstat()",
    "except FileNotFoundError:",
    'current_uid = getattr(os, "getuid", lambda: -1)()',
    "if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != current_uid:",
    'raise ValueError("修复备份目录不可信，清理已暂停")',
    'for database_path in sorted(repair_root.rglob("state.sqlite3")):',
    "original = database_path.lstat()",
    "if (not stat.S_ISREG(original.st_mode) or original.st_uid != current_uid",
    "or original.st_nlink != 1):",
    'raise ValueError("修复备份不是私有普通文件，清理已暂停")',
    "restrict_private_file(database_path)",
    "backup = sqlite3.connect(database_path, timeout=10, isolation_level=None)",
    'backup.execute("PRAGMA busy_timeout=10000")',
    'backup.execute("PRAGMA foreign_keys=ON")',
    'backup.execute("PRAGMA synchronous=FULL")',
    'backup.execute("PRAGMA secure_delete=ON")',
    'version = int(backup.execute("PRAGMA user_version").fetchone()[0])',
    "if version > SCHEMA_VERSION:",
    'raise ValueError("修复备份包含较新索引，无法安全删除会话")',
    "tables = {row[0] for row in backup.execute(",
    '"SELECT name FROM sqlite_master WHERE type=\'table\'").fetchall()}',
    'backup.execute("BEGIN IMMEDIATE")',
    'if "events" in tables:',
    'backup.execute("DELETE FROM events WHERE thread_id=?", (thread_id,))',
    'if "turns" in tables:',
    'backup.execute("DELETE FROM turns WHERE thread_id=?", (thread_id,))',
    'if "threads" in tables:',
    'backup.execute("DELETE FROM threads WHERE id=?", (thread_id,))',
    "backup.commit()",
    "backup.rollback()",
    'backup.execute("VACUUM")',
    'result = backup.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()',
    "if result and result[0] != 0:",
    'raise OSError("修复备份 WAL 尚未收敛")',
    "backup.close()",
    "backup_directory = database_path.parent",
    'for sidecar in (database_path.with_name(database_path.name + "-wal"),',
    'database_path.with_name(database_path.name + "-shm")):',
    "sidecar_stat = sidecar.lstat()",
    "if (not stat.S_ISREG(sidecar_stat.st_mode) or sidecar_stat.st_uid != current_uid",
    "or sidecar_stat.st_nlink != 1):",
    'raise ValueError("修复备份 sidecar 不可信，清理已暂停")',
    "restrict_private_file(sidecar)",
    "sidecar.unlink()",
    "_fsync_directory(backup_directory)",
    'manifest_path = backup_directory / "manifest.json"',
    "if manifest_path.exists():",
    "restrict_private_file(manifest_path)",
    "manifest = json.loads(_read_bounded_file(",
    "manifest_path, maximum=MAX_REPAIR_MANIFEST_BYTES,",
    'label="修复备份清单").decode("utf-8"))',
    "except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):",
    'raise ValueError("修复备份清单损坏，清理已暂停")',
    "if not isinstance(manifest, list) or any(not isinstance(item, dict) for item in manifest):",
    'raise ValueError("修复备份清单格式无效，清理已暂停")',
    "updated = []",
    "for item in manifest:",
    'if item.get("name") in {"state.sqlite3-wal", "state.sqlite3-shm"}:',
    'if item.get("name") == "state.sqlite3":',
    'item = {**item, "bytes": database_path.stat().st_size,',
    '"sha256": _sha256_file(database_path)}',
    "updated.append(item)",
    'temporary = manifest_path.with_name(f".manifest.{uuid.uuid4().hex}.tmp")',
    "descriptor = open_private_file(temporary, os.O_WRONLY | os.O_EXCL)",
    'with os.fdopen(descriptor, "wb") as output:',
    'output.write((json.dumps(updated, indent=2) + "\\n").encode("utf-8"))',
    "output.flush()",
    "os.fsync(output.fileno())",
    "os.replace(temporary, manifest_path)",
    "temporary.unlink(missing_ok=True)",
    "_fsync_directory(backup_directory)",
)
REASONS = (
    "修复备份目录不可信，清理已暂停",
    "修复备份不是私有普通文件，清理已暂停",
    "修复备份包含较新索引，无法安全删除会话",
    "修复备份 sidecar 不可信，清理已暂停",
    "修复备份清单损坏，清理已暂停",
    "修复备份清单格式无效，清理已暂停",
)
TABLES = (("events", "thread_id"), ("turns", "thread_id"), ("threads", "id"))


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


def _backup(root: Path, name: str = "run-1") -> Path:
    directory = root / "repairs" / name
    directory.mkdir(parents=True)
    return directory


def _database(directory: Path, rows: dict[str, list[str]] | None = None) -> Path:
    path = directory / "state.sqlite3"
    connection = sqlite3.connect(path)
    try:
        if rows is not None:
            for table, column in TABLES:
                connection.execute(f"CREATE TABLE {table} ({column} TEXT)")
                connection.executemany(f"INSERT INTO {table} ({column}) VALUES (?)",
                                       [(value,) for value in rows.get(table, [])])
            connection.commit()
    finally:
        connection.close()
    path.chmod(0o644)
    return path


def _remaining(path: Path) -> dict[str, list[str]]:
    connection = sqlite3.connect(path)
    try:
        return {table: sorted(row[0] for row in connection.execute(f"SELECT {column} FROM {table}"))
                for table, column in TABLES}
    finally:
        connection.close()


def _wal_database(directory: Path, rows: dict[str, list[str]]) -> tuple[Path, sqlite3.Connection]:
    """构造 WAL 模式备份；保持连接以避免 SQLite 在关闭时清理 sidecar。"""
    path = directory / "state.sqlite3"
    holder = sqlite3.connect(path)
    holder.execute("PRAGMA journal_mode=WAL")
    for table, column in TABLES:
        holder.execute(f"CREATE TABLE {table} ({column} TEXT)")
        holder.executemany(f"INSERT INTO {table} ({column}) VALUES (?)",
                           [(value,) for value in rows.get(table, [])])
    holder.commit()
    return path, holder


def _set_version(path: Path, version: int) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"PRAGMA user_version={version}")
    finally:
        connection.close()


def _manifest(directory: Path, entries: list[dict]) -> Path:
    path = directory / "manifest.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    path.chmod(0o644)
    return path


def check_repair_backup() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    purge = _method(tree, source, "SessionStore", "_purge_repair_backups")
    checked = _ordered(PURGE_ORDER, purge, SESSION)
    for reason in REASONS:
        if purge.count(f'"{reason}"') != 1:
            raise ValueError(f"{SESSION} 的修复备份原因必须恰好一处：{reason}")
        checked += 1
    # 内部版本守卫读取持久化层常量，不得写死数字。
    if purge.count("SCHEMA_VERSION") != 1 or purge.count("user_version") != 1:
        raise ValueError(f"{SESSION} 的修复备份必须按 SCHEMA_VERSION 守卫版本")
    checked += 1
    for pragma in ("busy_timeout=10000", "foreign_keys=ON", "synchronous=FULL",
                   "secure_delete=ON", "wal_checkpoint(TRUNCATE)"):
        if purge.count(pragma) != 1:
            raise ValueError(f"{SESSION} 的修复备份必须恰好设置一次 {pragma}")
        checked += 1
    for statement in ("BEGIN IMMEDIATE", "VACUUM", "backup.commit()", "backup.rollback()"):
        if purge.count(statement) != 1:
            raise ValueError(f"{SESSION} 的修复备份必须恰好一处 {statement}")
        checked += 1
    if purge.count("restrict_private_file") != 3:
        raise ValueError(f"{SESSION} 的修复备份必须收紧数据库、sidecar 与清单权限")
    checked += 1
    if purge.count("_fsync_directory(backup_directory)") != 2:
        raise ValueError(f"{SESSION} 的修复备份必须刷新 sidecar 与清单所在目录")
    checked += 1
    for fragment in ('database_path.name + "-wal"', 'database_path.name + "-shm"',
                     '"state.sqlite3-wal"', '"state.sqlite3-shm"'):
        if purge.count(fragment) != 1:
            raise ValueError(f"{SESSION} 的 sidecar 数量或清单过滤变化：{fragment}")
        checked += 1
    if purge.count("os.replace(temporary, manifest_path)") != 1:
        raise ValueError(f"{SESSION} 的清单必须原子替换")
    checked += 1
    if "manifest_path.unlink" in purge:
        raise ValueError(f"{SESSION} 不得删除清单本身")
    checked += 1
    # 行为：无备份目录直接返回。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            store._purge_repair_backups("thread-a")
            checked += 1
        finally:
            store.close()
    # 行为：备份目录不可信。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            (store.root.parent / "repairs").write_text("x", encoding="utf-8")
            _expect_error(lambda: store._purge_repair_backups("thread-a"),
                          "修复备份目录不可信，清理已暂停", "备份目录是普通文件")
            checked += 1
        finally:
            store.close()
    # 行为：正常清理删除目标会话并保留其他会话，sidecar 删除，清单重写。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database = _database(directory, {
                "events": ["thread-a", "thread-b"],
                "turns": ["thread-a", "thread-b"],
                "threads": ["thread-a", "thread-b"],
            })
            wal = directory / "state.sqlite3-wal"
            shm = directory / "state.sqlite3-shm"
            wal.write_bytes(b"wal")
            shm.write_bytes(b"shm")
            manifest = _manifest(directory, [
                {"name": "state.sqlite3", "bytes": 1, "sha256": "old"},
                {"name": "state.sqlite3-wal", "bytes": 3},
                {"name": "state.sqlite3-shm", "bytes": 3},
                {"name": "notes.txt", "bytes": 4},
            ])
            store._purge_repair_backups("thread-a")
            checked += 1
            remaining = _remaining(database)
            if remaining != {"events": ["thread-b"], "turns": ["thread-b"],
                             "threads": ["thread-b"]}:
                raise ValueError(f"修复备份必须只删除目标会话：{remaining}")
            checked += 1
            if wal.exists() or shm.exists():
                raise ValueError("修复备份 sidecar 必须被删除")
            checked += 1
            if database.stat().st_mode & 0o077:
                raise ValueError("修复备份数据库权限必须被收紧")
            checked += 1
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            if [item.get("name") for item in updated] != ["state.sqlite3", "notes.txt"]:
                raise ValueError(f"修复备份清单必须过滤 sidecar 并保留其他条目：{updated}")
            checked += 1
            entry = updated[0]
            if entry.get("bytes") != database.stat().st_size:
                raise ValueError("修复备份清单必须更新数据库大小")
            checked += 1
            if entry.get("sha256") != hashlib.sha256(database.read_bytes()).hexdigest():
                raise ValueError("修复备份清单必须更新数据库摘要")
            checked += 1
            if manifest.stat().st_mode & 0o077:
                raise ValueError("修复备份清单权限必须被收紧")
            checked += 1
            if list(directory.glob(".manifest.*.tmp")):
                raise ValueError("修复备份清单临时文件必须被清理")
            checked += 1
        finally:
            store.close()
    # 行为：空库与恰好当前版本的备份被允许，且清单缺失时不创建。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database = _database(directory)
            _set_version(database, SCHEMA_VERSION)
            store._purge_repair_backups("thread-a")
            if not database.exists():
                raise ValueError("当前版本的修复备份必须保留")
            checked += 1
            if database.stat().st_mode & 0o077:
                raise ValueError("无清单时数据库权限必须被收紧")
            checked += 1
            if (directory / "manifest.json").exists():
                raise ValueError("缺少清单时不得创建")
            checked += 1
        finally:
            store.close()
    # 行为：较新版本的备份被拒绝且不修改行。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database = _database(directory, {"events": ["thread-a"], "turns": ["thread-a"],
                                             "threads": ["thread-a"]})
            _set_version(database, SCHEMA_VERSION + 1)
            _expect_error(lambda: store._purge_repair_backups("thread-a"),
                          "修复备份包含较新索引，无法安全删除会话", "较新版本")
            checked += 1
            if _remaining(database)["events"] != ["thread-a"]:
                raise ValueError("较新版本的修复备份不得删除行")
            checked += 1
        finally:
            store.close()
    # 行为：数据库硬链接与符号链接被拒绝。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database = _database(directory, {"events": ["thread-a"]})
            other = directory / "other.bin"
            os.link(database, other)
            _expect_error(lambda: store._purge_repair_backups("thread-a"),
                          "修复备份不是私有普通文件，清理已暂停", "数据库硬链接")
            checked += 1
            if not database.exists():
                raise ValueError("被拒绝的修复备份不得删除")
            checked += 1
        finally:
            store.close()
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database = _database(directory, {"events": ["thread-a"]})
            target = store.root.parent / "outside.sqlite3"
            target.write_bytes(b"x")
            database.unlink()
            database.symlink_to(target)
            _expect_error(lambda: store._purge_repair_backups("thread-a"),
                          "修复备份不是私有普通文件，清理已暂停", "数据库符号链接")
            checked += 1
        finally:
            store.close()
    # 行为：sidecar 硬链接与符号链接被拒绝（WAL 模式保持连接以保留 sidecar）。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            _database_path, holder = _wal_database(directory, {"events": ["thread-a"]})
            try:
                wal = directory / "state.sqlite3-wal"
                other = directory / "other.bin"
                os.link(wal, other)
                _expect_error(lambda: store._purge_repair_backups("thread-a"),
                              "修复备份 sidecar 不可信，清理已暂停", "sidecar 硬链接")
                checked += 1
                if not wal.exists():
                    raise ValueError("被拒绝的 sidecar 不得删除")
                checked += 1
            finally:
                holder.close()
        finally:
            store.close()
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            database, holder = _wal_database(directory, {"events": ["thread-a"]})
            try:
                target = store.root.parent / "outside.bin"
                target.write_bytes(b"x")
                shm = directory / "state.sqlite3-shm"
                shm.unlink()
                shm.symlink_to(target)
                _expect_error(lambda: store._purge_repair_backups("thread-a"),
                              "修复备份 sidecar 不可信，清理已暂停", "sidecar 符号链接")
                checked += 1
            finally:
                holder.close()
        finally:
            store.close()
    # 行为：清单损坏、非 UTF-8、格式无效都被拒绝。
    for label, payload in (("清单截断", b"{"), ("清单非 UTF-8", b"\xff"),
                           ("清单非列表", b"{}"), ("清单元素非对象", b"[1]")):
        with tempfile.TemporaryDirectory() as temporary:
            store = SessionStore(Path(temporary) / "sessions")
            try:
                directory = _backup(store.root.parent)
                _database(directory, {"events": ["thread-a"]})
                (directory / "manifest.json").write_bytes(payload)
                expected = ("修复备份清单损坏，清理已暂停" if label in ("清单截断", "清单非 UTF-8")
                            else "修复备份清单格式无效，清理已暂停")
                _expect_error(lambda: store._purge_repair_backups("thread-a"), expected, label)
                checked += 1
            finally:
                store.close()
    # 行为：递归发现嵌套备份目录并逐个清理。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            first = _backup(store.root.parent, "run-1")
            second = store.root.parent / "repairs" / "run-2" / "nested"
            second.mkdir(parents=True)
            _database(first, {"events": ["thread-a", "thread-b"]})
            _database(second, {"events": ["thread-a", "thread-c"]})
            store._purge_repair_backups("thread-a")
            if _remaining(first / "state.sqlite3")["events"] != ["thread-b"]:
                raise ValueError("第一份修复备份必须只删除目标会话")
            checked += 1
            if _remaining(second / "state.sqlite3")["events"] != ["thread-c"]:
                raise ValueError("嵌套修复备份必须只删除目标会话")
            checked += 1
        finally:
            store.close()
    # 行为：空清单被重写为规范空列表。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            directory = _backup(store.root.parent)
            _database(directory)
            manifest = _manifest(directory, [])
            store._purge_repair_backups("thread-a")
            if manifest.read_text(encoding="utf-8") != "[]\n":
                raise ValueError("空清单必须被规范重写")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_repair_backup()
    except (ValueError, SyntaxError) as error:
        print(f"修复备份清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"修复备份清理一致：{checked} 项所有权、版本与清单重写校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
