#!/usr/bin/env python3
"""核对摘要 checkpoint 的原子发布口径。

`SessionStore.append_checkpoint` 把整份会话日志复制为 `.checkpoint.tmp` 候选文件：
复制前对 lstat 与已打开描述符做双重签名，复制期间按 1 MiB 分块并记住最后一个
完整记录边界，末尾残段只截到边界、找不到边界即拒绝；追加 `context_checkpoint`
条目后固定权限并 fsync，再核对复制后的源签名、候选 lstat 签名与发布前源签名，
最后以 `os.replace` 作为唯一提交点。替换异常按可见 inode 区分「未替换」、
「已提交」与「无法确认」；提交后的目录 fsync / 回调 / 索引刷新失败一律转换为
`CheckpointCommittedError`，临时文件在 finally 中清理。这里先按源码顺序固定这些
边界，再用临时目录与合成 `SessionStore` 实际执行 `append_checkpoint`，覆盖尾部
残段、发布前变化、替换异常三态与提交后失败转换。
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

import boss_harness.session as session_module  # noqa: E402

from boss_harness.session import (  # noqa: E402
    CheckpointCommittedError,
    CheckpointCommitUncertain,
    Entry,
    SessionStore,
)

CHECKPOINT_ORDER = (
    "def append_checkpoint(self, thread_id: str, entry_factory: Callable[[], Entry], *,",
    "on_committed: Callable[[], None] | None = None) -> Entry:",
    "if not callable(entry_factory) or (on_committed is not None and not callable(on_committed)):",
    'raise ValueError("摘要提交回调必须可调用")',
    "temporary: Path | None = None",
    "entry: Entry | None = None",
    "committed = False",
    "with self._lock, self._index.transaction() as connection:",
    "path = self.path_for(thread_id)",
    "original = path.lstat()",
    'current_uid = getattr(os, "getuid", None)',
    "if (not stat.S_ISREG(original.st_mode) or original.st_nlink != 1",
    "or current_uid is None or original.st_uid != current_uid()):",
    'raise ValueError("摘要仅支持当前用户拥有的普通单链接会话文件")',
    "original_identity = (original.st_dev, original.st_ino)",
    "original_signature = (original.st_dev, original.st_ino, original.st_size,",
    "original.st_mtime_ns, original.st_ctime_ns,",
    "original.st_mode, original.st_uid, original.st_gid, original.st_nlink)",
    'with path.open("rb") as source:',
    "opened = os.fstat(source.fileno())",
    "opened_signature = (opened.st_dev, opened.st_ino, opened.st_size,",
    "if opened_signature != original_signature or not stat.S_ISREG(opened.st_mode):",
    'raise ValueError("会话文件已变化，请重新读取摘要来源")',
    "self.require_thread(thread_id)",
    "entry = entry_factory()",
    'if not isinstance(entry, Entry) or entry.type != "context_checkpoint":',
    'raise ValueError("摘要提交必须构造 context_checkpoint 条目")',
    "encoded = _encode_session_line(entry.to_dict())",
    'candidate_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.checkpoint.tmp")',
    "descriptor = open_private_file(candidate_path, os.O_WRONLY | os.O_EXCL)",
    "temporary = candidate_path",
    'with os.fdopen(descriptor, "wb") as target:',
    "last_byte = b\"\"",
    "copied = 0",
    "complete_end = 0",
    "while chunk := source.read(1024 * 1024):",
    "boundary = chunk.rfind(b\"\\n\")",
    "if boundary >= 0:",
    "complete_end = copied - len(chunk) + boundary + 1",
    "last_byte = chunk[-1:]",
    'if last_byte and last_byte != b"\\n":',
    "if not complete_end:",
    'raise ValueError("会话日志末尾缺少完整记录边界")',
    "target.truncate(complete_end)",
    "target.seek(complete_end)",
    "target.write(encoded)",
    "target.flush()",
    "os.fchown(target.fileno(), -1, original.st_gid)",
    "os.fchmod(target.fileno(), 0o600)",
    "os.fsync(target.fileno())",
    "candidate = os.fstat(target.fileno())",
    "candidate_identity = (candidate.st_dev, candidate.st_ino)",
    "copied = os.fstat(source.fileno())",
    "copied_signature = (copied.st_dev, copied.st_ino, copied.st_size,",
    "if copied_signature != original_signature:",
    'raise ValueError("会话文件在摘要复制期间变化，请重新读取摘要来源")',
    "candidate_stat = temporary.lstat()",
    "candidate_signature = (candidate_stat.st_dev, candidate_stat.st_ino,",
    "expected_candidate_signature = (candidate_identity[0], candidate_identity[1],",
    "if candidate_signature != expected_candidate_signature:",
    'raise ValueError("已同步的摘要候选文件在发布前变化")',
    "visible_before_replace = path.lstat()",
    "visible_signature = (visible_before_replace.st_dev, visible_before_replace.st_ino,",
    "if visible_signature != original_signature or not stat.S_ISREG(visible_before_replace.st_mode):",
    'raise ValueError("会话文件在摘要发布前变化，请重新读取摘要来源")',
    "os.replace(temporary, path)",
    "visible_identity = (visible.st_dev, visible.st_ino)",
    "if visible_identity == original_identity:",
    "if visible_identity != candidate_identity or not stat.S_ISREG(visible.st_mode):",
    "if ((visible.st_dev, visible.st_ino) != candidate_identity",
    "committed = True",
    "_fsync_directory(path.parent)",
    "if on_committed is not None:",
    "on_committed()",
    "self._index_thread(thread_id, connection)",
    "return entry",
    "if committed and entry is not None:",
    "raise CheckpointCommittedError(entry.id) from exc",
    "if temporary is not None:",
    "temporary.unlink(missing_ok=True)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SessionStore":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SessionStore.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_checkpoint_publish() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    checkpoint = _method(tree, source, "append_checkpoint")
    checked = _ordered(CHECKPOINT_ORDER, checkpoint, SESSION)
    # 提交点唯一：只经 os.replace，不走单条或批量追加路径。
    if checkpoint.count("os.replace(temporary, path)") != 1:
        raise ValueError(f"{SESSION} 的摘要提交点必须唯一")
    checked += 1
    if "self._append_line(" in checkpoint or "self.append(" in checkpoint or "append_many" in checkpoint:
        raise ValueError(f"{SESSION} 的摘要发布不得走追加路径")
    checked += 1
    # 条目构造在锁内且只调用一次；类型必须是 context_checkpoint。
    if checkpoint.count("entry_factory()") != 1:
        raise ValueError(f"{SESSION} 的摘要条目必须只构造一次")
    checked += 1
    if "\n                    entry = entry_factory()" not in checkpoint:
        raise ValueError(f"{SESSION} 的摘要条目必须在校验签名后于锁内构造")
    checked += 1
    if checkpoint.count('entry.type != "context_checkpoint"') != 1:
        raise ValueError(f"{SESSION} 的摘要提交必须限定 context_checkpoint")
    checked += 1
    # 复制：固定 1 MiB 分块，记录最后一个完整记录边界，残段只截到边界。
    if checkpoint.count("1024 * 1024") != 1:
        raise ValueError(f"{SESSION} 的摘要复制必须按 1 MiB 分块")
    checked += 1
    if checkpoint.count("complete_end = copied - len(chunk) + boundary + 1") != 1:
        raise ValueError(f"{SESSION} 的摘要复制必须记录完整记录边界")
    checked += 1
    if checkpoint.count("target.truncate(complete_end)") != 1 or checkpoint.count("target.seek(complete_end)") != 1:
        raise ValueError(f"{SESSION} 的摘要残余段必须截到最后完整记录边界")
    checked += 1
    if checkpoint.count("if not complete_end:") != 1:
        raise ValueError(f"{SESSION} 的摘要复制必须拒绝没有完整记录边界的日志")
    checked += 1
    # 候选文件：固定后缀、独占创建、固定权限与 fsync。
    if checkpoint.count(".checkpoint.tmp") != 1:
        raise ValueError(f"{SESSION} 的摘要候选文件必须使用 .checkpoint.tmp 后缀")
    checked += 1
    if checkpoint.count("os.O_WRONLY | os.O_EXCL") != 1:
        raise ValueError(f"{SESSION} 的摘要候选文件必须独占创建")
    checked += 1
    if checkpoint.count("os.fchmod(target.fileno(), 0o600)") != 1:
        raise ValueError(f"{SESSION} 的摘要候选文件必须固定为 0600")
    checked += 1
    if checkpoint.count("os.fsync(target.fileno())") != 1:
        raise ValueError(f"{SESSION} 的摘要候选文件必须 fsync")
    checked += 1
    # 三方签名：打开、复制完成、发布前都必须等于原始签名。
    if checkpoint.count("if opened_signature != original_signature or not stat.S_ISREG(opened.st_mode):") != 1:
        raise ValueError(f"{SESSION} 的摘要复制必须核对打开时的源签名")
    checked += 1
    if checkpoint.count("if copied_signature != original_signature:") != 1:
        raise ValueError(f"{SESSION} 的摘要复制必须核对复制完成后的源签名")
    checked += 1
    if checkpoint.count("if candidate_signature != expected_candidate_signature:") != 1:
        raise ValueError(f"{SESSION} 的摘要候选必须核对 lstat 与 fstat 签名")
    checked += 1
    if checkpoint.count("if visible_signature != original_signature or not stat.S_ISREG(visible_before_replace.st_mode):") != 1:
        raise ValueError(f"{SESSION} 的摘要发布必须核对发布前的源签名")
    checked += 1
    # 替换异常：原始 inode 则重抛，候选 inode 视为已提交，其他一律不确定。
    if checkpoint.count("CheckpointCommitUncertain(") != 4:
        raise ValueError(f"{SESSION} 的摘要替换必须用四种身份判断报告不确定")
    checked += 1
    if "\n                    if visible_identity == original_identity:\n                        raise\n" not in checkpoint:
        raise ValueError(f"{SESSION} 的摘要替换在源未变时必须重抛原异常")
    checked += 1
    if checkpoint.count("if visible_identity != candidate_identity or not stat.S_ISREG(visible.st_mode):") != 1:
        raise ValueError(f"{SESSION} 的摘要替换必须把候选 inode 视为已提交")
    checked += 1
    # 提交后：目录 fsync → 回调 → 索引刷新，顺序不可交换。
    if checkpoint.count("_fsync_directory(path.parent)") != 1:
        raise ValueError(f"{SESSION} 的摘要提交必须在事务内 fsync 会话目录")
    checked += 1
    if checkpoint.count("on_committed()") != 1 or "\n                    on_committed()" not in checkpoint:
        raise ValueError(f"{SESSION} 的摘要提交回调必须在目录 fsync 后调用")
    checked += 1
    if checkpoint.count("self._index_thread(thread_id, connection)") != 1:
        raise ValueError(f"{SESSION} 的摘要提交必须刷新一次索引")
    checked += 1
    if checkpoint.count("committed = True") != 1:
        raise ValueError(f"{SESSION} 的摘要提交标志必须在发布成功后设置")
    checked += 1
    # 提交后异常一律转换；未提交原样抛出；临时文件必须清理。
    if checkpoint.count("raise CheckpointCommittedError(entry.id) from exc") != 1:
        raise ValueError(f"{SESSION} 的摘要提交后异常必须转换为 CheckpointCommittedError")
    checked += 1
    if "\n        except Exception as exc:\n            if committed and entry is not None:" not in checkpoint:
        raise ValueError(f"{SESSION} 的摘要提交必须只转换已提交异常")
    checked += 1
    if checkpoint.count("temporary.unlink(missing_ok=True)") != 1:
        raise ValueError(f"{SESSION} 的摘要临时文件必须在 finally 清理")
    checked += 1
    if "                except Exception:\n                    pass" not in checkpoint:
        raise ValueError(f"{SESSION} 的清理失败不得影响发布结果")
    checked += 1
    # 异常类型保持 RuntimeError 语义，便于上层区分提交不确定与已提交。
    if "class CheckpointCommitUncertain(RuntimeError):" not in source:
        raise ValueError(f"{SESSION} 缺少 CheckpointCommitUncertain")
    checked += 1
    if "class CheckpointCommittedError(RuntimeError):" not in source:
        raise ValueError(f"{SESSION} 缺少 CheckpointCommittedError")
    checked += 1
    return checked


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"摘要发布行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(action, message: str, label: str) -> int:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(
                f"摘要发布行为变化 {label} 错误信息：期望包含 {message!r}，实际 {error}") from None
        return 1
    raise ValueError(f"摘要发布行为变化 {label} 必须被拒绝")


def _expect_raises(action, kind, label: str):
    try:
        action()
    except kind as error:
        return error
    except Exception as error:
        raise ValueError(
            f"摘要发布行为变化 {label} 异常类型：期望 {kind.__name__}，"
            f"实际 {type(error).__name__}: {error}") from None
    raise ValueError(f"摘要发布行为变化 {label} 必须抛出 {kind.__name__}")


def _build(base: Path) -> tuple[SessionStore, str]:
    sessions = base / "sessions"
    sessions.mkdir(parents=True, mode=0o700)
    (base / "attachments").mkdir(mode=0o700)
    store = SessionStore(sessions)
    return store, store.create("摘要")["id"]


def _checkpoint_factory(created: list, parent_id: str | None = None):
    def factory() -> Entry:
        entry = Entry(type="context_checkpoint", parent_id=parent_id,
                      payload={"throughTurnId": None})
        created.append(entry)
        return entry
    return factory


def _lines(path: Path) -> list[bytes]:
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise ValueError("摘要发布行为变化 会话文件必须以换行结尾")
    return data.split(b"\n")[:-1] if data else []


def _kinds(path: Path) -> list[str]:
    return [json.loads(line)["type"] for line in _lines(path)]


def _temp_leftovers(path: Path) -> list[str]:
    return sorted(item.name for item in path.parent.glob(f".{path.name}.*.checkpoint.tmp"))


def _behavior_checks() -> int:
    checked = 0
    # 成功发布：保留原记录、追加一行、回调在发布后执行且只执行一次。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "success")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            second = store.append(thread_id, Entry(type="user", payload={"text": "二"}))
            path = store.path_for(thread_id)
            before = _lines(path)
            calls: list[str] = []
            created: list = []

            def on_committed() -> None:
                calls.append("committed")
                if json.loads(_lines(path)[-1]).get("id") != created[0].id:
                    raise ValueError("摘要发布行为变化 回调必须看到已发布的检查点")

            returned = store.append_checkpoint(
                thread_id, _checkpoint_factory(created, parent_id=second.id),
                on_committed=on_committed)
            after = _lines(path)
            checked += _expect_value(len(created), 1, "条目工厂调用次数")
            checked += _expect_value(returned.id, created[0].id, "发布返回条目")
            checked += _expect_value(len(after), len(before) + 1, "发布后行数")
            checked += _expect_value(after[:len(before)], before, "原有记录保留")
            checked += _expect_value(json.loads(after[-1]), created[0].to_dict(), "检查点记录")
            checked += _expect_value(calls, ["committed"], "提交回调")
            checked += _expect_value(stat.S_IMODE(path.stat().st_mode), 0o600, "会话文件权限")
            checked += _expect_value(_temp_leftovers(path), [], "临时文件清理")
            checked += _expect_value(created[0].parent_id, second.id, "检查点父引用")
        finally:
            store.close()
    # 入口与条目校验：拒绝时文件不变、临时文件不残留。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "validation")
        try:
            path = store.path_for(thread_id)
            before = path.read_bytes()
            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, None),
                "摘要提交回调必须可调用", "工厂不可调用")
            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, _checkpoint_factory([]), on_committed=1),
                "摘要提交回调必须可调用", "回调不可调用")
            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, lambda: Entry(type="user")),
                "摘要提交必须构造 context_checkpoint 条目", "条目类型不符")
            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, lambda: {"type": "context_checkpoint"}),
                "摘要提交必须构造 context_checkpoint 条目", "条目不是 Entry")

            def failing_factory():
                raise RuntimeError("工厂失败")

            _expect_raises(
                lambda: store.append_checkpoint(thread_id, failing_factory),
                RuntimeError, "工厂抛错")
            checked += 1
            checked += _expect_value(path.read_bytes(), before, "拒绝时文件不变")
            checked += _expect_value(_temp_leftovers(path), [], "拒绝时无临时文件")
        finally:
            store.close()
    # 缺失、符号链接与硬链接文件一律拒绝。
    with tempfile.TemporaryDirectory() as temporary:
        store, _ = _build(Path(temporary) / "shapes")
        try:
            _expect_raises(
                lambda: store.append_checkpoint("aaaaaaaaaaaa", _checkpoint_factory([])),
                FileNotFoundError, "缺失会话")
            checked += 1
            target = store.root / "target.bin"
            target.write_bytes(b"x")
            linked = store.create("符号链接")["id"]
            linked_path = store.path_for(linked)
            linked_path.unlink()
            linked_path.symlink_to(target)
            checked += _expect_error(
                lambda: store.append_checkpoint(linked, _checkpoint_factory([])),
                "摘要仅支持当前用户拥有的普通单链接会话文件", "符号链接")
            shared = store.create("硬链接")["id"]
            os.link(store.path_for(shared), store.root / "shared.bin")
            checked += _expect_error(
                lambda: store.append_checkpoint(shared, _checkpoint_factory([])),
                "摘要仅支持当前用户拥有的普通单链接会话文件", "硬链接")
        finally:
            store.close()
    # 待删除标记优先于摘要发布。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "deleting")
        try:
            marker = store._delete_intent_path(thread_id)
            marker.write_bytes(b"x")
            path = store.path_for(thread_id)
            before = path.read_bytes()
            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, _checkpoint_factory([])),
                "会话正在删除，暂不可读取", "待删除会话")
            checked += _expect_value(path.read_bytes(), before, "待删除时文件不变")
            marker.unlink()
        finally:
            store.close()
    # 尾部半条记录只截到最后一个完整边界。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "partial")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            with path.open("ab") as handle:
                handle.write(b'{"type":"user"')
            created: list = []
            store.append_checkpoint(thread_id, _checkpoint_factory(created))
            checked += _expect_value(_kinds(path), ["session", "user", "context_checkpoint"], "残段截断")
            checked += _expect_value(json.loads(_lines(path)[-1])["id"], created[0].id, "截断后检查点")
            checked += _expect_value(path.read_bytes().endswith(b"\n"), True, "截断后换行结尾")
            checked += _expect_value(_temp_leftovers(path), [], "截断后无临时文件")
        finally:
            store.close()
    # 整份日志没有完整记录边界时拒绝发布。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "boundary")
        try:
            path = store.path_for(thread_id)
            header = path.read_bytes().split(b"\n", 1)[0]

            def truncating_factory() -> Entry:
                entry = Entry(type="context_checkpoint")
                path.write_bytes(header)
                return entry

            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, truncating_factory),
                "会话日志末尾缺少完整记录边界", "缺少记录边界")
            checked += _expect_value(path.read_bytes(), header, "缺少边界时文件不变")
            checked += _expect_value(_temp_leftovers(path), [], "缺少边界时无临时文件")
        finally:
            store.close()
    # 条目工厂期间源文件变化：复制签名核对拒绝发布。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "changed")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)

            def changing_factory() -> Entry:
                entry = Entry(type="context_checkpoint")
                with path.open("ab") as handle:
                    handle.write(b'{"type":"user"')
                return entry

            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, changing_factory),
                "会话文件在摘要复制期间变化，请重新读取摘要来源", "复制期间变化")
            checked += _expect_value(_temp_leftovers(path), [], "复制期间变化无临时文件")
        finally:
            store.close()
    # 发布前源路径被换掉：可见签名核对拒绝发布。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "visible")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            before = path.read_bytes()

            def swapping_factory() -> Entry:
                entry = Entry(type="context_checkpoint")
                root = store.root
                root.rename(root.with_name("visible-old"))
                root.mkdir(mode=0o700)
                (root / path.name).write_bytes(before)
                return entry

            checked += _expect_error(
                lambda: store.append_checkpoint(thread_id, swapping_factory),
                "会话文件在摘要发布前变化，请重新读取摘要来源", "发布前变化")
            checked += _expect_value(path.read_bytes(), before, "发布前变化文件不变")
            checked += _expect_value(_temp_leftovers(path), [], "发布前变化无临时文件")
        finally:
            store.close()
    # 替换失败且源 inode 仍在：原样重抛，不视为已提交。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "replace-original")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            before = path.read_bytes()
            real_replace = session_module.os.replace

            def failed_replace(source, target) -> None:
                raise OSError("替换假失败")

            session_module.os.replace = failed_replace
            try:
                error = _expect_raises(
                    lambda: store.append_checkpoint(thread_id, _checkpoint_factory([])),
                    OSError, "替换失败源未变")
            finally:
                session_module.os.replace = real_replace
            checked += _expect_value(
                isinstance(error, (CheckpointCommittedError, CheckpointCommitUncertain)),
                False, "替换失败源未变不视为提交")
            checked += _expect_value(path.read_bytes(), before, "替换失败源未变文件不变")
            checked += _expect_value(_temp_leftovers(path), [], "替换失败源未变无临时文件")
        finally:
            store.close()
    # 替换已生效但随后报错：按候选 inode 视为已提交。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "replace-candidate")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            real_replace = session_module.os.replace
            created: list = []

            def committed_then_failed(source, target) -> None:
                real_replace(source, target)
                raise OSError("替换后报错")

            session_module.os.replace = committed_then_failed
            try:
                returned = store.append_checkpoint(thread_id, _checkpoint_factory(created))
            finally:
                session_module.os.replace = real_replace
            checked += _expect_value(returned.id, created[0].id, "替换后报错返回条目")
            checked += _expect_value(json.loads(_lines(path)[-1])["id"], created[0].id, "替换后报错视为提交")
            checked += _expect_value(_temp_leftovers(path), [], "替换后报错无临时文件")
        finally:
            store.close()
    # 替换失败且路径消失：提交结果无法确认。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "replace-uncertain")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            real_replace = session_module.os.replace
            created: list = []

            def vanishing_replace(source, target) -> None:
                Path(target).unlink()
                raise OSError("替换后消失")

            session_module.os.replace = vanishing_replace
            try:
                error = _expect_raises(
                    lambda: store.append_checkpoint(thread_id, _checkpoint_factory(created)),
                    CheckpointCommitUncertain, "提交无法确认")
            finally:
                session_module.os.replace = real_replace
            checked += _expect_value(error.checkpoint_id, created[0].id, "无法确认的检查点编号")
            checked += _expect_value(_temp_leftovers(path), [], "无法确认后无临时文件")
        finally:
            store.close()
    # 提交后的目录同步、回调与索引刷新失败都转换为 CheckpointCommittedError。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _build(Path(temporary) / "post-commit")
        try:
            store.append(thread_id, Entry(type="user", payload={"text": "一"}))
            path = store.path_for(thread_id)
            created: list = []

            def failing_callback() -> None:
                raise RuntimeError("回调失败")

            error = _expect_raises(
                lambda: store.append_checkpoint(
                    thread_id, _checkpoint_factory(created), on_committed=failing_callback),
                CheckpointCommittedError, "回调失败")
            checked += _expect_value(error.checkpoint_id, created[0].id, "回调失败的检查点编号")
            checked += _expect_value(json.loads(_lines(path)[-1])["id"], created[0].id, "回调失败仍已提交")

            saved_fsync = session_module._fsync_directory
            created.clear()

            def failing_fsync(directory) -> None:
                raise OSError("目录同步失败")

            session_module._fsync_directory = failing_fsync
            try:
                error = _expect_raises(
                    lambda: store.append_checkpoint(thread_id, _checkpoint_factory(created)),
                    CheckpointCommittedError, "目录同步失败")
            finally:
                session_module._fsync_directory = saved_fsync
            checked += _expect_value(error.checkpoint_id, created[0].id, "目录同步失败的检查点编号")
            checked += _expect_value(json.loads(_lines(path)[-1])["id"], created[0].id, "目录同步失败仍已提交")

            saved_index = store._index_thread
            created.clear()

            def failing_index(*args, **kwargs) -> None:
                raise OSError("索引刷新失败")

            store._index_thread = failing_index
            try:
                error = _expect_raises(
                    lambda: store.append_checkpoint(thread_id, _checkpoint_factory(created)),
                    CheckpointCommittedError, "索引刷新失败")
            finally:
                store._index_thread = saved_index
            checked += _expect_value(error.checkpoint_id, created[0].id, "索引刷新失败的检查点编号")
            checked += _expect_value(json.loads(_lines(path)[-1])["id"], created[0].id, "索引刷新失败仍已提交")
            checked += _expect_value(_temp_leftovers(path), [], "提交后失败无临时文件")
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_checkpoint_publish()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"摘要发布核对失败，{error}", file=sys.stderr)
        return 2
    print(f"摘要发布一致：{checked} 项复制、签名与提交校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
