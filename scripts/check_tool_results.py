#!/usr/bin/env python3
"""核对工具结果分页、内容寻址与引用恢复边界，成功时输出核对项数量。

源码检查覆盖预算常量和读取路径的接入边界。行为检查覆盖执行状态、重试处置、
桌面结果投影、内容寻址引用和两条读取路径之间的分页续读。
"""

from __future__ import annotations

import ast
import base64
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOL_RESULTS = "harness/src/boss_harness/tool_results.py"
APPLICATION = "harness/src/boss_harness/application.py"
MODEL_TOOLS = "harness/src/boss_harness/model_tools.py"
RPC = "harness/src/boss_harness/rpc.py"
EXPECTED_CONSTANTS = {
    "MAX_INLINE_TOOL_RESULT_BYTES": 64 * 1024,
    "MAX_PAGE_BYTES": 1024 * 1024,
    "DEFAULT_RESULT_CHARS": 16_384,
    "MAX_RESULT_CHARS": 32_768,
    "MODEL_RESULT_READ_CHARS": 8_192,
}
TOOL_RESULTS_FRAGMENTS = (
    'if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:',
    're.fullmatch(r"[a-f0-9]{64}", sha256) is None',
    '"code": "STALE_RESULT", "currentRef": reference',
    'not cursor.startswith("tr1_") or len(cursor) > 2048',
    'value[:3] != [thread_id, item_id, reference["sha256"]]',
    'or type(value[3]) is not int or not 0 <= value[3] < len(text)',
    'if len(text.encode("utf-8", "surrogatepass")) > MAX_INLINE_TOOL_RESULT_BYTES:',
    '"nextCursor": _cursor(reference, end) if end < len(text) else None',
)
APPLICATION_FRAGMENTS = (
    'if set(params) - {"threadId", "itemId", "sha256", "cursor", "limit"}:',
    'if item.get("kind") != "toolCall" or not isinstance(item.get("result"), dict):',
)
MODEL_TOOLS_FRAGMENTS = (
    '"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},',
    '"additionalProperties": False,',
    'limit=arguments.get("limit", MODEL_RESULT_READ_CHARS))',
    'error["currentRef"] = current_ref',
    '"code": code if isinstance(code, str) else "RESULT_READ_FAILED",',
)
RPC_DEFAULT = re.compile(
    r'def on_tool_result_read\(.*?return read_result_chunk\(.*?limit=params\.get\("limit",\s*([\d_]+)\)',
    re.DOTALL,
)

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.rpc import RpcError  # noqa: E402
from boss_harness.tool_results import (  # noqa: E402
    MAX_INLINE_TOOL_RESULT_BYTES,
    MAX_PAGE_BYTES,
    TOOL_EXECUTION_STATES,
    canonical_result_text,
    disposition_for_state,
    project_item,
    read_result_chunk,
    read_result_text_chunk,
    result_reference,
    result_text,
    tool_disposition,
    tool_execution_state,
    wire_size,
)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"工具结果行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_raises(call, label: str) -> int:
    try:
        call()
    except ValueError:
        return 1
    except RpcError as error:
        raise ValueError(f"工具结果行为变化 {label}：收到 RPC 错误 {error.code}") from None
    raise ValueError(f"工具结果行为变化 {label}：没有抛出 ValueError")


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    values: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value
    return values


def _int_expression(node: ast.expr, values: dict[str, ast.expr],
                    seen: frozenset[str] = frozenset()) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_expression(node.left, values, seen) * _int_expression(node.right, values, seen)
    if isinstance(node, ast.Name) and node.id not in seen and node.id in values:
        return _int_expression(values[node.id], values, seen | {node.id})
    raise ValueError("工具结果常量必须是正整数乘积表达式")


def _frame_limit() -> int:
    try:
        tree = ast.parse(_read(RPC))
    except SyntaxError:
        raise ValueError(f"无法解析 {RPC}") from None
    values = _assigned(tree)
    if "MAX_FRAME_BYTES" not in values:
        raise ValueError(f"{RPC} 缺少 MAX_FRAME_BYTES")
    return _int_expression(values["MAX_FRAME_BYTES"], values)


def _missing(fragments: tuple[str, ...], text: str) -> list[str]:
    return [fragment for fragment in fragments if fragment not in text]


