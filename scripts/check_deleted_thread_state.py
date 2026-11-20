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
APPROVAL = "apps/desktop/src/renderer/src/data/approvalSubmission.ts"
DIALOGS = "apps/desktop/src/renderer/src/data/deletedDialogTarget.ts"
PANEL = "apps/desktop/src/renderer/src/data/useContextPanel.ts"
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"
APP = "apps/desktop/src/renderer/src/App.tsx"

MODULE_FRAGMENTS = (
    "export type ForgettableByThread = { delete(key: string): boolean };",
    "export function forgetDeletedThread(targets: readonly ForgettableByThread[], threadId: string): boolean {",
    "if (!threadId) return false;",
    "let forgotten = false;",
    "for (const target of targets) if (target.delete(threadId)) forgotten = true;",
    "return forgotten;",
)

withoutThread_FRAGMENTS = (
    "export function withoutThread<T>(record: Record<string, T>, threadId: string): Record<string, T> {",
    "if (!threadId || !Object.prototype.hasOwnProperty.call(record, threadId)) return record;",
    "const next = { ...record };",
    "delete next[threadId];",
    "return next;",
)

PANEL_FRAGMENTS = (
    'import { withoutThread } from "./deletedThreadState";',
    "const forgotten = useRef(new Set<string>());",
    "if (!alive.current || forgotten.current.has(id)) return;",
    "const forget = useCallback((id: string) => {",
    "if (!id || !alive.current || forgotten.current.has(id)) return;",
    "forgotten.current.add(id);",
    "readVersions.current.set(id, (readVersions.current.get(id) ?? 0) + 1);",
    "readFlights.current.delete(id);",
    "if (!current.current.connected || forgotten.current.has(id)) return Promise.resolve();",
    "const next = withoutThread(stateRef.current, id);",
    "forgotten.current.clear();",
    'if (event.method === "thread/deleted") {',
    "if (typeof params.threadId === \"string\") forget(params.threadId);",
)

BRANCH_FRAGMENTS = (
    'import { withoutThread } from "./deletedThreadState";',
    "const forgotten = useRef(new Set<string>());",
    "if (!alive.current || forgotten.current.has(id)) return;",
    "const forget = useCallback((id: string) => {",
    "if (!id || !alive.current || forgotten.current.has(id)) return;",
    "versions.current.set(id, (versions.current.get(id) ?? 0) + 1);",
    "if (target.current?.threadId === id) target.current = null;",
    "if (!current.current.connected || !current.current.support || forgotten.current.has(id)) return;",
    "const next = withoutThread(stateRef.current, id);",
    "forgotten.current.clear();",
    'if (event.method === "thread/deleted") {',
    "if (typeof params.threadId === \"string\") forget(params.threadId);",
)

APPROVAL_FRAGMENTS = (
    "export function forgetApprovalSubmission(threadId: string): boolean {",
    "if (!threadId) return false;",
    "return submissions.delete(threadId);",
    "export function approvalSubmissionIsCurrent(threadId: string, submission: ReturnType<typeof approvalSubmissionFor>): boolean {",
    "return submissions.get(threadId) === submission;",
)

DIALOG_FRAGMENTS = (
    "export type DialogThreadTarget = { threadId: string } | null;",
    "export function detachedTarget<T extends DialogThreadTarget>(target: T, deleted: string): T | null {",
    "if (!target || !deleted) return target;",
    "return target.threadId === deleted ? null : target;",
)

