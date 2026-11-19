#!/usr/bin/env python3
"""核对桌面 webPreferences 的静态安全配置。"""

from __future__ import annotations

import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "apps/desktop/src/main"
RENDERER = ROOT / "apps/desktop/src/renderer/src"
EXTERNAL_SCHEMES = re.compile(r'EXTERNAL_SCHEMES\s*=\s*\[([^\]]*)\]')
PRELOAD_INVOKE = re.compile(r'ipcRenderer\.invoke\(\s*"([^"]+)"')
PRELOAD_LISTEN = re.compile(r'ipcRenderer\.on\(\s*"([^"]+)"')
MAIN_HANDLE = re.compile(r'ipcMain\.handle\(\s*"([^"]+)"')
MAIN_SEND = re.compile(r'\b(?:send|sendWhenLoaded)\(\s*(?:[^,()]+,\s*)?"([^"]+)"')
CHANNEL_CALLS = (
    (re.compile(r'\bipcRenderer\.invoke\(\s*(?!")'), "ipcRenderer.invoke"),
    (re.compile(r'\bipcRenderer\.on\(\s*(?!")'), "ipcRenderer.on"),
    (re.compile(r'\bipcRenderer\.removeListener\(\s*(?!")'), "ipcRenderer.removeListener"),
    (re.compile(r'\bipcMain\.handle\(\s*(?!")'), "ipcMain.handle"),
)
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
PRELOAD_EXPOSURE = re.compile(
    r'contextBridge\.exposeInMainWorld\(\s*"([^"]+)"\s*,\s*([A-Za-z_$][\w$]*)\s*\)'
)
PRELOAD_IMPORT = re.compile(r'(?:from\s+|import\s*\(\s*)["\']([^"\']+)["\']')
PRELOAD_ALLOWED_MODULES = frozenset({
    "electron",
    "@boss-harness/protocol",
    "@boss-harness/shared",
    "@boss-harness/app-client",
})
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


def _arrow_body(text: str, start: int) -> str:
    """从 start 起找到箭头函数主体；块语句按大括号配对，单表达式取到行尾。"""
    arrow = text.find("=>", start)
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


def _handler_body(text: str, name: str) -> str:
    """取出事件处理器的主体：支持块语句与单表达式两种箭头函数。"""
    match = re.search(rf'\bon\(\s*"{re.escape(name)}"', text)
    return _arrow_body(text, match.end()) if match else ""


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


