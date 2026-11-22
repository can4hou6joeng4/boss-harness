#!/usr/bin/env python3
"""核对工具定义、组合与注册表的校验边界。

`tool_bundle.py` 冻结进程内工具组合：定义的名称、描述、回调、审批标记、执行模式
与结果预算决定允许清单；组合 id 与成员去重决定快照稳定；注册表的只读投影与
描述字段直接进入桌面工具面板。这里既静态固定关键分支，也直接构造定义、组合与
注册表核对结果与固定文案。不启动子进程、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/tool_bundle.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.tool_bundle import (  # noqa: E402
    _ARGUMENT_ERROR,
    _BUNDLE_ERROR,
    _DEFINITION_ERROR,
    ToolBundle,
    ToolDefinition,
    ToolRegistry,
    _definitions,
)
from boss_harness.toolkit import ToolResult  # noqa: E402

CONSTANT_FRAGMENTS = (
    '_DEFINITION_ERROR = "工具定义无效"',
    '_BUNDLE_ERROR = "工具组合定义无效"',
    '_ARGUMENT_ERROR = "工具参数不符合已注册的 schema"',
)
DEFINITION_FRAGMENTS = (
    're.fullmatch(r"[A-Za-z0-9_-]{1,64}", name)',
    "or not isinstance(description, str) or not description.strip()",
    "or not callable(handler) or type(requires_approval) is not bool",
    'or type(execution_mode) is not str or execution_mode not in {"sequential", "parallel"}',
    'or (execution_mode == "parallel" and requires_approval)',
    "or not MIN_MODEL_TOOL_RESULT_BYTES <= max_model_result_bytes <= MAX_MODEL_TOOL_RESULT_BYTES",
    "(validate_arguments is not None and not callable(validate_arguments))",
    "schema_json = canonical_schema(input_schema)",
    "return json.loads(self._schema_json)",
    "callback_copy = json.loads(json.dumps(copied, ensure_ascii=False))",
    "raise ValueError(_ARGUMENT_ERROR) from None",
)
BUNDLE_FRAGMENTS = (
    "if type(tools) is not tuple or any(not isinstance(tool, ToolDefinition) for tool in tools):",
    "if len({tool.name for tool in tools}) != len(tools):",
    'raise ValueError("工具组合包含重复名称")',
    "or not self.id or len(self.id) > 128",
    "or any(char.isspace() for char in self.id)",
    "or not callable(self.pause_on_result) or not callable(self.describe_bridge)",
    "(self.offline_reply is not None and not callable(self.offline_reply))",
)
REGISTRY_FRAGMENTS = (
    'object.__setattr__(self, "_by_name", MappingProxyType({tool.name: tool for tool in definitions}))',
    "frozenset(tool.name for tool in definitions if tool.requires_approval)",
    "if not read_only or not tool.requires_approval",
    "if type(read_only) is not bool:",
    'raise ValueError("只读工具投影标记无效")',
    '"readOnly": not tool.requires_approval,',
    '"executionMode": tool.execution_mode}',
    "if not isinstance(name, str) or name not in self._by_name:",
    'raise ValueError("工具不在注册表中")',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}：期望 {expected!r}，实际 {actual!r}")


def _expect_error(call, message: str | None, label: str) -> None:
    try:
        call()
    except ValueError as error:
        if message is not None and str(error) != message:
            raise ValueError(f"{label}：文案 {str(error)!r} != {message!r}") from None
        return
    raise ValueError(f"{label}：未抛出 ValueError")


def _behavior_checks() -> int:
    checked = 0
    minimum = 8 * 1024
    maximum = 1024 * 1024
    default = 20 * 1024
    schema = {"type": "object", "properties": {"x": {"type": "string"}},
              "required": ["x"], "additionalProperties": False}

    def handler(bridge, arguments):
        return ToolResult(ok=True, command="probe")

    def definition(**overrides):
        values = dict(name="probe", description="核对用工具", input_schema={"type": "object"},
                      handler=handler, requires_approval=False)
        values.update(overrides)
        return ToolDefinition(**values)

    # 定义：名称、描述、回调、审批标记、执行模式、结果预算与 schema 规范化。
    basic = definition()
    _expect_value(basic.name, "probe", "名称")
    checked += 1
    _expect_value(basic.input_schema, {"type": "object"}, "schema 往返")
    checked += 1
    _expect_value(basic.spec().input_schema, {"type": "object"}, "spec schema")
    checked += 1
    _expect_value(basic.execution_mode, "sequential", "默认执行模式")
    checked += 1
    _expect_value(basic.max_model_result_bytes, default, "默认结果预算")
    checked += 1
    _expect_value(basic.requires_approval, False, "默认只读")
    checked += 1
    schema_copy = basic.input_schema
    schema_copy["extra"] = 1
    _expect_value(basic.input_schema, {"type": "object"}, "schema 每次新副本")
    checked += 1
    for name in ("a", "a" * 64, "a-b_c"):
        _expect_value(definition(name=name).name, name, f"名称合法 {name!r}")
        checked += 1
    for name in ("", "a" * 65, "bad name", "名", "a.b"):
        _expect_error(lambda name=name: definition(name=name), _DEFINITION_ERROR, f"名称非法 {name!r}")
        checked += 1
    for description in ("", "   "):
        _expect_error(
            lambda description=description: definition(description=description),
            _DEFINITION_ERROR,
            f"描述非法 {description!r}",
        )
        checked += 1
    _expect_error(lambda: definition(handler=None), _DEFINITION_ERROR, "handler 非可调用")
    checked += 1
    for value in (1, "true", None):
        _expect_error(
            lambda value=value: definition(requires_approval=value),
            _DEFINITION_ERROR,
            f"审批标记非布尔 {value!r}",
        )
        checked += 1
    _expect_value(definition(execution_mode="parallel").execution_mode, "parallel", "并行模式")
    checked += 1
    _expect_error(lambda: definition(execution_mode="parallel", requires_approval=True),
                  _DEFINITION_ERROR, "并行不可审批")
    checked += 1
    _expect_error(lambda: definition(execution_mode="concurrent"), _DEFINITION_ERROR, "执行模式非法")
    checked += 1
    for value in (minimum - 1, maximum + 1, True, "20000"):
        _expect_error(
            lambda value=value: definition(max_model_result_bytes=value),
            _DEFINITION_ERROR,
            f"结果预算非法 {value!r}",
        )
        checked += 1
    _expect_value(definition(max_model_result_bytes=minimum).max_model_result_bytes, minimum, "结果预算下界")
    checked += 1
    _expect_value(definition(max_model_result_bytes=maximum).max_model_result_bytes, maximum, "结果预算上界")
    checked += 1
    _expect_error(lambda: definition(validate_arguments=1), _DEFINITION_ERROR, "校验回调非可调用")
    checked += 1
    _expect_error(lambda: definition(input_schema={"type": "array"}), None, "schema 非法")
    checked += 1
    # 参数校验：宿主回调收到深拷贝，异常与错误返回收敛为固定文案。
    tool = definition(input_schema=schema)
    _expect_value(tool.validate({"x": "v"}), {"x": "v"}, "参数通过")
    checked += 1
    _expect_error(lambda: tool.validate({"x": "v", "y": 1}), None, "多余参数拒绝")
    checked += 1
    seen: list[dict] = []

    def callback(arguments):
        seen.append(dict(arguments))
        arguments["x"] = "mutated"

    fixed = definition(input_schema=schema, validate_arguments=callback)
    _expect_value(fixed.validate({"x": "v"}), {"x": "v"}, "回调不污染返回值")
    checked += 1
    _expect_value(seen, [{"x": "v"}], "回调收到深拷贝")
    checked += 1

    def raising(arguments):
        raise RuntimeError("boom")

    _expect_error(
        lambda: definition(input_schema=schema, validate_arguments=raising).validate({"x": "v"}),
        _ARGUMENT_ERROR,
        "回调异常固定文案",
    )
    checked += 1
    _expect_error(
        lambda: definition(input_schema=schema, validate_arguments=lambda arguments: "bad").validate({"x": "v"}),
        _ARGUMENT_ERROR,
        "回调返回非 None 固定文案",
    )
    checked += 1
    _expect_value(
        definition(input_schema=schema, validate_arguments=lambda arguments: None).validate({"x": "v"}),
        {"x": "v"},
        "回调返回 None 通过",
    )
    checked += 1
    # 组合：id 非空、不超过 128 字符且无空白；成员必须是 ToolDefinition 元组且不重名。
    _expect_value(_definitions(()), (), "空组合")
    checked += 1
    _expect_value(_definitions((basic,)), (basic,), "单元组合")
    checked += 1
    _expect_error(lambda: _definitions([basic]), _BUNDLE_ERROR, "非 tuple")
    checked += 1
    _expect_error(lambda: _definitions((basic, "x")), _BUNDLE_ERROR, "非定义成员")
    checked += 1
    _expect_error(lambda: _definitions((basic, definition(name="probe"))),
                  "工具组合包含重复名称", "重复名称")
    checked += 1
    bundle = ToolBundle(id="boss", tools=(basic,), system_prompt="", pause_on_result=lambda result: False,
                        describe_bridge=lambda bridge: {})
    _expect_value(bundle.id, "boss", "组合 id")
    checked += 1
    _expect_value(bundle.system_prompt, "", "系统提示可为空")
    checked += 1
    _expect_value(
        ToolBundle(id="a" * 128, tools=(), system_prompt="s", pause_on_result=lambda r: False,
                   describe_bridge=lambda b: {}).id,
        "a" * 128,
        "128 字符组合 id",
    )
    checked += 1
    for bundle_id in ("", "a" * 129, "a b", "a\tb"):
        _expect_error(
            lambda bundle_id=bundle_id: ToolBundle(
                id=bundle_id, tools=(), system_prompt="s", pause_on_result=lambda r: False,
                describe_bridge=lambda b: {}),
            _BUNDLE_ERROR,
            f"组合 id 非法 {bundle_id!r}",
        )
        checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=(), system_prompt=1,
                           pause_on_result=lambda r: False, describe_bridge=lambda b: {}),
        _BUNDLE_ERROR,
        "系统提示非字符串",
    )
    checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=(), system_prompt="s", pause_on_result=None,
                           describe_bridge=lambda b: {}),
        _BUNDLE_ERROR,
        "暂停回调非可调用",
    )
    checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=(), system_prompt="s", pause_on_result=lambda r: False,
                           describe_bridge=None),
        _BUNDLE_ERROR,
        "描述回调非可调用",
    )
    checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=(), system_prompt="s", pause_on_result=lambda r: False,
                           describe_bridge=lambda b: {}, offline_reply=1),
        _BUNDLE_ERROR,
        "离线回复非可调用",
    )
    checked += 1
    _expect_value(
        ToolBundle(id="boss", tools=(), system_prompt="s", pause_on_result=lambda r: False,
                   describe_bridge=lambda b: {}, offline_reply=lambda b, x, y: "").id,
        "boss",
        "离线回复可调用",
    )
    checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=[basic], system_prompt="s", pause_on_result=lambda r: False,
                           describe_bridge=lambda b: {}),
        _BUNDLE_ERROR,
        "组合工具非 tuple",
    )
    checked += 1
    _expect_error(
        lambda: ToolBundle(id="boss", tools=(basic, definition(name="probe")), system_prompt="s",
                           pause_on_result=lambda r: False, describe_bridge=lambda b: {}),
        "工具组合包含重复名称",
        "组合重复名称",
    )
    checked += 1
    # 注册表：顺序、处理器、审批集合与只读投影；描述字段直接供桌面面板读取。
    approval_tool = definition(name="write", requires_approval=True)
    parallel_tool = definition(name="read", execution_mode="parallel", input_schema=schema)
    registry = ToolRegistry((approval_tool, parallel_tool))
    _expect_value(registry.definitions, (approval_tool, parallel_tool), "注册表顺序")
    checked += 1
    _expect_value(set(registry.handlers), {"write", "read"}, "处理器映射")
    checked += 1
    _expect_value(registry.approval_required, frozenset({"write"}), "审批集合")
    checked += 1
    _expect_value(isinstance(registry.handlers, MappingProxyType), True, "处理器只读映射")
    checked += 1
    _expect_value(registry.allowed_names(), frozenset({"write", "read"}), "全部工具")
    checked += 1
    _expect_value(registry.allowed_names(read_only=True), frozenset({"read"}), "只读工具")
    checked += 1
    _expect_error(lambda: registry.allowed_names(read_only=1), "只读工具投影标记无效", "只读标记非布尔")
    checked += 1
    _expect_value([spec.name for spec in registry.specs(read_only=True)], ["read"], "只读 spec")
    checked += 1
    _expect_value(registry.specs(read_only=True)[0].max_model_result_bytes, default, "spec 预算")
    checked += 1
    described = {item["name"]: item for item in registry.describe()}
    _expect_value(described["write"]["readOnly"], False, "描述审批只读标记")
    checked += 1
    _expect_value(described["write"]["requiresApproval"], True, "描述审批标记")
    checked += 1
    _expect_value(described["read"]["readOnly"], True, "描述只读标记")
    checked += 1
    _expect_value(described["read"]["executionMode"], "parallel", "描述执行模式")
    checked += 1
    _expect_value(described["read"]["inputSchema"], schema, "描述 schema")
    checked += 1
    _expect_value(described["read"]["maxModelResultBytes"], default, "描述预算")
    checked += 1
    _expect_value(registry.execution_modes(), {"write": "sequential", "read": "parallel"}, "执行模式映射")
    checked += 1
    _expect_error(lambda: registry.validate("missing", {}), "工具不在注册表中", "未知工具")
    checked += 1
    _expect_error(lambda: registry.validate(1, {}), "工具不在注册表中", "非字符串工具名")
    checked += 1
    _expect_error(lambda: registry.validate("read", {"x": 1}), None, "注册表参数错误")
    checked += 1
    _expect_value(ToolRegistry(()).allowed_names(), frozenset(), "空注册表")
    checked += 1
    return checked


def check_tool_bundle() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, DEFINITION_FRAGMENTS, BUNDLE_FRAGMENTS, REGISTRY_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    checked += _behavior_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_tool_bundle()
    except ValueError as error:
        print(f"工具组合边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具组合边界一致：{checked} 项定义、组合与注册表防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
