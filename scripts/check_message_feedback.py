#!/usr/bin/env python3
"""核对消息反馈的键编码、校验、淘汰与本地存储回退。

`messageFeedback.ts` 只把「有帮助 / 需要改进」保存在本机：键由会话与消息 id
的 JSON 数组编码（避免分隔符歧义），单键不超过 600 字符；解析只留合法键与
`up` / `down`；最多 2000 条，按插入顺序淘汰最早条目；删除会话时清理该会话
条目；存储不可用时读空、写失败返回 false。这里用 Node 在临时目录加载真实
模块并注入内存 `localStorage`，逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK = "apps/desktop/src/renderer/src/data/messageFeedback.ts"
UI_STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FEEDBACK_FRAGMENTS = (
    'export const MESSAGE_FEEDBACK_STORAGE_KEY = UI_STORAGE_PREFIX + "messageFeedback";',
    "export const MAX_FEEDBACK_KEY_LENGTH = 600;",
    "export const MAX_MESSAGE_FEEDBACK_ENTRIES = 2_000;",
    "export function feedbackEntryKey(threadId: string, messageId: string): string | null {",
    "const key = JSON.stringify([thread, message]);",
    "return key.length <= MAX_FEEDBACK_KEY_LENGTH ? key : null;",
    "export function parseFeedbackEntryKey(key: string): [string, string] | null {",
    "if (!Array.isArray(value) || value.length !== 2) return null;",
    "if (!thread || !message || thread.trim() !== thread || message.trim() !== message) return null;",
    "export function parseMessageFeedback(value: unknown): MessageFeedbackStore {",
    'if (choice !== "up" && choice !== "down") continue;',
    "return Object.fromEntries(entries.slice(-MAX_MESSAGE_FEEDBACK_ENTRIES));",
    "export function withMessageFeedback(",
    "delete next[key];",
    "if (choice !== undefined) next[key] = choice;",
    "const excess = keys.length - MAX_MESSAGE_FEEDBACK_ENTRIES;",
    "if (excess > 0) for (const stale of keys.slice(0, excess)) delete next[stale];",
    "export function feedbackForThread(store: MessageFeedbackStore, threadId: string): MessageFeedbackStore {",
    "if (parsed?.[0] === threadId) result[parsed[1]] = choice;",
    "export function clearThreadFeedback(store: MessageFeedbackStore, threadId: string): MessageFeedbackStore {",
    "if (keys.length === 0) return store;",
    "export function readStoredMessageFeedback(): MessageFeedbackStore {",
    "export function saveStoredMessageFeedback(store: MessageFeedbackStore): boolean {",
    "if (Object.keys(store).length === 0) localStorage.removeItem(MESSAGE_FEEDBACK_STORAGE_KEY);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const memory = new Map();
let throwGet = false;
let throwSet = false;
globalThis.localStorage = {
  get length() { return memory.size; },
  key: (index) => [...memory.keys()][index] ?? null,
  getItem: (key) => { if (throwGet) throw new Error("denied"); return memory.has(key) ? memory.get(key) : null; },
  setItem: (key, value) => { if (throwSet) throw new Error("quota"); memory.set(key, String(value)); },
  removeItem: (key) => { memory.delete(key); },
  clear: () => memory.clear(),
};
const {
  feedbackEntryKey, parseFeedbackEntryKey, parseMessageFeedback, withMessageFeedback,
  feedbackForThread, clearThreadFeedback, readStoredMessageFeedback, saveStoredMessageFeedback,
  MESSAGE_FEEDBACK_STORAGE_KEY,
} = await import(pathToFileURL(process.argv[1]).href);
const store = (entries) => Object.fromEntries(entries);
const key = (thread, message) => JSON.stringify([thread, message]);
const results = {
  keys: [
    feedbackEntryKey(" t1 ", " m1 "),
    feedbackEntryKey("", "m1"),
    feedbackEntryKey("t1", "   "),
    feedbackEntryKey("t".repeat(300), "m".repeat(300)),
    parseFeedbackEntryKey(key("t1", "m1")),
    [
      parseFeedbackEntryKey(JSON.stringify(["t1"])),
      parseFeedbackEntryKey(JSON.stringify(["t1", "m1", "x"])),
      parseFeedbackEntryKey(JSON.stringify([" t1", "m1"])),
      parseFeedbackEntryKey("not json"),
      parseFeedbackEntryKey(123),
    ],
  ],
  parse: [
    parseMessageFeedback(null),
    parseMessageFeedback([]),
    parseMessageFeedback({ [key("t1", "m1")]: "up", [key("t1", "m2")]: "down", [key("t1", "m3")]: "meh", "bad": "up" }),
    (() => {
      const entries = Array.from({ length: 2001 }, (_, index) => [key(`t${index}`, "m"), "up"]);
      const keys = Object.keys(parseMessageFeedback(store(entries)));
      return [keys.length, keys[0] === key("t1", "m"), keys[keys.length - 1] === key("t2000", "m")];
    })(),
    (() => {
      const keys = Object.keys(parseMessageFeedback(store([[key("b", "m"), "up"], [key("a", "m"), "down"]])));
      return [keys.length, keys[0] === key("b", "m"), keys[1] === key("a", "m")];
    })(),
  ],
  with: [
    withMessageFeedback({}, key("t1", "m1"), "up"),
    withMessageFeedback({ [key("t1", "m1")]: "up" }, key("t1", "m1"), undefined),
    (() => {
      const original = { [key("a", "m")]: "up", [key("b", "m")]: "down" };
      const next = withMessageFeedback(original, key("a", "m"), "down");
      return [Object.keys(next).length, Object.keys(next)[0] === key("b", "m"), Object.keys(next)[1] === key("a", "m"),
        Object.keys(original).length, next[key("a", "m")]];
    })(),
    (() => {
      const entries = Array.from({ length: 2000 }, (_, index) => [key(`t${index}`, "m"), "up"]);
      const next = withMessageFeedback(store(entries), key("new", "m"), "up");
      const keys = Object.keys(next);
      return [keys.length, Object.prototype.hasOwnProperty.call(next, key("t0", "m")), keys[keys.length - 1] === key("new", "m")];
    })(),
  ],
  thread: [
    feedbackForThread({
      [key("t1", "m1")]: "up",
      [key("t1", "m2")]: "down",
      [key("t2", "m1")]: "up",
      "bad": "up",
    }, "t1"),
    (() => {
      const base = { [key("t2", "m1")]: "up" };
      return clearThreadFeedback(base, "t1") === base;
    })(),
    (() => {
      const next = clearThreadFeedback({
        [key("t1", "m1")]: "up",
        [key("t1", "m2")]: "down",
        [key("t2", "m1")]: "up",
        "bad": "up",
      }, "t1");
      return [Object.keys(next).length, Object.prototype.hasOwnProperty.call(next, "bad"),
        Object.keys(next)[0] === key("t2", "m1")];
    })(),
  ],
  storage: [
    (() => {
      memory.clear();
      return [saveStoredMessageFeedback({}), memory.has(MESSAGE_FEEDBACK_STORAGE_KEY)];
    })(),
    (() => {
      memory.clear();
      return [saveStoredMessageFeedback({ [key("t1", "m1")]: "up" }), readStoredMessageFeedback()];
    })(),
    (() => {
      throwGet = true;
      const value = readStoredMessageFeedback();
      throwGet = false;
      return value;
    })(),
    (() => {
      throwSet = true;
      const ok = saveStoredMessageFeedback({ [key("t1", "m1")]: "up" });
      throwSet = false;
      return ok;
    })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

K1 = '["t1","m1"]'
K2 = '["t1","m2"]'
KB = '["b","m"]'
KA = '["a","m"]'
KT2 = '["t2","m1"]'

EXPECTED_KEYS = (
    K1,
    None,
    None,
    None,
    ["t1", "m1"],
    [None, None, None, None, None],
)
EXPECTED_PARSE = (
    {},
    {},
    {K1: "up", K2: "down"},
    [2000, True, True],
    [2, True, True],
)
EXPECTED_WITH = (
    {K1: "up"},
    {},
    [2, True, True, 2, "down"],
    [2000, False, True],
)
EXPECTED_THREAD = (
    {"m1": "up", "m2": "down"},
    True,
    [2, True, True],
)
EXPECTED_STORAGE = (
    [True, False],
    [True, {K1: "up"}],
    {},
    False,
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # messageFeedback 以无扩展名相对路径导入 uiStorage；Node 的类型剥离只解析
    # 显式扩展名，所以复制到临时目录并改写导入，不改动仓库源文件。
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base / "uiStorage.ts").write_text(_read(UI_STORAGE), encoding="utf-8")
        target = base / "messageFeedback.ts"
        target.write_text(
            _read(FEEDBACK).replace('from "./uiStorage"', 'from "./uiStorage.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 消息反馈试算失败，请核对 Node.js 24+ 与 messageFeedback.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的消息反馈结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回消息反馈矩阵")
    for key in ("keys", "parse", "with", "thread", "storage"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"消息反馈{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"消息反馈{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["keys"], EXPECTED_KEYS, "键")
    checked += _compare(payload["parse"], EXPECTED_PARSE, "解析")
    checked += _compare(payload["with"], EXPECTED_WITH, "写入")
    checked += _compare(payload["thread"], EXPECTED_THREAD, "会话")
    checked += _compare(payload["storage"], EXPECTED_STORAGE, "存储")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_message_feedback.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_message_feedback.py")
    if "共 24 项结构、22 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_message_feedback.py 检查 24 项结构、22 项行为")
    return 2


def check_message_feedback() -> tuple[int, int]:
    structure = _expect(FEEDBACK_FRAGMENTS, _read(FEEDBACK), FEEDBACK)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_message_feedback()
    except (OSError, ValueError) as error:
        print(f"消息反馈规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"消息反馈规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
