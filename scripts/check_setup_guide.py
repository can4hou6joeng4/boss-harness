#!/usr/bin/env python3
"""核对安装指南：工具链、安装、自检与启动命令，以及最低版本要求。

SETUP.md 会被直接交给编码 Agent 执行。这里锁定命令与版本要求：工具链核对、内核与
桌面依赖安装、`--check` 自检与禁用模型的桌面启动命令必须原样保留；最低版本要求从
`package.json` 的 engines.node 与 `harness/pyproject.toml` 的 requires-python 推导，
文档中的「需要 X 或更高」必须与元数据一致；安全约定（不碰凭据、不执行平台写操作）
与 macOS 最低版本也必须保留；文件不得含本机绝对路径。行为侧用合成 Markdown 核对每条规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
SETUP = "SETUP.md"
LOCAL_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\\\Users")
NODE_ENGINE = re.compile(r">=(\d+)(?:\.\d+)*")
REQUIRES_PYTHON = re.compile(r'^requires-python\s*=\s*"([^"]+)"', re.MULTILINE)
PYTHON_ENGINE = re.compile(r">=(\d+\.\d+)")

SETUP_COMMANDS = (
    "node --version",
    "python3 --version",
    "uv --version",
    "uv venv --python 3.12 .venv",
    "uv pip install --python .venv/bin/python -e ./harness",
    "npm ci",
    "npx install-electron --no",
    ".venv/bin/boss-harness --check --provider none --format text",
    'BOSS_HARNESS_DIR="$trial_dir/state" BOSS_HARNESS_PROVIDER=none npm run dev',
)
SETUP_PHRASES = (
    "不执行招聘平台写操作",
    "不读取、不回显、不写入任何凭据",
)
MACOS_MINIMUM = "桌面最低要求 macOS 12"


def _read(relative: str, parse):
    try:
        return parse((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, ValueError, SyntaxError, RecursionError):
        raise ValueError(f"无法读取或解析 {relative}") from None


def _minimum_versions() -> tuple[str, str]:
    root = _read("package.json", json.loads)
    engines = root.get("engines") if isinstance(root, dict) else None
    node = engines.get("node") if isinstance(engines, dict) else None
    match = NODE_ENGINE.fullmatch(node) if isinstance(node, str) else None
    if match is None:
        raise ValueError("package.json 的 engines.node 必须采用 >=N 形式")
    # Python 3.10 没有 tomllib；requires-python 是顶层简单赋值，按文本解析避免额外依赖。
    text = _read("harness/pyproject.toml", lambda value: value)
    requires = REQUIRES_PYTHON.search(text)
    python = PYTHON_ENGINE.fullmatch(requires.group(1)) if requires else None
    if python is None:
        raise ValueError("harness/pyproject.toml 的 requires-python 必须采用 >=X.Y 形式")
    return match.group(1), python.group(1)


def _local_path_problems(text: str) -> list[str]:
    found: list[str] = []
    for match in LOCAL_PATH.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append(f"{SETUP}:{line} 含本机绝对路径")
    return found


def _missing(text: str, items, kind: str) -> list[str]:
    return [f"{SETUP} 缺少{kind} {item}" for item in items if item not in text]


def _setup_problems(text: str, node: str, python: str) -> list[str]:
    found = _local_path_problems(text)
    found += _missing(text, SETUP_COMMANDS, "命令")
    found += _missing(text, SETUP_PHRASES, "安全约定")
    found += _missing(text, (f"需要 {node} 或更高", f"需要 {python} 或更高"), "版本要求")
    found += _missing(text, (MACOS_MINIMUM,), "平台要求")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"安装指南变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    node, python = _minimum_versions()
    problems = _setup_problems(_read(SETUP, lambda value: value), node, python)
    if problems:
        raise ValueError("安装指南变化：" + "；".join(problems))
    return (1 + len(SETUP_COMMANDS) + len(SETUP_PHRASES) + 2 + 1)


def _clean_setup() -> str:
    commands = "\n".join(f"    {command}" for command in SETUP_COMMANDS)
    phrases = "\n".join(f"- {phrase}" for phrase in SETUP_PHRASES)
    return (f"# 安装\n\n```sh\n{commands}\n```\n\n{phrases}\n\n"
            f"需要 24 或更高\n需要 3.10 或更高\n{MACOS_MINIMUM}\n")


def _expect_count(found: int, expected: int, label: str) -> int:
    return _expect_value(found, expected, label)


def _check_behaviors() -> int:
    checked = 0
    checked += _expect_count(len(_setup_problems(_clean_setup(), "24", "3.10")), 0,
                             "干净安装指南")
    for command in SETUP_COMMANDS:
        checked += _expect_count(
            len(_setup_problems(_clean_setup().replace(command, ""), "24", "3.10")),
            1, f"缺少命令 {command}")
    checked += _expect_count(
        len(_setup_problems(_clean_setup().replace("需要 24 或更高", "需要 22 或更高"),
                            "24", "3.10")),
        1, "Node 版本要求漂移")
    checked += _expect_count(
        len(_setup_problems(_clean_setup().replace("需要 3.10 或更高", "需要 3.9 或更高"),
                            "24", "3.10")),
        1, "Python 版本要求漂移")
    for phrase in SETUP_PHRASES:
        checked += _expect_count(
            len(_setup_problems(_clean_setup().replace(phrase, ""), "24", "3.10")),
            1, f"缺少安全约定 {phrase}")
    checked += _expect_count(
        len(_setup_problems(_clean_setup().replace(MACOS_MINIMUM, ""), "24", "3.10")),
        1, "缺少平台要求")
    checked += _expect_count(
        len(_setup_problems(_clean_setup() + "路径 /Users/example/project。\n", "24", "3.10")),
        1, "本机路径")
    checked += _expect_count(
        len(_setup_problems(_clean_setup().replace("# 安装", "# 安装与自检"), "24", "3.10")),
        0, "无关措辞调整")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE, lambda value: value)
    if "scripts/check_setup_guide.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_setup_guide.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少安装指南检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"安装指南一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
