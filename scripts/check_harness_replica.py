#!/usr/bin/env python3
"""核对删除会话后在途恢复的抑制顺序与四处守卫。

删除通知到达后，目标会话的在途快照、正文与缓冲增量必须全部失效：迟到结果不能写回
已清理的缓存，当前连接内也不能重新读取。`HarnessReplica` 用删除记号配合既有 epoch /
generation 独立实现；连接重置清除记号，其他会话不受影响。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REPLICA = "apps/desktop/src/renderer/src/data/harnessReplica.ts"

REPLICA_FRAGMENTS = (
    "private readonly deleted = new Set<string>();",
    'if (event.method === "thread/deleted") {',
    "const deletedId = (event.params as { deletedThreadId?: unknown } | undefined)?.deletedThreadId;",
    'if (typeof deletedId === "string" && deletedId) {',
    "this.deleted.add(deletedId);",
    "this.generations.delete(deletedId);",
    "this.loading.delete(deletedId);",
    "this.cursors.delete(deletedId);",
    "this.failures.delete(deletedId);",
    "for (const key of this.itemVersions.keys()) if (key.startsWith(`${deletedId}\\0`)) this.itemVersions.delete(key);",
    "if (id && this.deleted.has(id)) return;",
    "if (epoch !== this.epoch || (id && (this.deleted.has(id) || this.generations.get(id) !== generation)) ||",
    "if (this.deleted.has(threadId)) return Promise.resolve(null);",
    "this.deleted.clear();",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_harness_replica() -> int:
    replica = _read(REPLICA)
    checked = _expect(REPLICA_FRAGMENTS, replica, REPLICA)
    branch_start = replica.find('if (event.method === "thread/deleted") {')
    branch_end = replica.find("const id = event.params?.threadId;", branch_start)
    if branch_start < 0 or branch_end < 0:
        raise ValueError(f"{REPLICA} 缺少删除通知分支")
    branch = replica[branch_start:branch_end]
    # 删除分支：先登记记号，再按会话清理在读状态、游标与条目版本。
    checked += _ordered(
        (
            "this.deleted.add(deletedId);",
            "this.generations.delete(deletedId);",
            "this.loading.delete(deletedId);",
            "this.cursors.delete(deletedId);",
            "this.failures.delete(deletedId);",
            "for (const key of this.itemVersions.keys())",
        ),
        branch,
        REPLICA,
    )
    # 四处守卫：ingest 与 apply 丢弃增量，current 校验阻止迟到页面，resume 直接拒绝重读。
    for guard in (
        "if (id && this.deleted.has(id)) return;",
        "(id && (this.deleted.has(id) || this.generations.get(id) !== generation))",
        "if (this.deleted.has(threadId)) return Promise.resolve(null);",
    ):
        if replica.count(guard) < 1:
            raise ValueError(f"{REPLICA} 缺少删除后守卫：{guard}")
        checked += 1
    if replica.count("if (id && this.deleted.has(id)) return;") < 2:
        raise ValueError(f"{REPLICA} 的 ingest 与 apply 都要丢弃已删除会话的事件")
    # 反向断言：删除分支只清目标会话的条目版本，不整表清空；连接重置才清除删除记号。
    if ".itemVersions.clear()" in branch:
        raise ValueError(f"{REPLICA} 的删除分支不得整表清空条目版本")
    invalidate_start = replica.find("invalidate(")
    invalidate_end = replica.find("ingest(", invalidate_start)
    if invalidate_start < 0 or invalidate_end < 0:
        raise ValueError(f"{REPLICA} 缺少 invalidate 或 ingest")
    invalidate = replica[invalidate_start:invalidate_end]
    checked += _ordered(
        ("this.generations.clear();", "this.itemVersions.clear();", "this.deleted.clear();"),
        invalidate,
        REPLICA,
    )
    return checked


def main() -> int:
    try:
        checked = check_harness_replica()
    except ValueError as error:
        print(f"删除后在途恢复抑制核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除后在途恢复抑制一致：{checked} 项记号、按会话清理与四处守卫")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
