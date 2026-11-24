#!/usr/bin/env python3
"""核对搜索状态行与空态只描述已完成的搜索范围。

状态行与空态分别实现，但必须遵守同一条规则：消息搜索失败、未启用、
查询过短或过长时不能宣称「没有找到相关聊天或消息」；零命中且截断时
两者使用同一说法。结构侧固定各分支文案、顺序与阈值引用；行为侧把真实
`searchStatus.ts` 与共享 `shared/index.ts` 复制到临时目录、改写导入，由
Node 驱动状态行与空态的全部分支，以及按码点计数的最短长度边界。
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
STATUS = "apps/desktop/src/renderer/src/data/searchStatus.ts"
SHARED = "packages/shared/src/index.ts"

EXPECTED = 20

NODE_SCRIPT = """\
import {
  MESSAGE_SEARCH_MAX_LENGTH,
  searchEmptyCopy,
  searchStatusText,
} from "./searchStatus.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);

expect("空查询状态", searchStatusText("", 3, 5, "ready") === "最近聊天");
expect("空白查询状态", searchStatusText("   ", 3, 5, "ready") === "最近聊天");
expect("完成状态", searchStatusText("q", 3, 5, "ready") === "找到 3 个聊天、5 条消息");
expect("完成缺省不截断", searchStatusText("q", 3, 0, "ready") === "找到 3 个聊天、0 条消息");
expect(
  "截断且零消息状态",
  searchStatusText("q", 3, 0, "ready", true) === "找到 3 个聊天；消息搜索不完整",
);
expect(
  "截断且有消息状态",
  searchStatusText("q", 3, 2, "ready", true) === "找到 3 个聊天、2 条消息（仅显示部分结果）",
);
expect(
  "超限状态",
  searchStatusText("q", 3, 0, "tooLong")
    === `找到 3 个聊天；搜索词超过 ${MESSAGE_SEARCH_MAX_LENGTH} 字符，未搜索消息`,
);
expect("失败状态", searchStatusText("q", 3, 0, "error") === "找到 3 个聊天；消息搜索失败");
expect("加载状态", searchStatusText("q", 3, 0, "loading") === "找到 3 个聊天");
expect("空闲状态", searchStatusText("q", 3, 0, "idle") === "找到 3 个聊天");

expect(
  "空查询空态",
  same(searchEmptyCopy("", "ready", true), {
    title: "还没有聊天",
    hint: "创建聊天后，可以在这里快速找到它",
  }),
);
expect(
  "未启用空态",
  same(searchEmptyCopy("q", "ready", false), {
    title: "没有找到相关聊天",
    hint: "当前内核只按标题与项目搜索；升级内核后可搜索消息内容",
  }),
);
expect(
  "失败空态",
  same(searchEmptyCopy("q", "error", true), {
    title: "标题中没有匹配的聊天",
    hint: "消息搜索失败，暂时无法确认消息内容是否有命中；可稍后重试或换个关键词",
  }),
);
expect(
  "超限空态",
  same(searchEmptyCopy("q", "tooLong", true), {
    title: "没有找到匹配的聊天",
    hint: `标题中没有匹配；消息搜索需要 ${MESSAGE_SEARCH_MAX_LENGTH} 个字符以内，可缩短搜索词后重试`,
  }),
);
expect(
  "过短空态",
  same(searchEmptyCopy("a", "ready", true), {
    title: "没有找到匹配的聊天",
    hint: "标题中没有匹配；输入至少 2 个字符可同时搜索消息内容",
  }),
);
expect(
  "双码点 emoji 满足最短长度",
  same(searchEmptyCopy("\\u{1F600}\\u{1F600}", "ready", true), {
    title: "没有找到相关聊天或消息",
    hint: "试试其他关键词、项目名称或消息内容",
  }),
);
expect(
  "单码点补充平面字符过短",
  same(searchEmptyCopy("\\u{1F600}", "ready", true), {
    title: "没有找到匹配的聊天",
    hint: "标题中没有匹配；输入至少 2 个字符可同时搜索消息内容",
  }),
);
expect(
  "加载空态",
  same(searchEmptyCopy("qq", "loading", true), {
    title: "正在搜索消息…",
    hint: "标题结果已更新；消息内容仍在检索中",
  }),
);
expect(
  "空闲空态",
  same(searchEmptyCopy("qq", "idle", true), {
    title: "正在搜索消息…",
    hint: "标题结果已更新；消息内容仍在检索中",
  }),
);
expect(
  "超限空态优先于长度判断",
  same(searchEmptyCopy("a".repeat(MESSAGE_SEARCH_MAX_LENGTH + 1), "tooLong", true), {
    title: "没有找到匹配的聊天",
    hint: `标题中没有匹配；消息搜索需要 ${MESSAGE_SEARCH_MAX_LENGTH} 个字符以内，可缩短搜索词后重试`,
  }),
);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'if (!query.trim()) return "最近聊天";',
    'if (messageState === "ready") {',
    "? `找到 ${chatCount} 个聊天、${messageCount} 条消息（仅显示部分结果）`",
    ": `找到 ${chatCount} 个聊天；消息搜索不完整`",
    "return `找到 ${chatCount} 个聊天、${messageCount} 条消息`;",
    'if (messageState === "tooLong") return `找到 ${chatCount} 个聊天；搜索词超过 ${MESSAGE_SEARCH_MAX_LENGTH} 字符，未搜索消息`;',
    'if (messageState === "error") return `找到 ${chatCount} 个聊天；消息搜索失败`;',
    "return `找到 ${chatCount} 个聊天`;",
    'if (!query.trim()) return { title: "还没有聊天", hint: "创建聊天后，可以在这里快速找到它" };',
    "if (!searchMessages) {",
    'hint: "当前内核只按标题与项目搜索；升级内核后可搜索消息内容",',
    'if (messageState === "error") {',
    'title: "标题中没有匹配的聊天",',
    'hint: "消息搜索失败，暂时无法确认消息内容是否有命中；可稍后重试或换个关键词",',
    'if (messageState === "tooLong") {',
    "hint: `标题中没有匹配；消息搜索需要 ${MESSAGE_SEARCH_MAX_LENGTH} 个字符以内，可缩短搜索词后重试`,",
    "if (codePointLength(query.trim()) < MESSAGE_SEARCH_MIN_LENGTH) {",
    "hint: `标题中没有匹配；输入至少 ${MESSAGE_SEARCH_MIN_LENGTH} 个字符可同时搜索消息内容`,",
    'if (messageState !== "ready") {',
    'title: "正在搜索消息…",',
    'hint: "标题结果已更新；消息内容仍在检索中",',
    'return { title: "没有找到相关聊天或消息", hint: "试试其他关键词、项目名称或消息内容" };',
)

