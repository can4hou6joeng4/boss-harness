#!/usr/bin/env python3
"""核对桌面 webPreferences 的静态安全配置。"""

from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "apps/desktop/src/main"
EXPECTED: dict[str, dict[str, bool]] = {
    "window.ts": {
        "contextIsolation": True,
        "sandbox": True,
        "nodeIntegration": False,
        "nodeIntegrationInSubFrames": False,
        "webviewTag": False,
        "webSecurity": True,
        "allowRunningInsecureContent": False,
    },
    "platformLogin.ts": {
        "contextIsolation": True,
        "sandbox": True,
        "nodeIntegration": False,
        "nodeIntegrationInSubFrames": False,
        "webviewTag": False,
        "devTools": False,
        "webSecurity": True,
        "allowRunningInsecureContent": False,
        "safeDialogs": True,
        "navigateOnDragDrop": False,
    },
}
PRELOAD_FILES = frozenset({"window.ts"})


def _blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"\bwebPreferences\s*:\s*\{", text):
        start = match.end() - 1
        depth = 0
        for index in range(start, len(text)):
            character = text[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start + 1:index])
                    break
    return blocks


def _boolean(block: str, key: str) -> bool | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*(true|false)\b", block)
    return None if match is None else match.group(1) == "true"


def _check_file(name: str, expected: dict[str, bool]) -> int:
    path = MAIN / name
    if not path.is_file():
        raise ValueError(f"缺少桌面主进程文件 apps/desktop/src/main/{name}")
    blocks = _blocks(path.read_text(encoding="utf-8"))
    if not blocks:
        raise ValueError(f"apps/desktop/src/main/{name} 缺少 webPreferences")
    checked = 0
    for number, block in enumerate(blocks, 1):
        if name in PRELOAD_FILES and not re.search(r"\bpreload\s*:", block):
            raise ValueError(f"apps/desktop/src/main/{name} 第 {number} 个 webPreferences 缺少 preload")
        for key, value in expected.items():
            actual = _boolean(block, key)
            checked += 1
            if actual is not value:
                shown = "缺失" if actual is None else str(actual).lower()
                raise ValueError(
                    f"apps/desktop/src/main/{name} 第 {number} 个 webPreferences 的 "
                    f"{key} 应为 {str(value).lower()}，实际为 {shown}"
                )
    return checked


def _unregistered() -> list[str]:
    found: list[str] = []
    for path in sorted(MAIN.rglob("*.ts")):
        if path.name in EXPECTED:
            continue
        if re.search(r"\bwebPreferences\s*:", path.read_text(encoding="utf-8")):
            found.append(path.relative_to(ROOT).as_posix())
    return found


def check_desktop_security() -> tuple[int, int]:
    checked = 0
    for name, expected in EXPECTED.items():
        checked += _check_file(name, expected)
    unregistered = _unregistered()
    if unregistered:
        raise ValueError("未登记的 webPreferences：" + "、".join(unregistered))
    return len(EXPECTED), checked


def main() -> int:
    try:
        blocks, checked = check_desktop_security()
    except (OSError, ValueError) as error:
        print(f"桌面安全配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面安全配置一致：{blocks} 个 webPreferences 块、{checked} 项布尔值")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
