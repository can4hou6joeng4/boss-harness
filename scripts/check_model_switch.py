#!/usr/bin/env python3
"""核对模型线路切换的在途锁与回执令牌。

输入区随通知切换会话卸载，在途锁与失败原因必须按会话留在应用生命周期内：
同一会话同一时间只允许一个设置请求，迟到回执只能结算发起它的那次请求，
匿名预览不能把状态混进会话缓存。这里固定令牌自增、结算核对与实例复用，
避免重复请求或旧回执改写新状态。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SWITCH = "apps/desktop/src/renderer/src/data/modelSwitchState.ts"

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


def check_model_switch() -> int:
    source = _read(SWITCH)
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


def main() -> int:
    try:
        checked = check_model_switch()
    except ValueError as error:
        print(f"模型切换核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型切换一致：{checked} 项在途锁、令牌与实例复用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
