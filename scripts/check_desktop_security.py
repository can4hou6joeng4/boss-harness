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
PERMISSION_ALLOWLIST = frozenset({"clipboard-sanitized-write"})
PERMISSION_FILES = ("window.ts", "platformLogin.ts")
PERMISSION_HANDLERS = ("setPermissionRequestHandler", "setPermissionCheckHandler")
NAVIGATION_HANDLERS: dict[str, dict[str, tuple[str, ...]]] = {
    "window.ts": {
        "will-navigate": ("isTrustedRendererUrl(url", "preventDefault()"),
        "will-frame-navigate": ("event.isMainFrame", "isTrustedRendererUrl(event.url", "preventDefault()"),
    },
    "platformLogin.ts": {
        "will-navigate": ("isOfficialLoginUrl(url", "preventDefault()"),
        "will-frame-navigate": ("event.isMainFrame", "isOfficialLoginUrl(event.url", "preventDefault()"),
        "will-redirect": ("mainFrame", "isOfficialLoginUrl(url", "preventDefault()"),
        "will-prevent-unload": ("preventDefault()",),
    },
}


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


def _main_text(name: str) -> str:
    path = MAIN / name
    if not path.is_file():
        raise ValueError(f"缺少桌面主进程文件 apps/desktop/src/main/{name}")
    return path.read_text(encoding="utf-8")


def _handler_body(text: str, name: str) -> str:
    """取出事件处理器的主体：支持块语句与单表达式两种箭头函数。"""
    match = re.search(rf'\bon\(\s*"{re.escape(name)}"', text)
    if match is None:
        return ""
    arrow = text.find("=>", match.end())
    if arrow == -1:
        return ""
    index = arrow + 2
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    if index < len(text) and text[index] == "{":
        depth = 0
        for end in range(index, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    return text[index:end + 1]
        return ""
    end = text.find("\n", index)
    return text[index:] if end == -1 else text[index:end]


def _check_navigation_handlers() -> int:
    checked = 0
    for name, handlers in NAVIGATION_HANDLERS.items():
        text = _main_text(name)
        for handler, required in handlers.items():
            body = _handler_body(text, handler)
            if not body:
                raise ValueError(f"apps/desktop/src/main/{name} 缺少 {handler} 处理器")
            missing = [fragment for fragment in required if fragment not in body]
            if missing:
                raise ValueError(
                    f"apps/desktop/src/main/{name} 的 {handler} 处理器缺少："
                    + "、".join(missing)
                )
            checked += len(required)
    return checked


def _check_permission_allowlist() -> int:
    text = _main_text("permissionPolicy.ts")
    match = re.search(r"MAIN_WINDOW_PERMISSIONS[^=]*=\s*new Set\(\[(.*?)\]\)", text, re.DOTALL)
    if match is None:
        raise ValueError("apps/desktop/src/main/permissionPolicy.ts 缺少 MAIN_WINDOW_PERMISSIONS")
    values = set(re.findall(r'"([^"]+)"', match.group(1)))
    if values != PERMISSION_ALLOWLIST:
        raise ValueError(
            "主窗口权限白名单应恰为 " + "、".join(sorted(PERMISSION_ALLOWLIST))
            + "，实际为 " + ("、".join(sorted(values)) if values else "空")
        )
    if "isTrustedRendererUrl(" not in text:
        raise ValueError("apps/desktop/src/main/permissionPolicy.ts 必须核对请求来源是否受信")
    return len(values) + 1


def _check_permission_handlers() -> int:
    checked = 0
    for name in PERMISSION_FILES:
        text = _main_text(name)
        for handler in PERMISSION_HANDLERS:
            if handler not in text:
                raise ValueError(f"apps/desktop/src/main/{name} 缺少 {handler}")
            checked += 1
        if not re.search(r"setWindowOpenHandler\([\s\S]{0,240}?action:\s*\"deny\"", text):
            raise ValueError(f"apps/desktop/src/main/{name} 的 setWindowOpenHandler 应返回 deny")
        checked += 1
        if not re.search(r"on\(\"will-attach-webview\",[^\n]*preventDefault\(\)", text):
            raise ValueError(f"apps/desktop/src/main/{name} 的 will-attach-webview 应 preventDefault")
        checked += 1
    window = _main_text("window.ts")
    if len(re.findall(r"allowsMainWindowPermission\(", window)) < 2:
        raise ValueError("apps/desktop/src/main/window.ts 的权限请求与检查处理器都应调用 allowsMainWindowPermission")
    checked += 1
    login = _main_text("platformLogin.ts")
    if "callback(false)" not in login:
        raise ValueError("apps/desktop/src/main/platformLogin.ts 的权限请求处理器应拒绝")
    if re.search(r"setPermissionCheckHandler\(\(\)\s*=>\s*false\)", login) is None:
        raise ValueError("apps/desktop/src/main/platformLogin.ts 的权限检查处理器应返回 false")
    checked += 2
    if "session.fromPartition(" not in login:
        raise ValueError("apps/desktop/src/main/platformLogin.ts 必须使用独立 session 分区")
    if "session.defaultSession" in login:
        raise ValueError("apps/desktop/src/main/platformLogin.ts 不得使用默认 session")
    checked += 2
    return checked


def _check_preload_bridge() -> int:
    relative = "apps/desktop/src/preload/index.ts"
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"缺少桌面 preload 文件 {relative}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None
    if "contextBridge.exposeInMainWorld(" not in text:
        raise ValueError(f"{relative} 必须通过 contextBridge.exposeInMainWorld 暴露 API")
    if re.search(r"exposeInMainWorld\([^;]*\bipcRenderer\b", text):
        raise ValueError(f"{relative} 不得直接暴露 ipcRenderer")
    return 2


def check_desktop_security() -> tuple[int, int, int]:
    checked = 0
    for name, expected in EXPECTED.items():
        checked += _check_file(name, expected)
    unregistered = _unregistered()
    if unregistered:
        raise ValueError("未登记的 webPreferences：" + "、".join(unregistered))
    allowlist = _check_permission_allowlist()
    handlers = _check_permission_handlers()
    navigation = _check_navigation_handlers()
    preload = _check_preload_bridge()
    return len(EXPECTED), checked, allowlist + handlers + navigation + preload


def main() -> int:
    try:
        blocks, checked, guards = check_desktop_security()
    except (OSError, ValueError) as error:
        print(f"桌面安全配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面安全配置一致：{blocks} 个 webPreferences 块、{checked} 项布尔值、{guards} 项权限、导航与桥接防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
