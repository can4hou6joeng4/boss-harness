#!/usr/bin/env python3
"""核对状态目录与状态文件的私有权限边界，成功时输出各类核对项数量。"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HARNESS = "harness/src/boss_harness"
PRIVATE_FILES = f"{HARNESS}/private_files.py"
PRIVATE_FRAGMENTS = (
    "def ensure_private_directory(path: Path, mode: int = 0o700)",
    "def check_private_directory(path: Path)",
    "_walk_private_directory(path, 0o700, create=False)",
    "os.O_NOFOLLOW",
    'getattr(os, "O_NOFOLLOW", 0)',
    "os.fchmod(child, mode)",
    "os.fchmod(descriptor, 0o600)",
    "opened.st_uid != uid",
    "(opened.st_dev, opened.st_ino)",
    "_clear_extended_acl(",
    "状态目录不能是文件系统根目录",
    "if opened.st_mode & 0o022:",
)
CALL_SITES = (
    ("ownership.py", "ensure_private_directory(self.root)"),
    ("ownership.py", 'open_private_file(self.root / ".owner.lock", os.O_RDWR)'),
    ("persistence.py", "ensure_private_directory(self.path.parent)"),
    ("persistence.py", "open_private_file(self.path, os.O_RDWR | os.O_EXCL)"),
    ("persistence.py", "restrict_private_file(self.path)"),
    ("session.py", "ensure_private_directory(self.root)"),
    ("session.py", "open_private_file("),
    ("session.py", "restrict_private_file("),
    ("snapshot_store.py", "ensure_private_directory(self.root)"),
    ("snapshot_store.py", "open_private_file("),
    ("snapshot_store.py", "restrict_private_file("),
    ("settings.py", "open_private_file(path, os.O_RDONLY)"),
    ("maintenance.py", "restrict_private_file(path)"),
    ("maintenance.py", 'open_private_file(backup / "manifest.json"'),
    ("startup_check.py", "check_private_directory(state_dir.resolve())"),
)
PROTECTED_MODULES = (
    "ownership.py",
    "persistence.py",
    "session.py",
    "snapshot_store.py",
    "settings.py",
    "maintenance.py",
    "resources.py",
)
# 索引修复只针对已有状态目录：存在性核对必须先于会创建目录的占用锁与备份目录。
REPAIR_ORDERED = (
    "root = resolve_private_path(root)",
    "root.lstat()",
    'raise ValueError("状态目录不存在，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR") from None',
    "owner = StateDirectoryOwner(root)",
    "ensure_private_directory(backup)",
)
DIRECT_WRITE = re.compile(r'(?<!fd)\b(?:open\([^)]*["\']([wa])|(write_text|write_bytes)\()')


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def check_private_files() -> tuple[int, int, int]:
    text = _read(PRIVATE_FILES)
    missing = [fragment for fragment in PRIVATE_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError("private_files.py 缺少私有权限原语：" + "、".join(missing))
    for name, fragment in CALL_SITES:
        if fragment not in _read(f"{HARNESS}/{name}"):
            raise ValueError(f"{name} 缺少私有状态调用：{fragment}")
    for name in PROTECTED_MODULES:
        match = DIRECT_WRITE.search(_read(f"{HARNESS}/{name}"))
        if match is not None:
            raise ValueError(f"{name} 不得直接写状态文件：{match.group(0)}")
    maintenance = _read(f"{HARNESS}/maintenance.py")
    position = -1
    for fragment in REPAIR_ORDERED:
        if maintenance.count(fragment) != 1:
            raise ValueError(f"maintenance.py 的修复前置核对片段缺失或重复：{fragment}")
        found = maintenance.index(fragment)
        if found < position:
            raise ValueError(f"maintenance.py 必须先核对状态目录存在再占用或创建：{fragment}")
        position = found
    return len(PRIVATE_FRAGMENTS), len(CALL_SITES) + len(REPAIR_ORDERED), len(PROTECTED_MODULES)


def main() -> int:
    try:
        fragments, calls, modules = check_private_files()
    except ValueError as error:
        print(f"私有状态文件边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"私有状态文件边界一致：{fragments} 项权限原语、{calls} 个调用点、"
          f"{modules} 个状态模块无直接写入")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
