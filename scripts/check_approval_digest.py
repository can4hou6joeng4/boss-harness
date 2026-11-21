#!/usr/bin/env python3
"""核对审批参数摘要的规范化、负载一致与索引往返。

`approval_parameters_digest` 把工具参数规范化为 SHA-256 摘要；`_prepare_tool`
把同一份 `arguments` 同时写入审批负载的 `params` 与 `paramsDigest`，并通过
`start_tool_call` 把参数写进条目的 `toolArguments`；`_index_thread` 再把摘要
持久化，`pending_approvals` 读回。规范化参数一旦变化，重启前后的摘要不一致，
已持久化的待审批会被 `_valid_approval_item` 判为无效而消失。这里按源码顺序
固定规范化、负载七字段与索引往返，要求只有一处摘要实现，并直接调用摘要函数
核对编码与错误收敛。
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
AGENT = "harness/src/boss_harness/agent.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import approval_parameters_digest  # noqa: E402

# 摘要规范化：精确 dict → 稳定键序、不转义非 ASCII、紧凑分隔符、拒绝非有限数 →
# 失败收敛为固定错误 → UTF-8 SHA-256 十六进制摘要。
DIGEST_ORDER = (
    "def approval_parameters_digest(arguments: dict[str, Any]) -> str:",
    "if type(arguments) is not dict:",
    'raise ValueError("审批参数必须是对象")',
    'encoded = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"),',
    'sort_keys=True, allow_nan=False).encode("utf-8")',
    "except (TypeError, ValueError, RecursionError):",
    'raise ValueError("审批参数无法规范化") from None',
    "return hashlib.sha256(encoded).hexdigest()",
)
# 工具调用记录：同一份参数进入 toolArguments，带审批时先记为待审批。
START_ORDER = (
    "payload: dict[str, Any] = {",
    '"kind": "toolCall",',
    '"toolArguments": arguments,',
    '"turnId": self.turn_id,',
    '"executionState": "pending_approval" if approval else "queued",',
)
# 审批负载：七个字段固定，params 与摘要来自同一变量，描述不回显参数。
PREPARE_ORDER = (
    '"approvalId": uuid.uuid4().hex,',
    '"toolName": name,',
    '"description": f"需要你批准后才会执行：{name}",',
    '"params": arguments,',
    '"paramsDigest": approval_parameters_digest(arguments),',
    '"consequential": True,',
    '"deadline": time.time() + self.approval_timeout,',
    "self.start_tool_call(thread_id, name, arguments, call_id, approval, batch_id,",
)
# 索引持久化：投影条目经校验后直接读取必填摘要，不做可选读取。
INDEX_ORDER = (
    "for item in self._project_items(thread_id, entries):",
    "if not self._valid_approval_item(item, pending_only=False):",
    'approval = item["approval"]',
    'connection.execute("""INSERT INTO approvals',
    'float(approval["deadline"]), approval["paramsDigest"], approval.get("decision"),',
)
# 待审批分页回读：摘要取自持久化列。
READ_ORDER = (
    '"paramsDigest": row["params_digest"]',
)
APPROVAL_KEYS = {
    "approvalId", "toolName", "description", "params",
    "paramsDigest", "consequential", "deadline",
}


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _approval_literal(tree: ast.Module) -> ast.Dict:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "approval":
                if isinstance(node.value, ast.Dict):
                    return node.value
    raise ValueError(f"{AGENT} 缺少 approval 字典字面量")


