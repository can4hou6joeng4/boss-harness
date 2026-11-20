#!/usr/bin/env python3
"""核对审批高风险标记的失败关闭，以及记住与自动批准的放行条件。

协议把 `consequential` 定义为必填布尔值，内核对每次审批都发出 `true`。桌面有
四处按这个标记做决定：实时审批卡、快照恢复的审批卡、写入「本次会话记住选择」
与自动批准。它们必须共用同一个判定：只有明确的布尔 `false` 才算可记住，缺省
或畸形值一律按必须逐次确认处理。这里固定共享判定与四处的接入，避免某一处
各自约定默认值，让对外操作被显示成可记住或被自动批准代替确认。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = "apps/desktop/src/renderer/src/data/itemFields.ts"
BRIDGE = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
EVENTS = "apps/desktop/src/renderer/src/data/harnessEvents.ts"
APP = "apps/desktop/src/renderer/src/App.tsx"
CONVERSATION = "apps/desktop/src/renderer/src/shell/ConversationArea.tsx"

FLAG = "consequential"
SHARED_READ = "approvalConsequential("
# 标记名在各文件出现的次数，以及其中经共享判定读取的次数。数据层与应用层的读取
# 必须全部经过共享判定；视图只读取已归一的卡片。新增任何一处都要回到这里核对。
FLAG_USES = (
    (BRIDGE, 2, 1),
    (EVENTS, 4, 2),
    (APP, 1, 1),
    (CONVERSATION, 3, 0),
)

FIELDS_FRAGMENTS = (
    "export function approvalConsequential(value: unknown): boolean {",
    "return value !== false;",
)

BRIDGE_FRAGMENTS = (
    'export function toApproval(state: ApprovalState): NonNullable<MessageItem["approval"]> {',
    "const value = plainRecord(state) ?? {};",
    "consequential: approvalConsequential(value.consequential),",
)

EVENTS_FRAGMENTS = (
    "consequential: approvalConsequential(params.consequential),",
    "export function autoApprovalTarget(",
    "event: HarnessEvent, remembered: ReadonlySet<string> | undefined,",
    "): { approvalId: string; toolName: string } | null {",
    'if (event.method !== "approval/requested" || !remembered) return null;',
    "if (approvalConsequential(params.consequential)) return null;",
    'const approvalId = typeof params.approvalId === "string" && params.approvalId ? params.approvalId : undefined;',
    'const toolName = typeof params.toolName === "string" && params.toolName ? params.toolName : undefined;',
    "return approvalId && toolName && remembered.has(toolName) ? { approvalId, toolName } : null;",
    "export function autoApprovalFallback(previous: MessageItem[], event: HarnessEvent, delivery: ApprovalDelivery): MessageItem[] {",
    'if (delivery === "accepted") return previous;',
    "return hasApprovalDecision(previous, event.params?.approvalId) ? previous : reduceHarnessEvent(previous, event);",
    "export function hasApprovalDecision(previous: MessageItem[], approvalId?: string): boolean {",
    "message.approval.approvalId === approvalId && message.approval.decision !== undefined);",
)

APP_FRAGMENTS = (
    "const rememberedApprovals = useRef(new Map<string, Set<string>>());",
    'if (params.kind !== "userMessage" && params.turnId && turnIds.current.has(id) && turnIds.current.get(id) !== params.turnId) return;',
    "const autoApproval = autoApprovalTarget(event, rememberedApprovals.current.get(id));",
    "if (autoApproval) {",
    "void respondApproval(autoApproval.approvalId, true).then(outcome => {",
    'if (outcome.delivery === "accepted") return;',
    "const decided = hasApprovalDecision(cache.current.get(id) ?? [], autoApproval.approvalId);",
    "updateThread(id, previous => autoApprovalFallback(previous, event, outcome.delivery));",
    "const outcome = await respondApproval(approvalId, approved);",
    'if (outcome.delivery !== "accepted") {',
    "const approval = cache.current.get(targetThreadId)?.find(message => message.approval?.approvalId === approvalId)?.approval;",
    "if (remember && approved && approval && !approvalConsequential(approval.consequential)) {",
    "const tools = rememberedApprovals.current.get(targetThreadId) ?? new Set<string>(); tools.add(toolName); rememberedApprovals.current.set(targetThreadId, tools);",
)

CONVERSATION_FRAGMENTS = (
    "const remember = !approval.consequential && (approvalSubmission.remember[msgId] || false);",
    "disabled={Boolean(item.approval.consequential)}",
    '<span>{item.approval.consequential ? "对外操作需要逐次确认" : "本次会话记住选择"}</span>',
)

EVENTS_ORDERED = (
    # 自动批准判定：先看通知与记住集合，再看高风险标记，最后才取标识并比对工具名。
    (
        "export function autoApprovalTarget(",
        'if (event.method !== "approval/requested" || !remembered) return null;',
        "if (approvalConsequential(params.consequential)) return null;",
        'const approvalId = typeof params.approvalId === "string" && params.approvalId ? params.approvalId : undefined;',
        'const toolName = typeof params.toolName === "string" && params.toolName ? params.toolName : undefined;',
        "return approvalId && toolName && remembered.has(toolName) ? { approvalId, toolName } : null;",
        "export function autoApprovalFallback(",
    ),
)

APP_ORDERED = (
    # 自动路径：其他回合的事件先丢弃，判定通过才提交，未受理时按回执时的缓存回退。
    (
        'if (params.kind !== "userMessage" && params.turnId && turnIds.current.has(id) && turnIds.current.get(id) !== params.turnId) return;',
        "const autoApproval = autoApprovalTarget(event, rememberedApprovals.current.get(id));",
        "if (autoApproval) {",
        "void respondApproval(autoApproval.approvalId, true).then(outcome => {",
        'if (outcome.delivery === "accepted") return;',
        "const decided = hasApprovalDecision(cache.current.get(id) ?? [], autoApproval.approvalId);",
        "updateThread(id, previous => autoApprovalFallback(previous, event, outcome.delivery));",
    ),
    # 记住写入：内核受理之后，才按缓存里的审批与共享判定写入记住集合。
    (
        "const outcome = await respondApproval(approvalId, approved);",
        'if (outcome.delivery !== "accepted") {',
        "return outcome;",
        "const approval = cache.current.get(targetThreadId)?.find(message => message.approval?.approvalId === approvalId)?.approval;",
        "if (remember && approved && approval && !approvalConsequential(approval.consequential)) {",
        "tools.add(toolName);",
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


def _flag_uses(text: str, label: str, uses: int, shared: int) -> int:
    """标记名每多出现一次（含解构与类型判断）都算新的使用点，必须回到这里核对。"""
    found = text.count(FLAG)
    through = sum(text.count(f"{SHARED_READ}{owner}.{FLAG})") for owner in ("value", "params", "approval"))
    if found != uses or through != shared:
        raise ValueError(
            f"{label} 的高风险标记出现 {found} 处、经共享判定 {through} 处，应为 {uses} 处与 {shared} 处")
    return 1


def check_approval_remember() -> int:
    fields = _read(FIELDS)
    bridge = _read(BRIDGE)
    events = _read(EVENTS)
    app = _read(APP)
    conversation = _read(CONVERSATION)
    checked = 0
    checked += _expect(FIELDS_FRAGMENTS, fields, FIELDS)
    checked += _expect(BRIDGE_FRAGMENTS, bridge, BRIDGE)
    checked += _expect(EVENTS_FRAGMENTS, events, EVENTS)
    checked += _expect(APP_FRAGMENTS, app, APP)
    checked += _expect(CONVERSATION_FRAGMENTS, conversation, CONVERSATION)
    for group in EVENTS_ORDERED:
        checked += _ordered(group, events, EVENTS)
    for group in APP_ORDERED:
        checked += _ordered(group, app, APP)
    # 反向断言：标记的使用点数量固定，数据层与应用层的读取全部经过共享判定。
    sources = {BRIDGE: bridge, EVENTS: events, APP: app, CONVERSATION: conversation}
    for label, uses, shared in FLAG_USES:
        checked += _flag_uses(sources[label], label, uses, shared)
    # 应用层只有手动裁决与自动批准两处提交；写入记住集合只有一处。
    if app.count("respondApproval(") != 2:
        raise ValueError(f"{APP} 的审批提交只能有手动裁决与自动批准两处")
    if app.count("rememberedApprovals.current.set(") != 1 or app.count("tools.add(") != 1:
        raise ValueError(f"{APP} 的记住集合只能在受理后的一处写入")
    return checked + 2


def main() -> int:
    try:
        checked = check_approval_remember()
    except ValueError as error:
        print(f"审批记住与自动批准核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批记住与自动批准一致：{checked} 项失败关闭判定与放行条件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
