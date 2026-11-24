#!/usr/bin/env python3
"""核对搜索回执的形状校验与上限。

`thread/search` 的命中条目直接进入搜索弹窗：标识拼进选项 key，片段交给
关键词高亮，角色决定显示成你、助手还是工具。这里固定对象与数组判定、
标识与文本上限、角色白名单、回执级上限与「任一命中非法即整体拒绝」，
避免把内核异常传成渲染期抛错或把损坏响应当成完整结果。

会话区按当前分支视图展示，搜索却覆盖完整日志：命中可能位于被放弃的分支上。
这里同时固定内核的分支标记、弹窗标签与会话区的定位说明，避免再次出现
「点击搜索结果后什么都没发生」。行为侧把真实 `threadSearchResult.ts` 复制
到临时目录、删去类型导入，由 Node 直接加载驱动条目与回执的边界。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
RESULT = "apps/desktop/src/renderer/src/data/threadSearchResult.ts"
SESSION = "harness/src/boss_harness/session.py"
DIALOG = "apps/desktop/src/renderer/src/components/SearchDialog.tsx"
SHELL = "apps/desktop/src/renderer/src/shell/AppShell.tsx"
CONVERSATION = "apps/desktop/src/renderer/src/shell/ConversationArea.tsx"
PROTOCOL = "packages/protocol/src/index.ts"
CSS = "apps/desktop/src/renderer/src/styles/replica.css"

EXPECTED = 35

NODE_SCRIPT = """\
import {
  SEARCH_MATCH_LIMIT,
  threadSearchMatchOf,
  threadSearchResultOf,
} from "./threadSearchResult.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);
const entry = (overrides: Record<string, unknown> = {}): any => ({
  threadId: "t1",
  threadTitle: "标题",
  itemId: "i1",
  role: "user",
  snippet: "片段",
  ...overrides,
});
const resultOf = (overrides: Record<string, unknown> = {}): any => ({
  matches: [entry()],
  truncated: false,
  ...overrides,
});

expect(
  "合法条目形状",
  same(threadSearchMatchOf(entry()), {
    threadId: "t1",
    threadTitle: "标题",
    itemId: "i1",
    role: "user",
    snippet: "片段",
  }),
);
expect("条目无 onBranch 键", !("onBranch" in (threadSearchMatchOf(entry()) as any)));
expect("onBranch 真保留", threadSearchMatchOf(entry({ onBranch: true }))!.onBranch === true);
expect("onBranch 假保留", threadSearchMatchOf(entry({ onBranch: false }))!.onBranch === false);
expect("onBranch 非布尔拒绝", threadSearchMatchOf(entry({ onBranch: "true" })) === null);
expect(
  "非对象拒绝",
  threadSearchMatchOf(null) === null
    && threadSearchMatchOf(42) === null
    && threadSearchMatchOf([]) === null,
);
const arrayLike: any = [];
arrayLike.threadId = "t1";
arrayLike.threadTitle = "";
arrayLike.itemId = "i1";
arrayLike.role = "user";
arrayLike.snippet = "";
expect("带属性的数组仍拒绝", threadSearchMatchOf(arrayLike) === null);
expect("空 threadId 拒绝", threadSearchMatchOf(entry({ threadId: "" })) === null);
expect("threadId 非字符串拒绝", threadSearchMatchOf(entry({ threadId: 7 })) === null);
expect("threadId 200 通过", threadSearchMatchOf(entry({ threadId: "a".repeat(200) })) !== null);
expect("threadId 201 拒绝", threadSearchMatchOf(entry({ threadId: "a".repeat(201) })) === null);
expect("标题允许为空", threadSearchMatchOf(entry({ threadTitle: "" }))!.threadTitle === "");
expect(
  "标题 4096 通过",
  threadSearchMatchOf(entry({ threadTitle: "a".repeat(4096) })) !== null,
);
expect("标题 4097 拒绝", threadSearchMatchOf(entry({ threadTitle: "a".repeat(4097) })) === null);
expect("标题非字符串拒绝", threadSearchMatchOf(entry({ threadTitle: 7 })) === null);
expect("空 itemId 拒绝", threadSearchMatchOf(entry({ itemId: "" })) === null);
expect("未知角色拒绝", threadSearchMatchOf(entry({ role: "system" })) === null);
expect(
  "三种角色通过",
  ["user", "agent", "tool"].every(role => threadSearchMatchOf(entry({ role })) !== null),
);
expect("角色非字符串拒绝", threadSearchMatchOf(entry({ role: 7 })) === null);
expect("片段允许为空", threadSearchMatchOf(entry({ snippet: "" }))!.snippet === "");
expect(
  "片段 4096 通过",
  threadSearchMatchOf(entry({ snippet: "a".repeat(4096) })) !== null,
);
expect("片段 4097 拒绝", threadSearchMatchOf(entry({ snippet: "a".repeat(4097) })) === null);
expect(
  "多余字段丢弃",
  same(Object.keys(threadSearchMatchOf(entry({ extra: 1 }))!).sort(), [
    "itemId",
    "role",
    "snippet",
    "threadId",
    "threadTitle",
  ]),
);
const rawEntry = entry();
threadSearchMatchOf(rawEntry);
expect("条目不被修改", same(rawEntry, entry()));