def _expect_value(actual: object, expected: object, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"审批参数摘要行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"审批参数摘要行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"审批参数摘要行为变化 {label}：期望 ValueError")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _behavior_checks() -> int:
    non_object = "审批参数必须是对象"
    unencodable = "审批参数无法规范化"
    checked = _expect_value(
        approval_parameters_digest({}), _sha("{}"), "空对象")
    checked += _expect_value(
        approval_parameters_digest({"b": 1, "a": 2}),
        approval_parameters_digest({"a": 2, "b": 1}), "键序稳定")
    checked += _expect_value(
        approval_parameters_digest({"o": {"b": 1, "a": 2}}),
        approval_parameters_digest({"o": {"a": 2, "b": 1}}), "嵌套键序稳定")
    checked += _expect_value(
        approval_parameters_digest({"a": 1, "b": [1, 2]}),
        _sha('{"a":1,"b":[1,2]}'), "紧凑分隔符")
    checked += _expect_value(
        approval_parameters_digest({"名": "值"}), _sha('{"名":"值"}'),
        "非 ASCII 不转义")
    checked += _expect_value(
        approval_parameters_digest({"t": True, "f": False, "n": None, "i": 7}),
        _sha('{"f":false,"i":7,"n":null,"t":true}'), "布尔与空值")
    checked += _expect_value(
        approval_parameters_digest({"v": 1.5}), _sha('{"v":1.5}'), "浮点表示")
    checked += _expect_value(
        approval_parameters_digest({"v": 9007199254740993}),
        _sha('{"v":9007199254740993}'), "大整数")
    checked += _expect_value(
        approval_parameters_digest({"v": (1, 2)}),
        approval_parameters_digest({"v": [1, 2]}), "元组转数组")
    checked += _expect_value(
        approval_parameters_digest({1: "a"}), _sha('{"1":"a"}'), "数字键转字符串")
    checked += _expect_value(
        approval_parameters_digest({"阿": 1, "a": 2}), _sha('{"a":2,"阿":1}'),
        "非 ASCII 键排序")
    checked += _expect_value(
        approval_parameters_digest({"a": 1}) != approval_parameters_digest({"a": 2}),
        True, "不同参数不同摘要")
    checked += _expect_value(
        approval_parameters_digest({"v": True}) != approval_parameters_digest({"v": 1}),
        True, "布尔与整数区分")
    first = approval_parameters_digest({"k": "v"})
    checked += _expect_value(len(first), 64, "摘要长度")
    checked += _expect_value(
        all(character in "0123456789abcdef" for character in first), True,
        "小写十六进制")

    checked += _expect_error(
        lambda: approval_parameters_digest([]), non_object, "拒绝列表")
    checked += _expect_error(
        lambda: approval_parameters_digest(None), non_object, "拒绝空值")
    checked += _expect_error(
        lambda: approval_parameters_digest("text"), non_object, "拒绝字符串")

    class Mapping(dict):
        pass

    checked += _expect_error(
        lambda: approval_parameters_digest(Mapping()), non_object, "拒绝字典子类")
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": float("nan")}), unencodable,
        "拒绝 NaN")
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": float("inf")}), unencodable,
        "拒绝 Infinity")
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": object()}), unencodable,
        "拒绝不可序列化值")
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": b"bytes"}), unencodable,
        "拒绝字节值")
    checked += _expect_error(
        lambda: approval_parameters_digest({1: "a", "b": 2}), unencodable,
        "拒绝混合键")
    cycle: dict[str, object] = {}
    cycle["self"] = cycle
    checked += _expect_error(
        lambda: approval_parameters_digest(cycle), unencodable, "拒绝循环引用")
    deep: list[object] = []
    cursor = deep
    for _ in range(10000):
        nested: list[object] = []
        cursor.append(nested)
        cursor = nested
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": deep}), unencodable, "拒绝超深嵌套")
    checked += _expect_error(
        lambda: approval_parameters_digest({"v": [float("nan")]}), unencodable,
        "拒绝嵌套 NaN")
    return checked


