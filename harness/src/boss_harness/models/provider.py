"""模型供应商抽象与配置解析。

职责边界参考 Pi 的 Provider/Models 划分：provider 只管「把一次请求变成事件流」，
模型选择与凭据解析在这里完成，调用方不接触供应商 SDK。

当前有两条真实线路，各自一套线协议：
- `anthropic`：Anthropic Messages，凭据取环境变量 `ANTHROPIC_*`；
- `openai`：OpenAI Responses，凭据与端点取自 `~/.codex/config.toml`（或 `BOSS_HARNESS_OPENAI_*`）。
另有 `none`（确定性回合，不调用模型）。
"""
from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlparse

from boss_harness.models.config_errors import ModelConfigError
from boss_harness.models.secret import Secret
from boss_harness.models.types import ModelRequest, StreamEvent

#: 技能规定的默认模型。用户可用 BOSS_HARNESS_MODEL 覆盖。
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_MAX_TOKENS = 64000
DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS = 600
MAX_MODEL_REQUEST_TIMEOUT_SECONDS = 3600

_FIRST_PARTY_HOST = "api.anthropic.com"


def _is_first_party_base_url(base_url: str | None) -> bool:
    """`base_url` 是否指向 Anthropic 官方主机。

    用主机名精确比较而非子串包含：`api.anthropic.com.evil.example` 与
    `api.anthropic.com@proxy.example` 都含有同样子串，实际却指向别处；反过来说 DNS
    主机名不区分大小写，大写的官方域名同样应算官方。`urlparse` 会小写化主机名并剥掉
    userinfo，未写 scheme 时先按网络位置补全；末尾的根点（`api.anthropic.com.`）是同一
    主机的完全限定写法，一并归一。
    """
    if base_url is None or not base_url.strip():
        # 没有自定义端点即直连官方默认地址。
        return True
    candidate = base_url.strip()
    if "://" not in candidate:
        candidate = f"//{candidate}"
    try:
        host = (urlparse(candidate).hostname or "").rstrip(".")
    except ValueError:
        # 畸形的 IPv6 字面量等解析不出主机名；交给 SDK 在真正建连时报错，
        # 判定本身不能因此让配置解析崩溃。
        return False
    return host == _FIRST_PARTY_HOST

ProviderName = Literal["anthropic", "openai", "none"]

#: 显式接受的值；`codex` 是 `openai` 的别名，便于按来源称呼这条线路。
_EXPLICIT_PROVIDERS = {"none", "anthropic", "openai", "codex"}


@dataclass(frozen=True)
class ModelConfig:
    provider: ProviderName
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    effort: str | None = None
    thinking: Mapping[str, object] | None = None
    base_url: str | None = None
    #: 服务端 fallback 是 beta 能力，仅在直连官方域名时默认开启。
    server_side_fallback: bool = False
    #: openai 线路的 bearer 凭据，用 Secret 包装：repr 脱敏，且不可 JSON 序列化。
    api_key: Secret | None = None
    request_timeout_seconds: int = DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS


class Provider(Protocol):
    id: str

    def stream(self, request: ModelRequest) -> Iterator[StreamEvent]:
        """产出一条事件流；生成开始后的失败必须以 `error` 事件终止，不抛异常。"""
        ...


