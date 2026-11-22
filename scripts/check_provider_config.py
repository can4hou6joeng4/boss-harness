#!/usr/bin/env python3
"""核对模型端点判定与服务端回退开关的配置边界。

`_is_first_party_base_url` 决定 Anthropic 端点是否按官方主机处理：主机名必须精确
比较，大小写、尾根点、端口与路径不影响结果，前缀伪装、userinfo 与畸形 IPv6 不得
误判为官方。`_server_side_fallback` 解析 `BOSS_HARNESS_SERVER_FALLBACK`：未设置取
默认，空白视为关闭，只接受固定开关写法，未知取值在严格模式失败且不回显原文。
这里静态固定归一化与开关分支，并直接调用两个函数核对边界。不访问网络或模型。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/provider.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.config_errors import ModelConfigError  # noqa: E402
from boss_harness.models.provider import (  # noqa: E402
    _FIRST_PARTY_HOST,
    _SWITCH_OFF,
    _SWITCH_ON,
    _is_first_party_base_url,
    _server_side_fallback,
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


def _expect_error(call, label: str) -> int:
    try:
        call()
    except ModelConfigError as error:
        if error.code != "MODEL_SERVER_FALLBACK_INVALID":
            raise ValueError(f"{label}：错误码 {error.code!r}") from None
        if "mystery-value-9" in str(error):
            raise ValueError(f"{label}：错误文案回显了原始取值") from None
        return 1
    raise ValueError(f"{label}：未抛出 ModelConfigError")


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


def check_provider_config() -> int:
    module = _read(MODULE)
    checked = _expect(HOST_FRAGMENTS, module, MODULE)
    checked += _expect(SWITCH_FRAGMENTS, module, MODULE)
    checked += _behavior_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_provider_config()
    except ValueError as error:
        print(f"模型配置边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型配置边界一致：{checked} 项端点判定与回退开关防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