def check_approval_digest() -> int:
    session = _read(SESSION)
    agent = _read(AGENT)
    session_tree = ast.parse(session)
    agent_tree = ast.parse(agent)
    digest = _function(session_tree, session, "approval_parameters_digest")
    start = _function(agent_tree, agent, "start_tool_call")
    prepare = _function(agent_tree, agent, "_prepare_tool")
    index = _function(session_tree, session, "_index_thread")
    pending = _function(session_tree, session, "pending_approvals")
    checked = _ordered(DIGEST_ORDER, digest, SESSION)
    checked += _ordered(START_ORDER, start, AGENT)
    checked += _ordered(PREPARE_ORDER, prepare, AGENT)
    checked += _ordered(INDEX_ORDER, index, SESSION)
    checked += _ordered(READ_ORDER, pending, SESSION)
    # 规范化参数各出现一次，不得静默跳过无法序列化的值。
    for fragment in ('sort_keys=True', "allow_nan=False", "ensure_ascii=False",
                     'separators=(",", ":")', ".hexdigest()"):
        if digest.count(fragment) != 1:
            raise ValueError(f"{SESSION} 的审批参数摘要缺少稳定规范：{fragment}")
        checked += 1
    if "default=" in digest:
        raise ValueError(f"{SESSION} 的审批参数摘要不得静默转换无法序列化的值")
    checked += 1
    if "isinstance(arguments, dict)" in digest:
        raise ValueError(f"{SESSION} 的审批参数摘要必须用精确 dict 类型判断")
    checked += 1
    # 工具调用记录只写一份参数。
    if start.count('"toolArguments": arguments,') != 1:
        raise ValueError(f"{AGENT} 的工具调用必须只写一份参数")
    checked += 1
    # 审批负载的 params 与摘要必须来自同一变量，描述不回显参数。
    if prepare.count("approval_parameters_digest(arguments)") != 1:
        raise ValueError(f"{AGENT} 的审批摘要必须在负载内就地计算")
    checked += 1
    # 每个 params 字段都必须直接引用工具参数，不得另做拷贝或投影。
    params_lines = [line.strip() for line in prepare.splitlines() if '"params":' in line]
    if not params_lines or any(not line.startswith('"params": arguments,') for line in params_lines):
        raise ValueError(f"{AGENT} 的审批参数必须与工具参数一致")
    checked += 1
    if "{arguments}" in prepare or "{name} {arguments}" in prepare:
        raise ValueError(f"{AGENT} 的审批描述不得回显参数")
    checked += 1
    # 负载键集合必须恰好是七个字段。
    literal = _approval_literal(agent_tree)
    keys = {key.value for key in literal.keys if isinstance(key, ast.Constant)}
    if keys != APPROVAL_KEYS:
        raise ValueError(f"{AGENT} 的审批负载字段集合变化：{sorted(keys)}")
    checked += 1
    # paramsDigest 与 params 都必须以同名变量 arguments 引用摘要与参数。
    values = {key.value: value for key, value in zip(literal.keys, literal.values)
              if isinstance(key, ast.Constant)}
    params_value = values.get("params")
    if not isinstance(params_value, ast.Name) or params_value.id != "arguments":
        raise ValueError(f"{AGENT} 的 params 必须直接引用工具参数")
    checked += 1
    digest_value = values.get("paramsDigest")
    if (not isinstance(digest_value, ast.Call)
            or not isinstance(digest_value.func, ast.Name)
            or digest_value.func.id != "approval_parameters_digest"
            or len(digest_value.args) != 1
            or not isinstance(digest_value.args[0], ast.Name)
            or digest_value.args[0].id != "arguments"):
        raise ValueError(f"{AGENT} 的 paramsDigest 必须由同名参数计算")
    checked += 1
    # 索引持久化直接读必填摘要，不得回退可选读取。
    if index.count('approval["paramsDigest"]') != 1:
        raise ValueError(f"{SESSION} 的索引必须持久化条目摘要")
    checked += 1
    if 'approval.get("paramsDigest")' in index:
        raise ValueError(f"{SESSION} 的索引不得可选读取摘要")
    checked += 1
    if index.count('float(approval["deadline"])') != 1:
        raise ValueError(f"{SESSION} 的索引必须把截止时间转为数值")
    checked += 1
    # 摘要只有一处实现，代理不得自带哈希。
    if "hashlib" in agent or "sha256" in agent:
        raise ValueError(f"{AGENT} 不得维护第二份审批摘要实现")
    checked += 1
    return checked + _behavior_checks()


def main() -> int:
    try:
        checked = check_approval_digest()
    except (ValueError, SyntaxError) as error:
        print(f"审批参数摘要核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批参数摘要一致：{checked} 项规范化、负载、索引往返与行为对照")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
