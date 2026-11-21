#!/usr/bin/env python3
"""对照会话分叉时上下文检查点的归属过滤。

`fork_thread` 复制分支前缀时用 `checkpoint_in_branch` 决定哪些
`context_checkpoint` 属于选中回合：检查点载荷的 `throughTurnId` 必须出现在当前
分支的回合表里，且位置不晚于选中回合；复制前缀与边界后的恢复修正使用同一判据。
判据看错位置表、比较符号或只读方式，分叉会继承其他分支的检查点或丢掉本应随
修正复制的检查点。本脚本在临时目录构造会话做行为对照，不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import Entry, SessionStore  # noqa: E402

FORK_ORDER = (
    'turn_positions = {turn["turnId"]: position for position, turn in enumerate(turns)}',
    'selected_position = turn_positions[selected["turnId"]]',
    "def checkpoint_in_branch(entry: dict) -> bool:",
    'payload = entry.get("payload")',
    'through_turn_id = payload.get("throughTurnId") if isinstance(payload, dict) else None',
    'position = turn_positions.get(through_turn_id) if isinstance(through_turn_id, str) else None',
    "return position is not None and position <= selected_position",
    "prefix = [entry for entry in entries[:cutoff + 1]",
    'if entry.get("type") != "context_checkpoint" or checkpoint_in_branch(entry)]',
    'or (entry.get("type") == "context_checkpoint" and checkpoint_in_branch(entry))):',
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


def _add(store: SessionStore, thread_id: str, kind: str, **payload) -> None:
    store.append(thread_id, Entry(type=kind, parent_id=store.last_entry_id(thread_id),
                                  payload=payload))


def _checkpoints(store: SessionStore, thread_id: str) -> list:
    return [entry["payload"].get("throughTurnId") if isinstance(entry.get("payload"), dict) else None
            for entry in store.read_entries(thread_id)
            if entry.get("type") == "context_checkpoint"]


def _expect(actual, expected, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} 检查点归属变化：期望 {expected!r}，实际 {actual!r}")


def _session(temporary: str, title: str) -> tuple[SessionStore, str]:
    store = SessionStore(Path(temporary) / title / "sessions")
    return store, store.create(title)["id"]


def check_fork_checkpoints() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    fork = _method(tree, source, "SessionStore", "fork_thread")
    checked = _ordered(FORK_ORDER, fork, SESSION)
    if fork.count("checkpoint_in_branch(") != 3:
        raise ValueError(f"{SESSION} 的检查点归属必须由定义与两处调用组成")
    checked += 1
    if fork.count("turn_positions") != 3 or fork.count("selected_position") != 2:
        raise ValueError(f"{SESSION} 的检查点归属必须只按当前分支回合表判定")
    checked += 1
    if fork.count("throughTurnId") != 1:
        raise ValueError(f"{SESSION} 的检查点归属必须只读取 throughTurnId")
    checked += 1
    # 判据片段只读载荷，不按下标取值，也不接受未知回合。
    start = fork.index("def checkpoint_in_branch")
    end = fork.index("prefix = [entry for entry in entries[:cutoff + 1]")
    checkpoint = fork[start:end]
    if 'entry["payload"]' in checkpoint or 'payload["throughTurnId"]' in checkpoint:
        raise ValueError(f"{SESSION} 的检查点判据必须安全读取载荷")
    checked += 1
    if "position is not None and position <= selected_position" not in checkpoint:
        raise ValueError(f"{SESSION} 的检查点判据必须按位置上限比较")
    checked += 1
    # 行为：选中回合之前的检查点被复制，之后的被过滤。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _session(temporary, "basic")
        try:
            _add(store, thread_id, "turn", turnId="turn-a", status="completed")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-a")
            _add(store, thread_id, "turn", turnId="turn-b", status="completed")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-b")
            first = store.fork_thread(thread_id, turn_id="turn-a")
            _expect(_checkpoints(store, first["id"]), ["turn-a"], "第一回合分叉")
            checked += 1
            second = store.fork_thread(thread_id, turn_id="turn-b")
            _expect(_checkpoints(store, second["id"]), ["turn-a", "turn-b"], "第二回合分叉")
            checked += 1
        finally:
            store.close()
    # 行为：未知回合、非字符串与缺失 throughTurnId 的检查点都不复制。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _session(temporary, "unknown")
        try:
            _add(store, thread_id, "turn", turnId="turn-a", status="completed")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-a")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-z")
            _add(store, thread_id, "context_checkpoint", throughTurnId=3)
            _add(store, thread_id, "context_checkpoint")
            _add(store, thread_id, "turn", turnId="turn-b", status="completed")
            forked = store.fork_thread(thread_id, turn_id="turn-b")
            _expect(_checkpoints(store, forked["id"]), ["turn-a"], "过滤未知检查点")
            checked += 1
            earlier = store.fork_thread(thread_id, turn_id="turn-a")
            _expect(_checkpoints(store, earlier["id"]), ["turn-a"], "过滤边界后未知检查点")
            checked += 1
        finally:
            store.close()
    # 行为：默认选中当前分支最后一个回合，仍按同一判据过滤。
    with tempfile.TemporaryDirectory() as temporary:
        store, thread_id = _session(temporary, "default")
        try:
            _add(store, thread_id, "turn", turnId="turn-a", status="completed")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-a")
            _add(store, thread_id, "turn", turnId="turn-b", status="completed")
            _add(store, thread_id, "context_checkpoint", throughTurnId="turn-b")
            forked = store.fork_thread(thread_id)
            _expect(_checkpoints(store, forked["id"]), ["turn-a", "turn-b"], "默认回合分叉")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_fork_checkpoints()
    except (ValueError, SyntaxError) as error:
        print(f"分叉检查点核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分叉检查点一致：{checked} 项归属判据与复制过滤校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
