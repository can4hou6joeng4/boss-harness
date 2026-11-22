#!/usr/bin/env python3
"""核对模型端点判定、请求时限、输出上限与凭据解析的配置边界。

`_is_first_party_base_url` 决定 Anthropic 端点是否按官方主机处理：主机名必须精确
比较，大小写、尾根点、端口与路径不影响结果，前缀伪装、userinfo 与畸形 IPv6 不得
误判为官方。`_server_side_fallback` 解析 `BOSS_HARNESS_SERVER_FALLBACK`：未设置取
默认，空白视为关闭，只接受固定开关写法，未知取值在严格模式失败且不回显原文。
`_request_timeout_seconds` 与 `_max_tokens` 把空白视为未设置，按整数解析并收敛到
固定错误码；`_configured_model`、`_has_configured_value` 与 `has_anthropic_credential`
让纯空白占位值不遮蔽后续变量。`resolve_config` 按显式参数 > `BOSS_HARNESS_PROVIDER` >
凭据自动选择的顺序解析线路，模型按命令行 > 通用变量 > 线路专属变量 > 默认取值；
`_openai_config` 只在缺项时读取 Codex 文件，缺端点与缺凭据返回固定错误码。这里静态固定
解析分支，并直接调用这些函数核对边界。不访问网络或模型。
"""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/provider.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.config_errors import ModelConfigError  # noqa: E402
from boss_harness.models.provider import (  # noqa: E402
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS,
    MAX_MODEL_REQUEST_TIMEOUT_SECONDS,
    _EXPLICIT_PROVIDERS,
    _FIRST_PARTY_HOST,
    _SWITCH_OFF,
    _SWITCH_ON,
    _configured_model,
    _has_configured_value,
    _is_first_party_base_url,
    _max_tokens,
    _openai_config,
    _request_timeout_seconds,
    _server_side_fallback,
    has_anthropic_credential,
    resolve_config,
)

