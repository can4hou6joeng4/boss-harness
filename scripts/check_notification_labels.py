#!/usr/bin/env python3
"""核对通知分组标题的拼接与截断。

通知标题优先「项目 · 会话」，缺失会话时用线程 id 前 8 位回退，归档会话补
「 · 已归档」。这里固定空白折叠、去重、后缀保留与按码点截断，避免标题重复、
截断后丢掉归档标记，或把非 BMP 字符切成半个码点。行为侧把真实
`notificationLabels.ts` 与共享 `shared/index.ts` 复制到临时目录、改写导入，
由 Node 直接加载驱动回退、去重、归档后缀与截断边界。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
LABELS = "apps/desktop/src/renderer/src/data/notificationLabels.ts"
SHARED = "packages/shared/src/index.ts"

EXPECTED = 33

NODE_SCRIPT = """\
import { NOTIFICATION_LABEL_LIMIT, notificationGroupLabel } from "./notificationLabels.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const label = (source: Record<string, unknown>): string => notificationGroupLabel(source as any);
const SUFFIX = " · 已归档";

expect("上限常量", NOTIFICATION_LABEL_LIMIT === 120);
expect("只有会话标题", label({ threadId: "t1", session: { title: "标题" } }) === "标题");
expect("标题折叠空白", label({ threadId: "t1", session: { title: "  a \\n\\t b  " } }) === "a b");
expect("缺失会话按线程前 8 位回退", label({ threadId: "abcdefghijkl" }) === "会话 abcdefgh");
expect("会话为 null 同样回退", label({ threadId: "abcdefghijkl", session: null }) === "会话 abcdefgh");
expect("短线程 id 原样回退", label({ threadId: "abc" }) === "会话 abc");
expect("线程 id 先折叠空白再截取", label({ threadId: "  ab  cd  efghij" }) === "会话 ab cd ef");
expect(
  "空线程 id 显示未知",
  label({ threadId: "" }) === "会话 未知" && label({ threadId: "   " }) === "会话 未知",
);
expect("线程 id 非字符串显示未知", label({ threadId: 42 }) === "会话 未知");
expect("空白标题回退", label({ threadId: "abc", session: { title: "   " } }) === "会话 abc");
expect("标题非字符串回退", label({ threadId: "abc", session: { title: 42 } }) === "会话 abc");
expect(
  "项目与会话拼接",
  label({ threadId: "t1", session: { title: "标题" }, project: "项目" }) === "项目 · 标题",
);
expect(
  "项目与标题相同不重复",
  label({ threadId: "t1", session: { title: "标题" }, project: "标题" }) === "标题",
);
expect(
  "折叠后相同也不重复",
  label({ threadId: "t1", session: { title: "a b" }, project: " a   b " }) === "a b",
);
expect(
  "空白项目不拼接",
  label({ threadId: "t1", session: { title: "标题" }, project: "   " }) === "标题",
);
expect(
  "项目非字符串不拼接",
  label({ threadId: "t1", session: { title: "标题" }, project: 42 }) === "标题",
);
expect(
  "项目与回退拼接",
  label({ threadId: "abcdefghij", project: "项目" }) === "项目 · 会话 abcdefgh",
);
expect(
  "归档补后缀",
  label({ threadId: "t1", session: { title: "标题", archived: true } }) === "标题" + SUFFIX,
);
expect(
  "归档只认显式 true",
  label({ threadId: "t1", session: { title: "标题", archived: 1 } }) === "标题"
    && label({ threadId: "t1", session: { title: "标题", archived: "true" } }) === "标题",
);
expect(
  "未归档不补后缀",
  label({ threadId: "t1", session: { title: "标题", archived: false } }) === "标题",
);
expect(
  "项目与归档同时出现",
  label({ threadId: "t1", session: { title: "标题", archived: true }, project: "项目" })
    === "项目 · 标题" + SUFFIX,
);
expect(
  "归档回退标题",
  label({ threadId: "abcdefghij", session: { title: "", archived: true } })
    === "会话 abcdefgh" + SUFFIX,
);
expect(
  "120 字符放行",
  label({ threadId: "t1", session: { title: "a".repeat(120) } }) === "a".repeat(120),
);
const cut = label({ threadId: "t1", session: { title: "a".repeat(121) } });
expect("121 字符截断并补省略号", cut === "a".repeat(119) + "…");
expect("截断结果恰为上限", cut.length === 120);
expect(
  "归档后缀计入上限时 114 放行",
  label({ threadId: "t1", session: { title: "a".repeat(114), archived: true } })
    === "a".repeat(114) + SUFFIX,
);
const archivedCut = label({ threadId: "t1", session: { title: "a".repeat(115), archived: true } });
expect("归档后缀计入上限时 115 截断", archivedCut === "a".repeat(113) + "…" + SUFFIX);
expect("归档截断结果恰为上限", archivedCut.length === 120);
expect(
  "拼接后超限按整体截断",
  label({ threadId: "t1", session: { title: "t".repeat(100) }, project: "p".repeat(100) })
    === ("p".repeat(100) + " · " + "t".repeat(100)).slice(0, 119) + "…",
);
expect(
  "emoji 120 码元放行",
  label({ threadId: "t1", session: { title: "😀".repeat(60) } }) === "😀".repeat(60),
);
const emojiCut = label({ threadId: "t1", session: { title: "😀".repeat(61) } });
expect("截断不切半个码点", emojiCut === "😀".repeat(59) + "…");
expect("截断结果是合法 Unicode", (emojiCut as any).isWellFormed() === true);
const raw = { threadId: "t1", session: { title: " 标题 ", archived: true }, project: " 项目 " };
const snapshot = JSON.stringify(raw);
label(raw);
expect("输入不被修改", JSON.stringify(raw) === snapshot);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    'import type { SessionItem } from "./mockData";',
    "export const NOTIFICATION_LABEL_LIMIT = 120;",
    'const ARCHIVED_SUFFIX = " · 已归档";',
    "const FALLBACK_ID_LIMIT = 8;",
    "function compact(value: unknown): string {",
    'return typeof value === "string" ? value.replace(/\\s+/g, " ").trim() : "";',
    "export function notificationGroupLabel(source: NotificationGroupSource): string {",
    "const threadId = compact(source.threadId);",
    'const fallback = `会话 ${threadId.slice(0, FALLBACK_ID_LIMIT) || "未知"}`;',
    "const title = compact(source.session?.title) || fallback;",
    "const project = compact(source.project);",
    "const base = project && project !== title ? `${project} · ${title}` : title;",
    'const suffix = source.session?.archived === true ? ARCHIVED_SUFFIX : "";',
    "if (base.length + suffix.length <= NOTIFICATION_LABEL_LIMIT) return `${base}${suffix}`;",
    "const room = Math.max(1, NOTIFICATION_LABEL_LIMIT - suffix.length - 1);",
    "return `${safeSlice(base, room)}…${suffix}`;",
)

