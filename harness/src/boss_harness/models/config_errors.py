"""模型配置的固定错误原因；说明与建议不接受配置值或原始异常。"""
from __future__ import annotations

from typing import Literal


ModelConfigErrorCode = Literal[
    "MODEL_ENDPOINT_MISSING",
    "MODEL_CREDENTIAL_MISSING",
    "MODEL_CODEX_UNREADABLE",
    "MODEL_CODEX_INVALID_TOML",
    "MODEL_CODEX_NOT_FILE",
]

_DIAGNOSTICS: dict[ModelConfigErrorCode, tuple[str, str]] = {
    "MODEL_ENDPOINT_MISSING": (
        "OpenAI 线路缺少端点。",
        "设置 BOSS_HARNESS_OPENAI_BASE_URL，或在有效 Codex profile 的 provider 中配置 base_url。",
    ),
    "MODEL_CREDENTIAL_MISSING": (
        "OpenAI 线路缺少凭据。",
        "设置 BOSS_HARNESS_OPENAI_API_KEY，或在有效 Codex profile 的 provider 中配置 experimental_bearer_token 或 env_key 指向的环境变量。",
    ),
    "MODEL_CODEX_UNREADABLE": (
        "无法读取 Codex 模型配置文件。",
        "核对 BOSS_HARNESS_CODEX_CONFIG、CODEX_HOME 或默认 Codex 配置的路径与读取权限。",
    ),
    "MODEL_CODEX_INVALID_TOML": (
        "Codex 模型配置的 TOML 格式无效。",
        "检查 Codex 配置的 TOML 语法与 UTF-8 编码；完整显式模型配置可跳过该文件。",
    ),
    "MODEL_CODEX_NOT_FILE": (
        "Codex 模型配置路径不是普通文件。",
        "将 BOSS_HARNESS_CODEX_CONFIG 指向配置文件，或核对 CODEX_HOME 下的 config.toml。",
    ),
}


class ModelConfigError(ValueError):
    """可按固定码诊断的解析错误；保持既有 ValueError 捕获方式。"""

    def __init__(self, code: ModelConfigErrorCode) -> None:
        self.code = code
        self.message, self.hint = _DIAGNOSTICS[code]
        super().__init__(self.message + self.hint)
