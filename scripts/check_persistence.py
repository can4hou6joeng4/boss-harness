#!/usr/bin/env python3
"""核对 SQLite 投影索引的迁移、私有权限与连接边界。

persistence.py 是可重建的派生索引：日志才是事实源。版本迁移、WAL、私有
sidecar 权限、宽容解码与逐操作连接任一被删改都不会触发构建失败，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/persistence.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

CONSTANT_FRAGMENTS = (
    "SCHEMA_VERSION = 2\n",
)
DECODE_FRAGMENTS = (
    # 索引可能被外部改写：非法 UTF-8 降级为 U+FFFD，而不是让读取变成内部错误。
    'return raw.decode("utf-8", "replace")',
)
INIT_FRAGMENTS = (
    "self.path = Path(path).absolute()",
    "ensure_private_directory(self.path.parent)",
    "descriptor = open_private_file(self.path, os.O_RDWR | os.O_EXCL)",
    "except FileExistsError:",
    "restrict_private_file(self.path)",
    'connection.execute("PRAGMA journal_mode=WAL")',
    'connection.execute("BEGIN IMMEDIATE")',
    # 更新的索引版本必须拒绝打开，不能按旧结构误读。
    "if version > SCHEMA_VERSION:",
    'raise ValueError("会话索引版本较新，请使用兼容的应用版本")',
    "if version < 1:",
    'connection.execute("PRAGMA user_version=1")',
    "if version < 2:",
    'connection.execute("UPDATE threads SET indexed_size=-1")',
    'connection.execute("PRAGMA user_version=2")',
    "connection.commit()",
    "connection.rollback()",
    'connection.execute("CREATE INDEX IF NOT EXISTS events_method_cursor ON events(method,cursor)")',
)
SCHEMA_FRAGMENTS = (
    "id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,",
    "rollout_path TEXT NOT NULL, title TEXT NOT NULL,",
    "indexed_size INTEGER NOT NULL, indexed_mtime_ns INTEGER NOT NULL",
    "PRIMARY KEY(thread_id, turn_id)",
    "event_id TEXT NOT NULL UNIQUE, method TEXT NOT NULL,",
    "PRIMARY KEY(approval_id, thread_id, item_id)",
    "REFERENCES threads(id) ON DELETE CASCADE",
    "checkpoints (name TEXT PRIMARY KEY, value TEXT NOT NULL)",
)
CONNECTION_FRAGMENTS = (
    # 每次操作独占连接：worker 线程之间不共享游标或未提交事务。
    "connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)",
    "connection.row_factory = sqlite3.Row",
    "connection.text_factory = _decode_text",
    'connection.execute("PRAGMA foreign_keys=ON")',
    'connection.execute("PRAGMA busy_timeout=10000")',
    'connection.execute("PRAGMA synchronous=FULL")',
    "connection.close()",
)
SIDECAR_FRAGMENTS = (
    'self.path.with_name(self.path.name + "-wal")',
    'self.path.with_name(self.path.name + "-shm")',
    "except FileNotFoundError:",
)
TRANSACTION_FRAGMENTS = (
    'connection.execute("BEGIN IMMEDIATE")',
    "self._restrict_sidecars()",
    "connection.commit()",
    "connection.rollback()",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "日志是事实源，SQLite 是可重建索引"),
    (TECHNICAL_REFERENCE, "会话和事件 JSONL 的冷读、事件索引重建及删除清理对无效 UTF-8、JSON、重复对象键、非有限浮点、孤立 Unicode 代理项及无效记录结构严格失败"),
    (TECHNICAL_REFERENCE, "历史错计数可退出应用后运行 `boss-harness --repair-state` 从日志重建"),
    (USER_GUIDE, "自检不创建状态目录、不修改权限、不读取会话、不写入索引，与 `--repair-state` 互斥。"),
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


def check_persistence() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(DECODE_FRAGMENTS, module, MODULE)
    checked += _expect(INIT_FRAGMENTS, module, MODULE)
    checked += _expect(SCHEMA_FRAGMENTS, module, MODULE)
    checked += _expect(CONNECTION_FRAGMENTS, module, MODULE)
    checked += _expect(SIDECAR_FRAGMENTS, module, MODULE)
    checked += _expect(TRANSACTION_FRAGMENTS, module, MODULE)
    # 版本检查与迁移必须按 1 → 2 顺序执行，旧库才能逐步升级。
    checked += _ordered(
        (
            "if version > SCHEMA_VERSION:",
            "if version < 1:",
            "if version < 2:",
        ),
        module,
        MODULE,
    )
    # 连接先启用外键，再设置同步级别；顺序无关正确性，但固定可避免回退。
    checked += _ordered(
        (
            'connection.execute("PRAGMA foreign_keys=ON")',
            'connection.execute("PRAGMA synchronous=FULL")',
        ),
        module,
        MODULE,
    )
    # 索引文本必须宽容解码；严格解码会让损坏行变成内部错误。
    if 'decode("utf-8")' in module:
        raise ValueError(f"{MODULE} 的索引文本必须宽容解码")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_persistence()
    except ValueError as error:
        print(f"索引持久化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"索引持久化一致：{checked} 项迁移、权限与连接防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
