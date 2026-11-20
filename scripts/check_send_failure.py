#!/usr/bin/env python3
"""核对发送失败与结果未确认的措辞边界。

内核明确拒绝说明请求没有进入会话，必须写「发送失败」；断连、IPC 失败或
回执不可读仍按不确定处理，写「提交结果尚未确认」。复核提示保留发送主因，
只追加读取结论。这里固定两种来源的对应关系与下一步文案。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FAILURE = "apps/desktop/src/renderer/src/data/sendFailure.ts"

FRAGMENTS = (
    'import { harnessErrorText, isHarnessRpcRejection } from "./harnessBridge";',
    "export function sendFailureNotice(error: unknown): string {",
    "return isHarnessRpcRejection(error)",
    "? `发送失败：${harnessErrorText(error)}。正在读取会话状态，请核对后重试。`",
    ": `提交结果尚未确认：${harnessErrorText(error)}。正在读取会话状态，请核对记录后再决定下一步。`;",
    "export function sendFailureRecheckNotice(error: unknown, verificationFailure: string): string {",
    'const primary = isHarnessRpcRejection(error) ? "发送失败" : "提交结果尚未确认";',
    "return `${primary}：${harnessErrorText(error)}；${verificationFailure}`;",
)

ORDERED = (
    # 主提示：内核拒绝 → 发送失败；其余 → 结果尚未确认。
    (
        "export function sendFailureNotice(error: unknown): string {",
        "return isHarnessRpcRejection(error)",
        "? `发送失败：",
        ": `提交结果尚未确认：",
    ),
    # 复核提示：先取主因，再拼接读取结论。
    (
        "export function sendFailureRecheckNotice(error: unknown, verificationFailure: string): string {",
        'const primary = isHarnessRpcRejection(error) ? "发送失败" : "提交结果尚未确认";',
        "return `${primary}：${harnessErrorText(error)}；${verificationFailure}`;",
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


def check_send_failure() -> int:
    source = _read(FAILURE)
    checked = 0
    checked += _expect(FRAGMENTS, source, FAILURE)
    for group in ORDERED:
        checked += _ordered(group, source, FAILURE)
    # 反向断言：两种来源不得对调；复核提示不得重复包裹读取说明。
    if 'isHarnessRpcRejection(error) ? "提交结果尚未确认"' in source:
        raise ValueError(f"{FAILURE} 的内核拒绝必须写成发送失败")
    if source.count("正在读取会话状态") != 2:
        raise ValueError(f"{FAILURE} 主提示的下一步说明不得在复核提示里重复")
    if "正在读取会话状态" in source.split("export function sendFailureRecheckNotice")[1]:
        raise ValueError(f"{FAILURE} 复核提示只追加读取结论，不重复包裹说明")
    return checked + 3


def main() -> int:
    try:
        checked = check_send_failure()
    except ValueError as error:
        print(f"发送失败措辞核对失败，{error}", file=sys.stderr)
        return 2
    print(f"发送失败措辞一致：{checked} 项来源判定、下一步与复核拼接")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
