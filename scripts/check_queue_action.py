#!/usr/bin/env python3
"""核对队列撤回与重新排队的本地收敛规则。

`queueAction.ts` 区分请求未发出、结果未确认与新项已受理但旧项撤回未确认三种情况，
并在刷新失败时维护本地列表与持久计数：旧项只有确认撤回才移出界面，总数只随新增记录
增加，截断投影只记录分类增量而不把可见数写成内核总数。这里在临时目录改写错误文案
导入后用 Node 加载真实模块，核对提示、拒绝分类、列表过滤与计数合入。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueAction.ts"
QUEUE_MAPPING = "apps/desktop/src/renderer/src/data/queueMapping.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'export type QueueActionOutcome =',
    '| { status: "done" }',
    '| { status: "skipped"; reason: string }',
    '| { status: "uncertain" }',
    'export type QueueRetryOutcome = QueueActionOutcome | { status: "partial" };',
    'export function queueActionNotice(action: "撤回" | "重新排队" | "转为当前回合", outcome: QueueRetryOutcome): string | null {',
    'if (outcome.status === "partial") return "重新排队已受理，但旧队列项撤回结果尚未确认；请先刷新队列，核对并撤回仍保留的旧项，不要重复重新排队。";',
    'if (outcome.status === "skipped") return `${action}没有发出：${outcome.reason}。`;',
    'if (outcome.status === "uncertain") return `${action}结果尚未确认；请先核对队列状态，再决定是否重试。`;',
    "return null;",
    "export function queueRetryRejection(error: unknown): QueueActionOutcome | null {",
    'return isHarnessRpcRejection(error) ? { status: "skipped", reason: harnessErrorText(error) } : null;',
    "export function queueRetryLocalItems(previous: QueueItem[], oldId: string, created: QueueItem,",
    "const kept = previous.filter(item => item.id !== created.id && (!removed || item.id !== oldId));",
    "return [...kept, created];",
    "export function queueRetryPage(page: QueuePage | undefined, previousItems: QueueItem[], oldId: string,",
    "const items = queueRetryLocalItems(previousItems, oldId, created, removed);",
    "const previousOld = (page?.items ?? previousItems).find(entry => entry.id === oldId);",
    "const droppedOld = removed && previousOld !== undefined && isQueueActive(previousOld.status);",
    "const addedCreated = isQueueActive(created.status) ? 1 : 0;",
    'if (typeof page?.activeItems === "number") {',
    "activeItems = Math.max(0, page.activeItems + addedCreated - (droppedOld ? 1 : 0));",
    '} else if (page?.truncated !== true) {',
    "activeItems = items.filter(entry => isQueueActive(entry.status)).length;",
    'if (typeof page?.totalItems === "number") {',
    "totalItems = Math.max(page.totalItems + 1, items.length);",
    '} else if (items.length > 0) {',
    "totalItems = items.length;",
    "const delta = queueCountsDelta(previousItems, items);",
    "const countsDelta = page?.truncated === true ? delta : undefined;",
    "if (page?.counts) {",
    "queued: page.counts.queued + delta.queued,",
    "delivering: page.counts.delivering + delta.delivering,",
    "paused: page.counts.paused + delta.paused,",
    "if (next.queued >= 0 && next.delivering >= 0 && next.paused >= 0",
    "|| next.queued + next.delivering + next.paused === activeItems)) counts = next;",
    "return { items, totalItems, activeItems, counts, truncated: page?.truncated, countsDelta };",
)

STUB = r"""
export function harnessErrorText(error) {
  if (error && typeof error === "object" && error.rpcError === true) {
    const data = error.data && typeof error.data === "object" ? error.data : null;
    const code = data && typeof data.code === "string" ? data.code : "";
    return code ? `RPC ${code}` : "RPC 错误";
  }
  return "本地错误";
}
export function isHarnessRpcRejection(error) {
  return Boolean(error && typeof error === "object" && error.rpcError === true);
}
"""

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { queueActionNotice, queueRetryRejection, queueRetryLocalItems, queueRetryPage } =
  await import(pathToFileURL(process.argv[1]).href);
const item = (id, status = "queued") => ({ id, kind: "followUp", input: "x", status });
const old = () => item("old", "paused");
const other = () => item("other", "queued");
const created = () => item("new", "queued");
const preview = page => ({
  items: page.items.map(entry => entry.id),
  totalItems: page.totalItems ?? null,
  activeItems: page.activeItems ?? null,
  counts: page.counts ?? null,
  truncated: page.truncated ?? null,
  countsDelta: page.countsDelta ?? null,
});
const local = (previous, oldId, createdItem, removed) =>
  queueRetryLocalItems(previous, oldId, createdItem, removed).map(entry => entry.id);
const rejection = value => {
  const result = queueRetryRejection(value);
  return result === null ? null : [result.status, result.reason ?? null];
};
const page = (over = {}) => ({ items: [old(), other()], ...over });
const result = {
  notices: [
    queueActionNotice("撤回", { status: "partial" }),
    queueActionNotice("撤回", { status: "skipped", reason: "连接断开" }),
    queueActionNotice("重新排队", { status: "skipped", reason: "队列已变化" }),
    queueActionNotice("转为当前回合", { status: "skipped", reason: "回合已结束" }),
    queueActionNotice("撤回", { status: "uncertain" }),
    queueActionNotice("重新排队", { status: "uncertain" }),
    queueActionNotice("撤回", { status: "done" }),
    queueActionNotice("重新排队", { status: "done" }),
  ],
  rejections: [
    rejection({ rpcError: true, data: { code: "QUEUE_CONFLICT" } }),
    rejection({ rpcError: true }),
    rejection(new Error("boom")),
    rejection({ rpcError: false, data: { code: "QUEUE_CONFLICT" } }),
    rejection(null),
    rejection({ rpcError: "true", data: { code: "QUEUE_CONFLICT" } }),
  ],
  local: [
    local([old(), other()], "old", created(), true),
    local([old(), other()], "old", created(), false),
    local([old(), other(), created()], "old", created(), true),
    local([], "old", created(), true),
    local([other()], "old", created(), true),
  ],
  pages: [
    preview(queueRetryPage(undefined, [old(), other()], "old", created(), true)),
    preview(queueRetryPage(page({
      totalItems: 5, activeItems: 2, counts: { queued: 1, delivering: 0, paused: 1 }, truncated: false,
    }), [old(), other()], "old", created(), true)),
    preview(queueRetryPage(page({ truncated: true }), [old(), other()], "old", created(), true)),
    preview(queueRetryPage(page({
      totalItems: 3, activeItems: 0, counts: { queued: 0, delivering: 0, paused: 0 },
    }), [old(), other()], "old", created(), true)),
    preview(queueRetryPage(page({
      items: [item("old", "cancelled"), other()],
      totalItems: 5, activeItems: 1, counts: { queued: 1, delivering: 0, paused: 0 },
    }), [item("old", "cancelled"), other()], "old", created(), true)),
    preview(queueRetryPage(page({
      totalItems: 5, activeItems: 2, counts: { queued: 1, delivering: 0, paused: 1 }, truncated: false,
    }), [old(), other()], "old", item("new", "cancelled"), true)),
    preview(queueRetryPage(page({
      items: [item("old", "cancelled"), other()],
      totalItems: 5, activeItems: 3, counts: { queued: 5, delivering: 0, paused: 0 },
    }), [item("old", "cancelled"), other()], "old", created(), true)),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

PARTIAL = "重新排队已受理，但旧队列项撤回结果尚未确认；请先刷新队列，核对并撤回仍保留的旧项，不要重复重新排队。"
EXPECTED_NOTICES = (
    PARTIAL,
    "撤回没有发出：连接断开。",
    "重新排队没有发出：队列已变化。",
    "转为当前回合没有发出：回合已结束。",
    "撤回结果尚未确认；请先核对队列状态，再决定是否重试。",
    "重新排队结果尚未确认；请先核对队列状态，再决定是否重试。",
    None,
    None,
)
EXPECTED_REJECTIONS = (
    ["skipped", "RPC QUEUE_CONFLICT"],
    ["skipped", "RPC 错误"],
    None, None, None, None,
)
EXPECTED_LOCAL = (
    ["other", "new"],
    ["old", "other", "new"],
    ["other", "new"],
    ["new"],
    ["other", "new"],
)
EXPECTED_PAGES = (
    {"items": ["other", "new"], "totalItems": 2, "activeItems": 2, "counts": None, "truncated": None, "countsDelta": None},
    {"items": ["other", "new"], "totalItems": 6, "activeItems": 2, "counts": {"queued": 2, "delivering": 0, "paused": 0}, "truncated": False, "countsDelta": None},
    {"items": ["other", "new"], "totalItems": 2, "activeItems": None, "counts": None, "truncated": True, "countsDelta": {"queued": 1, "delivering": 0, "paused": -1}},
    {"items": ["other", "new"], "totalItems": 4, "activeItems": 0, "counts": None, "truncated": None, "countsDelta": None},
    {"items": ["other", "new"], "totalItems": 6, "activeItems": 2, "counts": {"queued": 2, "delivering": 0, "paused": 0}, "truncated": None, "countsDelta": None},
    {"items": ["other", "new"], "totalItems": 6, "activeItems": 1, "counts": {"queued": 1, "delivering": 0, "paused": 0}, "truncated": False, "countsDelta": None},
    {"items": ["other", "new"], "totalItems": 6, "activeItems": 4, "counts": None, "truncated": None, "countsDelta": None},
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "queueAction.ts"
        stub = Path(directory) / "harnessBridge.mjs"
        source = _read(TARGET).replace(
            'from "./harnessBridge"',
            f'from "{stub.as_uri()}"',
        ).replace(
            'from "./queueMapping"',
            f'from "{(ROOT / QUEUE_MAPPING).as_uri()}"',
        )
        target.write_text(source, encoding="utf-8")
        stub.write_text(STUB, encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 队列操作试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 队列操作试算失败，请核对 Node.js 24+ 与 queueAction.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的队列操作结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回队列操作矩阵")
    for key in ("notices", "rejections", "local", "pages"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"队列操作{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"队列操作{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["notices"], EXPECTED_NOTICES, "提示")
    checked += _compare(payload["rejections"], EXPECTED_REJECTIONS, "拒绝分类")
    checked += _compare(payload["local"], EXPECTED_LOCAL, "本地列表")
    checked += _compare(payload["pages"], EXPECTED_PAGES, "计数投影")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_action.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_action.py")
    if "共 37 项结构、26 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_action.py 检查 37 项结构、26 项行为")
    return 2


def check_queue_action() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_action()
    except (OSError, ValueError) as error:
        print(f"队列操作规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列操作规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
