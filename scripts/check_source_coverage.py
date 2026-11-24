#!/usr/bin/env python3
"""固化源码覆盖不变量：每个桌面 / 共享 / 内核模块都被某个检查脚本引用。

`scripts/check_*.py` 为桌面主进程、预加载、渲染层、共享包与内核模块提供回归保护。
新增模块时若没有任何检查提及它，覆盖缺口不会出现在 CI 信号里。这里扫描 `.ts` 与
`.py` 模块（排除测试、声明与 `__init__.py`），要求模块名（Python 也可用模块名）被
至少一个检查脚本引用；确实无法在 Node 中直接加载的 React hooks 列入显式豁免，
且豁免项必须真实存在，避免名单陈旧。
"""

from __future__ import annotations

import re
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"

ROOTS = (
    "apps/desktop/src",
    "packages/shared/src",
    "packages/protocol/src",
    "packages/app-client/src",
)

EXEMPT = frozenset({
    "apps/desktop/src/renderer/src/data/usePlatformLogin.ts",
})

MODULE_GLOB = "*.ts"
EXCLUDED_SUFFIXES = (".test.ts", ".d.ts")

PY_ROOT = "harness/src/boss_harness"
PYTHON_GLOB = "*.py"
PY_EXCLUDED_NAMES = ("__init__.py",)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def scan_modules(root: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(root.rglob(MODULE_GLOB)):
        if path.name.endswith(EXCLUDED_SUFFIXES):
            continue
        found.append(path.relative_to(root).as_posix())
    return found


def _mentioned(name: str, corpus: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_])"
    return re.search(pattern, corpus) is not None


def uncovered_modules(files: list[str], corpus: str, exempt: frozenset[str]) -> list[str]:
    return sorted(
        path for path in files
        if path not in exempt and not _mentioned(Path(path).name, corpus)
    )


def scan_python_modules(root: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(root.rglob(PYTHON_GLOB)):
        if path.name in PY_EXCLUDED_NAMES:
            continue
        found.append(path.relative_to(root).as_posix())
    return found


def _python_mentioned(path: str, corpus: str) -> bool:
    if _mentioned(Path(path).name, corpus):
        return True
    stem = Path(path).stem
    # 模块名允许出现在点分路径中（`boss_harness.search_unicode`），短名不做宽松匹配。
    if len(stem) < 3:
        return False
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(stem)}(?![A-Za-z0-9_])"
    return re.search(pattern, corpus) is not None


def uncovered_python(files: list[str], corpus: str, exempt: frozenset[str]) -> list[str]:
    return sorted(
        path for path in files
        if path not in exempt and not _python_mentioned(path, corpus)
    )


def _check_real_tree() -> None:
    corpus = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "scripts").glob("check_*.py"))
    )
    files: list[str] = []
    for base in ROOTS:
        files.extend(f"{base}/{relative}" for relative in scan_modules(ROOT / base))
    missing = uncovered_modules(files, corpus, EXEMPT)
    if missing:
        raise ValueError("以下模块未被任何检查脚本引用：" + "、".join(missing))
    missing_python = uncovered_python(scan_python_modules(ROOT / PY_ROOT), corpus, frozenset())
    if missing_python:
        raise ValueError("以下内核模块未被任何检查脚本引用：" + "、".join(missing_python))
    stale = sorted(path for path in EXEMPT if not (ROOT / path).is_file())
    if stale:
        raise ValueError("豁免清单包含不存在的模块：" + "、".join(stale))


def _check_behaviors() -> int:
    _check_real_tree()

    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "a.ts").write_text("", encoding="utf-8")
        (folder / "a.test.ts").write_text("", encoding="utf-8")
        (folder / "a.d.ts").write_text("", encoding="utf-8")
        (folder / "sub").mkdir()
        (folder / "sub/b.ts").write_text("", encoding="utf-8")
        scanned = scan_modules(folder)
    if scanned != ["a.ts", "sub/b.ts"]:
        raise ValueError(f"扫描未正确过滤测试与声明文件：{scanned!r}")
    with tempfile.TemporaryDirectory() as directory:
        if scan_modules(Path(directory)) != []:
            raise ValueError("空目录扫描应为空列表")

    files = ["x/z.ts", "x/a.ts"]
    if uncovered_modules(files, "", frozenset()) != ["x/a.ts", "x/z.ts"]:
        raise ValueError("未覆盖列表应稳定排序")
    if uncovered_modules(files, "提到了 z.ts", frozenset()) != ["x/a.ts"]:
        raise ValueError("部分覆盖判定不符")
    if uncovered_modules(files, "", frozenset({"x/a.ts", "x/z.ts"})) != []:
        raise ValueError("豁免未生效")
    if uncovered_modules(["x/ax.ts"], "bax.ts", frozenset()) != ["x/ax.ts"]:
        raise ValueError("前缀相近的名字不应算作覆盖")
    if uncovered_modules(["x/a.ts"], "a.tsx", frozenset()) != ["x/a.ts"]:
        raise ValueError("后缀相近的名字不应算作覆盖")

    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "a.py").write_text("", encoding="utf-8")
        (folder / "b.py").write_text("", encoding="utf-8")
        (folder / "__init__.py").write_text("", encoding="utf-8")
        (folder / "sub").mkdir()
        (folder / "sub/c.py").write_text("", encoding="utf-8")
        scanned_python = scan_python_modules(folder)
    if scanned_python != ["a.py", "b.py", "sub/c.py"]:
        raise ValueError(f"Python 扫描未正确排除 __init__.py：{scanned_python!r}")
    if uncovered_python(["x/search_unicode.py"], "from boss_harness import search_unicode", frozenset()) != []:
        raise ValueError("模块名引用应算作覆盖")
    if uncovered_python(["x/search_unicode.py"], "from boss_harness.search_unicode import f", frozenset()) != []:
        raise ValueError("点分模块名引用应算作覆盖")
    if uncovered_python(["x/q.py"], "q.py", frozenset()) != []:
        raise ValueError("文件名引用应算作覆盖")
    if uncovered_python(["x/search_unicode.py"], "b", frozenset()) != ["x/search_unicode.py"]:
        raise ValueError("未引用的内核模块应被列出")
    if uncovered_python(["x/q.py"], "q", frozenset()) != ["x/q.py"]:
        raise ValueError("短模块名不应做宽松匹配")
    return 14


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_source_coverage.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_source_coverage.py")
    if "共 12 项结构、14 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_source_coverage.py 检查 12 项结构、14 项行为")
    return 2


FRAGMENTS = (
    "ROOTS = (",
    "EXEMPT = frozenset({",
    'MODULE_GLOB = "*.ts"',
    'EXCLUDED_SUFFIXES = (".test.ts", ".d.ts")',
    "def scan_modules(root: Path) -> list[str]:",
    "def uncovered_modules(files: list[str], corpus: str, exempt: frozenset[str]) -> list[str]:",
    'PY_ROOT = "harness/src/boss_harness"',
    'PYTHON_GLOB = "*.py"',
    'PY_EXCLUDED_NAMES = ("__init__.py",)',
    "def scan_python_modules(root: Path) -> list[str]:",
    "def _python_mentioned(path: str, corpus: str) -> bool:",
    "def uncovered_python(files: list[str], corpus: str, exempt: frozenset[str]) -> list[str]:",
)


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_source_coverage() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, Path(__file__).read_text(encoding="utf-8"), __file__)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_source_coverage()
    except (OSError, ValueError) as error:
        print(f"源码覆盖不变量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"源码覆盖不变量一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