def _named_body(text: str, name: str) -> str:
    """按名称取出函数声明或箭头常量的大括号主体。"""
    match = re.search(
        rf'\b(?:function\s+{re.escape(name)}\s*\(|const\s+{re.escape(name)}\s*=)', text
    )
    if match is None:
        return ""
    start = text.find("{", match.end())
    if start == -1:
        return ""
    depth = 0
    for end in range(start, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[start:end + 1]
    return ""


def _schemes(text: str, where: str) -> set[str]:
    match = re.search(r'\[([^\]]*)\]', text)
    if match is None:
        raise ValueError(f"{where} 缺少协议白名单")
    values = set(re.findall(r'"([^"]+)"', match.group(1)))
    if not values:
        raise ValueError(f"{where} 的协议白名单为空")
    return values


def _check_external_links() -> int:
    renderer = RENDERER / "components/RichMarkdown.tsx"
    if not renderer.is_file():
        raise ValueError("缺少渲染层链接组件 apps/desktop/src/renderer/src/components/RichMarkdown.tsx")
    renderer_text = renderer.read_text(encoding="utf-8")
    renderer_match = EXTERNAL_SCHEMES.search(renderer_text)
    if renderer_match is None:
        raise ValueError("apps/desktop/src/renderer/src/components/RichMarkdown.tsx 缺少 EXTERNAL_SCHEMES")
    renderer_schemes = _schemes(renderer_match.group(0), "RichMarkdown.tsx 的 EXTERNAL_SCHEMES")
    target_body = _named_body(renderer_text, "externalTarget")
    if not target_body:
        raise ValueError("apps/desktop/src/renderer/src/components/RichMarkdown.tsx 缺少 externalTarget")
    for fragment in ("EXTERNAL_SCHEMES.includes(", "new URL(url).protocol"):
        if fragment not in target_body:
            raise ValueError(f"RichMarkdown.tsx 的 externalTarget 缺少 {fragment}")
    main_body = _named_body(_main_text("security.ts"), "isAllowedExternalUrl")
    if not main_body:
        raise ValueError("apps/desktop/src/main/security.ts 缺少 isAllowedExternalUrl")
    if "new URL(url).protocol" not in main_body:
        raise ValueError("isAllowedExternalUrl 必须按 URL 解析后的协议判定")
    main_schemes = _schemes(main_body, "isAllowedExternalUrl 的协议白名单")
    if main_schemes != renderer_schemes:
        raise ValueError(
            "外部链接协议白名单不一致：渲染层 " + "、".join(sorted(renderer_schemes))
            + "；主进程 " + "、".join(sorted(main_schemes))
        )
    window = _main_text("window.ts")
    open_body = _named_body(window, "openExternal")
    if not open_body:
        raise ValueError("apps/desktop/src/main/window.ts 缺少 openExternal")
    for fragment in ("isAllowedExternalUrl(", "shell.openExternal("):
        if fragment not in open_body:
            raise ValueError(f"window.ts 的 openExternal 缺少 {fragment}")
    if re.search(r"setWindowOpenHandler\([\s\S]{0,240}?openExternal\(", window) is None:
        raise ValueError("window.ts 的 setWindowOpenHandler 应调用 openExternal")
    calls = [
        (path, count)
        for path in sorted(MAIN.rglob("*.ts"))
        if (count := path.read_text(encoding="utf-8").count("shell.openExternal("))
    ]
    if len(calls) != 1 or calls[0][0].name != "window.ts" or calls[0][1] != 1:
        shown = "、".join(f"{path.name} × {count}" for path, count in calls) or "无"
        raise ValueError(
            "shell.openExternal 只允许在 window.ts 的 openExternal 中调用一次，实际为 " + shown
        )
    return 9


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
    body = _named_body(text, "allowsMainWindowPermission")
    if not body:
        raise ValueError("apps/desktop/src/main/permissionPolicy.ts 缺少 allowsMainWindowPermission")
    required = (
        "Boolean(requestingUrl)",
        "MAIN_WINDOW_PERMISSIONS.has(permission)",
        "isTrustedRendererUrl(requestingUrl!",
    )
    missing = [fragment for fragment in required if fragment not in body]
    if missing:
        raise ValueError("permissionPolicy.ts 的 allowsMainWindowPermission 缺少：" + "、".join(missing))
    return len(values) + len(required)


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
    if 'from "./bridge"' not in text:
        raise ValueError(f"{relative} 必须引用 bridge.ts 的共享桥接类型")
    bridge = ROOT / "apps/desktop/src/preload/bridge.ts"
    if not bridge.is_file():
        raise ValueError("缺少桌面桥接类型文件 apps/desktop/src/preload/bridge.ts")
    if "export interface BossBridge" not in bridge.read_text(encoding="utf-8"):
        raise ValueError("apps/desktop/src/preload/bridge.ts 必须导出 BossBridge")
    if re.search(r"const api:\s*BossBridge\s*=", text) is None:
        raise ValueError(f"{relative} 的 api 必须标注为 BossBridge")
    declaration = ROOT / "apps/desktop/src/renderer/src/env.d.ts"
    if not declaration.is_file():
        raise ValueError("缺少渲染层声明 apps/desktop/src/renderer/src/env.d.ts")
    declared = declaration.read_text(encoding="utf-8")
    if 'from "../../preload/bridge"' not in declared:
        raise ValueError("env.d.ts 必须引用 preload/bridge.ts 的共享桥接类型")
    if "boss: BossBridge" not in declared:
        raise ValueError("env.d.ts 的 Window.boss 必须声明为 BossBridge")
    return 7


def _check_preload_exposure() -> int:
    relative = "apps/desktop/src/preload/index.ts"
    text = (ROOT / relative).read_text(encoding="utf-8")
    exposures = PRELOAD_EXPOSURE.findall(text)
    if exposures != [("boss", "api")]:
        shown = "、".join(f'"{name}" ← {target}' for name, target in exposures) or "无"
        raise ValueError(
            f'{relative} 必须恰好一次调用 contextBridge.exposeInMainWorld("boss", api)，实际为 {shown}'
        )
    return 1


def _check_preload_imports() -> int:
    checked = 0
    for name in ("index.ts", "bridge.ts"):
        relative = f"apps/desktop/src/preload/{name}"
        path = ROOT / relative
        if not path.is_file():
            raise ValueError(f"缺少桌面 preload 文件 {relative}")
        for specifier in PRELOAD_IMPORT.findall(path.read_text(encoding="utf-8")):
            if specifier.startswith("."):
                continue
            if specifier not in PRELOAD_ALLOWED_MODULES:
                raise ValueError(f"{relative} 不得导入未登记模块 {specifier}")
            checked += 1
    return checked


SESSION_EXPORT_FRAGMENTS = (
    "trustedSender(event)",
    "validateSessionExportRequest(payload)",
    "validateThreadExportResponse(response, request)",
    "writeSessionExport(choice.filePath, exported.content)",
    "basename(choice.filePath)",
    "createDirectory",
    "showOverwriteConfirmation",
)


PROCESS_BOUNDARIES = (
    ("apps/desktop/src/main", "../renderer", "主进程不得导入渲染层源码"),
    ("apps/desktop/src/preload", "../main", "preload 不得导入主进程源码"),
)
PROCESS_ROLE_SYMBOLS = (
    ("apps/desktop/src/main", "ipcRenderer", "主进程不得使用 ipcRenderer"),
    ("apps/desktop/src/preload", "ipcMain", "preload 不得使用 ipcMain"),
)
PROCESS_MAIN_FORBIDDEN = (
    ("executeJavaScript", "主进程不得向渲染层注入脚本"),
    ("debugger", "主进程不得挂载调试器或保留 debugger 语句"),
)
SPAWN_OWNER = "startupCheck.ts"
APP_CLIENT = ROOT / "packages/app-client/src"
APP_CLIENT_SPAWN_OWNER = "index.ts"
PRELOAD_FORBIDDEN = (
    ("process.env", "preload 不得读取环境变量"),
    ("process.exit", "preload 不得退出进程"),
    ("process.argv", "preload 不得读取启动参数"),
    ("process.cwd", "preload 不得读取工作目录"),
)
PROCESS_EXEC_AREAS = (
    (MAIN, "主进程"),
    (APP_CLIENT, "app-client"),
)
PROCESS_EXEC_NAMES = ("execFileSync", "execFile", "execSync", "spawnSync", "fork", "exec")
PROCESS_EXEC_CALL = re.compile(
    r"(?<![.\w$])(" + "|".join(PROCESS_EXEC_NAMES) + r")\s*\("
)
CHILD_PROCESS_IMPORT = re.compile(
    r'import\s*\{([^}]*)\}\s*from\s*"node:child_process"'
)
CHILD_PROCESS_SPECIFIER = re.compile(r'["\']node:child_process["\']')


def _check_process_boundaries() -> int:
    for area, marker, message in PROCESS_BOUNDARIES:
        for path in sorted((ROOT / area).rglob("*.ts")):
            for specifier in PRELOAD_IMPORT.findall(path.read_text(encoding="utf-8")):
                if marker in specifier:
                    raise ValueError(
                        f"{message}：{path.relative_to(ROOT).as_posix()} → {specifier}"
                    )
    for area, symbol, message in PROCESS_ROLE_SYMBOLS:
        for path in sorted((ROOT / area).rglob("*.ts")):
            if symbol in path.read_text(encoding="utf-8"):
                raise ValueError(f"{message}：{path.relative_to(ROOT).as_posix()}")
    for symbol, message in PROCESS_MAIN_FORBIDDEN:
        for path in sorted((ROOT / "apps/desktop/src/main").rglob("*.ts")):
            if symbol in path.read_text(encoding="utf-8"):
                raise ValueError(f"{message}：{path.relative_to(ROOT).as_posix()}")
    for symbol, message in PRELOAD_FORBIDDEN:
        for path in sorted((ROOT / "apps/desktop/src/preload").rglob("*.ts")):
            if symbol in path.read_text(encoding="utf-8"):
                raise ValueError(f"{message}：{path.relative_to(ROOT).as_posix()}")
    return (
        len(PROCESS_BOUNDARIES)
        + len(PROCESS_ROLE_SYMBOLS)
        + len(PROCESS_MAIN_FORBIDDEN)
        + len(PRELOAD_FORBIDDEN)
    )


def _check_spawn(area: Path, owner: str, label: str, display: str) -> int:
    callers = [
        path.name
        for path in sorted(area.rglob("*.ts"))
        if "spawn(" in path.read_text(encoding="utf-8")
    ]
    if callers != [owner]:
        raise ValueError(
            f"{label}只允许 {owner} 调用 spawn：" + ("、".join(callers) or "无")
        )
    if "shell: false" not in (area / owner).read_text(encoding="utf-8"):
        raise ValueError(f"{display}/{owner} 的 spawn 必须显式设置 shell: false")
    return 2


def _check_process_spawn() -> int:
    return _check_spawn(
        MAIN, SPAWN_OWNER, "主进程", "apps/desktop/src/main"
    ) + _check_spawn(
        APP_CLIENT, APP_CLIENT_SPAWN_OWNER, "app-client", "packages/app-client/src"
    )


def _check_process_exec() -> int:
    for area, label in PROCESS_EXEC_AREAS:
        for path in sorted(area.rglob("*.ts")):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            match = PROCESS_EXEC_CALL.search(text)
            if match is not None:
                raise ValueError(
                    f"{label}子进程只允许 spawn，不得调用 {match.group(1)}：{relative}"
                )
            imports = CHILD_PROCESS_IMPORT.findall(text)
            if len(CHILD_PROCESS_SPECIFIER.findall(text)) != len(imports):
                raise ValueError(
                    f"{label}必须以具名导入引入 node:child_process：{relative}"
                )
            for names in imports:
                for name in names.split(","):
                    name = name.strip()
                    if not name or name == "spawn" or name.startswith("type "):
                        continue
                    raise ValueError(
                        f"{label}的 node:child_process 只允许导入 spawn 与类型："
                        f"{relative}（{name}）"
                    )
    return len(PROCESS_EXEC_AREAS) * (len(PROCESS_EXEC_NAMES) + 1)


def _check_session_export() -> int:
    text = _main_text("harness.ts")
    match = re.search(r'ipcMain\.handle\(\s*"session-export:save"', text)
    if match is None:
        raise ValueError("apps/desktop/src/main/harness.ts 缺少 session-export:save 处理器")
    body = _arrow_body(text, match.end())
    if not body:
        raise ValueError("session-export:save 处理器缺少主体")
    missing = [fragment for fragment in SESSION_EXPORT_FRAGMENTS if fragment not in body]
    if missing:
        raise ValueError("session-export:save 处理器缺少：" + "、".join(missing))
    return len(SESSION_EXPORT_FRAGMENTS)


def _channel_diff(label: str, expected: set[str], actual: set[str]) -> str:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    return (label + "不一致；缺少：" + ("、".join(missing) or "无")
            + "；多出：" + ("、".join(extra) or "无"))


RENDERER_HTML = ROOT / "apps/desktop/src/renderer/index.html"
CSP_META = re.compile(
    r'<meta[^>]*http-equiv="Content-Security-Policy"[^>]*content="([^"]+)"', re.DOTALL
)
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)
EMBED_ELEMENT = re.compile(r"<\s*(?:iframe|webview|object|embed)\b", re.IGNORECASE)
REMOTE_RESOURCE = re.compile(
    r"""\b(?:src|href|action)\s*=\s*["'](?:https?:)?//""", re.IGNORECASE
)
RENDERER_BOUNDARY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bipcRenderer\b"), "不得引用 ipcRenderer"),
    (re.compile(r'(?:from\s+|import\s*\(\s*)["\']electron["\']'), "不得直接导入 electron"),
    (re.compile(r"\brequire\s*\("), "不得使用 CommonJS require"),
    (re.compile(r'(?:from\s+|import\s*\(\s*)["\']node:'), "不得直接导入 node: 内置模块"),
    (re.compile(r"\bdangerouslySetInnerHTML\b"), "不得使用 dangerouslySetInnerHTML"),
    (re.compile(r"\binnerHTML\b"), "不得直接读写 innerHTML"),
    (re.compile(r"\b(?:outerHTML|insertAdjacentHTML)\b"), "不得直接写入 HTML"),
    (re.compile(r"\beval\s*\("), "不得使用 eval"),
    (re.compile(r"\bnew\s+Function\s*\("), "不得使用 new Function"),
)
REPLICA_SOURCE = "apps/desktop/src/renderer/src/data/harnessReplica.ts"
REPLICA_CONSTANTS = (
    "const MAX_PAGE_COUNT = 10_000;",
    "const MAX_CURSOR_LENGTH = 2048;",
    "const MIN_CONTENT_CHUNK_CHARS = 1024;",
    "const MAX_CONTENT_PAGE_READS = 10_000;",
)
REPLICA_FRAGMENTS = (
    'reference.encoding !== "text"',
    "/^[a-f0-9]{64}$/.test(reference.sha256)",
    "/^[a-f0-9]{12}$/.test(reference.threadId)",
    'reference.part !== "text" && reference.part !== "thinking"',
    "/^[a-f0-9]{32}$/.test(reference.snapshotId)",
    "reference.characterLength < 1",
    "reference.byteLength < reference.characterLength",
    "reference.byteLength > reference.characterLength * 4",
    "reference.byteLength > 16 * 1024 * 1024",
    "会话内容引用无效或超出自动恢复上限",
)


