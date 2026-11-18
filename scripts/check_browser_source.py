#!/usr/bin/env python3
"""核对上游 CLI 浏览器来源覆盖边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = "harness/src/boss_harness/tools/boss_cli.py"
STARTUP = "harness/src/boss_harness/startup_check.py"
APPLICATION = "harness/src/boss_harness/application.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
REPORT = "apps/desktop/src/renderer/src/data/connectionReport.ts"
SETTINGS = "apps/desktop/src/renderer/src/components/ConnectionSettings.tsx"
VALUES = frozenset({"auto", "existing-browser", "stored-cookie"})
ENV = "BOSS_HARNESS_BROWSER_SOURCE"
TOOLS_FRAGMENTS = (
    f'BROWSER_SOURCE_ENV = "{ENV}"',
    'BROWSER_SOURCE_VALUES = frozenset({"auto", "existing-browser", "stored-cookie"})',
    "def resolve_browser_source_override(value: str | None = None) -> str | None:",
    "value = os.environ.get(BROWSER_SOURCE_ENV)",
    "normalized = value.strip().lower()",
    'if normalized == "":',
    "if normalized not in BROWSER_SOURCE_VALUES:",
    "raise ValueError(f\"{BROWSER_SOURCE_ENV} 必须是以下值之一：{choices}\")",
    "self.browser_source = resolve_browser_source_override()",
    'self.browser_source_policy = self.browser_source or "inherit"',
    'argv += ["--browser-source", self.browser_source]',
    "shell=False",
)
STARTUP_FRAGMENTS = (
    '"browserSource", "error", "BROWSER_SOURCE_INVALID"',
    "BROWSER_SOURCE_VALID",
    ENV,
)
APPLICATION_FRAGMENTS = (
    "browser_source_policy=getattr(self.tools, \"browser_source_policy\", None),",
    '"connection/check": lambda p: self.connections.start(_text(p, "target")),',
)
CONNECTIONS_FRAGMENTS = (
    "browser_source_policy: str | None = None,",
    'self.report["cli"]["browserSourcePolicy"] = browser_source_policy',
    'self.report["platform"]["browserSourcePolicy"] = browser_source_policy',
)
DESKTOP_FRAGMENTS = (
    'new Set(["inherit", "auto", "existing-browser", "stored-cookie"])',
    "browserSourcePolicy",
    "BROWSER_SOURCE_LABELS",
    "招聘 CLI 浏览器来源",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(source: str, name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {TOOLS}") from None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"{TOOLS} 缺少 {name}")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_browser_source() -> tuple[int, int]:
    tools = _read(TOOLS)
    checked = _expect(TOOLS_FRAGMENTS, tools, "boss_cli.py")
    resolver = _function(tools, "resolve_browser_source_override")
    # The policy must be a strict allowlist; no shell/exec construction and no implicit fallback.
    if "subprocess" in resolver or "Popen" in resolver:
        raise ValueError("浏览器来源解析不得启动子进程")
    if "strip().lower()" not in resolver:
        raise ValueError("浏览器来源必须先规范化再校验")
    checked += 2
    try:
        source = _read(TOOLS)
        tree = ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {TOOLS}") from None
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Set):
            for element in node.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    found.add(element.value)
    if not VALUES <= found:
        raise ValueError("浏览器来源允许值与文档不一致：" + "、".join(sorted(VALUES - found)))
    checked += 1

    checked += _expect(STARTUP_FRAGMENTS, _read(STARTUP), "startup_check.py")
    checked += _expect(APPLICATION_FRAGMENTS, _read(APPLICATION), "application.py")
    checked += _expect(CONNECTIONS_FRAGMENTS, _read(CONNECTIONS), "connections.py")
    checked += _expect(DESKTOP_FRAGMENTS, _read(REPORT) + _read(SETTINGS), "桌面连接报告")
    return 1, checked


def main() -> int:
    try:
        resolver, guards = check_browser_source()
    except ValueError as error:
        print(f"浏览器来源边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"浏览器来源边界一致：{resolver} 个解析器、{guards} 项上游参数与展示防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
