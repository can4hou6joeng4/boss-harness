#!/usr/bin/env python3
"""核对摘要 checkpoint 的原子发布口径。

`SessionStore.append_checkpoint` 把整份会话日志复制为 `.checkpoint.tmp` 候选文件：
复制前对 lstat 与已打开描述符做双重签名，复制期间按 1 MiB 分块并记住最后一个
完整记录边界，末尾残段只截到边界、找不到边界即拒绝；追加 `context_checkpoint`
条目后固定权限并 fsync，再核对复制后的源签名、候选 lstat 签名与发布前源签名，
最后以 `os.replace` 作为唯一提交点。替换异常按可见 inode 区分「未替换」、
「已提交」与「无法确认」；提交后的目录 fsync / 回调 / 索引刷新失败一律转换为
`CheckpointCommittedError`，临时文件在 finally 中清理。这里按源码顺序固定这些
边界，避免复制、截断或提交判定被重构放松。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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


def main() -> int:
    try:
        checked = check_checkpoint_publish()
    except (ValueError, SyntaxError) as error:
        print(f"摘要发布核对失败，{error}", file=sys.stderr)
        return 2
    print(f"摘要发布一致：{checked} 项复制、签名与提交校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
