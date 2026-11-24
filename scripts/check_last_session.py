#!/usr/bin/env python3
"""核对最近打开会话的存储解析与回退。

启动时据本地存储的会话 id 回到上次会话；损坏记录、超长 id 与存储不可用
都必须退回首页，不能把异常拖到启动阶段。这里固定严格解析、命名空间键、
异常回退与清空语义，避免带首尾空白的记录或空 id 被当成可恢复会话。行为
侧把真实 `lastSession.ts` 与 `uiStorage.ts` 复制到临时目录、改写导入，由
Node 注入可控 `localStorage` 驱动解析边界、读写与异常回退。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
LAST = "apps/desktop/src/renderer/src/data/lastSession.ts"
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"

EXPECTED = 20

NODE_SCRIPT = """\
import {
  LAST_SESSION_KEY,
  parseLastSessionId,
  readLastSessionId,
  rememberLastSessionId,
} from "./lastSession.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const store = new Map<string, string>();
let mode: "ok" | "throw" = "ok";
globalThis.localStorage = {
  getItem(key: string): string | null {
    if (mode === "throw") throw new Error("blocked");
    return store.has(key) ? store.get(key)! : null;
  },
  setItem(key: string, value: string): void {
    if (mode === "throw") throw new Error("blocked");
    store.set(key, String(value));
  },
  removeItem(key: string): void {
    if (mode === "throw") throw new Error("blocked");
    store.delete(key);
  },
} as any;

expect("命名空间键", LAST_SESSION_KEY === "boss-harness.ui.lastSession");
expect("空存储读取", readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "thread-1");
expect("读取正常 id", readLastSessionId() === "thread-1");
store.set(LAST_SESSION_KEY, " thread-1");
expect("前导空白视为损坏", readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "thread-1 ");
expect("尾随空白视为损坏", readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "");
expect("空字符串视为损坏", readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "   ");
expect("纯空白视为损坏", readLastSessionId() === null);
const long200 = "a".repeat(200);
const long201 = "a".repeat(201);
store.set(LAST_SESSION_KEY, long200);
expect("200 码点可恢复", readLastSessionId() === long200);
store.set(LAST_SESSION_KEY, long201);
expect("超长视为损坏", readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "含空白 thread");
expect("内部空白不算损坏", readLastSessionId() === "含空白 thread");
expect("解析空值", parseLastSessionId(null) === null);
expect(
  "解析非字符串",
  parseLastSessionId(undefined as any) === null && parseLastSessionId(7 as any) === null,
);
expect("解析不修剪", parseLastSessionId(" id ") === null);
rememberLastSessionId("thread-9");
expect("记录写入键", store.get(LAST_SESSION_KEY) === "thread-9" && readLastSessionId() === "thread-9");
rememberLastSessionId(null);
expect("记录 null 删除键", !store.has(LAST_SESSION_KEY) && readLastSessionId() === null);
store.set(LAST_SESSION_KEY, "keep");
rememberLastSessionId("");
expect("记录空字符串删除键", !store.has(LAST_SESSION_KEY));
store.set("other", "value");
rememberLastSessionId("thread-2");
expect("记录不触碰其他键", store.get("other") === "value");
mode = "throw";
expect("读取异常回退 null", readLastSessionId() === null);
let writeRaised = false;
try {
  rememberLastSessionId("thread-3");
} catch {
  writeRaised = true;
}
expect("写入异常不抛出", !writeRaised);
let clearRaised = false;
try {
  rememberLastSessionId(null);
} catch {
  clearRaised = true;
}
expect("删除异常不抛出", !clearRaised);
mode = "ok";
store.clear();

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { UI_STORAGE_PREFIX } from "./uiStorage";',
    'export const LAST_SESSION_KEY = UI_STORAGE_PREFIX + "lastSession";',
    "const MAX_SESSION_ID_LENGTH = 200;",
    "export function parseLastSessionId(raw: string | null): string | null {",
    'if (typeof raw !== "string") return null;',
    "const id = raw.trim();",
    "if (!id || id.length > MAX_SESSION_ID_LENGTH || id !== raw) return null;",
    "return id;",
    "export function readLastSessionId(): string | null {",
    "return parseLastSessionId(localStorage.getItem(LAST_SESSION_KEY));",
    "export function rememberLastSessionId(id: string | null): void {",
    "if (id) localStorage.setItem(LAST_SESSION_KEY, id);",
    "else localStorage.removeItem(LAST_SESSION_KEY);",
)

STORAGE_FRAGMENTS = (
    'export const UI_STORAGE_PREFIX = "boss-harness.ui.";',
)

ORDERED = (
    # 解析：类型 → 去空白 → 严格判定 → 返回。
    (
        "export function parseLastSessionId(raw: string | null): string | null {",
        'if (typeof raw !== "string") return null;',
        "const id = raw.trim();",
        "if (!id || id.length > MAX_SESSION_ID_LENGTH || id !== raw) return null;",
        "return id;",
    ),
    # 记录：有 id 写入，没有则删除键。
    (
        "export function rememberLastSessionId(id: string | null): void {",
        "if (id) localStorage.setItem(LAST_SESSION_KEY, id);",
        "else localStorage.removeItem(LAST_SESSION_KEY);",
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
    rewritten = source.replace('from "./uiStorage";', 'from "./uiStorage.ts";')
    if 'from "./uiStorage";' in rewritten:
        raise ValueError(f"{LAST} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str, storage: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, LAST)
    checked += _expect(STORAGE_FRAGMENTS, storage, STORAGE)
    for group in ORDERED:
        checked += _ordered(group, source, LAST)
    # 反向断言：损坏记录不得恢复；读写都要有异常回退；清空不得写入空字符串。
    if "id !== raw" not in source:
        raise ValueError(f"{LAST} 带首尾空白的记录必须视为损坏")
    if source.count("catch {") != 2:
        raise ValueError(f"{LAST} 读写本地存储都必须捕获异常并退回首页")
    if 'setItem(LAST_SESSION_KEY, "")' in source:
        raise ValueError(f"{LAST} 清空必须删除键，不能写入空字符串")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(LAST)
    storage = _read(STORAGE)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "lastSession.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "uiStorage.ts").write_text(storage, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("最近会话行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"最近会话行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_last_session.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_last_session.py")
    if "共 25 项结构、20 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_last_session.py 检查 25 项结构、20 项行为")
    return 2


def check_last_session() -> tuple[int, int]:
    source = _read(LAST)
    storage = _read(STORAGE)
    structure = _check_structure(source, storage)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_last_session()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"最近会话核对失败，{error}", file=sys.stderr)
        return 2
    print(f"最近会话一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
