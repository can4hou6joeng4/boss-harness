#!/usr/bin/env python3
"""核对内核通知到界面的分发契约：33 项通知、界面落点与豁免理由。

内核把会话、队列、审批、压缩与重试的实时变化推给桌面，主进程原样转发；渲染层若不
接线，更新会被静默丢给事件归约函数。这里从内核源码推导实际发送的通知集合，与固定清单
逐项比对（新增或消失都失败），并要求每项通知要么登记精确的界面分发片段，要么带源码
锚点的豁免理由；豁免还须验证渲染层确实没有引用该方法。行为侧真实构造
`ApplicationService`（`provider=none`），断言创建、重命名、归档、恢复、分支、叶移动与
删除通知的发送方法与载荷标识。不访问网络、模型或招聘平台。
"""

from __future__ import annotations

from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402
from boss_harness.session import Entry  # noqa: E402

PROTOCOL = "packages/protocol/src/index.ts"
KERNEL = "harness/src/boss_harness"
APPLICATION = "harness/src/boss_harness/application.py"
AGENT = "harness/src/boss_harness/agent.py"
SESSION = "harness/src/boss_harness/session.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
APP = "apps/desktop/src/renderer/src/App.tsx"
EVENTS = "apps/desktop/src/renderer/src/data/harnessEvents.ts"
REASONING = "apps/desktop/src/renderer/src/data/useSessionReasoning.ts"
CONTEXT = "apps/desktop/src/renderer/src/data/useContextPanel.ts"
COCKPIT = "apps/desktop/src/renderer/src/data/cockpitData.ts"
BRANCHES = "apps/desktop/src/renderer/src/data/useSessionBranches.ts"
BRIDGE = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
EXPECTED_KERNEL = {
    "agentMessage/delta": {"application.py", "agent.py"},
    "agentThinking/delta": {"application.py", "agent.py"},
    "approval/decided": {"application.py", "agent.py"},
    "approval/requested": {"application.py", "agent.py"},
    "context/compacted": {"application.py"},
    "context/compactionCompleted": {"application.py"},
    "context/compactionFailed": {"application.py"},
    "context/compactionProgress": {"application.py"},
    "context/compactionStarted": {"application.py"},
    "context/edited": {"application.py"},
    "item/completed": {"application.py", "agent.py"},
    "item/started": {"agent.py"},
    "kernel/hookError": {"application.py"},
    "kernel/shutdown": {"hooks.py", "application.py"},
    "model/retryEnded": {"agent.py"},
    "model/retryStarted": {"agent.py"},
    "queue/updated": {"application.py"},
    "session/error": {"application.py", "agent.py"},
    "thread/archived": {"application.py"},
    "thread/created": {"application.py"},
    "thread/deleted": {"session.py"},
    "thread/leafChanged": {"application.py"},
    "thread/model/updated": {"application.py"},
    "thread/reasoning/updated": {"application.py"},
    "thread/renamed": {"application.py"},
    "thread/unarchived": {"application.py"},
    "thread/updated": {"application.py", "agent.py"},
    "toolCall/completed": {"hooks.py", "application.py", "agent.py"},
    "toolCall/executing": {"agent.py"},
    "toolCall/started": {"agent.py"},
    "turn/completed": {"application.py"},
    "turn/started": {"application.py", "agent.py"},
    "turn/steeringApplied": {"application.py"},
}
QUEUE_LIST = '["queue/updated", "turn/steeringApplied", "turn/started", "turn/completed"].includes(event.method)'
THREAD_LIST = '["thread/created", "thread/archived", "thread/unarchived", "thread/renamed", "thread/model/updated"].includes(event.method)'
REASONING_LIST = ('["thread/reasoning/updated", "thread/model/updated", "turn/started", "turn/completed", '
                  '"context/compactionStarted", "context/compactionCompleted", "context/compactionFailed"]')
PLAN_LIST = ('const PLAN_INVALIDATING_EVENTS: readonly string[] = ["turn/started", "turn/completed", '
             '"thread/updated", "context/compacted", "thread/leafChanged"];')
