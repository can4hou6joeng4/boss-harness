#!/usr/bin/env python3
"""核对单飞读取的尾随补跑与取消语义。

轮询、聚焦与通知防抖共用一个读取动作：在途期间的调用只记录尾随标记，
结束后补跑一次；同步抛错也要释放单飞标记；卸载取消后不再补跑。结构侧
固定入口守卫、标记流转与收尾顺序；行为侧把真实模块复制到临时目录，由
Node 直接加载 `createSingleFlightReload`，驱动立即执行、尾随合并、链式
补跑、失败恢复、取消与 `canRun` 门控。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
RELOAD = "apps/desktop/src/renderer/src/data/singleFlightReload.ts"

EXPECTED = 15

NODE_SCRIPT = """\
import { createSingleFlightReload } from "./singleFlightReload.ts";

interface Deferred {
  resolve: () => void;
  reject: (reason?: unknown) => void;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const tick = () => new Promise<void>(resolve => setTimeout(resolve, 0));
function deferred(): Deferred {
  let resolve!: () => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<void>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

async function run(): Promise<void> {
  let autoRuns = 0;
  const auto = createSingleFlightReload(() => { autoRuns += 1; return Promise.resolve(); });
  auto.run();
  await tick();
  expect("空闲调用立即执行", autoRuns === 1);

  let runs = 0;
  const tasks: Deferred[] = [];
  const reload = createSingleFlightReload(() => { runs += 1; const next = deferred(); tasks.push(next); return next.promise; });
  reload.run();
  expect("在途调用不重复执行", runs === 1);
  reload.run();
  reload.run();
  reload.run();
  expect("在途调用只记录尾随", runs === 1);
  tasks[0].resolve();
  await tick();
  expect("结束后补跑一次", runs === 2);
  reload.run();
  tasks[1].resolve();
  await tick();
  expect("补跑期间的新调用再次补跑", runs === 3);
  tasks[2].resolve();
  await tick();
  expect("无尾随时结束不再补跑", runs === 3);

  let failedRuns = 0;
  const failing = createSingleFlightReload(() => { failedRuns += 1; return Promise.reject(new Error("boom")); });
  failing.run();
  await tick();
  failing.run();
  await tick();
  expect("失败后仍可再次运行", failedRuns === 2);

  let syncRuns = 0;
  const throwing = createSingleFlightReload(() => { syncRuns += 1; throw new Error("sync"); });
  throwing.run();
  await tick();
  throwing.run();
  expect("同步抛错释放单飞标记", syncRuns === 2);
  await tick();

  let stoppedRuns = 0;
  const stopped = createSingleFlightReload(() => { stoppedRuns += 1; return Promise.resolve(); });
  stopped.cancel();
  stopped.run();
  expect("取消后不再执行", stoppedRuns === 0);

  let midRuns = 0;
  const midTasks: Deferred[] = [];
  const mid = createSingleFlightReload(() => { midRuns += 1; const next = deferred(); midTasks.push(next); return next.promise; });
  mid.run();
  mid.run();
  mid.cancel();
  midTasks[0].resolve();
  await tick();
  expect("取消后结束不再补跑", midRuns === 1);

  let gate = false;
  let gatedRuns = 0;
  const gated = createSingleFlightReload(() => { gatedRuns += 1; return Promise.resolve(); }, () => gate);
  gated.run();
  expect("canRun 为假时不执行", gatedRuns === 0);
  gate = true;
  gated.run();
  await tick();
  expect("canRun 放行后执行", gatedRuns === 1);

  let tailGate = true;
  let tailRuns = 0;
  const tailTasks: Deferred[] = [];
  const tailed = createSingleFlightReload(() => { tailRuns += 1; const next = deferred(); tailTasks.push(next); return next.promise; }, () => tailGate);
  tailed.run();
  tailed.run();
  tailGate = false;
  tailTasks[0].resolve();
  await tick();
  expect("尾随补跑遵守 canRun", tailRuns === 1);

  let priorityRuns = 0;
  const priority = createSingleFlightReload(() => { priorityRuns += 1; return Promise.resolve(); }, () => true);
  priority.cancel();
  priority.run();
  expect("取消优先于 canRun", priorityRuns === 0);

  let retryRuns = 0;
  const retryTasks: Deferred[] = [];
  const retried = createSingleFlightReload(() => { retryRuns += 1; const next = deferred(); retryTasks.push(next); return next.promise; });
  retried.run();
  retried.run();
  retryTasks[0].reject(new Error("boom"));
  await tick();
  expect("失败后仍补跑尾随", retryRuns === 2);
  retryTasks[1].resolve();
  await tick();

  console.log(`PASS ${passed}`);
}

await run();
"""

FRAGMENTS = (
    "export interface SingleFlightReload {",
    "run(): void;",
    "cancel(): void;",
    "export function createSingleFlightReload(",
    "task: () => Promise<void>,",
    "canRun: () => boolean = () => true,",
    "): SingleFlightReload {",
    "let inFlight = false;",
    "let pending = false;",
    "let cancelled = false;",
    "if (cancelled || !canRun()) return;",
    "if (inFlight) {",
    "pending = true;",
    "inFlight = true;",
    "flight = task();",
    "flight = Promise.resolve();",
    "void flight.catch(() => {",
    "}).finally(() => {",
    "if (cancelled || !pending) return;",
    "pending = false;",
    "run();",
    "cancelled = true;",
)

ORDERED = (
    # 入口：先判取消与 canRun，再判在途。
    (
        "const run = (): void => {",
        "if (cancelled || !canRun()) return;",
        "if (inFlight) {",
        "pending = true;",
        "return;",
        "}",
        "inFlight = true;",
    ),
    # 同步抛错也转成已解决的 Promise。
    (
        "let flight: Promise<void>;",
        "try {",
        "flight = task();",
        "} catch {",
        "flight = Promise.resolve();",
    ),
    # 链尾释放单飞标记，再按取消与尾随标记决定是否补跑。
    (
        "void flight.catch(() => {",
        "}).finally(() => {",
        "inFlight = false;",
        "if (cancelled || !pending) return;",
        "pending = false;",
        "run();",
    ),
    # 取消：清除取消与尾随标记，不直接补跑。
    (
        "cancel() {",
        "cancelled = true;",
        "pending = false;",
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
    checked += _expect(FRAGMENTS, source, RELOAD)
    for group in ORDERED:
        checked += _ordered(group, source, RELOAD)
    # 反向断言：单飞标记只在声明与收尾出现；尾随标记只在补跑与取消清除；
    # 不得用延时轮询代替尾随补跑。
    if source.count("inFlight = false;") != 2:
        raise ValueError(f"{RELOAD} 的单飞标记只能在收尾释放")
    if source.count("pending = false;") != 3:
        raise ValueError(f"{RELOAD} 的尾随标记只在补跑与取消时清除")
    if "setTimeout" in source:
        raise ValueError(f"{RELOAD} 不得用延时轮询代替尾随补跑")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(RELOAD)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "singleFlightReload.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("单飞读取行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"单飞读取行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_single_flight.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_single_flight.py")
    if "共 46 项结构、15 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_single_flight.py 检查 46 项结构、15 项行为")
    return 2


def check_single_flight() -> tuple[int, int]:
    source = _read(RELOAD)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_single_flight()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"单飞读取核对失败，{error}", file=sys.stderr)
        return 2
    print(f"单飞读取一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
