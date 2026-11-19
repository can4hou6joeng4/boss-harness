#!/usr/bin/env python3
"""核对自动压缩策略的校验、归一化与失败契约。

compaction.py 决定自动压缩的三项界面设置与三项摘要线路设置如何校验、归一化与
合并：未知字段、重复键和非法类型一律拒绝，错误不回显原配置，codex 归一为
openai。任一放宽都会让坏配置静默生效，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/compaction.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    return checked + 1


def main() -> int:
    try:
        checked = check_compaction()
    except ValueError as error:
        print(f"自动压缩策略核对失败，{error}", file=sys.stderr)
        return 2
    print(f"自动压缩策略一致：{checked} 项校验与归一化防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
