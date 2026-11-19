"""Explicit, reversible index repair; rollouts and events are never rewritten."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from boss_harness.ownership import StateDirectoryOwner
from boss_harness.private_files import (
    ensure_private_directory,
    open_private_file,
    resolve_private_path,
    restrict_private_file,
)
from boss_harness.session import SessionStore, _fsync_directory


def _manifest_entry(path: Path) -> dict:
    """计算清单条目：大小与摘要必须来自同一描述符，且移动前核对路径身份。

    ``stat`` 后再按路径打开会在两步之间被外部替换，让清单里的大小和摘要来自不同
    版本；这里用 ``restrict_private_file`` 固定普通文件与权限，再按路径打开并核对
    dev/ino，最后直接从同一句柄取大小并摘要。替换发生在校验之后时 ``os.replace``
    仍可能移动新文件，因此调用方在移动前再次核对路径身份。
    """
    uid = os.getuid()
    original = path.lstat()
    if not stat.S_ISREG(original.st_mode) or original.st_uid != uid:
        raise ValueError("状态文件必须是当前用户拥有的普通文件")
    restrict_private_file(path)
    descriptor = open_private_file(path, os.O_RDONLY)
    with os.fdopen(descriptor, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if ((opened.st_dev, opened.st_ino) != (original.st_dev, original.st_ino)
                or not stat.S_ISREG(opened.st_mode) or opened.st_uid != uid):
            raise ValueError("状态文件已变化，请重试索引修复")
        digest = hashlib.sha256()
        size = 0
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def repair_index(root: Path) -> dict:
    root = resolve_private_path(root)
    # 修复只针对已有状态目录：路径写错时不新建目录、不报告「已修复」。占用锁会创建目录，须先核对。
    # 只把确实不存在当作缺失；权限不足、路径中有非目录等仍按原有的系统错误报告。
    try:
        root.lstat()
    except FileNotFoundError:
        raise ValueError("状态目录不存在，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR") from None
    owner = StateDirectoryOwner(root)
    backup = root / "repairs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    names = ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm")
    moved: list[str] = []
    rebuilding = False
    try:
        ensure_private_directory(backup)
        manifest = []
        for name in names:
            source = root / name
            try:
                original = source.lstat()
            except FileNotFoundError:
                continue
            entry = _manifest_entry(source)
            # 校验与移动之间路径可能被换掉；只移动校验过的那个 inode。
            visible = source.lstat()
            if ((visible.st_dev, visible.st_ino) != (original.st_dev, original.st_ino)
                    or not stat.S_ISREG(visible.st_mode)):
                raise ValueError("状态文件已变化，请重试索引修复")
            manifest.append({"name": name, **entry})
            os.replace(source, backup / name)
            moved.append(name)
        descriptor = open_private_file(backup / "manifest.json", os.O_WRONLY | os.O_EXCL)
        with os.fdopen(descriptor, "wb") as output:
            output.write((json.dumps(manifest, indent=2) + "\n").encode())
            output.flush()
            os.fsync(output.fileno())
        # 目录项要等目录 fsync 后才落盘：先备份目录（移入的文件与清单），再状态根目录
        # （库文件的移除）。顺序保证崩溃时最多留下重复副本，不会出现根目录已删而备份缺失。
        _fsync_directory(backup)
        _fsync_directory(root)
        rebuilding = True
        store = SessionStore(root / "sessions")
        count = len(store.list_threads(include_archived=True))
        cursor = store.latest_event_cursor()
        skipped = sorted(store.unreadable_threads)
        store.close()
        summary = {"repaired": True, "backupPath": str(backup), "threads": count,
                   "eventCursor": cursor}
        if skipped:
            summary["skipped"] = skipped
        return summary
    except Exception:
        # Keep the failed candidate as well as the original database set.
        moved_failed = False
        if rebuilding:
            failed = backup / "failed-candidate"
            ensure_private_directory(failed)
            for name in names:
                source = root / name
                try:
                    source.lstat()
                except FileNotFoundError:
                    continue
                restrict_private_file(source)
                os.replace(source, failed / name)
                moved_failed = True
        for name in moved:
            os.replace(backup / name, root / name)
        # 回滚也改变了目录项：先同步新候选目录与备份目录，最后同步状态根目录。
        # 与成功路径相同的顺序保证崩溃时最多留下重复副本，不会让根目录先看见
        # 已删除的库文件；同步失败继续沿用原异常路径上报。
        if moved_failed:
            _fsync_directory(failed)
        _fsync_directory(backup)
        _fsync_directory(root)
        raise
    finally:
        owner.close()
