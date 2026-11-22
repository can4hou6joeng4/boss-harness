#!/usr/bin/env python3
"""核对索引修复的清单、移动与回滚边界。

maintenance.py 只移动索引文件，从不改写会话日志与事件：清单大小与摘要来自同一
描述符，移动前再次核对路径身份，成功与失败路径都以目录 fsync 收尾。检查核对
源码结构，并在临时状态目录中执行成功、拒绝与回滚场景。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness import maintenance  # noqa: E402
from boss_harness.session import Entry, SessionStore  # noqa: E402

MODULE = "harness/src/boss_harness/maintenance.py"
INDEX_FILES = ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm")
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

CONSTANT_FRAGMENTS = (
    'STATE_MARKERS = frozenset({".owner.lock", "sessions", "state.sqlite3"})',
    'names = ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm")',
    'backup = root / "repairs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")',
    '+ uuid.uuid4().hex[:8])',
)
MANIFEST_FRAGMENTS = (
    "uid = os.getuid()",
    "original = path.lstat()",
    "if not stat.S_ISREG(original.st_mode) or original.st_uid != uid:",
    'raise ValueError("状态文件必须是当前用户拥有的普通文件")',
    "restrict_private_file(path)",
    "descriptor = open_private_file(path, os.O_RDONLY)",
    'with os.fdopen(descriptor, "rb") as handle:',
    "opened = os.fstat(handle.fileno())",
    # 打开路径与 lstat 之间可能被替换：dev/ino 不一致就拒绝，不摘要未知文件。
    "if ((opened.st_dev, opened.st_ino) != (original.st_dev, original.st_ino)",
    "or not stat.S_ISREG(opened.st_mode) or opened.st_uid != uid):",
    'raise ValueError("状态文件已变化，请重试索引修复")',
    "digest = hashlib.sha256()",
    "while chunk := handle.read(1024 * 1024):",
    "digest.update(chunk)",
    "size += len(chunk)",
    'return {"bytes": size, "sha256": digest.hexdigest()}',
)
REPAIR_FRAGMENTS = (
    "root = resolve_private_path(root)",
    "root.lstat()",
    "except FileNotFoundError:",
    'raise ValueError("状态目录不存在，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR") from None',
    "names_present = {entry.name for entry in os.scandir(root)}",
    "if names_present and names_present.isdisjoint(STATE_MARKERS):",
    'raise ValueError("目标目录不是内核状态目录，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR")',
    # 占用锁会创建目录，必须晚于上面两次只读核对。
    "owner = StateDirectoryOwner(root)",
    "ensure_private_directory(backup)",
    "manifest = []",
    "original = source.lstat()",
    "entry = _manifest_entry(source)",
    "visible = source.lstat()",
    "if ((visible.st_dev, visible.st_ino) != (original.st_dev, original.st_ino)",
    "or not stat.S_ISREG(visible.st_mode)):",
    'manifest.append({"name": name, **entry})',
    "os.replace(source, backup / name)",
    "moved.append(name)",
    'descriptor = open_private_file(backup / "manifest.json", os.O_WRONLY | os.O_EXCL)',
    'with os.fdopen(descriptor, "wb") as output:',
    'output.write((json.dumps(manifest, indent=2) + "\\n").encode())',
    "output.flush()",
    "os.fsync(output.fileno())",
    "_fsync_directory(backup)",
    "_fsync_directory(root)",
    "rebuilding = True",
    'store = SessionStore(root / "sessions")',
    "count = len(store.list_threads(include_archived=True))",
    "cursor = store.latest_event_cursor()",
    "skipped = sorted(store.unreadable_threads)",
    "store.close()",
    'summary = {"repaired": True, "backupPath": str(backup), "threads": count,',
    '"eventCursor": cursor}',
    'summary["skipped"] = skipped',
    "return summary",
)
RECOVERY_FRAGMENTS = (
    "moved_failed = False",
    "if rebuilding:",
    'failed = backup / "failed-candidate"',
    "ensure_private_directory(failed)",
    "restrict_private_file(source)",
    "os.replace(source, failed / name)",
    "moved_failed = True",
    "for name in moved:",
    "os.replace(backup / name, root / name)",
    # 失败路径同样先同步新候选目录与备份，最后同步状态根目录，再沿原异常上报。
    "if moved_failed:\n            _fsync_directory(failed)\n        _fsync_directory(backup)\n"
    "        _fsync_directory(root)\n        raise",
    "finally:\n        owner.close()",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "`maintenance.py` 的索引修复必须先用 `lstat` 核对状态目录存在并在缺失时以固定说明拒绝"),
    (USER_GUIDE, "该命令不改写日志内容，也不能恢复已被删除或篡改的原始记录"),
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
        raise ValueError(f"索引修复行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_rejected(call, message: str, label: str) -> None:
    try:
        call()
    except ValueError as error:
        _expect_value(str(error), message, label)
    else:
        raise ValueError(f"索引修复应拒绝 {label}")


def _expect_failure(call, message: str, label: str) -> None:
    try:
        call()
    except RuntimeError as error:
        _expect_value(str(error), message, label)
    else:
        raise ValueError(f"索引修复应报告 {label}")


def _seed_state(root: Path) -> tuple[str, bytes, dict[str, bytes], str]:
    store = SessionStore(root / "sessions")
    thread = store.create("修复演示")
    store.append(thread["id"], Entry("item", payload={"text": "保留"}))
    store.append_event("演示/事件", {"threadId": thread["id"]})
    log = (root / "sessions" / f"{thread['id']}.jsonl").read_bytes()
    cursor = store.latest_event_cursor()
    store.close()
    (root / "state.sqlite3-wal").write_bytes(b"wal-demo")
    (root / "state.sqlite3-shm").write_bytes(b"shm-demo")
    return thread["id"], log, {name: (root / name).read_bytes() for name in INDEX_FILES}, cursor


def _manifest(names: dict[str, bytes]) -> list[dict]:
    return [{"name": name, "bytes": len(names[name]), "sha256": hashlib.sha256(names[name]).hexdigest()}
            for name in INDEX_FILES if name in names]


def _behavior_checks() -> int:
    missing_message = "状态目录不存在，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR"
    foreign_message = "目标目录不是内核状态目录，未执行索引修复；核对 --state-dir 或 BOSS_HARNESS_DIR"
    with TemporaryDirectory() as directory:
        base = Path(directory)
        absent = base / "absent"
        _expect_rejected(lambda: maintenance.repair_index(absent), missing_message, "缺失路径")
        _expect_value(absent.exists(), False, "缺失路径未被创建")

        foreign = base / "foreign"
        foreign.mkdir()
        (foreign / "notes.txt").write_text("保留", encoding="utf-8")
        _expect_rejected(lambda: maintenance.repair_index(foreign), foreign_message, "陌生目录")
        _expect_value(sorted(path.name for path in foreign.iterdir()), ["notes.txt"], "陌生目录未被写入")

        empty = base / "empty"
        empty.mkdir()
        empty_summary = maintenance.repair_index(empty)
        empty_backup = Path(empty_summary["backupPath"])
        _expect_value(empty_summary["repaired"], True, "空目录修复标记")
        _expect_value(empty_summary["threads"], 0, "空目录会话数")
        _expect_value(empty_summary["eventCursor"], "0", "空目录事件游标")
        _expect_value("skipped" in empty_summary, False, "空目录跳过列表")
        _expect_value(json.loads((empty_backup / "manifest.json").read_text(encoding="utf-8")),
                      [], "空目录清单")
        _expect_value((empty / "state.sqlite3").exists(), True, "空目录重建索引")

        state = base / "state"
        thread_id, log, before, cursor = _seed_state(state)
        summary = maintenance.repair_index(state)
        backup = Path(summary["backupPath"])
        _expect_value((summary["repaired"], summary["threads"]), (True, 1), "状态目录修复结果")
        _expect_value(summary["eventCursor"], cursor, "状态目录事件游标")
        _expect_value("skipped" in summary, False, "状态目录跳过列表")
        _expect_value(backup.resolve().parent, (state / "repairs").resolve(), "备份位于修复目录")
        _expect_value(json.loads((backup / "manifest.json").read_text(encoding="utf-8")),
                      _manifest(before), "状态目录清单")
        _expect_value({name: (backup / name).read_bytes() for name in INDEX_FILES}, before, "备份文件内容")
        _expect_value((state / "sessions" / f"{thread_id}.jsonl").read_bytes(), log, "会话日志保持不变")
        _expect_value((state / "state.sqlite3").exists(), True, "状态目录重建索引")

        early = base / "early"
        early_thread, early_log, early_before, _ = _seed_state(early)
        with patch.object(maintenance, "SessionStore", side_effect=RuntimeError("模拟重建失败")):
            _expect_failure(lambda: maintenance.repair_index(early), "模拟重建失败", "重建失败")
        early_backup = next((early / "repairs").iterdir())
        _expect_value({name: (early / name).read_bytes() for name in INDEX_FILES}, early_before, "重建失败回滚")
        _expect_value((early / "sessions" / f"{early_thread}.jsonl").read_bytes(), early_log,
                      "重建失败日志保持不变")
        _expect_value(json.loads((early_backup / "manifest.json").read_text(encoding="utf-8")),
                      _manifest(early_before), "重建失败清单")
        _expect_value(list((early_backup / "failed-candidate").iterdir()), [], "重建失败没有新候选")

        class _LateFailure(SessionStore):
            def latest_event_cursor(self) -> str:
                raise RuntimeError("模拟重建后失败")

        late = base / "late"
        late_thread, late_log, late_before, _ = _seed_state(late)
        with patch.object(maintenance, "SessionStore", _LateFailure):
            _expect_failure(lambda: maintenance.repair_index(late), "模拟重建后失败", "重建后失败")
        late_backup = next((late / "repairs").iterdir())
        _expect_value({name: (late / name).read_bytes() for name in INDEX_FILES}, late_before,
                      "重建后失败回滚")
        _expect_value((late / "sessions" / f"{late_thread}.jsonl").read_bytes(), late_log,
                      "重建后失败日志保持不变")
        _expect_value(sorted(path.name for path in (late_backup / "failed-candidate").iterdir()),
                      ["state.sqlite3"], "重建后失败保留新候选")

        skipped = base / "skipped"
        (skipped / "sessions").mkdir(parents=True)
        damaged = skipped / "sessions" / "0123456789ab.jsonl"
        damaged.write_bytes(b"{\n")
        skipped_summary = maintenance.repair_index(skipped)
        _expect_value((skipped_summary["threads"], skipped_summary["skipped"]), (0, ["0123456789ab"]),
                      "跳过损坏会话")
        _expect_value(damaged.read_bytes(), b"{\n", "损坏日志保持不变")
    return 7


def check_maintenance() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(MANIFEST_FRAGMENTS, module, MODULE)
    checked += _expect(REPAIR_FRAGMENTS, module, MODULE)
    checked += _expect(RECOVERY_FRAGMENTS, module, MODULE)
    # 清单：lstat → 收紧权限 → 私有描述符 → 复核身份 → 摘要 → 返回。
    checked += _ordered(
        (
            "original = path.lstat()",
            "restrict_private_file(path)",
            "descriptor = open_private_file(path, os.O_RDONLY)",
            "opened = os.fstat(handle.fileno())",
            "digest.update(chunk)",
            'return {"bytes": size, "sha256": digest.hexdigest()}',
        ),
        module,
        MODULE,
    )
    # 修复：只读核对 → 占用锁 → 备份 → 移动 → 清单 → 同步 → 重建 → 关闭。
    checked += _ordered(
        (
            "root.lstat()",
            "names_present = {entry.name for entry in os.scandir(root)}",
            "owner = StateDirectoryOwner(root)",
            "ensure_private_directory(backup)",
            "os.replace(source, backup / name)",
            'descriptor = open_private_file(backup / "manifest.json", os.O_WRONLY | os.O_EXCL)',
            "_fsync_directory(backup)",
            "_fsync_directory(root)",
            "rebuilding = True",
            'store = SessionStore(root / "sessions")',
            "store.close()",
            "return summary",
        ),
        module,
        MODULE,
    )
    # 修复不得删除或改写原始记录：只移动索引文件，日志由会话存储只读重建。
    if "unlink(" in module or "os.remove(" in module or "shutil.rmtree" in module:
        raise ValueError(f"{MODULE} 不得删除原始记录")
    if "json.dump(" in module:
        raise ValueError(f"{MODULE} 必须先生成完整清单文本再写入")
    if "handle.read()" in module:
        raise ValueError(f"{MODULE} 的摘要读取必须有界")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_maintenance()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"索引修复核对失败，{error}", file=sys.stderr)
        return 2
    print(f"索引修复一致：{checked} 项结构防护、{scenarios} 个修复场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
