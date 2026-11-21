#!/usr/bin/env python3
"""核对技能创建、替换与删除的独占、原子与摘要口径。

`SkillCatalog.create` 只创建不覆盖：id 限定小写字母 / 数字 / 下划线 / 连字符
且不超过 64 字符，正文非空且不超过大小上限，目录按需创建，`mkdir` 独占目标
目录，写入失败时回退空目录，新建的技能目录、根与父目录依次 fsync。
`_write_atomic` 在目标目录内用 `.SKILL-*.tmp` 临时文件写入、fsync、
`chmod 0644` 后 `os.replace` 发布并 fsync 目录，失败清理临时文件。
`replace` / `delete` 先核对 id 与摘要格式，再确认根目录与技能目录均为普通
目录，读取当前摘要必须与调用方一致；删除只允许目录中恰好只有 `SKILL.md`，
顺序为先 unlink 后 rmdir。这里按源码顺序固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

CREATE_ORDER = (
    "def create(self, skill_id: Any, content: Any) -> dict:",
    "if not isinstance(skill_id, str) or not self.SKILL_ID.match(skill_id):",
    'raise ValueError("技能 id 只能包含小写字母、数字、下划线与连字符，且不超过 64 字符")',
    "if not isinstance(content, str):",
    'raise ValueError("技能正文必须是字符串")',
    'data = content.encode("utf-8")',
    "if len(data) > self.MAX_SKILL_BYTES:",
    'raise ValueError(f"技能正文不得超过 {self.MAX_SKILL_BYTES} 字节")',
    "if not data.strip():",
    'raise ValueError("技能正文不能为空")',
    "parent_created = self._ensure_directory(self.create_root.parent)",
    "root_created = self._ensure_directory(self.create_root)",
    "target = self.create_root / skill_id",
    "os.mkdir(target, 0o755)",
    "except FileExistsError:",
    'raise ValueError("同名技能已存在，不会覆盖") from None',
    "self._write_atomic(target, data)",
    "if root_created:",
    "_fsync_directory(self.create_root)",
    "if parent_created:",
    "_fsync_directory(self.create_root.parent)",
    "os.rmdir(target)",
    "except OSError as exc:",
    'raise OSError(exc.strerror or str(exc) or "技能创建失败") from None',
    "fields = self._fields(content)",
    "return self._descriptor(skill_id, fields, hashlib.sha256(data).hexdigest(), len(data))",
)
REPLACE_ORDER = (
    "def replace(self, skill_id: Any, content: Any, expected_digest: Any) -> dict:",
    "skill_id = self._existing_id(skill_id)",
    "if not isinstance(content, str):",
    'data = content.encode("utf-8")',
    "if len(data) > self.MAX_SKILL_BYTES:",
    "if not data.strip():",
    'if not isinstance(expected_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_digest):',
    'raise ValueError("技能摘要格式无效")',
    "self._require_directory(self.create_root.parent)",
    "self._require_directory(self.create_root)",
    "directory = self.create_root / skill_id",
    "observed = os.lstat(directory)",
    "except FileNotFoundError:",
    'raise ValueError("技能不存在或不可编辑") from None',
    "if not stat.S_ISDIR(observed.st_mode) or os.path.islink(directory):",
    'raise ValueError("技能目录必须是普通目录")',
    'loaded = self._read_bounded(directory / "SKILL.md")',
    "if loaded is None:",
    'raise ValueError("技能文件不可读取或超过大小限制")',
    "if loaded[2] != expected_digest:",
    'raise ValueError("技能内容已变化，请刷新后重试")',
    "self._write_atomic(directory, data)",
    "except OSError as exc:",
    'raise OSError(exc.strerror or str(exc) or "技能写入失败") from None',
    "fields = self._fields(content)",
    "return self._descriptor(skill_id, fields, hashlib.sha256(data).hexdigest(), len(data))",
)
DELETE_ORDER = (
    "def delete(self, skill_id: Any, expected_digest: Any) -> dict:",
    "skill_id = self._existing_id(skill_id)",
    'if not isinstance(expected_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_digest):',
    'raise ValueError("技能摘要格式无效")',
    "self._require_directory(self.create_root.parent)",
    "self._require_directory(self.create_root)",
    "directory = self.create_root / skill_id",
    "observed = os.lstat(directory)",
    "except FileNotFoundError:",
    'raise ValueError("技能不存在或不可删除") from None',
    "if not stat.S_ISDIR(observed.st_mode) or os.path.islink(directory):",
    'raise ValueError("技能目录必须是普通目录")',
    'loaded = self._read_bounded(directory / "SKILL.md")',
    "if loaded is None:",
    'raise ValueError("技能文件不可读取或超过大小限制")',
    "if loaded[2] != expected_digest:",
    'raise ValueError("技能内容已变化，请刷新后重试")',
    "with os.scandir(directory) as scan:",
    "entries = list(scan)",
    "except OSError as exc:",
    'raise OSError(exc.strerror or str(exc) or "技能删除失败") from None',
    'if [entry.name for entry in entries] != ["SKILL.md"]:',
    'raise ValueError("技能目录还包含其他文件，请先手动清理后再删除")',
    'os.unlink(directory / "SKILL.md")',
    "os.rmdir(directory)",
    'return {"id": skill_id, "digest": expected_digest}',
)
ATOMIC_ORDER = (
    "def _write_atomic(directory: Path, data: bytes) -> None:",
    'descriptor, temporary = tempfile.mkstemp(prefix=".SKILL-", suffix=".tmp", dir=directory)',
    'with os.fdopen(descriptor, "wb") as handle:',
    "handle.write(data)",
    "handle.flush()",
    "os.fsync(handle.fileno())",
    "os.chmod(temporary, 0o644)",
    'os.replace(temporary, directory / "SKILL.md")',
    "_fsync_directory(directory)",
    "except BaseException:",
    "os.unlink(temporary)",
    "except OSError:",
    "pass",
    "raise",
)
ENSURE_ORDER = (
    "def _ensure_directory(path: Path) -> bool:",
    "observed = os.lstat(path)",
    "except FileNotFoundError:",
    "os.mkdir(path, 0o755)",
    "return True",
    "if not stat.S_ISDIR(observed.st_mode) or os.path.islink(path):",
    'raise OSError("技能目录必须是普通目录")',
    "return False",
)
EXISTING_ID_ORDER = (
    "def _existing_id(cls, skill_id: Any) -> str:",
    "if not isinstance(skill_id, str) or not skill_id or len(skill_id) > cls.MAX_EXISTING_SKILL_ID:",
    'raise ValueError("技能 id 必须是 1–200 字符的目录名")',
    'if (skill_id in {".", ".."} or "/" in skill_id or "\\\\" in skill_id',
    "or any(ord(ch) < 32 or ord(ch) == 127 for ch in skill_id)):",
    'raise ValueError("技能 id 不能包含路径分隔符或控制字符")',
    "return skill_id",
)
REQUIRE_ORDER = (
    "def _require_directory(path: Path) -> None:",
    "observed = os.lstat(path)",
    "except FileNotFoundError:",
    'raise ValueError("技能目录不存在") from None',
    "if not stat.S_ISDIR(observed.st_mode) or os.path.islink(path):",
    'raise ValueError("技能目录必须是普通目录")',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SkillCatalog":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SkillCatalog.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_skill_write() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    create = _method(tree, source, "create")
    replace = _method(tree, source, "replace")
    delete = _method(tree, source, "delete")
    atomic = _method(tree, source, "_write_atomic")
    ensure = _method(tree, source, "_ensure_directory")
    existing = _method(tree, source, "_existing_id")
    require = _method(tree, source, "_require_directory")
    checked = _ordered(CREATE_ORDER, create, RESOURCES)
    checked += _ordered(REPLACE_ORDER, replace, RESOURCES)
    checked += _ordered(DELETE_ORDER, delete, RESOURCES)
    checked += _ordered(ATOMIC_ORDER, atomic, RESOURCES)
    checked += _ordered(ENSURE_ORDER, ensure, RESOURCES)
    checked += _ordered(EXISTING_ID_ORDER, existing, RESOURCES)
    checked += _ordered(REQUIRE_ORDER, require, RESOURCES)
    # 新建：id 规则、独占创建、失败回退与目录 fsync 顺序。
    if create.count("self.SKILL_ID.match(skill_id)") != 1:
        raise ValueError(f"{RESOURCES} 的技能新建必须匹配固定 id 规则")
    checked += 1
    if create.count("os.mkdir(target, 0o755)") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录必须以独占方式创建")
    checked += 1
    if create.count('raise ValueError("同名技能已存在，不会覆盖") from None') != 1:
        raise ValueError(f"{RESOURCES} 的重复技能必须拒绝覆盖")
    checked += 1
    if create.count("os.rmdir(target)") != 1:
        raise ValueError(f"{RESOURCES} 的写入失败必须回退空目录")
    checked += 1
    if create.count("_fsync_directory(self.create_root)") != 1 or create.count("_fsync_directory(self.create_root.parent)") != 1:
        raise ValueError(f"{RESOURCES} 的新建技能必须刷新根与父目录")
    checked += 1
    if create.count("hashlib.sha256(data).hexdigest()") != 1:
        raise ValueError(f"{RESOURCES} 的新建技能必须返回摘要")
    checked += 1
    if create.count('raise OSError(exc.strerror or str(exc) or "技能创建失败") from None') != 1:
        raise ValueError(f"{RESOURCES} 的新建失败必须转 OSError")
    checked += 1
    # 原子写入：临时名、fsync、权限、替换、目录 fsync 与失败清理。
    if create.count("self._write_atomic(target, data)") != 1:
        raise ValueError(f"{RESOURCES} 的新建必须经原子写入")
    checked += 1
    if atomic.count('tempfile.mkstemp(prefix=".SKILL-", suffix=".tmp", dir=directory)') != 1:
        raise ValueError(f"{RESOURCES} 的技能临时文件必须使用固定前缀与目录")
    checked += 1
    if atomic.count("os.fsync(handle.fileno())") != 1:
        raise ValueError(f"{RESOURCES} 的技能候选文件必须 fsync")
    checked += 1
    if atomic.count("os.chmod(temporary, 0o644)") != 1:
        raise ValueError(f"{RESOURCES} 的技能文件必须设为 0644")
    checked += 1
    if atomic.count('os.replace(temporary, directory / "SKILL.md")') != 1:
        raise ValueError(f"{RESOURCES} 的技能必须原子替换 SKILL.md")
    checked += 1
    if atomic.count("_fsync_directory(directory)") != 1:
        raise ValueError(f"{RESOURCES} 的技能发布必须刷新目录")
    checked += 1
    if atomic.count("os.unlink(temporary)") != 1:
        raise ValueError(f"{RESOURCES} 的技能失败必须清理临时文件")
    checked += 1
    if atomic.count("except BaseException:") != 1:
        raise ValueError(f"{RESOURCES} 的技能失败必须覆盖所有异常")
    checked += 1
    if '            except OSError:\n                pass\n            raise' not in atomic:
        raise ValueError(f"{RESOURCES} 的技能清理失败不得影响原异常")
    checked += 1
    # 替换：摘要格式、目录检查、当前摘要一致后才原子写入。
    if replace.count("self._existing_id(skill_id)") != 1:
        raise ValueError(f"{RESOURCES} 的技能替换必须校验目录名")
    checked += 1
    if replace.count('re.fullmatch(r"[a-f0-9]{64}", expected_digest)') != 1:
        raise ValueError(f"{RESOURCES} 的技能替换必须校验摘要格式")
    checked += 1
    if replace.count("self._require_directory(self.create_root.parent)") != 1:
        raise ValueError(f"{RESOURCES} 的技能替换必须校验父目录")
    checked += 1
    if replace.count('if loaded[2] != expected_digest:') != 1:
        raise ValueError(f"{RESOURCES} 的技能替换必须核对当前摘要")
    checked += 1
    if replace.count("self._write_atomic(directory, data)") != 1:
        raise ValueError(f"{RESOURCES} 的技能替换必须经原子写入")
    checked += 1
    if replace.count('raise OSError(exc.strerror or str(exc) or "技能写入失败") from None') != 1:
        raise ValueError(f"{RESOURCES} 的技能替换失败必须转 OSError")
    checked += 1
    # 删除：当前摘要、目录内容与先 unlink 后 rmdir。
    if delete.count("self._existing_id(skill_id)") != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须校验目录名")
    checked += 1
    if delete.count('re.fullmatch(r"[a-f0-9]{64}", expected_digest)') != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须校验摘要格式")
    checked += 1
    if delete.count("self._require_directory(self.create_root.parent)") != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须校验父目录")
    checked += 1
    if delete.count('if loaded[2] != expected_digest:') != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须核对当前摘要")
    checked += 1
    if delete.count("entries = list(scan)") != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须枚举目录")
    checked += 1
    if delete.count('if [entry.name for entry in entries] != ["SKILL.md"]:') != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须要求目录只有 SKILL.md")
    checked += 1
    unlink = delete.index('os.unlink(directory / "SKILL.md")')
    rmdir = delete.index("os.rmdir(directory)")
    if unlink > rmdir:
        raise ValueError(f"{RESOURCES} 的技能删除必须先 unlink 再 rmdir")
    checked += 1
    if delete.count('return {"id": skill_id, "digest": expected_digest}') != 1:
        raise ValueError(f"{RESOURCES} 的技能删除必须回执摘要")
    checked += 1
    # 目录辅助：按需创建普通目录，拒绝符号链接。
    if ensure.count("os.mkdir(path, 0o755)") != 1 or ensure.count("return True") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录必须按需创建")
    checked += 1
    if ensure.count("os.path.islink(path)") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录不得是符号链接")
    checked += 1
    if require.count('raise ValueError("技能目录不存在") from None') != 1:
        raise ValueError(f"{RESOURCES} 的技能目录必须存在")
    checked += 1
    if require.count("os.path.islink(path)") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录检查不得接受符号链接")
    checked += 1
    # 目录名：单层、无控制字符、长度受限于既有 id 上限。
    if existing.count("skill_id in {\".\", \"..\"}") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录名不得是点目录")
    checked += 1
    if existing.count('"/" in skill_id') != 1:
        raise ValueError(f"{RESOURCES} 的技能目录名不得包含路径分隔符")
    checked += 1
    if existing.count("ord(ch) < 32 or ord(ch) == 127") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录名不得包含控制字符")
    checked += 1
    if existing.count("len(skill_id) > cls.MAX_EXISTING_SKILL_ID") != 1:
        raise ValueError(f"{RESOURCES} 的技能目录名必须限制长度")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_skill_write()
    except (ValueError, SyntaxError) as error:
        print(f"技能写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能写入一致：{checked} 项独占、原子与摘要校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
