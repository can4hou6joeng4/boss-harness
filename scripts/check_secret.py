#!/usr/bin/env python3
"""核对凭据包装与错误文本脱敏的结构性边界。

secret.py 是凭据进入日志、错误文本与导出的最后一道网：`Secret` 的 repr / str 固定
输出占位符且对象不可 JSON 序列化，`redact_secrets` 先按已知原值替换，再按三种
凭据形态抹除并保留可读的键名与分隔符。这里同时直接调用两个入口核对替换结果，
任一放宽都会让明文进入会话记录或诊断。
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/secret.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.secret import Secret, redact_secrets  # noqa: E402

PATTERN_FRAGMENTS = (
    "_PATTERNS = (",
    r're.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{6,}"),',
    r're.compile(r"\bsk-[A-Za-z0-9._\-]{6,}"),',
    r're.compile(r"(?i)\b(api[_-]?key|auth[_-]?token|access[_-]?token|token|secret|password)\b"',
    r'''r"([\"']?\s*[:=]\s*[\"']?)([A-Za-z0-9._\-]{6,})"),''',
    '_REDACTED = "<redacted>"',
)
SECRET_FRAGMENTS = (
    "class Secret:",
    '__slots__ = ("_value",)',
    "def __init__(self, value: str) -> None:",
    "def get(self) -> str:",
    "return self._value",
    "def __bool__(self) -> bool:",
    "return bool(self._value)",
    "def __repr__(self) -> str:",
    "return _REDACTED",
    "__str__ = __repr__",
)
REDACT_FRAGMENTS = (
    "def redact_secrets(text: str, extra: tuple[str, ...] = ()) -> str:",
    "if not text:",
    "return text",
    "for candidate in extra:",
    "if candidate and len(candidate) >= 6:",
    "out = out.replace(candidate, _REDACTED)",
    'out = _PATTERNS[0].sub(f"Bearer {_REDACTED}", out)',
    "out = _PATTERNS[1].sub(_REDACTED, out)",
    'out = _PATTERNS[2].sub(lambda match: f"{match.group(1)}{match.group(2)}{_REDACTED}", out)',
    "return out",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "凭据以 `Secret` 包装：`repr` / `str` 固定输出 `<redacted>`"),
    (TECHNICAL_REFERENCE, "`redact_secrets` 先按调用方给出的原值替换（长度至少 6），再依次抹掉 Bearer 令牌、`sk-` 密钥与 key/token/secret/password 赋值形式"),
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
        raise ValueError(
            f"凭据脱敏行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_raises(call, error_type, label: str) -> int:
    try:
        call()
    except error_type:
        return 1
    raise ValueError(f"凭据脱敏行为变化 {label}：期望 {error_type.__name__}")


def _behavior_checks() -> int:
    mark = "<redacted>"
    # 运行时拼出测试用键名与值，避免仓库里出现可被密钥扫描误判的完整凭据字面量。
    value = "abc" + "defgh"
    api_key = "api" + "_key"
    token_key = "to" + "ken"
    password_key = "pass" + "word"
    access_key = "access" + "_token"
    auth_key = "auth" + "-token"
    secret_key = "sec" + "ret"
    checked = _expect_value(redact_secrets(""), "", "空文本")
    checked += _expect_value(redact_secrets(None), None, "空值")
    checked += _expect_value(redact_secrets("plain text"), "plain text", "纯文本")
    checked += _expect_value(
        redact_secrets(f"known {value}", extra=(value,)), f"known {mark}", "已知原值")
    checked += _expect_value(
        redact_secrets(value, extra=("abcd" + "e",)), value, "短原值忽略")
    checked += _expect_value(
        redact_secrets(value, extra=("",)), value, "空原值忽略")
    checked += _expect_value(
        redact_secrets(f"{value} {value}", extra=(value,)), f"{mark} {mark}",
        "多次原值替换")

    checked += _expect_value(
        redact_secrets(f"Authorization: Bearer {value}"),
        f"Authorization: Bearer {mark}", "Bearer 头")
    checked += _expect_value(
        redact_secrets(f"bearer {value}"), f"Bearer {mark}", "Bearer 大小写")
    checked += _expect_value(
        redact_secrets(f"Bearer {'abc' + '12'}"), f"Bearer {'abc' + '12'}",
        "Bearer 长度下限")
    checked += _expect_value(
        redact_secrets(f"key sk-{value}"), f"key {mark}", "sk 前缀")
    checked += _expect_value(
        redact_secrets("sk-" + "abc"), "sk-" + "abc", "sk 长度下限")

    checked += _expect_value(
        redact_secrets(f"{api_key}={value}"), f"{api_key}={mark}", "api_key 赋值")
    checked += _expect_value(
        redact_secrets(f"{token_key}: {value}"), f"{token_key}: {mark}", "token 冒号")
    checked += _expect_value(
        redact_secrets(f'{password_key}="{value}"'), f'{password_key}="{mark}"',
        "引号赋值")
    checked += _expect_value(
        redact_secrets(f"{access_key}={value}"), f"{access_key}={mark}", "access_token")
    checked += _expect_value(
        redact_secrets(f"{auth_key} = {value}"), f"{auth_key} = {mark}", "auth-token")
    checked += _expect_value(
        redact_secrets(f"{secret_key}={value}"), f"{secret_key}={mark}", "secret 赋值")
    checked += _expect_value(
        redact_secrets(f"{token_key}={'abc'}"), f"{token_key}={'abc'}", "赋值长度下限")
    checked += _expect_value(
        redact_secrets(f"Bearer {value} sk-{value} {token_key}={value}"),
        f"Bearer {mark} {mark} {token_key}={mark}", "组合文本")

    secret = Secret("value-123")
    checked += _expect_value(secret.get(), "value-123", "取值")
    checked += _expect_value(bool(secret), True, "非空布尔")
    checked += _expect_value(bool(Secret("")), False, "空布尔")
    checked += _expect_value(
        (str(secret), repr(secret)), (mark, mark), "占位符")
    checked += _expect_value(
        "value-123" in (str(secret) + repr(secret)), False, "明文不出现")
    checked += _expect_raises(lambda: json.dumps(secret), TypeError, "不可 JSON 序列化")
    checked += _expect_value(hasattr(secret, "__dict__"), False, "仅槽位")
    checked += _expect_raises(
        lambda: setattr(secret, "other", "x"), AttributeError, "拒绝额外属性")
    return checked


def check_secret() -> int:
    module = _read(MODULE)
    checked = _expect(PATTERN_FRAGMENTS, module, MODULE)
    checked += _expect(SECRET_FRAGMENTS, module, MODULE)
    checked += _expect(REDACT_FRAGMENTS, module, MODULE)
    # 脱敏顺序：空值短路 → 已知原值 → Bearer → sk- → 赋值形式。
    checked += _ordered(
        (
            "if not text:",
            "for candidate in extra:",
            'out = _PATTERNS[0].sub(f"Bearer {_REDACTED}", out)',
            "out = _PATTERNS[1].sub(_REDACTED, out)",
            "out = _PATTERNS[2].sub(lambda match:",
            "return out",
        ),
        module,
        MODULE,
    )
    # 结构性保证：非 dataclass、仅一个槽位、repr 与 str 共用占位符。
    if "@dataclass" in module:
        raise ValueError(f"{MODULE} 的 Secret 不得使用 dataclass")
    if module.count("re.compile(") != 3:
        raise ValueError(f"{MODULE} 的凭据形态必须恰为三种")
    if 'return self._value' in module.split("def __repr__", 1)[1]:
        raise ValueError(f"{MODULE} 的 repr 不得返回明文")
    if "len(candidate) >= 6" not in module:
        raise ValueError(f"{MODULE} 的原值替换必须有长度下限")
    if '<redacted>' not in module:
        raise ValueError(f"{MODULE} 必须保留固定占位符")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_secret()
    except ValueError as error:
        print(f"凭据脱敏核对失败，{error}", file=sys.stderr)
        return 2
    print(f"凭据脱敏一致：{checked} 项包装、形态、顺序防护与行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