def resolve_config(
    environ: Mapping[str, str] | None = None, provider: str | None = None
) -> ModelConfig:
    """决定用哪个供应商。

    优先级：显式 `provider` 入参（来自命令行）> `BOSS_HARNESS_PROVIDER` >「有 Anthropic
    凭据就用 anthropic，否则 none」。没有可用凭据时返回 `none`，退回确定性回合。

    `BOSS_HARNESS_MODEL` 覆盖进程默认线路的模型；未设置时分别读取 provider 专属模型变量或
    Codex profile。provider 专属变量也用于同一进程列举其他已配置线路。

    `provider` 必须在这里就参与决策，不能在解析完之后再替换 provider 字段：各线路的端点与
    凭据来源不同（anthropic 取 `ANTHROPIC_*`，openai 取 Codex 配置），事后替换会拿到另一条
    线路的端点，并丢掉这条线路的凭据。
    """
    env = dict(os.environ if environ is None else environ)

    requested = (
        provider if provider is not None else env.get("BOSS_HARNESS_PROVIDER") or ""
    ).strip().lower()
    if requested == "codex":
        requested = "openai"

    if requested and requested not in _EXPLICIT_PROVIDERS:
        # 拼错的值必须响亮地失败。命令行侧用 argparse choices 拒绝未知值，环境变量侧若不校验，
        # 就会出现「以为切到了 openai，实际在跑 anthropic 甚至确定性回合」这种无声的错配。
        raise ModelConfigError("MODEL_PROVIDER_UNKNOWN")

    if requested in _EXPLICIT_PROVIDERS:
        resolved: ProviderName = requested  # type: ignore[assignment]
    else:
        has_anthropic_credential = bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))
        resolved = "anthropic" if has_anthropic_credential else "none"

    if resolved == "openai":
        return _openai_config(env)

    base_url = (env.get("ANTHROPIC_BASE_URL") or "").strip() or None

    thinking: Mapping[str, object] | None = None
    if (env.get("BOSS_HARNESS_THINKING") or "").strip() == "summarized":
        thinking = {"type": "adaptive", "display": "summarized"}

    # none 线路不发模型请求，不因这个只属于 Anthropic 请求形状的开关而失败。
    server_side_fallback = _server_side_fallback(
        env, _is_first_party_base_url(base_url), strict=resolved == "anthropic")

    return ModelConfig(
        provider=resolved,
        model=(env.get("BOSS_HARNESS_MODEL")
               or env.get("BOSS_HARNESS_ANTHROPIC_MODEL")
               or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        max_tokens=_max_tokens(env),
        request_timeout_seconds=_request_timeout_seconds(env),
        effort=(env.get("BOSS_HARNESS_EFFORT") or "").strip() or None,
        thinking=thinking,
        base_url=base_url,
        server_side_fallback=server_side_fallback,
    )


def _openai_config(env: Mapping[str, str]) -> ModelConfig:
    """完整显式配置独立运行；缺项时才读取 Codex 文件补全。

    端点与凭据刻意不走 `ANTHROPIC_*`：那是另一条线路的地址，混用会把请求发错地方。
    """
    from boss_harness.models.codex_config import load_profile

    explicit_model = (env.get("BOSS_HARNESS_MODEL") or env.get("BOSS_HARNESS_OPENAI_MODEL") or "").strip()
    explicit_url = (env.get("BOSS_HARNESS_OPENAI_BASE_URL") or "").strip()
    explicit_key = (env.get("BOSS_HARNESS_OPENAI_API_KEY") or "").strip()
    # Optional file settings must not make a fully specified route depend on
    # unrelated local files or an interpreter's TOML parser availability.
    profile = None if all((explicit_model, explicit_url, explicit_key)) else load_profile(environ=env, strict=True)
    model = explicit_model or (profile.model if profile else "") or DEFAULT_MODEL
    base_url = explicit_url or (profile.base_url if profile else None)
    file_key = profile.bearer_token.get() if profile and profile.bearer_token else ""
    # Codex 官方推荐把 provider 密钥放在环境变量中；显式文件令牌保持优先以兼容既有配置。
    if not file_key and profile and profile.env_key:
        file_key = (env.get(profile.env_key) or "").strip()
    raw_key = explicit_key or file_key
    effort = (env.get("BOSS_HARNESS_EFFORT") or "").strip() or (profile.effort if profile else None)

    if not base_url:
        raise ModelConfigError("MODEL_ENDPOINT_MISSING")
    if not raw_key:
        raise ModelConfigError("MODEL_CREDENTIAL_MISSING")

    return ModelConfig(
        provider="openai",
        model=model,
        max_tokens=_max_tokens(env),
        request_timeout_seconds=_request_timeout_seconds(env),
        effort=effort,
        base_url=base_url,
        api_key=Secret(raw_key),
    )


_SWITCH_ON = frozenset({"1", "true", "yes", "on"})
_SWITCH_OFF = frozenset({"0", "false", "no", "off"})


def _server_side_fallback(env: Mapping[str, str], default: bool, *, strict: bool) -> bool:
    """未设置按端点取默认值，空值为关闭；其余须是可识别的开关写法。

    拼错或大小写不同的关闭写法若被当作开启，请求会带上网关未必支持的 beta 参数，
    因此无法识别的取值明确失败，错误不带原始取值；`strict` 为假时改用默认值。
    """
    raw = env.get("BOSS_HARNESS_SERVER_FALLBACK")
    if raw is None:
        return default
    value = raw.strip().lower()
    if not value or value in _SWITCH_OFF:
        return False
    if value in _SWITCH_ON:
        return True
    if not strict:
        return default
    raise ModelConfigError("MODEL_SERVER_FALLBACK_INVALID")


def _request_timeout_seconds(env: Mapping[str, str]) -> int:
    raw = (env.get("BOSS_HARNESS_MODEL_REQUEST_TIMEOUT_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS
    try:
        seconds = int(raw)
    except ValueError:
        raise ModelConfigError("MODEL_REQUEST_TIMEOUT_INVALID") from None
    if not 1 <= seconds <= MAX_MODEL_REQUEST_TIMEOUT_SECONDS:
        raise ModelConfigError("MODEL_REQUEST_TIMEOUT_INVALID")
    return seconds


def _max_tokens(env: Mapping[str, str]) -> int:
    """未设置或为空用默认值；其余须为正整数，错误不带原始取值。"""
    raw = env.get("BOSS_HARNESS_MAX_TOKENS")
    if not raw:
        return DEFAULT_MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        raise ModelConfigError("MODEL_MAX_TOKENS_INVALID") from None
    if value <= 0:
        raise ModelConfigError("MODEL_MAX_TOKENS_INVALID")
    return value


def build_provider(config: ModelConfig) -> Provider | None:
    """按配置构造 provider；`none` 返回 None，由调用方走确定性路径。"""
    if config.provider == "none":
        return None
    if config.provider == "openai":
        from boss_harness.models.openai_responses import OpenAIResponsesProvider

        return OpenAIResponsesProvider(config)
    from boss_harness.models.anthropic_provider import AnthropicProvider

    return AnthropicProvider(config)
