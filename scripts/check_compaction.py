#!/usr/bin/env python3
"""核对自动压缩策略的校验、归一化与失败契约。

compaction.py 决定自动压缩的三项界面设置与三项摘要线路设置如何校验、归一化与
合并：未知字段、重复键和非法类型一律拒绝，错误不回显原配置，codex 归一为
openai。任一放宽都会让坏配置静默生效，因此既静态固定关键片段，也直接调用
校验、构造、覆盖与环境解析核对结果与错误文案。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/compaction.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.compaction import (  # noqa: E402
    CompactionPolicy,
    ContextCompactionFailed,
    verified_policy,
)
from boss_harness.models.capabilities import REASONING_EFFORTS  # noqa: E402

CONSTANT_FRAGMENTS = (
    '_FIELDS = ("enabled", "triggerPercent", "keepRecentTokens", "provider", "model", "effort")\n',
    "_COMPACTION_FIELDS = set(_FIELDS)\n",
    '_PROVIDERS = {"anthropic", "openai", "codex"}\n',
)
VERIFIED_FRAGMENTS = (
    # 未知字段、空对象与非对象一律按「未记录」处理。
    "if not isinstance(value, dict) or not value or set(value) - set(fields):",
    'if "enabled" in value and type(enabled) is not bool:',
    'if "triggerPercent" in value and (type(trigger) is not int or not 1 <= trigger <= 100):',
    'if "keepRecentTokens" in value and (type(keep) is not int or not 1 <= keep <= 1_000_000):',
    'if "provider" in value and provider is not None and (',
    "not isinstance(provider, str) or provider not in _PROVIDERS):",
    "not isinstance(model, str) or not model.strip() or len(model) > 200",
    "or any(char.isspace() for char in model)):",
    'if "effort" in value and effort is not None and effort not in REASONING_EFFORTS:',
    "return {key: value[key] for key in fields if key in value}",
)
ERROR_FRAGMENTS = (
    "class ContextCompactionFailed(ValueError):",
    "super().__init__(message)",
    "self.code = code",
)
POLICY_FRAGMENTS = (
    "@dataclass(frozen=True)",
    "enabled: bool = True",
    "trigger_percent: int = 80",
    "keep_recent_tokens: int = 20_000",
    "if type(self.enabled) is not bool:",
    "if type(self.trigger_percent) is not int or not 1 <= self.trigger_percent <= 100:",
    "if type(self.keep_recent_tokens) is not int or not 1 <= self.keep_recent_tokens <= 1_000_000:",
    "if not isinstance(self.provider, str) or self.provider.strip().lower() not in _PROVIDERS:",
    # 摘要线路与主线路共用 provider 名：codex 必须归一为 openai。
    'object.__setattr__(self, "provider", "openai" if normalized == "codex" else normalized)',
    "or len(self.model) > 200 or any(c.isspace() for c in self.model)):",
    'raise ValueError("自动压缩 model 必须是最多 200 字符的非空模型 ID")',
    'raise ValueError("自动压缩 effort 档位无效")',
    '"keepRecentTokens": self.keep_recent_tokens, "provider": self.provider,',
)
OVERRIDE_FRAGMENTS = (
    'set(value) - {"enabled", "triggerPercent", "keepRecentTokens"}',
    'raise ValueError("autoCompaction 必须是只包含 enabled、triggerPercent、keepRecentTokens 的对象")',
    "value.get(\"enabled\", self.enabled)",
    "self.provider, self.model, self.effort)",
)
ENVIRONMENT_FRAGMENTS = (
    'base = verified_policy(stored, ("enabled", "triggerPercent", "keepRecentTokens")) or {}',
    'raw = os.environ.get("BOSS_HARNESS_COMPACTION")',
    # 空值或只有空白按未设置处理，占位行不能阻挡启动。
    "if raw is None or not raw.strip():",
    "def unique(pairs: list[tuple]) -> dict:",
    "if key in result:",
    'raise ValueError("duplicate field")',
    "if len(raw.encode(\"utf-8\")) > 4096:",
    "json.loads(raw, object_pairs_hook=unique)",
    "if not isinstance(value, dict) or set(value) - _COMPACTION_FIELDS:",
    "value.get(\"provider\"), value.get(\"model\"), value.get(\"effort\"))",
    "except (TypeError, ValueError, UnicodeError, RecursionError):",
    'raise ValueError("BOSS_HARNESS_COMPACTION 配置无效；请检查自动压缩字段与类型") from None',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "拒绝未知字段、重复键和无效类型，错误不显示原配置；空值或只有空白视为未设置，来源不报告为 `environment`。"),
    (USER_GUIDE, "`BOSS_HARNESS_COMPACTION` 的 JSON 字段、类型或取值范围无效；空值或只有空白视为未设置。"),
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
        raise ValueError(f"自动压缩策略行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"自动压缩策略行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}")
        return 1
    raise ValueError(f"自动压缩策略行为变化 {label}：期望 ValueError")


def _described(enabled: bool = True, trigger: int = 80, keep: int = 20_000,
               provider=None, model=None, effort=None) -> dict:
    return {"enabled": enabled, "triggerPercent": trigger, "keepRecentTokens": keep,
            "provider": provider, "model": model, "effort": effort}


def _environment_check(raw, expected, label: str, stored=None) -> int:
    name = "BOSS_HARNESS_COMPACTION"
    previous = os.environ.get(name)
    try:
        if raw is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = raw
        try:
            actual = ("policy", CompactionPolicy.from_environment(stored).describe())
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
    trigger_message = "自动压缩 triggerPercent 必须是 1 到 100 的整数"
    keep_message = "自动压缩 keepRecentTokens 必须是 1 到 1000000 的整数"
    provider_message = "自动压缩 provider 必须是 anthropic、openai 或 codex"
    model_message = "自动压缩 model 必须是最多 200 字符的非空模型 ID"
    effort_message = "自动压缩 effort 档位无效"
    override_message = "autoCompaction 必须是只包含 enabled、triggerPercent、keepRecentTokens 的对象"
    environment_message = "BOSS_HARNESS_COMPACTION 配置无效；请检查自动压缩字段与类型"

    checked += _expect_value(verified_policy(None), None, "非对象快照")
    checked += _expect_value(verified_policy([]), None, "列表快照")
    checked += _expect_value(verified_policy(""), None, "字符串快照")
    checked += _expect_value(verified_policy({}), None, "空快照")
    checked += _expect_value(verified_policy({"unknown": 1}), None, "未知字段")
    checked += _expect_value(verified_policy({"enabled": True}), {"enabled": True}, "开关真")
    checked += _expect_value(verified_policy({"enabled": False}), {"enabled": False}, "开关假")
    checked += _expect_value(verified_policy({"enabled": 1}), None, "开关整数")
    checked += _expect_value(verified_policy({"enabled": "true"}), None, "开关字符串")
    checked += _expect_value(
        verified_policy({"triggerPercent": 1}), {"triggerPercent": 1}, "触发下限")
    checked += _expect_value(
        verified_policy({"triggerPercent": 100}), {"triggerPercent": 100}, "触发上限")
    checked += _expect_value(verified_policy({"triggerPercent": 0}), None, "触发零")
    checked += _expect_value(verified_policy({"triggerPercent": 101}), None, "触发超限")
    checked += _expect_value(verified_policy({"triggerPercent": True}), None, "触发布尔")
    checked += _expect_value(verified_policy({"triggerPercent": 1.0}), None, "触发浮点")
    checked += _expect_value(
        verified_policy({"keepRecentTokens": 1}), {"keepRecentTokens": 1}, "保留下限")
    checked += _expect_value(
        verified_policy({"keepRecentTokens": 1_000_000}),
        {"keepRecentTokens": 1_000_000}, "保留上限")
    checked += _expect_value(verified_policy({"keepRecentTokens": 0}), None, "保留零")
    checked += _expect_value(
        verified_policy({"keepRecentTokens": 1_000_001}), None, "保留超限")
    checked += _expect_value(verified_policy({"keepRecentTokens": False}), None, "保留布尔")
    checked += _expect_value(verified_policy({"provider": None}), {"provider": None}, "线路空")
    checked += _expect_value(
        verified_policy({"provider": "anthropic"}), {"provider": "anthropic"}, "线路 anthropic")
    checked += _expect_value(
        verified_policy({"provider": "openai"}), {"provider": "openai"}, "线路 openai")
    checked += _expect_value(
        verified_policy({"provider": "codex"}), {"provider": "codex"}, "线路 codex")
    checked += _expect_value(verified_policy({"provider": "OpenAI"}), None, "线路大小写")
    checked += _expect_value(verified_policy({"provider": ""}), None, "线路空串")
    checked += _expect_value(verified_policy({"provider": 1}), None, "线路整数")
    checked += _expect_value(verified_policy({"model": None}), {"model": None}, "模型空")
    checked += _expect_value(
        verified_policy({"model": "gpt-5"}), {"model": "gpt-5"}, "模型常规")
    checked += _expect_value(
        verified_policy({"model": "m" * 200}), {"model": "m" * 200}, "模型长度边界")
    checked += _expect_value(verified_policy({"model": "m" * 201}), None, "模型超长")
    checked += _expect_value(verified_policy({"model": ""}), None, "模型空串")
    checked += _expect_value(verified_policy({"model": "   "}), None, "模型空白")
    checked += _expect_value(verified_policy({"model": "a b"}), None, "模型含空白")
    checked += _expect_value(verified_policy({"model": 1}), None, "模型整数")
    checked += _expect_value(verified_policy({"effort": None}), {"effort": None}, "档位空")
    checked += _expect_value(
        verified_policy({"effort": "low"}), {"effort": "low"}, "档位合法")
    checked += _expect_value(verified_policy({"effort": "ultra"}), None, "档位非法")
    checked += _expect_value(verified_policy({"effort": 1}), None, "档位整数")
    checked += _expect_value(
        list(verified_policy({"effort": "low", "model": "gpt-5", "enabled": False}).keys()),
        ["enabled", "model", "effort"], "字段顺序")
    checked += _expect_value(
        verified_policy({"enabled": True}, ("enabled", "triggerPercent")),
        {"enabled": True}, "自定义字段过滤")
    checked += _expect_value(
        verified_policy({"provider": "openai"}, ("enabled",)), None, "自定义字段外拒绝")
    checked += _expect_value(verified_policy({}, ()), None, "空字段空快照")
    checked += _expect_value(verified_policy({"enabled": True}, ()), None, "空字段非空快照")

    failure = ContextCompactionFailed("overflow", "上下文过大")
    checked += _expect_value(
        (failure.code, str(failure), isinstance(failure, ValueError)),
        ("overflow", "上下文过大", True), "失败契约")

    checked += _expect_value(CompactionPolicy().describe(), _described(), "默认策略")
    checked += _expect_value(
        CompactionPolicy(False, 50, 1000, " Anthropic ", "gpt-5", "high").describe(),
        _described(False, 50, 1000, "anthropic", "gpt-5", "high"), "自定义策略")
    checked += _expect_value(
        CompactionPolicy(provider=" OpenAI ").provider, "openai", "线路去空白小写")
    checked += _expect_value(CompactionPolicy(provider="CODEX").provider, "openai", "codex 大写归一")
    checked += _expect_value(
        CompactionPolicy(provider=" codex ").provider, "openai", "codex 去空白归一")
    checked += _expect_value(
        CompactionPolicy(provider="anthropic").provider, "anthropic", "线路保持")
    checked += _expect_value(
        CompactionPolicy(model="m" * 200).model, "m" * 200, "模型策略边界")
    checked += _expect_error(
        lambda: CompactionPolicy(enabled=1), "自动压缩 enabled 必须是布尔值", "开关策略类型")
    checked += _expect_error(lambda: CompactionPolicy(trigger_percent=0), trigger_message, "触发策略零")
    checked += _expect_error(
        lambda: CompactionPolicy(trigger_percent=101), trigger_message, "触发策略超限")
    checked += _expect_error(
        lambda: CompactionPolicy(trigger_percent=True), trigger_message, "触发策略布尔")
    checked += _expect_error(
        lambda: CompactionPolicy(trigger_percent=1.0), trigger_message, "触发策略浮点")
    checked += _expect_error(
        lambda: CompactionPolicy(keep_recent_tokens=0), keep_message, "保留策略零")
    checked += _expect_error(
        lambda: CompactionPolicy(keep_recent_tokens=1_000_001), keep_message, "保留策略超限")
    checked += _expect_error(
        lambda: CompactionPolicy(keep_recent_tokens=True), keep_message, "保留策略布尔")
    checked += _expect_error(
        lambda: CompactionPolicy(provider="other"), provider_message, "线路策略非法")
    checked += _expect_error(
        lambda: CompactionPolicy(provider=""), provider_message, "线路策略空串")
    checked += _expect_error(
        lambda: CompactionPolicy(provider=1), provider_message, "线路策略整数")
    checked += _expect_error(
        lambda: CompactionPolicy(model=""), model_message, "模型策略空串")
    checked += _expect_error(
        lambda: CompactionPolicy(model="   "), model_message, "模型策略空白")
    checked += _expect_error(
        lambda: CompactionPolicy(model="a b"), model_message, "模型策略含空白")
    checked += _expect_error(
        lambda: CompactionPolicy(model="m" * 201), model_message, "模型策略超长")
    checked += _expect_error(
        lambda: CompactionPolicy(model=1), model_message, "模型策略整数")
    checked += _expect_error(
        lambda: CompactionPolicy(effort="ultra"), effort_message, "档位策略非法")
    checked += _expect_error(
        lambda: CompactionPolicy(effort=" high "), effort_message, "档位策略空白")
    checked += _expect_error(
        lambda: CompactionPolicy(effort=1), effort_message, "档位策略整数")

    base = CompactionPolicy(True, 80, 20_000, "openai", "gpt-5", "high")
    checked += _expect_value(
        base.override({"enabled": False}).describe(),
        _described(False, 80, 20_000, "openai", "gpt-5", "high"), "覆盖合并")
    checked += _expect_value(base.override({}).describe(), base.describe(), "空覆盖")
    checked += _expect_value(
        base.override({"triggerPercent": 90, "keepRecentTokens": 500}).describe(),
        _described(True, 90, 500, "openai", "gpt-5", "high"), "覆盖多项")
    checked += _expect_value(base.describe(), _described(True, 80, 20_000, "openai", "gpt-5", "high"),
                             "覆盖不改基准")
    checked += _expect_error(
        lambda: base.override({"provider": "anthropic"}), override_message, "覆盖拒绝线路")
    checked += _expect_error(lambda: base.override([]), override_message, "覆盖拒绝列表")
    checked += _expect_error(lambda: base.override(None), override_message, "覆盖拒绝空值")
    checked += _expect_error(
        lambda: base.override({"triggerPercent": 0}), trigger_message, "覆盖传播校验")
    checked += _expect_error(
        lambda: base.override({"keepRecentTokens": True}), keep_message, "覆盖传播布尔")

    checked += _environment_check(
        None, ("policy", _described()), "环境未设置默认")
    stored = {"enabled": False, "triggerPercent": 50, "keepRecentTokens": 1000}
    checked += _environment_check(
        None, ("policy", _described(False, 50, 1000)), "持久设置生效", stored)
    checked += _environment_check(
        None, ("policy", _described()), "持久设置非法回退", {"triggerPercent": 0})
    checked += _environment_check(
        None, ("policy", _described()), "持久设置未知字段回退",
        {"enabled": False, "provider": "anthropic"})
    checked += _environment_check(
        "", ("policy", _described(False, 50, 1000)), "环境空值用持久设置", stored)
    checked += _environment_check(
        "   ", ("policy", _described()), "环境空白用默认")
    checked += _environment_check(
        '{"enabled": false}', ("policy", _described(False, 50, 1000)),
        "环境合并持久设置", stored)
    checked += _environment_check(
        '{"triggerPercent": 25}', ("policy", _described(False, 25, 1000)),
        "环境单项覆盖", stored)
    checked += _environment_check(
        '{"enabled": false, "triggerPercent": 10, "keepRecentTokens": 500, '
        '"provider": "CODEX", "model": "gpt-5", "effort": "high"}',
        ("policy", _described(False, 10, 500, "openai", "gpt-5", "high")), "环境全字段")
    checked += _environment_check(
        "{}", ("policy", _described(False, 30, 1000)), "环境空对象用持久设置",
        {"enabled": False, "triggerPercent": 30, "keepRecentTokens": 1000})
    checked += _environment_check(
        '{"provider": "anthropic"}', ("policy", _described(provider="anthropic")), "环境仅线路")
    checked += _environment_check(
        '{"enabled": true, "enabled": false}', ("error", environment_message), "环境重复键")
    checked += _environment_check(
        '{"foo": 1}', ("error", environment_message), "环境未知字段")
    checked += _environment_check("[1]", ("error", environment_message), "环境列表")
    checked += _environment_check("{", ("error", environment_message), "环境非法 JSON")
    checked += _environment_check("null", ("error", environment_message), "环境空值 JSON")
    checked += _environment_check("5", ("error", environment_message), "环境数字 JSON")
    checked += _environment_check(
        '{"enabled": 1}', ("error", environment_message), "环境开关类型")
    checked += _environment_check(
        '{"triggerPercent": 0}', ("error", environment_message), "环境触发越界")
    checked += _environment_check(
        '{"keepRecentTokens": 1000001}', ("error", environment_message), "环境保留越界")
    checked += _environment_check(
        '{"provider": "other"}', ("error", environment_message), "环境线路非法")
    checked += _environment_check(
        '{"model": "a b"}', ("error", environment_message), "环境模型含空白")
    checked += _environment_check(
        '{"model": "' + "m" * 201 + '"}', ("error", environment_message), "环境模型超长")
    checked += _environment_check(
        '{"effort": "ultra"}', ("error", environment_message), "环境档位非法")
    checked += _environment_check(
        '{"enabled": true}' + " " * 4100, ("error", environment_message), "环境超长")
    return checked


def check_compaction() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(VERIFIED_FRAGMENTS, module, MODULE)
    checked += _expect(ERROR_FRAGMENTS, module, MODULE)
    checked += _expect(POLICY_FRAGMENTS, module, MODULE)
    checked += _expect(OVERRIDE_FRAGMENTS, module, MODULE)
    checked += _expect(ENVIRONMENT_FRAGMENTS, module, MODULE)
    # 校验顺序固定：开关 → 触发阈值 → 保留量 → provider → model → effort。
    checked += _ordered(
        (
            'if "enabled" in value and type(enabled) is not bool:',
            'if "triggerPercent" in value and (type(trigger) is not int or not 1 <= trigger <= 100):',
            'if "keepRecentTokens" in value and (type(keep) is not int or not 1 <= keep <= 1_000_000):',
            'if "provider" in value and provider is not None and (',
            'if "effort" in value and effort is not None and effort not in REASONING_EFFORTS:',
            "return {key: value[key] for key in fields if key in value}",
        ),
        module,
        MODULE,
    )
    # 环境解析：读取 → 空白判断 → 重复键 → 大小 → 解析 → 字段检查 → 构造。
    checked += _ordered(
        (
            'raw = os.environ.get("BOSS_HARNESS_COMPACTION")',
            "if raw is None or not raw.strip():",
            "def unique(pairs: list[tuple]) -> dict:",
            'if len(raw.encode("utf-8")) > 4096:',
            "json.loads(raw, object_pairs_hook=unique)",
            "if not isinstance(value, dict) or set(value) - _COMPACTION_FIELDS:",
            'raise ValueError("BOSS_HARNESS_COMPACTION 配置无效；请检查自动压缩字段与类型") from None',
        ),
        module,
        MODULE,
    )
    # 解析必须带重复键钩子；错误提示不得回显原配置。
    if "json.loads(raw)" in module:
        raise ValueError(f"{MODULE} 必须拒绝重复键")
    if "{raw}" in module:
        raise ValueError(f"{MODULE} 的错误不得回显原配置")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_compaction()
    except (ValueError, OSError) as error:
        print(f"自动压缩策略核对失败，{error}", file=sys.stderr)
        return 2
    print(f"自动压缩策略一致：{checked} 项结构、行为与归一化校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
