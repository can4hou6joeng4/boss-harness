#!/usr/bin/env python3
"""核对显式 none 禁用模型调用的进程级边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness import __main__ as entrypoint, startup_check  # noqa: E402
from boss_harness.models import ModelConfig  # noqa: E402
from boss_harness.tools.boss_cli import BinaryChoice  # noqa: E402

KERNEL = ROOT / "harness" / "src" / "boss_harness"
APPLICATION = "harness/src/boss_harness/application.py"
MAIN_ENTRY = "harness/src/boss_harness/__main__.py"
STARTUP = "harness/src/boss_harness/startup_check.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
PROVIDER = "harness/src/boss_harness/models/provider.py"
ANTHROPIC = "harness/src/boss_harness/models/anthropic_provider.py"


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

    summary_available = _method(app_tree, application, "ApplicationService", "_summary_available")
    guards += _expect((
        "provider = policy.provider or base_provider",
        'if self.provider_factory is None or self.model_calls_disabled or provider == "none":\n            return False',
        'if provider == "anthropic" and provider != base_provider:\n            return has_anthropic_credential(os.environ)',
    ), summary_available, "_summary_available")
    guards += _ordered(summary_available, "return False", "return has_anthropic_credential(os.environ)",
                       "_summary_available")
    if any(call in summary_available for call in ("resolve_config(", "self._compaction_model_config(",
                                                  "self._provider_for(", "self._compaction_provider(")):
        raise ValueError("_summary_available 不得读取模型配置文件或构造供应商")
    guards += 1
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
        "normalized = raw.strip().lower()",
        'return "" if normalized == "auto" else normalized',
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
        'resolve_config(provider="openai", model_override=requested_model)',
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
    provider_tree = _parse(provider_source, PROVIDER)
    build = _function(provider_tree, provider_source, "build_provider")
    guards += _expect((
        "def build_provider(config: ModelConfig) -> Provider | None:",
        'if config.provider == "none":',
        "return None",
    ), build, "build_provider")
    guards += _ordered(build, 'if config.provider == "none":', "return None", "build_provider")

    # 启动和自检提示共用模型选择。参数与环境变量分别去除首尾空白，再判断是否覆盖下一项。
    guards += _expect((
        "return resolve_config(provider=explicit, model_override=args.model)",
    ), _function(entry_tree, entry, "_build_config"), "_build_config")
    guards += _expect((
        "for name in names:",
        'value = (env.get(name) or "").strip()',
        "if value:\n            return value",
    ), _function(provider_tree, provider_source, "_configured_model"), "_configured_model")
    # 自动线路判断、目录发现、摘要解析与启动自检共用同一条凭据规则：只有空白的值视为未设置。
    guards += _expect((
        "def _has_configured_value(env: Mapping[str, str], *names: str) -> bool:",
        'return any((env.get(name) or "").strip() for name in names)',
    ), _function(provider_tree, provider_source, "_has_configured_value"), "_has_configured_value")
    guards += _expect((
        "def has_anthropic_credential(env: Mapping[str, str]) -> bool:",
        'return _has_configured_value(env, "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")',
    ), _function(provider_tree, provider_source, "has_anthropic_credential"), "has_anthropic_credential")
    guards += _expect((
        'resolved = "anthropic" if has_anthropic_credential(env) else "none"',
    ), _function(provider_tree, provider_source, "resolve_config"), "resolve_config")
    if 'bool(env.get("ANTHROPIC_API_KEY")' in provider_source:
        raise ValueError("provider.py 不得绕过 _has_configured_value 直接判定 Anthropic 凭据")
    guards += 1
    if "ANTHROPIC_API_KEY" in application or "ANTHROPIC_AUTH_TOKEN" in application:
        raise ValueError("application.py 不得直接读取 Anthropic 凭据变量，须共用 has_anthropic_credential")
    guards += 1
    guards += _expect((
        'if provider == "anthropic" and not has_anthropic_credential(environ):',
        "continue",
    ), discover, "_discover_model_configs")
    guards += _expect((
        'if provider == "anthropic" and not has_anthropic_credential(environ):',
        'raise RpcError(-32013, "本机没有可用的摘要模型线路配置",',
    ), _method(app_tree, application, "ApplicationService", "_compaction_model_config"),
        "_compaction_model_config")
    guards += _expect((
        'override = (model_override or "").strip()',
        'if override:\n        env["BOSS_HARNESS_MODEL"] = override',
        'model=_configured_model(env, "BOSS_HARNESS_MODEL", "BOSS_HARNESS_ANTHROPIC_MODEL") or DEFAULT_MODEL,',
    ), _function(provider_tree, provider_source, "resolve_config"), "resolve_config")
    guards += _expect((
        'explicit_model = _configured_model(env, "BOSS_HARNESS_MODEL", "BOSS_HARNESS_OPENAI_MODEL")',
    ), _function(provider_tree, provider_source, "_openai_config"), "_openai_config")
    # 环境变量里的 auto 与命令行默认值同义，且必须先于未知取值检查归一化。
    guards += _expect((
        'if requested == "auto":\n        requested = ""',
    ), _function(provider_tree, provider_source, "resolve_config"), "resolve_config")
    guards += _ordered(_function(provider_tree, provider_source, "resolve_config"),
                       'if requested == "auto":',
                       'if requested and requested not in _EXPLICIT_PROVIDERS:', "resolve_config")
    # 凭据先去除首尾空白再交给 SDK；纯空白不遮蔽另一项真实凭据。
    anthropic = _read(ANTHROPIC)
    anthropic_tree = _parse(anthropic, ANTHROPIC)
    anthropic_init = _method(anthropic_tree, anthropic, "AnthropicProvider", "__init__")
    guards += _expect((
        'env_api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()',
        'env_auth_token = (os.environ.get("ANTHROPIC_AUTH_TOKEN") or "").strip()',
        'credential_options["api_key"] = env_api_key',
        "elif env_auth_token:",
        "snapshot = anthropic.Anthropic(timeout=30.0, max_retries=0, **credential_options)",
        'snapshot_api_key = snapshot.api_key.strip() if isinstance(snapshot.api_key, str) else ""',
        'snapshot_auth_token = snapshot.auth_token.strip() if isinstance(snapshot.auth_token, str) else ""',
        "if snapshot_api_key:",
        "if snapshot_auth_token:",
        "if not (snapshot_api_key or snapshot_auth_token)",
    ), anthropic_init, "AnthropicProvider.__init__")
    if "anthropic.Anthropic(timeout=30.0, max_retries=0)\n" in anthropic:
        raise ValueError("AnthropicProvider 不得让 SDK 直接读取未去除空白的凭据")
    guards += 1
    if 'env.get("BOSS_HARNESS_MODEL")' in provider_source:
        raise ValueError("provider.py 不得绕过 _configured_model 直接读取 BOSS_HARNESS_MODEL")
    guards += 1
    return sites, guards


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"自检行为变化 {label}：期望 {expected!r}，实际 {actual!r}")


def _check_startup_behavior() -> int:
    # 开关优先级和回退判断走真实入口。备用线路与 CLI 只用本地替身，避免读取机器配置。
    cases = (
        ("命令行覆盖环境", {"BOSS_HARNESS_PROVIDER": "openai"}, ("--provider", "none"),
         "disabled", 0, "本进程不使用任何模型线路"),
        ("环境变量归一化", {"BOSS_HARNESS_PROVIDER": " NoNe "}, ("--strict",),
         "disabled", 1, "none 不会禁止招聘 CLI 或平台网络"),
        ("未指定线路", {}, (), "unconfigured", 0, "配置 provider 及对应凭据"),
        ("自动回退且未安装 SDK", {"BOSS_HARNESS_PROVIDER": " AuTo "}, ("--strict",),
         "missing-sdk", 1, "缺少内核运行依赖 openai"),
        ("空白凭据且备用线路可用", {"ANTHROPIC_API_KEY": " \t", "ANTHROPIC_AUTH_TOKEN": "\n"},
         ("--provider", "auto"), "available", 0, "核对这条线路使用 --check --provider openai"),
    )
    model = "diagnostic-demo"
    for label, environment, flags, state, expected_exit, hint in cases:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            backup_config = ModelConfig(provider="openai", model=model)
            config_error = ValueError("模拟配置解析失败") if state == "unconfigured" else None
            choice = BinaryChoice(str(root / "missing-boss"), "path")
            output = StringIO()
            args = ["--check", "--state-dir", str(root / "state"), "--model", model, *flags]
            with (patch.dict(os.environ, environment, clear=True),
                  patch.object(entrypoint, "build_provider", side_effect=AssertionError("自检不应创建模型供应商")),
                  patch.object(startup_check, "resolve_binary", return_value=choice),
                  patch.object(startup_check, "resolve_config", return_value=backup_config,
                               side_effect=config_error) as resolve,
                  patch.object(startup_check, "_module_available", return_value=state == "available") as sdk,
                  patch.object(startup_check, "startup_report", wraps=startup_check.startup_report) as report_call,
                  redirect_stdout(output)):
                exit_code = entrypoint.main(args)

            _expect_value(exit_code, expected_exit, f"{label}退出码")
            _expect_value(report_call.call_count, 1, f"{label}自检次数")
            requested = "none" if state == "disabled" else ""
            _expect_value(report_call.call_args.kwargs["requested_provider"], requested, f"{label}入口归一化")
            report = json.loads(output.getvalue())
            _expect_value(report["ok"], True, f"{label}报告状态")
            check = next(item for item in report["checks"] if item["name"] == "model")
            expected_code = "MODEL_DISABLED" if state == "disabled" else "MODEL_NOT_CONFIGURED"
            _expect_value((check["status"], check["code"]), ("warning", expected_code), f"{label}模型诊断")
            _expect_value(hint in check["hint"], True, f"{label}提示")
            if state == "disabled":
                resolve.assert_not_called()
            else:
                resolve.assert_called_once_with(provider="openai", model_override=model)
            if state in {"disabled", "unconfigured"}:
                sdk.assert_not_called()
            else:
                sdk.assert_called_once_with("openai")
    return len(cases)


def main() -> int:
    try:
        sites, guards = check_model_disable()
        scenarios = _check_startup_behavior()
    except (ValueError, SyntaxError, AssertionError) as error:
        print(f"显式禁用模型边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"显式禁用模型边界一致：{sites} 个工厂调用点、{guards} 项结构防护、{scenarios} 个启动自检场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
