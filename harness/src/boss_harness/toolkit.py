"""领域适配器与通用执行器共用的最小工具结果契约。"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    command: str
    data: Any = None
    error: dict | None = None
    hints: dict | None = None
    raw: str = ""
    pagination: dict | None = None


def snapshot_result(result: object) -> ToolResult:
    """Validate and detach a handler result before persisting or applying policy.

    Callbacks are trusted host code, but an invalid envelope must still finalize
    the dispatched call. JSON-only values avoid implicit tuple/key conversion;
    the depth bound keeps serialization within a predictable recursion limit.
    """
    def check(value: Any, depth: int = 0) -> None:
        if depth > 64:
            raise ValueError
        if value is None or type(value) in {str, bool, int}:
            return
        if type(value) is float and math.isfinite(value):
            return
        if type(value) is dict and all(type(key) is str for key in value):
            for child in value.values():
                check(child, depth + 1)
            return
        if type(value) is list:
            for child in value:
                check(child, depth + 1)
            return
        raise ValueError

    try:
        if (not isinstance(result, ToolResult) or type(result.ok) is not bool
                or type(result.command) is not str or not result.command or type(result.raw) is not str
                or any(value is not None and type(value) is not dict
                       for value in (result.error, result.hints, result.pagination))):
            raise ValueError
        error = result.error
        if error is not None:
            if (type(error.get("code")) is not str or not error["code"]
                    or type(error.get("message")) is not str):
                raise ValueError
            # 固定上游的 v1 错误信封允许 recovery_action 为 null（JOB_NOT_FOUND、
            # GREET_LIMIT 等直接登记为 None；search 的平台错误不传恢复动作时也是
            # null）。null 与字段缺失同义：下游都用 ``or ""`` 读取，若按非法类型
            # 拒绝，合法平台错误会被替换为 TOOL_ERROR，RATE_LIMITED 等暂停码也会
            # 失去暂停语义。非字符串、非 null 的值仍视为无效信封。
            if "recovery_action" in error:
                if error["recovery_action"] is None:
                    error = {key: value for key, value in error.items() if key != "recovery_action"}
                elif type(error["recovery_action"]) is not str:
                    raise ValueError
        envelope = {"ok": result.ok, "command": result.command, "data": result.data,
                    "error": error, "hints": result.hints, "pagination": result.pagination}
        check(envelope)
        copied = json.loads(json.dumps(envelope, ensure_ascii=False, allow_nan=False))
        return ToolResult(**copied, raw=result.raw)
    except Exception:
        raise ValueError("工具处理器返回了无效 ToolResult") from None
