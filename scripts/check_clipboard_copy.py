#!/usr/bin/env python3
"""核对剪贴板写入结果与迟到回执的失效。

界面只有在真正写入成功后才显示「已复制」；失败原因只用于提示，不能
包含被复制的正文。连续点击时用版本令牌丢弃迟到回执，重置或卸载后清除
计时器，避免旧提示重新出现或卸载后继续更新状态。结构侧固定写入路径、
原因截断与清理顺序；行为侧把真实模块复制到临时目录，以 `react`、
共享包与计时器桩加载，由 Node 驱动 `copyText` 与 `useClipboardCopy`。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
CLIPBOARD = "apps/desktop/src/renderer/src/data/clipboardCopy.ts"

EXPECTED = 23

REACT_STUB = """\
export interface Slot {
  value: unknown;
}

export const slots: Slot[] = [];
export let effectCleanup: (() => void) | undefined;
let renderIndex = 0;
let mounted = false;

export function beginRender(): void {
  renderIndex = 0;
}

export function reset(): void {
  slots.length = 0;
  renderIndex = 0;
  mounted = false;
  effectCleanup = undefined;
}

export function useState<T>(init: T | (() => T)): [T, (next: T | ((prev: T) => T)) => void] {
  const index = renderIndex++;
  if (!slots[index]) {
    slots[index] = { value: typeof init === "function" ? (init as () => T)() : init };
  }
  const slot = slots[index];
  const set = (next: T | ((prev: T) => T)) => {
    slot.value = typeof next === "function" ? (next as (prev: T) => T)(slot.value) : next;
  };
  return [slot.value as T, set];
}

export function useRef<T>(initial: T): { current: T } {
  const index = renderIndex++;
  if (!slots[index]) {
    slots[index] = { value: { current: initial } };
  }
  return slots[index].value as { current: T };
}

export function useCallback<T>(callback: T): T {
  return callback;
}

export function useEffect(run: () => void | (() => void)): void {
  if (mounted) return;
  mounted = true;
  const cleanup = run();
  effectCleanup = typeof cleanup === "function" ? cleanup : undefined;
}
"""

SHARED_STUB = """\
export function safeSlice(text: string, end: number): string {
  const limit = Math.min(Math.floor(end), text.length);
  if (!Number.isFinite(limit) || limit <= 0) return "";
  const last = text.charCodeAt(limit - 1);
  return text.slice(0, last >= 0xd800 && last <= 0xdbff ? limit - 1 : limit);
}
"""

TIMERS_STUB = """\
export interface TimerRecord {
  callback: () => void;
  delay: number;
  cleared: boolean;
}

export const timers: TimerRecord[] = [];
const handles = new Map<number, TimerRecord>();
let nextHandle = 0;

(globalThis as { setTimeout?: unknown }).setTimeout = (callback: () => void, delay: number) => {
  nextHandle += 1;
  const record = { callback, delay, cleared: false };
  timers.push(record);
  handles.set(nextHandle, record);
  return nextHandle;
};
(globalThis as { clearTimeout?: unknown }).clearTimeout = (handle: number) => {
  const record = handles.get(handle);
  if (record) record.cleared = true;
};
"""

NODE_SCRIPT = """\
import { copyText, useClipboardCopy } from "./clipboardCopy.ts";
import { beginRender, effectCleanup, reset } from "./reactStub.ts";
import { timers } from "./timersStub.ts";

interface Deferred {
  promise: Promise<unknown>;
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}
interface Feedback {
  key: string;
  ok: boolean;
  reason?: string;
}
interface View {
  feedback: Feedback | null;
  copy: (text: string, key: string) => Promise<{ ok: boolean; reason?: string }>;
  reset: () => void;
}

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

