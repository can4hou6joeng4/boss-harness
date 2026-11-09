"""Per-thread runtime ownership and durable steering/follow-up delivery.

The application owns consent and queues; a runner owns one turn. Restart never
replays an in-flight submission or an external effect with an unknown outcome.
"""
from __future__ import annotations

import threading
import time
import uuid
import re
from typing import Any, Callable

from boss_harness.queue_view import project_queue, queue_record
from boss_harness.rpc import RpcError
from boss_harness.request_identity import RequestIdentity, resolve_request, valid_client_id
from boss_harness.session import Entry, SessionStore
from boss_harness.shutdown import TrackedAbort, join_until

MAX_PENDING_QUEUE_ITEMS = 128
MAX_PENDING_QUEUE_INPUT_BYTES = 4 * 1024 * 1024
# 暂停来源只作为可核对的有限枚举写入队列记录；界面据此提供重试入口，不猜原因。
PAUSE_REASON_COMPACTION_FAILED = "COMPACTION_FAILED"
# 归档会暂停全部待处理项（_idle 保证没有运行中的回合或投递），恢复后可安全重新排队。
PAUSE_REASON_THREAD_ARCHIVED = "THREAD_ARCHIVED"
# 回合未完成时剩余项从未被领取，输入不会写入会话；界面可据来源提供重新排队入口。
PAUSE_REASON_TURN_NOT_COMPLETED = "TURN_NOT_COMPLETED"


