#!/usr/bin/env python3
"""核对内核注册表与协议常量，成功时输出各类常量数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "packages/protocol/src/index.ts"
APPLICATION = "harness/src/boss_harness/application.py"
SOURCE_ROOT = "harness/src/boss_harness"
EMITTERS = frozenset({"emit", "emit_until", "_emit_committed", "notify"})


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


def check_protocol() -> tuple[int, int, int]:
    protocol = _read(PROTOCOL)
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
    return len(client), len(notifications), len(requests)


def main() -> int:
    try:
        methods, notifications, requests = check_protocol()
    except ValueError as error:
        print(f"协议常量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"{methods} 个方法、{notifications} 个通知、{requests} 个服务端请求")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
