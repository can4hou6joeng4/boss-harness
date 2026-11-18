#!/usr/bin/env python3
"""核对内核注册表与协议常量，成功时输出各类常量数量。"""

from __future__ import annotations

import ast
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
EMITTERS = frozenset({"emit", "emit_until", "_emit_committed", "notify"})
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


def _describe(missing: set[str], extra: set[str]) -> str:
    parts = []
    if missing:
        parts.append("缺少 " + "、".join(sorted(missing)))
    if extra:
        parts.append("多出 " + "、".join(sorted(extra)))
    return "；".join(parts)


def check_protocol() -> tuple[str, int, int, int, int, int]:
    protocol = _read(PROTOCOL)
    python_protocol = _python_protocol_version()
    typescript_protocol = _typescript_protocol_version(protocol)
    if python_protocol != typescript_protocol:
        raise ValueError(f"内核协议版本 {python_protocol} 与协议包 {typescript_protocol} 不一致")
    for relative in (APPLICATION, EXPORT):
        if re.search(r'PROTOCOL_VERSION\s*=\s*"', _read(relative)):
            raise ValueError(f"{relative} 不得重复定义 PROTOCOL_VERSION")

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
    renderer, thread = _check_desktop(client)
    return python_protocol, len(client), len(notifications), len(requests), renderer, thread


def main() -> int:
    try:
        version, methods, notifications, requests, renderer, thread = check_protocol()
    except ValueError as error:
        print(f"协议常量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"协议 {version}、{methods} 个方法、{notifications} 个通知、{requests} 个服务端请求、"
          f"{renderer} 个渲染层方法、{thread} 个线程方法")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
