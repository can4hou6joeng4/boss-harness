#!/usr/bin/env python3
"""核对 RPC 方法表与检查脚本的覆盖完整性。

`ApplicationService._register` 里的方法表是外壳可见契约的唯一入口：每个键都要映射到
已声明的方法或受控的内联路由，每个 `on_*` 方法都必须出现在表里，且每个 handler 都要
被至少一个检查脚本真实调用。新增 handler 却不注册、注册了却没人覆盖、或检查脚本被
删减造成覆盖回退，都会在这里失败——这是覆盖本身的不变量，而不是某个入口的行为。
静态部分解析方法表并扫描 `scripts/` 的调用；行为部分构造真实服务，核对 `server._methods`
与静态表逐项一致、全部可调用，并验证空服务上的代表读取可用。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
SCRIPTS = ROOT / "scripts"
SELF = "check_handler_coverage.py"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
EXPECTED_METHODS = 70
EXPECTED_HANDLERS = 64
INLINE_ROUTES = {"connection/read", "connection/check", "platform/login/start",
                 "platform/login/read", "platform/login/complete", "platform/login/cancel"}


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _tree(relative: str) -> ast.Module:
    try:
        return ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _application(tree: ast.Module) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ApplicationService":
            return node
    raise ValueError("application.py 缺少 ApplicationService")


def _register_table(tree: ast.Module) -> dict[str, str]:
    """方法名 -> 处理函数名；内联 lambda 记为 `<inline>`。"""
    for child in _application(tree).body:
        if isinstance(child, ast.FunctionDef) and child.name == "_register":
            for stmt in child.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Dict):
                    table: dict[str, str] = {}
                    for key, value in zip(stmt.value.keys, stmt.value.values):
                        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                            raise ValueError("方法表的键必须是字符串常量")
                        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) \
                                and value.value.id == "self":
                            table[key.value] = value.attr
                        else:
                            table[key.value] = "<inline>"
                    return table
    raise ValueError("ApplicationService._register 缺少方法表")


def _declared(application: ast.ClassDef) -> set[str]:
    return {child.name for child in application.body
            if isinstance(child, ast.FunctionDef) and child.name.startswith("on_")}


def _script_text() -> str:
    texts = []
    for path in sorted(SCRIPTS.glob("check_*.py")):
        if path.name == SELF:
            continue
        texts.append(path.read_text(encoding="utf-8"))
    return "\n".join(texts)


def _check_structures() -> int:
    tree = _tree(MODULE)
    table = _register_table(tree)
    application = _application(tree)
    declared = _declared(application)
    handlers = {name for name in table.values() if name != "<inline>"}
    inline = {method for method, name in table.items() if name == "<inline>"}
    checked = 0
    checked += _expect_value(len(table), EXPECTED_METHODS, "方法表数量")
    checked += _expect_value(len(handlers), EXPECTED_HANDLERS, "handler 数量")
    checked += _expect_value(inline, INLINE_ROUTES, "内联路由集合")
    checked += _expect_value(handlers - declared, set(), "注册未声明")
    checked += _expect_value(declared - handlers, set(), "声明未注册")
    scripts = _script_text()
    unchecked = sorted(name for name in handlers if f".{name}(" not in scripts)
    checked += _expect_value(unchecked, [], "handler 无检查调用")
    checked += _expect_value(all(method and "/" in method or method in {"initialize", "initialized", "shutdown"}
                                 for method in table), True, "方法名格式")
    for method in ("initialize", "initialized", "shutdown", "thread/leaf/set",
                   "thread/branches/list", "thread/branchSummary/read"):
        checked += _expect_value(method in table, True, f"关键路由 {method}")
    return checked


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"方法表覆盖行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


@contextmanager
def _clean_environment():
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        yield


def _behavior_checks() -> int:
    checked = 0
    table = _register_table(_tree(MODULE))
    with TemporaryDirectory() as directory, _clean_environment():
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, root / "state", ModelConfig(provider="none", model="none"),
                                     None, workspace=workspace)
        try:
            registered = getattr(server, "_methods")
            checked += _expect_value(set(registered), set(table), "注册键集合")
            checked += _expect_value(all(callable(handler) for handler in registered.values()),
                                     True, "注册可调用")
            checked += _expect_value(service.on_initialize(
                {"clientInfo": {"name": "probe", "version": "1.0"},
                 "protocolVersion": "0.2.0"})["protocolVersion"], "0.2.0", "握手协议")
            checked += _expect_value(service.on_initialized(None), {"ready": True}, "握手完成")
            checked += _expect_value(isinstance(service.on_thread_list({})["threads"], list), True,
                                     "空线程列表")
            checked += _expect_value(isinstance(service.on_model_list({})["models"], list), True,
                                     "模型列表")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read("docs/TECHNICAL_REFERENCE.md")
    if "scripts/check_handler_coverage.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_handler_coverage.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少方法表覆盖检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _behavior_checks()
    _check_documentation(structures, behaviors)
    print(f"方法表覆盖检查通过：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