def _check_renderer_boundary() -> int:
    renderer = ROOT / "apps/desktop/src/renderer"
    for path in sorted(renderer.rglob("*")):
        if not path.is_file() or path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for pattern, message in RENDERER_BOUNDARY:
            if pattern.search(text):
                raise ValueError(f"渲染层{message}：{relative}")
    return len(RENDERER_BOUNDARY)


def _check_restore_bounds() -> int:
    text = (ROOT / REPLICA_SOURCE).read_text(encoding="utf-8")
    missing = [
        fragment
        for fragment in (*REPLICA_CONSTANTS, *REPLICA_FRAGMENTS)
        if fragment not in text
    ]
    if missing:
        raise ValueError(f"{REPLICA_SOURCE} 的恢复边界缺少：" + "、".join(missing))
    return len(REPLICA_CONSTANTS) + len(REPLICA_FRAGMENTS)


def _csp_directives(content: str) -> dict[str, tuple[str, ...]]:
    directives: dict[str, tuple[str, ...]] = {}
    for part in content.split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0].lower()] = tuple(tokens[1:])
    return directives


def _check_renderer_csp() -> int:
    if not RENDERER_HTML.is_file():
        raise ValueError("缺少渲染层入口 apps/desktop/src/renderer/index.html")
    text = RENDERER_HTML.read_text(encoding="utf-8")
    match = CSP_META.search(text)
    if match is None:
        raise ValueError("apps/desktop/src/renderer/index.html 缺少 Content-Security-Policy meta")
    directives = _csp_directives(match.group(1))
    if directives.get("default-src") != ("'self'",):
        raise ValueError("渲染层 CSP 的 default-src 应恰为 'self'")
    if directives.get("script-src") != ("'self'",):
        raise ValueError(
            "渲染层 CSP 的 script-src 应恰为 'self'，不得含 'unsafe-inline'、'unsafe-eval' 或远程来源"
        )
    for name, tokens in directives.items():
        if "'unsafe-eval'" in tokens or "*" in tokens or any("://" in token for token in tokens):
            raise ValueError(f"渲染层 CSP 的 {name} 不得包含 'unsafe-eval'、* 或远程来源")
    if INLINE_SCRIPT.search(text):
        raise ValueError("apps/desktop/src/renderer/index.html 不得包含无 src 的内联脚本")
    return 4


