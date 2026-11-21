#!/usr/bin/env python3
"""核对待审批分页与计数的共享过滤口径。

`_pending_approvals_where` 是 `pending_approvals` 与 `pending_approval_counts`
共用的过滤条件：未裁决、运行中回合、未归档会话、期限范围内，列类型与非空
约束必须同时成立，删除占位过多时整次读取放弃。列表用 `limit + 1` 判定是否
还有更多，损坏行按缺失跳过；计数按会话分组，不受列表上限影响。这里按源码
顺序固定这些边界，避免侧栏徽标与列表对不上，或损坏行让整次读取失败。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

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
    except (ValueError, SyntaxError) as error:
        print(f"待审批分页与计数核对失败，{error}", file=sys.stderr)
        return 2
    print(f"待审批分页与计数一致：{checked} 项过滤、分页与分组校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
