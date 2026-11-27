#!/usr/bin/env python3
"""对照内核消息搜索的扫描、预算与截断口径。

`SessionStore.search_messages` 是有界全文搜索入口：会话数 / 文本预算、超大
会话跳过、读取失败标记不完整、逐条消息预算、工具调用文本投影、跨分支命中
标记，以及 `limit` / 单会话上限 / 更多命中三处截断都在这里。`_search_tool_text`
决定工具调用以什么文本进入搜索。本脚本直接导入 `_search_tool_text` 做行为
对照，并扫描 `search_messages` 的扫描与截断结构；它不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore  # noqa: E402

TOOL_TEXT = SessionStore._search_tool_text

SEARCH_ORDER = (
    "def search_messages(self, query: str, *, limit: int = 30, include_archived: bool = False) -> dict:",
    'if not isinstance(query, str) or not query.strip() or len(query) > 200:',
    'raise ValueError("query 必须是非空字符串（最多 200 字符）")',
    "if type(limit) is not int or not 1 <= limit <= 50:",
    'raise ValueError("limit 必须是 1–50 的整数")',
    "if type(include_archived) is not bool:",
    'raise ValueError("includeArchived 必须是布尔值")',
    "needle, _, _ = self._search_normalized(query.strip())",
    "if not needle:",
    'return {"query": query.strip(), "matches": [], "truncated": False}',
    "for thread in self.list_threads(include_archived=include_archived):",
    "if scanned_threads >= _SEARCH_THREADS or scanned_chars >= _SEARCH_TEXT_BUDGET:",
    'if self.path_for(thread["id"]).stat().st_size > _SEARCH_THREAD_BYTES:',
    'entries = self.read_entries(thread["id"])',
    'items = self._project_items(thread["id"], entries)',
    'if any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):',
    'branch_item_ids = {str(item.get("id") or "")',
    "for item in self._project_items(thread[\"id\"],",
    "self._active_entries(entries)",
    "except ValueError:",
    "except (OSError, ValueError):",
    "scanned_threads += 1",
    "for item in items:",
    "if scanned_chars >= _SEARCH_TEXT_BUDGET:",
    'kind = item.get("kind")',
    'if kind == "toolCall":',
    'text, role = self._search_tool_text(item), "tool"',
    'elif kind in ("userMessage", "agentMessage") and isinstance(item.get("text"), str) and item["text"]:',
    'text, role = item["text"], "user" if kind == "userMessage" else "agent"',
    "remaining = _SEARCH_TEXT_BUDGET - scanned_chars",
    "if len(text) > remaining:",
    "text = text[:remaining]",
    "scanned_chars += len(text)",
    "normalized, starts, ends = self._search_normalized(text)",
    "index = normalized.find(needle)",
    "if index < 0:",
    "if len(matches) >= limit or per_thread >= _SEARCH_PER_THREAD:",
    "more_matches = True",
    "if starts is None:",
    "start, end = index, index + len(needle)",
    "start = starts[index]",
    "end = ends[index + len(needle) - 1]",
    '"snippet": self._search_snippet(text, start, end),',
    "if branch_item_ids is not None:",
    'match["onBranch"] = item_id in branch_item_ids',
    "matches.append(match)",
    "per_thread += 1",
    "if more_matches or scanned_chars >= _SEARCH_TEXT_BUDGET:",
    'return {"query": query.strip(), "matches": matches[:_SEARCH_MATCHES], "truncated": truncated}',
)
TOOL_ORDER = (
    'name = item.get("toolName")',
    "if not isinstance(name, str) or not name.strip():",
    'return ""',
    "parts = [name.strip()]",
    'source = item.get("source")',
    'reference = source.get("ref") if isinstance(source, dict) else None',
    "if isinstance(reference, str) and reference.strip():",
    "parts.append(reference.strip())",
    'arguments = item.get("toolArguments")',
    "if isinstance(arguments, dict):",
    'rendered = json.dumps(arguments, ensure_ascii=False, sort_keys=True)',
    "except (TypeError, ValueError, RecursionError):",
    "if rendered and len(rendered) <= _SEARCH_TOOL_ARGS:",
    "parts.append(rendered)",
    'summary = item.get("resultSummary")',
    "if isinstance(summary, str) and summary:",
    "parts.append(summary)",
    'return "\\n".join(parts)[:_SEARCH_TOOL_TEXT]',
)


def _deep_tool_arguments(depth: int = 1000) -> dict:
    """构造旧解释器会在 json.dumps 中抛 RecursionError 的参数。"""
    root: dict = {}
    cursor = root
    for _ in range(depth):
        child: dict = {}
        cursor["x"] = child
        cursor = child
    return root


TOOL_CASES = (
    ({}, ""),
    ({"toolName": ""}, ""),
    ({"toolName": "   "}, ""),
    ({"toolName": " boss_hr_greet "}, "boss_hr_greet"),
    ({"toolName": "t", "source": {"ref": " ref-1 "}}, "t\nref-1"),
    ({"toolName": "t", "source": {"ref": ""}}, "t"),
    ({"toolName": "t", "source": "ref"}, "t"),
    ({"toolName": "t", "toolArguments": {"b": 1, "a": 2}}, 't\n{"a": 2, "b": 1}'),
    ({"toolName": "t", "toolArguments": {"q": "招聘"}}, 't\n{"q": "招聘"}'),
    ({"toolName": "t", "toolArguments": {"o": object()}}, "t"),
    ({"toolName": "t", "toolArguments": {1, 2}}, "t"),
    ({"toolName": "t", "toolArguments": [1]}, "t"),
    ({"toolName": "t", "toolArguments": {}}, "t\n{}"),
    ({"toolName": "t", "resultSummary": 3}, "t"),
    ({"toolName": "t", "resultSummary": "s"}, "t\ns"),
    ({"toolName": "t", "source": {"ref": "r"}, "toolArguments": {"a": 1}, "resultSummary": "s"},
     't\nr\n{"a": 1}\ns'),
    ({"toolName": "t", "toolArguments": {"q": "x" * 1991}}, 't\n{"q": "' + "x" * 1991 + '"}'),
    ({"toolName": "t", "toolArguments": {"q": "x" * 1992}}, "t"),
    ({"toolName": "t", "toolArguments": _deep_tool_arguments()}, "t"),
    ({"toolName": "t", "resultSummary": "x" * 7000}, "t\n" + "x" * 5998),
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_search_scan() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    search = _method(tree, source, "SessionStore", "search_messages")
    tool = _method(tree, source, "SessionStore", "_search_tool_text")
    checked = _ordered(SEARCH_ORDER, search, SESSION)
    # 三类查询校验各报一条错误，最终由扫描侧兜底。
    if search.count("raise ValueError(") != 3:
        raise ValueError(f"{SESSION} 的消息搜索必须有三处入参校验")
    checked += 1
    # 七处截断：会话 / 文本预算、超大会话、读取失败、消息预算、单条截断、展示上限、末尾兜底。
    if search.count("truncated = True") != 7:
        raise ValueError(f"{SESSION} 的消息搜索必须有七处截断标记")
    checked += 1
    if search.count("_SEARCH_TEXT_BUDGET") != 4 or search.count("_SEARCH_THREADS") != 1:
        raise ValueError(f"{SESSION} 的消息搜索必须保留会话与文本预算")
    checked += 1
    if search.count("_SEARCH_THREAD_BYTES") != 1 or search.count("_SEARCH_MATCHES") != 1:
        raise ValueError(f"{SESSION} 的消息搜索必须保留会话大小与展示上限")
    checked += 1
    if search.count("_SEARCH_PER_THREAD") != 1:
        raise ValueError(f"{SESSION} 的消息搜索必须保留单会话上限")
    checked += 1
    # 分支标记来自当前分支投影，投影失败时省略字段。
    if search.count('branch_item_ids = {str(item.get("id") or "")') != 1 or search.count("onBranch") != 1:
        raise ValueError(f"{SESSION} 的消息搜索必须标注跨分支命中")
    checked += 1
    if search.count("self._active_entries(entries)") != 1:
        raise ValueError(f"{SESSION} 的分支标记必须来自当前分支投影")
    checked += 1
    # 读取失败与超大会话都按不完整结果处理。
    if search.count("except (OSError, ValueError):") != 1 or search.count("truncated = True") != 7:
        raise ValueError(f"{SESSION} 的读取失败必须标记不完整")
    checked += 1
    # 数据来源：线程列表、条目读取、条目投影各一次。
    if (search.count("self.list_threads(include_archived=include_archived)") != 1
            or search.count('self.read_entries(thread["id"])') != 1
            or search.count('self._project_items(thread["id"], entries)') != 1):
        raise ValueError(f"{SESSION} 的消息搜索必须经线程列表与条目投影")
    checked += 1
    # 工具文本只走 _search_tool_text，正文只走消息 text。
    if search.count("self._search_tool_text(item)") != 1 or search.count("self._search_normalized(text)") != 1:
        raise ValueError(f"{SESSION} 的消息搜索必须复用工具投影与归一化入口")
    checked += 1
    if search.count("self._search_snippet(text, start, end)") != 1:
        raise ValueError(f"{SESSION} 的命中片段必须由归一化索引映射")
    checked += 1
    if search.count("break") != 4 or search.count("continue") != 5:
        raise ValueError(f"{SESSION} 的消息搜索循环必须保留预算与跳过分支")
    checked += 1
    # 返回前必须按展示上限截断，不能返回未截断列表。
    if '"matches": matches,' in search:
        raise ValueError(f"{SESSION} 的消息搜索必须截断展示结果")
    checked += 1
    checked += _ordered(TOOL_ORDER, tool, SESSION)
    # 工具文本：名称、来源、参数、摘要各只追加一次；参数长度有上限。
    if tool.count("parts.append(") != 3 or tool.count('return ""') != 1:
        raise ValueError(f"{SESSION} 的工具文本必须按名称、来源、参数、摘要组装")
    checked += 1
    if tool.count("json.dumps") != 1 or tool.count("ensure_ascii=False") != 1 or tool.count("sort_keys=True") != 1:
        raise ValueError(f"{SESSION} 的工具参数必须稳定排序且不转义非 ASCII")
    checked += 1
    if tool.count("_SEARCH_TOOL_ARGS") != 1 or tool.count("_SEARCH_TOOL_TEXT") != 1:
        raise ValueError(f"{SESSION} 的工具文本必须保留参数与文本上限")
    checked += 1
    if "raise" in tool:
        raise ValueError(f"{SESSION} 的工具文本不得抛出错误")
    checked += 1
    # 行为对照：逐用例比较工具投影文本；失败只报序号，不打印深层对象。
    for index, (item, expected) in enumerate(TOOL_CASES):
        actual = TOOL_TEXT(item)
        if actual != expected:
            raise ValueError(
                f"{SESSION} 的工具文本变化：用例 {index}，期望 {expected!r}，实际 {actual!r}")
        checked += 1
    if len(TOOL_TEXT({"toolName": "t", "resultSummary": "x" * 7000})) != 6000:
        raise ValueError(f"{SESSION} 的工具文本上限必须是 6000 字符")
    checked += 1
    return checked


def _documentation_check(checked: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    phrase = "深层嵌套参数在 Python 3.10–3.14 一致省略"
    if phrase not in reference or f"共 {checked} 项" not in reference:
        raise ValueError(
            f"{TECHNICAL_REFERENCE} 缺少搜索深度边界说明或计数：{phrase}，共 {checked} 项")


def main() -> int:
    try:
        checked = check_search_scan()
        _documentation_check(checked)
    except (ValueError, SyntaxError) as error:
        print(f"搜索扫描核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索扫描一致：{checked} 项预算、截断与工具投影校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
