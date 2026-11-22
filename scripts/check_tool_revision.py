#!/usr/bin/env python3
"""核对工具结果修订的恢复口径。

`SessionStore.append_tool_revision` 是工具结果从「不确定失败」恢复的唯一入口：
条目必须是带 `revises` 的 `toolCall`；首次追加走与 `append` 相同的写前 / 写后
索引刷新，成功返回 `(entry, False)`。失败后重新读取日志：同 id 内容不同为
`conflict`，已存在并 fsync 成功为 `durable`，仅存在但无法确认落盘为
`present_uncertain`，不存在为 `absent`；至多再追加一次，绝不在恢复路径重放
handler 或审批。检查核对源码顺序，并在临时会话中注入追加和同步故障，
验证实际返回值、写入次数和日志内容。
"""

from __future__ import annotations

import ast
from contextlib import nullcontext
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import Entry, SessionStore, ToolRevisionPersistenceError  # noqa: E402

SESSION = "harness/src/boss_harness/session.py"

REVISION_ORDER = (
    "def append_tool_revision(self, thread_id: str, entry: Entry) -> tuple[Entry, bool]:",
    "payload = entry.payload or {}",
    'if (entry.type != "item" or payload.get("kind") != "toolCall"',
    'or not isinstance(payload.get("revises"), str)):',
    'raise ValueError("工具结果修订格式无效")',
    "path = self.path_for(thread_id)",
    "expected = entry.to_dict()",
    'outcome = "absent"',
    "def inspect_and_sync() -> str:",
    "for line_number, line in enumerate(_iter_bounded_lines(",
    "current = _decode_session_record(line, line_number=line_number)",
    'if current.get("id") == entry.id:',
    "if current != expected:",
    'return "conflict"',
    'raise ToolRevisionPersistenceError("invalid") from exc',
    "if not found:",
    'return "absent"',
    'with path.open("r+b") as handle:',
    "os.fsync(handle.fileno())",
    'return "present_uncertain"',
    'return "durable"',
    "with self._lock, self._index.transaction() as connection:",
    "self._append_line(path, expected)",
    "return entry, False",
    "for attempt in range(2):",
    "outcome = inspect_and_sync()",
    'if outcome == "durable":',
    "return entry, True",
    'if outcome in {"conflict", "present_uncertain"}:',
    "raise ToolRevisionPersistenceError(outcome)",
    "if attempt == 0:",
    'if attempt == 1 or outcome != "absent":',
    "raise ToolRevisionPersistenceError(outcome) from last_error",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SessionStore":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SessionStore.{name}")


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
        raise ValueError(f"工具结果修订行为变化 {label}：期望 {expected!r}，实际 {actual!r}")


def _expect_outcome(store: SessionStore, thread_id: str, revision: Entry,
                    expected: bool | str, label: str) -> None:
    if isinstance(expected, bool):
        entry, recovered = store.append_tool_revision(thread_id, revision)
        _expect_value(entry, revision, f"{label}返回条目")
        _expect_value((type(recovered), recovered), (bool, expected), f"{label}恢复标记")
        return
    try:
        store.append_tool_revision(thread_id, revision)
    except ToolRevisionPersistenceError as error:
        _expect_value(error.outcome, expected, f"{label}失败分类")
        if expected == "absent":
            _expect_value(str(error.__cause__), "模拟追加故障 2", f"{label}最后一次错误")
    else:
        raise ValueError(f"{label}应报告持久化错误 {expected}")


def _behavior_case(root: Path, label: str, steps: tuple[str, ...],
                   outcome: bool | str, saved: str) -> None:
    store = SessionStore(root / "sessions")
    thread_id = store.create(label)["id"]
    path = store.path_for(thread_id)
    header = path.read_bytes()
    revision = Entry("item", payload={"kind": "toolCall", "revises": "original", "result": "结果"})
    row = revision.to_dict()
    conflict = {**row, "payload": {**row["payload"], "result": "冲突"}}
    damaged_line = b"{\n"
    append = store._append_line
    remaining = iter(enumerate(steps, start=1))

    def append_step(target: Path, value: dict) -> None:
        attempt, step = next(remaining)
        if step in {"write", "after"}:
            append(target, value)
        elif step == "conflict":
            append(target, conflict)
        elif step == "invalid":
            with target.open("ab") as handle:
                handle.write(damaged_line)
        if step != "write":
            raise OSError(f"模拟追加故障 {attempt}")

    sync = nullcontext()
    if outcome == "present_uncertain":
        # 先留下已写入的行，再让恢复时对该行的同步失败。
        store.append(thread_id, revision)
        sync = patch("boss_harness.session.os.fsync", side_effect=OSError("模拟同步故障"))
    with patch.object(store, "_append_line", side_effect=append_step) as writer, sync as fsync:
        _expect_outcome(store, thread_id, revision, outcome, label)
        _expect_value(writer.call_count, len(steps), f"{label}追加次数")
        if fsync is not None:
            _expect_value(fsync.call_count, 1, f"{label}同步次数")
    if saved == "invalid":
        _expect_value(path.read_bytes(), header + damaged_line, f"{label}日志内容")
    else:
        records = {"empty": [], "revision": [row], "conflict": [conflict]}[saved]
        _expect_value(store.read_entries(thread_id), records, f"{label}日志条目")