expect("回执上限常量", SEARCH_MATCH_LIMIT === 200);
expect(
  "合法回执与显式 true",
  same(threadSearchResultOf(resultOf({ truncated: true })), {
    matches: [threadSearchMatchOf(entry())],
    truncated: true,
  }),
);
expect("truncated 缺省为假", threadSearchResultOf({ matches: [] })!.truncated === false);
expect("truncated 非布尔拒绝", threadSearchResultOf(resultOf({ truncated: "true" })) === null);
expect(
  "matches 非数组拒绝",
  threadSearchResultOf(resultOf({ matches: {} })) === null,
);
expect(
  "matches 200 通过",
  threadSearchResultOf(resultOf({ matches: Array.from({ length: 200 }, () => entry()) }))!.matches.length === 200,
);
expect(
  "matches 201 拒绝",
  threadSearchResultOf(resultOf({ matches: Array.from({ length: 201 }, () => entry()) })) === null,
);
expect(
  "任一命中非法整包拒绝",
  threadSearchResultOf(resultOf({ matches: [entry(), { bad: true }] })) === null,
);
expect(
  "空 matches 回执",
  same(threadSearchResultOf({ matches: [], truncated: false }), { matches: [], truncated: false }),
);
expect(
  "回执非对象拒绝",
  threadSearchResultOf(null) === null
    && threadSearchResultOf(42) === null
    && threadSearchResultOf([]) === null,
);
const rawResult = resultOf();
threadSearchResultOf(rawResult);
expect("回执不被修改", same(rawResult, resultOf()));

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const TITLE_LIMIT = 4096;",
    "const SNIPPET_LIMIT = 4096;",
    "export const SEARCH_MATCH_LIMIT = 200;",
    'const ROLES: ReadonlySet<string> = new Set(["user", "agent", "tool"]);',
    "function boundedText(value: unknown, limit: number): value is string {",
    'return typeof value === "string" && value.length > 0 && value.length <= limit;',
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    "const raw = value as Record<string, unknown>;",
    "if (!boundedText(raw.threadId, ID_LIMIT)) return null;",
    'if (typeof raw.threadTitle !== "string" || raw.threadTitle.length > TITLE_LIMIT) return null;',
    "if (!boundedText(raw.itemId, ID_LIMIT)) return null;",
    'if (typeof raw.role !== "string" || !ROLES.has(raw.role)) return null;',
    'if (typeof raw.snippet !== "string" || raw.snippet.length > SNIPPET_LIMIT) return null;',
    'if (raw.onBranch !== undefined && typeof raw.onBranch !== "boolean") return null;',
    'role: raw.role as ThreadSearchMatch["role"],',
    '...(typeof raw.onBranch === "boolean" ? { onBranch: raw.onBranch } : {}),',
    "if (!Array.isArray(raw.matches) || raw.matches.length > SEARCH_MATCH_LIMIT) return null;",
    'if (raw.truncated !== undefined && typeof raw.truncated !== "boolean") return null;',
    "const matches: ThreadSearchMatch[] = [];",
    "const match = threadSearchMatchOf(item);",
    "if (!match) return null;",
    "matches.push(match);",
    "return { matches, truncated: raw.truncated === true };",
)

