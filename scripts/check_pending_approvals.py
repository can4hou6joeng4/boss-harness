#!/usr/bin/env python3
"""核对待审批分页与计数的共享过滤口径。

`_pending_approvals_where` 是 `pending_approvals` 与 `pending_approval_counts`
共用的过滤条件：未裁决、运行中回合、未归档会话、期限范围内，列类型与非空
约束必须同时成立，删除占位过多时整次读取放弃。列表用 `limit + 1` 判定是否
还有更多，损坏行按缺失跳过；计数按会话分组，不受列表上限影响。这里按源码
顺序固定这些边界，避免侧栏徽标与列表对不上，或损坏行让整次读取失败；并用
临时合成会话、回合与审批记录实际执行列表与计数。
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import (  # noqa: E402
    Entry,
    SessionStore,
    approval_parameters_digest,
)

# 共享过滤：删除占位上限 → 三表连接 → 未裁决与活跃回合 → 列类型与非空守卫 →
# 期限范围 → 当前时间与可选会话 / 删除过滤参数。
WHERE_ORDER = (
    "def _pending_approvals_where(self, thread_id: str | None) -> tuple[str, list[Any]] | None:",
    "pending_deletions = sorted(self._pending_deletion_ids())",
    "if len(pending_deletions) > 800:",
    "return None",
    "FROM approvals a",
    "JOIN threads t ON t.id=a.thread_id",
    "JOIN turns r ON r.thread_id=a.thread_id AND r.turn_id=a.turn_id",
    "WHERE a.decision IS NULL AND a.status='running'",
    "AND a.execution_state='pending_approval' AND a.deadline>?",
    "AND t.archived=0 AND r.status IN ('running','interrupted')",
    "AND typeof(a.approval_id)='text' AND typeof(a.thread_id)='text'",
    "AND typeof(a.turn_id)='text' AND typeof(a.item_id)='text'",
    "AND typeof(a.tool_name)='text' AND typeof(a.params_digest)='text'",
    "AND typeof(a.deadline) IN ('integer','real')",
    "AND a.approval_id<>'' AND a.thread_id<>'' AND a.turn_id<>''",
    "AND a.item_id<>'' AND a.tool_name<>'' AND a.params_digest<>''",
    "AND a.deadline BETWEEN 0 AND 1e15",
    "parameters: list[Any] = [time.time()]",
    'where += " AND a.thread_id=?"',
    "parameters.append(thread_id)",
    "if pending_deletions:",
    'where += " AND a.thread_id NOT IN (" + ",".join("?" for _ in pending_deletions) + ")"',
    "parameters.extend(pending_deletions)",
    "return where, parameters",
)
# 列表分页：条目上限 → 共享条件 → 稳定排序 → 多取一行判定截断 → 损坏行跳过 →
# 固定展示字段。
LIST_ORDER = (
    "def pending_approvals(self, thread_id: str | None = None, *,",
    "limit: int = 100) -> tuple[list[dict], bool]:",
    "_limit(limit, maximum=200)",
    "if thread_id is not None:",
    "self.path_for(thread_id)",
    "with self._lock:",
    "self.require_thread(thread_id)",
    "condition = self._pending_approvals_where(thread_id)",
    "if condition is None:",
    "return [], False",
    "ORDER BY t.updated_at DESC,a.thread_id DESC,a.item_id DESC LIMIT ?",
    "parameters.append(limit + 1)",
    "rows = connection.execute(query, parameters).fetchall()",
    "truncated = len(rows) > limit",
    "for row in rows[:limit]:",
    "deadline_valid = (type(deadline) is int",
    "or (isinstance(deadline, float) and math.isfinite(deadline)))",
    "if (not deadline_valid",
    '"approval_id", "thread_id", "turn_id", "item_id",',
    '"tool_name", "params_digest"))):',
    "continue",
    'approvals.append({"approvalId": row["approval_id"], "threadId": row["thread_id"],',
    '"summary": f"需要你批准后才会执行：{row[\'tool_name\']}",',
    '"deadline": deadline, "paramsDigest": row["params_digest"]})',
    "return approvals, truncated",
)
# 计数：共享条件 → 按会话分组 → 字符串键与整数计数。
COUNT_ORDER = (
    "def pending_approval_counts(self, thread_id: str | None = None) -> dict[str, int]:",
    "if thread_id is not None:",
    "self.path_for(thread_id)",
    "with self._lock:",
    "self.require_thread(thread_id)",
    "condition = self._pending_approvals_where(thread_id)",
    "if condition is None:",
    "return {}",
    '"SELECT a.thread_id,COUNT(*)" + where + " GROUP BY a.thread_id",',
    "return {str(row[0]): int(row[1]) for row in rows}",
)


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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"待审批行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"待审批行为变化 {label}：期望错误 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"待审批行为变化 {label}：期望错误 {message!r}，实际未抛出")


def _approval_id(item_id: str) -> str:
    return hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:32]


def _approval_payload(turn_id: str, *, approval_id: str, tool: str = "boss_hr_greet",
                      deadline: float | None = None, decision: str | None = None,
                      status: str = "running",
                      execution_state: str = "pending_approval",
                      arguments: dict | None = None,
                      description: str = "对外发起沟通") -> dict:
    arguments = {"jobId": "job-1"} if arguments is None else arguments
    approval = {"approvalId": approval_id, "toolName": tool,
                "deadline": time.time() + 3600 if deadline is None else deadline,
                "description": description, "params": arguments,
                "paramsDigest": approval_parameters_digest(arguments)}
    if decision is not None:
        approval["decision"] = decision
    return {"kind": "toolCall", "toolName": tool, "turnId": turn_id, "status": status,
            "executionState": execution_state, "toolArguments": arguments,
            "approval": approval}


def _add_turn(store: SessionStore, thread_id: str, turn_id: str, status: str = "running") -> None:
    store.append(thread_id, Entry(type="turn", payload={"turnId": turn_id, "status": status}))


def _add_approval(store: SessionStore, thread_id: str, item_id: str, turn_id: str, *,
                  approval_id: str | None = None, **options) -> None:
    store.append(thread_id, Entry(type="item", id=item_id, payload=_approval_payload(
        turn_id, approval_id=approval_id or _approval_id(item_id), **options)))


def _behavior_checks() -> int:
    checked = 0
    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        checked += _expect_value(store.pending_approvals(), ([], False), "空状态目录列表")
        checked += _expect_value(store.pending_approval_counts(), {}, "空状态目录计数")

        thread = store.create("审批")["id"]
        deadline = time.time() + 3600
        _add_turn(store, thread, "turn-1")
        _add_approval(store, thread, "item-1", "turn-1", deadline=deadline,
                      description="机密说明 sk-demo-123456")
        approvals, truncated = store.pending_approvals()
        checked += _expect_value(truncated, False, "单条列表截断标记")
        checked += _expect_value(approvals, [{
            "approvalId": _approval_id("item-1"), "threadId": thread, "turnId": "turn-1",
            "itemId": "item-1", "toolName": "boss_hr_greet",
            "summary": "需要你批准后才会执行：boss_hr_greet", "deadline": deadline,
            "paramsDigest": approval_parameters_digest({"jobId": "job-1"}),
        }], "单条待审批投影")
        checked += _expect_value(store.pending_approval_counts(), {thread: 1}, "单条分组计数")
        if "sk-demo-123456" in str(approvals) or "job-1" in str(approvals):
            raise ValueError("待审批列表泄露了审批参数或描述")
        checked += 1

        _add_approval(store, thread, "item-approved", "turn-1", decision="approve",
                      execution_state="approved")
        _add_approval(store, thread, "item-denied", "turn-1", decision="deny",
                      status="failed", execution_state="not_approved")
        _add_approval(store, thread, "item-expired", "turn-1", decision="expired",
                      status="failed", execution_state="not_executed")
        _add_approval(store, thread, "item-late", "turn-1", deadline=time.time() - 1)
        approvals, _ = store.pending_approvals()
        checked += _expect_value([row["itemId"] for row in approvals], ["item-1"],
                                 "已裁决与过期审批排除")
        checked += _expect_value(store.pending_approval_counts(), {thread: 1},
                                 "已裁决与过期计数排除")

        _add_turn(store, thread, "turn-done", "completed")
        _add_approval(store, thread, "item-done-turn", "turn-done")
        _add_turn(store, thread, "turn-interrupted", "interrupted")
        _add_approval(store, thread, "item-interrupted", "turn-interrupted")
        approvals, _ = store.pending_approvals()
        checked += _expect_value(sorted(row["itemId"] for row in approvals),
                                 ["item-1", "item-interrupted"], "回合状态过滤")
        checked += _expect_value(store.pending_approval_counts(), {thread: 2}, "回合状态计数")

        store.append(thread, Entry(type="thread_info", payload={"archived": True}))
        checked += _expect_value(store.pending_approvals(), ([], False), "归档会话排除")
        checked += _expect_value(store.pending_approval_counts(), {}, "归档会话计数排除")
        store.append(thread, Entry(type="thread_info", payload={"archived": False}))
        checked += _expect_value(len(store.pending_approvals()[0]), 2, "取消归档后恢复列表")

        other = store.create("其他")["id"]
        _add_turn(store, other, "turn-2")
        _add_approval(store, other, "item-2", "turn-2")
        checked += _expect_value([row["itemId"] for row in store.pending_approvals(thread)[0]],
                                 ["item-interrupted", "item-1"], "会话过滤列表")
        checked += _expect_value(store.pending_approvals(other)[0][0]["itemId"], "item-2",
                                 "会话过滤单条")
        checked += _expect_value(store.pending_approval_counts(thread), {thread: 2},
                                 "会话过滤计数")
        checked += _expect_value(store.pending_approval_counts(), {thread: 2, other: 1},
                                 "跨会话分组计数")
        checked += _expect_error(lambda: store.pending_approvals("../bad"),
                                 "threadId 格式无效", "非法会话列表")
        checked += _expect_error(lambda: store.pending_approvals("0123456789ab"),
                                 "会话不存在", "未知会话列表")
        checked += _expect_error(lambda: store.pending_approval_counts("0123456789ab"),
                                 "会话不存在", "未知会话计数")

        page = store.create("排序")["id"]
        _add_turn(store, page, "turn-3")
        for item_id in ("item-a", "item-b", "item-c"):
            _add_approval(store, page, item_id, "turn-3")
        first, truncated = store.pending_approvals(page, limit=2)
        checked += _expect_value([row["itemId"] for row in first], ["item-c", "item-b"],
                                 "倒序分页")
        checked += _expect_value(truncated, True, "分页截断标记")
        second, truncated = store.pending_approvals(page, limit=3)
        checked += _expect_value([row["itemId"] for row in second],
                                 ["item-c", "item-b", "item-a"], "整页排序")
        checked += _expect_value(truncated, False, "整页不截断")
        checked += _expect_value(len(store.pending_approvals(page, limit=200)[0]), 3,
                                 "上限 200 可用")
        checked += _expect_value(store.pending_approval_counts(page), {page: 3},
                                 "计数不受列表上限影响")
        for limit in (0, 201, True):
            checked += _expect_error(lambda limit=limit: store.pending_approvals(page, limit=limit),
                                     "limit 必须是 1 到 200 之间的整数", f"条目上限拒绝 {limit!r}")

        marked = store.create("删除中")["id"]
        _add_turn(store, marked, "turn-4")
        _add_approval(store, marked, "item-marked", "turn-4")
        (Path(store.root) / f".delete-{marked}.json").write_text(json.dumps(
            {"version": 1, "threadId": marked, "attachmentDigests": [], "eventId": "0" * 32},
            ensure_ascii=False), encoding="utf-8")
        listed = [row["itemId"] for row in store.pending_approvals(limit=200)[0]]
        checked += _expect_value("item-marked" in listed, False, "删除标记会话排除")
        checked += _expect_value(marked in store.pending_approval_counts(), False,
                                 "删除标记计数排除")
        checked += _expect_error(lambda: store.pending_approvals(marked),
                                 "会话正在删除，暂不可读取", "删除标记会话过滤拒绝")

        for index in range(801):
            marker = f"{index + 1:012x}"
            if marker == marked:
                marker = "deadbeefcafe"
            (Path(store.root) / f".delete-{marker}.json").write_text("{}", encoding="utf-8")
        checked += _expect_value(store.pending_approvals(), ([], False), "占位超限放弃列表")
        checked += _expect_value(store.pending_approval_counts(), {}, "占位超限放弃计数")

    with TemporaryDirectory() as temporary:
        store = SessionStore(Path(temporary) / "sessions")
        thread = store.create("索引")["id"]
        _add_turn(store, thread, "turn-5")
        future = time.time() + 3600
        digest = approval_parameters_digest({"jobId": "job-1"})
        rows = (
            ("a" * 32, thread, "direct-ok", "turn-5", "boss_hr_greet", future, digest,
             None, "running", "pending_approval"),
            ("", thread, "bad-empty-approval", "turn-5", "boss_hr_greet", future, digest,
             None, "running", "pending_approval"),
            ("b" * 32, thread, "", "turn-5", "boss_hr_greet", future, digest,
             None, "running", "pending_approval"),
            ("c" * 32, thread, "bad-empty-tool", "turn-5", "", future, digest,
             None, "running", "pending_approval"),
            ("d" * 32, thread, "bad-empty-digest", "turn-5", "boss_hr_greet", future, "",
             None, "running", "pending_approval"),
            ("e" * 32, thread, "bad-text-deadline", "turn-5", "boss_hr_greet", "later",
             digest, None, "running", "pending_approval"),
            ("f" * 32, thread, "bad-huge-deadline", "turn-5", "boss_hr_greet", 1e16, digest,
             None, "running", "pending_approval"),
            ("1" * 32, thread, "bad-zero-deadline", "turn-5", "boss_hr_greet", 0, digest,
             None, "running", "pending_approval"),
            ("2" * 32, thread, "bad-status", "turn-5", "boss_hr_greet", future, digest,
             None, "completed", "pending_approval"),
            ("3" * 32, thread, "bad-state", "turn-5", "boss_hr_greet", future, digest,
             None, "running", "approved"),
            ("4" * 32, thread, "bad-decided", "turn-5", "boss_hr_greet", future, digest,
             "approve", "running", "pending_approval"),
            ("5" * 32, thread, "bad-turn", "turn-6", "boss_hr_greet", future, digest,
             None, "running", "pending_approval"),
        )
        with store._index.connection() as connection:
            connection.execute(
                "INSERT INTO turns (thread_id,turn_id,status,first_ordinal,last_ordinal,"
                "metadata_json) VALUES (?,?,?,?,?,?)",
                (thread, "turn-6", "completed", 0, 0, "{}"))
            for row in rows:
                connection.execute(
                    "INSERT INTO approvals (approval_id,thread_id,item_id,turn_id,tool_name,"
                    "deadline,params_digest,decision,status,execution_state) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)", row)
        approvals, truncated = store.pending_approvals()
        checked += _expect_value([row["itemId"] for row in approvals], ["direct-ok"],
                                 "畸形索引行排除")
        checked += _expect_value(truncated, False, "畸形索引行不触发截断")
        checked += _expect_value(store.pending_approval_counts(), {thread: 1},
                                 "畸形索引行计数排除")
        with store._index.connection() as connection:
            connection.execute("UPDATE threads SET archived=1 WHERE id=?", (thread,))
        checked += _expect_value(store.pending_approvals(), ([], False), "索引归档排除")
        checked += _expect_value(store.pending_approval_counts(), {}, "索引归档计数排除")
        with store._index.connection() as connection:
            connection.execute("UPDATE threads SET archived=0 WHERE id=?", (thread,))
        checked += _expect_value([row["itemId"] for row in store.pending_approvals()[0]],
                                 ["direct-ok"], "取消索引归档后恢复")
        approvals[0]["itemId"] = "changed"
        checked += _expect_value(store.pending_approvals()[0][0]["itemId"], "direct-ok",
                                 "投影不复用返回对象")
    return checked


def check_pending_approvals() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    where = _function(tree, source, "_pending_approvals_where")
    listing = _function(tree, source, "pending_approvals")
    counts = _function(tree, source, "pending_approval_counts")
    checked = _ordered(WHERE_ORDER, where, SESSION)
    checked += _ordered(LIST_ORDER, listing, SESSION)
    checked += _ordered(COUNT_ORDER, counts, SESSION)
    # 列表与计数必须共用同一条件，恰好两处调用。
    if source.count("self._pending_approvals_where(thread_id)") != 2:
        raise ValueError(f"{SESSION} 的待审批列表与计数必须共用同一过滤条件")
    checked += 1
    # 删除占位超过 800 时必须整次放弃，不能继续拼接巨型 NOT IN。
    if where.count("len(pending_deletions) > 800") != 1:
        raise ValueError(f"{SESSION} 的删除占位上限必须唯一")
    checked += 1
    if "len(pending_deletions) >= 800" in where:
        raise ValueError(f"{SESSION} 的删除占位上限必须严格大于")
    checked += 1
    # 七个类型守卫与六个非空守卫必须完整保留。
    if where.count("typeof(a.") != 7:
        raise ValueError(f"{SESSION} 的待审批过滤必须保留七个类型守卫")
    checked += 1
    if where.count("<>''") != 6:
        raise ValueError(f"{SESSION} 的待审批过滤必须保留六个非空守卫")
    checked += 1
    # 期限范围必须同时有下限与上限，避免外部写入的极大值进入列表。
    if where.count("a.deadline>?") != 1 or where.count("BETWEEN 0 AND 1e15") != 1:
        raise ValueError(f"{SESSION} 的待审批期限必须限定在合理范围")
    checked += 1
    # 删除会话必须用占位符过滤，不能把 id 直接拼进 SQL。
    if where.count("NOT IN (") != 1:
        raise ValueError(f"{SESSION} 的删除会话过滤必须使用占位符")
    checked += 1
    if '" + ",".join("?" for _ in pending_deletions)' not in where:
        raise ValueError(f"{SESSION} 的删除会话过滤必须逐个绑定参数")
    checked += 1
    # 列表必须只多取一行、只按上限切片，并从超出行数得出截断标记。
    if listing.count("parameters.append(limit + 1)") != 1:
        raise ValueError(f"{SESSION} 的待审批列表必须多取一行判定截断")
    checked += 1
    if listing.count("rows[:limit]") != 1 or listing.count("len(rows) > limit") != 1:
        raise ValueError(f"{SESSION} 的待审批列表必须按上限切片并比较截断")
    checked += 1
    if listing.count("_limit(limit, maximum=200)") != 1:
        raise ValueError(f"{SESSION} 的待审批列表条目上限必须唯一")
    checked += 1
    # 计数不受列表上限影响：不得出现 LIMIT 或条目上限校验。
    if "LIMIT" in counts or "_limit(" in counts:
        raise ValueError(f"{SESSION} 的待审批计数不得受列表上限影响")
    checked += 1
    # 列表摘要只回显工具名。
    if listing.count('"summary"') != 1 or "{row['tool_name']}" not in listing:
        raise ValueError(f"{SESSION} 的待审批摘要必须只回显工具名")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_pending_approvals()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError, OSError) as error:
        print(f"待审批分页与计数核对失败，{error}", file=sys.stderr)
        return 2
    print(f"待审批分页与计数一致：{checked} 项过滤、分页与分组校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
