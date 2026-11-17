"""Harness-local settings persisted next to sessions and snapshots.

The file is intentionally small and optional: a missing or malformed config must
never prevent the kernel from starting, so reads fall back to built-in defaults.
Writes are atomic and merge into the existing object to keep unrelated keys.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

from boss_harness.compaction import verified_policy
from boss_harness.private_files import open_private_file

CONFIG_FILE = "config.json"
AUTO_COMPACTION_FIELDS = ("enabled", "triggerPercent", "keepRecentTokens")
_MAX_CONFIG_BYTES = 256 * 1024
# 配置只承载少量标量设置；与工具参数、事件载荷同级的嵌套上限。
_MAX_CONFIG_DEPTH = 64


def _within_depth(value: object, limit: int = _MAX_CONFIG_DEPTH) -> bool:
    """迭代检测嵌套深度，不依赖解析器或编码器的递归余量。

    与自动压缩无关的深层数组也能让 ``json.dumps(indent=2)`` 在纯 Python
    编码器中抛 ``RecursionError``；迭代检测把这类配置整体按不可读处理。
    """
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if isinstance(current, dict):
            if depth >= limit:
                return False
            stack.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            if depth >= limit:
                return False
            stack.extend((child, depth + 1) for child in current)
    return True


def _read_object(path: Path) -> dict | None:
    """Return the stored JSON object, or None when absent / unreadable / not an object.

    大小判定必须来自实际读取的那个描述符：先对路径 ``stat`` 再按路径 ``read_text``，
    两次解析之间文件可被截断或替换，让 256 KiB 上限按旧大小误判；描述符也不跟随
    符号链接，并确认是普通文件，避免从其他状态路径读入配置。
    """
    try:
        descriptor = open_private_file(path, os.O_RDONLY)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
        chunks: list[bytes] = []
        remaining = _MAX_CONFIG_BYTES + 1
        with os.fdopen(os.dup(descriptor), "rb") as handle:
            while remaining > 0:
                chunk = handle.read(min(remaining, 64 * 1024))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
        # 只读到上限 + 1 字节；多出的一字节说明文件超限，不再解码半截内容。
        if remaining == 0:
            return None
        raw = b"".join(chunks)
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None
    finally:
        os.close(descriptor)
    return value if isinstance(value, dict) and _within_depth(value) else None


def _fsync_directory(path: Path) -> None:
    """目录项落盘：``os.replace`` 只保证新名称对运行中的进程可见，掉电后仍可能回退。

    会话追加、附件发布与索引修复备份都把目录 ``fsync`` 当作持久边界；设置保存
    同样需要，否则 ``config/autoCompaction/set`` 返回成功后崩溃会让旧配置复活。
    """
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_auto_compaction(state_dir: Path) -> dict | None:
    """Valid persisted auto-compaction fields; invalid values are treated as absent."""
    stored = _read_object(state_dir / CONFIG_FILE)
    return verified_policy((stored or {}).get("autoCompaction"), AUTO_COMPACTION_FIELDS)


def save_auto_compaction(state_dir: Path, fields: dict) -> None:
    """Persist the three policy fields atomically, preserving unrelated keys.

    Refuses to overwrite a file that exists but cannot be read as an object:
    clobbering unknown settings would be worse than reporting the failure.
    """
    verified = verified_policy(fields, AUTO_COMPACTION_FIELDS)
    if verified is None or set(verified) != set(AUTO_COMPACTION_FIELDS):
        raise ValueError("自动压缩设置必须包含 enabled、triggerPercent、keepRecentTokens")
    path = state_dir / CONFIG_FILE
    if path.exists():
        current = _read_object(path)
        if current is None:
            raise ValueError("内核配置文件不可读或格式无效，未写入自动压缩设置")
    else:
        current = {}
    try:
        payload = json.dumps({**current, "autoCompaction": verified}, ensure_ascii=False, indent=2) + "\n"
        encoded = payload.encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeEncodeError):
        # 配置可能由外部写入：深层嵌套或孤立代理项会让编码失败。此时尚未写
        # 任何字节，返回可读中文错误而不是让 RecursionError / codec 信息逃逸。
        raise ValueError("内核配置文件包含无法保存的内容，未写入自动压缩设置") from None
    if len(encoded) > _MAX_CONFIG_BYTES:
        raise ValueError("内核配置文件超过大小上限，未写入自动压缩设置")
    state_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=state_dir)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(state_dir)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