def _check_renderer_bootstrap() -> int:
    text = RENDERER_HTML.read_text(encoding="utf-8")
    tags = re.findall(r"<script\b([^>]*)>", text, re.IGNORECASE)
    if len(tags) != 1:
        raise ValueError("apps/desktop/src/renderer/index.html 应恰好包含一个 script 标签")
    attributes = tags[0]
    if 'type="module"' not in attributes:
        raise ValueError('渲染层入口的 script 必须标注 type="module"')
    match = re.search(r'\bsrc="([^"]+)"', attributes)
    if match is None or not match.group(1).startswith("./src/"):
        raise ValueError("渲染层入口的 script src 必须指向本地 ./src/ 模块")
    return 3


def _check_renderer_embed() -> int:
    text = RENDERER_HTML.read_text(encoding="utf-8")
    if EMBED_ELEMENT.search(text):
        raise ValueError("渲染层入口不得包含 iframe / webview / object / embed 嵌入元素")
    if REMOTE_RESOURCE.search(text):
        raise ValueError("渲染层入口的 src / href / action 不得引用远程或协议相对 URL")
    return 2


def _check_ipc_channels() -> int:
    relative = "apps/desktop/src/preload/index.ts"
    text = (ROOT / relative).read_text(encoding="utf-8")
    invokes = set(PRELOAD_INVOKE.findall(text))
    listens = set(PRELOAD_LISTEN.findall(text))
    if not invokes or not listens:
        raise ValueError(f"{relative} 缺少 ipcRenderer.invoke 或 on 通道")
    handled: set[str] = set()
    sent: set[str] = set()
    for file in sorted(MAIN.rglob("*.ts")):
        source = file.read_text(encoding="utf-8")
        sent.update(MAIN_SEND.findall(source))
        for match in MAIN_HANDLE.finditer(source):
            channel = match.group(1)
            if channel in handled:
                raise ValueError(f"IPC 通道重复注册：{channel}")
            handled.add(channel)
            body = _arrow_body(source, match.end())
            if not body:
                raise ValueError(
                    f"{file.relative_to(ROOT).as_posix()} 的 {channel} 处理器缺少主体"
                )
            if "trustedSender(event)" not in body:
                raise ValueError(
                    f"{file.relative_to(ROOT).as_posix()} 的 {channel} 处理器"
                    "必须在入口调用 trustedSender(event)"
                )
            inner = body.strip()
            if inner.startswith("{") and inner.endswith("}"):
                inner = inner[1:-1].lstrip()
            if not inner.startswith("trustedSender(event)"):
                raise ValueError(
                    f"{file.relative_to(ROOT).as_posix()} 的 {channel} 处理器"
                    "必须在任何工作之前先调用 trustedSender(event)"
                )
    if invokes != handled:
        raise ValueError(_channel_diff("preload invoke 与 ipcMain.handle 通道", invokes, handled))
    if listens != sent:
        raise ValueError(_channel_diff("preload 订阅与主进程发送通道", listens, sent))
    return len(handled) * 2 + len(sent) + 2


