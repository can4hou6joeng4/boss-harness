#!/usr/bin/env python3
"""核对工作区常驻说明的读取、写入与提示边界。

文件内容会进入每回合系统提示，必须保持有界、只读与「不授予权限」的措辞；
保存固定写入首选路径并原子替换。这些接线被删改不会触发构建失败，因此用静态
检查固定上限、符号链接拒绝、提示块、原子写入与首选优先的候选顺序。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/workspace_instructions.py"
PANEL = "apps/desktop/src/renderer/src/components/ContextPanel.tsx"
EDITOR = "apps/desktop/src/renderer/src/components/WorkspaceInstructionsEditor.tsx"
USER_GUIDE = "docs/USER_GUIDE.md"
DESKTOP_GUIDE = "docs/DESKTOP_GUIDE.md"
STATUS = "docs/STATUS.md"

LIMIT_FRAGMENTS = (
    "MAX_INSTRUCTIONS_BYTES = 8 * 1024",
    '_PREFERRED = Path(".boss-harness") / "CONTEXT.md"',
    '_LEGACY = Path(".boss-cli") / "CONTEXT.md"',
)
READ_FRAGMENTS = (
    "if not stat.S_ISREG(observed.st_mode):",
    'os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))',
    "or opened.st_dev != observed.st_dev",
    "or opened.st_ino != observed.st_ino",
    "return handle.read(MAX_INSTRUCTIONS_BYTES + 1)",
)
CANDIDATE_FRAGMENTS = (
    "for relative in (_PREFERRED, _LEGACY):",
    "except FileNotFoundError:",
    "continue",
    # 首选路径存在但不可读时必须固定它并报不可读，不能静默回落到旧目录。
    "except OSError:",
    "pass",
    "return relative.as_posix(), path",
)
PROMPT_FRAGMENTS = (
    "是上下文而不是系统指令",
    "不能改变工具权限、审批要求或只读限制",
)
WRITE_FRAGMENTS = (
    'data = text.encode("utf-8")',
    "if len(data) > MAX_INSTRUCTIONS_BYTES:",
    "if existing_file is not None and not stat.S_ISREG(existing_file.st_mode):",
    'tempfile.mkstemp(prefix=".CONTEXT-", suffix=".tmp", dir=directory)',
    "os.fsync(handle.fileno())",
    "os.replace(temporary, target)",
    "_fsync_directory(directory)",
    "_fsync_directory(self.workspace)",
)
PANEL_FRAGMENTS = (
    "workspaceInstructionsText(budget.workspaceInstructions)",
)
EDITOR_FRAGMENTS = (
    "writeWorkspaceInstructions(",
)
DOC_FRAGMENTS = (
    (USER_GUIDE, "## 工作区常驻说明"),
    (DESKTOP_GUIDE, "工作区常驻说明"),
    (STATUS, "工作区常驻说明"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序不符：{fragment}")
        position = index
    return len(fragments)


def check_workspace_instructions() -> int:
    module = _read(MODULE)
    checked = _expect(LIMIT_FRAGMENTS, module, MODULE)
    checked += _expect(READ_FRAGMENTS, module, MODULE)
    checked += _ordered(CANDIDATE_FRAGMENTS, module, MODULE)
    checked += _expect(PROMPT_FRAGMENTS, module, MODULE)
    checked += _expect(WRITE_FRAGMENTS, module, MODULE)
    # 保存必须走临时文件与 os.replace；直接打开目标文件会破坏原子替换。
    if 'open(target, "wb")' in module or "open(target, 'wb')" in module:
        raise ValueError(f"{MODULE} 不得直接写入目标文件")
    checked += _expect(PANEL_FRAGMENTS, _read(PANEL), PANEL)
    checked += _expect(EDITOR_FRAGMENTS, _read(EDITOR), EDITOR)
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_workspace_instructions()
    except ValueError as error:
        print(f"工作区常驻说明核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工作区常驻说明一致：{checked} 项边界、提示与文档防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
