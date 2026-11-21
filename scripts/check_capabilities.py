#!/usr/bin/env python3
"""核对模型容量配置的预算、校验与错误收敛边界。

capabilities.py 把显式容量覆盖与供应商传输分离：解析在 64 KiB / 128 项内，
只接受三种 provider、两个必需字段与一个可选的七档数组，容量关系必须自洽；
任何解析错误都收敛为固定说明，不显示原配置。任一放宽都会让未知字段或
无效数值进入上下文预算，因此静态固定，并用行为对照核对解析与回退。
不访问网络、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/capabilities.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.models.capabilities import (  # noqa: E402
    _CONFIG_ERROR,
    _reject_constant,
    REASONING_EFFORTS,
    ModelCapabilities,
    ModelCatalog,
)

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"模型容量配置行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, error: type[BaseException], label: str) -> int:
    try:
        call()
    except error:
        return 1
    raise ValueError(f"模型容量配置行为变化 {label}：未抛出 {error.__name__}")


def _expect_config_error(call, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != _CONFIG_ERROR:
            raise ValueError(f"模型容量配置行为变化 {label}：错误消息未收敛：{error}") from None
        return 1
    raise ValueError(f"模型容量配置行为变化 {label}：未抛出 ValueError")


def _assign(mapping, key, value) -> None:
    mapping[key] = value


def _behavior_checks() -> int:
    checked = 0
    # 容量关系：窗口须大于 4096，输出须为不超过窗口的正整数，布尔不算整数。
    caps = ModelCapabilities(8192, 4096)
    checked += _expect_value(caps.describe(),
                             {"contextWindow": 8192, "maxOutputTokens": 4096,
                              "capabilitySource": "configured", "capacityIsEstimate": False,
                              "reasoningEfforts": []}, "默认投影")
    checked += _expect_value(ModelCapabilities(4097, 1).context_window, 4097, "窗口下限放行")
    for window, output in ((4096, 1), (8192, 0), (8192, 8193), (True, 1), (8192, True)):
        checked += _expect_error(lambda window=window, output=output:
                                 ModelCapabilities(window, output), ValueError,
                                 f"容量关系 {window!r}/{output!r}")
    for source, estimated in (("", False), ("  ", False), (1, False), ("configured", 1)):
        checked += _expect_error(lambda source=source, estimated=estimated:
                                 ModelCapabilities(8192, 1024, source, estimated), ValueError,
                                 f"来源与估算 {source!r}/{estimated!r}")

    # 推理档位：七档白名单、去重、元组类型。
    checked += _expect_value(
        ModelCapabilities(8192, 1024, reasoning_efforts=("low", "high")).describe()
        ["reasoningEfforts"], ["low", "high"], "推理档位投影")
    for efforts in (("low", "low"), ("bogus",), ("low",) * 8, ["low"], (1,)):
        checked += _expect_error(
            lambda efforts=efforts: ModelCapabilities(8192, 1024, reasoning_efforts=efforts),
            ValueError, f"推理档位 {efforts!r}")
    checked += _expect_value(len(REASONING_EFFORTS), 7, "档位数量")

    # 目录：覆盖命中返回同一对象，未命中回退 legacy 默认，覆盖表只读。
    empty = ModelCatalog()
    fallback = empty.resolve("openai", "unknown")
    checked += _expect_value((fallback.context_window, fallback.max_output_tokens,
                              fallback.source, fallback.estimated),
                             (200_000, 64_000, "legacy-default", True), "默认容量")
    checked += _expect_value(empty.resolve("x", "y") is fallback, True, "默认容量复用")
    catalog = ModelCatalog({("openai", "gpt"): caps})
    checked += _expect_value(catalog.resolve("openai", "gpt") is caps, True, "覆盖命中")
    checked += _expect_value(catalog.resolve("OpenAI", "gpt") is fallback, True, "区分大小写")
    checked += _expect_error(lambda: _assign(catalog._overrides, ("openai", "gpt"), caps),
                             TypeError, "覆盖表只读")

    # 目录构造：非映射、项数、键格式与值类型都拒绝。
    checked += _expect_error(lambda: ModelCatalog([("openai", "m")]), ValueError, "覆盖表类型")
    checked += _expect_error(
        lambda: ModelCatalog({("openai", f"m{i}"): caps for i in range(129)}), ValueError,
        "覆盖表项数")
    for key in (("x", "m"), ("openai", ""), ("openai", "a b"), ("openai", 1), "openai/m"):
        checked += _expect_error(lambda key=key: ModelCatalog({key: caps}), ValueError,
                                 f"覆盖键 {key!r}")
    checked += _expect_error(lambda: ModelCatalog({("openai", "m"): {"contextWindow": 1}}),
                             ValueError, "覆盖值类型")

    # 环境解析：未设置与空白使用默认；有效配置投影来源与推理档位。
    checked += _expect_value(ModelCatalog.from_environment({}).resolve("a", "b") is fallback,
                             True, "未设置")
    checked += _expect_value(
        ModelCatalog.from_environment({"BOSS_HARNESS_MODEL_LIMITS": "   "}).resolve("a", "b")
        is fallback, True, "空白配置")
    raw = ('{"openai/gpt-5": {"contextWindow": 128000, "maxOutputTokens": 32000, '
           '"reasoningEfforts": ["low", "high"]}}')
    parsed = ModelCatalog.from_environment({"BOSS_HARNESS_MODEL_LIMITS": raw})
    resolved = parsed.resolve("openai", "gpt-5")
    checked += _expect_value((resolved.context_window, resolved.max_output_tokens,
                              resolved.reasoning_efforts, resolved.source, resolved.estimated),
                             (128000, 32000, ("low", "high"), "configured", False),
                             "有效配置")
    checked += _expect_value(parsed.resolve("openai", "gpt-4") is fallback, True, "部分命中回退")

    # 非法配置全部收敛为同一条固定说明，且不回显原配置。
    invalid = {
        "非 JSON": "not json",
        "重复键": '{"openai/m": {"contextWindow": 8192, "maxOutputTokens": 1}, '
                  '"openai/m": {"contextWindow": 8192, "maxOutputTokens": 1}}',
        "NaN 常量": '{"openai/m": {"contextWindow": NaN, "maxOutputTokens": 1}}',
        "Infinity 常量": '{"openai/m": {"contextWindow": Infinity, "maxOutputTokens": 1}}',
        "顶层数组": "[]",
        "非字符串": 1,
        "字节上限": "x" * (64 * 1024 + 1),
        "项数上限": "{" + ",".join(
            f'"openai/m{i}": {{"contextWindow": 8192, "maxOutputTokens": 1}}'
            for i in range(129)) + "}",
        "缺少分隔符": '{"gpt": {"contextWindow": 8192, "maxOutputTokens": 1}}',
        "未知 provider": '{"x/m": {"contextWindow": 8192, "maxOutputTokens": 1}}',
        "模型名含空白": '{"openai/a b": {"contextWindow": 8192, "maxOutputTokens": 1}}',
        "限制不是对象": '{"openai/m": 1}',
        "缺少必填字段": '{"openai/m": {"contextWindow": 8192}}',
        "多余字段": '{"openai/m": {"contextWindow": 8192, "maxOutputTokens": 1, "x": 1}}',
        "档位不是数组": '{"openai/m": {"contextWindow": 8192, "maxOutputTokens": 1, '
                        '"reasoningEfforts": "low"}}',
        "档位含数字": '{"openai/m": {"contextWindow": 8192, "maxOutputTokens": 1, '
                      '"reasoningEfforts": [1]}}',
        "窗口过小": '{"openai/m": {"contextWindow": 4096, "maxOutputTokens": 1}}',
        "输出超过窗口": '{"openai/m": {"contextWindow": 8192, "maxOutputTokens": 8193}}',
        "布尔窗口": '{"openai/m": {"contextWindow": true, "maxOutputTokens": 1}}',
        "secret 标记": '{"openai/secret-model": {"contextWindow": 1}}',
    }
    for label, value in invalid.items():
        checked += _expect_config_error(
            lambda value=value: ModelCatalog.from_environment({"BOSS_HARNESS_MODEL_LIMITS": value}),
            label)
    checked += _expect_config_error(lambda: _reject_constant("NaN"), "常量钩子")
    return checked


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
    # 常量钩子必须直接拒绝 NaN / Infinity，而不是依赖后续容量校验兜底。
    if ("def _reject_constant(_value: str) -> None:\n    raise ValueError(_CONFIG_ERROR)"
            not in module):
        raise ValueError(f"{MODULE} 的常量钩子必须拒绝非有限数值")
    checked += 1
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
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_capabilities()
    except (ValueError, TypeError) as error:
        print(f"模型容量配置核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型容量配置一致：{checked} 项预算、校验与错误收敛校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
