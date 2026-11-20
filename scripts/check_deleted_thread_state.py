#!/usr/bin/env python3
"""核对删除会话通知的连接内状态清理与当前视图退出。

内核在 `thread/delete` 回执之前广播 `thread/deleted`。回执丢失或形状不符时列表按约定
保留，但通知已移除侧栏条目；被删除的正是当前会话时，界面不能停在已不存在的聊天上。
`deletedThreadState.ts` 按会话遗忘消息缓存、队列投影、失败提示、条目版本、回合标识
与记住的审批；主界面的删除通知与删除回执复用同一组目标，并清掉后台完成标记。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "apps/desktop/src/renderer/src/data/deletedThreadState.ts"
APP = "apps/desktop/src/renderer/src/App.tsx"

MODULE_FRAGMENTS = (
    "export type ForgettableByThread = { delete(key: string): boolean };",
    "export function forgetDeletedThread(targets: readonly ForgettableByThread[], threadId: string): boolean {",
    "if (!threadId) return false;",
    "let forgotten = false;",
    "for (const target of targets) if (target.delete(threadId)) forgotten = true;",
    "return forgotten;",
)

APP_FRAGMENTS = (
    'import { forgetDeletedThread } from "./data/deletedThreadState";',
    'const clearDeletedConversationRef = useRef<((id: string) => void) | null>(null);',
    "const clearDeletedConversation = useCallback((id: string) => {",
    "if (activeRef.current?.id === id) clearActiveConversation();",
    "clearDeletedConversationRef.current = clearDeletedConversation;",
    "applyQueuePage, clearCompletedUnread, clearModelRetry",
)

FORGET_TARGETS = "forgetDeletedThread([cache.current, queueCache.current, sessionErrors.current, versions.current, turnIds.current, rememberedApprovals.current]"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _slice(text: str, start_marker: str, end_marker: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"{label} 缺少：{start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise ValueError(f"{label} 缺少收尾标记：{end_marker}")
    return text[start:end]


def check_deleted_thread_state() -> int:
    module = _read(MODULE)
    app = _read(APP)
    checked = _expect(MODULE_FRAGMENTS, module, MODULE)
    checked += _expect(APP_FRAGMENTS, app, APP)

    branch = _slice(app, 'if (event.method === "thread/deleted")', "if (!id) return;", APP)
    # 通知分支：先遗忘六类连接内状态，再清完成标记与视图，最后移除列表项并刷新。
    position = -1
    for fragment in (
        f"{FORGET_TARGETS}, deleted);",
        "clearCompletedUnread(deleted);",
        "releaseInterrupt(deleted);",
        "clearDeletedConversationRef.current?.(deleted);",
        "setFolders(previous => previous.map(folder => ({ ...folder, sessions: folder.sessions.filter(item => item.id !== deleted) })));",
        "void refresh();",
    ):
        index = branch.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{APP} 的删除通知分支缺少或首次出现顺序变化：{fragment}")
        position = index
        checked += 1

    delete_session = _slice(app, "const handleDeleteSession = useCallback", "/** 归档/恢复会话", APP)
    for fragment in (
        f"{FORGET_TARGETS}, session.id);",
        "clearCompletedUnread(session.id);",
        "if (activeRef.current?.id === session.id) clearActiveConversation();",
    ):
        if fragment not in delete_session:
            raise ValueError(f"{APP} 的删除回执缺少：{fragment}")
        checked += 1

    # 反向断言：两条删除路径都不能退回只删缓存的旧写法，视图退出必须在列表移除之前读到会话。
    for stale in ("cache.current.delete(deleted);", "queueCache.current.delete(deleted);"):
        if stale in branch:
            raise ValueError(f"{APP} 的删除通知分支仍单独删除：{stale}")
    if "cache.current.delete(session.id);" in delete_session:
        raise ValueError(f"{APP} 的删除回执仍单独删除消息缓存")
    if "clearDeletedConversationRef.current?.(deleted);" in delete_session:
        raise ValueError(f"{APP} 的删除回执应直接退出视图，不依赖通知回调")
    return checked


def main() -> int:
    try:
        checked = check_deleted_thread_state()
    except ValueError as error:
        print(f"删除会话状态清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除会话状态清理一致：{checked} 项遗忘、视图退出与复用防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
