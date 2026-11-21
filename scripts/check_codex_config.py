#!/usr/bin/env python3
"""核对 Codex 配置文件路径、严格错误与 profile 解析边界。

codex_config.py 只读本地 `~/.codex/config.toml`：路径按显式入参、环境覆盖与
CODEX_HOME 依次选择，strict 只让实际需要的文件错误明确失败，TOML 诊断不夹带
配置原文；profile 只接受 Responses 协议，凭据用 Secret 包装且只记录 env_key 名称。
任一放宽都会让凭据或配置原文进入诊断，或让不支持的协议静默上线，因此既静态
固定关键片段，也直接调用路径、映射与读取函数核对结果和错误码。不访问网络、
模型或招聘平台。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/codex_config.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
import boss_harness.models.codex_config as codex_config  # noqa: E402
from boss_harness.models.codex_config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    config_path,
    load_profile,
    profile_from_mapping,
)
from boss_harness.models.config_errors import ModelConfigError  # noqa: E402

CONSTANT_FRAGMENTS = (
    'DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "config.toml"\n',
    "try:  # tomllib 自 Python 3.11 起进入标准库",
    "tomllib = None",
)
PROFILE_DATACLASS_FRAGMENTS = (
    "class CodexModelProfile:",
    "model: str",
    "base_url: str",
    'wire_api: str = "responses"',
    'provider_id: str = ""',
    "effort: str | None = None",
    "bearer_token: Secret | None = None",
    "env_key: str | None = None",
)
PATH_FRAGMENTS = (
    "def config_path(",
    "if explicit:",
    "return Path(explicit).expanduser()",
    'override = (env.get("BOSS_HARNESS_CODEX_CONFIG") or "").strip()',
    "return Path(override).expanduser()",
    'home = (env.get("CODEX_HOME") or "").strip()',
    'return Path(home).expanduser() / "config.toml"',
    "return DEFAULT_CONFIG_PATH",
)
LOAD_FRAGMENTS = (
    "def load_profile(",
    "target = config_path(path, environ)",
    "if not target.is_file():",
    'raise ModelConfigError("MODEL_CODEX_NOT_FILE")',
    "return None",
    "except OSError:",
    'raise ModelConfigError("MODEL_CODEX_UNREADABLE") from None',
    "if tomllib is None:  # 仅在 Python 3.10 上触发",
    'raise ModelConfigError("MODEL_CODEX_TOML_UNAVAILABLE")',
    'with target.open("rb") as handle:',
    "data = tomllib.load(handle)",
    "except tomllib.TOMLDecodeError:",
    'raise ModelConfigError("MODEL_CODEX_INVALID_TOML") from None',
    "return profile_from_mapping(data)",
)
MAPPING_FRAGMENTS = (
    "def profile_from_mapping(data: dict[str, Any]) -> CodexModelProfile | None:",
    'model = str(data.get("model") or "").strip()',
    'provider_id = str(data.get("model_provider") or "").strip()',
    'providers = data.get("model_providers")',
    "if isinstance(providers, dict) and provider_id:",
    "if isinstance(raw, dict):",
    'base_url = str(entry.get("base_url") or "").strip()',
    "if not model or not base_url:",
    'wire_api = entry.get("wire_api", "responses")',
    "if isinstance(wire_api, str):",
    'wire_api = wire_api.strip().lower() or "responses"',
    'if wire_api != "responses":',
    'raise ModelConfigError("MODEL_CODEX_WIRE_API_UNSUPPORTED")',
    'token = entry.get("experimental_bearer_token")',
    'env_key = str(entry.get("env_key") or "").strip() or None',
    'effort = str(data.get("model_reasoning_effort") or "").strip() or None',
    'provider_id=provider_id or str(entry.get("name") or ""),',
    "bearer_token=Secret(str(token).strip()) if token else None,",
)
DOC_FRAGMENTS = (
    (USER_GUIDE, "按此顺序选择文件，显式字段仍优先"),
    (USER_GUIDE, "profile 的 `wire_api` 缺省或为空白时使用 `responses`，显式值忽略首尾空白并按不区分大小写处理"),
    (USER_GUIDE, "配置解析只读本地文件，不探测真实服务"),
    (TECHNICAL_REFERENCE, "可用 Codex profile 的 `wire_api` 仅接受 `responses`，忽略大小写与首尾空白"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"Codex 配置行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, code: str, label: str) -> int:
    try:
        call()
    except ModelConfigError as error:
        if error.code != code:
            raise ValueError(
                f"Codex 配置行为变化 {label}：期望错误 {code!r}，实际 {error.code!r}")
        return 1
    raise ValueError(f"Codex 配置行为变化 {label}：期望 ModelConfigError")


def _expect_raises(call, error_type, label: str) -> int:
    try:
        call()
    except error_type:
        return 1
    raise ValueError(f"Codex 配置行为变化 {label}：期望 {error_type.__name__}")


def _error_text(call) -> str:
    try:
        call()
    except ModelConfigError as error:
        return str(error)
    raise ValueError("Codex 配置行为变化：期望 ModelConfigError")


def _mapping(**entry) -> dict:
    return {"model": "m", "model_provider": "p", "model_providers": {"p": entry}}


def _without_process_override(expected: Path, label: str) -> int:
    name = "BOSS_HARNESS_CODEX_CONFIG"
    previous = os.environ.get(name)
    try:
        os.environ[name] = "/tmp/harness-ignored.toml"
        actual = config_path(None, {})
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
    return _expect_value(actual, expected, label)


def _behavior_checks() -> int:
    checked = 0

    checked += _expect_value(
        config_path("~/cfg.toml", {}), Path("~/cfg.toml").expanduser(), "显式路径")
    checked += _expect_value(
        config_path(Path("/tmp/explicit.toml"), {}), Path("/tmp/explicit.toml"),
        "显式路径对象")
    checked += _expect_value(
        config_path("", {"BOSS_HARNESS_CODEX_CONFIG": "/tmp/a.toml"}),
        Path("/tmp/a.toml"), "显式空串回退")
    checked += _expect_value(
        config_path(None, {"BOSS_HARNESS_CODEX_CONFIG": " /tmp/b.toml "}),
        Path("/tmp/b.toml"), "环境覆盖去空白")
    checked += _expect_value(
        config_path(None, {"BOSS_HARNESS_CODEX_CONFIG": "  ", "CODEX_HOME": "/tmp/home"}),
        Path("/tmp/home/config.toml"), "覆盖空白回退")
    checked += _expect_value(
        config_path(None, {"CODEX_HOME": " /tmp/home "}),
        Path("/tmp/home/config.toml"), "CODEX_HOME 去空白")
    checked += _expect_value(
        config_path(None, {"BOSS_HARNESS_CODEX_CONFIG": "/tmp/a.toml",
                           "CODEX_HOME": "/tmp/home"}),
        Path("/tmp/a.toml"), "环境覆盖优先")
    checked += _expect_value(config_path(None, {}), DEFAULT_CONFIG_PATH, "默认路径")
    checked += _without_process_override(DEFAULT_CONFIG_PATH, "忽略进程环境")

    checked += _expect_value(profile_from_mapping({}), None, "空映射")
    checked += _expect_value(profile_from_mapping({"model": "m"}), None, "缺端点")
    checked += _expect_value(
        profile_from_mapping({"model": "m", "model_provider": "p"}), None, "缺 provider 表")
    checked += _expect_value(
        profile_from_mapping({"model": "m", "model_provider": "p",
                              "model_providers": []}), None, "provider 表类型")
    checked += _expect_value(
        profile_from_mapping({"model": "m", "model_provider": "p",
                              "model_providers": {"p": []}}), None, "provider 项类型")
    checked += _expect_value(
        profile_from_mapping({"model": "m", "model_provider": "p",
                              "model_providers": {"p": {"base_url": " "}}}), None,
        "端点空白")
    minimal = profile_from_mapping({
        "model": " m ", "model_provider": " p ",
        "model_providers": {"p": {"base_url": " https://x "}}})
    checked += _expect_value(
        (minimal.model, minimal.base_url, minimal.wire_api, minimal.provider_id,
         minimal.effort, minimal.bearer_token, minimal.env_key),
        ("m", "https://x", "responses", "p", None, None, None), "最小 profile")
    checked += _expect_value(
        profile_from_mapping(_mapping(base_url="https://x", wire_api=" RESPONSES ")).wire_api,
        "responses", "协议大小写归一")
    checked += _expect_value(
        profile_from_mapping(_mapping(base_url="https://x", wire_api="   ")).wire_api,
        "responses", "协议空白默认")
    checked += _expect_error(
        lambda: profile_from_mapping(_mapping(base_url="https://x", wire_api="chat")),
        "MODEL_CODEX_WIRE_API_UNSUPPORTED", "协议非法")
    checked += _expect_error(
        lambda: profile_from_mapping(_mapping(base_url="https://x", wire_api=None)),
        "MODEL_CODEX_WIRE_API_UNSUPPORTED", "协议空值")
    checked += _expect_error(
        lambda: profile_from_mapping(_mapping(base_url="https://x", wire_api=5)),
        "MODEL_CODEX_WIRE_API_UNSUPPORTED", "协议类型")
    checked += _expect_value(
        profile_from_mapping({**_mapping(base_url="https://x"),
                              "model_reasoning_effort": " high "}).effort,
        "high", "推理档位去空白")
    checked += _expect_value(
        profile_from_mapping({**_mapping(base_url="https://x"),
                              "model_reasoning_effort": "  "}).effort,
        None, "推理档位空白")
    checked += _expect_value(
        profile_from_mapping(_mapping(base_url="https://x", env_key=" CODEX_KEY ")).env_key,
        "CODEX_KEY", "环境变量名去空白")
    checked += _expect_value(
        profile_from_mapping(_mapping(base_url="https://x", env_key="  ")).env_key,
        None, "环境变量名空白")
    secured = profile_from_mapping(
        _mapping(base_url="https://x", experimental_bearer_token=" tok "))
    checked += _expect_value(
        (secured.bearer_token.get(), repr(secured.bearer_token), str(secured.bearer_token),
         bool(secured.bearer_token)),
        ("tok", "<redacted>", "<redacted>", True), "凭据包装")
    checked += _expect_value(
        profile_from_mapping(
            _mapping(base_url="https://x", experimental_bearer_token=123)).bearer_token.get(),
        "123", "凭据转字符串")
    checked += _expect_value(
        profile_from_mapping(_mapping(base_url="https://x",
                                      experimental_bearer_token=0)).bearer_token,
        None, "空凭据省略")
    checked += _expect_raises(lambda: json.dumps(asdict(secured)), TypeError, "凭据不可序列化")

    valid_toml = (
        'model = "gpt-5"\n'
        'model_provider = "p"\n'
        'model_reasoning_effort = " high "\n'
        '\n'
        '[model_providers.p]\n'
        'base_url = "https://example.test/v1"\n'
        'wire_api = "Responses"\n'
        'env_key = "CODEX_KEY"\n'
        'experimental_bearer_token = "secret-token"\n'
    )
    unsupported_toml = (
        'model = "gpt-5"\n'
        'model_provider = "p"\n'
        '\n'
        '[model_providers.p]\n'
        'base_url = "https://example.test/v1"\n'
        'wire_api = "chat"\n'
    )
    incomplete_toml = 'model = "gpt-5"\n'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        missing = root / "missing.toml"
        checked += _expect_value(load_profile(missing, {}, strict=False), None, "缺失文件")
        checked += _expect_value(load_profile(missing, {}, strict=True), None, "缺失文件严格")
        folder = root / "folder"
        folder.mkdir()
        checked += _expect_value(load_profile(folder, {}, strict=False), None, "目录非严格")
        checked += _expect_error(
            lambda: load_profile(folder, {}, strict=True), "MODEL_CODEX_NOT_FILE", "目录严格")
        invalid = root / "invalid.toml"
        invalid.write_text('model = "x"\n[broken\n', encoding="utf-8")
        checked += _expect_value(load_profile(invalid, {}, strict=False), None, "非法 TOML 非严格")
        checked += _expect_error(
            lambda: load_profile(invalid, {}, strict=True), "MODEL_CODEX_INVALID_TOML",
            "非法 TOML 严格")
        checked += _expect_value(
            "broken" in _error_text(lambda: load_profile(invalid, {}, strict=True)), False,
            "错误不回显原文")
        valid = root / "valid.toml"
        valid.write_text(valid_toml, encoding="utf-8")
        profile = load_profile(valid, {}, strict=True)
        checked += _expect_value(
            (profile.model, profile.base_url, profile.wire_api),
            ("gpt-5", "https://example.test/v1", "responses"), "有效文件")
        checked += _expect_value(
            (profile.effort, profile.env_key, profile.bearer_token.get()),
            ("high", "CODEX_KEY", "secret-token"), "有效字段")
        checked += _expect_value(
            load_profile(None, {"BOSS_HARNESS_CODEX_CONFIG": str(valid)}, strict=True).model,
            "gpt-5", "环境选择文件")
        checked += _expect_value(
            load_profile(missing, {"BOSS_HARNESS_CODEX_CONFIG": str(valid)},
                         strict=True),
            None, "显式优先于环境")
        unsupported = root / "unsupported.toml"
        unsupported.write_text(unsupported_toml, encoding="utf-8")
        checked += _expect_error(
            lambda: load_profile(unsupported, {}, strict=True),
            "MODEL_CODEX_WIRE_API_UNSUPPORTED", "文件协议拒绝")
        incomplete = root / "incomplete.toml"
        incomplete.write_text(incomplete_toml, encoding="utf-8")
        checked += _expect_value(
            load_profile(incomplete, {}, strict=True), None, "不完整文件")
        secret_invalid = root / "secret.toml"
        secret_invalid.write_text(
            'experimental_bearer_token = "sk-secret-value"\n[broken\n', encoding="utf-8")
        checked += _expect_value(
            "sk-secret-value" in _error_text(
                lambda: load_profile(secret_invalid, {}, strict=True)), False,
            "错误不回显凭据")
        original_tomllib = codex_config.tomllib
        codex_config.tomllib = None
        try:
            checked += _expect_error(
                lambda: load_profile(valid, {}, strict=True),
                "MODEL_CODEX_TOML_UNAVAILABLE", "解析器不可用")
        finally:
            codex_config.tomllib = original_tomllib
    return checked


def check_codex_config() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(PROFILE_DATACLASS_FRAGMENTS, module, MODULE)
    checked += _expect(PATH_FRAGMENTS, module, MODULE)
    checked += _expect(LOAD_FRAGMENTS, module, MODULE)
    checked += _expect(MAPPING_FRAGMENTS, module, MODULE)
    # 路径优先级：显式入参 → 环境覆盖 → CODEX_HOME → 默认路径。
    checked += _ordered(
        (
            "if explicit:",
            'override = (env.get("BOSS_HARNESS_CODEX_CONFIG") or "").strip()',
            'home = (env.get("CODEX_HOME") or "").strip()',
            "return DEFAULT_CONFIG_PATH",
        ),
        module,
        MODULE,
    )
    # 读取：普通文件判定 → 严格错误 → 解析器可用 → 二进制读取 → 解码错误 → profile。
    checked += _ordered(
        (
            "if not target.is_file():",
            'raise ModelConfigError("MODEL_CODEX_UNREADABLE") from None',
            "if tomllib is None:",
            'with target.open("rb") as handle:',
            "except tomllib.TOMLDecodeError:",
            "return profile_from_mapping(data)",
        ),
        module,
        MODULE,
    )
    # profile：模型与 provider → 端点 → 协议归一化 → 凭据与档位。
    checked += _ordered(
        (
            'provider_id = str(data.get("model_provider") or "").strip()',
            'base_url = str(entry.get("base_url") or "").strip()',
            'wire_api = wire_api.strip().lower() or "responses"',
            "bearer_token=Secret(str(token).strip()) if token else None,",
        ),
        module,
        MODULE,
    )
    # 反向断言：只读、不写入、不回显解析器原文、凭据必须包装。
    if 'target.open("r"' in module:
        raise ValueError(f"{MODULE} 的配置读取必须是二进制模式")
    if (".write(" in module or "write_text(" in module or "write_bytes(" in module
            or 'open("w' in module):
        raise ValueError(f"{MODULE} 不得写入配置")
    if "str(exc)" in module or "{data}" in module:
        raise ValueError(f"{MODULE} 的错误不得包含配置原文")
    if "bearer_token=token" in module:
        raise ValueError(f"{MODULE} 的凭据必须用 Secret 包装")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_codex_config()
    except (ValueError, OSError) as error:
        print(f"Codex 配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"Codex 配置一致：{checked} 项结构、行为与 profile 校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
