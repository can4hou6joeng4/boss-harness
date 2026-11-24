#!/usr/bin/env python3
"""核对 session/error 通知的形状校验与单行摘要。

提示条把正文直接渲染为 React 子节点：对象或数组会让整屏落入错误边界，
非字符串的会话标识会污染错误缓存。结构侧固定会话标识上限、正文的空白
折叠与码点截断、缺省正文的通用文案，以及无法识别时整条丢弃；行为侧把
真实 `sessionErrorNotice.ts` 与共享 `shared/index.ts` 复制到临时目录、改写
导入，由 Node 驱动形状校验、边界长度与截断行为。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
NOTICE = "apps/desktop/src/renderer/src/data/sessionErrorNotice.ts"
SHARED = "packages/shared/src/index.ts"

EXPECTED = 17

NODE_SCRIPT = """\
import { SESSION_ERROR_FALLBACK, sessionErrorNoticeOf } from "./sessionErrorNotice.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);

expect(
  "非对象被拒绝",
  sessionErrorNoticeOf(null) === null
    && sessionErrorNoticeOf(undefined) === null
    && sessionErrorNoticeOf("x") === null
    && sessionErrorNoticeOf([]) === null,
);
expect("缺会话标识被拒绝", sessionErrorNoticeOf({}) === null);
const arrayLike: any = [];
arrayLike.threadId = "t";
expect("数组参数被拒绝", sessionErrorNoticeOf(arrayLike) === null);
expect("空会话标识被拒绝", sessionErrorNoticeOf({ threadId: "" }) === null);
expect("超长会话标识被拒绝", sessionErrorNoticeOf({ threadId: "a".repeat(201) }) === null);
expect(
  "上限会话标识可用",
  same(sessionErrorNoticeOf({ threadId: "a".repeat(200) }), {
    threadId: "a".repeat(200),
    message: SESSION_ERROR_FALLBACK,
  }),
);
expect(
  "缺省正文回退通用文案",
  same(sessionErrorNoticeOf({ threadId: "t" }), { threadId: "t", message: SESSION_ERROR_FALLBACK }),
);
expect(
  "null 正文回退通用文案",
  same(sessionErrorNoticeOf({ threadId: "t", message: null }), {
    threadId: "t",
    message: SESSION_ERROR_FALLBACK,
  }),
);
expect(
  "空白正文回退通用文案",
  same(sessionErrorNoticeOf({ threadId: "t", message: "  \\n\\t " }), {
    threadId: "t",
    message: SESSION_ERROR_FALLBACK,
  }),
);
expect(
  "非字符串正文被拒绝",
  sessionErrorNoticeOf({ threadId: "t", message: {} }) === null
    && sessionErrorNoticeOf({ threadId: "t", message: 42 }) === null,
);
expect(
  "正文本原样保留",
  same(sessionErrorNoticeOf({ threadId: "t", message: "出错了" }), {
    threadId: "t",
    message: "出错了",
  }),
);
expect(
  "空白折叠为单空格",
  sessionErrorNoticeOf({ threadId: "t", message: "  a\\n\\n b\\tc  " })?.message === "a b c",
);
expect(
  "会话标识原样保留",
  sessionErrorNoticeOf({ threadId: " abc ", message: "x" })?.threadId === " abc ",
);
const long = "字".repeat(600);
expect("六百字不截断", sessionErrorNoticeOf({ threadId: "t", message: long })?.message === long);
const longer = "字".repeat(601);
const clipped = sessionErrorNoticeOf({ threadId: "t", message: longer })?.message ?? "";
expect(
  "超限截断补省略号",
  clipped === "字".repeat(599) + "…" && clipped.length === 600,
);
const surrogate = "a".repeat(598) + "\\u{1F600}" + "bc";
const safe = sessionErrorNoticeOf({ threadId: "t", message: surrogate })?.message ?? "";
const lone = [...safe].some(character => {
  const point = character.codePointAt(0) ?? 0;
  return point >= 0xd800 && point <= 0xdfff;
});
expect("补充平面字符不被切开", !lone && safe.endsWith("…"));
const keys = Object.keys(sessionErrorNoticeOf({ threadId: "t", extra: 1 }) ?? {}).sort();
expect("多余字段被丢弃", same(keys, ["message", "threadId"]));

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    "const ID_LIMIT = 200;",
    "const MESSAGE_LIMIT = 600;",
    'export const SESSION_ERROR_FALLBACK = "任务遇到错误，请检查后重试。";',
    "export interface SessionErrorNotice {",
    "threadId: string;",
    "message: string;",
    "function compact(value: string): string {",
    'const collapsed = value.replace(/\\s+/g, " ").trim();',
    "if (collapsed.length <= MESSAGE_LIMIT) return collapsed;",
    "return `${safeSlice(collapsed, MESSAGE_LIMIT - 1).trimEnd()}…`;",
    "export function sessionErrorNoticeOf(params: unknown): SessionErrorNotice | null {",
    "if (!params || typeof params !== \"object\" || Array.isArray(params)) return null;",
    "const raw = params as Record<string, unknown>;",
    "if (typeof raw.threadId !== \"string\" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT) return null;",
    "if (raw.message !== undefined && raw.message !== null && typeof raw.message !== \"string\") return null;",
    'const message = typeof raw.message === "string" ? compact(raw.message) : "";',
    "return { threadId: raw.threadId, message: message || SESSION_ERROR_FALLBACK };",
)

