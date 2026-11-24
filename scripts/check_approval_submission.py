#!/usr/bin/env python3
"""运行时核对审批提交状态机：按会话缓存、在途锁、记住选择与删除失效。

对话区会随通知切换会话卸载，审批提交的在途锁、失败原因与「本次会话记住
选择」必须留在应用生命周期内：同一会话同一时间只允许一张卡提交，迟到回执
只结算发起时的实例，删除会话后的旧实例不得再写入。结构侧固定实例缓存、
结算核对、记住记录与删除入口；行为侧把真实 `approvalSubmission.ts` 复制到
临时目录、以 `react` 桩加载，由 Node 驱动持锁、迟到回执、记住写删、订阅与
快照、删除失效与匿名视图。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
APPROVAL = "apps/desktop/src/renderer/src/data/approvalSubmission.ts"

EXPECTED = 27

REACT_STUB = """\
export const storeHooks: Array<{ subscribe: (cb: () => void) => () => void; getSnapshot: () => unknown }> = [];

export function useState<T>(init: T | (() => T)): [T, (next: T) => void] {
  const value = typeof init === "function" ? (init as () => T)() : init;
  return [value, () => {}];
}

export function useSyncExternalStore<T>(
  subscribe: (cb: () => void) => () => void,
  getSnapshot: () => T,
): T {
  storeHooks.push({ subscribe, getSnapshot });
  return getSnapshot();
}
"""

NODE_SCRIPT = """\
import {
  approvalSubmissionFor,
  approvalSubmissionIsCurrent,
  forgetApprovalSubmission,
  useApprovalSubmission,
} from "./approvalSubmission.ts";
import { storeHooks } from "./reactStub.ts";

interface SubmissionState {
  pendingMessageId: string | null;
  error: string;
  remember: Record<string, boolean>;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const a = approvalSubmissionFor("a");
expect("会话实例缓存", approvalSubmissionFor("a") === a && approvalSubmissionFor("b") !== a);
const initial = a.getSnapshot() as SubmissionState;
expect("初始状态为空闲", initial.pendingMessageId === null && initial.error === "" && Object.keys(initial.remember).length === 0);
expect("实例状态互相隔离", approvalSubmissionFor("b").getSnapshot() !== a.getSnapshot());

a.begin("m1");
expect("持锁并清空错误", a.getSnapshot().pendingMessageId === "m1" && a.getSnapshot().error === "");
a.begin("m2");
expect("后发提交改写在途卡", a.getSnapshot().pendingMessageId === "m2");
a.settle("m1", "旧卡失败");
expect("迟到回执不结算新卡", a.getSnapshot().pendingMessageId === "m2" && a.getSnapshot().error === "");
a.settle("m2", "boom");
expect("结算当前卡并记录错误", a.getSnapshot().pendingMessageId === null && a.getSnapshot().error === "boom");
a.begin("m3");
expect("新提交清空错误", a.getSnapshot().error === "");
a.settle("m3", "");
expect("成功结算清锁并保留空错误", a.getSnapshot().pendingMessageId === null && a.getSnapshot().error === "");

a.reportError("自动批准失败");
expect("自动批准错误不改锁", a.getSnapshot().pendingMessageId === null && a.getSnapshot().error === "自动批准失败");

a.setRemember("m1", true);
expect("记住写入目标卡", a.getSnapshot().remember.m1 === true);
a.setRemember("m2", true);
a.setRemember("m1", false);
expect("取消记住删除记录", !("m1" in a.getSnapshot().remember));
expect("记住只影响目标卡", a.getSnapshot().remember.m2 === true);

let notified = 0;
const unsubscribe = a.subscribe(() => { notified += 1; });
a.begin("m4");
expect("订阅者收到通知", notified === 1);
unsubscribe();
a.settle("m4", "");
expect("退订后不再通知", notified === 1);
const snapshotA = a.getSnapshot();
const snapshotB = a.getSnapshot();
expect("无更新读取复用快照", snapshotA === snapshotB);

const b = approvalSubmissionFor("b");
b.reportError("另一会话");
expect("其他会话不受影响", a.getSnapshot().error === "" && b.getSnapshot().error === "另一会话");

const hooked = useApprovalSubmission("a");
expect("会话视图复用缓存方法", hooked.getState === approvalSubmissionFor("a").getSnapshot);

const anon = useApprovalSubmission();
const anonStore = storeHooks.at(-1)!;
const anonAgain = useApprovalSubmission();
const anonAgainStore = storeHooks.at(-1)!;
expect("匿名视图持有本地实例", anonStore.getSnapshot() !== anonAgainStore.getSnapshot());
expect("匿名视图不混入会话状态", (anonStore.getSnapshot() as SubmissionState).error === "");

expect("实例归属为真", approvalSubmissionIsCurrent("a", a) === true);
expect("归属核对不创建实例", approvalSubmissionIsCurrent("missing", a) === false);
expect("删除存在的会话", forgetApprovalSubmission("a") === true);
expect("删除后旧实例失效", approvalSubmissionIsCurrent("a", a) === false);
const fresh = approvalSubmissionFor("a");
expect("删除后取用新实例", fresh !== a && fresh.getSnapshot().pendingMessageId === null);
expect("删除空标识", forgetApprovalSubmission("") === false);
expect("删除不存在的会话", forgetApprovalSubmission("none") === false);

void anon;
void anonAgain;

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { useState, useSyncExternalStore } from "react";',
    "function createSubmissions() {",
    'let state: ApprovalSubmissionState = { pendingMessageId: null, error: "", remember: {} };',
    "const listeners = new Set<() => void>();",
    "if (next === state) return;",
    "for (const listener of listeners) listener();",
    "getSnapshot: () => state,",
    'begin: (messageId: string) => update({ ...state, pendingMessageId: messageId, error: "" }),',
    "if (state.pendingMessageId !== messageId) return;",
    "update({ ...state, pendingMessageId: null, error });",
    "reportError: (error: string) => update({ ...state, error }),",
    "if (checked) remember[messageId] = true; else delete remember[messageId];",
    "const submissions = new Map<string, ReturnType<typeof createSubmissions>>();",
    "export function approvalSubmissionFor(threadId: string) {",
    "if (existing) return existing;",
    "submissions.set(threadId, created);",
    "export function approvalSubmissionIsCurrent(threadId: string, submission: ReturnType<typeof approvalSubmissionFor>): boolean {",
    "return submissions.get(threadId) === submission;",
    "export function forgetApprovalSubmission(threadId: string): boolean {",
    "if (!threadId) return false;",
    "return submissions.delete(threadId);",
    "const store = threadId ? approvalSubmissionFor(threadId) : local;",
    "return { ...state, setRemember: store.setRemember, getState: store.getSnapshot };",
)

