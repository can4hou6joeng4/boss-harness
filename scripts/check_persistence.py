#!/usr/bin/env python3
"""核对 SQLite 投影索引的迁移、私有权限与连接边界。

persistence.py 是可重建的派生索引：日志才是事实源。版本迁移、WAL、私有
sidecar 权限、宽容解码与逐操作连接任一被删改都不会触发构建失败，因此静态固定。

会话投影只在会话文件变化后重建：投影内容新增派生字段时，已有会话要靠投影内容版本
失效一次。这里同时固定该版本的记录位置、失效范围与启动顺序。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/persistence.py"
SESSION = "harness/src/boss_harness/session.py"
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
# 投影内容版本：先比对记录，只让含位置记录的已索引会话失效，最后写回版本；同一事务。
PROJECTION_FRAGMENTS = (
    "def _expire_outdated_projections(self) -> None:",
    "with self._lock, self._index.transaction() as connection:",
    "\"SELECT value FROM checkpoints WHERE name='threadProjection'\").fetchone()",
    'if row is not None and row["value"] == THREAD_PROJECTION_VERSION:',
    "return",
    'for indexed in connection.execute("SELECT id FROM threads WHERE indexed_size>=0").fetchall():',
    "if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):",
    'outdated = _log_mentions_leaf(self.root / f"{thread_id}.jsonl")',
    "except FileNotFoundError:",
    "continue",
    "except OSError:",
    "outdated = True",
    "if outdated:",
    '"UPDATE threads SET indexed_size=-1,indexed_mtime_ns=-1 WHERE id=?", (thread_id,))',
    "\"INSERT INTO checkpoints(name,value) VALUES('threadProjection',?) \"",
    '"ON CONFLICT(name) DO UPDATE SET value=excluded.value", (THREAD_PROJECTION_VERSION,))',
)
# 字节扫描：两种分隔写法、分块读取并保留跨块尾部；不解析日志。
SCAN_FRAGMENTS = (
    'THREAD_PROJECTION_VERSION = "2"\n',
    "_LEAF_RECORD_MARKERS = tuple(",
    'f\'"type":{separator}"{LEAF_ENTRY_TYPE}"\'.encode("ascii") for separator in ("", " "))',
    "def _log_mentions_leaf(path: Path) -> bool:",
    "overlap = max(len(marker) for marker in _LEAF_RECORD_MARKERS) - 1",
    'with path.open("rb") as handle:',
    "while chunk := handle.read(1 << 20):",
    "window = tail + chunk",
    "if any(marker in window for marker in _LEAF_RECORD_MARKERS):",
    "return True",
    "tail = window[-overlap:]",
    "return False",
)
# 启动顺序：先恢复未完成的删除，再让过期投影失效，随后由刷新重建。
STARTUP_ORDER = (
    "self._index = PersistenceIndex(self.database_path)",
    "self._recover_deletions()",
    "self._expire_outdated_projections()",
    "self._refresh_threads()",
    "self._sync_events()",
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


def _sequence(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 片段可重复（如多个 continue）：从上一个片段之后继续查找。
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
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
    checked += 1
    session = _read(SESSION)
    start = session.find(PROJECTION_FRAGMENTS[0])
    end = session.find("    def _refresh_threads(self) -> None:", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少投影失效函数或其收尾标记")
    checked += _sequence(PROJECTION_FRAGMENTS, session[start:end], SESSION)
    start = session.find(SCAN_FRAGMENTS[0])
    end = session.find("# Pi branchWithSummary()", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少投影内容版本、位置记录扫描或其收尾标记")
    checked += _sequence(SCAN_FRAGMENTS, session[start:end], SESSION)
    # 只看构造函数这一段：后面的列表读取也会调用刷新，整文件查找会放过颠倒的顺序。
    start = session.find(STARTUP_ORDER[0])
    end = session.find("    def close(self) -> None:", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少会话存储的启动段或其收尾标记")
    checked += _sequence(STARTUP_ORDER, session[start:end], SESSION)
    # 失效函数只在启动时调用一次：放进列表刷新会让每次读取都重查版本。
    if session.count("self._expire_outdated_projections()") != 1 or session.count("_log_mentions_leaf(") != 2:
        raise ValueError(f"{SESSION} 的投影失效只能在启动时调用一次，位置记录扫描只供它使用")
    # 版本记在 checkpoints 表：提升索引结构版本会让旧版本拒绝打开同一状态目录。
    if "THREAD_PROJECTION_VERSION" in module or "threadProjection" in module:
        raise ValueError(f"{MODULE} 不得把投影内容版本并入索引结构迁移")
    if session.count("'threadProjection'") != 2 or session.count("THREAD_PROJECTION_VERSION") != 3:
        raise ValueError(f"{SESSION} 的投影内容版本只能读取一次、写回一次")
    # 整库失效会让启动解析全部会话日志；旧形态不得出现在会话存储里。
    if '"UPDATE threads SET indexed_size=-1")' in session or '"UPDATE threads SET indexed_size=-1,indexed_mtime_ns=-1")' in session:
        raise ValueError(f"{SESSION} 的投影失效必须限定到具体会话")
    return checked + 4


def main() -> int:
    try:
        checked = check_persistence()
    except ValueError as error:
        print(f"索引持久化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"索引持久化一致：{checked} 项迁移、权限、连接防护与投影内容版本")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
