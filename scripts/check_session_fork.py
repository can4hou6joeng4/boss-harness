#!/usr/bin/env python3
"""核对会话分叉的复制边界、记录改写与源日志只读约束。

`fork_thread` 只复制当前分支的一个已结束回合前缀：排除 `thread_info` / `queue` /
`task_phase` 等内核专用记录，按 owner 归属迟到修订，拒绝拆开工具批次，并在副本里
改写 parentId、threadId、approvalId 与 continuationRequestOffset，最后按复制前缀
重算继承的续接边界摘要。漏掉任一改写会让分支会话与源会话共享歧义状态；复制过程
改写源日志则会静默污染来源会话。这里先按源码顺序固定这些不变量，再用临时目录与
合成 JSONL 构造真实 `SessionStore` 实际执行 `fork_thread`，覆盖分支选择、改写与
拒绝路径。
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.session import SessionStore, continuation_entries_digest  # noqa: E402

# 分支选择、前缀裁剪与拒绝条件。
SELECT_MARK = (
    "raw_entries = self.read_entries(thread_id)",
    "entries = self._active_entries(raw_entries)",
    'synthetic = Entry(type=LEAF_ENTRY_TYPE, parent_id=records[-1]["id"],',
    'or selected.get("status") not in _TERMINAL):',
    'raise ValueError("仅可从已经结束的回合创建分支")',
    'cutoff = selected.get("boundaryOrdinal", selected["lastOrdinal"])',
    "return position is not None and position <= selected_position",
    "prefix = [entry for entry in entries[:cutoff + 1]",
    "owners = self._item_owners(entries)",
    'owners.get(entry["id"]) in included_turns',
    'raise ValueError("回合中仍有未收尾条目或审批，不能创建分支")',
    'raise ValueError("分支边界会拆开工具批次")',
)
# 新会话头：派生字段不继承，来源标识另行写入。
HEADER_MARK = (
    'if key not in {"id", "sessionId", "createdAt", "updatedAt", "lastTurn",',
    'if source.get("projectIdTruncated"):',
    'header.pop("projectId", None)',
    'forkedFromId=thread_id, forkedFromTurnId=selected["turnId"]',
)
# 复制循环：排除内核专用记录并改写跨会话引用。
COPY_MARK = (
    'if entry["type"] in {"thread_info", "queue", "task_phase"}:',
    'entry["payload"]["continuationRequestOffset"] = request_offset',
    'and owners.get(_record_id(entry["payload"].get("targetItemId"))) not in included_turns):',
    'if entry.get("parentId") not in copied_ids:',
    'if entry["payload"].get("threadId") == thread_id:',
    "approval_ids[approval_id] = uuid.uuid4().hex",
)
COPY_ORDER = (
    "def fork_thread(",
    "for entry in json.loads(_json(prefix)):",
    'if entry.get("parentId") not in copied_ids:',
    'entry["payload"]["threadId"] = header["id"]',
    "approval_ids[approval_id] = uuid.uuid4().hex",
    "copied.append(entry)",
    "copied_ids.add(entry[\"id\"])",
    "_rehash_continuation_boundaries(copied)",
    "return self._write_new(header, copied)",
)

_THREAD = "abcdef012345"
_TIMESTAMP = "2026-01-01T00:00:00+00:00"


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


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


def check_session_fork() -> int:
    source = _read(SESSION)
    start = source.index("def fork_thread(")
    end = source.find("\n    def ", start + 1)
    fork = source[start:] if end < 0 else source[start:end]
    checked = _expect(SELECT_MARK, fork, SESSION)
    checked += _expect(HEADER_MARK, fork, SESSION)
    checked += _expect(COPY_MARK, fork, SESSION)
    checked += _ordered(COPY_ORDER, fork, SESSION)
    # 只复制当前分支：两条选择路径（当前分支与合成 leaf）都必须经过 _active_entries。
    if fork.count("_active_entries(") != 2:
        raise ValueError(f"{SESSION} 的分叉必须只按当前分支复制（两条选择路径各一次）")
    # 源日志只读：副本只能通过 _write_new 写成新会话，不得追加到来源会话。
    for forbidden in ("self.append(", "self.record_turn(", "self._append_line("):
        if forbidden in fork:
            raise ValueError(f"{SESSION} 的分叉不得改写源日志：{forbidden}")
    if "return self._write_new(header, copied)" not in fork:
        raise ValueError(f"{SESSION} 的分叉必须只写新会话")
    checked += 4
    return checked


def _record(kind: str, entry_id: str, parent: str | None, payload: dict,
            second: int = 0) -> dict:
    return {"type": kind, "id": entry_id, "parentId": parent,
            "timestamp": f"2026-01-01T00:00:{second:02d}+00:00", "payload": payload}


def _store(base: Path, name: str, entries: list[dict],
           header_extra: dict | None = None) -> tuple[SessionStore, Path]:
    root = base / name
    sessions = root / "sessions"
    sessions.mkdir(parents=True, mode=0o700)
    header = {"type": "session", "version": 2, "id": _THREAD, "sessionId": "sess-1",
              "title": "源会话", "createdAt": _TIMESTAMP, "archived": False}
    header.update(header_extra or {})
    path = sessions / f"{_THREAD}.jsonl"
    lines = [json.dumps(value, ensure_ascii=False) for value in [header, *entries]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return SessionStore(sessions), sessions


def _rows(sessions: Path, fork_id: str) -> list[dict]:
    text = (sessions / f"{fork_id}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def _fork_rows(store: SessionStore, sessions: Path, *, turn_id: str | None = None,
               title: str | None = None) -> tuple[dict, list[dict]]:
    fork = store.fork_thread(_THREAD, turn_id=turn_id, title=title)
    return fork, _rows(sessions, fork["id"])


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"会话分叉行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_absent(container: dict, keys: tuple[str, ...], label: str) -> int:
    present = [key for key in keys if key in container]
    if present:
        raise ValueError(f"会话分叉行为变化 {label}：不应继承 " + "、".join(present))
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"会话分叉行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"会话分叉行为变化 {label}：期望 ValueError，实际 {type(error).__name__}") from None
    raise ValueError(f"会话分叉行为变化 {label}：未抛出错误")


def _behavior_checks() -> int:
    checked = 0
    missing_turn = "仅可从已经结束的回合创建分支"
    pending = "回合中仍有未收尾条目或审批，不能创建分支"
    split_batch = "分支边界会拆开工具批次"
    bad_phase = "来源回合模型请求阶段无法核验，不能创建分支"
    bad_offset = "来源回合模型请求计数无法核验，不能创建分支"
    title_message = "title 必须是最多 500 字符的字符串"
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        # 混合日志：两个已结束回合、迟到修订、内核专用记录与共享审批。
        store, sessions = _store(base, "mixed", [
            _record("thread_info", "ti1", None, {"title": "新标题"}),
            _record("turn", "t1", "ti1", {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "completed", "threadId": _THREAD}, 2),
            _record("item", "i2", "i1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed",
                                         "approval": {"approvalId": "ap-1",
                                                      "decision": "approved",
                                                      "toolName": "boss_hr_greet"}}, 3),
            _record("turn", "t2", "i2", {"turnId": "turn-2", "status": "completed"}, 4),
            _record("item", "i3", "t2", {"kind": "message", "turnId": "turn-2",
                                         "status": "completed",
                                         "threadId": "other-session"}, 5),
            _record("item", "i4", "i3", {"kind": "toolCall", "turnId": "turn-2",
                                         "status": "completed", "revises": "i2",
                                         "approval": {"approvalId": "ap-1",
                                                      "decision": "approved",
                                                      "toolName": "boss_hr_greet"}}, 6),
            _record("queue", "q1", "i4", {"id": "queued-1", "kind": "prompt",
                                          "input": "继续", "status": "queued"}, 7),
            _record("task_phase", "p1", "q1", {"taskId": "turn-2", "ownerKind": "turn",
                                               "phase": "model_request", "attempt": 4,
                                               "restartLimit": 1, "status": "completed"}, 8),
            _record("leaf", "l1", "p1", {"targetId": "t2", "turnId": "turn-2"}, 9),
        ], {"projectId": "proj-1", "projectIdTruncated": True, "titleTruncated": True,
            "lastTurn": {"turnId": "陈旧"}, "queueActiveItems": 9,
            "queueCounts": {"queued": 9}, "archived": True})
        source_path = sessions / f"{_THREAD}.jsonl"
        source_bytes = source_path.read_bytes()
        source_mtime = source_path.stat().st_mtime_ns
        fork, rows = _fork_rows(store, sessions)
        header, body = rows[0], rows[1:]
        checked += _expect_value(header.get("title"), "新标题", "thread_info 标题继承")
        checked += _expect_value(header.get("forkedFromId"), _THREAD, "来源会话标识")
        checked += _expect_value(header.get("forkedFromTurnId"), "turn-2", "来源回合标识")
        fork_id = header.get("id")
        checked += _expect_value(
            isinstance(fork_id, str) and fork_id != _THREAD and len(fork_id) == 12
            and all(char in "0123456789abcdef" for char in fork_id), True, "副本编号")
        session_id = header.get("sessionId")
        checked += _expect_value(
            isinstance(session_id, str) and session_id != "sess-1" and len(session_id) == 32,
            True, "副本会话标识")
        checked += _expect_value((header.get("type"), header.get("version")),
                                 ("session", 2), "副本头格式")
        checked += _expect_value(header.get("archived"), False, "副本未归档")
        checked += _expect_absent(header, ("projectId",), "截断项目标识")
        checked += _expect_absent(header, ("lastTurn", "queueActiveItems", "queueCounts",
                                           "projectIdTruncated", "titleTruncated"), "派生字段")
        checked += _expect_value([row["id"] for row in body],
                                 ["t1", "i1", "i2", "t2", "i3", "i4"], "复制前缀")
        checked += _expect_value(sorted({row["type"] for row in body}), ["item", "turn"],
                                 "记录类型")
        checked += _expect_value(body[1]["payload"].get("threadId"), fork_id, "线程标识改写")
        checked += _expect_value(body[4]["payload"].get("threadId"), "other-session",
                                 "外部线程标识保留")
        approval_id = body[2]["payload"]["approval"]["approvalId"]
        checked += _expect_value(approval_id,
                                 body[5]["payload"]["approval"]["approvalId"], "共享审批改写一致")
        checked += _expect_value(approval_id != "ap-1" and len(approval_id) == 32, True,
                                 "审批编号重新生成")
        checked += _expect_value(body[5]["payload"].get("revises"), "i2", "修订目标保留")
        checked += _expect_value(body[3]["payload"].get("continuationRequestOffset"), 4,
                                 "请求计数提升")
        checked += _expect_value(body[0]["payload"].get("continuationRequestOffset"), None,
                                 "未选中回合不改写")
        checked += _expect_value(source_path.read_bytes(), source_bytes, "源日志只读")
        checked += _expect_value(source_path.stat().st_mtime_ns, source_mtime, "源日志时间不变")
        text = (sessions / f"{fork_id}.jsonl").read_text(encoding="utf-8")
        checked += _expect_value(len(rows), 7, "副本记录数")
        checked += _expect_value(text.endswith("\n"), True, "副本以换行结尾")

        # 选择较早回合：其后运行中的回合不进入前缀。
        store, sessions = _store(base, "older", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "completed"}, 2),
            _record("turn", "t2", "i1", {"turnId": "turn-2", "status": "running"}, 3),
            _record("item", "i2", "t2", {"kind": "message", "turnId": "turn-2",
                                         "status": "running"}, 4),
        ])
        fork, rows = _fork_rows(store, sessions, turn_id="turn-1")
        checked += _expect_value([row["id"] for row in rows[1:]], ["t1", "i1"], "较早回合前缀")
        checked += _expect_value(rows[0].get("forkedFromTurnId"), "turn-1", "较早回合来源")
        checked += _expect_error(lambda: store.fork_thread(_THREAD), missing_turn,
                                 "运行中回合")
        checked += _expect_error(lambda: store.fork_thread(_THREAD, turn_id="bad id"),
                                 "turnId 格式无效", "非法回合编号")
        checked += _expect_error(lambda: store.fork_thread(_THREAD, turn_id="turn-9"),
                                 missing_turn, "不存在回合")

        # 未收尾条目、未决审批与非对象审批。
        store, sessions = _store(base, "running-item", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "running"}, 2),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD), pending, "运行中条目")
        store, sessions = _store(base, "pending-approval", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed",
                                         "approval": {"approvalId": "ap-1",
                                                      "toolName": "boss_hr_greet"}}, 2),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD), pending, "未决审批")
        store, sessions = _store(base, "broken-approval", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed", "approval": "损坏"}, 2),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value(rows[2]["payload"].get("approval"), "损坏", "非对象审批保留")
        checked += _expect_error(lambda: store.fork_thread("ffffffffffff"), "会话不存在",
                                 "缺失会话")

        # 合成叶：当前叶指向其他分支时，仍可分叉被放弃的已结束回合。
        store, sessions = _store(base, "branches", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "completed"}, 2),
            _record("turn", "t2", "i1", {"turnId": "turn-2", "status": "completed"}, 3),
            _record("item", "i2", "t2", {"kind": "message", "turnId": "turn-2",
                                         "status": "completed"}, 4),
            _record("leaf", "l1", "i2", {"targetId": "t1", "turnId": "turn-1"}, 5),
            _record("turn", "t3", "l1", {"turnId": "turn-3", "status": "completed"}, 6),
            _record("item", "i3", "t3", {"kind": "message", "turnId": "turn-3",
                                         "status": "completed"}, 7),
        ])
        fork, rows = _fork_rows(store, sessions, turn_id="turn-2")
        checked += _expect_value([row["id"] for row in rows[1:]],
                                 ["t1", "i1", "t2", "i2"], "合成叶分支前缀")
        checked += _expect_value(rows[0].get("forkedFromTurnId"), "turn-2", "合成叶来源回合")
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value([row["id"] for row in rows[1:]],
                                 ["t1", "i1", "t3", "i3"], "活动分支前缀")
        checked += _expect_value(rows[0].get("forkedFromTurnId"), "turn-3", "活动分支来源回合")
        checked += _expect_value([row["type"] for row in rows[1:] if row["type"] == "leaf"],
                                 [], "叶记录不复制")

        # 工具批次不得被分支边界拆开。
        store, sessions = _store(base, "split-batch", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed", "toolBatchId": "batch-1"}, 2),
            _record("turn", "t2", "i1", {"turnId": "turn-2", "status": "completed"}, 3),
            _record("item", "i2", "t2", {"kind": "toolCall", "turnId": "turn-2",
                                         "status": "completed", "toolBatchId": "batch-1"}, 4),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD, turn_id="turn-1"),
                                 split_batch, "拆开工具批次")
        store, sessions = _store(base, "whole-batch", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed", "toolBatchId": "batch-1"}, 2),
            _record("item", "i2", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed", "toolBatchId": "batch-1"}, 3),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value([row["id"] for row in rows[1:]], ["t1", "i1", "i2"],
                                 "完整批次可复制")

        # 续接请求计数：模型请求阶段提升，非法记录与负数拒绝。
        store, sessions = _store(base, "offset", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed",
                                         "continuationRequestOffset": 3}, 1),
            _record("task_phase", "p1", "t1", {"taskId": "turn-1", "ownerKind": "turn",
                                               "phase": "model_request", "attempt": 7,
                                               "restartLimit": 2, "status": "completed"}, 2),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value(rows[1]["payload"].get("continuationRequestOffset"), 7,
                                 "请求计数提升覆盖")
        store, sessions = _store(base, "phase-owner", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("task_phase", "p1", "t1", {"taskId": "turn-1", "ownerKind": "queue",
                                               "phase": "model_request", "attempt": 1,
                                               "restartLimit": 0, "status": "completed"}, 2),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD), bad_phase,
                                 "非回合阶段记录")
        store, sessions = _store(base, "phase-attempt", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("task_phase", "p1", "t1", {"taskId": "turn-1", "ownerKind": "turn",
                                               "phase": "model_request", "attempt": True,
                                               "restartLimit": 0, "status": "completed"}, 2),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD), bad_phase,
                                 "布尔尝试次数")
        store, sessions = _store(base, "negative-offset", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed",
                                         "continuationRequestOffset": -1}, 1),
        ])
        checked += _expect_error(lambda: store.fork_thread(_THREAD), bad_offset,
                                 "负数请求计数")

        # 续接边界摘要按复制前缀重算；边界条目未复制时删除摘要。
        store, sessions = _store(base, "boundary", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed",
                                         "continuationBoundaryEntryId": "i1"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "completed"}, 2),
        ])
        fork, rows = _fork_rows(store, sessions)
        digest = rows[1]["payload"].get("continuationBoundaryDigest")
        stripped = {**rows[1],
                    "payload": {key: value for key, value in rows[1]["payload"].items()
                                if key != "continuationBoundaryDigest"}}
        checked += _expect_value(digest, continuation_entries_digest([stripped, rows[2]]),
                                 "边界摘要重算")
        store, sessions = _store(base, "dropped-boundary", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed",
                                         "continuationBoundaryEntryId": "q1",
                                         "continuationBoundaryDigest": "陈旧摘要"}, 1),
            _record("queue", "q1", "t1", {"id": "queued-1", "kind": "prompt",
                                          "input": "继续", "status": "queued"}, 2),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_absent(rows[1]["payload"], ("continuationBoundaryDigest",),
                                  "未复制边界摘要")

        # 标题：显式标题、空标题与非法标题。
        store, sessions = _store(base, "titles", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}),
        ])
        fork, rows = _fork_rows(store, sessions, title="分叉标题")
        checked += _expect_value(rows[0].get("title"), "分叉标题", "指定标题")
        fork, rows = _fork_rows(store, sessions, title="")
        checked += _expect_value(rows[0].get("title"), "", "空标题")
        checked += _expect_error(lambda: store.fork_thread(_THREAD, title="长" * 501),
                                 title_message, "超长标题")
        checked += _expect_error(lambda: store.fork_thread(_THREAD, title=123),
                                 title_message, "非字符串标题")

        # 未截断的项目标识继承，归档标记不继承。
        store, sessions = _store(base, "inherit", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}),
        ], {"projectId": "proj-9", "archived": True})
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value(rows[0].get("projectId"), "proj-9", "项目标识继承")
        checked += _expect_value(rows[0].get("archived"), False, "归档标记不继承")

        # 父引用修复：被排除的首条父记录与迟到修订。
        store, sessions = _store(base, "parents", [
            _record("thread_info", "ti1", None, {"title": "父引用"}, 1),
            _record("turn", "t1", "ti1", {"turnId": "turn-1", "status": "completed"}, 2),
            _record("leaf", "l1", "t1", {"targetId": "t1", "turnId": "turn-1"}, 3),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value(rows[1].get("parentId"), None, "首条父引用修复")
        checked += _expect_value([row["id"] for row in rows[1:]], ["t1"], "叶记录排除")
        store, sessions = _store(base, "late-revision", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "message", "turnId": "turn-1",
                                         "status": "completed"}, 2),
            _record("turn", "t2", "i1", {"turnId": "turn-2", "status": "completed"}, 3),
            _record("item", "i2", "t2", {"kind": "message", "turnId": "turn-2",
                                         "status": "completed"}, 4),
            _record("task_phase", "p1", "i2", {"taskId": "turn-2", "ownerKind": "turn",
                                               "phase": "finish", "attempt": 1,
                                               "restartLimit": 0, "status": "completed"}, 5),
            _record("item", "i5", "p1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed", "revises": "i1"}, 6),
        ])
        fork, rows = _fork_rows(store, sessions)
        checked += _expect_value([row["id"] for row in rows[1:]],
                                 ["t1", "i1", "t2", "i2", "i5"], "迟到修订前缀")
        checked += _expect_value(rows[-1].get("parentId"), "i2", "迟到修订父引用修复")
        checked += _expect_value(rows[-1]["payload"].get("revises"), "i1", "迟到修订保留目标")

        # 不同审批改写为互不相同的新编号，不再复用来源值。
        store, sessions = _store(base, "approvals", [
            _record("turn", "t1", None, {"turnId": "turn-1", "status": "completed"}, 1),
            _record("item", "i1", "t1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed",
                                         "approval": {"approvalId": "ap-1",
                                                      "decision": "approved"}}, 2),
            _record("item", "i2", "i1", {"kind": "toolCall", "turnId": "turn-1",
                                         "status": "completed",
                                         "approval": {"approvalId": "ap-2",
                                                      "decision": "approved"}}, 3),
        ])
        fork, rows = _fork_rows(store, sessions)
        approval_ids = [row["payload"]["approval"]["approvalId"] for row in rows[1:]
                        if row["payload"].get("approval")]
        checked += _expect_value(len(set(approval_ids)), 2, "不同审批改写为不同编号")
        checked += _expect_value(
            all(item not in {"ap-1", "ap-2"} for item in approval_ids), True,
            "审批编号不再复用来源值")
    return checked


def main() -> int:
    try:
        checked = check_session_fork()
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"会话分叉核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话分叉一致：{checked} 项分支复制、记录改写与源日志只读校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