def _behavior_checks() -> int:
    cases = (
        ("首次追加", ("write",), False, "revision"),
        ("写入前失败后重试", ("before", "write"), True, "revision"),
        ("首次写入后失败", ("after",), True, "revision"),
        ("重试写入后失败", ("before", "after"), True, "revision"),
        ("同编号内容冲突", ("conflict",), "conflict", "conflict"),
        ("重试写入后产生冲突", ("before", "conflict"), "conflict", "conflict"),
        ("首次追加后发现损坏日志", ("invalid",), "invalid", "invalid"),
        ("重试后无法核对日志", ("before", "invalid"), "uncertain", "invalid"),
        ("同步已有条目失败", ("before",), "present_uncertain", "revision"),
        ("两次写入均失败", ("before", "before"), "absent", "empty"),
    )
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for index, (label, steps, outcome, saved) in enumerate(cases):
            _behavior_case(root / str(index), label, steps, outcome, saved)
    return len(cases)


def check_tool_revision() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    revision = _method(tree, source, "append_tool_revision")
    checked = _ordered(REVISION_ORDER, revision, SESSION)
    # 恢复入口只做持久化核对，不得重放执行或审批。
    if revision.count("handler") != 1 or revision.count("approval") != 1:
        raise ValueError(f"{SESSION} 的工具结果修订只能在说明中提及 handler 与 approval")
    checked += 1
    if "self.append(" in revision or "append_many" in revision:
        raise ValueError(f"{SESSION} 的工具结果修订必须走内部追加")
    checked += 1
    # 首次追加一次；至多重试一次，共两次写入机会。
    if revision.count("self._append_line(path, expected)") != 2:
        raise ValueError(f"{SESSION} 的工具结果修订至多追加两次")
    checked += 1
    if revision.count("for attempt in range(2):") != 1 or "range(3)" in revision:
        raise ValueError(f"{SESSION} 的工具结果修订至多重试一轮")
    checked += 1
    # 索引刷新：首次写前 / 写后、durable 与重试成功后各一次。
    if revision.count("self._index_thread(thread_id, connection)") != 4:
        raise ValueError(f"{SESSION} 的工具结果修订必须在每次确认后刷新索引")
    checked += 1
    if revision.count('return entry, False') != 1 or revision.count("return entry, True") != 3:
        raise ValueError(f"{SESSION} 的工具结果修订必须区分首次写入与恢复")
    checked += 1
    # inspect_and_sync：一次定义、两次调用（主路径与异常路径）。
    if revision.count("inspect_and_sync()") != 3:
        raise ValueError(f"{SESSION} 的工具结果修订必须在主路径与异常路径各核对一次")
    checked += 1
    if revision.count('if outcome == "durable":') != 2:
        raise ValueError(f"{SESSION} 的工具结果修订必须在两条路径各处理一次 durable")
    checked += 1
    if revision.count('if outcome in {"conflict", "present_uncertain"}:') != 2:
        raise ValueError(f"{SESSION} 的工具结果修订必须在两条路径拒绝冲突与不确定结果")
    checked += 1
    if revision.count('outcome = "uncertain"') != 1:
        raise ValueError(f"{SESSION} 的工具结果修订必须把二次核对失败标为 uncertain")
    checked += 1
    # 冲突与不确定一律抛持久化错误；invalid 只在解码失败时产生。
    if revision.count("ToolRevisionPersistenceError(") != 5:
        raise ValueError(f"{SESSION} 的工具结果修订必须用固定异常报告五类失败")
    checked += 1
    if revision.count('raise ToolRevisionPersistenceError("invalid") from exc') != 1:
        raise ValueError(f"{SESSION} 的损坏日志必须报告 invalid")
    checked += 1
    if revision.count("raise ToolRevisionPersistenceError(outcome) from last_error") != 2:
        raise ValueError(f"{SESSION} 的重试耗尽必须附带最后一次错误")
    checked += 1
    if revision.count("except ToolRevisionPersistenceError:\n                raise") != 1:
        raise ValueError(f"{SESSION} 的持久化错误不得被重试循环吞掉")
    checked += 1
    if revision.count("except Exception as exc:") != 2:
        raise ValueError(f"{SESSION} 的首次追加与重试循环必须分别捕获失败")
    checked += 1
    # durable 确认：只读打开并 fsync 已有行，不得重写。
    if revision.count("os.fsync(") != 1 or revision.count('path.open("r+b")') != 1:
        raise ValueError(f"{SESSION} 的 durable 确认必须 fsync 已有日志")
    checked += 1
    if revision.count('if current.get("id") == entry.id:') != 1:
        raise ValueError(f"{SESSION} 的恢复核对必须按 id 定位已有结果")
    checked += 1
    if revision.count("if current != expected:") != 1:
        raise ValueError(f"{SESSION} 的恢复核对必须比对完整条目")
    checked += 1
    # durable 与重试成功都先刷新索引再返回。
    if revision.count('if outcome == "durable":\n                        self._index_thread(thread_id, connection)\n                        return entry, True') != 1:
        raise ValueError(f"{SESSION} 的 durable 恢复必须在刷新索引后返回")
    checked += 1
    if revision.count('if attempt == 0:\n                        self._append_line(path, expected)\n                        self._index_thread(thread_id, connection)\n                        return entry, True') != 1:
        raise ValueError(f"{SESSION} 的唯一重试必须在刷新索引后返回")
    checked += 1
    if revision.count("self._index_thread(thread_id, connection)\n            return entry, False") != 1:
        raise ValueError(f"{SESSION} 的首次写入必须在刷新索引后返回")
    checked += 1
    # 全局：异常类型必须保持 OSError 语义，便于上层区分持久化不确定。
    if "class ToolRevisionPersistenceError(OSError):" not in source:
        raise ValueError(f"{SESSION} 缺少 ToolRevisionPersistenceError")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_tool_revision()
        behavior_cases = _behavior_checks()
    except (ValueError, SyntaxError, ToolRevisionPersistenceError) as error:
        print(f"工具结果修订核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具结果修订一致：{checked} 项结构校验、{behavior_cases} 项恢复场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