function deferred(): Deferred {
  let resolve!: (value?: unknown) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

type Mode = "manual" | "resolve" | "reject-error" | "reject-string";
let mode: Mode = "manual";
let rejection: unknown = undefined;
const writes: string[] = [];
const pending: Deferred[] = [];
const clipboard = {
  writeText(text: string): Promise<unknown> {
    writes.push(text);
    const next = deferred();
    if (mode === "resolve") next.resolve(undefined);
    else if (mode === "reject-error") next.reject(new Error(String(rejection)));
    else if (mode === "reject-string") next.reject(rejection);
    else pending.push(next);
    return next.promise;
  },
};
Object.defineProperty(globalThis, "navigator", { value: { clipboard }, configurable: true, writable: true });

let resetMs = 2000;
const render = (): View => { beginRender(); return useClipboardCopy(resetMs) as unknown as View; };

async function run(): Promise<void> {
  mode = "resolve";
  writes.length = 0;
  expect("写入成功返回成功", (await copyText("正文")).ok === true && writes[0] === "正文");

  mode = "reject-error"; rejection = "denied";
  const failed = await copyText("正文");
  expect("写入失败返回原因", failed.ok === false && failed.reason === "denied");

  mode = "reject-string"; rejection = "字符串原因";
  const stringFailed = await copyText("正文");
  expect("字符串原因可用", stringFailed.ok === false && stringFailed.reason === "字符串原因");

  mode = "reject-error"; rejection = "";
  const emptyFailed = await copyText("正文");
  expect("空原因回退固定文案", emptyFailed.ok === false && emptyFailed.reason === "系统拒绝了剪贴板写入");

  mode = "reject-error"; rejection = "x".repeat(200);
  const longFailed = await copyText("正文");
  expect("长原因截断到 80", longFailed.ok === false && longFailed.reason.length === 80);

  const saved = (globalThis as { navigator?: unknown }).navigator;
  delete (globalThis as { navigator?: unknown }).navigator;
  expect("无剪贴板返回不支持", (await copyText("正文")).reason === "当前环境不支持剪贴板写入");
  Object.defineProperty(globalThis, "navigator", { value: { clipboard: {} }, configurable: true, writable: true });
  expect("无写入方法返回不支持", (await copyText("正文")).reason === "当前环境不支持剪贴板写入");
  Object.defineProperty(globalThis, "navigator", { value: saved, configurable: true, writable: true });

  reset(); resetMs = 2000;
  let view = render();
  expect("初始无反馈", view.feedback === null);

  timers.length = 0; mode = "resolve";
  await view.copy("正文A", "k1");
  let current = render();
  expect("成功反馈带标识", current.feedback?.key === "k1" && current.feedback?.ok === true);
  expect("成功启动计时器", timers.at(-1)?.delay === 2000 && timers.at(-1)?.cleared === false);
  timers.at(-1)!.callback();
  expect("计时器到期清空反馈", render().feedback === null);

  timers.length = 0; mode = "resolve";
  await render().copy("A", "k1");
  const firstTimer = timers.at(-1)!;
  await render().copy("B", "k2");
  expect("新复制清除旧计时器", firstTimer.cleared === true);
  expect("新反馈替换旧反馈", render().feedback?.key === "k2");

  timers.length = 0; mode = "reject-error"; rejection = "denied";
  await render().copy("正文", "k3");
  current = render();
  expect("失败反馈带原因", current.feedback?.ok === false && current.feedback?.reason === "denied");
  expect("失败也启动计时器", timers.at(-1)?.delay === 2000);

  timers.length = 0; pending.length = 0; mode = "manual";
  const slow = render().copy("慢", "slow");
  mode = "resolve";
  await render().copy("快", "fast");
  expect("后发复制先反馈", render().feedback?.key === "fast");
  pending.at(-1)!.resolve(undefined);
  await slow;
  expect("迟到回执不覆盖新反馈", render().feedback?.key === "fast");

  pending.length = 0; mode = "manual";
  const delayed = render().copy("延迟", "late");
  await render().reset();
  expect("重置清空反馈", render().feedback === null);
  pending.at(-1)!.resolve(undefined);
  await delayed;
  expect("重置后迟到回执不恢复", render().feedback === null);

  reset(); timers.length = 0; mode = "resolve";
  await render().copy("清理", "k");
  const unloadTimer = timers.at(-1)!;
  effectCleanup?.();
  expect("卸载清除计时器", unloadTimer.cleared === true);

  reset(); pending.length = 0; mode = "manual";
  const lateUnmount = render().copy("卸载", "late");
  effectCleanup?.();
  pending.at(-1)!.resolve(undefined);
  await lateUnmount;
  expect("卸载后迟到回执不写反馈", render().feedback === null);

  reset(); resetMs = 500; timers.length = 0; mode = "resolve";
  view = render();
  await view.copy("短", "k");
  expect("自定义周期生效", timers.at(-1)?.delay === 500);

  reset(); pending.length = 0; mode = "manual";
  const lateResult = render().copy("迟到结果", "k");
  await render().reset();
  pending.at(-1)!.resolve(undefined);
  expect("迟到复制仍返回真实结果", (await lateResult).ok === true);

  console.log(`PASS ${passed}`);
}

await run();
"""

FRAGMENTS = (
    'import { useCallback, useEffect, useRef, useState } from "react";',
    'import { safeSlice } from "@boss-harness/shared";',
    "export type CopyResult = { ok: true } | { ok: false; reason: string };",
    "const MAX_REASON_LENGTH = 80;",
    "export async function copyText(text: string): Promise<CopyResult> {",
    "const clipboard = typeof navigator === \"undefined\" ? undefined : navigator.clipboard;",
    "if (!clipboard || typeof clipboard.writeText !== \"function\") return { ok: false, reason: \"当前环境不支持剪贴板写入\" };",
    "await clipboard.writeText(text);",
    "return { ok: true };",
    "const message = error instanceof Error ? error.message : typeof error === \"string\" ? error : \"\";",
    "return { ok: false, reason: safeSlice(message.trim(), MAX_REASON_LENGTH) || \"系统拒绝了剪贴板写入\" };",
    "export interface CopyFeedback {",
    "key: string;",
    "ok: boolean;",
    "reason?: string;",
    "export function useClipboardCopy(resetMs = 2000) {",
    "const [feedback, setFeedback] = useState<CopyFeedback | null>(null);",
    "const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);",
    "const version = useRef(0);",
    "const clear = useCallback(() => {",
    "if (timer.current !== undefined) clearTimeout(timer.current);",
    "timer.current = undefined;",
    "useEffect(() => () => { version.current += 1; clear(); }, [clear]);",
    "const mine = ++version.current;",
    "clear();",
    "setFeedback(null);",
    "const result = await copyText(text);",
    "if (version.current !== mine) return result;",
    "setFeedback(result.ok ? { key, ok: true } : { key, ok: false, reason: result.reason });",
    "timer.current = setTimeout(() => {",
    "if (version.current !== mine) return;",
    "timer.current = undefined;",
    "}, resetMs);",
    "return result;",
    "const reset = useCallback(() => { version.current += 1; clear(); setFeedback(null); }, [clear]);",
    "return { feedback, copy, reset };",
)

ORDERED = (
    # 写入：环境守卫、系统写入、成功回执。
    (
        "export async function copyText(text: string): Promise<CopyResult> {",
        "const clipboard = typeof navigator === \"undefined\" ? undefined : navigator.clipboard;",
        "if (!clipboard || typeof clipboard.writeText !== \"function\")",
        "await clipboard.writeText(text);",
        "return { ok: true };",
    ),
    # 失败：只取错误消息并截断，为空时回退固定文案。
    (
        "try {",
        "const message = error instanceof Error ? error.message : typeof error === \"string\" ? error : \"\";",
        "return { ok: false, reason: safeSlice(message.trim(), MAX_REASON_LENGTH) || \"系统拒绝了剪贴板写入\" };",
    ),
    # 清理：先取消计时器再清空引用。
    (
        "const clear = useCallback(() => {",
        "if (timer.current !== undefined) clearTimeout(timer.current);",
        "timer.current = undefined;",
    ),
    # 复制：领取新版本、清空旧提示、写入后按版本决定是否反馈。
    (
        "const mine = ++version.current;",
        "clear();",
        "setFeedback(null);",
        "const result = await copyText(text);",
        "if (version.current !== mine) return result;",
        "setFeedback(result.ok ? { key, ok: true } : { key, ok: false, reason: result.reason });",
        "timer.current = setTimeout(() => {",
        "if (version.current !== mine) return;",
        "timer.current = undefined;",
        "}, resetMs);",
        "return result;",
    ),
    # 重置：推进版本并清空提示。
    (
        "const reset = useCallback(() => { version.current += 1; clear(); setFeedback(null); }, [clear]);",
        "return { feedback, copy, reset };",
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
    rewritten = rewritten.replace('from "@boss-harness/shared"', 'from "./sharedStub.ts"')
    if 'from "./reactStub.ts"' not in rewritten or 'from "./sharedStub.ts"' not in rewritten:
        raise ValueError(f"{CLIPBOARD} 的导入结构已变化，需要更新桩")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, CLIPBOARD)
    for group in ORDERED:
        checked += _ordered(group, source, CLIPBOARD)
    # 反向断言：失败原因不得拼接正文；迟到回执不得恢复提示；
    # 版本令牌必须在卸载与重置时推进。
    if "safeSlice(text" in source:
        raise ValueError(f"{CLIPBOARD} 的失败原因不得包含被复制正文")
    if "version.current === mine" in source:
        raise ValueError(f"{CLIPBOARD} 的迟到回执必须丢弃")
    if source.count("version.current += 1") != 2:
        raise ValueError(f"{CLIPBOARD} 的版本令牌必须在卸载与重置时推进")
    if source.count("setFeedback(null)") != 3:
        raise ValueError(f"{CLIPBOARD} 的清空必须覆盖开始、计时器与重置")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(CLIPBOARD)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "clipboardCopy.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "reactStub.ts").write_text(REACT_STUB, encoding="utf-8")
        (folder / "sharedStub.ts").write_text(SHARED_STUB, encoding="utf-8")
        (folder / "timersStub.ts").write_text(TIMERS_STUB, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("剪贴板行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"剪贴板行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_clipboard_copy.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_clipboard_copy.py")
    if "共 64 项结构、23 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_clipboard_copy.py 检查 64 项结构、23 项行为")
    return 2


def check_clipboard_copy() -> tuple[int, int]:
    source = _read(CLIPBOARD)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_clipboard_copy()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"剪贴板写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"剪贴板写入一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
