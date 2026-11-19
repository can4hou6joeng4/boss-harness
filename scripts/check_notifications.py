#!/usr/bin/env python3
"""核对桌面通知的内容、去重、保留与点击定位边界。

系统通知会在锁屏与通知中心留下副本，所以正文只能来自受限字段：审批通知给出工具名
与截断后的摘要，回合通知只给状态与时长，不携带会话标题或正文。同一审批只提醒一次，
通知对象保留上限内并在关闭或失败后释放；徽标只接受 0–999 的整数。点击通知聚焦窗口，
审批还要同时具备会话与条目 id 才定位，避免打开错误位置。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = "apps/desktop/src/main/approvalNotification.ts"
TURN = "apps/desktop/src/main/turnNotification.ts"
REGISTRY = "apps/desktop/src/main/notificationRegistry.ts"
BADGE = "apps/desktop/src/main/notificationBadge.ts"
HARNESS = "apps/desktop/src/main/harness.ts"

APPROVAL_FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const TOOL_NAME_LIMIT = 120;",
    "const TITLE_LIMIT = 80;",
    "const BODY_LIMIT = 240;",
    "const SEEN_LIMIT = 200;",
    'const FALLBACK_BODY = "有操作等待你的批准，打开工作台查看。";',
    'if (!notification || notification.method !== "approval/requested") return null;',
    "const trimmed = value.trim();",
    "return trimmed && trimmed.length <= limit ? trimmed : null;",
    'const collapsed = value.replace(/\\s+/g, " ").trim();',
    "return `${safeSlice(collapsed, limit - 1).trimEnd()}…`;",
    "const approvalId = exactText(record.approvalId, ID_LIMIT);",
    "const toolName = exactText(record.toolName, TOOL_NAME_LIMIT);",
    "if (!approvalId || !toolName) return null;",
    'const summary = typeof record.summary === "string" ? compact(record.summary, BODY_LIMIT) : "";',
    "const threadId = exactText(record.threadId, ID_LIMIT);",
    "const itemId = exactText(record.itemId, ID_LIMIT);",
    "title: compact(`待批准：${toolName}`, TITLE_LIMIT),",
    "body: summary || FALLBACK_BODY,",
    "...(threadId && itemId ? { threadId, itemId } : {}),",
    "if (seen.has(approvalId)) return false;",
    "seen.add(approvalId);",
    "while (seen.size > limit) {",
    "const oldest = seen.values().next().value;",
    "seen.delete(oldest);",
    "return true;",
)
TURN_FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const START_LIMIT = 200;",
    "export const TURN_NOTIFY_MIN_MS = 20_000;",
    'if (method !== "turn/started" && method !== "turn/completed") return null;',
    'const status = typeof record.status === "string" ? record.status.trim().slice(0, 32) : "";',
    'return { kind: method === "turn/started" ? "started" : "completed", threadId, turnId, ...(status ? { status } : {}) };',
    "starts.set(turnId, startedAt);",
    "const oldest = starts.keys().next().value;",
    "starts.delete(oldest);",
    'if (typeof startedAt !== "number" || typeof finishedAt !== "number") return null;',
    "if (!Number.isFinite(startedAt) || !Number.isFinite(finishedAt)) return null;",
    "return duration >= 0 ? duration : null;",
    'case "completed": return "回合已完成";',
    'case "interrupted": return "回合已中断";',
    'case "blocked": return "回合已暂停";',
    'case "error": return "回合出错";',
    'default: return "回合已结束";',
    "export const formatTurnDuration = formatDurationMs;",
    'if (!event || event.kind !== "completed") return null;',
    "if (duration === null || duration < TURN_NOTIFY_MIN_MS) return null;",
    "body: `运行 ${formatTurnDuration(duration)}，点击打开该会话查看详情。`,",
)
REGISTRY_FRAGMENTS = (
    "export const NOTIFICATION_RETENTION_LIMIT = 32;",
    'if (!Number.isSafeInteger(limit) || limit < 1) throw new Error("通知保留上限必须是正整数");',
    "this.retained.delete(notification);",
    "this.retained.add(notification);",
    "while (this.retained.size > this.limit) {",
    'notification.once("close", release);',
    'notification.once("failed", release);',
    "notification.show();",
)
BADGE_FRAGMENTS = (
    "/** 应用图标徽标只接受 0–999 的整数；其它输入返回 null，调用方保持现有徽标不变。 */",
    "export const BADGE_COUNT_LIMIT = 999;",
    'if (typeof value !== "number" || !Number.isInteger(value)) return null;',
    "return value >= 0 && value <= BADGE_COUNT_LIMIT ? value : null;",
)
HARNESS_FRAGMENTS = (
    "if (startedAt === undefined || BrowserWindow.getFocusedWindow()) return;",
    "const content = turnNotificationContent(notification, startedAt);",
    "if (!content || !Notification.isSupported()) return;",
    "const native = new Notification({ title: content.title, body: content.body });",
    'native.on("click", () => {',
    "const target = revealWindow();",
    "if (target) sendThreadFocus(target, { threadId: event.threadId });",
    "notifications.show(native);",
    "if (BrowserWindow.getFocusedWindow()) return;",
    "const content = approvalNotificationContent(notification);",
    "if (!content || !rememberApproval(notifiedApprovals, content.approvalId)) return;",
    "if (!target || !content.threadId || !content.itemId) return;",
    "sendApprovalFocus(target, { threadId: content.threadId, itemId: content.itemId });",
    "const count = normalizeBadgeCount(value);",
    "if (count === null) return { applied: false };",
    "try { return { applied: app.setBadgeCount(count) }; } catch { return { applied: false }; }",
    "if (!Notification.isSupported()) return { sent: false, supported: false };",
    'const native = new Notification({ title: "Boss Harness", body: "系统通知可用：审批请求与较久回合结束会通过这里提醒。" });',
    "return { sent: true, supported: true };",
    "return { sent: false, supported: true };",
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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_notifications() -> int:
    approval = _read(APPROVAL)
    turn = _read(TURN)
    registry = _read(REGISTRY)
    badge = _read(BADGE)
    harness = _read(HARNESS)
    checked = 0
    checked += _expect(APPROVAL_FRAGMENTS, approval, APPROVAL)
    checked += _expect(TURN_FRAGMENTS, turn, TURN)
    checked += _expect(REGISTRY_FRAGMENTS, registry, REGISTRY)
    checked += _expect(BADGE_FRAGMENTS, badge, BADGE)
    checked += _expect(HARNESS_FRAGMENTS, harness, HARNESS)
    # 审批提醒：只接受审批请求，字段裁剪与回退顺序固定。
    checked += _ordered(
        (
            'if (!notification || notification.method !== "approval/requested") return null;',
            "const approvalId = exactText(record.approvalId, ID_LIMIT);",
            "const toolName = exactText(record.toolName, TOOL_NAME_LIMIT);",
            "if (!approvalId || !toolName) return null;",
            'const summary = typeof record.summary === "string" ? compact(record.summary, BODY_LIMIT) : "";',
            "title: compact(`待批准：${toolName}`, TITLE_LIMIT),",
            "body: summary || FALLBACK_BODY,",
        ),
        approval,
        APPROVAL,
    )
    # 回合提醒：先记录开始时间，结束只提醒运行足够久且窗口不在前台的回合。
    checked += _ordered(
        (
            "const startedAt = turnStartedAt.get(event.turnId);",
            "turnStartedAt.delete(event.turnId);",
            "if (startedAt === undefined || BrowserWindow.getFocusedWindow()) return;",
            "const content = turnNotificationContent(notification, startedAt);",
            "if (!content || !Notification.isSupported()) return;",
            'native.on("click", () => {\n      const target = revealWindow();\n      if (target) sendThreadFocus(target, { threadId: event.threadId });',
            "notifications.show(native);",
        ),
        harness,
        HARNESS,
    )
    # 审批提醒：前台不打扰、同一审批只提醒一次、两个定位 id 齐全才跳转。
    checked += _ordered(
        (
            "function notifyApproval(notification: JsonRpcNotification): void {",
            "if (BrowserWindow.getFocusedWindow()) return;",
            "const content = approvalNotificationContent(notification);",
            "if (!content || !rememberApproval(notifiedApprovals, content.approvalId)) return;",
            "if (!Notification.isSupported()) return;",
            'native.on("click", () => {\n      const target = revealWindow();\n      if (!target || !content.threadId || !content.itemId) return;',
            "sendApprovalFocus(target, { threadId: content.threadId, itemId: content.itemId });\n    });\n    notifications.show(native);",
        ),
        harness,
        HARNESS,
    )
    # 保留队列：重复显示重新排到最新，先注册释放监听再显示。
    checked += _ordered(
        (
            "this.retained.delete(notification);",
            "this.retained.add(notification);",
            "while (this.retained.size > this.limit) {",
            'notification.once("close", release);',
            'notification.once("failed", release);',
            "notification.show();",
        ),
        registry,
        REGISTRY,
    )
    # 反向断言：通知正文不得拼接会话标题、正文或记录参数。
    for label, text in ((APPROVAL, approval), (TURN, turn)):
        for forbidden in ("threadTitle", "record.title", "record.preview", "record.summary &&"):
            if forbidden in text:
                raise ValueError(f"{label} 的通知内容不得携带 {forbidden}")
    if "content.threadId" in turn:
        raise ValueError(f"{TURN} 的通知内容不得携带会话定位字段")
    return checked + 1


def main() -> int:
    try:
        checked = check_notifications()
    except ValueError as error:
        print(f"桌面通知边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面通知边界一致：{checked} 项内容、去重与点击防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