ORDERED = (
    # 拼接：折叠空白 → 回退 → 标题 → 项目去重 → 后缀 → 放行 → 截断。
    (
        "export function notificationGroupLabel(source: NotificationGroupSource): string {",
        "const threadId = compact(source.threadId);",
        "const fallback =",
        "const title = compact(source.session?.title) || fallback;",
        "const project = compact(source.project);",
        "const base = project && project !== title",
        'const suffix = source.session?.archived === true ? ARCHIVED_SUFFIX : "";',
        "if (base.length + suffix.length <= NOTIFICATION_LABEL_LIMIT) return `${base}${suffix}`;",
        "const room = Math.max(1, NOTIFICATION_LABEL_LIMIT - suffix.length - 1);",
        "return `${safeSlice(base, room)}…${suffix}`;",
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
    rewritten = "".join(
        line for line in source.splitlines(keepends=True) if not line.startswith("import type ")
    ).replace('from "@boss-harness/shared";', 'from "./shared.ts";')
    if "import type" in rewritten or '"@boss-harness/shared"' in rewritten:
        raise ValueError(f"{LABELS} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, LABELS)
    for group in ORDERED:
        checked += _ordered(group, source, LABELS)
    # 反向断言：截断必须按码点；长度判断必须计入后缀；放行路径也带后缀。
    if "base.slice(" in source:
        raise ValueError(f"{LABELS} 的截断必须按 Unicode 码点，不能按 UTF-16 码元")
    if "if (base.length <= NOTIFICATION_LABEL_LIMIT)" in source:
        raise ValueError(f"{LABELS} 的长度判断必须计入归档后缀")
    return checked + 2


def _check_behaviors() -> int:
    source = _read(LABELS)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "notificationLabels.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("通知标题行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"通知标题行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_notification_labels.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_notification_labels.py")
    if "共 29 项结构、33 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_notification_labels.py 检查 29 项结构、33 项行为")
    return 2


def check_notification_labels() -> tuple[int, int]:
    structure = _check_structure(_read(LABELS))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_notification_labels()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"通知标题核对失败，{error}", file=sys.stderr)
        return 2
    print(f"通知标题一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