APP_FRAGMENTS = (
    'import { forgetDeletedThread } from "./data/deletedThreadState";',
    'import { detachedTarget } from "./data/deletedDialogTarget";',
    'import { approvalSubmissionFor, approvalSubmissionIsCurrent, forgetApprovalSubmission } from "./data/approvalSubmission";',
    'const clearDeletedConversationRef = useRef<((id: string) => void) | null>(null);',
    'const dismissDeletedTargetsRef = useRef<((id: string) => void) | null>(null);',
    "const clearDeletedConversation = useCallback((id: string) => {",
    "if (activeRef.current?.id === id) clearActiveConversation();",
    "clearDeletedConversationRef.current = clearDeletedConversation;",
    "dismissDeletedTargetsRef.current = (id: string) => {",
    "if (context !== contextTarget) { contextPanel.close(); setContextTarget(context); }",
    "if (usage !== usageTarget) { threadUsage.close(); setUsageTarget(usage); }",
    "if (exported !== exportTarget) setExportTarget(exported);",
    "if (branch !== branchTarget) { setIsBranchesOpen(false); setBranchTarget(branch); }",
    "if (rewind !== rewindTarget) setRewindTarget(rewind);",
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
    checked += _expect(APPROVAL_FRAGMENTS, _read(APPROVAL), APPROVAL)
    checked += _expect(DIALOG_FRAGMENTS, _read(DIALOGS), DIALOGS)
    checked += _expect(withoutThread_FRAGMENTS, module, MODULE)
    checked += _expect(PANEL_FRAGMENTS, _read(PANEL), PANEL)
    checked += _expect(BRANCH_FRAGMENTS, _read(BRANCHES), BRANCHES)
    checked += _expect(APP_FRAGMENTS, app, APP)

    # 两个 hook 都必须在通用会话 id 分支之前处理删除通知，且处理完直接返回：
    # 否则通用分支会按旧状态继续读取，或把删除事件当成任务事件刷新。
    for relative, after in ((PANEL, "const id = typeof params.threadId"), (BRANCHES, "if (!id || !current.current.support)")):
        hook = _read(relative)
        removal = hook.find('if (event.method === "thread/deleted") {')
        generic = hook.find(after)
        if removal < 0 or generic < 0 or removal > generic:
            raise ValueError(f"{relative} 的删除通知必须在通用会话分支之前处理")
        checked += 1
        deleted = _slice(hook, 'if (event.method === "thread/deleted") {', "\n      }\n", relative)
        if "return;" not in deleted:
            raise ValueError(f"{relative} 的删除通知处理必须直接返回，不进入通用刷新")
        checked += 1
        forget = _slice(hook, "const forget = useCallback((id: string) => {", "\n  }, []);", relative)
        # 遗忘直接改写状态表；经 update 写入会被自身守卫丢弃，也说明删除路径仍在走常规更新。
        if "update(id" in forget:
            raise ValueError(f"{relative} 的遗忘不得经 update 写入状态")
        if "stateRef.current = next;" not in forget or "setStates(next);" not in forget:
            raise ValueError(f"{relative} 的遗忘必须从状态表移除会话并更新界面")
        checked += 1
        # 定时器仍只遍历状态表：会话被移除后自然不再轮询，不依赖逐项跳过。
        interval = 2000 if relative == BRANCHES else 1500
        if "}, " + str(interval) + ");" not in hook:
            raise ValueError(f"{relative} 的轮询间隔或收尾标记变化")
        checked += 1

    branch = _slice(app, 'if (event.method === "thread/deleted")', "if (!id) return;", APP)
    # 通知分支：先让在途队列读取失效并遗忘六类连接内状态，再清完成标记与视图，最后移除列表项并刷新。
    position = -1
    for fragment in (
        "queueReads.current.invalidate(deleted);",
        f"{FORGET_TARGETS}, deleted);",
        "forgetApprovalSubmission(deleted);",
        "clearCompletedUnread(deleted);",
        "releaseInterrupt(deleted);",
        "clearDeletedConversationRef.current?.(deleted);",
        "dismissDeletedTargetsRef.current?.(deleted);",
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
        "queueReads.current.invalidate(session.id);",
        f"{FORGET_TARGETS}, session.id);",
        "forgetApprovalSubmission(session.id);",
        "clearCompletedUnread(session.id);",
        "if (activeRef.current?.id === session.id) clearActiveConversation();",
        "dismissDeletedTargetsRef.current?.(session.id);",
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
    # 弹窗目标只在目标会话被删除时收起：五个固定目标逐一判定，不得无条件清空。
    dismiss = _slice(app, "dismissDeletedTargetsRef.current = (id: string) => {", "\n  };", APP)
    if dismiss.count("detachedTarget(") != 5:
        raise ValueError(f"{APP} 的删除弹窗清理必须逐一判定五个固定目标")
    for stale in ("setContextTarget(null);", "setUsageTarget(null);", "setExportTarget(null);",
                  "setBranchTarget(null);", "setRewindTarget(null);"):
        if stale in dismiss:
            raise ValueError(f"{APP} 的删除弹窗清理不得无条件清空目标：{stale}")
    # 在途审批只可结算发起时的实例；检查必须先于消息回退、重读与提示写入。
    for start, end, fragments in (
        ("if (autoApproval) {", 'if (event.method === "model/retryStarted"', (
            "const submission = approvalSubmissionFor(id);",
            "void respondApproval(autoApproval.approvalId, true).then(outcome => {",
            "if (!approvalSubmissionIsCurrent(id, submission)) return;",
            'if (outcome.delivery === "accepted") return;',
            "updateThread(id,",
            "submission.reportError(",
        )),
        ("const handleApproval = useCallback", "const openRewind", (
            "const submission = approvalSubmissionFor(targetThreadId);",
            "const outcome = await respondApproval(approvalId, approved);",
            "if (!approvalSubmissionIsCurrent(targetThreadId, submission)) return outcome;",
            'if (outcome.delivery !== "accepted") {',
            "updateThread(targetThreadId,",
        )),
    ):
        callback = _slice(app, start, end, APP)
        position = -1
        for fragment in fragments:
            index = callback.find(fragment)
            if index < 0 or index <= position:
                raise ValueError(f"{APP} 的审批回执实例检查缺失或顺序变化：{fragment}")
            position = index
            checked += 1
        if ").reportError(" in callback:
            raise ValueError(f"{APP} 的审批回执不得重新取得实例写入错误")
    return checked


def main() -> int:
    try:
        checked = check_deleted_thread_state()
    except ValueError as error:
        print(f"删除会话状态清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除会话状态清理一致：{checked} 项遗忘、在途失效与视图退出防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