ORDERED = (
    # 摘要：折叠空白、判上限、按码点截断并补省略号。
    (
        "function compact(value: string): string {",
        'const collapsed = value.replace(/\\s+/g, " ").trim();',
        "if (collapsed.length <= MESSAGE_LIMIT) return collapsed;",
        "return `${safeSlice(collapsed, MESSAGE_LIMIT - 1).trimEnd()}…`;",
    ),
    # 校验：参数形状、会话标识、正文类型，最后回退通用文案。
    (
        "export function sessionErrorNoticeOf(params: unknown): SessionErrorNotice | null {",
        "if (!params || typeof params !== \"object\" || Array.isArray(params)) return null;",
        "const raw = params as Record<string, unknown>;",
        "if (typeof raw.threadId !== \"string\" || raw.threadId.length === 0 || raw.threadId.length > ID_LIMIT) return null;",
        "if (raw.message !== undefined && raw.message !== null && typeof raw.message !== \"string\") return null;",
        'const message = typeof raw.message === "string" ? compact(raw.message) : "";',
        "return { threadId: raw.threadId, message: message || SESSION_ERROR_FALLBACK };",
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
        'import { safeSlice } from "@boss-harness/shared";',
        'import { safeSlice } from "./shared.ts";',
    )
    if 'from "./shared.ts"' not in rewritten:
        raise ValueError(f"{NOTICE} 的共享导入已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, NOTICE)
    for group in ORDERED:
        checked += _ordered(group, source, NOTICE)
    # 反向断言：不得直接按 UTF-16 码元切正文；空白正文必须回退通用文案；
    # 多余字段不得进入结果。
    if "collapsed.slice(" in source:
        raise ValueError(f"{NOTICE} 的正文必须用 safeSlice 按码点截断")
    if 'message: message || ""' in source:
        raise ValueError(f"{NOTICE} 的空白正文必须回退通用文案")
    if "..." in source:
        raise ValueError(f"{NOTICE} 的结果不得夹带多余字段")
    if source.count("SESSION_ERROR_FALLBACK") != 2:
        raise ValueError(f"{NOTICE} 的通用文案只在定义与兜底各出现一次")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(NOTICE)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        (folder / "sessionErrorNotice.ts").write_text(_rewrite(source), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("会话错误提示行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"会话错误提示行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_session_error_notice.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_session_error_notice.py")
    if "共 33 项结构、17 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_session_error_notice.py 检查 33 项结构、17 项行为")
    return 2


def check_session_error_notice() -> tuple[int, int]:
    source = _read(NOTICE)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_session_error_notice()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"会话错误提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话错误提示一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
