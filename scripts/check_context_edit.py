#!/usr/bin/env python3
"""核对上下文编辑回执的形状校验。

`contextEdit.ts` 校验 `context/edit/read` 回执，并把可选原因收敛后交给弹窗渲染。
这里静态核对模块契约，并在临时目录加载真实模块覆盖身份匹配、来源摘要、正文字符
上限、布尔标记、原因归一化与截断、额外字段忽略等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/contextEdit.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ContextEditReadResponse } from "@boss-harness/protocol";',
    'import { safeSlice } from "@boss-harness/shared";',
    " * 编辑弹窗把 `reason` 直接作为状态说明与警告正文渲染：对象或数组会让 React 抛",
    "const ID_LIMIT = 200;",
    "const TEXT_LIMIT = 2_000_000;",
    "const REASON_LIMIT = 4096;",
    "const SOURCE_DIGEST = /^[a-f0-9]{64}$/;",
    "const isText = (value: unknown): value is string => typeof value === \"string\" && value.length <= TEXT_LIMIT;",
    "const isId = (value: unknown): value is string =>",
    'typeof value === "string" && value.length > 0 && value.length <= ID_LIMIT;',
    "const plainRecord = (value: unknown): Record<string, unknown> | null =>",
    'value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;',
    "function invalid(): never {",
    'throw new Error("上下文编辑响应与当前消息不匹配，已停止操作。");',
    "export function contextEditOf(value: unknown, expected: ContextEditExpectation): ContextEditReadResponse {",
    "const raw = plainRecord(value);",
    "if (!raw || raw.threadId !== expected.threadId || raw.itemId !== expected.itemId) invalid();",
    "if (!isId(raw.threadId) || !isId(raw.itemId)) invalid();",
    'if (typeof raw.sourceDigest !== "string" || !SOURCE_DIGEST.test(raw.sourceDigest)) invalid();',
    "if (!isText(raw.originalText)) invalid();",
    "if (raw.currentText !== null && !isText(raw.currentText)) invalid();",
    'if (typeof raw.canEdit !== "boolean" || typeof raw.excluded !== "boolean") invalid();',
    "if (raw.reason !== undefined && raw.reason !== null) {",
    'if (typeof raw.reason !== "string") invalid();',
    "const reason = raw.reason.trim();",
    "if (reason) result.reason = safeSlice(reason, REASON_LIMIT);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { contextEditOf } = await import(pathToFileURL(process.argv[1]).href);
const expected = { threadId: "t1", itemId: "i1" };
const digest = "a".repeat(64);
const base = { threadId: "t1", itemId: "i1", sourceDigest: digest, originalText: "hello", currentText: null, canEdit: true, excluded: false };
const shape = value => ({
  threadId: value.threadId,
  itemIdLength: value.itemId.length,
  sourceDigestLength: value.sourceDigest.length,
  originalLength: value.originalText.length,
  currentLength: value.currentText === null ? null : value.currentText.length,
  canEdit: value.canEdit,
  excluded: value.excluded,
  hasReason: "reason" in value,
  reason: value.reason ?? null,
  reasonLength: value.reason === undefined ? null : Array.from(value.reason).length,
  lastCodeUnit: value.reason === undefined ? null : value.reason.charCodeAt(value.reason.length - 1),
});
const attempt = (value, expect = expected) => {
  try {
    return { ok: shape(contextEditOf(value, expect)) };
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
};
const result = {
  cases: [
    attempt(null),
    attempt([]),
    attempt({ ...base, threadId: "t2" }),
    attempt({ ...base, itemId: "i2" }),
    attempt({ ...base, threadId: "" }, { threadId: "", itemId: "i1" }),
    attempt({ ...base, itemId: "" }, { threadId: "t1", itemId: "" }),
    attempt(base),
    attempt({ ...base, currentText: "new" }),
    attempt({ ...base, sourceDigest: "A".repeat(64) }),
    attempt({ ...base, sourceDigest: "a".repeat(63) }),
    attempt({ ...base, sourceDigest: 42 }),
    attempt({ ...base, originalText: 42 }),
    attempt({ ...base, originalText: "x".repeat(2_000_001) }),
    attempt({ ...base, originalText: "x".repeat(2_000_000) }),
    attempt({ ...base, currentText: 42 }),
    attempt({ ...base, canEdit: "yes" }),
    attempt({ ...base, excluded: 0 }),
    attempt({ ...base, reason: undefined }),
    attempt({ ...base, reason: null }),
    attempt({ ...base, reason: "   " }),
    attempt({ ...base, reason: "  why  " }),
    attempt({ ...base, reason: 42 }),
    attempt({ ...base, reason: "🙂".repeat(5000) }),
    attempt({ ...base, extra: true }),
    attempt({ ...base, threadId: "x".repeat(201) }, { threadId: "x".repeat(201), itemId: "i1" }),
    attempt({ ...base, itemId: "y".repeat(201) }, { threadId: "t1", itemId: "y".repeat(201) }),
    attempt({ ...base, threadId: "x".repeat(200) }, { threadId: "x".repeat(200), itemId: "i1" }),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

ERROR = {"error": "上下文编辑响应与当前消息不匹配，已停止操作。"}


def _ok(*, thread="t1", item_length=2, original=5, current=None, can_edit=True, excluded=False,
        reason=None, reason_length=None, last_code_unit=None):
    return {"ok": {
        "threadId": thread, "itemIdLength": item_length, "sourceDigestLength": 64,
        "originalLength": original, "currentLength": current, "canEdit": can_edit,
        "excluded": excluded, "hasReason": reason is not None, "reason": reason,
        "reasonLength": reason_length, "lastCodeUnit": last_code_unit,
    }}


EXPECTED = (
    ERROR,
    ERROR,
    ERROR,
    ERROR,
    ERROR,
    ERROR,
    _ok(),
    _ok(current=3),
    ERROR,
    ERROR,
    ERROR,
    ERROR,
    ERROR,
    _ok(original=2_000_000),
    ERROR,
    ERROR,
    ERROR,
    _ok(),
    _ok(),
    _ok(),
    _ok(reason="why", reason_length=3, last_code_unit=ord("y")),
    ERROR,
    _ok(reason="🙂" * 2048, reason_length=2048, last_code_unit=0xDE42),
    _ok(),
    ERROR,
    ERROR,
    _ok(thread="x" * 200, item_length=2),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "contextEdit.ts"
        target.write_text(
            _read(TARGET).replace('from "@boss-harness/shared"', f'from "{(ROOT / SHARED).as_uri()}"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 上下文编辑试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 上下文编辑试算失败，请核对 Node.js 24+ 与 contextEdit.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的上下文编辑结果") from None
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Node 未返回 cases 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"上下文编辑{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"上下文编辑{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED, "回执")


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_context_edit.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_context_edit.py")
    if "共 26 项结构、27 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_context_edit.py 检查 26 项结构、25 项行为")
    return 2


def check_context_edit() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_context_edit()
    except (OSError, ValueError) as error:
        print(f"上下文编辑规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文编辑规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