ORDERED = (
    # 单条命中：对象判定 → 标识 → 标题 → 角色 → 片段 → 返回带类型的对象。
    (
        "export function threadSearchMatchOf(value: unknown): ThreadSearchMatch | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!boundedText(raw.threadId, ID_LIMIT)) return null;",
        'if (typeof raw.threadTitle !== "string" || raw.threadTitle.length > TITLE_LIMIT) return null;',
        "if (!boundedText(raw.itemId, ID_LIMIT)) return null;",
        'if (typeof raw.role !== "string" || !ROLES.has(raw.role)) return null;',
        'if (typeof raw.snippet !== "string" || raw.snippet.length > SNIPPET_LIMIT) return null;',
        'if (raw.onBranch !== undefined && typeof raw.onBranch !== "boolean") return null;',
        'role: raw.role as ThreadSearchMatch["role"],',
        '...(typeof raw.onBranch === "boolean" ? { onBranch: raw.onBranch } : {}),',
    ),
    # 整体回执：对象判定 → 上限 → 截断标记类型 → 逐条校验 → 拒绝整包。
    (
        "export function threadSearchResultOf(value: unknown): ThreadSearchResult | null {",
        'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
        "if (!Array.isArray(raw.matches) || raw.matches.length > SEARCH_MATCH_LIMIT) return null;",
        'if (raw.truncated !== undefined && typeof raw.truncated !== "boolean") return null;',
        "for (const item of raw.matches) {",
        "if (!match) return null;",
        "matches.push(match);",
        "return { matches, truncated: raw.truncated === true };",
    ),
)