HOST_FRAGMENTS = (
    '_FIRST_PARTY_HOST = "api.anthropic.com"',
    "if base_url is None or not base_url.strip():",
    "candidate = base_url.strip()",
    'if "://" not in candidate:\n        candidate = f"//{candidate}"',
    'host = (urlparse(candidate).hostname or "").rstrip(".")',
    "except ValueError:",
    "return host == _FIRST_PARTY_HOST",
)
SWITCH_FRAGMENTS = (
    '_SWITCH_ON = frozenset({"1", "true", "yes", "on"})',
    '_SWITCH_OFF = frozenset({"0", "false", "no", "off"})',
    'raw = env.get("BOSS_HARNESS_SERVER_FALLBACK")',
    "if raw is None:\n        return default",
    "value = raw.strip().lower()",
    "if not value or value in _SWITCH_OFF:",
    "if value in _SWITCH_ON:",
    "if not strict:\n        return default",
    'raise ModelConfigError("MODEL_SERVER_FALLBACK_INVALID")',
)
TIMEOUT_FRAGMENTS = (
    'raw = (env.get("BOSS_HARNESS_MODEL_REQUEST_TIMEOUT_SECONDS") or "").strip()',
    "if not raw:\n        return DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS",
    'except ValueError:\n        raise ModelConfigError("MODEL_REQUEST_TIMEOUT_INVALID") from None',
    'if not 1 <= seconds <= MAX_MODEL_REQUEST_TIMEOUT_SECONDS:\n'
    '        raise ModelConfigError("MODEL_REQUEST_TIMEOUT_INVALID")',
)
TOKENS_FRAGMENTS = (
    'raw = (env.get("BOSS_HARNESS_MAX_TOKENS") or "").strip()',
    "if not raw:\n        return DEFAULT_MAX_TOKENS",
    'except ValueError:\n        raise ModelConfigError("MODEL_MAX_TOKENS_INVALID") from None',
    'if value <= 0:\n        raise ModelConfigError("MODEL_MAX_TOKENS_INVALID")',
)
MODEL_HELPER_FRAGMENTS = (
    'value = (env.get(name) or "").strip()',
    "if value:\n            return value",
    'return any((env.get(name) or "").strip() for name in names)',
    'return _has_configured_value(env, "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")',
)
PROVIDER_FRAGMENTS = (
    'if override:\n        env["BOSS_HARNESS_MODEL"] = override',
    'requested = (\n        provider if provider is not None else env.get("BOSS_HARNESS_PROVIDER") or ""\n    ).strip().lower()',
    'if requested == "codex":\n        requested = "openai"',
    'if requested == "auto":\n        requested = ""',
    "if requested and requested not in _EXPLICIT_PROVIDERS:",
    'raise ModelConfigError("MODEL_PROVIDER_UNKNOWN")',
    'resolved = "anthropic" if has_anthropic_credential(env) else "none"',
    'model=_configured_model(env, "BOSS_HARNESS_MODEL", "BOSS_HARNESS_ANTHROPIC_MODEL") '
    "or DEFAULT_MODEL",
    "return _openai_config(env)",
)
OPENAI_FRAGMENTS = (
    'explicit_model = _configured_model(env, "BOSS_HARNESS_MODEL", "BOSS_HARNESS_OPENAI_MODEL")',
    "profile = None if all((explicit_model, explicit_url, explicit_key)) "
    "else load_profile(environ=env, strict=True)",
    "if not file_key and profile and profile.env_key:",
    'if not base_url:\n        raise ModelConfigError("MODEL_ENDPOINT_MISSING")',
    'if not raw_key:\n        raise ModelConfigError("MODEL_CREDENTIAL_MISSING")',
    "api_key=Secret(raw_key)",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型配置边界变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_code(call, code: str, label: str, *, absent: str | None = None) -> int:
    try:
        call()
    except ModelConfigError as error:
        if error.code != code:
            raise ValueError(f"{label}：错误码 {error.code!r}，期望 {code!r}") from None
        if absent is not None and absent in str(error):
            raise ValueError(f"{label}：错误文案回显了原始取值") from None
        return 1
    raise ValueError(f"{label}：未抛出 ModelConfigError")


def _expect_error(call, label: str) -> int:
    return _expect_code(call, "MODEL_SERVER_FALLBACK_INVALID", label,
                        absent="mystery-value-9")


def _behavior_checks() -> int:
    checked = _expect_value(_FIRST_PARTY_HOST, "api.anthropic.com", "官方主机常量")
    # 端点判定：空白与官方写法为真；主机名精确比较，大小写与尾点归一，端口与路径忽略。
    for value in (None, "", "   ", "https://api.anthropic.com", "https://API.ANTHROPIC.COM",
                  "https://api.anthropic.com.", "https://API.ANTHROPIC.COM.",
                  "https://api.anthropic.com:8443/v1", "api.anthropic.com",
                  "http://api.anthropic.com/v1", " https://api.anthropic.com "):
        checked += _expect_value(_is_first_party_base_url(value), True, f"官方端点 {value!r}")
    for value in ("https://api.anthropic.com.evil.example",
                  "https://api.anthropic.com@proxy.example",
                  "https://evil.example/api.anthropic.com",
                  "https://[::1", "https://[::1]", "https://evil.example"):
        checked += _expect_value(_is_first_party_base_url(value), False, f"非官方端点 {value!r}")
    # 回退开关：未设置取默认；空白与关闭写法为关闭；开启写法为开启。
    checked += _expect_value((_server_side_fallback({}, True, strict=True),
                              _server_side_fallback({}, False, strict=True)),
                             (True, False), "未设置取默认")
    for raw in ("", "  ", "off", " OFF ", "0", "no", "false"):
        checked += _expect_value(
            _server_side_fallback({"BOSS_HARNESS_SERVER_FALLBACK": raw}, True, strict=True),
            False, f"关闭写法 {raw!r}")
    for raw in ("1", "TRUE", "Yes", "on", "  On  "):
        checked += _expect_value(
            _server_side_fallback({"BOSS_HARNESS_SERVER_FALLBACK": raw}, False, strict=True),
            True, f"开启写法 {raw!r}")
    # 未知取值：严格模式失败且不回显原文；非严格模式回退默认。
    checked += _expect_error(
        lambda: _server_side_fallback(
            {"BOSS_HARNESS_SERVER_FALLBACK": "mystery-value-9"}, True, strict=True),
        "未知取值严格失败")
    checked += _expect_value(
        (_server_side_fallback({"BOSS_HARNESS_SERVER_FALLBACK": "mystery-value-9"}, True,
                               strict=False),
         _server_side_fallback({"BOSS_HARNESS_SERVER_FALLBACK": "mystery-value-9"}, False,
                               strict=False)),
        (True, False), "未知取值回退默认")
    checked += _expect_value((frozenset(_SWITCH_ON), frozenset(_SWITCH_OFF)),
                             (frozenset({"1", "true", "yes", "on"}),
                              frozenset({"0", "false", "no", "off"})), "开关集合")
    return checked


def _model_env_checks() -> int:
    checked = _expect_value((DEFAULT_MAX_TOKENS, DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS,
                             MAX_MODEL_REQUEST_TIMEOUT_SECONDS),
                            (64000, 600, 3600), "默认预算常量")
    # 请求时限：未设置与纯空白取默认，去掉首尾空白后按整数解析，1 与 3600 都在界内。
    timeout_name = "BOSS_HARNESS_MODEL_REQUEST_TIMEOUT_SECONDS"
    checked += _expect_value(_request_timeout_seconds({}),
                             DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS, "时限缺省")
    for raw in ("", "   "):
        checked += _expect_value(_request_timeout_seconds({timeout_name: raw}),
                                 DEFAULT_MODEL_REQUEST_TIMEOUT_SECONDS, f"时限空白 {raw!r}")
    checked += _expect_value((_request_timeout_seconds({timeout_name: " 30 "}),
                              _request_timeout_seconds({timeout_name: "1"}),
                              _request_timeout_seconds({timeout_name: "3600"}),
                              _request_timeout_seconds({timeout_name: " 600 "})),
                             (30, 1, 3600, 600), "时限取值")
    for raw, absent in (("0", None), ("3601", "3601"), ("-5", "-5"), ("soon", "soon")):
        checked += _expect_code(
            lambda raw=raw: _request_timeout_seconds({timeout_name: raw}),
            "MODEL_REQUEST_TIMEOUT_INVALID", f"时限非法 {raw!r}", absent=absent)
    # 输出上限：未设置与纯空白取默认，去掉首尾空白后按正整数解析，错误不回显原文。
    tokens_name = "BOSS_HARNESS_MAX_TOKENS"
    checked += _expect_value(_max_tokens({}), DEFAULT_MAX_TOKENS, "上限缺省")
    for raw in ("", "  "):
        checked += _expect_value(_max_tokens({tokens_name: raw}),
                                 DEFAULT_MAX_TOKENS, f"上限空白 {raw!r}")
    checked += _expect_value((_max_tokens({tokens_name: " 1 "}),
                              _max_tokens({tokens_name: "128000"})),
                             (1, 128000), "上限取值")
    for raw, absent in (("0", None), ("-1", "-1"), ("lots", "lots")):
        checked += _expect_code(
            lambda raw=raw: _max_tokens({tokens_name: raw}),
            "MODEL_MAX_TOKENS_INVALID", f"上限非法 {raw!r}", absent=absent)
    # 模型变量：按顺序取第一个去空白后非空的值；纯空白不遮蔽后续变量。
    checked += _expect_value((_configured_model({}, "A"), _configured_model({"A": "  "}, "A")),
                             ("", ""), "模型变量缺省")
    checked += _expect_value(_configured_model({"A": "  ", "B": " model-b "}, "A", "B"),
                             "model-b", "模型变量跳过空白")
    checked += _expect_value(_configured_model({"A": "model-a", "B": "model-b"}, "A", "B"),
                             "model-a", "模型变量优先级")
    checked += _expect_value((_has_configured_value({}, "A", "B"),
                              _has_configured_value({"A": " ", "B": ""}, "A", "B"),
                              _has_configured_value({"A": " ", "B": "x"}, "A", "B")),
                             (False, False, True), "凭据存在判定")
    # Anthropic 凭据：两项去空白后任一非空即可；空键占位不遮蔽令牌。
    checked += _expect_value(has_anthropic_credential({}), False, "Anthropic 凭据缺省")
    checked += _expect_value((has_anthropic_credential({"ANTHROPIC_API_KEY": "k"}),
                              has_anthropic_credential({"ANTHROPIC_AUTH_TOKEN": "t"})),
                             (True, True), "Anthropic 单项凭据")
    checked += _expect_value(has_anthropic_credential(
        {"ANTHROPIC_API_KEY": "  ", "ANTHROPIC_AUTH_TOKEN": "t"}), True, "空键不遮蔽令牌")
    checked += _expect_value(has_anthropic_credential(
        {"ANTHROPIC_API_KEY": "  ", "ANTHROPIC_AUTH_TOKEN": " "}), False, "Anthropic 全空白")
    return checked


def _resolve_checks() -> int:
    checked = _expect_value(sorted(_EXPLICIT_PROVIDERS),
                            ["anthropic", "codex", "none", "openai"], "显式线路集合")
    anthropic_env = {"ANTHROPIC_API_KEY": "sk-test"}
    # 线路优先级：显式参数 > 环境变量 > 按凭据自动选择；空白凭据不算已配置。
    checked += _expect_value(
        resolve_config({**anthropic_env, "BOSS_HARNESS_PROVIDER": "anthropic"}, "none").provider,
        "none", "显式参数优先")
    checked += _expect_value(
        resolve_config({**anthropic_env, "BOSS_HARNESS_PROVIDER": "none"}).provider,
        "none", "环境变量线路")
    checked += _expect_value(resolve_config(anthropic_env).provider, "anthropic", "凭据自动选择")
    checked += _expect_value((resolve_config({}).provider,
                              resolve_config({"ANTHROPIC_API_KEY": "  ",
                                              "ANTHROPIC_AUTH_TOKEN": ""}).provider),
                             ("none", "none"), "无凭据退回 none")
    checked += _expect_value(resolve_config({"BOSS_HARNESS_PROVIDER": "auto"}).provider,
                             "none", "auto 按自动选择")
    openai_env = {
        "BOSS_HARNESS_MODEL": "gpt-x",
        "BOSS_HARNESS_OPENAI_BASE_URL": "https://openai.example/v1",
        "BOSS_HARNESS_OPENAI_API_KEY": "sk-openai-9",
    }
    codex_config = resolve_config({**openai_env, "BOSS_HARNESS_PROVIDER": "codex"})
    checked += _expect_value((codex_config.provider, codex_config.base_url),
                             ("openai", "https://openai.example/v1"), "codex 别名")
    checked += _expect_code(lambda: resolve_config({"BOSS_HARNESS_PROVIDER": "bogus-line"}),
                            "MODEL_PROVIDER_UNKNOWN", "未知线路", absent="bogus-line")
    # 模型覆盖顺序：命令行 > 通用环境变量 > 线路专属变量 > 默认。
    checked += _expect_value(
        resolve_config(anthropic_env, model_override="cmd-model").model,
        "cmd-model", "命令行模型优先")
    checked += _expect_value(
        resolve_config({**anthropic_env, "BOSS_HARNESS_MODEL": "env-model",
                        "BOSS_HARNESS_ANTHROPIC_MODEL": "line-model"}).model,
        "env-model", "通用模型变量")
    checked += _expect_value(
        resolve_config({**anthropic_env, "BOSS_HARNESS_ANTHROPIC_MODEL": " line-model "}).model,
        "line-model", "线路专属模型变量")
    checked += _expect_value(resolve_config(anthropic_env).model, DEFAULT_MODEL, "模型默认值")
    # Anthropic 线路：端点去空白，思考开关与回退开关按线路严格性生效。
    config = resolve_config({**anthropic_env, "ANTHROPIC_BASE_URL": " https://proxy.example/v1 ",
                             "BOSS_HARNESS_THINKING": "summarized",
                             "BOSS_HARNESS_SERVER_FALLBACK": " 0 "})
    checked += _expect_value(
        (config.base_url, config.thinking, config.server_side_fallback),
        ("https://proxy.example/v1", {"type": "adaptive", "display": "summarized"}, False),
        "Anthropic 线路字段")
    checked += _expect_value(resolve_config(anthropic_env).server_side_fallback,
                             True, "官方端点回退默认")
    checked += _expect_value(
        resolve_config({"BOSS_HARNESS_PROVIDER": "none",
                        "BOSS_HARNESS_SERVER_FALLBACK": "mystery"}).server_side_fallback,
        True, "none 线路不因开关失败")
    checked += _expect_code(
        lambda: resolve_config({**anthropic_env, "BOSS_HARNESS_SERVER_FALLBACK": "mystery"}),
        "MODEL_SERVER_FALLBACK_INVALID", "anthropic 线路严格失败")
    # OpenAI：完整显式配置跳过 Codex 文件；缺项时缺失文件按未配置处理。
    with TemporaryDirectory() as directory:
        full = {**openai_env, "BOSS_HARNESS_CODEX_CONFIG": directory}
        openai_config = resolve_config(full, "openai")
        checked += _expect_value(
            (openai_config.provider, openai_config.model, openai_config.api_key.get(),
             "sk-openai-9" in repr(openai_config)),
            ("openai", "gpt-x", "sk-openai-9", False), "OpenAI 完整显式配置")
        missing = {"BOSS_HARNESS_CODEX_CONFIG": str(Path(directory) / "missing.toml")}
        checked += _expect_code(lambda: resolve_config(missing, "openai"),
                                "MODEL_ENDPOINT_MISSING", "OpenAI 缺端点")
        checked += _expect_code(
            lambda: resolve_config({**missing,
                                    "BOSS_HARNESS_OPENAI_BASE_URL": "https://openai.example/v1"},
                                   "openai"),
            "MODEL_CREDENTIAL_MISSING", "OpenAI 缺凭据")
        default_model = resolve_config(
            {**missing, "BOSS_HARNESS_OPENAI_BASE_URL": "https://openai.example/v1",
             "BOSS_HARNESS_OPENAI_API_KEY": "sk-openai-9"}, "openai")
        checked += _expect_value(default_model.model, DEFAULT_MODEL, "OpenAI 模型默认值")
    return checked


def check_provider_config() -> int:
    module = _read(MODULE)
    checked = _expect(HOST_FRAGMENTS, module, MODULE)
    checked += _expect(SWITCH_FRAGMENTS, module, MODULE)
    checked += _expect(TIMEOUT_FRAGMENTS, module, MODULE)
    checked += _expect(TOKENS_FRAGMENTS, module, MODULE)
    checked += _expect(MODEL_HELPER_FRAGMENTS, module, MODULE)
    checked += _expect(PROVIDER_FRAGMENTS, module, MODULE)
    checked += _expect(OPENAI_FRAGMENTS, module, MODULE)
    checked += _behavior_checks()
    checked += _model_env_checks()
    checked += _resolve_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_provider_config()
    except ValueError as error:
        print(f"模型配置边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型配置边界一致：{checked} 项端点、回退、时限、上限、凭据与线路解析防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
