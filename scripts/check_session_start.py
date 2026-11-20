#!/usr/bin/env python3
"""核对新建会话与首条消息的四种结果。

会话是否存在与首条消息是否送达必须分开：failed 之外都要能打开会话，
unconfirmed 必须保留草稿并按「不确定」处理，只有内核明确拒绝才按失败。
这里固定四种状态、发送结果映射与两处提示的分支，避免用户重发已经建立的会话。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
START = "apps/desktop/src/renderer/src/data/sessionStart.ts"

FRAGMENTS = (
    'import type { ComposerSendOutcome } from "./composerDraft";',
    'import type { SessionItem } from "./mockData";',
    "export type SessionStartOutcome =",
    '| { status: "started"; session: SessionItem }',
    '| { status: "unsent"; session: SessionItem }',
    '| { status: "unconfirmed"; session: SessionItem }',
    '| { status: "failed" };',
    "export function createdSession(outcome: SessionStartOutcome): SessionItem | null {",
    'return outcome.status === "failed" ? null : outcome.session;',
    "export function sessionStartSendOutcome(outcome: SessionStartOutcome): ComposerSendOutcome {",
    'if (outcome.status === "started") return true;',
    'if (outcome.status === "unconfirmed") return "uncertain";',
    "return false;",
    "export function sessionStartNotice(outcome: SessionStartOutcome): string | null {",
    'if (outcome.status === "unsent") {',
    "已创建，但首条消息被内核拒绝；草稿已保留，请打开该会话核对后重试。",
    'if (outcome.status === "unconfirmed") {',
    "已创建，但首条消息提交结果尚未确认；草稿已保留，请从会话列表打开该会话核对，不会自动重试。",
    "export function quickAskNotice(outcome: SessionStartOutcome): string | null {",
    "已创建，但这个问题没有被接受；输入已保留，请从会话列表打开该会话核对后重试。",
    "已创建，但提交结果尚未确认；输入已保留，请从会话列表打开该会话核对，不会自动重试。",
    'if (outcome.status === "failed") {',
    'return "未能创建会话；输入已保留，不会自动重试。请按主界面的提示处理后重试。";',
)

ORDERED = (
    # 会话：只有失败才没有可打开的会话。
    (
        "export function createdSession(outcome: SessionStartOutcome): SessionItem | null {",
        'return outcome.status === "failed" ? null : outcome.session;',
    ),
    # 发送结果：started → 成功；unconfirmed → 不确定；其余 → 失败。
    (
        "export function sessionStartSendOutcome(outcome: SessionStartOutcome): ComposerSendOutcome {",
        'if (outcome.status === "started") return true;',
        'if (outcome.status === "unconfirmed") return "uncertain";',
        "return false;",
    ),
    # 主界面提示：未送达 → 结果未确认 → 其余不提示。
    (
        "export function sessionStartNotice(outcome: SessionStartOutcome): string | null {",
        'if (outcome.status === "unsent") {',
        'if (outcome.status === "unconfirmed") {',
        "return null;",
    ),
    # 快速提问提示：未送达 → 结果未确认 → 创建失败 → 其余不提示。
    (
        "export function quickAskNotice(outcome: SessionStartOutcome): string | null {",
        'if (outcome.status === "unsent") {',
        'if (outcome.status === "unconfirmed") {',
        'if (outcome.status === "failed") {',
        "return null;",
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


def check_session_start() -> int:
    source = _read(START)
    checked = 0
    checked += _expect(FRAGMENTS, source, START)
    for group in ORDERED:
        checked += _ordered(group, source, START)
    # 反向断言：失败之外都有会话；未确认不得按失败处理；创建失败提示只出现一次。
    if 'outcome.status === "started" ? outcome.session : null' in source:
        raise ValueError(f"{START} 失败之外都必须能打开已建立的会话")
    if 'if (outcome.status === "unconfirmed") return false;' in source:
        raise ValueError(f"{START} 的未确认结果必须保留草稿，不能按失败处理")
    if source.count('return "未能创建会话；') != 1:
        raise ValueError(f"{START} 的创建失败提示只能出现在快速提问的失败分支")
    if source.index('return "未能创建会话；') < source.index("export function quickAskNotice"):
        raise ValueError(f"{START} 的创建失败提示不得出现在主界面通知里")
    return checked + 4


def main() -> int:
    try:
        checked = check_session_start()
    except ValueError as error:
        print(f"会话启动核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话启动一致：{checked} 项状态、发送结果与提示")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
