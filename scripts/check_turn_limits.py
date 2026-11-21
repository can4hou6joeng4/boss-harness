#!/usr/bin/env python3
"""核对回合模型请求上限的严格整数与有界解析。

turn_limits.py 决定宿主上限与单回合收紧：只接受真正的整数，环境变量先去空白、
再按十进制文本长度与形态判定，错误不回显原值。任一放宽都会让布尔值、字符串或
超长配置进入回合，因此既静态固定关键片段，也直接调用两个解析函数核对边界与
错误文案。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/turn_limits.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.turn_limits import (  # noqa: E402
    DEFAULT_MAX_MODEL_REQUESTS,
    MAX_MODEL_REQUESTS,
    model_request_limit,
    model_request_limit_from_environment,
)

CONSTANT_FRAGMENTS = (
    "DEFAULT_MAX_MODEL_REQUESTS = 6\n",
    "MAX_MODEL_REQUESTS = 64\n",
)
LIMIT_FRAGMENTS = (
    "def model_request_limit(value: object, *, ceiling: int = MAX_MODEL_REQUESTS) -> int:",
    # 布尔值在 Python 里是 int 子类：必须按精确类型拒绝。
    "if type(value) is not int or not 1 <= value <= ceiling:",
    'raise ValueError(f"maxModelRequests 必须是 1 到 {ceiling} 的整数")',
    "return value",
)
ENVIRONMENT_FRAGMENTS = (
    'raw = os.environ.get("BOSS_HARNESS_MAX_MODEL_REQUESTS")',
    # 空值或只有空白按未设置处理；首尾空白不影响合法数字。
    'value = "" if raw is None else raw.strip()',
    "if not value:",
    "return DEFAULT_MAX_MODEL_REQUESTS",
    # 先按文本长度与形态设限，再转换；错误不得包含原值。
    "if len(value) > 2 or re.fullmatch(r\"[1-9][0-9]?\", value) is None:",
    'raise ValueError("BOSS_HARNESS_MAX_MODEL_REQUESTS 必须是 1 到 64 的十进制整数")',
    "return model_request_limit(int(value))",
    "except ValueError:",
    'raise ValueError("BOSS_HARNESS_MAX_MODEL_REQUESTS 必须是 1 到 64 的十进制整数") from None',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "每回合默认最多 6 次业务模型请求；启动环境变量 `BOSS_HARNESS_MAX_MODEL_REQUESTS` 去除首尾空白后可设为 1–64 的十进制整数，空值或只有空白时使用默认上限。"),
    (USER_GUIDE, "`BOSS_HARNESS_MAX_MODEL_REQUESTS` 去除首尾空白后须为 1 到 64 的十进制整数；空值或只有空白时使用默认值。"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"回合请求上限行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"回合请求上限行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}")
        return 1
    raise ValueError(f"回合请求上限行为变化 {label}：期望 ValueError")


def _environment_check(raw, expected, label: str) -> int:
    name = "BOSS_HARNESS_MAX_MODEL_REQUESTS"
    previous = os.environ.get(name)
    try:
        if raw is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = raw
        try:
            actual = ("value", model_request_limit_from_environment())
        except ValueError as error:
            actual = ("error", str(error))
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
    return _expect_value(actual, expected, label)


def _behavior_checks() -> int:
    checked = 0
    message = f"maxModelRequests 必须是 1 到 {MAX_MODEL_REQUESTS} 的整数"
    environment_message = "BOSS_HARNESS_MAX_MODEL_REQUESTS 必须是 1 到 64 的十进制整数"

    checked += _expect_value(model_request_limit(1), 1, "下限")
    checked += _expect_value(
        model_request_limit(MAX_MODEL_REQUESTS), MAX_MODEL_REQUESTS, "上限")
    checked += _expect_value(model_request_limit(7), 7, "常规值")
    checked += _expect_value(model_request_limit(5, ceiling=5), 5, "自定义上限")
    checked += _expect_error(
        lambda: model_request_limit(6, ceiling=5),
        "maxModelRequests 必须是 1 到 5 的整数", "自定义上限拒绝")
    checked += _expect_error(lambda: model_request_limit(0), message, "零拒绝")
    checked += _expect_error(lambda: model_request_limit(65), message, "超上限拒绝")
    checked += _expect_error(lambda: model_request_limit(-1), message, "负数拒绝")
    checked += _expect_error(lambda: model_request_limit(True), message, "布尔拒绝")
    checked += _expect_error(lambda: model_request_limit(False), message, "假布尔拒绝")
    checked += _expect_error(lambda: model_request_limit(1.0), message, "浮点拒绝")
    checked += _expect_error(lambda: model_request_limit("1"), message, "字符串拒绝")
    checked += _expect_error(lambda: model_request_limit(None), message, "None 拒绝")

    checked += _environment_check(
        None, ("value", DEFAULT_MAX_MODEL_REQUESTS), "未设置默认")
    checked += _environment_check("", ("value", DEFAULT_MAX_MODEL_REQUESTS), "空值默认")
    checked += _environment_check("   ", ("value", DEFAULT_MAX_MODEL_REQUESTS), "空白默认")
    checked += _environment_check(
        "\t\n", ("value", DEFAULT_MAX_MODEL_REQUESTS), "控制空白默认")
    checked += _environment_check("1", ("value", 1), "环境下限")
    checked += _environment_check(
        str(MAX_MODEL_REQUESTS), ("value", MAX_MODEL_REQUESTS), "环境上限")
    checked += _environment_check(" 7 ", ("value", 7), "环境去空白")
    checked += _environment_check("6  ", ("value", 6), "尾部空白")
    checked += _environment_check("0", ("error", environment_message), "环境零拒绝")
    checked += _environment_check(
        str(MAX_MODEL_REQUESTS + 1), ("error", environment_message), "环境超上限拒绝")
    checked += _environment_check("01", ("error", environment_message), "前导零拒绝")
    checked += _environment_check("00", ("error", environment_message), "双零拒绝")
    checked += _environment_check("100", ("error", environment_message), "三位数拒绝")
    checked += _environment_check("-1", ("error", environment_message), "负号拒绝")
    checked += _environment_check("+1", ("error", environment_message), "正号拒绝")
    checked += _environment_check("1.0", ("error", environment_message), "小数拒绝")
    checked += _environment_check("1e1", ("error", environment_message), "科学计数拒绝")
    checked += _environment_check("abc", ("error", environment_message), "字母拒绝")
    checked += _environment_check(" 65 ", ("error", environment_message), "去空白后越界")
    checked += _environment_check("0001", ("error", environment_message), "超长文本拒绝")
    checked += _environment_check("9", ("value", 9), "环境读取即时")
    checked += _environment_check(
        None, ("value", DEFAULT_MAX_MODEL_REQUESTS), "恢复后默认")
    return checked


def check_turn_limits() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(LIMIT_FRAGMENTS, module, MODULE)
    checked += _expect(ENVIRONMENT_FRAGMENTS, module, MODULE)
    # 环境解析：读取 → 去空白 → 空值默认 → 文本边界 → 转换 → 统一错误。
    checked += _ordered(
        (
            'raw = os.environ.get("BOSS_HARNESS_MAX_MODEL_REQUESTS")',
            'value = "" if raw is None else raw.strip()',
            "if not value:",
            "return DEFAULT_MAX_MODEL_REQUESTS",
            "if len(value) > 2 or re.fullmatch(r\"[1-9][0-9]?\", value) is None:",
            "return model_request_limit(int(value))",
        ),
        module,
        MODULE,
    )
    # 错误提示不得回显原值。
    if "{value}" in module or "{raw}" in module:
        raise ValueError(f"{MODULE} 的错误不得回显原配置")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_turn_limits()
    except (ValueError, OSError) as error:
        print(f"回合请求上限核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合请求上限一致：{checked} 项结构、行为与有界解析校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