def _check_channel_literals() -> int:
    for area in (MAIN, ROOT / "apps/desktop/src/preload"):
        for path in sorted(area.rglob("*.ts")):
            text = path.read_text(encoding="utf-8")
            for pattern, name in CHANNEL_CALLS:
                if pattern.search(text):
                    raise ValueError(
                        "IPC 通道必须使用双引号字符串字面量："
                        f"{path.relative_to(ROOT).as_posix()} 的 {name}"
                    )
    return len(CHANNEL_CALLS)


ORIGIN_POLICIES: dict[str, tuple[str, ...]] = {
    "isTrustedRendererUrl": (
        'actual.protocol === "file:"',
        "fileURLToPath(actual) === resolve(entryFile)",
        "actual.origin === expected.origin",
        "actual.pathname === expected.pathname",
        'actual.protocol === "http:"',
        'actual.protocol === "https:"',
    ),
    "isOfficialLoginUrl": (
        'parsed.protocol === "https:"',
        "!parsed.username",
        "!parsed.password",
        'parsed.port === "443"',
        'parsed.hostname === "zhipin.com"',
        'parsed.hostname.endsWith(".zhipin.com")',
    ),
}

TRUSTED_SENDER_FRAGMENTS = (
    "event.senderFrame !== event.sender.mainFrame",
    "event.senderFrame.url",
    "isTrustedRendererUrl(",
    "webContents === event.sender",
)


