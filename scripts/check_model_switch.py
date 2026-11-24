#!/usr/bin/env python3
"""核对模型线路切换的在途锁与回执令牌。

输入区随通知切换会话卸载，在途锁与失败原因必须按会话留在应用生命周期内：
同一会话同一时间只允许一个设置请求，迟到回执只能结算发起它的那次请求，
匿名预览不能把状态混进会话缓存。结构侧固定令牌自增、结算核对与实例复用；
行为侧把真实模块复制到临时目录、以 `react` 桩加载，由 Node 驱动
`modelSwitchFor` / `useModelSwitch` 核对令牌、迟到回执、缓存与订阅。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
SWITCH = "apps/desktop/src/renderer/src/data/modelSwitchState.ts"

EXPECTED = 18

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
import { modelSwitchFor, useModelSwitch } from "./modelSwitchState.ts";
import { storeHooks } from "./reactStub.ts";

interface Snapshot {
  pending: boolean;
  error: string;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const render = (threadId?: string) => useModelSwitch(threadId);

const t1 = modelSwitchFor("t1");
expect("会话实例缓存", modelSwitchFor("t1") === t1 && modelSwitchFor("t2") !== t1);
expect("初始状态为空闲", t1.getSnapshot().pending === false && t1.getSnapshot().error === "");

const token1 = t1.begin();
expect("首次持锁并交出令牌", token1 === 1 && t1.getSnapshot().pending === true);
expect("在途再次申请被拒绝", t1.begin() === null);
t1.settle(token1!, "boom");
expect("结算解锁并记录原因", t1.getSnapshot().pending === false && t1.getSnapshot().error === "boom");
t1.settle(0, "旧回执");
expect("旧令牌结算被忽略", t1.getSnapshot().error === "boom");
const token2 = t1.begin();
expect("再次申请令牌自增", token2 === 2 && t1.getSnapshot().pending === true && t1.getSnapshot().error === "");
t1.settle(1, "迟到回执");
expect("在途时旧令牌不改写锁", t1.getSnapshot().pending === true && t1.getSnapshot().error === "");
t1.settle(2, "");
expect("当前令牌解锁", t1.getSnapshot().pending === false);

const hooked = render("t1");
expect(
  "会话视图复用缓存方法",
  hooked.begin === t1.begin && hooked.settle === t1.settle && hooked.getState === t1.getSnapshot,
);
t1.begin();
const rehooked = render("t1");
expect("会话视图读取缓存状态", rehooked.pending === true);
t1.settle(3, "");

const anon = render();
const anonStore = storeHooks.at(-1)!;
anon.begin();
const anonSnapshot = anonStore.getSnapshot() as Snapshot;
expect("匿名视图持有本地锁", anonSnapshot.pending === true);
expect("匿名锁不影响会话", t1.getSnapshot().pending === false);
const anonAgain = render();
const anonAgainSnapshot = storeHooks.at(-1)!.getSnapshot() as Snapshot;
expect("匿名视图互不共享锁", anonAgainSnapshot.pending === false);

let notified = 0;
const unsubscribe = t1.subscribe(() => { notified += 1; });
const token4 = t1.begin();
expect("订阅者收到通知", notified === 1);
const before = notified;
unsubscribe();
t1.settle(token4!, "x");
expect("退订后不再通知", notified === before);

const idleA = t1.getSnapshot();
const idleB = t1.getSnapshot();
expect("无更新读取复用快照", idleA === idleB);
const beforeSettle = t1.getSnapshot();
t1.settle(4, "x");
expect("结算产生新快照", beforeSettle !== t1.getSnapshot());

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export interface ModelSwitchState {",
    "pending: boolean;",
    "error: string;",
    'let state: ModelSwitchState = { pending: false, error: "" };',
    "let token = 0;",
    "const listeners = new Set<() => void>();",
    "const update = (next: ModelSwitchState) => {",
    "if (next === state) return;",
    "for (const listener of listeners) listener();",
    "getSnapshot: () => state,",
    "subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; },",
    "begin: (): number | null => {",
    "if (state.pending) return null;",
    "token += 1;",
    'update({ pending: true, error: "" });',
    "return token;",
    "settle: (forToken: number, error: string) => {",
    "if (forToken !== token) return;",
    "update({ pending: false, error });",
    "const switches = new Map<string, ReturnType<typeof createSwitches>>();",
    "export function modelSwitchFor(threadId: string) {",
    "const existing = switches.get(threadId);",
    "if (existing) return existing;",
    "switches.set(threadId, created);",
    "const [local] = useState(createSwitches);",
    "const store = threadId ? modelSwitchFor(threadId) : local;",
    "const state = useSyncExternalStore(store.subscribe, store.getSnapshot);",
    "return { ...state, begin: store.begin, settle: store.settle, getState: store.getSnapshot };",
)

ORDERED = (
    # 持锁：在途拒绝 → 令牌自增 → 进入在途并清空错误 → 交出令牌。
    (
        "begin: (): number | null => {",
        "if (state.pending) return null;",
        "token += 1;",
        'update({ pending: true, error: "" });',
        "return token;",
    ),
    # 结算：先核对令牌，再解锁并记录错误。
    (
        "settle: (forToken: number, error: string) => {",
        "if (forToken !== token) return;",
        "update({ pending: false, error });",
    ),
    # 订阅：匿名预览用本地实例，关联会话取缓存实例。
    (
        "const [local] = useState(createSwitches);",
        "const store = threadId ? modelSwitchFor(threadId) : local;",
        "const state = useSyncExternalStore(store.subscribe, store.getSnapshot);",
        "return { ...state, begin: store.begin, settle: store.settle, getState: store.getSnapshot };",
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
        raise ValueError(f"{SWITCH} 的导入结构已变化，需要更新桩")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, SWITCH)
    for group in ORDERED:
        checked += _ordered(group, source, SWITCH)
    # 反向断言：在途时不得交出令牌；结算必须先核对令牌；实例必须复用。
    if "if (state.pending) return token;" in source:
        raise ValueError(f"{SWITCH} 的在途会话不得再次交出令牌")
    if source.index("if (forToken !== token) return;") > source.index("update({ pending: false, error });"):
        raise ValueError(f"{SWITCH} 的迟到回执不得越过令牌核对")
    if "switches.set(threadId, createSwitches());" in source:
        raise ValueError(f"{SWITCH} 必须复用按会话缓存的实例")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(SWITCH)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "modelSwitchState.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("模型切换行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"模型切换行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_model_switch.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_model_switch.py")
    if "共 43 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_model_switch.py 检查 43 项结构、17 项行为")
    return 2


def check_model_switch() -> tuple[int, int]:
    source = _read(SWITCH)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_model_switch()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"模型切换核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型切换一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
