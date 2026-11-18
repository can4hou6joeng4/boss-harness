#!/usr/bin/env python3
"""核对内核注册表与协议常量，成功时输出各类常量数量。"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "packages/protocol/src/index.ts"
PROTOCOL_PY = "harness/src/boss_harness/protocol.py"
APPLICATION = "harness/src/boss_harness/application.py"
EXPORT = "harness/src/boss_harness/session_export.py"
SECURITY = "apps/desktop/src/main/security.ts"
SOURCE_ROOT = "harness/src/boss_harness"
APP_CLIENT = "packages/app-client/src"
DESKTOP_ROOT = "apps/desktop/src"
EMITTERS = frozenset({"emit", "emit_until", "_emit_committed", "notify"})
METHOD_LITERAL = re.compile(r'method\s*(?:[!=]==?|:)\s*"([^"]+/[^"]*)"')
PROTOCOL_DEFAULT = re.compile(r'protocolVersion\s*\?\?\s*"(\d+\.\d+\.\d+)"')
WORKSPACE_IMPORT = re.compile(r'(?:from\s+|import\(\s*)"(@boss-harness/[^"]+)"')
# 内核经变量或元组发送、静态扫描无法识别的通知。新增此类路径时在此显式登记。
DYNAMIC_KERNEL_NOTIFICATIONS = frozenset({"thread/deleted", "turn/completed"})
# 经协议暴露、但只允许主进程调用的方法。新增此类方法时在此显式登记。
MAIN_ONLY_METHODS = frozenset({
    "initialize", "initialized", "shutdown",
    "platform/login/start", "platform/login/read", "platform/login/complete", "platform/login/cancel",
    "thread/export",
})


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _protocol_constants(text: str, name: str) -> set[str]:
    match = re.search(rf"export const {name} = \{{(.*?)\}} as const;", text, re.DOTALL)
    if match is None:
        raise ValueError(f"{PROTOCOL} 缺少 {name}")
    values = set(re.findall(r':\s*"([^"]+)"', match.group(1)))
    if not values:
        raise ValueError(f"{PROTOCOL} 的 {name} 没有常量")
    return values


def _desktop_methods(text: str, name: str) -> set[str]:
    match = re.search(rf"const {name} = new Set\(\[(.*?)\]\);", text, re.DOTALL)
    if match is None:
        raise ValueError(f"{SECURITY} 缺少 {name}")
    values = set(re.findall(r'"([^"]+)"', match.group(1)))
    if not values:
        raise ValueError(f"{SECURITY} 的 {name} 没有方法")
    return values


def _check_desktop(client: set[str]) -> tuple[int, int]:
    security = _read(SECURITY)
    renderer = _desktop_methods(security, "RENDERER_METHODS")
    outside = renderer - client
    if outside:
        raise ValueError("RENDERER_METHODS 含协议之外的方法：" + "、".join(sorted(outside)))
    unlisted = client - renderer - MAIN_ONLY_METHODS
    if unlisted:
        raise ValueError("ClientMethods 中未暴露给渲染层且未登记为仅主进程的方法：" + "、".join(sorted(unlisted)))
    promoted = MAIN_ONLY_METHODS - (client - renderer)
    if promoted:
        raise ValueError("仅主进程方法已暴露给渲染层或不在协议中：" + "、".join(sorted(promoted)))
    thread = _desktop_methods(security, "THREAD_METHODS")
    stray = thread - renderer
    if stray:
        raise ValueError("THREAD_METHODS 含未暴露给渲染层的方法：" + "、".join(sorted(stray)))
    return len(renderer), len(thread)


def _python_protocol_version() -> str:
    try:
        tree = ast.parse(_read(PROTOCOL_PY))
    except SyntaxError:
        raise ValueError(f"无法解析 {PROTOCOL_PY}") from None
    values = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == "PROTOCOL_VERSION" for target in targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                values.append(node.value.value)
    if len(values) == 1 and values[0]:
        return values[0]
    raise ValueError(f"{PROTOCOL_PY} 必须包含唯一的顶层 PROTOCOL_VERSION 字符串声明")


def _typescript_protocol_version(text: str) -> str:
    match = re.search(r'export const PROTOCOL_VERSION = "([^"]+)";', text)
    if match is None:
        raise ValueError(f"{PROTOCOL} 缺少 PROTOCOL_VERSION")
    return match.group(1)


def _kernel_capabilities() -> set[str]:
    try:
        tree = ast.parse(_read(APPLICATION))
    except SyntaxError:
        raise ValueError(f"无法解析 {APPLICATION}") from None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "on_initialize":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Dict):
                continue
            for key, value in zip(child.keys, child.values):
                if (isinstance(key, ast.Constant) and key.value == "capabilities"
                        and isinstance(value, ast.Dict)):
                    names = {
                        item.value for item in value.keys
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    }
                    if names:
                        return names
    raise ValueError(f"{APPLICATION} 未找到 on_initialize 的 capabilities 字典")


def _typescript_capabilities(text: str) -> set[str]:
    start = text.find("export interface InitializeResponse {")
    if start < 0:
        raise ValueError(f"{PROTOCOL} 缺少 InitializeResponse")
    marker = text.find("capabilities?: {", start)
    if marker < 0:
        raise ValueError(f"{PROTOCOL} 的 InitializeResponse 缺少 capabilities")
    tail = re.sub(r"/\*.*?\*/", "", text[marker:], flags=re.DOTALL)
    tail = re.sub(r"//.*", "", tail)
    opening = tail.find("{")
    depth = 0
    for index in range(opening, len(tail)):
        if tail[index] == "{":
            depth += 1
        elif tail[index] == "}":
            depth -= 1
            if depth == 0:
                names = set(re.findall(r"(\w+)\??:\s*boolean\b", tail[opening + 1:index]))
                if names:
                    return names
                break
    raise ValueError(f"{PROTOCOL} 的 capabilities 没有布尔字段")


def _check_capabilities(protocol: str) -> int:
    kernel = _kernel_capabilities()
    declared = _typescript_capabilities(protocol)
    if kernel != declared:
        raise ValueError("InitializeResponse.capabilities 与内核不一致：" + _describe(kernel - declared, declared - kernel))
    return len(kernel)


def _registered_methods() -> set[str]:
    try:
        tree = ast.parse(_read(APPLICATION))
    except SyntaxError:
        raise ValueError(f"无法解析 {APPLICATION}") from None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_register":
            continue
        for child in node.body:
            if (isinstance(child, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "methods" for target in child.targets)
                    and isinstance(child.value, ast.Dict)):
                methods = {
                    key.value for key in child.value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                if methods:
                    return methods
    raise ValueError(f"{APPLICATION} 未找到 _register() 的 methods 字典")


def _module_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            constants[node.targets[0].id] = node.value.value
    return constants


def _called(value: ast.expr) -> str | None:
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Name):
        return value.id
    return None


def _is_server_request(value: ast.expr) -> bool:
    return (isinstance(value, ast.Attribute) and value.attr == "request"
            and isinstance(value.value, ast.Attribute) and value.value.attr == "server")


def _text(value: ast.expr, constants: dict[str, str]) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Name):
        return constants.get(value.id)
    return None


def _static_messages() -> tuple[set[str], set[str]]:
    """扫描字面量或模块常量形式的消息；动态方法名无法静态核对。"""
    notifications: set[str] = set()
    requests: set[str] = set()
    for path in sorted((ROOT / SOURCE_ROOT).rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            raise ValueError(f"无法解析 {relative}") from None
        constants = _module_constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            called = _called(node.func)
            if called in EMITTERS:
                message = _text(node.args[0], constants)
                if message and "/" in message:
                    notifications.add(message)
            elif called and called.startswith("_emit"):
                for argument in node.args:
                    message = _text(argument, constants)
                    if message and "/" in message:
                        notifications.add(message)
            elif _is_server_request(node.func):
                message = _text(node.args[0], constants)
                if message and "/" in message:
                    requests.add(message)
    return notifications, requests


def _host_notifications() -> set[str]:
    """宿主以字面量 `method` 发送的通知；动态方法名无法静态核对。"""
    messages: set[str] = set()
    try:
        for path in sorted((ROOT / APP_CLIENT).rglob("*.ts")):
            messages.update(re.findall(r'method:\s*"([^"]+)"', path.read_text(encoding="utf-8")))
    except OSError:
        raise ValueError(f"无法读取 {APP_CLIENT}") from None
    if not messages:
        raise ValueError(f"{APP_CLIENT} 未找到宿主通知字面量")
    return messages


def _desktop_method_literals() -> set[str]:
    """桌面比较或构造的协议方法字面量；类型判断等不含 ``/`` 的值不参与。"""
    literals: set[str] = set()
    try:
        paths = [*sorted((ROOT / DESKTOP_ROOT).rglob("*.ts")),
                 *sorted((ROOT / DESKTOP_ROOT).rglob("*.tsx"))]
        for path in paths:
            literals.update(METHOD_LITERAL.findall(path.read_text(encoding="utf-8")))
    except OSError:
        raise ValueError(f"无法读取 {DESKTOP_ROOT}") from None
    return literals


def _default_protocol_versions() -> list[tuple[str, str]]:
    """宿主与桌面不得为握手默认值另立协议版本字面量。"""
    found: list[tuple[str, str]] = []
    try:
        paths = [*sorted((ROOT / APP_CLIENT).rglob("*.ts")),
                 *sorted((ROOT / DESKTOP_ROOT).rglob("*.ts")),
                 *sorted((ROOT / DESKTOP_ROOT).rglob("*.tsx"))]
        for path in paths:
            for literal in PROTOCOL_DEFAULT.findall(path.read_text(encoding="utf-8")):
                found.append((path.relative_to(ROOT).as_posix(), literal))
    except OSError:
        raise ValueError("无法读取宿主或桌面源码") from None
    return found


def _workspace_dependencies() -> int:
    """工作区源码导入的 @boss-harness 包必须在其 package.json 中声明。"""
    try:
        root = json.loads(_read("package.json"))
    except (ValueError, json.JSONDecodeError):
        raise ValueError("无法解析根 package.json") from None
    patterns = root.get("workspaces") if isinstance(root, dict) else None
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("根 package.json 缺少 workspaces")
    workspaces: list[Path] = []
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("根 package.json 的 workspaces 必须是字符串列表")
        workspaces.extend(sorted(path for path in ROOT.glob(pattern)
                                 if path.is_dir() and (path / "package.json").is_file()))
    if not workspaces:
        raise ValueError("根 package.json 的 workspaces 没有匹配到工作区")
    checked = 0
    for directory in workspaces:
        relative = directory.relative_to(ROOT).as_posix()
        try:
            manifest = json.loads((directory / "package.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise ValueError(f"无法解析 {relative}/package.json") from None
        name = manifest.get("name") if isinstance(manifest, dict) else None
        if not isinstance(name, str) or not name:
            raise ValueError(f"{relative}/package.json 缺少名称")
        declared: set[str] = set()
        for key in ("dependencies", "devDependencies"):
            values = manifest.get(key)
            if isinstance(values, dict):
                declared.update(values)
        imported: set[str] = set()
        source = directory / "src"
        if source.is_dir():
            try:
                for path in (*sorted(source.rglob("*.ts")), *sorted(source.rglob("*.tsx"))):
                    imported.update(WORKSPACE_IMPORT.findall(path.read_text(encoding="utf-8")))
            except OSError:
                raise ValueError(f"无法读取 {relative}/src") from None
        imported.discard(name)
        missing = imported - declared
        if missing:
            raise ValueError(f"{relative} 未声明工作区包依赖：" + "、".join(sorted(missing)))
        checked += len(imported)
    return checked


def _describe(missing: set[str], extra: set[str]) -> str:
    parts = []
    if missing:
        parts.append("缺少 " + "、".join(sorted(missing)))
    if extra:
        parts.append("多出 " + "、".join(sorted(extra)))
    return "；".join(parts)


def check_protocol() -> tuple[str, int, int, int, int, int, int]:
    protocol = _read(PROTOCOL)
    python_protocol = _python_protocol_version()
    typescript_protocol = _typescript_protocol_version(protocol)
    if python_protocol != typescript_protocol:
        raise ValueError(f"内核协议版本 {python_protocol} 与协议包 {typescript_protocol} 不一致")
    for relative in (APPLICATION, EXPORT):
        if re.search(r'PROTOCOL_VERSION\s*=\s*"', _read(relative)):
            raise ValueError(f"{relative} 不得重复定义 PROTOCOL_VERSION")
    defaults = _default_protocol_versions()
    if defaults:
        raise ValueError("协议版本默认值必须引用 PROTOCOL_VERSION：" + "、".join(
            f'{path} 的 "{literal}"' for path, literal in defaults))
    _workspace_dependencies()

    client = _protocol_constants(protocol, "ClientMethods")
    registered = _registered_methods()
    if client != registered:
        raise ValueError("ClientMethods 与内核注册方法不一致：" + _describe(registered - client, client - registered))

    notifications = _protocol_constants(protocol, "ServerNotifications")
    requests = _protocol_constants(protocol, "ServerRequests")
    emitted, requested = _static_messages()
    missing_notifications = emitted - notifications
    if missing_notifications:
        raise ValueError("ServerNotifications 缺少内核发送的通知：" + "、".join(sorted(missing_notifications)))
    missing_requests = requested - requests
    if missing_requests:
        raise ValueError("ServerRequests 缺少内核发送的请求：" + "、".join(sorted(missing_requests)))
    host = _host_notifications()
    unknown_host = host - notifications
    if unknown_host:
        raise ValueError("ServerNotifications 缺少宿主发送的通知：" + "、".join(sorted(unknown_host)))
    unused = notifications - emitted - host - DYNAMIC_KERNEL_NOTIFICATIONS
    if unused:
        raise ValueError("ServerNotifications 含未登记发送方的通知：" + "、".join(sorted(unused)))
    literals = _desktop_method_literals()
    unknown_literals = literals - client - notifications
    if unknown_literals:
        raise ValueError("桌面引用了协议之外的方法：" + "、".join(sorted(unknown_literals)))
    renderer, thread = _check_desktop(client)
    capabilities = _check_capabilities(protocol)
    return python_protocol, len(client), len(notifications), len(requests), capabilities, renderer, thread


def main() -> int:
    try:
        version, methods, notifications, requests, capabilities, renderer, thread = check_protocol()
    except ValueError as error:
        print(f"协议常量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"协议 {version}、{methods} 个方法、{notifications} 个通知、{requests} 个服务端请求、"
          f"{capabilities} 个能力、{renderer} 个渲染层方法、{thread} 个线程方法")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
