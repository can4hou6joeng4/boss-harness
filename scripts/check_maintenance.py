#!/usr/bin/env python3
"""核对索引修复的清单、移动与回滚边界。

maintenance.py 只移动索引文件，从不改写会话日志与事件：清单大小与摘要来自同一
描述符，移动前再次核对路径身份，成功与失败路径都以目录 fsync 收尾。任一保护被
删改都不会触发构建失败，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/maintenance.py"
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
    except ValueError as error:
        print(f"索引修复核对失败，{error}", file=sys.stderr)
        return 2
    print(f"索引修复一致：{checked} 项清单、移动与回滚防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