ORDERED = (
    # 状态行：空查询 → 完成（含截断）→ 过长 → 失败 → 其他。
    (
        'if (!query.trim()) return "最近聊天";',
        'if (messageState === "ready") {',
        'if (messageState === "tooLong") return',
        'if (messageState === "error") return',
        "return `找到 ${chatCount} 个聊天`;",
    ),
    # 空态：空查询 → 未启用 → 失败 → 过长 → 过短 → 未完成 → 完整。
    (
        'if (!query.trim()) return { title: "还没有聊天"',
        "if (!searchMessages) {",
        'if (messageState === "error") {',
        'if (messageState === "tooLong") {',
        "if (codePointLength(query.trim()) < MESSAGE_SEARCH_MIN_LENGTH) {",
        'if (messageState !== "ready") {',
        'return { title: "没有找到相关聊天或消息"',
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
    rewritten = source.replace(
        'import { codePointLength } from "@boss-harness/shared";',
        'import { codePointLength } from "./shared.ts";',
    )
    if 'from "./shared.ts"' not in rewritten:
        raise ValueError(f"{STATUS} 的共享导入已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, STATUS)
    for group in ORDERED:
        checked += _ordered(group, source, STATUS)
    # 反向断言：完整结论只在最后分支出现一次；最短字符数不得写死。
    if re.search(r"至少 \d+ 个字符", source):
        raise ValueError(f"{STATUS} 的空态提示必须引用 MESSAGE_SEARCH_MIN_LENGTH，不得写死数字")
    if source.count('title: "没有找到相关聊天或消息"') != 1:
        raise ValueError(f"{STATUS} 的完整结论只能出现在所有未完成分支之后")
    if source.index('title: "没有找到相关聊天或消息"') < source.index('if (messageState !== "ready") {'):
        raise ValueError(f"{STATUS} 的完整结论不得先于未完成分支出现")
    if source.count("MESSAGE_SEARCH_MIN_LENGTH") < 2:
        raise ValueError(f"{STATUS} 的最短字符数必须同时用于触发条件与提示文案")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(STATUS)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        (folder / "searchStatus.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("搜索状态行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"搜索状态行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_search_status.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_search_status.py")
    if "共 38 项结构、20 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_search_status.py 检查 38 项结构、20 项行为")
    return 2


def check_search_status() -> tuple[int, int]:
    source = _read(STATUS)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_search_status()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"搜索状态核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索状态一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
