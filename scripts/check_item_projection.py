#!/usr/bin/env python3
"""核对条目投影 `_project_items` 的编号收敛、修订合并与旧记录回退。

条目投影把日志里的 item 记录合并成逻辑条目：空编号跳过；`revises` 指向已投影的
条目时把载荷合并进同一槽位并保留原编号与 threadId；旧记录里非 running 的工具调用
可以用 `parentId` 回退到父工具条目；编号字段只保留字符串，非对象 approval 删除；
同编号的新条目只保留先出现的一条。这里固定这些规则，避免重构后编辑、压缩、分叉
与快照按编号定位时同时命中多条消息，或让修订覆盖原条目身份。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

# 投影顺序：跳过非 item → 编号与修订目标 → 工具调用回退 → 编号字段与审批清理 →
# 修订合并到原槽位 → 同编号只保留先出现 → 新条目追加。
PROJECT_ORDER = (
    "def _project_items(thread_id: str, entries: list[dict]) -> list[dict]:",
    "items: list[dict] = []",
    "index_by_id: dict[str, int] = {}",
    'if entry.get("type") != "item":',
    'payload = dict(entry.get("payload") or {})',
    'entry_id = _record_id(entry.get("id")) or ""',
    "if not entry_id:",
    "continue",
    'target_id = _record_id(payload.get("revises")) or ""',
    'if not target_id and payload.get("kind") == "toolCall" and payload.get("status") != "running":',
    'parent_id = str(entry.get("parentId") or "")',
    'if parent_id in index_by_id and items[index_by_id[parent_id]].get("kind") == "toolCall":',
    "target_id = parent_id",
    "for field in _ITEM_ID_FIELDS:",
    "if field in payload and not isinstance(payload[field], str):",
    "del payload[field]",
    'if "approval" in payload and not isinstance(payload["approval"], dict):',
    'del payload["approval"]',
    "if target_id and target_id in index_by_id:",
    "slot = index_by_id[target_id]",
    'items[slot] = {**items[slot], **payload, "id": items[slot]["id"], "threadId": thread_id}',
    "index_by_id[entry_id] = slot",
    "if entry_id in index_by_id:",
    "continue",
    "index_by_id[entry_id] = len(items)",
    'items.append({**payload, "id": entry_id, "threadId": thread_id})',
    "return items",
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


def check_item_projection() -> int:
    source = _read(SESSION)
    start = source.index("def _project_items(")
    end = source.find("\n    def ", start + 1)
    projection = source[start:] if end < 0 else source[start:end]
    checked = _ordered(PROJECT_ORDER, projection, SESSION)
    # 修订合并必须保留原槽位编号；新条目是唯一追加路径。
    if projection.count('"id": items[slot]["id"]') != 1 or projection.count("items.append(") != 1:
        raise ValueError(f"{SESSION} 的修订合并必须保留原编号且只有新条目才追加")
    checked += 1
    # 同编号条目只保留先出现的一条：重复分支必须 continue，不能覆盖或再次追加。
    if projection.count("if entry_id in index_by_id:") != 1:
        raise ValueError(f"{SESSION} 的重复编号必须保留先出现的条目")
    duplicate = projection.index("if entry_id in index_by_id:")
    if "continue" not in projection[duplicate:duplicate + 400]:
        raise ValueError(f"{SESSION} 的重复编号必须保留先出现的条目")
    checked += 1
    # parentId 只在旧记录工具调用回退处读取一次，不能从 payload 或其它位置读取。
    if projection.count('entry.get("parentId")') != 1 or 'payload.get("parentId")' in projection:
        raise ValueError(f"{SESSION} 的条目投影只允许旧记录工具调用回退读取 parentId")
    checked += 1
    # 非字符串编号字段与非对象审批都必须删除，不能只跳过或改名。
    if projection.count("del payload[field]") != 1 or projection.count('del payload["approval"]') != 1:
        raise ValueError(f"{SESSION} 的条目投影必须清理非字符串编号字段与非对象审批")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_item_projection()
    except ValueError as error:
        print(f"条目投影核对失败，{error}", file=sys.stderr)
        return 2
    print(f"条目投影一致：{checked} 项编号、修订与回退校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
