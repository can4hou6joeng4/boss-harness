#!/usr/bin/env python3
"""核对队列对话框的实时快照同步与未保存草稿保留。

`queueDialogs.ts` 用两个纯函数处理对话框：命中实时条目时替换 item 并保留其他字段，
未命中时普通对话框关闭、编辑对话框只在确有未保存修改时保留原对象。这里静态核对
模块结构，并用 Node 直接加载真实模块覆盖同步、失效与回退分支。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueDialogs.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { QueueItem } from "@boss-harness/protocol";',
    " * 把对话框绑定的条目换成队列投影中的最新快照；条目已消失时返回 null。",
    " * 内核投递、撤回或暂停后，条目会按 id 原位替换成终态并保留在投影里，id 判重",
    " * 不足以发现对话框已经失效：继续展示旧快照会让编辑框承诺「保存后投递的是这段",
    " * 正文」，实际内核只接受 `queued` 条目，保存必然失败。因此对话框跟随实时条目，",
    " * 由调用方按最新状态决定是否还允许保存。",
    "export function syncQueueDialogItem<T extends { item: QueueItem }>(",
    "current: T | null,",
    "items: QueueItem[],",
    "): T | null {",
    "if (!current) return null;",
    "const live = items.find(item => item.id === current.item.id);",
    "return live ? { ...current, item: live } : null;",
    " * 目标移出当前投影后，未保存的编辑正文仍是用户的唯一副本，保留供复制或明确丢弃。",
    " * 调用方必须从当前列表判断能否保存，不能沿用保留快照里的 queued 状态。",
    " * 无修改的编辑窗口仍随目标消失关闭，避免后续新条目复活旧窗口。",
    "export function syncQueueEditDialog<T extends { item: QueueItem; draft: string; originalInput: string }>(",
    "return syncQueueDialogItem(current, items)",
    "?? (current && current.draft !== current.originalInput ? current : null);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { syncQueueDialogItem, syncQueueEditDialog } = await import(pathToFileURL(process.argv[1]).href);
const item = (id, status = "queued") => ({ id, kind: "followUp", input: id, status });
const dlg = (entry, draft, originalInput) => ({ item: entry, draft, originalInput, marker: "m" });
const sig = value => value
  ? `${value.item.id}|${value.item.status}|${value.draft}|${value.originalInput}|${value.marker}`
  : null;
const itemsA = [item("a"), item("b", "paused")];
const itemsB = [item("b", "paused"), item("a", "delivered")];
const curA = dlg(item("a"), "draft", "original");
const curB = dlg(item("b"), "draft", "original");
const curX = dlg(item("x"), "draft", "original");
const cleanX = dlg(item("x"), "same", "same");
const result = {
  dialog: [
    sig(syncQueueDialogItem(null, itemsA)),
    sig(syncQueueDialogItem(curA, itemsB)),
    sig(syncQueueDialogItem(curB, itemsB)),
    sig(syncQueueDialogItem(curX, itemsB)),
    sig(syncQueueDialogItem(curA, itemsA)),
    sig(syncQueueDialogItem(curA, [])),
    sig(syncQueueDialogItem(curA, [item("A")])),
  ],
  edit: [
    sig(syncQueueEditDialog(null, itemsA)),
    sig(syncQueueEditDialog(curA, itemsB)),
    sig(syncQueueEditDialog(curX, itemsB)),
    sig(syncQueueEditDialog(cleanX, itemsB)),
    sig(syncQueueEditDialog(curB, itemsB)),
    sig(syncQueueEditDialog(curX, [])),
    sig(syncQueueEditDialog(cleanX, [])),
    sig(syncQueueEditDialog(dlg(item("a"), "same", "same"), itemsB)),
  ],
  identity: [syncQueueEditDialog(curX, itemsB) === curX],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_DIALOG = (
    None,
    "a|delivered|draft|original|m",
    "b|paused|draft|original|m",
    None,
    "a|queued|draft|original|m",
    None,
    None,
)
EXPECTED_EDIT = (
    None,
    "a|delivered|draft|original|m",
    "x|queued|draft|original|m",
    None,
    "b|paused|draft|original|m",
    "x|queued|draft|original|m",
    None,
    "a|delivered|same|same|m",
)
EXPECTED_IDENTITY = (True,)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 队列对话框试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 队列对话框试算失败，请核对 Node.js 24+ 与 queueDialogs.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的队列对话框结果") from None
    for key in ("dialog", "edit", "identity"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"队列对话框{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"队列对话框{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["dialog"], EXPECTED_DIALOG, "普通对话框")
    checked += _compare(payload["edit"], EXPECTED_EDIT, "编辑对话框")
    checked += _compare(payload["identity"], EXPECTED_IDENTITY, "原对象回退")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_dialogs.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_dialogs.py")
    if "共 19 项结构、16 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_dialogs.py 检查 19 项结构、16 项行为")
    return 2


def check_queue_dialogs() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_dialogs()
    except (OSError, ValueError) as error:
        print(f"队列对话框规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列对话框规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