class RuntimeManager:
    def __init__(self, *, capacity: int = 8) -> None:
        self.lock = threading.RLock()
        self.active: dict[str, dict[str, Any]] = {}
        # Keep model ownership through completion notifications and cleanup.
        # The application tracks follow-up storage tails separately.
        self.jobs: dict[str, dict[str, Any]] = {}
        self.capacity = capacity
        self.closed = False
        self.on_idle = None
        self._capacity_wake = threading.Event()
        self._capacity_callback: Callable[[], None] | None = None
        self._capacity_worker: threading.Thread | None = None
        self._capacity_worker_done = threading.Event()
        self._capacity_worker_done.set()

    def start_capacity_notifications(self, callback: Callable[[], None]) -> None:
        """Start one tracked wake worker before accepting application work."""
        with self.lock:
            if self.closed or self._capacity_worker is not None:
                raise RuntimeError("容量通知 worker 已启动或内核已关闭")
            self._capacity_callback = callback
            worker = threading.Thread(target=self._run_capacity_notifications,
                                      name="turn-capacity-wake", daemon=True)
            self._capacity_worker_done.clear()
            self._capacity_worker = worker
            try:
                worker.start()
            except Exception:
                if worker.ident is None:
                    self._capacity_worker = None
                    self._capacity_worker_done.set()
                    raise

    @property
    def capacity_notifications_stopped(self) -> bool:
        return self._capacity_worker_done.is_set()

    def _run_capacity_notifications(self) -> None:
        try:
            while True:
                self._capacity_wake.wait()
                self._capacity_wake.clear()
                with self.lock:
                    if self.closed:
                        return
                    callback = self._capacity_callback
                try:
                    if callback is not None:
                        callback()
                except Exception:
                    # Durable queue state remains authoritative after a failed
                    # wake; later ownership changes or explicit input may retry.
                    pass
        finally:
            self._capacity_worker_done.set()
            self._notify_idle()

    @property
    def owner_capacity(self) -> int:
        # Permit one batch of cleanup tails to overlap the active batch.
        return 2 * self.capacity

    def has_capacity(self) -> bool:
        with self.lock:
            return (not self.closed and len(self.active) < self.capacity
                    and len(self.jobs) < self.owner_capacity)

    def check_admission(self, thread_id: str) -> None:
        """Preflight resource bounds; reserve repeats this under the same lock."""
        with self.lock:
            if self.closed:
                raise RpcError(-32003, "内核正在关闭")
            if thread_id in self.active:
                raise RpcError(-32004, "该会话已有回合运行", {"turnId": self.active[thread_id]["turnId"]})
            if len(self.active) >= self.capacity:
                raise RpcError(-32005, "已达到并发会话上限",
                               {"code": "TURN_CONCURRENCY_LIMIT", "limit": self.capacity})
            if len(self.jobs) >= self.owner_capacity:
                raise RpcError(-32005, "仍在执行或收尾的回合已达到内核资源上限",
                               {"code": "TURN_OWNER_LIMIT", "limit": self.owner_capacity})

    def reserve(self, thread_id: str, text: str, runner: Any) -> dict:
        with self.lock:
            self.check_admission(thread_id)
            job = {"threadId": thread_id, "turnId": uuid.uuid4().hex, "input": text,
                   "cancel": threading.Event(), "runner": runner, "worker": None,
                   "_startedMonotonic": time.monotonic()}
            self.active[thread_id] = job
            self.jobs[job["turnId"]] = job
            return job

    def release(self, job: dict) -> None:
        with self.lock:
            if self.active.get(job["threadId"]) is job:
                self.active.pop(job["threadId"])

    def finish(self, job: dict) -> None:
        with self.lock:
            job["_worker_done"] = True
            self._retire_locked(job)
        self._notify_idle()

    def _retire_locked(self, job: dict) -> bool:
        abort = job.get("_shutdown_abort")
        if job.get("_worker_done") and (abort is None or abort.done.is_set()):
            if self.jobs.get(job["turnId"]) is job:
                self.jobs.pop(job["turnId"], None)
                return True
        return False

    def _notify_idle(self) -> None:
        if self.on_idle is not None:
            self.on_idle()

    def _abort_done(self, job: dict) -> None:
        with self.lock:
            retired = self._retire_locked(job)
        # Abort start failure can call this inline in the cancelling thread.
        # Signal the prestarted worker; never dispatch unrelated work here.
        if retired:
            self._capacity_wake.set()
        self._notify_idle()

    def _claim_abort_locked(self, job: dict, *, interrupt: bool) -> TrackedAbort:
        if "_shutdown_abort" not in job:
            # Manual cancellation and shutdown share one claim. The application
            # captures summary providers separately, rather than consulting a
            # runner's mutable context_abort when this hook eventually runs.
            job["_shutdown_abort"] = TrackedAbort(job["runner"].provider,
                lambda job=job: self._abort_done(job), name="turn-abort",
                callback=job["runner"].interrupt if interrupt else None)
        return job["_shutdown_abort"]

    def prepare_interrupt(self, thread_id: str, expected_turn_id: str | None = None,
                          *, interrupt: bool = True) -> dict | None:
        """Cancel and claim ownership; dispatch only after all owner locks exit."""
        with self.lock:
            job = self.active.get(thread_id)
            if job is None:
                return None
            if expected_turn_id and expected_turn_id != job["turnId"]:
                raise RpcError(-32004, "回合已变化；请刷新后再中断")
            job["cancel"].set()
            self._claim_abort_locked(job, interrupt=interrupt)
            return job

    def interrupt(self, thread_id: str, expected_turn_id: str | None = None) -> bool:
        job = self.prepare_interrupt(thread_id, expected_turn_id)
        if job is None:
            return False
        job["_shutdown_abort"].start()
        return True

    def cancel_all(self, *, interrupt: bool = True) -> None:
        with self.lock:
            self.closed = True
            self._capacity_wake.set()
            for job in self.jobs.values():
                job["cancel"].set()
                self._claim_abort_locked(job, interrupt=interrupt)

    def request_stop_aborts(self) -> None:
        with self.lock:
            aborts = [job["_shutdown_abort"] for job in self.jobs.values() if "_shutdown_abort" in job]
        for abort in aborts:
            abort.start()

    def wait_for_stop(self, deadline: float) -> None:
        with self.lock:
            workers = [job.get("worker") for job in self.jobs.values()]
            workers.append(self._capacity_worker)
            workers.extend(job["_shutdown_abort"].worker for job in self.jobs.values()
                           if "_shutdown_abort" in job)
        join_until(workers, deadline)

    def stop(self, *, deadline: float | None = None) -> None:
        deadline = time.monotonic() + 2 if deadline is None else deadline
        self.cancel_all(interrupt=True)
        self.request_stop_aborts()
        self.wait_for_stop(deadline)


