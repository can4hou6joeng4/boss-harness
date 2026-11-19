#!/usr/bin/env python3
"""核对显式 none 禁用模型调用的进程级边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "harness" / "src" / "boss_harness"
APPLICATION = "harness/src/boss_harness/application.py"
MAIN_ENTRY = "harness/src/boss_harness/__main__.py"
STARTUP = "harness/src/boss_harness/startup_check.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
PROVIDER = "harness/src/boss_harness/models/provider.py"


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _parse(source: str, relative: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少模块级函数 {name}")


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(text: str, first: str, second: str, label: str) -> int:
    start, end = text.find(first), text.find(second)
    if start == -1 or end == -1 or start > end:
        raise ValueError(f"{label} 中「{first}」必须先于「{second}」")
    return 1


def _call_sites(tree: ast.Module) -> dict[str, list[str]]:
    """按最内层函数名收集调用点；嵌套定义只记最内层，避免同一调用重复计数。"""
    sites: dict[str, list[str]] = {}

    def visit(node: ast.AST, owner: str) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.iter_child_nodes(node):
                visit(child, node.name)
            return
        if isinstance(node, ast.Call):
            target = node.func
            name = (target.id if isinstance(target, ast.Name)
                    else target.attr if isinstance(target, ast.Attribute) else "")
            if name:
                sites.setdefault(name, []).append(owner)
        for child in ast.iter_child_nodes(node):
            visit(child, owner)

    visit(tree, "<module>")
    return sites


def check_model_disable() -> tuple[int, int]:
    application = _read(APPLICATION)
    app_tree = _parse(application, APPLICATION)
    guards = 0
    guards += _expect(('MODEL_CALLS_DISABLED = "当前进程已显式禁用模型调用（provider=none）"',),
                      application, "application.py 常量")

    # 工厂调用点：应用层只经 _provider_for，连接检查只经 _run，别处不得直接调用工厂。
    app_sites = _call_sites(app_tree)
    if app_sites.get("provider_factory") != ["_provider_for"]:
        raise ValueError("application.py 中 provider_factory 的调用点必须只有 _provider_for")
    connections = _read(CONNECTIONS)
    conn_tree = _parse(connections, CONNECTIONS)
    conn_sites = _call_sites(conn_tree)
    if conn_sites.get("provider_factory") != ["_run"]:
        raise ValueError("connections.py 中 provider_factory 的调用点必须只有 _run")
    sites = len(app_sites.get("provider_factory", [])) + len(conn_sites.get("provider_factory", []))
    guards += sites

    # 构造位置：build_provider 只允许入口调用；provider 实例只允许在 models/provider.py 构造。
    build_calls: list[str] = []
    class_calls: list[str] = []
    for path in sorted(KERNEL.rglob("*.py")):
        relative = str(path.relative_to(ROOT))
        for name, owners in _call_sites(_parse(_read(relative), relative)).items():
            if name == "build_provider":
                build_calls.extend(f"{relative}:{owner}" for owner in owners)
            if name in ("AnthropicProvider", "OpenAIResponsesProvider"):
                class_calls.extend(f"{relative}:{owner}" for owner in owners)
    for entry in build_calls:
        if not entry.startswith(MAIN_ENTRY):
            raise ValueError(f"build_provider 只能在入口调用：{entry}")
    for entry in class_calls:
        if not entry.startswith(PROVIDER):
            raise ValueError(f"provider 实例只能在 models/provider.py 构造：{entry}")
    guards += 2

    provider_for = _method(app_tree, application, "ApplicationService", "_provider_for")
    guards += _expect((
        'if self.model_calls_disabled and config.provider != "none":',
        'raise RpcError(-32013, MODEL_CALLS_DISABLED + "，不构造模型供应商",',
        "return self.provider_factory(config)",
    ), provider_for, "_provider_for")
    guards += _ordered(provider_for, 'if self.model_calls_disabled and config.provider != "none":',
                       "return self.provider_factory(config)", "_provider_for")

    discover = _method(app_tree, application, "ApplicationService", "_discover_model_configs")
    guards += _expect(("if self.provider_factory is None or self.model_calls_disabled:",),
                      discover, "_discover_model_configs")
    guards += _ordered(discover, "if self.provider_factory is None or self.model_calls_disabled:",
                       "routes[provider] = resolve_config(environ=candidate_env, provider=provider)",
                       "_discover_model_configs")

    guards += _expect((
        'if self.model_calls_disabled and provider in {"anthropic", "openai"}:',
        'message = (f"{MODEL_CALLS_DISABLED}，{provider} 线路不可用；"',
        'raise RpcError(-32013, message, {"code": "MODEL_PROVIDER_UNAVAILABLE", "provider": provider})',
        'message = "本机没有可用的该模型线路配置"',
    ), _method(app_tree, application, "ApplicationService", "_configured_route"), "_configured_route")

    guards += _expect((
        "return (self.provider_factory is not None and not self.model_calls_disabled",
        'and (policy.provider or base_provider) != "none")',
    ), _method(app_tree, application, "ApplicationService", "_summary_available"), "_summary_available")
    context_read = _method(app_tree, application, "ApplicationService", "on_context_read")
    if context_read.count("self._summary_available(") != 2:
        raise ValueError("on_context_read 的两处 summaryAvailable 必须都经 _summary_available")
    if "provider_factory" in context_read:
        raise ValueError("on_context_read 不得内联判断 provider_factory")
    guards += 2

    compaction_config = _method(app_tree, application, "ApplicationService", "_compaction_model_config")
    guards += _expect((
        "if self.model_calls_disabled:",
        'raise RpcError(-32013, MODEL_CALLS_DISABLED + "，无法生成摘要",',
        '{"code": "COMPACTION_MODEL_UNAVAILABLE", "provider": provider}',
    ), compaction_config, "_compaction_model_config")
    guards += _ordered(compaction_config, "if self.model_calls_disabled:",
                       "route = resolve_config(environ=environ, provider=provider)",
                       "_compaction_model_config")
    guards += _expect((
        'reason = (MODEL_CALLS_DISABLED + "，无法生成被放弃分支摘要" if self.model_calls_disabled',
        '"code": "BRANCH_SUMMARY_MODEL_UNAVAILABLE"',
    ), _method(app_tree, application, "ApplicationService", "_prepare_branch_summary"), "_prepare_branch_summary")
    guards += _expect(("provider = self._provider_for(config)",),
                      _method(app_tree, application, "ApplicationService", "_compaction_provider"),
                      "_compaction_provider")
    guards += _expect(("provider = self._provider_for(config)",),
                      _method(app_tree, application, "ApplicationService", "_runner_for"), "_runner_for")

    plan = _method(app_tree, application, "ApplicationService", "_turn_continuation_plan")
    guards += _expect(('return fail("CONTINUATION_PROVIDER_UNAVAILABLE", MODEL_CALLS_DISABLED + "，无法续接。")',),
                      plan, "_turn_continuation_plan")
    guards += _ordered(plan, "if self.model_calls_disabled:",
                       'config = self._model_config(thread, {"model": source_model})',
                       "_turn_continuation_plan")

    # 新的排队消息与 turn/start 同一入口校验线路：线路不可用时当场拒绝，不留下只会暂停的队列项。
    queue_add = _method(app_tree, application, "ApplicationService", "on_queue_add")
    guards += _expect((
        'raise RpcError(-32004, "请先恢复归档会话，再添加排队消息")',
        "if identity.queue is None and identity.turn is None:",
        "self._thread_route(thread)",
    ), queue_add, "on_queue_add")
    guards += _ordered(queue_add, "identity = resolve_request(", "self._thread_route(thread)", "on_queue_add")
    guards += _ordered(queue_add, 'raise RpcError(-32004, "请先恢复归档会话，再添加排队消息")',
                       "self._thread_route(thread)", "on_queue_add")

    init = _method(app_tree, application, "ApplicationService", "__init__")
    guards += _expect((
        "model_calls_disabled: bool = False) -> None:",
        "if type(model_calls_disabled) is not bool:",
        'raise ValueError("model_calls_disabled 必须是布尔值")',
        'if model_calls_disabled and (config.provider != "none" or provider is not None):',
        'raise ValueError("model_calls_disabled 只能用于 none 默认线路，且不能同时提供 provider")',
        "self.model_calls_disabled = model_calls_disabled",
        "self._model_configs = self._discover_model_configs()",
    ), init, "ApplicationService.__init__")
    guards += _ordered(init, "self.model_calls_disabled = model_calls_disabled",
                       "self._model_configs = self._discover_model_configs()", "ApplicationService.__init__")

    entry = _read(MAIN_ENTRY)
    entry_tree = _parse(entry, MAIN_ENTRY)
    guards += _expect((
        'raw = args.provider if args.provider != "auto" else os.environ.get("BOSS_HARNESS_PROVIDER", "")',
        "return raw.strip().lower()",
    ), _function(entry_tree, entry, "_requested_provider"), "_requested_provider")
    guards += _expect((
        "requested_provider=_requested_provider(args)",
        "requested_model=args.model",
        'model_calls_disabled = _requested_provider(args) == "none"',
        "model_calls_disabled=model_calls_disabled",
        "model_calls_disabled={harness.model_calls_disabled}",
    ), _function(entry_tree, entry, "main"), "入口 main")

    startup = _read(STARTUP)
    startup_tree = _parse(startup, STARTUP)
    guards += _expect((
        'if requested_provider.strip().lower() == "none":',
        '"MODEL_DISABLED", "已显式禁用模型调用。"',
        '"MODEL_NOT_CONFIGURED", "未配置默认模型线路，自动回退为 none。"',
        "其他已配置线路与摘要线路同样不可用",
        "_unconfigured_hint(requested_model)",
    ), _function(startup_tree, startup, "_model_check"), "_model_check")
    # 自动回退只有在本机另一条 OpenAI 线路可解析且 openai 包可发现时才点名它；
    # 解析失败保持通用提示，缺包时改为安装提示。
    guards += _expect((
        '_UNCONFIGURED_HINT = "配置 provider 及对应凭据；核对桌面默认线路时使用 --check --provider openai。"',
        '"本机已配置 OpenAI 线路；需要模型时用 --provider openai（桌面用 BOSS_HARNESS_PROVIDER=openai）启动，"',
        '"本机已配置 OpenAI 线路，但缺少内核运行依赖 openai；按安装步骤安装内核依赖后，"',
        'def _unconfigured_hint(requested_model: str | None) -> str:',
    ), startup, "startup_check.py 回退提示常量")
    guards += _expect((
        'environ["BOSS_HARNESS_MODEL"] = requested_model',
        'resolve_config(environ=environ, provider="openai")',
        "except Exception:",
        "return _UNCONFIGURED_HINT",
        'if not _module_available("openai"):',
        "return _OPENAI_SDK_MISSING_HINT",
        "return _OPENAI_AVAILABLE_HINT",
    ), _function(startup_tree, startup, "_unconfigured_hint"), "_unconfigured_hint")
    guards += _ordered(_function(startup_tree, startup, "_unconfigured_hint"),
                       "return _UNCONFIGURED_HINT", "return _OPENAI_SDK_MISSING_HINT", "_unconfigured_hint")
    guards += _ordered(_function(startup_tree, startup, "_unconfigured_hint"),
                       "return _OPENAI_SDK_MISSING_HINT", "return _OPENAI_AVAILABLE_HINT", "_unconfigured_hint")

    guards += _ordered(init, "self.model_calls_disabled = model_calls_disabled",
                       "self.connections = ConnectionChecks(", "ApplicationService.__init__")
    guards += _expect(("model_calls_disabled=self.model_calls_disabled",),
                      init, "ApplicationService.__init__")
    guards += _expect(('_MODEL_CALLS_DISABLED_CODE = "MODEL_DISABLED"',),
                      connections, "connections.py 常量")
    guards += _expect((
        "model_calls_disabled: bool = False) -> None:",
        "if type(model_calls_disabled) is not bool:",
        'if model_calls_disabled and config.provider != "none":',
        'raise ValueError("model_calls_disabled 只能用于 none 默认线路")',
        'real = config.provider in {"openai", "anthropic"}',
        '"state": "unchecked" if real else "disabled",',
        'if model_calls_disabled:\n            self.report["model"]["code"] = _MODEL_CALLS_DISABLED_CODE',
    ), _method(conn_tree, connections, "ConnectionChecks", "__init__"), "ConnectionChecks.__init__")
    guards += _ordered(_method(conn_tree, connections, "ConnectionChecks", "start"),
                       'self.report[key]["state"] == "disabled"', "threading.Thread(",
                       "ConnectionChecks.start")

    provider_source = _read(PROVIDER)
    build = _function(_parse(provider_source, PROVIDER), provider_source, "build_provider")
    guards += _expect((
        "def build_provider(config: ModelConfig) -> Provider | None:",
        'if config.provider == "none":',
        "return None",
    ), build, "build_provider")
    guards += _ordered(build, 'if config.provider == "none":', "return None", "build_provider")
    return sites, guards


def main() -> int:
    try:
        sites, guards = check_model_disable()
    except (ValueError, SyntaxError) as error:
        print(f"显式禁用模型边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"显式禁用模型边界一致：{sites} 个工厂调用点、{guards} 项目录、摘要、续接、连接、排队、自动回退提示与入口防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
