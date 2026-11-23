#!/usr/bin/env python3
"""核对系统通知的会话定位载荷与定位意图判定。

`threadFocus.ts` 校验 IPC 载荷里的 threadId，`focusIntent.ts` 决定列表加载状态下
是否应用定位意图。这里静态核对两个模块的契约，并用 Node 直接加载真实模块覆盖
类型错误、空白与超长标识、加载中等待、加载完成放弃等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_FOCUS = "apps/desktop/src/renderer/src/data/threadFocus.ts"
TARGET_RESOLUTION = "apps/desktop/src/renderer/src/data/focusIntent.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 回合结束系统通知的会话定位载荷。",
    " * 定位字段相同的上限重新校验，读不到就放弃定位，绝不猜测或新建会话。",
    "const FIELD_LIMIT = 200;",
    "export function readThreadFocus(value: unknown): { threadId: string } | null {",
    'if (!value || typeof value !== "object") return null;',
    "const record = value as Record<string, unknown>;",
    'const threadId = typeof record.threadId === "string" ? record.threadId.trim() : "";',
    "return threadId && threadId.length <= FIELD_LIMIT ? { threadId } : null;",
    " * 系统通知的定位载荷通常在主窗口重建、渲染层重载或连接刚恢复时到达，此时 `thread/list`",
    " * 可能尚未返回。不能把「列表还没加载」当成「会话不存在」而丢弃定位意图：已找到目标就",
    'export type FocusResolution = "apply" | "wait" | "drop";',
    "export function focusResolution(sessionsLoaded: boolean, sessionFound: boolean): FocusResolution {",
    'if (sessionFound) return "apply";',
    'return sessionsLoaded ? "drop" : "wait";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { readThreadFocus } = await import(pathToFileURL(process.argv[1]).href);
const { focusResolution } = await import(pathToFileURL(process.argv[2]).href);
const result = {
  payload: [
    readThreadFocus(null),
    readThreadFocus(undefined),
    readThreadFocus("t1"),
    readThreadFocus(42),
    readThreadFocus(Object.assign(() => {}, { threadId: "fn" })),
    readThreadFocus({}),
    readThreadFocus({ threadId: 42 }),
    readThreadFocus({ threadId: "" }),
    readThreadFocus({ threadId: "   " }),
    JSON.stringify(readThreadFocus({ threadId: "  t-1  ", extra: true })),
    readThreadFocus({ threadId: "x".repeat(200) })?.threadId.length ?? null,
    readThreadFocus({ threadId: "x".repeat(201) }),
  ],
  resolution: [
    focusResolution(false, false),
    focusResolution(true, false),
    focusResolution(false, true),
    focusResolution(true, true),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_PAYLOAD = (
    None, None, None, None, None, None, None, None, None,
    '{"threadId":"t-1"}', 200, None,
)
EXPECTED_RESOLUTION = ("wait", "drop", "apply", "apply")
LABELS = {"payload": "定位载荷", "resolution": "定位意图"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
             str(ROOT / TARGET_FOCUS), str(ROOT / TARGET_RESOLUTION)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 通知定位试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 通知定位试算失败，请核对 Node.js 24+ 与 threadFocus.ts / focusIntent.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的通知定位结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"通知{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"通知{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["payload"], EXPECTED_PAYLOAD, LABELS["payload"])
            + _compare(payload["resolution"], EXPECTED_RESOLUTION, LABELS["resolution"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_notification_focus.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_notification_focus.py")
    if "共 14 项结构、16 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_notification_focus.py 检查 14 项结构、16 项行为")
    return 2


def check_notification_focus() -> tuple[int, int]:
    structure = (_expect(FRAGMENTS[:8], _read(TARGET_FOCUS), TARGET_FOCUS)
                 + _expect(FRAGMENTS[8:], _read(TARGET_RESOLUTION), TARGET_RESOLUTION))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_notification_focus()
    except (OSError, ValueError) as error:
        print(f"通知定位规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"通知定位规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
