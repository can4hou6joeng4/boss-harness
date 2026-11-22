#!/usr/bin/env python3
"""核对工具结果信封的校验、深拷贝与错误收敛边界。

toolkit.py 的 snapshot_result 是宿主回调与持久记录之间的唯一契约：只接受
JSON 原生值、限制 64 层嵌套、允许 recovery_action 为 null，并在任何非法
信封上抛出同一个 ValueError。检查同时核对源码结构和快照行为。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.toolkit import ToolResult, snapshot_result  # noqa: E402

MODULE = "harness/src/boss_harness/toolkit.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

RESULT_FRAGMENTS = (
    "@dataclass",
    "ok: bool",
    "command: str",
    "data: Any = None",
    "error: dict | None = None",
    "hints: dict | None = None",
    'raw: str = ""',
    "pagination: dict | None = None",
)
CHECK_FRAGMENTS = (
    "if depth > 64:",
    # 只接受 JSON 原生值：tuple、set、非有限浮点与自定义对象都不能进入记录。
    "if value is None or type(value) in {str, bool, int}:",
    "if type(value) is float and math.isfinite(value):",
    "if type(value) is dict and all(type(key) is str for key in value):",
    "if type(value) is list:",
    "raise ValueError",
)
ENVELOPE_FRAGMENTS = (
    "if (not isinstance(result, ToolResult) or type(result.ok) is not bool",
    "or type(result.command) is not str or not result.command or type(result.raw) is not str",
    "or any(value is not None and type(value) is not dict",
    "for value in (result.error, result.hints, result.pagination))):",
    'if (type(error.get("code")) is not str or not error["code"]',
    'or type(error.get("message")) is not str):',
)
RECOVERY_FRAGMENTS = (
    'if "recovery_action" in error:',
    # null 与字段缺失同义：下游都用 or "" 读取；按非法类型拒绝会把合法的
    # JOB_NOT_FOUND / GREET_LIMIT / search 平台错误替换为 TOOL_ERROR。
    'if error["recovery_action"] is None:',
    'error = {key: value for key, value in error.items() if key != "recovery_action"}',
    'elif type(error["recovery_action"]) is not str:',
)
COPY_FRAGMENTS = (
    'envelope = {"ok": result.ok, "command": result.command, "data": result.data,',
    '"error": error, "hints": result.hints, "pagination": result.pagination}',
    "copied = json.loads(json.dumps(envelope, ensure_ascii=False, allow_nan=False))",
    "return ToolResult(**copied, raw=result.raw)",
    'raise ValueError("工具处理器返回了无效 ToolResult") from None',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "嵌套最多 64 层"),
    (TECHNICAL_REFERENCE, "原始 CLI 信封保留在适配对象的 `raw` 中"),
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"工具结果信封行为变化 {label}：期望 {expected!r}，实际 {actual!r}")


def _expect_rejected(result: object, label: str) -> None:
    try:
        snapshot_result(result)
    except ValueError as error:
        _expect_value((type(error), str(error), error.__suppress_context__),
                      (ValueError, "工具处理器返回了无效 ToolResult", True), label)
    else:
        raise ValueError(f"工具结果信封应拒绝 {label}")


def _nested_lists(levels: int) -> object:
    value: object = "结果"
    for _ in range(levels):
        value = [value]
    return value


def _behavior_checks() -> int:
    data = {"列表": ["中🙂", None, True, 7, 1.5, {"文本": "原始"}]}
    error = {"code": "RATE_LIMITED", "message": "稍后重试", "recovery_action": None,
             "details": {"等待": [3]}}
    hints = {"下一步": ["查看"]}
    pagination = {"cursor": "下一页", "info": {"sizes": [2]}}
    host = ToolResult(False, "demo", data=data, error=error, hints=hints,
                      raw='{"消息":"中🙂"}', pagination=pagination)
    detached = snapshot_result(host)
    _expect_value("recovery_action" in error, True, "输入保留 null 恢复动作")
    data["列表"][-1]["文本"] = "宿主修改"
    error["details"]["等待"].append(5)
    hints["下一步"].clear()
    pagination["info"]["sizes"].append(8)
    _expect_value(detached, ToolResult(
        False, "demo", data={"列表": ["中🙂", None, True, 7, 1.5, {"文本": "原始"}]},
        error={"code": "RATE_LIMITED", "message": "稍后重试", "details": {"等待": [3]}},
        hints={"下一步": ["查看"]}, raw='{"消息":"中🙂"}',
        pagination={"cursor": "下一页", "info": {"sizes": [2]}},
    ), "深拷贝与 null 恢复动作")

    at_limit = ToolResult(True, "demo", data=_nested_lists(63))
    accepted = (
        ("缺省可选字段", ToolResult(True, "demo")),
        ("缺省恢复动作", ToolResult(False, "demo", error={"code": "FAIL", "message": "失败"})),
        ("字符串恢复动作", ToolResult(False, "demo", error={
            "code": "FAIL", "message": "", "recovery_action": "重试",
        })),
        ("深度 64", at_limit),
    )
    for label, result in accepted:
        _expect_value(snapshot_result(result), result, label)

    cycle: list = []
    cycle.append(cycle)
    rejected = (
        ("非 ToolResult", {"ok": True, "command": "demo"}),
        ("整数成功标记", ToolResult(1, "demo")),
        ("命令为空", ToolResult(True, "")),
        ("命令类型", ToolResult(True, 1)),
        ("raw 类型", ToolResult(True, "demo", raw=b"raw")),
        ("错误类型", ToolResult(False, "demo", error=[])),
        ("提示类型", ToolResult(True, "demo", hints=[])),
        ("分页类型", ToolResult(True, "demo", pagination=[])),
        ("错误码缺失", ToolResult(False, "demo", error={"message": "失败"})),
        ("错误码为空", ToolResult(False, "demo", error={"code": "", "message": "失败"})),
        ("错误消息类型", ToolResult(False, "demo", error={"code": "FAIL", "message": 1})),
        ("恢复动作类型", ToolResult(False, "demo", error={
            "code": "FAIL", "message": "失败", "recovery_action": [],
        })),
        ("深度 65", ToolResult(True, "demo", data=_nested_lists(64))),
        ("循环数组", ToolResult(True, "demo", data=cycle)),
        ("元组", ToolResult(True, "demo", data={"items": (1, 2)})),
        ("集合", ToolResult(True, "demo", data={"items": {1, 2}})),
        ("自定义对象", ToolResult(True, "demo", data=object())),
        ("非字符串键", ToolResult(True, "demo", data={1: "值"})),
        ("非有限数字 NaN", ToolResult(True, "demo", data=float("nan"))),
        ("非有限数字 Infinity", ToolResult(True, "demo", hints={"value": float("inf")})),
        ("分页内非法对象", ToolResult(True, "demo", pagination={"cursor": b"raw"})),
    )
    for label, result in rejected:
        _expect_rejected(result, label)
    return 2 + len(accepted) + len(rejected)


def check_toolkit() -> int:
    module = _read(MODULE)
    checked = _expect(RESULT_FRAGMENTS, module, MODULE)
    checked += _expect(CHECK_FRAGMENTS, module, MODULE)
    checked += _expect(ENVELOPE_FRAGMENTS, module, MODULE)
    checked += _expect(RECOVERY_FRAGMENTS, module, MODULE)
    checked += _expect(COPY_FRAGMENTS, module, MODULE)
    # 先按信封取值，再校验，最后经 JSON 往返深拷贝；顺序变化会跳过校验。
    checked += _ordered(
        (
            "envelope = {",
            "check(envelope)",
            "copied = json.loads(json.dumps(envelope, ensure_ascii=False, allow_nan=False))",
        ),
        module,
        MODULE,
    )
    # 信封必须显式构造并做 JSON 往返；整份展开 dataclass 会绕过字段白名单。
    if "**result" in module:
        raise ValueError(f"{MODULE} 不能整份展开宿主返回值")
    if "ensure_ascii=True" in module:
        raise ValueError(f"{MODULE} 的信封必须保留非 ASCII 字符")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_toolkit()
        behavior_cases = _behavior_checks()
    except ValueError as error:
        print(f"工具结果信封核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具结果信封一致：{checked} 项结构校验、{behavior_cases} 项行为检查")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