def _check_origin_policies() -> int:
    text = _main_text("security.ts")
    checked = 0
    for name, required in ORIGIN_POLICIES.items():
        body = _named_body(text, name)
        if not body:
            raise ValueError(f"apps/desktop/src/main/security.ts 缺少 {name}")
        missing = [fragment for fragment in required if fragment not in body]
        if missing:
            raise ValueError(f"security.ts 的 {name} 缺少：" + "、".join(missing))
        checked += len(required)
    return checked


def _check_trusted_sender() -> int:
    relative = "apps/desktop/src/main/harness.ts"
    body = _named_body(_main_text("harness.ts"), "trustedSender")
    if not body:
        raise ValueError(f"{relative} 缺少 trustedSender")
    missing = [fragment for fragment in TRUSTED_SENDER_FRAGMENTS if fragment not in body]
    if missing:
        raise ValueError(f"{relative} 的 trustedSender 缺少：" + "、".join(missing))
    if len(re.findall(r"\bthrow new Error\(", body)) < 2:
        raise ValueError(
            f"{relative} 的 trustedSender 必须分别拒绝非主窗口 / 非主框架与非受信来源"
        )
    return len(TRUSTED_SENDER_FRAGMENTS) + 1


STARTUP_CHECK_SIGNATURE = re.compile(
    r'ipcMain\.handle\(\s*"harness:startup-check"\s*,\s*'
    r"\(\s*event\s*\)\s*:\s*Promise<StartupDiagnosis>\s*=>"
)
STARTUP_CHECK_FRAGMENTS = (
    "trustedSender(event);",
    "const target = startupCheckTarget;",
    'if (!target) return Promise.resolve({ kind: "unavailable", reason: "spawn" });',
    "manualStartupCheck ??=",
    "await diagnostics?.settled();",
    "return runStartupCheck(target);",
)
STARTUP_CHECK_PRELOAD_CALL = (
    'ipcRenderer.invoke("harness:startup-check") as Promise<StartupDiagnosis>'
)


