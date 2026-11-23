#!/usr/bin/env python3
"""核对桌面队列手动刷新结果的展示文案。

`queueRefresh.ts` 把不可信的刷新返回值收敛成三种界面结果：成功为 null，
不可读为保守提示，其余情况折叠空白、裁剪首尾并按 UTF-16 安全上限截断原因。
这里静态核对模块结构，并用 Node 加载真实模块与真实 `safeSlice` 试算边界用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueRefresh.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"
IMPORT_LINE = 'import { safeSlice } from "@boss-harness/shared";\n'

FRAGMENTS = (
    IMPORT_LINE.rstrip("\n"),
    "/** 队列手动刷新的结果：成功时不带原因，失败时带回可展示的原因。 */",
    "export interface QueueRefreshResult {",
    "ok: boolean;",
    "message?: string;",
    "const MESSAGE_LIMIT = 240;",
    "export function queueRefreshErrorText(value: unknown): string | null {",
    'if (!value || typeof value !== "object") return "刷新结果未确认";',
    "const record = value as Record<string, unknown>;",
    "if (record.ok === true) return null;",
    'const message = typeof record.message === "string"',
    r'? safeSlice(record.message.replace(/\s+/g, " ").trim(), MESSAGE_LIMIT)',
    ': "";',
    'return message || "原因未知";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { safeSlice } = await import(pathToFileURL(process.argv[2]).href);
globalThis.safeSlice = safeSlice;
const { queueRefreshErrorText } = await import(pathToFileURL(process.argv[1]).href);
const text = value => queueRefreshErrorText(value);
const result = [
  text(null),
  text(undefined),
  text(42),
  text("ok"),
  text([]),
  text({}),
  text({ ok: true }),
  text({ ok: true, message: "失败" }),
  text({ ok: "true" }),
  text({ ok: false, message: "  失败  原因  " }),
  text({ message: "" }),
  text({ message: "   " }),
  text({ message: "x".repeat(240) }),
  text({ message: "x".repeat(241) }),
  text({ message: "😀".repeat(120) }),
  text({ message: "😀".repeat(120) + "x" }),
  text({ message: "x" + "😀".repeat(120) }),
  text({ ok: false, message: "\n失败\t原因\r\n下一行" }),
  text({ ok: false, message: ["x"] }),
  text({ ok: false, message: 42 }),
];
process.stdout.write(JSON.stringify(result));
"""

UNCONFIRMED = "刷新结果未确认"
UNKNOWN = "原因未知"
LONG = "x" * 240
EMOJI_120 = "😀" * 120
EMOJI_119 = "😀" * 119
EXPECTED = (
    UNCONFIRMED, UNCONFIRMED, UNCONFIRMED, UNCONFIRMED,
    UNKNOWN, UNKNOWN, None, None, UNKNOWN,
    "失败 原因", UNKNOWN, UNKNOWN,
    LONG, LONG, EMOJI_120, EMOJI_120, "x" + EMOJI_119,
    "失败 原因 下一行", UNKNOWN, UNKNOWN,
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _run_node(target: Path) -> list:
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / "queueRefresh.ts"
        source = target.read_text(encoding="utf-8")
        if IMPORT_LINE not in source:
            raise ValueError("目标模块缺少 safeSlice 导入，无法在隔离目录中试算")
        copy.write_text(source.replace(IMPORT_LINE, "", 1), encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
                    str(copy), str(ROOT / SHARED),
                ],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 刷新文案试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 刷新文案试算失败，请核对 Node.js 24+ 与 queueRefresh.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的刷新文案结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回刷新文案列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"刷新文案用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"刷新文案第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_run_node(ROOT / TARGET), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_refresh.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_refresh.py")
    if "共 14 项结构、20 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_refresh.py 检查 14 项结构、20 项行为")
    return 2


def check_queue_refresh() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_refresh()
    except (OSError, ValueError) as error:
        print(f"队列刷新文案核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列刷新文案一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
