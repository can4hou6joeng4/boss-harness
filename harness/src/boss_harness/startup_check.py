"""本地启动配置自检；只输出固定诊断，不运行模型或业务工具。"""
from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

from boss_harness import __version__
from boss_harness.models import ModelConfig
from boss_harness.models.config_errors import ModelConfigError
from boss_harness.tools.boss_cli import binary_available, resolve_binary, resolve_browser_source_override


def _check(name: str, status: str, code: str, message: str, hint: str) -> dict[str, str]:
    return {"name": name, "status": status, "code": code, "message": message, "hint": hint}


def _model_check(load_config: Callable[[], ModelConfig], requested_provider: str) -> dict[str, str]:
    try:
        config = load_config()
    except ModelConfigError as exc:
        return _check("model", "error", exc.code, exc.message, exc.hint)
    except Exception:
        # 配置异常可能带有文件名、环境值或原始 TOML，不输出异常文本。
        return _check(
            "model", "error", "MODEL_CONFIG_INVALID", "模型配置无法解析。",
            "核对 provider、显式模型配置及本地 Codex 配置；完整配置方式见使用指南。",
        )
    if config.max_tokens <= 0:
        return _check(
            "model", "error", "MODEL_CONFIG_INVALID", "模型输出上限必须是正整数。",
            "将 BOSS_HARNESS_MAX_TOKENS 设为正整数，或取消设置以使用默认值。",
        )
    if config.provider == "none":
        if requested_provider.strip().lower() == "none":
            return _check(
                "model", "warning", "MODEL_DISABLED", "已显式禁用模型调用。",
                "需要模型回合时配置模型线路；none 不会禁止招聘 CLI 或平台网络。",
            )
        return _check(
            "model", "warning", "MODEL_NOT_CONFIGURED", "未配置默认模型线路，自动回退为 none。",
            "配置 provider 及对应凭据；核对桌面默认线路时使用 --check --provider openai。",
        )
    has_credential = bool(config.api_key) if config.provider == "openai" else any(
        (os.environ.get(name) or "").strip() for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    )
    if not config.model or not has_credential:
        return _check(
            "model", "error", "MODEL_CONFIG_INCOMPLETE", "模型配置缺少必需字段。",
            "配置非空模型与对应 provider 的凭据；OpenAI 线路还需显式端点或有效 Codex profile。",
        )
    return _check(
        "model", "ok", "MODEL_CONFIG_VALID", "本地模型配置解析通过。",
        "未构造模型客户端或发起请求，仍需另行核对网络与认证。",
    )


def _cli_check() -> dict[str, str]:
    try:
        available = binary_available(resolve_binary().path)
    except (OSError, ValueError):
        available = False
    if not available:
        return _check(
            "bossCli", "warning", "BOSS_CLI_UNAVAILABLE", "未发现可用的业务 CLI 可执行文件。",
            "安装 boss-agent-cli，核对 BOSS_CLI_BIN、并排虚拟环境或 PATH；同时检查文件执行权限。",
        )
    return _check(
        "bossCli", "ok", "BOSS_CLI_FOUND", "已发现业务 CLI 可执行文件。",
        "只检查文件与执行权限，未运行 CLI、查询版本或核对平台登录。",
    )


def _browser_check() -> dict[str, str]:
    try:
        resolve_browser_source_override()
    except ValueError:
        return _check(
            "browserSource", "error", "BROWSER_SOURCE_INVALID", "浏览器来源配置无效。",
            "将 BOSS_HARNESS_BROWSER_SOURCE 设为 auto、existing-browser、stored-cookie，或取消设置。",
        )
    return _check(
        "browserSource", "ok", "BROWSER_SOURCE_VALID", "本地浏览器来源选项校验通过。",
        "未读取浏览器或 Cookie，也未核对上游 CLI 对该选项的支持。",
    )


def startup_report(
    load_config: Callable[[], ModelConfig], *, requested_provider: str = ""
) -> dict[str, Any]:
    """汇总静态检查；检查结果与实际模型、CLI 和平台可用性分别核对。"""
    checks = [_model_check(load_config, requested_provider), _cli_check(), _browser_check()]
    return {
        "schemaVersion": 1,
        "version": __version__,
        "pythonVersion": ".".join(str(part) for part in sys.version_info[:3]),
        "ok": all(check["status"] != "error" for check in checks),
        "checks": checks,
    }
