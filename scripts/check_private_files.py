#!/usr/bin/env python3
"""核对状态目录与状态文件的私有权限边界，成功时输出各类核对项数量。

`private_files.py` 是凭据与招聘状态文件的本地保密边界：逐组件以 `O_NOFOLLOW`
打开目录、比对 dev / inode、拒绝非当前用户所有的路径、清除 macOS 扩展 ACL，
并把文件收紧到 0o600。静态扫描固定权限原语、调用点与直接写盘禁令，行为侧用
临时目录核对目录 / 文件的创建、权限与符号链接拒绝。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import os
import re
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HARNESS = "harness/src/boss_harness"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.private_files import (  # noqa: E402
    check_private_directory,
    ensure_private_directory,
    ensure_private_file_support,
    open_private_file,
    resolve_private_path,
    restrict_private_file,
)

PRIVATE_FILES = f"{HARNESS}/private_files.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
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
    # 路径解析：3.14 起非严格 resolve 会放过符号链接环，需严格复核仍含链接的结果。
    "def _resolve_private_target(path: Path) -> Path:",
    "resolved = Path(path).resolve()",
    "if any(part.is_symlink() for part in (resolved, *resolved.parents)):",
    "return resolved.resolve(strict=True)",
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
    "names_present = {entry.name for entry in os.scandir(root)}",
    "if names_present and names_present.isdisjoint(STATE_MARKERS):",
    'raise ValueError("目标目录不是内核状态目录，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR")',
    "owner = StateDirectoryOwner(root)",
    "ensure_private_directory(backup)",
)
DIRECT_WRITE = re.compile(r'(?<!fd)\b(?:open\([^)]*["\']([wa])|(write_text|write_bytes)\()')


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"私有状态边界行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, error: type[BaseException], label: str) -> int:
    try:
        call()
    except error:
        return 1
    raise ValueError(f"私有状态边界行为变化 {label}：未抛出 {error.__name__}")


def _behavior_checks() -> int:
    checked = 0
    checked += _expect_value(ensure_private_file_support(), os.getuid(), "支持平台返回 uid")
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        # 路径解析：正常路径取真实路径；符号链接环按目录规则报错。
        checked += _expect_value(resolve_private_path(base / "x"), (base / "x").resolve(),
                                 "路径解析")
        first, second = base / "a", base / "b"
        first.symlink_to(second)
        second.symlink_to(first)
        checked += _expect_error(lambda: resolve_private_path(first), ValueError, "符号链接环")
        checked += _expect_error(lambda: ensure_private_directory(Path("/")), ValueError,
                                 "根目录拒绝")

        # 创建两层私有目录均为 0o700；只读核对对已有目录通过、对缺失路径不创建。
        state = base / "state"
        ensure_private_directory(state / "inner")
        checked += _expect_value((stat.S_IMODE(os.lstat(state).st_mode),
                                  stat.S_IMODE(os.lstat(state / "inner").st_mode)),
                                 (0o700, 0o700), "目录权限")
        checked += _expect_value(check_private_directory(state / "inner"), None, "只读核对通过")
        absent = base / "absent"
        checked += _expect_value(check_private_directory(absent / "child"), None, "缺失路径核对")
        checked += _expect_value(absent.exists(), False, "只读核对不创建")

        # 已有目录不收紧权限，也不因 0o755 被拒绝。
        shared = base / "shared"
        shared.mkdir()
        os.chmod(shared, 0o755)
        ensure_private_directory(shared)
        checked += _expect_value(stat.S_IMODE(os.lstat(shared).st_mode), 0o755,
                                 "已有目录不改权限")

        # 末级目录可被其他用户写入、父目录可被其他用户修改：都拒绝。
        loose = base / "loose"
        loose.mkdir()
        os.chmod(loose, 0o777)
        checked += _expect_error(lambda: ensure_private_directory(loose), ValueError,
                                 "末级目录可写拒绝")
        os.chmod(loose, 0o700)
        opened = base / "opened"
        opened.mkdir()
        os.chmod(opened, 0o777)
        checked += _expect_error(lambda: ensure_private_directory(opened / "child"), ValueError,
                                 "父目录可写拒绝")
        os.chmod(opened, 0o700)

        # 文件：写打开创建 0o600；读打开收紧已有 0o644；只读打开不创建缺失文件。
        target = base / "state.bin"
        descriptor = open_private_file(target, os.O_WRONLY)
        os.write(descriptor, b"state")
        os.close(descriptor)
        checked += _expect_value((target.read_bytes(), stat.S_IMODE(os.lstat(target).st_mode)),
                                 (b"state", 0o600), "文件创建")
        os.chmod(target, 0o644)
        descriptor = open_private_file(target, os.O_RDONLY)
        os.close(descriptor)
        checked += _expect_value(stat.S_IMODE(os.lstat(target).st_mode), 0o600, "读取收紧")
        missing = base / "missing.bin"
        checked += _expect_error(lambda: open_private_file(missing, os.O_RDONLY),
                                 FileNotFoundError, "只读不创建")
        checked += _expect_value(missing.exists(), False, "只读不创建文件")

        # 符号链接与目录：打开都拒绝，链接目标不被改写。
        link = base / "state.link"
        link.symlink_to(target)
        checked += _expect_error(lambda: open_private_file(link, os.O_WRONLY), OSError,
                                 "打开符号链接拒绝")
        checked += _expect_error(lambda: open_private_file(base, os.O_RDONLY), ValueError,
                                 "打开目录拒绝")

        # 收紧：普通文件到 0o600，符号链接与目录拒绝。
        os.chmod(target, 0o644)
        checked += _expect_value(restrict_private_file(target), None, "收紧普通文件")
        checked += _expect_value(stat.S_IMODE(os.lstat(target).st_mode), 0o600, "收紧后的权限")
        checked += _expect_error(lambda: restrict_private_file(link), ValueError,
                                 "收紧符号链接拒绝")
        checked += _expect_error(lambda: restrict_private_file(base), ValueError, "收紧目录拒绝")
    return checked


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def check_private_files() -> tuple[int, int, int, int]:
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
    if 'STATE_MARKERS = frozenset({".owner.lock", "sessions", "state.sqlite3"})' not in maintenance:
        raise ValueError("maintenance.py 的状态目录标志必须是占用锁、sessions 与 state.sqlite3")
    return (len(PRIVATE_FRAGMENTS), len(CALL_SITES) + len(REPAIR_ORDERED) + 1,
            len(PROTECTED_MODULES), _behavior_checks())


def _documentation_check(total: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if f"（{total} 项）" not in reference:
        raise ValueError(
            f"{TECHNICAL_REFERENCE} 缺少私有状态检查的计数：（{total} 项）")


def main() -> int:
    try:
        fragments, calls, modules, behaviors = check_private_files()
        _documentation_check(fragments + calls + modules + behaviors)
    except (ValueError, OSError) as error:
        print(f"私有状态文件边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"私有状态文件边界一致：{fragments} 项权限原语、{calls} 个调用点、"
          f"{modules} 个状态模块无直接写入、{behaviors} 项运行时校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