def _check_startup_check_target() -> int:
    """手动自检是进程执行边界：目标只能来自主进程，渲染层不得传参或并发启动。"""
    relative = "apps/desktop/src/main/harness.ts"
    text = _main_text("harness.ts")
    match = STARTUP_CHECK_SIGNATURE.search(text)
    if match is None:
        raise ValueError(
            f"{relative} 的 harness:startup-check 处理器必须只声明 event 参数，"
            "并返回 Promise<StartupDiagnosis>"
        )
    body = _arrow_body(text, match.start())
    if not body:
        raise ValueError(f"{relative} 的 harness:startup-check 处理器缺少函数体")
    missing = [fragment for fragment in STARTUP_CHECK_FRAGMENTS if fragment not in body]
    if missing:
        raise ValueError(
            f"{relative} 的 harness:startup-check 处理器缺少："
            + "、".join(missing)
            + "（自检目标必须来自主进程、在途请求去重并先等启动自检退出）"
        )
    preload = (ROOT / "apps/desktop/src/preload/index.ts").read_text(encoding="utf-8")
    if "runStartupCheck(): Promise<StartupDiagnosis> {" not in preload:
        raise ValueError(
            "apps/desktop/src/preload/index.ts 的 runStartupCheck 必须无参数"
        )
    if STARTUP_CHECK_PRELOAD_CALL not in preload:
        raise ValueError(
            "preload 的 runStartupCheck 只能调用 harness:startup-check 且不得附带实参"
        )
    bridge = (ROOT / "apps/desktop/src/preload/bridge.ts").read_text(encoding="utf-8")
    if "runStartupCheck(): Promise<StartupDiagnosis>;" not in bridge:
        raise ValueError("apps/desktop/src/preload/bridge.ts 的 runStartupCheck 必须无参数")
    renderer_path = "apps/desktop/src/renderer/src/components/ConnectionSettings.tsx"
    renderer = (ROOT / renderer_path).read_text(encoding="utf-8")
    calls = list(re.finditer(r"runStartupCheck\s*\(", renderer))
    if not calls:
        raise ValueError(f"{renderer_path} 必须调用 runStartupCheck")
    for call in calls:
        if not renderer[call.end():].lstrip().startswith(")"):
            raise ValueError(f"{renderer_path} 调用 runStartupCheck 时不得传参")
    return len(STARTUP_CHECK_FRAGMENTS) + len(calls) + 5


