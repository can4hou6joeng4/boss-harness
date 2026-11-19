#!/usr/bin/env python3
"""核对模型容量配置的预算、校验与错误收敛边界。

capabilities.py 把显式容量覆盖与供应商传输分离：解析在 64 KiB / 128 项内，
只接受三种 provider、两个必需字段与一个可选的七档数组，容量关系必须自洽；
任何解析错误都收敛为固定说明，不显示原配置。任一放宽都会让未知字段或
无效数值进入上下文预算，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/capabilities.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

CONSTANT_FRAGMENTS = (
    '_ENV_NAME = "BOSS_HARNESS_MODEL_LIMITS"\n',
    "_MAX_JSON_BYTES = 64 * 1024\n",
    "_MAX_MODELS = 128\n",
    '_PROVIDERS = frozenset({"anthropic", "openai", "none"})\n',
    '_FIELDS = frozenset({"contextWindow", "maxOutputTokens", "reasoningEfforts"})\n',
    '_REQUIRED_FIELDS = frozenset({"contextWindow", "maxOutputTokens"})\n',
    'REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")\n',
    "_REASONING_EFFORT_SET = frozenset(REASONING_EFFORTS)\n",
    '_CONFIG_ERROR = "BOSS_HARNESS_MODEL_LIMITS 必须是有效的模型容量配置"\n',
    "_UNSET = object()\n",
)
CAPABILITY_FRAGMENTS = (
    "class ModelCapabilities:",
    "if (type(self.context_window) is not int or self.context_window <= 4096",
    "or type(self.max_output_tokens) is not int or self.max_output_tokens <= 0",
    "or self.max_output_tokens > self.context_window):",
    'raise ValueError("模型上下文窗口必须大于 4096，输出上限必须为不超过窗口的正整数")',
    "if not isinstance(self.source, str) or not self.source.strip() or type(self.estimated) is not bool:",
    "if (not isinstance(self.reasoning_efforts, tuple)",
    "or len(self.reasoning_efforts) > len(_REASONING_EFFORT_SET)",
    "or any(not isinstance(level, str) or level not in _REASONING_EFFORT_SET",
    "or len(set(self.reasoning_efforts)) != len(self.reasoning_efforts)):",
    'raise ValueError("模型推理档位声明无效")',
    "def describe(self) -> dict[str, int | str | bool | list[str]]:",
    '"contextWindow": self.context_window, "maxOutputTokens": self.max_output_tokens,',
    '"capabilitySource": self.source, "capacityIsEstimate": self.estimated,',
    '"reasoningEfforts": list(self.reasoning_efforts)',
)
DEFAULT_FRAGMENTS = (
    '_LEGACY_DEFAULT = ModelCapabilities(200_000, 64_000, source="legacy-default", estimated=True)',
)
KEY_FRAGMENTS = (
    "def _valid_key(key: object) -> bool:",
    "return (isinstance(key, tuple) and len(key) == 2 and isinstance(key[0], str)",
    "and key[0] in _PROVIDERS and isinstance(key[1], str) and bool(key[1])",
    "and not any(char.isspace() for char in key[1]))",
    "def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:",
    "if key in result:",
    "raise ValueError(_CONFIG_ERROR)",
    "def _reject_constant(_value: str) -> None:",
)
CATALOG_FRAGMENTS = (
    "class ModelCatalog:",
    "_overrides: Mapping[tuple[str, str], ModelCapabilities] = field(repr=False)",
    "if not isinstance(overrides, Mapping) or len(overrides) > _MAX_MODELS:",
    'raise ValueError("模型容量覆盖表无效")',
    "if not _valid_key(key) or not isinstance(value, ModelCapabilities):",
    'object.__setattr__(self, "_overrides", MappingProxyType(copied))',
    "def resolve(self, provider: str, model: str) -> ModelCapabilities:",
    "return self._overrides.get((provider, model), _LEGACY_DEFAULT)",
)
ENV_FRAGMENTS = (
    "def from_environment(cls, environ: Mapping[str, str] | None = None) -> ModelCatalog:",
    "raw = (os.environ if environ is None else environ).get(_ENV_NAME, _UNSET)",
    "if raw is _UNSET:",
    "if isinstance(raw, str) and not raw.strip():",
    "if not isinstance(raw, str) or len(raw.encode(\"utf-8\")) > _MAX_JSON_BYTES:",
    "parsed = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)",
    "if not isinstance(parsed, dict) or len(parsed) > _MAX_MODELS:",
    'provider, separator, model = name.partition("/")',
    "if (not separator or not _valid_key(key) or not isinstance(limits, dict)",
    "or not _REQUIRED_FIELDS <= set(limits) or set(limits) - _FIELDS):",
    'efforts = limits.get("reasoningEfforts", [])',
    "if (not isinstance(efforts, list) or any(not isinstance(level, str) for level in efforts)):",
    'overrides[key] = ModelCapabilities(limits["contextWindow"], limits["maxOutputTokens"],',
    "reasoning_efforts=tuple(efforts))",
    "return cls(overrides)",
    "except (ValueError, TypeError, RecursionError, UnicodeError):",
    "raise ValueError(_CONFIG_ERROR) from None",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "窗口须大于 4096，输出上限须为不超过窗口的正数"),
    (TECHNICAL_REFERENCE, "配置最多 128 项、UTF-8 编码 64 KiB，拒绝重复键、未知字段、布尔值和无效类型；错误不显示原配置"),
    (TECHNICAL_REFERENCE, "空值或只有空白视为未设置，使用内置默认容量"),
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


def check_capabilities() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(CAPABILITY_FRAGMENTS, module, MODULE)
    checked += _expect(DEFAULT_FRAGMENTS, module, MODULE)
    checked += _expect(KEY_FRAGMENTS, module, MODULE)
    checked += _expect(CATALOG_FRAGMENTS, module, MODULE)
    checked += _expect(ENV_FRAGMENTS, module, MODULE)
    # 环境解析：未设置 → 空白 → 字节上限 → 带钩子解析 → 项数 → 逐项 → 构建。
    checked += _ordered(
        (
            "if raw is _UNSET:",
            "if isinstance(raw, str) and not raw.strip():",
            'if not isinstance(raw, str) or len(raw.encode("utf-8")) > _MAX_JSON_BYTES:',
            "parsed = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)",
            "if not isinstance(parsed, dict) or len(parsed) > _MAX_MODELS:",
            'provider, separator, model = name.partition("/")',
            "reasoning_efforts=tuple(efforts))",
            "return cls(overrides)",
        ),
        module,
        MODULE,
    )
    # 目录：可选覆盖 → 类型 / 项数 → 逐键校验 → 只读副本。
    checked += _ordered(
        (
            "if overrides is None:",
            "if not isinstance(overrides, Mapping) or len(overrides) > _MAX_MODELS:",
            "if not _valid_key(key) or not isinstance(value, ModelCapabilities):",
            'object.__setattr__(self, "_overrides", MappingProxyType(copied))',
        ),
        module,
        MODULE,
    )
    # 反向断言：禁止无钩子解析、错误回显原配置与可变覆盖表。
    if "json.loads(raw)" in module:
        raise ValueError(f"{MODULE} 的配置解析必须带重复键与常量钩子")
    if "str(exc)" in module or "{raw}" in module:
        raise ValueError(f"{MODULE} 不得在错误中回显原配置")
    if "raise ValueError(_CONFIG_ERROR) from None" not in module:
        raise ValueError(f"{MODULE} 的配置错误必须丢弃解析器上下文")
    if "MappingProxyType(copied)" not in module:
        raise ValueError(f"{MODULE} 的覆盖表必须只读")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_capabilities()
    except ValueError as error:
        print(f"模型容量配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型容量配置一致：{checked} 项预算、校验与错误收敛防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
