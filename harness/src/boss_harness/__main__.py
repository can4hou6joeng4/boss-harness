"""CLI composition root for the independent recruitment app-server."""
from __future__ import annotations

import argparse
import os
import json
import sys
from pathlib import Path

from boss_harness import __version__
from boss_harness.application import ApplicationService as Harness, _approval_timeout
from boss_harness.models import DEFAULT_MODEL, ModelConfig, build_provider, resolve_config
from boss_harness.models.config_errors import ModelConfigError
from boss_harness.models.secret import redact_secrets
from boss_harness.rpc import JsonRpcServer, describe_failure
from boss_harness.tools.boss_cli import resolve_browser_source_override

def _failure_text(exc: Exception) -> str:
    """stderr 常被原样贴进 Issue：本地文件错误不带路径，其余文本抹掉凭据形态。"""
    return redact_secrets(describe_failure(exc))


def _default_state_dir() -> Path:
    """内核状态目录：新变量优先，旧变量其次，最后按目录存在性选择默认位置。"""
    configured = os.environ.get("BOSS_HARNESS_DIR") or os.environ.get("BOSS_CLI_HARNESS_DIR")
    if configured:
        return Path(configured)
    preferred = Path.home() / ".boss-harness" / "harness"
    legacy = Path.home() / ".boss-cli" / "harness"
    # 升级后不丢历史会话：新目录尚未建立、而旧目录已存在时沿用旧目录；否则用新路径。
    return legacy if legacy.exists() and not preferred.exists() else preferred


DEFAULT_STATE_DIR = _default_state_dir()


def _build_config(args: argparse.Namespace) -> ModelConfig:
    """命令行 > 环境变量；`--provider none` 可强制不调用模型（仍可调用招聘 CLI）。

    provider 交给 `resolve_config` 一起决定，不能解析完再 `replace`：模型配置的字段会随
    provider 增加，而各线路的端点与凭据来源不同，事后替换会让 `--provider openai` 拿到
    Anthropic 的端点并丢掉 Codex 配置里的凭据。
    `--model` 也先参与解析，使完整显式线路无需读取本地配置。
    """
    explicit = None if args.provider == "auto" else args.provider
    env = dict(os.environ)
    if args.model:
        env["BOSS_HARNESS_MODEL"] = args.model
    return resolve_config(environ=env, provider=explicit)


