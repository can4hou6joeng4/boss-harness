#!/usr/bin/env python3
"""运行时核对队列草稿编辑器：保存锁、回执与按会话隔离。

`queueEditDrafts.ts` 里的编辑正文与保存回执共用生命周期：同一会话同一时间
只允许一次保存，保存中切换草稿或重复提交都不能绕过同步锁，成功回执清空
草稿，失败保留正文并给出可读提示。这里把真实模块复制到临时目录，把
`react` 与 `./harnessBridge` 替换为桩，由 Node 直接加载真实模块并驱动
`useQueueEditor`，核对匿名实例隔离、按会话缓存、持锁、回执与订阅语义。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
SOURCE = "apps/desktop/src/renderer/src/data/queueEditDrafts.ts"

EXPECTED = 24

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

BRIDGE_STUB = """\
export function harnessErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
"""

NODE_SCRIPT = """\
import { useQueueEditor } from "./queueEditDrafts.ts";
import { storeHooks } from "./reactStub.ts";

interface View {
  editing: { draft: string } | null;
  saving: boolean;
  editError: string;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const item = (id: string) => ({ id, threadId: "thread", input: "原文" } as never);
const draft = (id: string, text = "草稿") => ({ item: item(id), draft: text, originalInput: "原文" });
const view = (threadId?: string) => useQueueEditor(threadId);
const snapshot = () => storeHooks.at(-1)!.getSnapshot() as View;

const anon = view();
anon.setEditing(draft("anon-1"));
expect("匿名面板保留草稿", snapshot().editing?.draft === "草稿");
view();
expect("匿名面板互不影响", snapshot().editing === null);

const thread = view("thread-1");
thread.setEditing(draft("q1"));
expect("会话草稿写入缓存", view("thread-1").editing?.draft === "草稿");
expect("不同会话隔离", view("thread-2").editing === null);
expect("同会话方法复用", view("thread-1").setEditing === thread.setEditing);

let release!: () => void;
const gate = new Promise<void>(resolve => { release = resolve; });
let writes = 0;
const first = view("thread-1").saveEditing(async () => { writes += 1; await gate; });
expect("保存立即持锁", view("thread-1").saving === true);
expect("持锁时清空旧错误", view("thread-1").editError === "");
await view("thread-1").saveEditing(async () => { writes += 1; });
expect("保存中重复提交被忽略", writes === 1);
release();
await first;
expect("保存成功清空草稿", view("thread-1").editing === null);
expect("保存成功解除锁定", view("thread-1").saving === false && view("thread-1").editError === "");

const failing = view("thread-3");
failing.setEditing(draft("q3", "失败草稿"));
await view("thread-3").saveEditing(async () => { throw new Error("boom"); });
const failed = view("thread-3");
expect("失败保留草稿", failed.editing?.draft === "失败草稿");
expect("失败解除锁定", failed.saving === false);
expect(
  "失败文案可读",
  failed.editError.startsWith("保存失败：boom") && failed.editError.includes("草稿仍保留在编辑框中"),
);

const entry = storeHooks.at(-1)!;
let notified = 0;
const unsubscribe = entry.subscribe(() => { notified += 1; });
view("thread-3").setEditError("另一个错误");
expect("订阅者收到通知", notified === 1);
const before = notified;
unsubscribe();
view("thread-3").setEditError("退订后的错误");
expect("退订后不再通知", notified === before);
const snapA = entry.getSnapshot();
view("thread-3").setEditError("相同错误");
const snapB = entry.getSnapshot();
view("thread-3").setEditError("相同错误");
expect("状态变化产生新快照", snapA !== snapB);
expect("相同状态复用快照", snapB === entry.getSnapshot());

view("thread-4").setEditing(() => draft("q4", "函数式"));
expect("函数式更新生效", view("thread-4").editing?.draft === "函数式");

let releaseSwitch!: () => void;
const switchGate = new Promise<void>(resolve => { releaseSwitch = resolve; });
const switching = view("thread-5");
switching.setEditing(draft("q5", "第一版"));
const pending = switching.saveEditing(async () => { await switchGate; });
switching.setEditing(draft("q5", "第二版"));
expect("保存期间仍可编辑", view("thread-5").editing?.draft === "第二版");
releaseSwitch();
await pending;
expect("成功回执清空被切换的草稿", view("thread-5").editing === null);

const retrying = view("thread-6");
retrying.setEditing(draft("q6", "重试"));
await view("thread-6").saveEditing(async () => { throw new Error("first"); });
expect("失败后保留错误", view("thread-6").editError !== "");
await view("thread-6").saveEditing(async () => {});
expect("重试成功清空草稿与错误", view("thread-6").editing === null && view("thread-6").editError === "");
view("thread-6").setEditing(draft("q6b", "再次"));
await view("thread-6").saveEditing(async () => {});
expect("失败后可再次保存", view("thread-6").editing === null);

const beforeWrites = writes;
await view("thread-7").saveEditing(async () => { writes += 1; });
expect("无草稿不写入", writes === beforeWrites && view("thread-7").saving === false);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export interface QueueEditDraft {",
    "item: QueueItem;",
    "draft: string;",
    "originalInput: string;",
    "function createEditor() {",
    "if (next === state) return;",
    "saveEditing: async (write: (draft: QueueEditDraft) => Promise<unknown>) => {",
    "if (!submitted || state.saving) return;",
    'update({ ...state, saving: true, editError: "" });',
    'update({ editing: null, saving: false, editError: "" });',
    "const editors = new Map<string, ReturnType<typeof createEditor>>();",
    "export function useQueueEditor(threadId?: string) {",
    "const [localEditor] = useState(createEditor);",
    "const state = useSyncExternalStore(editor.subscribe, editor.getSnapshot);",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _rewrite(source: str) -> str:
    rewritten = source.replace('from "react"', 'from "./reactStub.ts"')
    rewritten = rewritten.replace('from "./harnessBridge"', 'from "./harnessBridge.ts"')
    if 'from "./reactStub.ts"' not in rewritten or 'from "./harnessBridge.ts"' not in rewritten:
        raise ValueError(f"{SOURCE} 的导入结构已变化，需要更新桩")
    return rewritten


def _check_source(source: str) -> int:
    checked = _expect(FRAGMENTS, source, SOURCE)
    if source.index("if (!submitted || state.saving) return;") > source.index(
        'update({ ...state, saving: true, editError: "" });'
    ):
        raise ValueError(f"{SOURCE} 必须先持锁再发起写入")
    if source.index("const [localEditor] = useState(createEditor);") > source.index(
        "const existing = editors.get(threadId);"
    ):
        raise ValueError(f"{SOURCE} 必须先建立匿名实例再查会话缓存")
    if "update({ editing: null, saving: false });" in source:
        raise ValueError(f"{SOURCE} 失败结算不得清空编辑草稿")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(SOURCE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "queueEditDrafts.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        (folder / "harnessBridge.ts").write_text(BRIDGE_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("队列草稿行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"队列草稿行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_edit_drafts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_edit_drafts.py")
    if "共 17 项结构、24 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_edit_drafts.py 检查 17 项结构、24 项行为")
    return 2


def check_queue_edit_drafts() -> tuple[int, int]:
    source = _read(SOURCE)
    structure = _check_source(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_edit_drafts()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"队列草稿编辑器核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列草稿编辑器一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