def _behavior_checks() -> int:
    checked = 0
    # 执行状态：九个合法值原样返回，其余一律 None，不猜测近似状态。
    states = {"queued", "pending_approval", "approved", "not_approved", "executing",
              "completed", "failed", "not_executed", "outcome_unknown"}
    checked += _expect_value(TOOL_EXECUTION_STATES, frozenset(states), "执行状态集合")
    checked += _expect_value(
        [tool_execution_state(state) for state in sorted(states)],
        sorted(states), "执行状态原样返回")
    checked += _expect_value(
        [tool_execution_state(value) for value in
         ("running", "COMPLETED", "", None, 1, ["completed"])],
        [None] * 6, "执行状态非法值")
    # 重试处置：只保留 delivery / retry 两个合法字段，多余字段丢弃。
    checked += _expect_value(
        tool_disposition({"delivery": "unknown", "retry": "unsafe", "extra": 1}),
        {"delivery": "unknown", "retry": "unsafe"}, "处置字段清洗")
    checked += _expect_value(
        [tool_disposition(value) for value in (
            {}, {"delivery": "unknown"}, {"delivery": "delivered", "retry": "safe"},
            {"delivery": "unknown", "retry": "yes"}, ["unknown"], None)],
        [None] * 6, "处置非法值")
    # 状态→处置矩阵：终态事实决定重试安全，写操作失败不得被当成可安全重试。
    for state, expected, label in (
        ("not_executed", {"delivery": "not_delivered", "retry": "safe"}, "未执行处置"),
        ("not_approved", {"delivery": "not_delivered", "retry": "safe"}, "未批准处置"),
        ("outcome_unknown", {"delivery": "delivery_uncertain", "retry": "unsafe"},
         "结果不确定处置"),
    ):
        checked += _expect_value(
            [disposition_for_state(state, write=write) for write in (True, False)],
            [expected] * 2, label)
    checked += _expect_value(
        disposition_for_state("failed", write=True),
        {"delivery": "unknown", "retry": "unknown"}, "写失败处置")
    checked += _expect_value(
        disposition_for_state("failed", write=False),
        {"delivery": "not_delivered", "retry": "safe"}, "读失败处置")
    checked += _expect_value(
        [disposition_for_state(state, write=False) for state in
         ("completed", "executing", "queued", "approved", "pending_approval", None, "bogus")],
        [None] * 7, "非终态处置")
    # 结果拼写：紧凑分隔符、保留插入顺序、非 ASCII 原样输出、非有限浮点拒绝。
    checked += _expect_value(
        result_text({"b": 1, "a": "中"}), '{"b":1,"a":"中"}', "紧凑 JSON 拼写")
    checked += _expect_value(result_text([1, None, True]), "[1,null,true]", "标量拼写")
    checked += _expect_raises(lambda: result_text(float("nan")), "NaN 拒绝")
    # 内容寻址：SHA-256 取 UTF-8 字节，长度分别按字节与码点记录。
    text = "中文"
    checked += _expect_value(
        result_reference("thread", "item", text),
        {"threadId": "thread", "itemId": "item", "encoding": "json",
         "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
         "byteLength": 6, "characterLength": 2}, "引用字段")
    # 孤立代理项按 surrogatepass 编码摘要，写入路径与读取路径对同一文本一致。
    surrogate = result_reference("thread", "item", "\ud800")
    checked += _expect_value(
        (surrogate["sha256"], surrogate["byteLength"], surrogate["characterLength"]),
        (hashlib.sha256(b"\xed\xa0\x80").hexdigest(), 3, 1), "代理项摘要")
    # 规范化拼写：干净值等同严格拼写；受损记录降级为可传输文本。
    checked += _expect_value(
        canonical_result_text({"ok": True}), result_text({"ok": True}), "干净值规范化")
    checked += _expect_value(
        canonical_result_text({"s": "\ud800"}), '{"s":"�"}', "代理项降级")
    checked += _expect_value(
        canonical_result_text({"n": float("nan")}), '{"n":null}', "非有限浮点降级")
    # wire 预算：JSON 字节数加 512 帧余量；不可编码值按超过任何单页预算处理。
    checked += _expect_value(wire_size({"a": 1}), 520, "wire 预算")
    checked += _expect_value(wire_size({"a": "中"}), 524, "wire 非 ASCII 预算")
    checked += _expect_value(wire_size("\ud800"), MAX_PAGE_BYTES + 1, "wire 代理项超限")
    checked += _expect_raises(lambda: wire_size(float("nan")), "wire 非有限浮点拒绝")
    # 内联上限：JSON 对象结构占 11 字节，恰好 64 KiB 时保留完整结果。
    exact = {"id": "item-1", "kind": "toolCall", "status": "completed",
             "result": {"text": "x" * (MAX_INLINE_TOOL_RESULT_BYTES - 11)}}
    projected = project_item("thread", deepcopy(exact))
    checked += _expect_value(projected == exact, True, "恰好上限内联")
    # 每个「中」占 3 字节，结果比上限多 1 字节，码点数仍低于上限。
    over = {"id": "item-1", "kind": "toolCall", "status": "failed", "modelResult": "x",
            "errorCode": "e" * 200, "recoveryAction": "r" * 1200,
            "resultSummary": "s" * 5000,
            "result": {"text": "中" * ((MAX_INLINE_TOOL_RESULT_BYTES - 10) // 3)}}
    original = deepcopy(over)
    projected = project_item("thread", over)
    text = canonical_result_text(original["result"])
    encoded = text.encode("utf-8", "surrogatepass")
    reference = projected.get("resultRef", {})
    checked += _expect_value(
        (sorted(projected), projected.get("resultOmitted"), projected.get("result")),
        (["errorCode", "id", "kind", "recoveryAction", "resultOmitted", "resultRef",
          "resultSummary", "status"], True, None), "超限省略")
    checked += _expect_value(
        (reference.get("threadId"), reference.get("itemId"), reference.get("encoding"),
         reference.get("sha256"), reference.get("byteLength"),
         reference.get("characterLength")),
        ("thread", "item-1", "json", hashlib.sha256(encoded).hexdigest(),
         len(encoded), len(text)), "超限引用")
    checked += _expect_value(
        (len(projected.get("errorCode", "")), len(projected.get("recoveryAction", "")),
         len(projected.get("resultSummary", ""))), (128, 1000, 4000), "固定字段截断")
    checked += _expect_value(over == original, True, "保留输入条目")
    return checked


def _pagination_checks() -> int:
    thread_id, item_id = "thread", "item-1"
    item = {"id": item_id, "kind": "toolCall", "result": {"text": "中🙂\ud800A"}}
    text = '{"text":"中🙂�A"}'
    reference = result_reference(thread_id, item_id, text)
    digest = reference["sha256"]
    read_item = partial(read_result_chunk, thread_id, item, sha256=digest)
    read_text = partial(read_result_text_chunk, thread_id, item_id, text, sha256=digest)

    # 在两个读取入口之间交替使用同一个结果的游标。
    first = read_item(limit=10)
    first_cursor = first["nextCursor"]
    checked = _expect_value(
        (first["text"], first["offset"], first["resultRef"]),
        ('{"text":"中', 0, reference), "分页首段")
    checked += _expect_value(
        isinstance(first_cursor, str) and first_cursor.startswith("tr1_"), True, "首段游标")
    second = read_text(cursor=first_cursor, limit=2)
    second_cursor = second["nextCursor"]
    checked += _expect_value(
        (second["text"], second["offset"], second["resultRef"]),
        ("🙂�", 10, reference), "文本入口续页")
    last = read_item(cursor=second_cursor, limit=EXPECTED_CONSTANTS["MAX_RESULT_CHARS"])
    checked += _expect_value(last, {
        "text": 'A"}', "offset": 12, "resultRef": reference, "nextCursor": None,
    }, "条目入口末页")
    checked += _expect_value(first["text"] + second["text"] + last["text"], text, "拼回全文")

    # limit 最小值可用；布尔值也必须被拒绝。
    for route, read in (("条目", read_item), ("文本", read_text)):
        checked += _expect_value(read(limit=1)["text"], "{", f"{route}入口最小 limit")
        for limit in (0, EXPECTED_CONSTANTS["MAX_RESULT_CHARS"] + 1, True, "2"):
            checked += _expect_raises(partial(read, limit=limit), f"{route}入口 limit {limit!r}")
        try:
            read(sha256="0" * 64)
        except RpcError as error:
            checked += _expect_value(
                (error.code, error.data), (-32011, {"code": "STALE_RESULT", "currentRef": reference}),
                f"{route}入口返回当前引用")
        else:
            raise ValueError(f"工具结果行为变化 {route}入口接受过期引用")

    changed_text = '{"text":"内容已更新"}'
    changed_ref = result_reference(thread_id, item_id, changed_text)
    for label, read in (
        ("会话不匹配", partial(read_result_chunk, "other-thread", item, sha256=digest)),
        ("条目不匹配", partial(read_result_chunk, thread_id, {**item, "id": "other-item"}, sha256=digest)),
        ("摘要不匹配", partial(read_result_text_chunk, thread_id, item_id, changed_text,
                              sha256=changed_ref["sha256"])),
    ):
        checked += _expect_raises(partial(read, cursor=first_cursor), label)
    # 给可解码的游标增加 JSON 末尾空白，单独触发长度边界。
    cursor_data = json.dumps([thread_id, item_id, digest, 1]).encode("ascii")
    padded = base64.urlsafe_b64encode(cursor_data + b" " * 2048).decode("ascii").rstrip("=")
    for label, cursor in (
        ("空游标", ""),
        ("游标前缀", "tr0_" + first_cursor[4:]),
        ("游标 Base64 格式", first_cursor + "!!!!"),
        ("游标长度", "tr1_" + padded),
    ):
        checked += _expect_raises(partial(read_text, cursor=cursor), label)

    # 用合成记录核对偏移字段的类型和范围。
    for offset in (-1, len(text), len(text) + 1, True, 1.0):
        data = json.dumps([thread_id, item_id, digest, offset]).encode("ascii")
        cursor = "tr1_" + base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
        checked += _expect_raises(partial(read_text, cursor=cursor), f"游标偏移 {offset!r}")
    checked += _expect_raises(partial(read_item, sha256=digest.upper()), "条目入口摘要格式")
    for label, overrides in (("非工具条目", {"kind": "agentMessage"}), ("缺少对象结果", {"result": None})):
        checked += _expect_raises(
            partial(read_result_chunk, thread_id, {**item, **overrides}, sha256=digest), label)
    return checked


def check_tool_results() -> tuple[int, int, int]:
    try:
        values = _assigned(ast.parse(_read(TOOL_RESULTS)))
    except SyntaxError:
        raise ValueError(f"无法解析 {TOOL_RESULTS}") from None
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in values:
            raise ValueError(f"tool_results.py 缺少常量 {name}")
        try:
            actual = _int_expression(values[name], values)
        except ValueError:
            raise ValueError(f"tool_results.py 的 {name} 必须是正整数乘积表达式") from None
        if actual != expected:
            raise ValueError(f"tool_results.py 的 {name} 必须是 {expected}，实际为 {actual}")
    if not 0 < EXPECTED_CONSTANTS["MODEL_RESULT_READ_CHARS"] <= EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"]:
        raise ValueError("模型读取上限不得超过 RPC 默认分段")
    if EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"] > EXPECTED_CONSTANTS["MAX_RESULT_CHARS"]:
        raise ValueError("RPC 默认分段不得超过最大分段")
    if EXPECTED_CONSTANTS["MAX_INLINE_TOOL_RESULT_BYTES"] >= EXPECTED_CONSTANTS["MAX_PAGE_BYTES"]:
        raise ValueError("内联结果上限必须小于单页预算")
    if EXPECTED_CONSTANTS["MAX_PAGE_BYTES"] >= _frame_limit():
        raise ValueError("工具结果单页预算必须小于 JSON-RPC 帧上限")

    tool_results = _read(TOOL_RESULTS)
    application = _read(APPLICATION)
    model_tools = _read(MODEL_TOOLS)
    missing = _missing(TOOL_RESULTS_FRAGMENTS, tool_results)
    if missing:
        raise ValueError("tool_results.py 的分页与引用边界缺少：" + "、".join(missing))
    missing = _missing(APPLICATION_FRAGMENTS, application)
    if missing:
        raise ValueError("application.py 的工具结果读取边界缺少：" + "、".join(missing))
    missing = _missing(MODEL_TOOLS_FRAGMENTS, model_tools)
    if missing:
        raise ValueError("model_tools.py 的模型读取边界缺少：" + "、".join(missing))

    defaults = RPC_DEFAULT.findall(application)
    if len(defaults) != 1:
        raise ValueError("application.py 的工具结果 RPC 默认分段必须唯一")
    if int(defaults[0].replace("_", "")) != EXPECTED_CONSTANTS["DEFAULT_RESULT_CHARS"]:
        raise ValueError("工具结果 RPC 默认分段与 DEFAULT_RESULT_CHARS 不一致")
    if tool_results.count('if type(limit) is not int or not 1 <= limit <= MAX_RESULT_CHARS:') < 2:
        raise ValueError("两条工具结果读取路径都必须校验 limit")
    if model_tools.count('"limit": {"type": "integer", "minimum": 1, "maximum": MODEL_RESULT_READ_CHARS},') != 2:
        raise ValueError("模型读取 schema 与工具描述必须一致使用 MODEL_RESULT_READ_CHARS")

    guards = (len(TOOL_RESULTS_FRAGMENTS) + len(APPLICATION_FRAGMENTS)
              + len(MODEL_TOOLS_FRAGMENTS) + 3)
    return len(EXPECTED_CONSTANTS), guards, _behavior_checks() + _pagination_checks()


def main() -> int:
    try:
        constants, guards, behaviors = check_tool_results()
    except ValueError as error:
        print(f"工具结果边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具结果边界一致：{constants} 个常量、{guards} 项分页与引用防护、"
          f"{behaviors} 项行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
