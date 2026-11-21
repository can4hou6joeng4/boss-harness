#!/usr/bin/env python3
"""核对中断回合续接的预检边界与文档一致性。

`turn/continuation/read` 的预检决定「继续中断回合」入口是否出现，也决定
`turn/continue` 能否启动新回合：最新回合与已有续接回合都按当前分支判定，
`continuationId` 去重却按整份会话日志判定。原因码散落在预检的各个门禁里，
技术参考的原因码表必须与源码双向一致，否则用户看到新的拒绝码却无处可查。
这里同时固定桌面入口的触发条件、回执形状校验与按钮禁用条件，避免把不可
续接的回合显示成可续接，或在回执未知时自动重发。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = "harness/src/boss_harness/application.py"
SESSION = "harness/src/boss_harness/session.py"
REFERENCE = "docs/TECHNICAL_REFERENCE.md"
STATUS = "docs/STATUS.md"
USER_GUIDE = "docs/USER_GUIDE.md"
DESKTOP_GUIDE = "docs/DESKTOP_GUIDE.md"
APP = "apps/desktop/src/renderer/src/App.tsx"
RECEIPT = "apps/desktop/src/renderer/src/data/continuation.ts"
CONVERSATION = "apps/desktop/src/renderer/src/shell/ConversationArea.tsx"
WORKFLOW = ".github/workflows/build.yml"

EXPECTED_CODES = 28
REASON_CODE = re.compile(r'fail\("([A-Z][A-Z0-9_]+)"')
TABLE_ROW = re.compile(r"^\| `([A-Z][A-Z0-9_]+)` \|", re.MULTILINE)

# 预检顺序：运行状态门禁 → 按当前分支读取 → 最新回合 → 中断状态 → 已有续接。
PLAN_ORDERED = (
    "def _turn_continuation_plan(self, thread_id: str, source_turn_id: str) -> dict[str, Any]:",
    'if thread.get("archived"):',
    'return fail("THREAD_ARCHIVED", "请先恢复会话，再检查中断回合。")',
    'return fail("KERNEL_SHUTTING_DOWN", "内核正在关闭，当前不能续接。")',
    'return fail("THREAD_BUSY", "会话仍有运行或收尾任务。")',
    'return fail("THREAD_REQUIRES_REVIEW", "工具结果持久化状态需要人工核对。")',
    'return fail("QUEUE_REQUIRES_REVIEW", "队列中仍有投递状态未核对的请求。")',
    'return fail("TURN_ADMISSION_WAITING", "已有更早排队的任务等待并发槽位。")',
    "entries = self.sessions._active_entries(self.sessions.read_entries_snapshot(thread_id))",
    "turns = self.sessions._turns(entries, thread_id)",
    'if not turns or turns[-1].get("turnId") != source_turn_id:',
    'return fail("CONTINUATION_NOT_LATEST", "只有最新回合可以续接。")',
    'if source is None or source.get("status") != "interrupted":',
    'return fail("CONTINUATION_NOT_INTERRUPTED", "来源回合不是可检查的中断状态。")',
    'if any(turn.get("continuedFromTurnId") == source_turn_id for turn in turns):',
    'return fail("CONTINUATION_ALREADY_EXISTS", "该中断回合已经创建过续接回合。")',
)
# `turn/continue`：去重先读整份日志，再走同一预检。
CONTINUE_ORDERED = (
    "def on_turn_continue(self, params: dict | None) -> dict:",
    "entries = self.sessions.read_entries_snapshot(thread_id)",
    "turns = self.sessions._turns(entries, thread_id)",
    'matches = [turn for turn in turns if turn.get("continuationId") == continuation_id]',
    "if (len(matches) != 1 or matches[0].get(\"continuedFromTurnId\") != source_turn_id):",
    '{"code": "CONTINUATION_ID_CONFLICT"}',
    '"deduplicated": True',
    "plan = self._turn_continuation_plan(thread_id, source_turn_id)",
    '{"code": plan.get("reasonCode", "CONTINUATION_REJECTED"),',
)
READ_MARK = (
    'if set(params) != {"threadId", "sourceTurnId"}:',
    'result = {"threadId": thread_id, "sourceTurnId": source_turn_id,',
    '"eligible": plan["eligible"], "warning": CONTINUATION_WARNING}',
    'for key in ("boundary", "completedToolCalls", "reasonCode", "reason"):',
    'CONTINUATION_WARNING = ("续接会发起新的模型请求，可能重复调用并产生额外费用；已完成工具结果会沿用，"',
)
# 桌面入口：能力字段 → 当前分支中断回合 → 只读预检 → 回执校验 → 一次性编号 → 未知回执不重发。
APP_MARK = (
    "setContinuationSupported(status?.capabilities?.explicitTurnContinuation === true);",
    'const sourceTurnId = session.lastTurnStatus === "interrupted" ? session.turnId : undefined;',
    "if (!window.boss || !continuationSupported || !sourceTurnId || session.projectId !== HARNESS_PROJECT_ID || session.archived === true) {",
    "const raw = await readTurnContinuation({ threadId: session.id, sourceTurnId });",
    "const response = continuationReadOf(raw, { threadId: session.id, sourceTurnId });",
    "const continuationId = crypto.randomUUID();",
    "const response = await continueTurn({ threadId: check.threadId, sourceTurnId: check.sourceTurnId, continuationId });",
    "if (response.continuedFromTurnId !== check.sourceTurnId || response.continuationId !== continuationId || !continuedTurnId) {",
    "续接请求的回执尚未确认：",
    "本次不会自动重发。",
    "matchesContinuation(previous, check) ? null : previous",
)
RECEIPT_MARK = (
    'const BOUNDARIES: ReadonlySet<string> = new Set(["user_input", "completed_tool_batch"]);',
    "if (!raw || raw.threadId !== expected.threadId || raw.sourceTurnId !== expected.sourceTurnId) {",
    'if (typeof raw.eligible !== "boolean") invalid();',
    'if (typeof raw.warning !== "string") invalid();',
    'if (typeof raw.boundary !== "string" || !BOUNDARIES.has(raw.boundary)) invalid();',
    "if (!isCount(raw.completedToolCalls)) invalid();",
    "Number.isSafeInteger(value) && value >= 0;",
    "const text = field.trim();",
    "result[key] = safeSlice(text, limit);",
)
CONVERSATION_MARK = (
    "<strong>此回合已中断</strong>",
    "续接会再次发起模型请求；若上次请求结果未能确认，可能重复调用并产生额外费用。",
    '检查点：{currentContinuationCheck.response.boundary === "user_input" ? "用户输入" : "已完成的工具批次"}',
    " · 已完成 ${currentContinuationCheck.response.completedToolCalls} 次工具调用",
    'currentContinuationCheck.response.reason ?? "当前检查点不满足续接条件。"',
    "（${currentContinuationCheck.response.reasonCode}）",
    '"正在提交续接…" : currentContinuationCheck.uncertain ? "等待核对续接结果" : "继续中断回合"',
    "disabled={Boolean(!harnessUp || currentContinuationCheck.submitting || currentContinuationCheck.uncertain || running || taskBlocked)}",
)
REFERENCE_MARK = (
    "## 中断回合续接",
    "`turn/continuation/read`（能力 `explicitTurnContinuation`）是只读预检",
    "最新回合」与「是否已有续接回合」按当前分支判定",
    "`continuationId` 的去重则按整份会话日志判定",
    "返回 `CONTINUATION_ID_CONFLICT`",
    "幂等回执（`deduplicated: true`）只说明编号已被使用",
    "继承的 `continuationBoundaryDigest` 因此按复制后的前缀重算",
    "普通回合启动前复位 runner 的历史提供者",
    "`fork_thread` 在 `_write_new` 之前按复制前缀重算继承边界",
    "rc.422 之前创建的分叉会话没有这层重算",
    "预检回执固定包含 `threadId`、`sourceTurnId`、`eligible` 与 `warning`",
    "### `check_turn_continuation.py`",
    "[`check_turn_continuation.py`](#check_turn_continuationpy)",
    "原因码集合由 `check_turn_continuation.py` 与技术参考的表格双向核对",
)
# 边界摘要单点计算：会话存储与分叉重算共用同一实现。
SESSION_MARK = (
    "def continuation_entries_digest(entries: list[dict]) -> str:",
    'encoded = json.dumps(entries, ensure_ascii=False, sort_keys=True,',
    "return hashlib.sha256(encoded).hexdigest()",
    "def _rehash_continuation_boundaries(copied: list[dict]) -> None:",
    'boundary_id = payload.get("continuationBoundaryEntryId")',
    'payload.pop("continuationBoundaryDigest", None)',
    'payload["continuationBoundaryDigest"] = continuation_entries_digest(copied[:index + 1])',
)
FORK_ORDERED = (
    "def fork_thread(",
    'copied_ids.add(entry["id"])',
    "_rehash_continuation_boundaries(copied)",
    "return self._write_new(header, copied)",
)
# 串行复用主 runner 时，续接钉住的历史边界不能留给下一个普通回合。
RESET_MARK = (
    "def _reset_runner_history(self, runner: TurnRunner) -> None:",
    "runner.history_provider = self.context.history\n",
    "self._reset_runner_history(runner)",
)
USER_MARK = (
    "- [继续中断回合](#继续中断回合)",
    "## 继续中断回合",
    "turn/continuation/read",
    "按当前分支的末回合判断",
    "explicitTurnContinuation",
    "CONTINUATION_ID_CONFLICT",
    "分叉会话遇到 `CONTINUATION_HISTORY_CHANGED` 时先核对来源",
    "[技术参考](TECHNICAL_REFERENCE.md#中断回合续接)",
    "不会自动重发",
)
# 旧分叉的摘要缺口必须留在「待完成」里，不能被当成已修复。
STATUS_MARK = (
    "旧分叉会话的续接摘要迁移：rc.422 之前创建的分叉没有重算继承的边界摘要",
)
DESKTOP_MARK = (
    "- **继续中断回合**：",
    "等待核对续接结果",
    "切回来源回合后可以再次续接",
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


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def check_turn_continuation() -> int:
    application = _read(APPLICATION)
    start = application.index("def _turn_continuation_plan(")
    end = application.index("def on_turn_continuation_read(")
    plan = application[start:end]
    reason_codes = set(REASON_CODE.findall(plan))
    if len(reason_codes) != EXPECTED_CODES:
        raise ValueError(f"{APPLICATION} 的续接原因码应为 {EXPECTED_CODES} 个，实际 {len(reason_codes)} 个")
    checked = 1
    checked += _ordered(PLAN_ORDERED, plan, APPLICATION)
    # 分支投影不能缺席：缺失时被放弃分支上的最新回合会再次被当成可续接。
    if plan.count("_active_entries(self.sessions.read_entries_snapshot(thread_id))") != 1:
        raise ValueError(f"{APPLICATION} 的续接预检必须按当前分支读取条目")
    if "entries = self.sessions.read_entries_snapshot(thread_id)\n" in plan:
        raise ValueError(f"{APPLICATION} 的续接预检不得直接读取整份日志")
    checked += 2
    start = application.index("def on_turn_continue(")
    end = application.find("\n    def ", start + 1)
    continuation = application[start:] if end < 0 else application[start:end]
    checked += _ordered(CONTINUE_ORDERED, continuation, APPLICATION)
    # 去重必须按整份日志：切回来源回合后，被放弃分支上的续接回合仍占着编号。
    if "_active_entries" in continuation:
        raise ValueError(f"{APPLICATION} 的 continuationId 去重不得改用分支投影")
    checked += 1
    checked += _expect(READ_MARK, application, APPLICATION)
    # 摘要口径单点计算：应用层只做委托，分叉在写出前按复制前缀重算。
    session = _read(SESSION)
    checked += _expect(SESSION_MARK, session, SESSION)
    start = session.index("def fork_thread(")
    end = session.find("\n    def ", start + 1)
    fork = session[start:] if end < 0 else session[start:end]
    checked += _ordered(FORK_ORDERED, fork, SESSION)
    if fork.count("_rehash_continuation_boundaries(copied)") != 1 or "json.dumps(" in fork:
        raise ValueError(f"{SESSION} 的分叉必须在写出前调用一次共用的边界重算")
    checked += 1
    if "def _continuation_entries_digest(entries: list[dict]) -> str:" not in application or \
            "return continuation_entries_digest(entries)" not in application:
        raise ValueError(f"{APPLICATION} 的续接摘要必须委托 session.continuation_entries_digest")
    start = application.index("def _continuation_entries_digest(")
    end = application.find("\n    def ", start + 1)
    delegation = application[start:] if end < 0 else application[start:end]
    if "hashlib" in delegation or "json.dumps(" in delegation:
        raise ValueError(f"{APPLICATION} 的续接摘要不得内联实现")
    checked += 2
    # 复位必须紧跟取用后的 runner，且只调用一次：续接的历史边界只属于该回合。
    checked += _expect(RESET_MARK, application, APPLICATION)
    start = application.index("def _on_turn_start(")
    end = application.find("\n    def ", start + 1)
    turn_start = application[start:] if end < 0 else application[start:end]
    checked += _ordered(
        ("runner = self._runner_for(config)", "self._reset_runner_history(runner)",
         "runner.max_model_requests = max_model_requests"),
        turn_start, APPLICATION)
    if turn_start.count("self._reset_runner_history(runner)") != 1:
        raise ValueError(f"{APPLICATION} 的普通回合启动必须复位一次 runner 历史")
    checked += 1
    reference = _read(REFERENCE)
    checked += _expect(REFERENCE_MARK, reference, REFERENCE)
    documented = set(TABLE_ROW.findall(_section(reference, "## 中断回合续接")))
    if documented != reason_codes:
        missing = sorted(reason_codes - documented)
        extra = sorted(documented - reason_codes)
        raise ValueError(
            f"{REFERENCE} 的续接原因码表与源码不一致：缺少 {missing or '无'}，多出 {extra or '无'}")
    checked += 1
    checked += _expect(USER_MARK, _read(USER_GUIDE), USER_GUIDE)
    checked += _expect(STATUS_MARK, _read(STATUS), STATUS)
    checked += _expect(DESKTOP_MARK, _read(DESKTOP_GUIDE), DESKTOP_GUIDE)
    app = _read(APP)
    checked += _expect(APP_MARK, app, APP)
    # 入口只看当前分支末回合是否为中断，不能用日志末回合的旧状态。
    if 'session.lastTurnStatus === "interrupted" ? session.turnId' not in app:
        raise ValueError(f"{APP} 的续接入口必须按当前分支的中断回合触发")
    checked += 1
    receipt = _read(RECEIPT)
    checked += _expect(RECEIPT_MARK, receipt, RECEIPT)
    # eligible 只接受显式布尔：真假值判断会把缺失字段当成可续接。
    if "if (raw.eligible)" in receipt or 'typeof raw.eligible !== "boolean"' not in receipt:
        raise ValueError(f"{RECEIPT} 的 eligible 只能按显式布尔校验")
    checked += 1
    checked += _expect(CONVERSATION_MARK, _read(CONVERSATION), CONVERSATION)
    if "python scripts/check_turn_continuation.py" not in _read(WORKFLOW):
        raise ValueError(f"{WORKFLOW} 缺少 check_turn_continuation.py 步骤")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_turn_continuation()
    except ValueError as error:
        print(f"续接预检核对失败，{error}", file=sys.stderr)
        return 2
    print(f"续接预检一致：{checked} 项分支判定、原因码表、分叉重算与桌面入口校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