def _requested_provider(args: argparse.Namespace) -> str:
    """用户点名的 provider：命令行优先，其次环境变量，未指定时为空串。

    归一化与 `resolve_config` 一致。启动自检与正式启动共用这一个判断，
    「显式 none」的自检结论（`MODEL_DISABLED`）和内核的实际开关才不会各说各话。
    """
    raw = args.provider if args.provider != "auto" else os.environ.get("BOSS_HARNESS_PROVIDER", "")
    return raw.strip().lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="boss-harness", description="BOSS Harness Agent Harness 内核")
    parser.add_argument("--listen", default="stdio://", help="传输端点，当前仅支持 stdio://")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="内核状态目录")
    maintenance = parser.add_mutually_exclusive_group()
    maintenance.add_argument("--repair-state", action="store_true", help="独占状态目录，备份 SQLite 索引后从原始日志重建")
    maintenance.add_argument("--check", action="store_true", help="只读检查本地启动配置，输出脱敏报告（默认 JSON），不联网、不执行业务 CLI")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="--check 的输出格式：json（默认，供程序解析）或 text（终端可读）")
    parser.add_argument("--strict", action="store_true",
                        help="与 --check 一起使用：没有错误但存在警告时返回退出码 1")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "anthropic", "openai", "codex", "none"],
        help="模型供应商；openai 与其别名 codex 走 Responses 线路（显式 BOSS_HARNESS_OPENAI_* 或 Codex 配置），"
             "none 表示整个进程不调用模型、回合走确定性路径（仍可调用招聘 CLI）",
    )
    parser.add_argument("--model", default=None, help=f"模型 id，默认 {DEFAULT_MODEL}")
    parser.add_argument("--version", action="version", version=f"boss-harness {__version__}")
    args = parser.parse_args(argv)

    if args.format != "json" and not args.check:
        parser.error("--format 只能与 --check 一起使用")
    if args.strict and not args.check:
        parser.error("--strict 只能与 --check 一起使用")

    if args.check:
        from boss_harness.startup_check import render_text, startup_report
        report = startup_report(lambda: _build_config(args), state_dir=Path(args.state_dir),
                                requested_provider=_requested_provider(args), requested_model=args.model)
        print(render_text(report) if args.format == "text" else json.dumps(report, ensure_ascii=False))
        if not report["ok"]:
            return 2
        warned = any(check["status"] == "warning" for check in report["checks"])
        return 1 if args.strict and warned else 0

    if args.repair_state:
        from boss_harness.maintenance import repair_index
        try:
            print(json.dumps(repair_index(Path(args.state_dir)), ensure_ascii=False))
            return 0
        except Exception as exc:
            print(f"[harness] 索引修复失败：{_failure_text(exc)}", file=sys.stderr)
            return 2

    if args.listen != "stdio://":
        print(f"[harness] 暂不支持 --listen {args.listen}", file=sys.stderr)
        return 2

    try:
        config = _build_config(args)
        provider = build_provider(config)
    except ModelConfigError as exc:
        print(f"[harness] 模型配置不可用（{exc.code}）：{exc}", file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        # 模型 SDK 是内核依赖：缺包不是配置错误，直接给出仓库已有的安装命令。
        print(f"[harness] 缺少内核运行依赖（{exc.name or '未知模块'}）；先按安装步骤安装内核依赖："
              "uv pip install --python .venv/bin/python -e ./harness", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        # 这里只包住「配置解析 + 构造 provider」两件事，所以宽捕获是安全的：任何失败都意味着
        # 模型线路起不来（缺凭据、缺端点、SDK 拒绝无凭据构造等），应当给出可读信息并以 2 退出。
        print(f"[harness] 模型配置不可用（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        return 2
    # 浏览器来源同样是进程级配置：在入口处校验，错误才能点名变量与可选值。留到工具桥
    # 构造时才失败会被 `_new_bridge` 统一包装成「工具桥工厂无法创建实例」，用户无从排查。
    try:
        resolve_browser_source_override()
    except ValueError as exc:
        print(f"[harness] 浏览器来源配置不可用（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        return 2
    server = JsonRpcServer()
    # 显式 none 是进程级开关：不列出其他线路、不解析摘要线路，整个进程不构造模型传输。
    # 未指定 provider 而自动回退得到的 none 只是没有默认线路，其他已配置线路照常可选。
    model_calls_disabled = _requested_provider(args) == "none"
    try:
        # 构造 Harness 会创建会话目录；state-dir 不可写同样是启动期的配置问题，应当走同一个干净
        # 退出码，而不是把回溯打到 stdout（stdout 只走协议）并以 1 结束。
        harness = Harness(server, Path(args.state_dir), config, provider, provider_factory=build_provider,
                          model_calls_disabled=model_calls_disabled)
    except (OSError, ValueError) as exc:
        print(f"[harness] 启动失败（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        # 固定文字，不带路径或取值：自检不联网、不写入，能把同一条件映射为检查码与处理建议。
        print("[harness] 可用相同参数与环境运行 boss-harness --check，查看本地条件的检查码与处理建议。",
              file=sys.stderr)
        return 2
    bridge = harness.tools
    print(
        f"[harness] listening on stdio, state={args.state_dir}, "
        f"boss binary={bridge.binary} (source={bridge.source}, available={bridge.available()}), "
        f"model provider={harness.config.provider} model={harness.config.model} driven={harness.provider is not None} "
        f"model_calls_disabled={harness.model_calls_disabled}",
        file=sys.stderr,
    )
    harness.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