ORDERED = (
    # 更新：同一引用直接返回，换引用后通知。
    (
        "const update = (next: ApprovalSubmissionState) => {",
        "if (next === state) return;",
        "state = next;",
        "for (const listener of listeners) listener();",
    ),
    # 结算：先核对发起时的卡，再清锁并记录错误。
    (
        "settle: (messageId: string, error: string) => {",
        "if (state.pendingMessageId !== messageId) return;",
        "update({ ...state, pendingMessageId: null, error });",
    ),
    # 记住：先复制记录，再按勾选写入或删除，最后整体替换。
    (
        "setRemember: (messageId: string, checked: boolean) => {",
        "const remember = { ...state.remember };",
        "if (checked) remember[messageId] = true; else delete remember[messageId];",
        "update({ ...state, remember });",
    ),
    # 缓存：先查已有实例，再创建并入表。
    (
        "export function approvalSubmissionFor(threadId: string) {",
        "const existing = submissions.get(threadId);",
        "if (existing) return existing;",
        "const created = createSubmissions();",
        "submissions.set(threadId, created);",
    ),
    # 视图：匿名用本地实例，关联会话取缓存实例。
    (
        "const [local] = useState(createSubmissions);",
        "const store = threadId ? approvalSubmissionFor(threadId) : local;",
        "const state = useSyncExternalStore(store.subscribe, store.getSnapshot);",
        "return { ...state, setRemember: store.setRemember, getState: store.getSnapshot };",
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


def _rewrite(source: str) -> str:
    rewritten = source.replace('from "react"', 'from "./reactStub.ts"')
    if 'from "./reactStub.ts"' not in rewritten:
        raise ValueError(f"{APPROVAL} 的导入结构已变化，需要更新桩")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, APPROVAL)
    for group in ORDERED:
        checked += _ordered(group, source, APPROVAL)
    # 反向断言：实例创建与删除各只有一处入口；状态只能整体替换。
    if source.count("submissions.set(") != 1:
        raise ValueError(f"{APPROVAL} 的实例只能在缓存缺失时创建")
    if source.count("submissions.delete(") != 1:
        raise ValueError(f"{APPROVAL} 的实例只能由删除入口移除")
    if "state.pendingMessageId = " in source:
        raise ValueError(f"{APPROVAL} 的状态必须整体替换，不能原地修改")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(APPROVAL)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "approvalSubmission.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("审批提交行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"审批提交行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_approval_submission.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_approval_submission.py")
    if "共 46 项结构、27 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_approval_submission.py 检查 46 项结构、27 项行为")
    return 2


def check_approval_submission() -> tuple[int, int]:
    source = _read(APPROVAL)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_approval_submission()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"审批提交状态机核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批提交状态机一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
