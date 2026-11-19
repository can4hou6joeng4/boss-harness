#!/usr/bin/env python3
"""核对 Codex 配置文件路径、严格错误与 profile 解析边界。

codex_config.py 只读本地 `~/.codex/config.toml`：路径按显式入参、环境覆盖与
CODEX_HOME 依次选择，strict 只让实际需要的文件错误明确失败，TOML 诊断不夹带
配置原文；profile 只接受 Responses 协议，凭据用 Secret 包装且只记录 env_key 名称。
任一放宽都会让凭据或配置原文进入诊断，或让不支持的协议静默上线，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/codex_config.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    return checked + 1


def main() -> int:
    try:
        checked = check_codex_config()
    except ValueError as error:
        print(f"Codex 配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"Codex 配置一致：{checked} 项路径、严格错误与 profile 防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
