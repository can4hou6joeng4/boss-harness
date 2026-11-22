#!/usr/bin/env python3
"""对照回合分页的游标、排序、边界守卫与投影解码。

`list_turns` 是回合列表的唯一分页入口：游标绑定 `{"threadId"}` 范围，
键是 `(first_ordinal, turn_id)` 的整数加标识符，查询用同一双列比较并
`ORDER BY first_ordinal,turn_id`，多取一行判定下一页；读取前刷新会话索引，
索引行的 `first_ordinal` 必须是整数、`turn_id` 必须是字符串，损坏时按
会话重建而不是把内部错误送给调用方。`_turn_metadata` 只解码投影 JSON，
非对象按索引损坏处理，且损坏信号携带的是会话 id（turns 表没有条目 id 列）。
行为对照覆盖同序号续页、越界游标、`limit` 恰好 200、负序号与空编号不触发重建，
以及 `metadata_json` 为非对象、非 JSON 与 `null` 三类损坏的重建。本脚本在临时
目录构造 `SessionStore` 做行为对照并扫描源码；不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore, _page_cursor  # noqa: E402

TURNS_ORDER = (
    "def list_turns(self, thread_id: str, *, cursor: str | None = None, limit: int = 50) -> dict:",
    "_limit(limit)",
    "self.path_for(thread_id)",
    'scope = {"threadId": thread_id}',
    'key = _read_page_cursor(cursor, "turns", scope)',
    'query = "SELECT * FROM turns WHERE thread_id=?"',
    "parameters: list[Any] = [thread_id]",
    "if key is not None:",
    "if len(key) != 2 or type(key[0]) is not int or key[0] < 0:",
    'raise ValueError("回合分页游标无效")',
    '_identifier(key[1], "turnId")',
    'query += " AND (first_ordinal>? OR (first_ordinal=? AND turn_id>?))"',
    "parameters.extend([key[0], key[0], key[1]])",
    'query += " ORDER BY first_ordinal,turn_id LIMIT ?"',
    "parameters.append(limit + 1)",
    "self._sync_thread(thread_id)",
    "page = rows[:limit]",
    'if type(row["first_ordinal"]) is not int or not isinstance(row["turn_id"], str):',
    'raise _IndexedMetadataError(thread_id)',
    'next_cursor = (_page_cursor("turns", scope, [page[-1]["first_ordinal"], page[-1]["turn_id"]])',
    "if len(rows) > limit else None)",
    'return {"turns": [self._turn_metadata(row) for row in page], "nextCursor": next_cursor}',
    "return self._with_repaired_index(read)",
)
TURN_META_ORDER = (
    "def _turn_metadata(row: sqlite3.Row) -> dict[str, Any]:",
    'metadata = json.loads(row["metadata_json"])',
    "except (TypeError, ValueError, RecursionError):",
    'raise _IndexedMetadataError(row["thread_id"]) from None',
    "if not isinstance(metadata, dict):",
    'raise _IndexedMetadataError(row["thread_id"])',
    "return metadata",
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


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def check_turn_page() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    turns = _method(tree, source, "SessionStore", "list_turns")
    metadata = _method(tree, source, "SessionStore", "_turn_metadata")
    checked = _ordered(TURNS_ORDER, turns, SESSION)
    checked += _ordered(TURN_META_ORDER, metadata, SESSION)
    # 游标与排序必须各一处，且键严格为整数序号加回合标识符。
    if turns.count('raise ValueError("回合分页游标无效")') != 1:
        raise ValueError(f"{SESSION} 的回合分页游标必须恰好一处拒绝")
    checked += 1
    if turns.count("ORDER BY first_ordinal,turn_id") != 1:
        raise ValueError(f"{SESSION} 的回合分页排序必须恰好一处")
    checked += 1
    if turns.count("parameters.append(limit + 1)") != 1 or turns.count("page = rows[:limit]") != 1:
        raise ValueError(f"{SESSION} 的回合分页必须多取一行再截断")
    checked += 1
    if turns.count("_read_page_cursor(cursor, \"turns\", scope)") != 1:
        raise ValueError(f"{SESSION} 的回合游标必须使用 turns 种类")
    checked += 1
    if turns.count("_identifier(key[1], \"turnId\")") != 1:
        raise ValueError(f"{SESSION} 的回合游标必须校验回合标识符")
    checked += 1
    # 单会话读取不带跳过集合：损坏必须报出具体会话。
    if "skip=" in turns or turns.count("_with_repaired_index(read)") != 1:
        raise ValueError(f"{SESSION} 的回合分页必须以单会话重建重试")
    checked += 1
    # 解码损坏信号携带 turns 表的 thread_id，且恰好两处。
    if metadata.count('_IndexedMetadataError(row["thread_id"])') != 2:
        raise ValueError(f"{SESSION} 的回合投影损坏信号必须恰好两处")
    checked += 1
    if metadata.count('row["id"]') != 0:
        raise ValueError(f"{SESSION} 的回合投影不得读取条目 id")
    checked += 1
    if metadata.count('json.loads(row["metadata_json"])') != 1:
        raise ValueError(f"{SESSION} 的回合投影只解析一次")
    checked += 1
    # 行为：分页、排序与游标。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("回合分页")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            store.record_turn(thread_id, "turn-b", "running")
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=? AND turn_id=?",
                                   (9, thread_id, "turn-a"))
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=? AND turn_id=?",
                                   (4, thread_id, "turn-b"))
            page = store.list_turns(thread_id)
            if [item.get("turnId") for item in page["turns"]] != ["turn-b", "turn-a"]:
                raise ValueError("回合分页必须按起始序号升序")
            checked += 1
            if page["nextCursor"] is not None:
                raise ValueError("恰好一页时不得返回游标")
            checked += 1
            first = store.list_turns(thread_id, limit=1)
            if [item.get("turnId") for item in first["turns"]] != ["turn-b"] or first["nextCursor"] is None:
                raise ValueError("首页必须返回第一条与游标")
            checked += 1
            second = store.list_turns(thread_id, cursor=first["nextCursor"], limit=1)
            if [item.get("turnId") for item in second["turns"]] != ["turn-a"] or second["nextCursor"] is not None:
                raise ValueError("续页必须返回剩余回合且无游标")
            checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=? AND turn_id=?",
                                   (7, thread_id, "turn-a"))
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=? AND turn_id=?",
                                   (7, thread_id, "turn-b"))
            tied = store.list_turns(thread_id)
            if [item.get("turnId") for item in tied["turns"]] != ["turn-a", "turn-b"]:
                raise ValueError("相同起始序号必须按回合编号升序")
            checked += 1
            tied_cursor = _page_cursor("turns", {"threadId": thread_id}, [7, "turn-a"])
            rest = store.list_turns(thread_id, cursor=tied_cursor)
            if [item.get("turnId") for item in rest["turns"]] != ["turn-b"] or rest["nextCursor"] is not None:
                raise ValueError("相同起始序号的续页必须跳过游标回合")
            checked += 1
            beyond = store.list_turns(thread_id, cursor=_page_cursor(
                "turns", {"threadId": thread_id}, [2**63 - 1, "zzz"]))
            if beyond != {"turns": [], "nextCursor": None}:
                raise ValueError("越界游标必须返回空页")
            checked += 1
            if len(store.list_turns(thread_id, limit=200)["turns"]) != 2:
                raise ValueError("limit 恰好 200 必须被接受")
            checked += 1
            empty = SessionStore(Path(temporary) / "empty" / "sessions")
            try:
                empty_thread = empty.create("空回合")["id"]
                if empty.list_turns(empty_thread) != {"turns": [], "nextCursor": None}:
                    raise ValueError("没有回合时必须返回空页")
                checked += 1
            finally:
                empty.close()
        finally:
            store.close()
    # 行为：游标范围与格式。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("游标")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            other_id = store.create("其他")["id"]
            store.record_turn(other_id, "turn-z", "completed")
            scope = {"threadId": thread_id}
            cursor = _page_cursor("turns", scope, [0, "turn-a"])
            _expect_error(lambda: store.list_turns(other_id, cursor=cursor),
                          "分页游标与查询范围不匹配", "会话范围变化")
            checked += 1
            wrong_kind = _page_cursor("threads", scope, [0, "turn-a"])
            _expect_error(lambda: store.list_turns(thread_id, cursor=wrong_kind),
                          "分页游标与查询范围不匹配", "游标种类变化")
            checked += 1
            for label, key, message in (
                ("单元素", [0], "回合分页游标无效"),
                ("三元素", [0, "turn-a", "x"], "回合分页游标无效"),
                ("序号字符串", ["0", "turn-a"], "回合分页游标无效"),
                ("序号布尔", [True, "turn-a"], "回合分页游标无效"),
                ("序号浮点", [0.0, "turn-a"], "回合分页游标无效"),
                ("序号为负", [-1, "turn-a"], "回合分页游标无效"),
                ("回合为空", [0, ""], "turnId 格式无效"),
                ("回合含空白", [0, "turn a"], "turnId 格式无效"),
                ("回合超长", [0, "t" * 129], "turnId 格式无效"),
                ("回合非字符串", [0, 3], "turnId 格式无效"),
            ):
                bad = _page_cursor("turns", scope, key)
                _expect_error(lambda bad=bad: store.list_turns(thread_id, cursor=bad), message, label)
                checked += 1
            _expect_error(lambda: store.list_turns(thread_id, cursor="bad"), "分页游标无效", "前缀")
            checked += 1
            _expect_error(lambda: store.list_turns(thread_id, cursor="p1_" + "%" * 8),
                          "分页游标无效", "编码")
            checked += 1
            _expect_error(lambda: store.list_turns(thread_id, cursor="p1_" + "A" * 5000),
                          "分页游标无效", "超长")
            checked += 1
        finally:
            store.close()
    # 行为：入参与会话边界。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("边界")["id"]
            for label, limit in (("零", 0), ("超上限", 201), ("布尔", True), ("浮点", 1.0)):
                _expect_error(lambda limit=limit: store.list_turns(thread_id, limit=limit),
                              "limit 必须是 1 到 200 之间的整数", label)
                checked += 1
            _expect_error(lambda: store.list_turns("zzz"), "threadId 格式无效", "会话格式")
            checked += 1
            _expect_error(lambda: store.list_turns("000000000000"), "会话不存在", "会话不存在")
            checked += 1
        finally:
            store.close()
    # 行为：索引合法边界与列损坏重建。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("损坏")["id"]
            store.record_turn(thread_id, "turn-a", "completed")
            store.record_turn(thread_id, "turn-b", "completed")
            # 负序号与空编号是合法列值：不重建，按列值排序。
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=? AND turn_id=?",
                                   (-5, thread_id, "turn-b"))
            page = store.list_turns(thread_id)
            if [item.get("turnId") for item in page["turns"]] != ["turn-b", "turn-a"]:
                raise ValueError("负起始序号不得触发重建且必须按列值排序")
            checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET first_ordinal=7 WHERE thread_id=?", (thread_id,))
                connection.execute("UPDATE turns SET turn_id='' WHERE thread_id=? AND turn_id=?",
                                   (thread_id, "turn-b"))
            page = store.list_turns(thread_id)
            if [item.get("turnId") for item in page["turns"]] != ["turn-b", "turn-a"]:
                raise ValueError("空回合编号不得触发重建且必须排在前面")
            checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET first_ordinal=? WHERE thread_id=?",
                                   (b"\x00", thread_id))
            page = store.list_turns(thread_id)
            if [item.get("turnId") for item in page["turns"]] != ["turn-a", "turn-b"]:
                raise ValueError("起始序号损坏后必须重建并返回回合")
            checked += 1
            for label, payload in (("非对象", "[]"), ("非 JSON", "not-json"), ("null", "null")):
                with store._index.transaction() as connection:
                    connection.execute("UPDATE turns SET metadata_json=? WHERE thread_id=?",
                                       (payload, thread_id))
                page = store.list_turns(thread_id)
                if (not page["turns"] or not isinstance(page["turns"][0], dict)
                        or page["turns"][0].get("turnId") != "turn-a"):
                    raise ValueError(f"{label}投影损坏后必须重建并返回对象")
                checked += 1
            with store._index.transaction() as connection:
                connection.execute("UPDATE turns SET turn_id=? WHERE thread_id=? AND turn_id=?",
                                   (b"\x00", thread_id, "turn-a"))
            page = store.list_turns(thread_id)
            if [item.get("turnId") for item in page["turns"]] != ["turn-a", "turn-b"]:
                raise ValueError("回合编号损坏后必须重建并返回")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_turn_page()
    except (ValueError, SyntaxError) as error:
        print(f"回合分页核对失败，{error}", file=sys.stderr)
        return 2
    print(f"回合分页一致：{checked} 项游标、排序与损坏守卫校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
