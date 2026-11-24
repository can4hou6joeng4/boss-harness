#!/usr/bin/env python3
"""核对队列读取的代数票据与失效语义。

事件通知、手动刷新与提交核对会并发发起 `queue/list`，返回顺序不保证与
发出顺序一致。这里按会话维护代数：每次读取领票并推进代数，只有票据仍是
最新一代时才允许写入；本地变更通过 `invalidate` 推进代数，让此前发出的
读取全部失效。结构侧固定领票、写入检查与失效顺序；行为侧把真实模块复制到
临时目录，由 Node 直接加载 `createQueueReadGuard`，驱动并发领票、乱序到达、
跨会话隔离与连续失效。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
GUARD = "apps/desktop/src/renderer/src/data/queueReadGuard.ts"

EXPECTED = 15

NODE_SCRIPT = """\
import { createQueueReadGuard } from "./queueReadGuard.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const guard = createQueueReadGuard();
const applied: string[] = [];

const first = guard.issue("a");
expect("首次领票为最新", first.isCurrent() === true);
first.commit(() => applied.push("first"));
expect("最新票据执行写入", applied.join() === "first");

const second = guard.issue("a");
expect("新票据使旧票失效", first.isCurrent() === false && second.isCurrent() === true);
first.commit(() => applied.push("stale"));
expect("旧票据不执行写入", applied.join() === "first");

const other = guard.issue("b");
expect("不同会话互不影响", other.isCurrent() === true && second.isCurrent() === true);

guard.invalidate("a");
expect("失效使票据作废", second.isCurrent() === false);
second.commit(() => applied.push("invalidated"));
expect("失效票据不执行写入", applied.join() === "first");
expect("失效不影响其他会话", other.isCurrent() === true);

const revived = guard.issue("a");
expect("失效后新票有效", revived.isCurrent() === true);
let writes = 0;
revived.commit(() => { writes += 1; });
revived.commit(() => { writes += 1; });
expect("最新票据可重复写入", writes === 2);

const staleTicket = guard.issue("c");
const freshTicket = guard.issue("c");
applied.length = 0;
staleTicket.commit(() => applied.push("old"));
freshTicket.commit(() => applied.push("fresh"));
expect("乱序到达只保留最新", applied.join() === "fresh");

const earlier = guard.issue("d");
const later = guard.issue("d");
applied.length = 0;
later.commit(() => applied.push("later"));
earlier.commit(() => applied.push("earlier"));
expect("新票先写入后旧票仍丢弃", applied.join() === "later");

const dropped = guard.issue("e");
guard.invalidate("e");
guard.invalidate("e");
expect("连续失效后票据作废", dropped.isCurrent() === false);
const recovered = guard.issue("e");
expect("连续失效后新票有效", recovered.isCurrent() === true);

let calls = 0;
dropped.commit(() => { calls += 1; });
expect("无效票据 commit 不执行", calls === 0);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export interface QueueReadTicket {",
    "commit(apply: () => void): void;",
    "isCurrent(): boolean;",
    "export interface QueueReadGuard {",
    "issue(threadId: string): QueueReadTicket;",
    "invalidate(threadId: string): void;",
    "export function createQueueReadGuard(): QueueReadGuard {",
    "const generations = new Map<string, number>();",
    "const current = (threadId: string): number => generations.get(threadId) ?? 0;",
    "const bump = (threadId: string): number => {",
    "const next = current(threadId) + 1;",
    "generations.set(threadId, next);",
    "return next;",
    "issue(threadId: string): QueueReadTicket {",
    "const generation = bump(threadId);",
    "const isCurrent = (): boolean => current(threadId) === generation;",
    "if (isCurrent()) apply();",
    "invalidate(threadId: string): void {",
    "bump(threadId);",
)

ORDERED = (
    # 票据接口：写入与只读判断。
    (
        "export interface QueueReadTicket {",
        "commit(apply: () => void): void;",
        "isCurrent(): boolean;",
    ),
    # 守卫接口：领票与失效。
    (
        "export interface QueueReadGuard {",
        "issue(threadId: string): QueueReadTicket;",
        "invalidate(threadId: string): void;",
    ),
    # 代数：读取当前值、加一、写回、返回。
    (
        "export function createQueueReadGuard(): QueueReadGuard {",
        "const generations = new Map<string, number>();",
        "const current = (threadId: string): number => generations.get(threadId) ?? 0;",
        "const bump = (threadId: string): number => {",
        "const next = current(threadId) + 1;",
        "generations.set(threadId, next);",
        "return next;",
    ),
    # 领票：先推进代数，再快照己方代。
    (
        "issue(threadId: string): QueueReadTicket {",
        "const generation = bump(threadId);",
        "const isCurrent = (): boolean => current(threadId) === generation;",
    ),
    # 写入：只有仍为最新一代才执行。
    (
        "return {",
        "isCurrent,",
        "commit(apply: () => void): void {",
        "if (isCurrent()) apply();",
    ),
    # 失效：只推进代数。
    (
        "invalidate(threadId: string): void {",
        "bump(threadId);",
    ),
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, GUARD)
    for group in ORDERED:
        checked += _ordered(group, source, GUARD)
    # 反向断言：写入必须经过当前代检查；失效不得删除记录；缺失会话从 0 起算。
    if source.count("apply();") != 1:
        raise ValueError(f"{GUARD} 的写入必须经过当前代检查")
    if "generations.delete" in source:
        raise ValueError(f"{GUARD} 的失效必须推进代数，不能删除记录")
    if "?? -1" in source:
        raise ValueError(f"{GUARD} 的缺失会话必须从 0 起算")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(GUARD)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "queueReadGuard.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("队列读取守卫行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"队列读取守卫行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_read_guard.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_read_guard.py")
    if "共 44 项结构、15 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_read_guard.py 检查 44 项结构、15 项行为")
    return 2


def check_queue_read_guard() -> tuple[int, int]:
    source = _read(GUARD)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_read_guard()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"队列读取守卫核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列读取守卫一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
