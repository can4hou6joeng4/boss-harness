#!/usr/bin/env python3
"""核对会话分叉的复制边界、记录改写与源日志只读约束。

`fork_thread` 只复制当前分支的一个已结束回合前缀：排除 `thread_info` / `queue` /
`task_phase` 等内核专用记录，按 owner 归属迟到修订，拒绝拆开工具批次，并在副本里
改写 parentId、threadId、approvalId 与 continuationRequestOffset，最后按复制前缀
重算继承的续接边界摘要。漏掉任一改写会让分支会话与源会话共享歧义状态；复制过程
改写源日志则会静默污染来源会话。这里固定这些不变量，避免重构时无声退化。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 分支选择、前缀裁剪与拒绝条件。
SELECT_MARK = (
    "raw_entries = self.read_entries(thread_id)",
    "entries = self._active_entries(raw_entries)",
    'synthetic = Entry(type=LEAF_ENTRY_TYPE, parent_id=records[-1]["id"],',
    'or selected.get("status") not in _TERMINAL):',
    'raise ValueError("仅可从已经结束的回合创建分支")',
    'cutoff = selected.get("boundaryOrdinal", selected["lastOrdinal"])',
    "return position is not None and position <= selected_position",
    "prefix = [entry for entry in entries[:cutoff + 1]",
    "owners = self._item_owners(entries)",
    'owners.get(entry["id"]) in included_turns',
    'raise ValueError("回合中仍有未收尾条目或审批，不能创建分支")',
    'raise ValueError("分支边界会拆开工具批次")',
)
# 新会话头：派生字段不继承，来源标识另行写入。
HEADER_MARK = (
    'if key not in {"id", "sessionId", "createdAt", "updatedAt", "lastTurn",',
    'if source.get("projectIdTruncated"):',
    'header.pop("projectId", None)',
    'forkedFromId=thread_id, forkedFromTurnId=selected["turnId"]',
)
# 复制循环：排除内核专用记录并改写跨会话引用。
COPY_MARK = (
    'if entry["type"] in {"thread_info", "queue", "task_phase"}:',
    'entry["payload"]["continuationRequestOffset"] = request_offset',
    'and owners.get(_record_id(entry["payload"].get("targetItemId"))) not in included_turns):',
    'if entry.get("parentId") not in copied_ids:',
    'if entry["payload"].get("threadId") == thread_id:',
    "approval_ids[approval_id] = uuid.uuid4().hex",
)
COPY_ORDER = (
    "def fork_thread(",
    "for entry in json.loads(_json(prefix)):",
    'if entry.get("parentId") not in copied_ids:',
    'entry["payload"]["threadId"] = header["id"]',
    "approval_ids[approval_id] = uuid.uuid4().hex",
    "copied.append(entry)",
    "copied_ids.add(entry[\"id\"])",
    "_rehash_continuation_boundaries(copied)",
    "return self._write_new(header, copied)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_session_fork() -> int:
    source = _read(SESSION)
    start = source.index("def fork_thread(")
    end = source.find("\n    def ", start + 1)
    fork = source[start:] if end < 0 else source[start:end]
    checked = _expect(SELECT_MARK, fork, SESSION)
    checked += _expect(HEADER_MARK, fork, SESSION)
    checked += _expect(COPY_MARK, fork, SESSION)
    checked += _ordered(COPY_ORDER, fork, SESSION)
    # 只复制当前分支：两条选择路径（当前分支与合成 leaf）都必须经过 _active_entries。
    if fork.count("_active_entries(") != 2:
        raise ValueError(f"{SESSION} 的分叉必须只按当前分支复制（两条选择路径各一次）")
    # 源日志只读：副本只能通过 _write_new 写成新会话，不得追加到来源会话。
    for forbidden in ("self.append(", "self.record_turn(", "self._append_line("):
        if forbidden in fork:
            raise ValueError(f"{SESSION} 的分叉不得改写源日志：{forbidden}")
    if "return self._write_new(header, copied)" not in fork:
        raise ValueError(f"{SESSION} 的分叉必须只写新会话")
    checked += 4
    return checked


def main() -> int:
    try:
        checked = check_session_fork()
    except ValueError as error:
        print(f"会话分叉核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话分叉一致：{checked} 项分支复制、记录改写与源日志只读校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
