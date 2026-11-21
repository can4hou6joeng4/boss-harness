#!/usr/bin/env python3
"""对照会话列表分页的筛选、游标、删除过滤与损坏行隔离。

`list_threads_page` 先校验 limit 与筛选参数，再把 `archived` / `projectId`
绑进分页游标范围；游标的双列比较必须与 `ORDER BY updated_at DESC,id DESC`
一致，待删除标记必须在 SQL 内过滤，损坏行必须从候选窗口之外继续取行而不是
吃掉翻页余量。`_thread_metadata` 把投影行的结构损坏统一转成内部重建信号，
超长标题与项目编号截断标记而不拒绝。本脚本在临时目录构造 `SessionStore`
做行为对照并扫描源码；不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import SessionStore, _page_cursor  # noqa: E402

THREAD_PAGE_ORDER = (
    "def list_threads_page(self, *, cursor: str | None = None, limit: int = 50,",
    "archived: bool = False, project_id: str | None = None) -> dict:",
    "_limit(limit)",
    "if type(archived) is not bool or (project_id is not None and not isinstance(project_id, str)):",
    'raise ValueError("会话筛选参数无效")',
    "if project_id is not None and len(project_id) > MAX_PROJECT_ID_CHARS:",
    'raise ValueError(f"projectId 必须是最多 {MAX_PROJECT_ID_CHARS} 字符的字符串")',
    'scope = {"archived": archived, "projectId": project_id}',
    'key = _read_page_cursor(cursor, "threads", scope)',
    "parameters: list[Any] = [int(archived)]",
    'query = "SELECT * FROM threads WHERE archived=?"',
    "if project_id is not None:",
    'query += " AND project_id=?"',
    "parameters.append(project_id)",
    "if key is not None:",
    "if len(key) != 2 or not isinstance(key[0], str) or not isinstance(key[1], str) or not _THREAD_ID.fullmatch(key[1]):",
    'raise ValueError("会话分页游标无效")',
    "datetime.fromisoformat(key[0])",
    'raise ValueError("会话分页游标无效") from None',
    'query += " AND (updated_at<? OR (updated_at=? AND id<?))"',
    "parameters.extend([key[0], key[0], key[1]])",
    "self._refresh_threads()",
    "pending = sorted(self._pending_deletion_ids())",
    "if pending:",
    'query += " AND id NOT IN (" + ",".join("?" for _ in pending) + ")"',
    "parameters.extend(pending)",
    'query += " ORDER BY updated_at DESC,id DESC"',
    "skip: set[str] = set()",
    "if row[\"id\"] in skip:",
    "continue",
    "if not isinstance(row[\"updated_at\"], str):",
    'raise _IndexedMetadataError(row["id"])',
    "if len(page) == limit:",
    "has_more = True",
    "page.append(row)",
    'next_cursor = (_page_cursor("threads", scope, [page[-1]["updated_at"], page[-1]["id"]])',
    "if page and has_more else None)",
    'return {"threads": [self._thread_metadata(row) for row in page],',
    '"nextCursor": next_cursor}',
    "return self._with_repaired_index(read, skip=skip)",
)
METADATA_ORDER = (
    "def _thread_metadata(row: sqlite3.Row) -> dict[str, Any]:",
    'metadata = json.loads(row["metadata_json"])',
    "except (TypeError, ValueError, RecursionError):",
    'raise _IndexedMetadataError(row["id"]) from None',
    "if not isinstance(metadata, dict):",
    'raise _IndexedMetadataError(row["id"])',
    'if metadata.get("id") != row["id"]:',
    'if not isinstance(metadata.get("createdAt"), str) or not isinstance(metadata.get("title"), str):',
    'for key in ("sessionId", "projectId")):',
    'metadata["projectId"] = project_id[:MAX_PROJECT_ID_CHARS]',
    'metadata["projectIdTruncated"] = True',
    'metadata["title"] = title[:MAX_THREAD_TITLE_CHARS]',
    'metadata["titleTruncated"] = True',
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


def check_thread_page() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    page = _method(tree, source, "SessionStore", "list_threads_page")
    metadata = _method(tree, source, "SessionStore", "_thread_metadata")
    checked = _ordered(THREAD_PAGE_ORDER, page, SESSION)
    checked += _ordered(METADATA_ORDER, metadata, SESSION)
    # 游标校验恰好两处拒绝；筛选参数恰好一处。
    if page.count('raise ValueError("会话分页游标无效")') != 2:
        raise ValueError(f"{SESSION} 的会话分页游标必须恰好两处拒绝")
    checked += 1
    if page.count('raise ValueError("会话筛选参数无效")') != 1:
        raise ValueError(f"{SESSION} 的会话筛选参数必须恰好一处拒绝")
    checked += 1
    if page.count('ORDER BY updated_at DESC,id DESC') != 1:
        raise ValueError(f"{SESSION} 的会话分页排序必须恰好一处")
    checked += 1
    if page.count("has_more = True") != 1 or page.count("if len(page) == limit:") != 1:
        raise ValueError(f"{SESSION} 的翻页判定必须恰好一处")
    checked += 1
    # 日期解析必须在 try 内，项目编号必须走参数绑定。
    if page.index("try:") > page.index("datetime.fromisoformat(key[0])"):
        raise ValueError(f"{SESSION} 的会话分页日期解析必须在 try 内")
    checked += 1
    if 'f" AND project_id=' in page or "parameters.append(project_id)" not in page:
        raise ValueError(f"{SESSION} 的项目筛选必须走参数绑定")
    checked += 1
    # skip 必须先于 read 定义；重建重试必须携带 skip。
    if page.index("skip: set[str] = set()") > page.index("def read()"):
        raise ValueError(f"{SESSION} 的跳过集合必须先于读取定义")
    checked += 1
    if page.count("_with_repaired_index(read, skip=skip)") != 1:
        raise ValueError(f"{SESSION} 的会话分页必须以 skip 重建重试")
    checked += 1
    # 投影损坏信号恰好五处；超长只截断不拒绝。
    if metadata.count('_IndexedMetadataError(row["id"])') != 5:
        raise ValueError(f"{SESSION} 的投影损坏信号必须恰好五处")
    checked += 1
    if metadata.count("json.loads(row[\"metadata_json\"])") != 1:
        raise ValueError(f"{SESSION} 的投影只解析一次")
    checked += 1
    if metadata.count("Truncated") != 2 or "raise" in metadata.split("Truncated")[0].split("projectId")[-1]:
        raise ValueError(f"{SESSION} 的超长字段必须截断标记而不拒绝")
    checked += 1
    # 行为：分页、排序与游标。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            created = [store.create(f"会话{index}")["id"] for index in range(5)]
            base = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
            for index, thread_id in enumerate(created):
                stamp = (base + timedelta(seconds=index)).timestamp()
                os.utime(store.path_for(thread_id), (stamp, stamp))
            first = store.list_threads_page(limit=2)
            if [item["id"] for item in first["threads"]] != [created[4], created[3]]:
                raise ValueError("会话列表必须按更新时间倒序")
            checked += 1
            if first["nextCursor"] is None:
                raise ValueError("存在更多会话时必须返回游标")
            checked += 1
            second = store.list_threads_page(cursor=first["nextCursor"], limit=2)
            if [item["id"] for item in second["threads"]] != [created[2], created[1]]:
                raise ValueError("第二页必须延续游标")
            checked += 1
            third = store.list_threads_page(cursor=second["nextCursor"], limit=2)
            if [item["id"] for item in third["threads"]] != [created[0]] or third["nextCursor"] is not None:
                raise ValueError("最后一页必须只含剩余会话且无游标")
            checked += 1
            exact = store.list_threads_page(limit=5)
            if len(exact["threads"]) != 5 or exact["nextCursor"] is not None:
                raise ValueError("恰好一页时不得返回游标")
            checked += 1
            same = (base + timedelta(minutes=5)).timestamp()
            for thread_id in (created[0], created[1]):
                os.utime(store.path_for(thread_id), (same, same))
            tied = store.list_threads_page(limit=2)
            if [item["id"] for item in tied["threads"]] != sorted(created[:2], reverse=True):
                raise ValueError("相同更新时间必须按会话编号倒序")
            checked += 1
            empty = SessionStore(Path(temporary) / "empty" / "sessions")
            try:
                if empty.list_threads_page() != {"threads": [], "nextCursor": None}:
                    raise ValueError("空库必须返回空页")
                checked += 1
            finally:
                empty.close()
        finally:
            store.close()
    # 行为：归档与项目筛选。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            kept = store.create("保留A")["id"]
            other = store.create("保留B")["id"]
            project = store.create("项目")["id"]
            gone = store.create("归档")["id"]
            store.update_thread(other, project_id="p1")
            store.update_thread(project, project_id="p2")
            store.archive_thread(gone)
            active = [item["id"] for item in store.list_threads_page()["threads"]]
            if gone in active or len(active) != 3:
                raise ValueError("默认列表不得包含已归档会话")
            checked += 1
            archived = [item["id"] for item in store.list_threads_page(archived=True)["threads"]]
            if archived != [gone]:
                raise ValueError("归档筛选必须只含已归档会话")
            checked += 1
            if [item["id"] for item in store.list_threads_page(project_id="p1")["threads"]] != [other]:
                raise ValueError("项目筛选必须只含对应会话")
            checked += 1
            if [item["id"] for item in store.list_threads_page(project_id="p2")["threads"]] != [project]:
                raise ValueError("项目筛选必须按编号精确匹配")
            checked += 1
            if kept not in active:
                raise ValueError("未筛选列表必须包含未归档会话")
            checked += 1
            # 游标与查询范围绑定。
            scope = {"archived": False, "projectId": None}
            cursor = _page_cursor("threads", scope, ["2026-01-01T00:00:00+00:00", kept])
            _expect_error(lambda: store.list_threads_page(cursor=cursor, archived=True),
                          "分页游标与查询范围不匹配", "归档范围变化")
            checked += 1
            scoped = _page_cursor("threads", {"archived": False, "projectId": "p1"},
                                  ["2026-01-01T00:00:00+00:00", kept])
            _expect_error(lambda: store.list_threads_page(cursor=scoped),
                          "分页游标与查询范围不匹配", "项目范围变化")
            checked += 1
            for label, key in (
                ("单元素", ["2026-01-01T00:00:00+00:00"]),
                ("三元素", ["2026-01-01T00:00:00+00:00", kept, "x"]),
                ("日期非字符串", [123, kept]),
                ("编号非字符串", ["2026-01-01T00:00:00+00:00", 123]),
                ("编号非十六进制", ["2026-01-01T00:00:00+00:00", "Z" * 12]),
                ("编号过长", ["2026-01-01T00:00:00+00:00", kept + "0"]),
                ("日期格式", ["2026-99-99", kept]),
            ):
                bad = _page_cursor("threads", scope, key)
                _expect_error(lambda bad=bad: store.list_threads_page(cursor=bad),
                              "会话分页游标无效", label)
                checked += 1
            _expect_error(lambda: store.list_threads_page(cursor="bad"), "分页游标无效", "前缀")
            checked += 1
            _expect_error(lambda: store.list_threads_page(cursor="p1_" + "%" * 8), "分页游标无效", "编码")
            checked += 1
            _expect_error(lambda: store.list_threads_page(cursor="p1_" + "A" * 5000), "分页游标无效", "超长")
            checked += 1
        finally:
            store.close()
    # 行为：入参校验顺序与边界。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            for label, limit in (("零", 0), ("超上限", 201), ("布尔", True), ("浮点", 1.0), ("字符串", "5")):
                _expect_error(lambda limit=limit: store.list_threads_page(limit=limit),
                              "limit 必须是 1 到 200 之间的整数", label)
                checked += 1
            for label, archived_value in (("整数", 1), ("空", None), ("字符串", "false")):
                _expect_error(lambda archived_value=archived_value: store.list_threads_page(archived=archived_value),
                              "会话筛选参数无效", label)
                checked += 1
            for label, project_value in (("整数", 1), ("字节", b"p"), ("列表", [])):
                _expect_error(lambda project_value=project_value: store.list_threads_page(project_id=project_value),
                              "会话筛选参数无效", label)
                checked += 1
            _expect_error(lambda: store.list_threads_page(project_id="x" * 201),
                          "projectId 必须是最多 200 字符的字符串", "项目编号超长")
            checked += 1
            if store.list_threads_page(limit=200, project_id="x" * 200)["threads"] != []:
                raise ValueError("恰好 200 字符的项目编号必须被接受")
            checked += 1
            _expect_error(lambda: store.list_threads_page(limit=0, archived=1),
                          "limit 必须是 1 到 200 之间的整数", "limit 先于筛选")
            checked += 1
        finally:
            store.close()
    # 行为：待删除标记在列表内过滤。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            kept = store.create("保留")["id"]
            blocked = store.create("待删除")["id"]
            store._write_delete_intent(blocked, store.read_entries(blocked))
            if blocked not in store._pending_deletion_ids():
                raise ValueError("删除标记必须登记待删除会话")
            checked += 1
            ids = [item["id"] for item in store.list_threads_page()["threads"]]
            if blocked in ids or kept not in ids:
                raise ValueError("待删除会话不得出现在列表")
            checked += 1
            if [item["id"] for item in store.list_threads() if item["id"] == blocked]:
                raise ValueError("旧列表接口同样不得返回待删除会话")
            checked += 1
        finally:
            store.close()
    # 行为：损坏行跳过且不吃掉翻页余量。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            healthy = store.create("健康A")["id"]
            broken = store.create("损坏")["id"]
            tail = store.create("健康B")["id"]
            base = datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
            for index, thread_id in enumerate((healthy, broken, tail)):
                stamp = (base + timedelta(seconds=index)).timestamp()
                os.utime(store.path_for(thread_id), (stamp, stamp))
            with store._index.transaction() as connection:
                connection.execute("UPDATE threads SET metadata_json=? WHERE id=?", ("[]", broken))
            path = store.path_for(broken)
            with path.open("ab") as handle:
                handle.write(b'{"broken": \n')
            os.utime(path, (base.timestamp() + 0.5, base.timestamp() + 0.5))
            first = store.list_threads_page(limit=1)
            if [item["id"] for item in first["threads"]] != [tail]:
                raise ValueError("损坏会话不得阻断列表且排序保持")
            checked += 1
            if first["nextCursor"] is None:
                raise ValueError("损坏会话不得吃掉翻页余量")
            checked += 1
            second = store.list_threads_page(cursor=first["nextCursor"], limit=1)
            if [item["id"] for item in second["threads"]] != [healthy] or second["nextCursor"] is not None:
                raise ValueError("损坏会话之后的健康会话必须继续返回")
            checked += 1
            if broken not in store.unreadable_thread_ids():
                raise ValueError("跳过重建的会话必须登记为不可读")
            checked += 1
        finally:
            store.close()
    # 行为：超长字段截断标记。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("短标题")["id"]
            with store._index.transaction() as connection:
                row = connection.execute("SELECT metadata_json FROM threads WHERE id=?",
                                         (thread_id,)).fetchone()
                value = json.loads(row["metadata_json"])
                value["title"] = "题" * 600
                value["projectId"] = "项" * 250
                connection.execute("UPDATE threads SET metadata_json=? WHERE id=?",
                                   (json.dumps(value, ensure_ascii=False), thread_id))
            item = store.list_threads_page()["threads"][0]
            if len(item["title"]) != 500 or item.get("titleTruncated") is not True:
                raise ValueError("超长标题必须截断到 500 并标记")
            checked += 1
            if len(item["projectId"]) != 200 or item.get("projectIdTruncated") is not True:
                raise ValueError("超长项目编号必须截断到 200 并标记")
            checked += 1
            if item["id"] != thread_id:
                raise ValueError("截断不得改写会话编号")
            checked += 1
        finally:
            store.close()
    # 行为：投影损坏但源日志完好必须重建返回。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("可重建")["id"]
            with store._index.transaction() as connection:
                connection.execute("UPDATE threads SET metadata_json=? WHERE id=?", ("[]", thread_id))
            page = store.list_threads_page()
            if ([item["id"] for item in page["threads"]] != [thread_id]
                    or page["threads"][0]["title"] != "可重建"):
                raise ValueError("投影损坏但源日志完好时必须重建返回")
            checked += 1
            if thread_id in store.unreadable_thread_ids():
                raise ValueError("重建成功的会话不得登记为不可读")
            checked += 1
        finally:
            store.close()
    # 行为：时间列被外部改写为 BLOB 时重建而非把内部错误送给调用方。
    with tempfile.TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        try:
            thread_id = store.create("时间列")["id"]
            with store._index.transaction() as connection:
                connection.execute("UPDATE threads SET updated_at=? WHERE id=?", (b"\x00", thread_id))
            page = store.list_threads_page()
            if [item["id"] for item in page["threads"]] != [thread_id]:
                raise ValueError("时间列损坏后必须重建并返回会话")
            checked += 1
            if not isinstance(store.list_threads_page()["threads"][0].get("updatedAt"), str):
                raise ValueError("重建后的更新时间必须是字符串")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_thread_page()
    except (ValueError, SyntaxError) as error:
        print(f"会话列表分页核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话列表分页一致：{checked} 项筛选、游标与损坏隔离校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
