#!/usr/bin/env python3
"""核对未发送草稿的本地持久化规则。

`composerDraftStorage.ts` 只保存正文、技能 id 与历史调取前的原稿：单条正文按码点
限制长度，技能 id 去重过滤并截断；解析时校验版本、`projectId` 与 `recallDraft`，
用无原型对象承接外部会话键；最多保留 20 条并稳定排序；未变条目沿用原时间戳；
全空时删除存储键；存储不可用或超限时静默回退。这里用 Node 在临时目录加载真实
模块（改写共享包与无扩展名导入），逐项核对解析、加载、保存与恢复。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STORAGE = "apps/desktop/src/renderer/src/data/composerDraftStorage.ts"
COMPOSER_DRAFT = "apps/desktop/src/renderer/src/data/composerDraft.ts"
UI_STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

STORAGE_FRAGMENTS = (
    'import { MAX_MESSAGE_TEXT_LENGTH, createComposerDraft, type ComposerDraft } from "./composerDraft";',
    'export const COMPOSER_DRAFT_STORAGE_KEY = UI_STORAGE_PREFIX + "composerDrafts";',
    "export const MAX_DRAFT_TEXT_LENGTH = MAX_MESSAGE_TEXT_LENGTH;",
    "export const MAX_SESSION_DRAFTS = 20;",
    "const MAX_SKILL_IDS = 50;",
    "const MAX_PROJECT_ID_LENGTH = 200;",
    "const STORE_VERSION = 1;",
    'if (typeof record.text !== "string" || codePointLength(record.text) > MAX_DRAFT_TEXT_LENGTH) return null;',
    'const recallDraft = typeof record.recallDraft === "string" && codePointLength(record.recallDraft) <= MAX_DRAFT_TEXT_LENGTH',
    'if (!record.text.trim() && skillIds.length === 0) return null;',
    'typeof record.updatedAt === "number" && Number.isFinite(record.updatedAt) && record.updatedAt >= 0',
    "record.projectId.trim() === record.projectId",
    "record.projectId.trim().length > 0 && record.projectId.length <= MAX_PROJECT_ID_LENGTH",
    "const sessions = Object.entries(store.sessions)",
    ".sort(([idA, a], [idB, b]) => b.updatedAt - a.updatedAt || idA.localeCompare(idB))",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return empty;',
    "if (record.version !== STORE_VERSION) return empty;",
    "const sessions: Record<string, PersistedComposerDraft> = Object.create(null);",
    "if (!id.trim()) continue;",
    "return prune({ home: draftEntry(record.home) ?? undefined, sessions });",
    "export function loadComposerDraftStore(storage: DraftStorage | null = defaultStorage()): PersistedComposerDraftStore {",
    "return raw === null ? empty : parseComposerDraftStore(JSON.parse(raw));",
    "} catch { return empty; }",
    "if (codePointLength(draft.text) > MAX_DRAFT_TEXT_LENGTH) return null;",
    "const recallDraft = draft.recallDraft !== undefined && codePointLength(draft.recallDraft) <= MAX_DRAFT_TEXT_LENGTH ? draft.recallDraft : undefined;",
    "const unchanged = sameDraft(current, previousEntry)",
    '&& (id !== null || (previousEntry?.projectId ?? "") === (homeProjectId || ""));',
    "const entry: PersistedComposerDraft = { ...current, updatedAt: unchanged ? previousEntry!.updatedAt : now };",
    "if (id === null && homeProjectId) entry.projectId = homeProjectId;",
    "storage.removeItem(COMPOSER_DRAFT_STORAGE_KEY);",
    "storage.setItem(COMPOSER_DRAFT_STORAGE_KEY, JSON.stringify({ version: STORE_VERSION, ...pruned }));",
    "export function restoreComposerDraft(entry?: PersistedComposerDraft): ComposerDraft {",
    "return entry ? { ...draft, text: entry.recallDraft ?? entry.text, skillIds: entry.skillIds } : draft;",
    "export function restoreSessionDrafts(store: PersistedComposerDraftStore): Record<string, ComposerDraft> {",
    "return Object.fromEntries(Object.entries(store.sessions).map(([id, entry]) => [id, restoreComposerDraft(entry)]));",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  parseComposerDraftStore, loadComposerDraftStore, saveComposerDrafts,
  restoreComposerDraft, restoreSessionDrafts, COMPOSER_DRAFT_STORAGE_KEY,
} = await import(pathToFileURL(process.argv[1]).href);
const draft = (over = {}) => ({ id: "d1", text: "", textVersion: 0, attachments: [], skillIds: [], pendingReads: 0, submitting: false, ...over });
const box = (initial) => {
  const map = new Map();
  if (initial !== undefined) map.set(COMPOSER_DRAFT_STORAGE_KEY, JSON.stringify(initial));
  const removed = [];
  const set = [];
  return {
    map, removed, set,
    storage: {
      getItem: (key) => (map.has(key) ? map.get(key) : null),
      setItem: (key, value) => { set.push(key); map.set(key, String(value)); },
      removeItem: (key) => { removed.push(key); map.delete(key); },
    },
  };
};
const readStore = (b) => JSON.parse(b.map.get(COMPOSER_DRAFT_STORAGE_KEY));
const memory = (get) => ({ getItem: get, setItem: () => {}, removeItem: () => {} });
const results = {
  parse: [
    parseComposerDraftStore(null),
    parseComposerDraftStore({ version: 2, sessions: {} }),
    parseComposerDraftStore({
      version: 1,
      home: { text: "hi", skillIds: ["a", "a", " ", "b"], updatedAt: 5, projectId: "p", recallDraft: "orig" },
      sessions: {},
    }),
    (() => {
      const parsed = parseComposerDraftStore({ version: 1, sessions: {
        a: { text: "  ", skillIds: [], updatedAt: 1 },
        b: { text: "", skillIds: ["x"], updatedAt: 2 },
      } });
      return [Object.keys(parsed.sessions), parsed.sessions.b.skillIds];
    })(),
    (() => {
      const parsed = parseComposerDraftStore({
        version: 1,
        home: { text: "x".repeat(100001), skillIds: [], updatedAt: 1 },
        sessions: { emoji: { text: "😀".repeat(100000), skillIds: [], updatedAt: 2 } },
      });
      return [parsed.home === undefined, Object.keys(parsed.sessions), parsed.sessions.emoji.text.length];
    })(),
    (() => {
      const parsed = parseComposerDraftStore({ version: 1, sessions: {
        a: { text: "t", skillIds: [], updatedAt: 1, recallDraft: 42 },
        b: { text: "t", skillIds: [], updatedAt: 1, recallDraft: "x".repeat(100001) },
        c: { text: "t", skillIds: [], updatedAt: 1, recallDraft: "ok" },
      } });
      return [parsed.sessions.a.recallDraft === undefined, parsed.sessions.b.recallDraft === undefined, parsed.sessions.c.recallDraft];
    })(),
    (() => {
      const bad = [" p", "p ", "", "p".repeat(201)];
      const parsed = parseComposerDraftStore({ version: 1, sessions: Object.fromEntries(
        bad.map((projectId, index) => [`s${index}`, { text: "t", skillIds: [], updatedAt: 1, projectId }]),
      ) });
      return bad.map((_, index) => parsed.sessions[`s${index}`].projectId === undefined);
    })(),
    (() => {
      const parsed = parseComposerDraftStore({ version: 1, sessions: {
        a: { text: "t", skillIds: [], updatedAt: -1 },
        b: { text: "t", skillIds: [], updatedAt: "5" },
        c: { text: "t", skillIds: [], updatedAt: 7 },
      } });
      return [parsed.sessions.a.updatedAt, parsed.sessions.b.updatedAt, parsed.sessions.c.updatedAt];
    })(),
    (() => {
      const parsed = parseComposerDraftStore({ version: 1, sessions: {
        " ": { text: "t", skillIds: [], updatedAt: 1 },
        ok: "nope",
        good: { text: "t", skillIds: [], updatedAt: 1 },
      } });
      return Object.keys(parsed.sessions);
    })(),
    (() => {
      const sessions = {};
      for (let index = 0; index < 22; index += 1) sessions[`s${String(index).padStart(2, "0")}`] = { text: "t", skillIds: [], updatedAt: index };
      const keys = Object.keys(parseComposerDraftStore({ version: 1, sessions }).sessions);
      return [keys.length, keys[0], keys[keys.length - 1]];
    })(),
    (() => {
      const parsed = parseComposerDraftStore({ version: 1, sessions: {
        b: { text: "t", skillIds: [], updatedAt: 9 },
        a: { text: "t", skillIds: [], updatedAt: 9 },
      } });
      return Object.keys(parsed.sessions);
    })(),
    (() => {
      const parsed = parseComposerDraftStore(JSON.parse('{"version":1,"sessions":{"__proto__":{"text":"x","skillIds":[],"updatedAt":1}}}'));
      return [Object.keys(parsed.sessions), parsed.sessions["__proto__"].text, ({}).text === undefined,
        Object.getPrototypeOf(parsed.sessions) === Object.prototype];
    })(),
  ],
  load: [
    loadComposerDraftStore(null),
    loadComposerDraftStore(memory(() => { throw new Error("denied"); })),
    loadComposerDraftStore(memory(() => "not json")),
    loadComposerDraftStore(memory(() => null)),
    (() => {
      const loaded = loadComposerDraftStore(memory(() => JSON.stringify({ version: 1, home: { text: "hi", skillIds: [], updatedAt: 3 } })));
      return [loaded.home.text, loaded.home.updatedAt];
    })(),
  ],
  save: [
    (() => { saveComposerDrafts(draft({ text: "t" }), {}, null, 10); return true; })(),
    (() => {
      const b = box();
      saveComposerDrafts(draft({
        text: "hi",
        skillIds: ["a", "a", " "],
        attachments: [{ id: "f", name: "f.txt", text: "x", size: 1 }],
        submitting: true,
      }), { s1: draft({ text: "later" }) }, b.storage, 50, "proj");
      const stored = readStore(b);
      return [stored.home.text, stored.home.projectId, stored.home.skillIds, Object.keys(stored.home),
        Object.keys(stored.sessions), stored.sessions.s1.text, stored.version];
    })(),
    (() => {
      const b = box({ version: 1, home: { text: "hi", skillIds: [], updatedAt: 111 }, sessions: { s1: { text: "old", skillIds: [], updatedAt: 222 } } });
      saveComposerDrafts(draft({ text: "hi" }), { s1: draft({ text: "new" }) }, b.storage, 999);
      const stored = readStore(b);
      return [stored.home.updatedAt, stored.sessions.s1.updatedAt];
    })(),
    (() => {
      const b = box({ version: 1, home: { text: "hi", skillIds: [], updatedAt: 111, projectId: "p1" }, sessions: {} });
      saveComposerDrafts(draft({ text: "hi" }), {}, b.storage, 999, "p2");
      const stored = readStore(b);
      return [stored.home.updatedAt, stored.home.projectId];
    })(),
    (() => {
      const b = box({ version: 1, home: { text: "old", skillIds: [], updatedAt: 1 } });
      saveComposerDrafts(draft(), {}, b.storage, 10, "proj");
      return [b.removed, b.set.length, b.map.size];
    })(),
    (() => {
      const b = box();
      b.storage.setItem = () => { throw new Error("quota"); };
      saveComposerDrafts(draft({ text: "t" }), {}, b.storage, 1);
      return true;
    })(),
    (() => {
      const b = box();
      saveComposerDrafts(draft({ text: "x".repeat(100001) }), { s1: draft({ text: "ok" }) }, b.storage, 1);
      const stored = readStore(b);
      return [stored.home === undefined, Object.keys(stored.sessions)];
    })(),
    (() => {
      const b = box();
      saveComposerDrafts(draft({ text: "hi" }), { " ": draft({ text: "x" }), s1: draft({ text: "y" }) }, b.storage, 1);
      return Object.keys(readStore(b).sessions);
    })(),
    (() => {
      const sessions = {};
      for (let index = 0; index < 21; index += 1) sessions[`s${String(index).padStart(2, "0")}`] = draft({ text: "t" });
      const b = box();
      saveComposerDrafts(draft({ text: "home" }), sessions, b.storage, 5);
      const keys = Object.keys(readStore(b).sessions);
      return [keys.length, keys.includes("s20"), keys.includes("s00")];
    })(),
  ],
  restore: [
    (() => {
      const restored = restoreComposerDraft();
      return [restored.text, restored.skillIds, restored.attachments, typeof restored.id];
    })(),
    (() => {
      const restored = restoreComposerDraft({ text: "quoted", skillIds: ["s"], updatedAt: 1, recallDraft: "orig" });
      return [restored.text, restored.skillIds];
    })(),
    restoreComposerDraft({ text: "quoted", skillIds: [], updatedAt: 1 }).text,
    (() => {
      const first = restoreComposerDraft({ text: "t", skillIds: [], updatedAt: 1 });
      const second = restoreComposerDraft({ text: "t", skillIds: [], updatedAt: 1 });
      return [first.text, first.id !== second.id];
    })(),
    (() => {
      const restored = restoreSessionDrafts({ home: { text: "h", skillIds: [], updatedAt: 1 }, sessions: { a: { text: "x", skillIds: ["k"], updatedAt: 1, recallDraft: "orig" } } });
      return [Object.keys(restored), restored.a.text, restored.a.skillIds];
    })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_PARSE = (
    {"sessions": {}},
    {"sessions": {}},
    {
        "home": {"text": "hi", "skillIds": ["a", "b"], "updatedAt": 5, "projectId": "p", "recallDraft": "orig"},
        "sessions": {},
    },
    [["b"], ["x"]],
    [True, ["emoji"], 200000],
    [True, True, "ok"],
    [True, True, True, True],
    [0, 0, 7],
    ["good"],
    [20, "s21", "s02"],
    ["a", "b"],
    [["__proto__"], "x", True, True],
)
EXPECTED_LOAD = (
    {"sessions": {}},
    {"sessions": {}},
    {"sessions": {}},
    {"sessions": {}},
    ["hi", 3],
)
EXPECTED_SAVE = (
    True,
    ["hi", "proj", ["a"], ["text", "skillIds", "updatedAt", "projectId"], ["s1"], "later", 1],
    [111, 999],
    [999, "p2"],
    [["boss-harness.ui.composerDrafts"], 0, 0],
    True,
    [True, ["s1"]],
    ["s1"],
    [20, False, True],
)
EXPECTED_RESTORE = (
    ["", [], [], "string"],
    ["orig", ["s"]],
    "quoted",
    ["t", True],
    [["a"], "orig", ["k"]],
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # composerDraftStorage 无扩展名相对导入共享包；Node 的类型剥离只解析显式
    # 扩展名与真实 URL，所以复制到临时目录并改写导入，不改动仓库源文件。
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        shared = (ROOT / SHARED).as_uri()
        (base / "uiStorage.ts").write_text(_read(UI_STORAGE), encoding="utf-8")
        (base / "composerDraft.ts").write_text(
            _read(COMPOSER_DRAFT).replace('from "@boss-harness/shared"', f'from "{shared}"'),
            encoding="utf-8",
        )
        target = base / "composerDraftStorage.ts"
        target.write_text(
            _read(STORAGE)
            .replace('from "@boss-harness/shared"', f'from "{shared}"')
            .replace(
                "MAX_MESSAGE_TEXT_LENGTH, createComposerDraft, type ComposerDraft",
                "MAX_MESSAGE_TEXT_LENGTH, createComposerDraft",
            )
            .replace('from "./composerDraft"', 'from "./composerDraft.ts"')
            .replace('from "./uiStorage"', 'from "./uiStorage.ts"'),
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
                "Node 草稿持久化试算失败，请核对 Node.js 24+ 与 composerDraftStorage.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的草稿持久化结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回草稿持久化矩阵")
    for key in ("parse", "load", "save", "restore"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"草稿持久化{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"草稿持久化{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["parse"], EXPECTED_PARSE, "解析")
    checked += _compare(payload["load"], EXPECTED_LOAD, "加载")
    checked += _compare(payload["save"], EXPECTED_SAVE, "保存")
    checked += _compare(payload["restore"], EXPECTED_RESTORE, "恢复")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_composer_drafts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_composer_drafts.py")
    if "共 35 项结构、31 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_composer_drafts.py 检查 35 项结构、31 项行为")
    return 2


def check_composer_drafts() -> tuple[int, int]:
    structure = _expect(STORAGE_FRAGMENTS, _read(STORAGE), STORAGE)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_composer_drafts()
    except (OSError, ValueError) as error:
        print(f"草稿持久化规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"草稿持久化规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