# 内核：会话有位置记录时按当前分支投影出条目集合，命中逐条标明是否在它上面；
# 投影失败时省略字段，搜索结果照常返回。
KERNEL_MARK = (
    "entries = self.read_entries(thread[\"id\"])",
    "items = self._project_items(thread[\"id\"], entries)",
    "branch_item_ids: set[str] | None = None",
    'if any(entry.get("type") == LEAF_ENTRY_TYPE for entry in entries):',
    "branch_item_ids = {str(item.get(\"id\") or \"\")",
    "self._active_entries(entries))}",
    "except ValueError:",
    "branch_item_ids = None",
    "if branch_item_ids is not None:",
    'match["onBranch"] = item_id in branch_item_ids',
    "matches.append(match)",
)
# 弹窗：只在确认不在当前分支时显示标签，并把该事实随打开动作传给会话区。
DIALOG_MARK = (
    "onOpenMessage?: (session: SessionItem, itemId: string, revealToolBlock: boolean, query: string, offBranch?: boolean) => void;",
    "onOpenMessage(option.row.session, focus.itemId, focus.revealToolBlock, focus.query, option.hit.onBranch === false);",
    "hit.onBranch === false && <b className=\"search-branch-badge\"",
)
# 会话区：历史未读尽时继续等待；列表就绪仍找不到时说明原因并可关闭，不静默放弃。
CONVERSATION_MARK = (
    "focusOffBranch?: boolean;",
    "focusMessageId, focusRevealTool = false, focusOffBranch = false, onFocusMessage,",
    "const [focusMiss, setFocusMiss] = useState(false);",
    "if (messages.length && !loadingHistory) setFocusMiss(true);",
    "setFocusMiss(false);",
    "[focusMessageId, focusRevealTool, focusOffBranch, messages, loadingHistory, onFocusMessage]",
    "data-focus-miss",
    "要定位的消息位于被放弃的分支上",
    "没有找到要定位的消息：它可能位于被放弃的分支上，或历史尚未载入。",
    "setFocusMiss(false); onFocusMessage?.();",
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
    rewritten = "".join(
        line for line in source.splitlines(keepends=True) if not line.startswith("import type ")
    )
    if "import type" in rewritten:
        raise ValueError(f"{RESULT} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str, session: str, dialog: str,
                     shell: str, conversation: str, protocol: str, css: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, RESULT)
    for group in ORDERED:
        checked += _ordered(group, source, RESULT)
    # 反向断言：角色必须先过白名单再断言类型；截断标记只取 true；单条非法必须整体拒绝。
    if source.index("ROLES.has(raw.role)") > source.index('raw.role as ThreadSearchMatch["role"]'):
        raise ValueError(f"{RESULT} 的角色必须先过白名单再断言类型")
    if "truncated: raw.truncated }" in source:
        raise ValueError(f"{RESULT} 的截断标记只能取显式 true")
    if "if (!match) continue;" in source:
        raise ValueError(f"{RESULT} 的单条命中非法时必须拒绝整包回执")
    # 分支标记只能取显式布尔：真假值判断会把缺失字段当成「其他分支」。
    if source.count('raw.onBranch === "boolean"') != 1 or "raw.onBranch === false" in source:
        raise ValueError(f"{RESULT} 的 onBranch 只能按显式布尔传递")
    checked += 4
    start = session.find(KERNEL_MARK[0])
    end = session.find("def record_turn(", start)
    if start < 0 or end < 0:
        raise ValueError(f"{SESSION} 缺少搜索的分支标记或其收尾标记")
    checked += _ordered(KERNEL_MARK, session[start:end], SESSION)
    if session.count('match["onBranch"] =') != 1:
        raise ValueError(f"{SESSION} 的搜索命中只能在一处写入 onBranch")
    # 分支投影失败必须省略字段：整段 raise 会让搜索因一条损坏日志整体失败。
    if "except ValueError:\n                        branch_item_ids = None" not in session:
        raise ValueError(f"{SESSION} 的分支标记必须容忍投影失败")
    checked += 2
    checked += _expect(DIALOG_MARK, dialog, DIALOG)
    for fragment in ("revealToolBlock?: boolean; offBranch?: boolean }", "offBranch = false) => {",
                     "setMessageFocus({ threadId: session.id, itemId, revealToolBlock, offBranch });",
                     "focusOffBranch={messageFocus !== null && messageFocus.threadId === props.activeSession?.id && messageFocus.offBranch === true}"):
        if shell.count(fragment) != 1:
            raise ValueError(f"{SHELL} 缺少跨分支定位的传递：{fragment}")
    checked += 4
    checked += _expect(CONVERSATION_MARK, conversation, CONVERSATION)
    # 旧形态：列表就绪后静默清除定位意图。
    if "if (messages.length) onFocusMessage?.();" in conversation:
        raise ValueError(f"{CONVERSATION} 定位失败不能静默放弃")
    if conversation.count("setFocusMiss(false)") != 2:
        raise ValueError(f"{CONVERSATION} 的定位说明只在命中或关闭时清除")
    checked += 2
    if 'onBranch?: boolean;' not in protocol:
        raise ValueError(f"{PROTOCOL} 的搜索命中缺少可选 onBranch")
    for fragment in (".focus-miss-notice {", ".search-branch-badge {"):
        if css.count(fragment) != 1:
            raise ValueError(f"{CSS} 缺少提示行或标签样式：{fragment}")
    checked += 3
    return checked


def _check_behaviors() -> int:
    source = _read(RESULT)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "threadSearchResult.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("搜索回执行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"搜索回执行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_thread_search_result.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_thread_search_result.py")
    if "共 81 项结构、35 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_thread_search_result.py 检查 81 项结构、35 项行为")
    return 2


def check_thread_search_result() -> tuple[int, int]:
    structure = _check_structure(
        _read(RESULT), _read(SESSION), _read(DIALOG), _read(SHELL),
        _read(CONVERSATION), _read(PROTOCOL), _read(CSS),
    )
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_thread_search_result()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"搜索回执核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索回执一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
