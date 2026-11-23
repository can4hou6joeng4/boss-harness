#!/usr/bin/env python3
"""核对构建前检查的离线边界：脚本不得导入或动态加载网络客户端。

`docs/TECHNICAL_REFERENCE.md` 承诺这组检查无需网络、模型凭据或招聘平台账号。
这里用 AST 扫描全部 `scripts/check_*.py`：禁止网络客户端模块（含 `urllib.request`、
`http.client`、`requests`、`httpx`、`aiohttp` 等）、禁止套接字连接调用与
`from socket import socket`，也禁止用 `__import__` / `importlib.import_module`
绕过导入检查；`socket.gaierror` 等错误类型与 `urllib.parse` 保持允许。行为侧用合成
源码逐条核对禁令会检出、允许项不误报。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = "scripts"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
FORBIDDEN_MODULES = (
    "urllib.request", "urllib.error", "http", "http.client", "requests", "httpx", "aiohttp",
    "websocket", "websockets", "smtplib", "ftplib", "imaplib", "poplib", "telnetlib", "xmlrpc",
    "grpc", "boto3", "paramiko", "pycurl", "ssl",
)
SOCKET_CALLS = (
    "socket.socket", "socket.create_connection", "socket.getaddrinfo",
    "socket.gethostbyname", "socket.gethostbyaddr",
)
SOCKET_ERROR_NAMES = frozenset({"gaierror"})
DYNAMIC_FUNCTIONS = frozenset({"__import__", "import_module"})


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _parse(source: str, label: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {label}") from None


def _dotted(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _forbidden(module: str) -> bool:
    return any(module == name or module.startswith(name + ".") for name in FORBIDDEN_MODULES)


def _violations(source: str, label: str = "合成源码") -> list[str]:
    tree = _parse(source, label)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _forbidden(alias.name):
                    found.append(f"{label}:{node.lineno} 导入了 {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module or ""
            candidates = [module]
            if module == "urllib":
                candidates = [f"urllib.{alias.name}" for alias in node.names]
            elif module == "socket":
                stray = sorted({alias.name for alias in node.names} - SOCKET_ERROR_NAMES)
                if stray:
                    found.append(f"{label}:{node.lineno} 从 socket 导入 {', '.join(stray)}")
            for candidate in candidates:
                if _forbidden(candidate):
                    found.append(f"{label}:{node.lineno} 导入了 {candidate}")
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in SOCKET_CALLS:
                found.append(f"{label}:{node.lineno} 调用了 {name}")
            if name is not None and name.rsplit(".", 1)[-1] in DYNAMIC_FUNCTIONS and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str) \
                        and _forbidden(argument.value):
                    found.append(f"{label}:{node.lineno} 动态导入了 {argument.value}")
    return found


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"检查脚本离线边界变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    scripts = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / SCRIPTS).glob("check_*.py"))
    if not scripts:
        raise ValueError("scripts 下没有 check_*.py")
    violations: list[str] = []
    for relative in scripts:
        violations.extend(_violations(_read(relative), relative))
    if violations:
        raise ValueError("检查脚本离线边界变化：" + "；".join(violations))
    checked = len(FORBIDDEN_MODULES) + len(SOCKET_CALLS) + 3
    return checked


def _expect_count(source: str, expected: int, label: str) -> int:
    found = _violations(source, label)
    return _expect_value(len(found), expected, label)


def _check_behaviors() -> int:
    checked = 0
    checked += _expect_count("import requests\n", 1, "导入网络客户端")
    checked += _expect_count("from urllib.request import urlopen\n", 1, "导入 urllib 请求")
    checked += _expect_count("from urllib import request\n", 1, "从 urllib 导入请求")
    checked += _expect_count("import urllib.parse\nfrom urllib.parse import unquote\n", 0,
                             "允许 urllib 解析")
    checked += _expect_count("import socket\nsocket.gaierror(Exception)\n", 0, "允许套接字错误类型")
    checked += _expect_count("from socket import gaierror\n", 0, "允许导入套接字错误类型")
    checked += _expect_count("import socket\nsocket.socket()\n", 1, "套接字连接调用")
    checked += _expect_count("import importlib\nimportlib.import_module(\"httpx\")\n", 1,
                             "动态导入网络客户端")
    checked += _expect_count("__import__(\"aiohttp\")\n", 1, "内置动态导入")
    checked += _expect_count("from socket import socket\n", 1, "从 socket 导入连接类型")
    checked += _expect_count("import json\nimport os\nfrom pathlib import Path\n", 0, "普通标准库")
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_offline_checks.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_offline_checks.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少离线边界检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    count = len(list((ROOT / SCRIPTS).glob("check_*.py")))
    print(f"检查脚本离线边界一致：{count} 个脚本、{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