BRANCH_LIST = ('const BRANCH_REFRESH_EVENTS: readonly string[] = ["thread/leafChanged", "turn/started", '
               '"turn/completed", "thread/updated", "context/compacted"];')
REFRESH_METHODS = "\n".join((
    "const REFRESH_METHODS = new Set([",
    '  "turn/started",',
    '  "turn/completed",',
    '  "approval/requested",',
    '  "approval/decided",',
    '  "queue/updated",',
    '  "context/compactionStarted",',
    '  "context/compactionCompleted",',
    '  "context/compactionFailed",',
    '  "context/compacted",',
    "]);",
))
CONSUMERS = {
    "agentMessage/delta": ((EVENTS, 'case "agentMessage/delta":'),),
    "agentThinking/delta": ((EVENTS, 'case "agentThinking/delta":'),),
    "approval/decided": ((EVENTS, 'case "approval/decided":'), (COCKPIT, REFRESH_METHODS)),
    "approval/requested": ((EVENTS, 'case "approval/requested":'), (COCKPIT, REFRESH_METHODS)),
    "context/compacted": ((CONTEXT, PLAN_LIST), (BRANCHES, BRANCH_LIST), (COCKPIT, REFRESH_METHODS)),
    "context/compactionCompleted": ((REASONING, REASONING_LIST), (COCKPIT, REFRESH_METHODS)),
    "context/compactionFailed": ((REASONING, REASONING_LIST), (COCKPIT, REFRESH_METHODS)),
    "context/compactionProgress": ((CONTEXT, 'if (event.method.startsWith("context/compaction")) {'),),
    "context/compactionStarted": ((CONTEXT, 'if (event.method.startsWith("context/compaction")) {'),
                                  (REASONING, REASONING_LIST), (COCKPIT, REFRESH_METHODS)),
    "item/completed": ((EVENTS, 'case "item/completed":'),),
    "model/retryEnded": ((APP, 'if (event.method === "model/retryStarted" || event.method === "model/retryEnded") {'),),
    "model/retryStarted": ((APP, 'if (event.method === "model/retryStarted" || event.method === "model/retryEnded") {'),),
    "queue/updated": ((APP, QUEUE_LIST), (COCKPIT, REFRESH_METHODS)),
    "session/error": ((APP, 'if (event.method === "session/error") {'),),
    "thread/archived": ((APP, THREAD_LIST),),
    "thread/created": ((APP, THREAD_LIST),),
    "thread/deleted": ((APP, 'if (event.method === "thread/deleted") {'),),
    "thread/leafChanged": ((APP, 'if (event.method === "thread/leafChanged") { void replica.reload(id); void refresh(); return; }'),
                            (CONTEXT, PLAN_LIST), (BRANCHES, BRANCH_LIST)),
    "thread/model/updated": ((APP, THREAD_LIST), (REASONING, REASONING_LIST)),
    "thread/reasoning/updated": ((REASONING, REASONING_LIST),),
    "thread/renamed": ((APP, THREAD_LIST),),
    "thread/unarchived": ((APP, THREAD_LIST),),
    "thread/updated": ((APP, 'if (event.method === "thread/updated") {'), (CONTEXT, PLAN_LIST), (BRANCHES, BRANCH_LIST)),
    "toolCall/completed": ((EVENTS, 'case "toolCall/completed":'),),
    "toolCall/executing": ((EVENTS, 'case "toolCall/executing":'),),
    "toolCall/started": ((EVENTS, 'case "toolCall/started":'),),
    "turn/completed": ((APP, QUEUE_LIST), (REASONING, REASONING_LIST), (CONTEXT, PLAN_LIST),
                        (BRANCHES, BRANCH_LIST), (COCKPIT, REFRESH_METHODS)),
    "turn/started": ((APP, QUEUE_LIST), (REASONING, REASONING_LIST), (CONTEXT, PLAN_LIST),
                      (BRANCHES, BRANCH_LIST), (COCKPIT, REFRESH_METHODS)),
    "turn/steeringApplied": ((APP, QUEUE_LIST),),
}
EXEMPT = {
    "context/edited": (
        "编辑回执直接返回最新投影，本窗口按响应更新；其他视图经下一次读取收敛",
        ((APPLICATION, 'self._emit_committed("context/edited", {"threadId": thread_id, "itemId": item_id,'),
         (BRIDGE, "export const writeContextEdit = (params: { threadId: string; itemId: string; sourceDigest: string; replacementText: string | null }): Promise<ContextEditReadResponse> =>")),
    ),
    "item/started": (
        "条目卡片由 toolCall/started 与 agentMessage/delta 建立，item/started 只是开始标记",
        ((AGENT, 'N_ITEM_STARTED, {"threadId": thread_id, "itemId": entry.id, "kind": "toolCall", "toolName": name}'),
         (AGENT, 'N_ITEM_STARTED, {"threadId": thread_id, "itemId": entry.id, "kind": "agentMessage"}')),
    ),
    "kernel/hookError": (
        "仅发给注入 hook 的宿主嵌入方，桌面不注入 hook",
        ((APPLICATION, 'events.emit("kernel/hookError", failure.as_dict(), observe=False)'),
         (APPLICATION, 'events.emit_until("kernel/hookError", failure.as_dict(), deadline=deadline, observe=False)')),
    ),
    "kernel/shutdown": (
        "可选关闭观测；协议明确不能作为进程退出信号",
        ((APPLICATION, 'self.events.emit_until("kernel/shutdown", {"state": "stopping"}, deadline=deadline)'),
         (TECHNICAL_REFERENCE, "客户端不得依赖它判断进程已退出")),
    ),
}
KERNEL_FRAGMENTS = (
    (AGENT, 'N_TURN_STARTED = "turn/started"'),
    (AGENT, 'N_ITEM_STARTED = "item/started"'),
    (AGENT, 'N_THREAD_UPDATED = "thread/updated"'),
    (APPLICATION, 'self._emit_committed("thread/created", {"threadId": thread["id"], "thread": thread})'),
    (APPLICATION, 'self._emit_committed("thread/archived", {"threadId": thread_id})'),
    (APPLICATION, 'self._emit_committed("thread/unarchived", {"threadId": thread_id})'),
    (APPLICATION, 'self._emit_committed("thread/renamed", {"threadId": thread_id, "thread": thread})'),
    (APPLICATION, 'self._emit_committed("thread/model/updated", {"threadId": thread_id, "provider": provider,'),
    (APPLICATION, 'self._emit_committed("thread/reasoning/updated", {"threadId": thread_id, "effort": effort})'),
    (APPLICATION, 'self._emit_committed("thread/leafChanged", {"threadId": thread_id, "leafTurnId": result["leafTurnId"]})'),
    (APPLICATION, 'self._emit_committed("queue/updated", {"threadId": thread_id, "queueId": queue_id})'),
    (APPLICATION, 'self._emit_compaction_terminal(job, "context/compacted"'),
    (APPLICATION, 'self._emit_compaction_terminal(job, "context/compactionCompleted")'),
    (APPLICATION, 'self._emit_compaction_terminal(job, "context/compactionFailed")'),
    (APPLICATION, 'self._emit_committed("context/compactionStarted", self._compaction_public(job))'),
    (APPLICATION, 'self._emit_committed("context/compactionProgress", self._compaction_public(job))'),
    (APPLICATION, 'self.events.emit("approval/decided", payload)'),
    (APPLICATION, 'self.events.emit("turn/steeringApplied", {"threadId": job["threadId"], "turnId": job["turnId"], "queueId": item["id"]})'),
    (APPLICATION, 'notifications = [("session/error", {**payload, "code": "TURN_START_FAILED",'),
    (APPLICATION, '("turn/completed", {**payload, "status": "error"}),'),
    (APPLICATION, '("thread/updated", {**payload, "status": "error"})]'),
    (APPLICATION, 'for method in ("turn/completed", "thread/updated"):'),
    (SESSION, 'event = {"method": "thread/deleted", "params": params}'),
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _protocol_notifications() -> set[str]:
    text = _read(PROTOCOL)
    start = text.find("export const ServerNotifications = {")
    if start < 0:
        raise ValueError("packages/protocol/src/index.ts 缺少 ServerNotifications")
    end = text.find("} as const;", start)
    if end < 0:
        raise ValueError("ServerNotifications 缺少结束标记")
    methods = set(re.findall(r':\s*"([^"]+)"', text[start:end]))
    if not methods:
        raise ValueError("ServerNotifications 没有通知方法")
    return methods


def _kernel_notifications(declared: set[str]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    files = sorted(path.relative_to(ROOT).as_posix()
                   for path in (ROOT / KERNEL).rglob("*.py"))
    for relative in files:
        text = _read(relative)
        for method in declared:
            if f'"{method}"' in text:
                found.setdefault(method, set()).add(Path(relative).name)
    return found


def _expect_text(source: str, fragment: str, label: str) -> int:
    if fragment not in source:
        raise ValueError(f"通知分发契约变化 {label}：缺少片段 {fragment}")
    return 1


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"通知分发契约变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    """静态锁定内核发送集合、界面落点与豁免锚点。"""
    declared = _protocol_notifications()
    kernel = _kernel_notifications(declared)
    checked = 0
    missing = sorted(set(EXPECTED_KERNEL) - set(kernel))
    added = sorted(set(kernel) - set(EXPECTED_KERNEL))
    if missing or added:
        raise ValueError("通知分发契约变化 内核发送集合：缺少 " + ("、".join(missing) or "无")
                         + "；新增 " + ("、".join(added) or "无"))
    for method, files in sorted(EXPECTED_KERNEL.items()):
        if method not in declared:
            raise ValueError(f"通知分发契约变化 协议集合：缺少内核通知 {method}")
        checked += _expect_value(kernel[method], files, f"{method} 发送文件")
    stray = sorted((set(CONSUMERS) | set(EXEMPT)) - set(EXPECTED_KERNEL))
    overlap = sorted(set(CONSUMERS) & set(EXEMPT))
    uncovered = sorted(set(EXPECTED_KERNEL) - set(CONSUMERS) - set(EXEMPT))
    if stray or overlap or uncovered:
        raise ValueError("通知分发契约变化 登记表：多余 " + ("、".join(stray) or "无")
                         + "；重复 " + ("、".join(overlap) or "无")
                         + "；未登记 " + ("、".join(uncovered) or "无"))
    checked += 2
    renderer = "apps/desktop/src/renderer/src"
    renderer_files = sorted(path.relative_to(ROOT).as_posix()
                            for path in (ROOT / renderer).rglob("*.ts*"))
    renderer_text = "\n".join(_read(relative) for relative in renderer_files)
    anchors: set[tuple[str, str]] = set()
    for method, consumers in sorted(CONSUMERS.items()):
        for relative, fragment in consumers:
            anchors.add((relative, fragment))
        literal = any(f'"{method}"' in fragment for _, fragment in consumers)
        prefixed = any(f'startsWith("{prefix}")' in fragment
                       for _, fragment in consumers
                       for prefix in [re.sub(r"[A-Z][A-Za-z]*$", "", method)]
                       if prefix != method and method.startswith(prefix))
        if not (literal or prefixed):
            raise ValueError(f"通知分发契约变化 界面落点：{method} 的片段没有引用该方法名")
    for method, (reason, anchors_) in sorted(EXEMPT.items()):
        if not reason.strip():
            raise ValueError(f"通知分发契约变化 豁免：{method} 缺少理由")
        if f'"{method}"' in renderer_text:
            raise ValueError(f"通知分发契约变化 豁免：{method} 已出现在渲染层，豁免不再成立")
        checked += 1
        for relative, fragment in anchors_:
            anchors.add((relative, fragment))
    for relative, fragment in sorted(anchors):
        checked += _expect_text(_read(relative), fragment, f"{relative} 片段")
    for relative, fragment in KERNEL_FRAGMENTS:
        checked += _expect_text(_read(relative), fragment, f"{relative} 内核发送")
    return checked


@contextmanager
def _clean_environment():
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        yield


class _Workspace:
    def __init__(self, directory: str) -> None:
        self.root = Path(directory)
        self.state = self.root / "state"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.server: JsonRpcServer | None = None

    def service(self, **kwargs) -> ApplicationService:
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, self.state, ModelConfig(provider="none", model="none"),
                                     None, workspace=self.workspace, **kwargs)
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                               "protocolVersion": "0.2.0"})
        service.on_initialized(None)
        self.server = server
        return service

    def take(self) -> list[dict]:
        if self.server is None:
            return []
        lines = self.server._out.getvalue().splitlines()
        self.server._out.seek(0)
        self.server._out.truncate(0)
        return [json.loads(line) for line in lines if line.strip()]


def _methods(events: list[dict], method: str) -> list[dict]:
    return [event for event in events if event.get("method") == method]


def _check_behaviors() -> int:
    """真实发送：创建、重命名、归档、恢复、分支、叶移动与删除。"""
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            thread_id = service.on_thread_start({})["thread"]["id"]
            created = _methods(workspace.take(), "thread/created")
            checked += _expect_value(len(created), 1, "创建通知次数")
            checked += _expect_value((created[0]["params"]["threadId"],
                                      created[0]["params"]["thread"]["id"]),
                                     (thread_id, thread_id), "创建通知载荷")
            service.on_thread_name({"threadId": thread_id, "name": "招聘助手"})
            renamed = _methods(workspace.take(), "thread/renamed")
            checked += _expect_value((len(renamed), renamed[0]["params"]["thread"]["title"]),
                                     (1, "招聘助手"), "重命名通知")
            service.on_thread_archive({"threadId": thread_id})
            checked += _expect_value([event["method"] for event in workspace.take()],
                                     ["thread/archived"], "归档通知")
            service.on_thread_unarchive({"threadId": thread_id})
            checked += _expect_value([event["method"] for event in workspace.take()],
                                     ["thread/unarchived"], "恢复通知")
            service.sessions.record_turn(thread_id, "turn-1", "completed")
            forked = service.on_thread_fork({"threadId": thread_id})["thread"]
            created = _methods(workspace.take(), "thread/created")
            checked += _expect_value((len(created), created[0]["params"]["thread"]["forkedFromId"],
                                      created[0]["params"]["thread"]["forkedFromTurnId"]),
                                     (1, thread_id, "turn-1"), "分支创建通知")
            service.sessions.record_turn(thread_id, "turn-2", "completed")
            service.sessions.append(thread_id, Entry(type="item", payload={
                "kind": "userMessage", "text": "turn-2", "turnId": "turn-2"}))
            service.on_thread_leaf_set({"threadId": thread_id, "turnId": "turn-1"})
            leaf = _methods(workspace.take(), "thread/leafChanged")
            checked += _expect_value((len(leaf), leaf[0]["params"]["leafTurnId"]),
                                     (1, "turn-1"), "分支指针通知")
            service.on_thread_delete({"threadId": forked["id"]})
            deleted = _methods(workspace.take(), "thread/deleted")
            checked += _expect_value((len(deleted), deleted[0]["params"]["deletedThreadId"]),
                                     (1, forked["id"]), "删除通知")
        finally:
            service.close()
    return checked


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if "scripts/check_notification_dispatch.py" not in reference:
        raise ValueError("TECHNICAL_REFERENCE.md 缺少 check_notification_dispatch.py 的索引")
    summary = f"{structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"TECHNICAL_REFERENCE.md 缺少通知分发检查的计数：{summary}")


def main() -> int:
    structures = _check_structures()
    behaviors = _check_behaviors()
    _check_documentation(structures, behaviors)
    print(f"通知分发契约一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"检查失败：{error}")
        raise SystemExit(1) from None
