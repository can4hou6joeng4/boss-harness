#!/usr/bin/env python3
"""运行时核对本机时间 hook：只在激活期间按 15 秒重绘，卸载即停。

`useLocalNow.ts` 用 `useReducer` 制造重绘并把 `Date.now()` 直接返回给调用方。
这里把真实模块复制到临时目录，把 `react` 替换为记录 effect 与 dispatch 的桩，
并模拟 `window.setInterval` / `clearInterval`，由 Node 直接加载真实模块，核对
默认定时器周期、首次渲染不刷新、回调触发 dispatch、清理停止定时器、
`active=false` 不注册定时器，以及每次渲染重新取当前时刻。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
SOURCE = "apps/desktop/src/renderer/src/data/useLocalNow.ts"

EXPECTED = 11

REACT_STUB = """\
export interface TimerRecord {
  callback: () => void;
  delay: number;
  cleared: boolean;
}

export const timers: TimerRecord[] = [];
export const hookLog = { effects: [] as Array<{ cleanup?: () => void }>, dispatches: 0 };

(globalThis as { window?: unknown }).window = {
  setInterval(callback: () => void, delay: number): number {
    timers.push({ callback, delay, cleared: false });
    return timers.length;
  },
  clearInterval(handle: number): void {
    timers[handle - 1].cleared = true;
  },
};

export function useEffect(run: () => void | (() => void)): void {
  const cleanup = run();
  hookLog.effects.push({ cleanup: typeof cleanup === "function" ? cleanup : undefined });
}

export function useReducer(
  _reducer: (tick: number) => number,
  initial: number,
): [number, () => void] {
  return [initial, () => { hookLog.dispatches += 1; }];
}
"""

NODE_SCRIPT = """\
import { useLocalNow } from "./useLocalNow.ts";
import { hookLog, timers } from "./reactStub.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const realNow = Date.now;
let stamps = [111, 222, 333];
Date.now = () => stamps.shift() ?? 999;

const first = useLocalNow();
expect("默认读取当前时间", first === 111);
expect("默认注册一个定时器", timers.length === 1);
expect("定时器周期为 15 秒", timers[0].delay === 15_000);
expect("首次渲染不触发刷新", hookLog.dispatches === 0);
timers[0].callback();
expect("定时器回调触发刷新", hookLog.dispatches === 1);
const cleanup = hookLog.effects[0].cleanup;
expect("effect 返回清理函数", typeof cleanup === "function");
cleanup!();
expect("清理停止定时器", timers[0].cleared === true);

const before = timers.length;
const second = useLocalNow(false);
expect("inactive 不注册定时器", timers.length === before);
expect("inactive 仍读取当前时间", second === 222);
expect("inactive 的 effect 无清理", hookLog.effects[1].cleanup === undefined);

const third = useLocalNow();
expect("每次渲染重新取时间", third === 333);

Date.now = realNow;
console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { useEffect, useReducer } from "react";',
    "export function useLocalNow(active = true): number {",
    "const [, refresh] = useReducer((tick: number) => tick + 1, 0);",
    "useEffect(() => {",
    "if (!active) return;",
    "const timer = window.setInterval(() => refresh(), 15_000);",
    "return () => window.clearInterval(timer);",
    "}, [active]);",
    "return Date.now();",
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
    if 'from "./reactStub.ts"' not in rewritten:
        raise ValueError(f"{SOURCE} 的导入结构已变化，需要更新桩")
    return rewritten


def _check_source(source: str) -> int:
    checked = _expect(FRAGMENTS, source, SOURCE)
    if source.index("if (!active) return;") > source.index("window.setInterval"):
        raise ValueError(f"{SOURCE} 必须在未激活时不注册定时器")
    if "Date.now()" not in source.split("return ", 1)[-1]:
        raise ValueError(f"{SOURCE} 必须直接返回当前时刻")
    return checked + 2


def _check_behaviors() -> int:
    source = _read(SOURCE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "useLocalNow.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("本机时间行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"本机时间行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_local_now.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_local_now.py")
    if "共 11 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_local_now.py 检查 11 项结构、11 项行为")
    return 2


def check_local_now() -> tuple[int, int]:
    source = _read(SOURCE)
    structure = _check_source(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_local_now()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"本机时间 hook 核对失败，{error}", file=sys.stderr)
        return 2
    print(f"本机时间 hook 一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
