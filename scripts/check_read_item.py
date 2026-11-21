#!/usr/bin/env python3
"""核对单条目读取 `read_item` 的修订别名、身份冲突与读取上限。

`read_item` 是模型工具结果与界面详情的读取路径：它只投影一个逻辑条目，并把
`revises` 链上的别名保留为可用编号。为避免被外部改写的日志把读取拖垮或冒充身份，
这里固定：请求编号的形状、快照读取、旧记录工具调用回退、修订条目的身份冲突、
修订记录 / 别名数量 / 别名字节三项上限、只继承 kind 与 result、选中条目的冲突
条件，以及失效别名的移除与字节回减。避免重构后读取无限历史、别名泄漏或身份冲突
被静默接受。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 读取顺序：请求校验 → 快照 → 修订目标 → 旧记录回退 → 别名身份冲突 → 三项上限 →
# 继承 kind / result → 选中条目与冲突 → 别名记账 → 失效别名移除。
READ_ORDER = (
    "def read_item(self, thread_id: str, item_id: str) -> dict | None:",
    "if not isinstance(item_id, str) or not item_id or len(item_id) > 128:",
    'raise ValueError("itemId 格式无效")',
    "aliases: set[str] = set()",
    "alias_bytes = 0",
    "revision_records = 0",
    "selected: dict | None = None",
    "with self.open_entries_snapshot(thread_id) as entries:",
    'if entry.get("type") != "item":',
    'payload = dict(entry.get("payload") or {})',
    'entry_id = str(entry.get("id") or "")',
    'target_id = str(payload.get("revises") or "")',
    'if (not target_id and payload.get("kind") == "toolCall"',
    'and payload.get("status") != "running"):',
    'parent_id = str(entry.get("parentId") or "")',
    "if (selected is not None and parent_id in aliases",
    'and selected.get("kind") == "toolCall"):',
    "target_id = parent_id",
    "if target_id in aliases:",
    "if entry_id == item_id:",
    'raise ItemLookupError("INVALID_RESULT_REFERENCE", "结果条目身份存在冲突")',
    "revision_records += 1",
    "if revision_records > MAX_ITEM_REVISION_RECORDS:",
    "if len(entry_id) > 128:",
    'raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订别名超过长度上限")',
    "if entry_id not in aliases and len(aliases) >= MAX_ITEM_REVISION_ALIASES:",
    'alias_bytes += len(entry_id.encode("utf-8"))',
    "if alias_bytes > MAX_ITEM_REVISION_ALIAS_BYTES:",
    'raise ItemLookupError("RESULT_HISTORY_LIMIT", "工具结果修订别名超过大小上限")',
    "aliases.add(entry_id)",
    'selected["kind"] = payload["kind"]',
    'selected["result"] = payload["result"]',
    'if entry_id == item_id:',
    "if selected is not None or target_id or (",
    'and entry.get("parentId")):',
    'raise ItemLookupError("INVALID_RESULT_REFERENCE", "结果条目身份存在冲突")',
    'selected = {"id": item_id, "threadId": thread_id}',
    'for key in ("kind", "result"):',
    "selected[key] = payload[key]",
    "aliases.add(entry_id)",
    'alias_bytes = len(entry_id.encode("utf-8"))',
    "else:",
    "if entry_id in aliases:",
    "aliases.remove(entry_id)",
    'alias_bytes -= len(entry_id.encode("utf-8"))',
    "return selected",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_read_item() -> int:
    source = _read(SESSION)
    start = source.index("def read_item(")
    end = source.find("\n    def ", start + 1)
    reader = source[start:] if end < 0 else source[start:end]
    checked = _ordered(READ_ORDER, reader, SESSION)
    # 三项读取上限各出现一次，避免被放宽或复制成第二道上限。
    for limit in ("MAX_ITEM_REVISION_RECORDS", "MAX_ITEM_REVISION_ALIASES", "MAX_ITEM_REVISION_ALIAS_BYTES"):
        if reader.count(limit) != 1:
            raise ValueError(f"{SESSION} 的读取上限 {limit} 必须唯一")
        checked += 1
    # 只允许从条目读取一次 parentId，且回退前必须已选中工具调用。
    if reader.count('entry.get("parentId")') != 2 or 'payload.get("parentId")' in reader:
        raise ValueError(f"{SESSION} 的旧记录回退只允许读取条目 parentId")
    checked += 1
    # 别名移除必须同时回减字节，避免长期读取后上限被虚高占用。
    if "aliases.remove(entry_id)" not in reader or 'alias_bytes -= len(entry_id.encode("utf-8"))' not in reader:
        raise ValueError(f"{SESSION} 的失效别名必须移除并回减字节")
    checked += 1
    # 身份冲突只接受 INVALID_RESULT_REFERENCE；历史超限只接受 RESULT_HISTORY_LIMIT。
    if reader.count("INVALID_RESULT_REFERENCE") != 2 or reader.count("RESULT_HISTORY_LIMIT") != 4:
        raise ValueError(f"{SESSION} 的读取错误码必须保持身份冲突与历史超限两类")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_read_item()
    except ValueError as error:
        print(f"单条目读取核对失败，{error}", file=sys.stderr)
        return 2
    print(f"单条目读取一致：{checked} 项修订别名、身份冲突与读取上限校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
