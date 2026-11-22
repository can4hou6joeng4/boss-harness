#!/usr/bin/env python3
"""核对状态目录独占锁的获取、释放与失败顺序。

ownership.py 用一个非阻塞 flock 声明状态目录所有权：拿不到锁时先释放描述符，
再以固定可读错误拒绝。锁文件属于状态标志，关闭时不得删除。任一顺序被删改都会
让两个内核共用同一状态目录，因此静态固定。
"""

from __future__ import annotations

import errno
import gc
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/ownership.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.ownership import StateDirectoryOwner  # noqa: E402

CONSTANT_FRAGMENTS = (
    "Exclusive runtime ownership precedes recovery or index maintenance.",
    "class StateDirectoryOwner:",
)
INIT_FRAGMENTS = (
    "self.root = resolve_private_path(root)",
    "ensure_private_directory(self.root)",
    "self._fd: int | None = None",
    'open_private_file(self.root / ".owner.lock", os.O_RDWR)',
    # 非阻塞独占锁：第二个内核必须立刻被拒绝，而不是挂起等待。
    "fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)",
    "except BlockingIOError:",
    'raise OSError(errno.EWOULDBLOCK, "状态目录已由另一个内核使用；请先关闭该内核") from None',
    "except OSError:",
)
CLOSE_FRAGMENTS = (
    # 先摘掉字段再关闭：重复 close 与 __del__ 都不会二次关闭同一描述符。
    'fd, self._fd = getattr(self, "_fd", None), None',
    "if fd is not None:",
    "os.close(fd)",
    "def __del__(self) -> None:",
    "self.close()",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "`maintenance.py` 的索引修复必须先用 `lstat` 核对状态目录存在并在缺失时以固定说明拒绝，非空且不含任何状态标志（占用锁、`sessions`、`state.sqlite3`）的目录同样拒绝，再获取占用锁与创建备份目录"),
    (USER_GUIDE, "检查不获取占用锁、不打开索引或会话、不尝试真实写入"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"状态目录占用行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_occupied(call, label: str) -> int:
    started = time.monotonic()
    try:
        call()
    except OSError as error:
        elapsed = time.monotonic() - started
        checked = _expect_value(error.errno, errno.EWOULDBLOCK, f"{label}错误码")
        checked += _expect_value(
            error.strerror, "状态目录已由另一个内核使用；请先关闭该内核", f"{label}文案")
        checked += _expect_value(elapsed < 1.0, True, f"{label}非阻塞")
        return checked
    raise ValueError(f"状态目录占用行为变化 {label}：期望 OSError，实际获取成功")


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        root = Path(temporary) / "state"
        lock = root / ".owner.lock"
        owner = StateDirectoryOwner(root)
        checked += _expect_value(owner.root, root.resolve(), "根路径解析")
        checked += _expect_value(lock.is_file(), True, "锁文件创建")
        checked += _expect_value(stat.S_IMODE(lock.stat().st_mode), 0o600, "锁文件权限")
        checked += _expect_value(stat.S_IMODE(root.stat().st_mode), 0o700, "状态目录权限")

        candidate = StateDirectoryOwner.__new__(StateDirectoryOwner)
        checked += _expect_occupied(lambda: candidate.__init__(root), "互斥拒绝")
        checked += _expect_value(getattr(candidate, "_fd", "missing"), None,
                                 "失败释放描述符")
        candidate.close()
        checked += _expect_value(getattr(candidate, "_fd", "missing"), None, "失败重复关闭")

        checked += _expect_value(owner._fd is not None, True, "拒绝后持有者保持")
        owner.close()
        owner.close()
        checked += _expect_value(owner._fd, None, "重复关闭摘字段")
        checked += _expect_value(lock.exists(), True, "关闭保留锁文件")

        again = StateDirectoryOwner(root)
        checked += _expect_value(again._fd is not None, True, "关闭后重新获取")
        again.close()

        bare = StateDirectoryOwner.__new__(StateDirectoryOwner)
        bare.close()
        checked += _expect_value(getattr(bare, "_fd", None), None, "未初始化关闭安全")

        doomed = StateDirectoryOwner(root)
        del doomed
        gc.collect()
        after = StateDirectoryOwner(root)
        checked += _expect_value(after._fd is not None, True, "析构释放锁")
        after.close()
    return checked


def check_ownership() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(INIT_FRAGMENTS, module, MODULE)
    checked += _expect(CLOSE_FRAGMENTS, module, MODULE)
    # 两种失败分支都必须先释放描述符再上报，不能泄漏已打开的锁文件。
    checked += _ordered(
        (
            "except BlockingIOError:",
            "self.close()",
            'raise OSError(errno.EWOULDBLOCK, "状态目录已由另一个内核使用；请先关闭该内核") from None',
            "except OSError:\n            self.close()\n            raise",
        ),
        module,
        MODULE,
    )
    # 释放顺序：先清字段，再按局部变量关闭。
    checked += _ordered(
        (
            'fd, self._fd = getattr(self, "_fd", None), None',
            "if fd is not None:",
            "os.close(fd)",
        ),
        module,
        MODULE,
    )
    # 锁文件是状态标志：关闭不能删除它，也不能改用共享锁或阻塞等待。
    if "unlink" in module or "os.remove" in module:
        raise ValueError(f"{MODULE} 不得删除占用锁文件")
    if "LOCK_SH" in module:
        raise ValueError(f"{MODULE} 必须使用独占锁")
    if "LOCK_BLOCK" in module:
        raise ValueError(f"{MODULE} 不得无限期等待占用锁")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_ownership()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"状态目录占用核对失败，{error}", file=sys.stderr)
        return 2
    print(f"状态目录占用一致：{checked} 项独占与释放防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