class TurnQueue:
    def __init__(self, sessions: SessionStore) -> None:
        self.sessions = sessions
        self.lock = threading.RLock()
        # kind -> 暂停来源；None 表示调用方没有说明来源（启动失败、恢复等既有路径）。
        self._pending_pauses: dict[str, dict[str | None, str | None]] = {}

    def list(self, thread_id: str) -> list[dict]:
        states: dict[str, dict] = {}
        for entry in self.sessions.read_entries(thread_id):
            if entry.get("type") != "queue":
                continue
            # 持久记录不可信：缺 id、未知状态或 input 不是字符串的条目无法定位、转移或展示，
            # 不能让一条坏记录在投影之前就打断整个队列读取。
            record = queue_record(entry.get("payload"))
            if record is None:
                continue
            states[record["id"]] = dict(record)
        return list(states.values())

    def view(self, thread_id: str) -> dict:
        """Bounded read projection; full input stays available through get()."""
        with self.lock:
            return project_queue(self.list(thread_id))

    def _save(self, thread_id: str, item: dict) -> dict:
        self.sessions.append(thread_id, Entry(type="queue", payload=item))
        return dict(item)

    @staticmethod
    def _pending_usage(items: list[dict]) -> tuple[int, int]:
        pending = [item for item in items if item.get("status") in {"queued", "delivering"}]
        total_bytes = sum(len(item["input"].encode("utf-8")) for item in pending)
        return len(pending), total_bytes

    def get(self, thread_id: str, queue_id: str) -> dict:
        with self.lock:
            item = next((q for q in self.list(thread_id) if q["id"] == queue_id), None)
            if item is None:
                raise ValueError("队列项不存在")
            return item

    def _fail_start(self, thread_id: str, queue_id: str, *, turn_id: str | None = None,
                    input_persisted: bool | None = None) -> dict:
        """Settle a proven unstarted delivery; callers hold runtime ownership.

        delivered means the input was persisted, not that its worker started.
        This restricted failure path never makes delivered generally resumable.
        """
        with self.lock:
            self.settle_pauses(thread_id)
            item = self.get(thread_id, queue_id)
            if item["status"] not in {"delivering", "paused"} and not (
                    item["status"] == "delivered" and turn_id is not None):
                return item
            failed = {**item, "status": "paused", "failureCode": "TURN_START_FAILED",
                      "executionStarted": False}
            if turn_id is not None:
                failed["turnId"] = turn_id
            if input_persisted is not None:
                failed["inputPersisted"] = input_persisted
            return item if failed == item else self._save(thread_id, failed)

    def defer_capacity(self, thread_id: str, queue_id: str) -> dict:
        """Return an unstarted follow-up to the durable queue after capacity backpressure."""
        with self.lock:
            self.settle_pauses(thread_id)
            item = self.get(thread_id, queue_id)
            if item["status"] != "delivering":
                return item
            deferred = {key: value for key, value in item.items()
                        if key not in {"turnId", "failureCode", "executionStarted", "inputPersisted"}}
            deferred["status"] = "queued"
            return self._save(thread_id, deferred)

    def _associate_request(self, thread_id: str, queue_id: str, identity: RequestIdentity) -> dict:
        """Append a receipt for an existing turn without resuming its request."""
        with self.lock:
            self.settle_pauses(thread_id)
            item = self.get(thread_id, queue_id)
            fields = identity.receipt()
            if item["status"] not in {"queued", "delivering"}:
                fields["status"] = item["status"]
            associated = {key: value for key, value in item.items()
                          if key not in {"failureCode", "executionStarted", "inputPersisted"}}
            associated.update(fields)
            return item if associated == item else self._save(thread_id, associated)

    def add(self, thread_id: str, text: str, *, kind: str = "followUp", turn_id: str | None = None,
            client_id: str | None = None, skill_ids: list[str] | None = None,
            auto_compaction: dict | None = None) -> dict:
        if kind not in {"steering", "followUp"}:
            raise ValueError("kind 必须是 steering 或 followUp")
        if not isinstance(text, str) or not text.strip() or len(text) > 100_000:
            raise ValueError("队列 input 必须是 1 到 100000 字符")
        if client_id is not None and (not isinstance(client_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", client_id)):
            raise ValueError("clientUserMessageId 格式无效")
        if skill_ids is None:
            skill_ids = []
        if not isinstance(skill_ids, list) or len(skill_ids) > 10 or not all(
                isinstance(item, str) and item for item in skill_ids):
            raise ValueError("skillIds 必须是最多 10 项的非空字符串数组")
        skill_ids = list(dict.fromkeys(skill_ids))
        if kind == "steering" and skill_ids:
            raise ValueError("转向消息不支持技能")
        with self.lock:
            self.settle_pauses(thread_id)
            items = self.list(thread_id)
            for item in items:
                if client_id and item.get("clientUserMessageId") == client_id:
                    if item["input"] != text or item["kind"] != kind or (item.get("skillIds") or []) != skill_ids:
                        raise ValueError("clientUserMessageId 已用于不同输入或技能组合")
                    # 未显式重发覆盖时沿用既有队列项；显式值不同则拒绝静默改写。
                    if auto_compaction is not None and item.get("autoCompaction") != auto_compaction:
                        raise ValueError("clientUserMessageId 已用于不同自动压缩覆盖")
                    return item
            pending_items, pending_bytes = self._pending_usage(items)
            input_bytes = len(text.encode("utf-8"))
            if (pending_items >= MAX_PENDING_QUEUE_ITEMS
                    or pending_bytes + input_bytes > MAX_PENDING_QUEUE_INPUT_BYTES):
                raise RpcError(-32005, "会话待处理队列已达到内核资源上限",
                               {"code": "QUEUE_LIMIT", "maxItems": MAX_PENDING_QUEUE_ITEMS,
                                "maxInputBytes": MAX_PENDING_QUEUE_INPUT_BYTES})
            return self._save(thread_id, {"id": uuid.uuid4().hex, "kind": kind,
                "input": text, "status": "queued", "expectedTurnId": turn_id,
                "clientUserMessageId": client_id, "skillIds": skill_ids,
                **({"autoCompaction": auto_compaction} if auto_compaction is not None else {})})

    def update_input(self, thread_id: str, queue_id: str, text: str) -> dict:
        """Replace the text of an unclaimed queue item without touching its identity."""
        if not isinstance(text, str) or not text.strip() or len(text) > 100_000:
            raise ValueError("队列 input 必须是 1 到 100000 字符")
        with self.lock:
            self.settle_pauses(thread_id)
            items = self.list(thread_id)
            item = next((q for q in items if q["id"] == queue_id), None)
            if item is None:
                raise ValueError("队列项不存在")
            if item.get("status") != "queued":
                raise ValueError("只有排队中的消息可以编辑")
            _, pending_bytes = self._pending_usage(items)
            pending_bytes += len(text.encode("utf-8")) - len(item["input"].encode("utf-8"))
            if pending_bytes > MAX_PENDING_QUEUE_INPUT_BYTES:
                raise RpcError(-32005, "会话待处理队列已达到内核资源上限",
                               {"code": "QUEUE_LIMIT", "maxItems": MAX_PENDING_QUEUE_ITEMS,
                                "maxInputBytes": MAX_PENDING_QUEUE_INPUT_BYTES})
            if item["input"] == text:
                return item
            return self._save(thread_id, {**item, "input": text})

    def transition(self, thread_id: str, queue_id: str, status: str) -> dict:
        with self.lock:
            self.settle_pauses(thread_id)
            item = next((q for q in self.list(thread_id) if q["id"] == queue_id), None)
            if item is None:
                raise ValueError("队列项不存在")
            allowed = {"queued": {"delivering", "delivered", "paused", "cancelled"},
                       "delivering": {"delivered", "paused"}, "paused": {"cancelled"}}
            if status not in allowed.get(item["status"], set()):
                raise ValueError("队列项已投递或状态不允许此操作")
            return self._save(thread_id, {**item, "status": status})

    def claim(self, thread_id: str, kind: str, turn_id: str | None = None) -> dict | None:
        with self.lock:
            self.settle_pauses(thread_id)
            item = next((q for q in self.list(thread_id) if q["kind"] == kind and q["status"] == "queued"
                         and (kind != "steering" or q["expectedTurnId"] == turn_id)), None)
            return self.transition(thread_id, item["id"], "delivering") if item else None

    def pause(self, thread_id: str, *, kind: str | None = None,
              reason: str | None = None) -> list[str]:
        """Pause matching pending work, remembering why it was paused.

        ``reason`` is written into each paused record so the desktop can explain
        the state and offer an explicit retry. It is a bounded enum owned by the
        kernel; callers that pause for internal recovery keep ``None``.
        """
        with self.lock:
            # Register responsibility before touching storage. A failed write
            # must not leave old work eligible for a later successful turn.
            scopes = self._pending_pauses.setdefault(thread_id, {})
            # 同一作用域已有具体来源时保留它；后到的无来源暂停不能抹掉前一次原因。
            if reason is not None or kind not in scopes:
                scopes[kind] = reason
            return self.settle_pauses(thread_id)

    def settle_pauses(self, thread_id: str, *, maximum_session_bytes: int | None = None) -> list[str]:
        """Finish earlier pauses before accepting or claiming more work.

        Reads remain read-only. New work can only be added after these scopes
        settle, so a delayed retry cannot accidentally pause a new request.
        Returns the queue ids actually paused by this settlement.
        """
        with self.lock:
            scopes = self._pending_pauses.get(thread_id)
            if not scopes:
                return []
            updates = []
            for item in self.list(thread_id):
                if item["status"] not in {"queued", "delivering"}:
                    continue
                # 具体 kind 的来源优先于无作用域兜底：两者同时登记时，
                # 压缩失败的 follow-up 仍应保留自己的原因。
                if item["kind"] in scopes:
                    reason = scopes[item["kind"]]
                elif None in scopes:
                    reason = scopes[None]
                else:
                    continue
                payload = {**item, "status": "paused"}
                if reason is not None:
                    payload["pausedReason"] = reason
                updates.append(Entry(type="queue", payload=payload))
            self.sessions.append_many(thread_id, updates, maximum_bytes=maximum_session_bytes)
            self._pending_pauses.pop(thread_id, None)
            return [entry.payload["id"] for entry in updates]

    def recover(self) -> None:
        for thread in self.sessions.list_threads(include_archived=True):
            thread_id = thread["id"]
            with self.lock:
                try:
                    delivered = {item.get("queueId") for item in self.sessions.read_items(thread_id)
                                 if item.get("kind") == "userMessage"}
                    items = self.list(thread_id)
                except (OSError, ValueError):
                    # A damaged log cannot say which inputs were delivered; leave
                    # that thread untouched and keep recovering the other sessions.
                    continue
                for item in items:
                    if item["status"] in {"queued", "delivering"}:
                        if item["kind"] == "steering":
                            self.transition(thread_id, item["id"],
                                            "delivered" if item["id"] in delivered else "paused")
                            continue
                        try:
                            identity = resolve_request(self.sessions, thread_id,
                                valid_client_id(item.get("clientUserMessageId")), item["input"],
                                queue_id=item["id"])
                        except (RpcError, ValueError):
                            # Inconsistent history is paused, never replayed or
                            # described as a proven failure before execution.
                            # A damaged persisted client ID is treated as absent;
                            # ValueError stays a pause, never a startup crash.
                            self.transition(thread_id, item["id"], "paused")
                            continue
                        if identity.turn is not None:
                            self._associate_request(thread_id, item["id"], identity)
                        else:
                            self.transition(thread_id, item["id"], "paused")
