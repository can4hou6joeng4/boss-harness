"""本地启动配置自检；只输出固定诊断，不运行模型或业务工具。"""
from __future__ import annotations

import errno
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from boss_harness import __version__
from boss_harness.application import steering_mode_from_environment
from boss_harness.compaction import CompactionPolicy
from boss_harness.models import ModelConfig
from boss_harness.models.capabilities import ModelCatalog
from boss_harness.models.config_errors import ModelConfigError
from boss_harness.private_files import check_private_directory
from boss_harness.resources import AttachmentStore
from boss_harness.turn_limits import model_request_limit_from_environment
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


def _state_check(state_dir: Path) -> dict[str, str]:
    try:
        # 与 StateDirectoryOwner 一样先按 cwd 解析；环境变量中的 ~ 不由内核展开。
        check_private_directory(state_dir.resolve())
    except NotADirectoryError:
        return _check(
            "stateDirectory", "error", "STATE_DIRECTORY_NOT_DIRECTORY", "状态路径或其父级不是目录。",
            "核对 --state-dir、BOSS_HARNESS_DIR 及旧变量 BOSS_CLI_HARNESS_DIR；保留已有文件，选择独立目录。",
        )
    except PermissionError:
        return _check(
            "stateDirectory", "error", "STATE_DIRECTORY_ACCESS_DENIED", "状态目录或已有父目录的访问权限不足。",
            "已有状态目录需可读、可写、可进入；缺失路径的已有父目录需可写、可进入。核对权限后重新连接。",
        )
    except OSError as exc:
        if exc.errno == errno.ENOTSUP:
            return _check(
                "stateDirectory", "error", "STATE_DIRECTORY_UNSUPPORTED", "当前系统无法执行内核要求的私有状态目录保护。",
                "当前私有状态机制要求受支持的 macOS 或 Linux 及相应文件与 ACL 能力；核对系统和解释器。",
            )
        return _check(
            "stateDirectory", "error", "STATE_DIRECTORY_UNAVAILABLE", "无法核对状态目录的本地条件。",
            "核对状态路径、文件系统与访问权限；自检不会创建目录或修改权限。",
        )
    except (ValueError, RuntimeError):
        return _check(
            "stateDirectory", "error", "STATE_DIRECTORY_INVALID", "状态路径或目录安全条件不符合内核要求。",
            "使用当前用户拥有的独立目录，避免根目录及允许他人修改的父目录或 ACL；不要放宽权限。",
        )
    return _check(
        "stateDirectory", "ok", "STATE_DIRECTORY_VALID", "状态目录路径与基本访问条件检查通过。",
        "未创建目录、修改权限或试写文件；未核对磁盘空间、占用锁、索引与会话完整性。",
    )


# 与 ApplicationService 构造时的读取顺序一致；每项复用正常启动的解析函数，只给出静态说明。
_RUNTIME_OPTIONS: tuple[tuple[str, Callable[[], object], str, str], ...] = (
    ("STEERING_MODE_INVALID", steering_mode_from_environment, "转向消息模式配置无效。",
     "将 BOSS_HARNESS_STEERING_MODE 设为 all 或 one-at-a-time，或取消设置。"),
    ("MAX_MODEL_REQUESTS_INVALID", model_request_limit_from_environment, "单回合模型请求上限配置无效。",
     "将 BOSS_HARNESS_MAX_MODEL_REQUESTS 设为 1 到 64 的十进制整数，或取消设置。"),
    ("ATTACHMENT_STORAGE_LIMIT_INVALID", AttachmentStore.limits_from_environment, "附件存储上限配置无效。",
     "将 BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_BYTES 与 BOSS_HARNESS_MAX_ATTACHMENT_STORAGE_OBJECTS 设为正的十进制整数，或取消设置。"),
    ("MODEL_LIMITS_INVALID", ModelCatalog.from_environment, "模型容量配置无效。",
     "核对 BOSS_HARNESS_MODEL_LIMITS 的 JSON 结构、provider/model 键与容量取值，或取消设置；格式见内核与业务契约参考。"),
    ("COMPACTION_CONFIG_INVALID", CompactionPolicy.from_environment, "自动压缩配置无效。",
     "核对 BOSS_HARNESS_COMPACTION 的 JSON 字段、类型与取值范围，或取消设置；格式见内核与业务契约参考。"),
)


def _runtime_check() -> dict[str, str]:
    for code, load, message, hint in _RUNTIME_OPTIONS:
        try:
            load()
        except Exception:
            # 解析错误可能带有环境值或 JSON 片段，只输出登记的静态说明。
            return _check("runtimeOptions", "error", code, message, hint)
    return _check(
        "runtimeOptions", "ok", "RUNTIME_OPTIONS_VALID", "内核运行参数的本地校验通过。",
        "只校验转向模式、模型请求上限、附件存储上限、模型容量与自动压缩环境变量的格式和取值；未读取状态目录中的持久设置。",
    )


def startup_report(
    load_config: Callable[[], ModelConfig], *, state_dir: Path, requested_provider: str = ""
) -> dict[str, Any]:
    """汇总静态检查；检查结果与实际模型、CLI 和平台可用性分别核对。"""
    checks = [_model_check(load_config, requested_provider), _cli_check(), _browser_check(), _state_check(state_dir),
              _runtime_check()]
    return {
        "schemaVersion": 1,
        "version": __version__,
        "pythonVersion": ".".join(str(part) for part in sys.version_info[:3]),
        "ok": all(check["status"] != "error" for check in checks),
        "checks": checks,
    }