SHARED_INDEX = "packages/shared/src/index.ts"


def _check_python_interpreter() -> int:
    """解释器选择与内核同口径：空白变量按未设置，回退 .venv 或 python3。"""
    shared = (ROOT / SHARED_INDEX).read_text(encoding="utf-8")
    fragments = (
        "export function choosePythonInterpreter(",
        'const trimmed = (configured ?? "").trim();',
        'return trimmed || (venvExists ? venvPython : "python3");',
    )
    missing = [fragment for fragment in fragments if fragment not in shared]
    if missing:
        raise ValueError("packages/shared 缺少空白解释器回退：" + "、".join(missing))
    text = _main_text("harness.ts")
    usage = "choosePythonInterpreter(process.env.BOSS_HARNESS_PYTHON, venvPython, existsSync(venvPython))"
    if usage not in text:
        raise ValueError("apps/desktop/src/main/harness.ts 必须经 choosePythonInterpreter 选择解释器")
    if "process.env.BOSS_HARNESS_PYTHON ??" in text:
        raise ValueError("apps/desktop/src/main/harness.ts 不得用 ?? 直接读取 BOSS_HARNESS_PYTHON")
    return len(fragments) + 2


def _check_provider_override() -> int:
    """线路覆盖值与内核同口径：空白变量按未设置，回退桌面默认 openai。"""
    shared = (ROOT / SHARED_INDEX).read_text(encoding="utf-8")
    fragments = (
        "export function chooseProviderOverride(configured: string | undefined): string {",
        'const trimmed = (configured ?? "").trim();',
        'return trimmed || "openai";',
    )
    missing = [fragment for fragment in fragments if fragment not in shared]
    if missing:
        raise ValueError("packages/shared 缺少空白线路回退：" + "、".join(missing))
    text = _main_text("harness.ts")
    usage = "chooseProviderOverride(process.env.BOSS_HARNESS_PROVIDER)"
    if usage not in text:
        raise ValueError("apps/desktop/src/main/harness.ts 必须经 chooseProviderOverride 选择线路")
    if "process.env.BOSS_HARNESS_PROVIDER ??" in text:
        raise ValueError("apps/desktop/src/main/harness.ts 不得用 ?? 直接读取 BOSS_HARNESS_PROVIDER")
    return len(fragments) + 2


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
    external = _check_external_links()
    preload = _check_preload_bridge()
    exposure = _check_preload_exposure()
    imports = _check_preload_imports()
    boundaries = _check_process_boundaries()
    spawn = _check_process_spawn()
    exec_guard = _check_process_exec()
    export = _check_session_export()
    ipc = _check_ipc_channels()
    literals = _check_channel_literals()
    boundary = _check_renderer_boundary()
    restore = _check_restore_bounds()
    csp = _check_renderer_csp()
    bootstrap = _check_renderer_bootstrap()
    embed = _check_renderer_embed()
    trusted = _check_trusted_sender()
    origins = _check_origin_policies()
    startup_check = _check_startup_check_target()
    interpreter = _check_python_interpreter()
    provider = _check_provider_override()
    return (len(EXPECTED), checked,
            allowlist + handlers + navigation + external + preload + exposure + imports
            + boundaries + spawn + exec_guard + export + ipc + literals + boundary + restore
            + csp + bootstrap + embed + trusted + origins + startup_check + interpreter + provider)


def main() -> int:
    try:
        blocks, checked, guards = check_desktop_security()
    except (OSError, ValueError) as error:
        print(f"桌面安全配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面安全配置一致：{blocks} 个 webPreferences 块、{checked} 项布尔值、{guards} 项权限、导航、桥接与渲染层隔离防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
