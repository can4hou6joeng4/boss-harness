#!/usr/bin/env python3
"""核对运行时容量准入、回合归属与关闭中断口径。

`RuntimeManager` 用两个上限保护内核：同时运行的会话数不超过 `capacity`，
仍在执行或收尾的回合数不超过 `2 * capacity`；`reserve` 在同一把锁内重复
准入检查并同时登记 `active` 与 `jobs`，`release` / `_retire_locked` 用对象
身份比较，避免旧回合释放新回合的槽位。中断与关闭共享一次 abort 认领，派发
在锁外完成；容量通知 worker 在关闭后不再回调。这里按源码顺序固定这些边界，
避免并发上限、槽位回收与关闭流程被重构悄悄放宽。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "harness/src/boss_harness/runtime.py"

# 类内顺序：初始状态 → 容量通知 worker → 双上限 → 准入 → 预留 / 释放 / 回收 →
# 空闲通知 → abort 认领 → 中断 → 关闭与停止。
CLASS_ORDER = (
    "class RuntimeManager:",
    "def __init__(self, *, capacity: int = 8) -> None:",
    "self.capacity = capacity",
    "self.closed = False",
    "self._capacity_worker_done = threading.Event()",
    "self._capacity_worker_done.set()",
    "def start_capacity_notifications(self, callback: Callable[[], None]) -> None:",
    "if self.closed or self._capacity_worker is not None:",
    'raise RuntimeError("容量通知 worker 已启动或内核已关闭")',
    "worker = threading.Thread(target=self._run_capacity_notifications,",
    'name="turn-capacity-wake", daemon=True)',
    "self._capacity_worker_done.clear()",
    "worker.start()",
    "if worker.ident is None:",
    "self._capacity_worker = None",
    "self._capacity_worker_done.set()",
    "def _run_capacity_notifications(self) -> None:",
    "self._capacity_wake.wait()",
    "self._capacity_wake.clear()",
    "if self.closed:",
    "return",
    "except Exception:",
    "self._capacity_worker_done.set()",
    "def owner_capacity(self) -> int:",
    "return 2 * self.capacity",
    "def has_capacity(self) -> bool:",
    "return (not self.closed and len(self.active) < self.capacity",
    "and len(self.jobs) < self.owner_capacity)",
    "def check_admission(self, thread_id: str) -> None:",
    'raise RpcError(-32003, "内核正在关闭")',
    "if thread_id in self.active:",
    'raise RpcError(-32004, "该会话已有回合运行", {"turnId": self.active[thread_id]["turnId"]})',
    "if len(self.active) >= self.capacity:",
    '"code": "TURN_CONCURRENCY_LIMIT", "limit": self.capacity}',
    "if len(self.jobs) >= self.owner_capacity:",
    '"code": "TURN_OWNER_LIMIT", "limit": self.owner_capacity}',
    "def reserve(self, thread_id: str, text: str, runner: Any) -> dict:",
    "self.check_admission(thread_id)",
    'job = {"threadId": thread_id, "turnId": uuid.uuid4().hex, "input": text,',
    '"cancel": threading.Event(), "runner": runner, "worker": None,',
    '"_startedMonotonic": time.monotonic()}',
    "self.active[thread_id] = job",
    'self.jobs[job["turnId"]] = job',
    "def release(self, job: dict) -> None:",
    'if self.active.get(job["threadId"]) is job:',
    'self.active.pop(job["threadId"])',
    "def finish(self, job: dict) -> None:",
    'job["_worker_done"] = True',
    "def _retire_locked(self, job: dict) -> bool:",
    'abort = job.get("_shutdown_abort")',
    'if job.get("_worker_done") and (abort is None or abort.done.is_set()):',
    'if self.jobs.get(job["turnId"]) is job:',
    'self.jobs.pop(job["turnId"], None)',
    "def _notify_idle(self) -> None:",
    "if self.on_idle is not None:",
    "self.on_idle()",
    "def _abort_done(self, job: dict) -> None:",
    "retired = self._retire_locked(job)",
    "if retired:",
    "self._capacity_wake.set()",
    "def _claim_abort_locked(self, job: dict, *, interrupt: bool) -> TrackedAbort:",
    'if "_shutdown_abort" not in job:',
    'job["_shutdown_abort"] = TrackedAbort(job["runner"].provider,',
    "lambda job=job: self._abort_done(job), name=\"turn-abort\",",
    'callback=job["runner"].interrupt if interrupt else None)',
    'return job["_shutdown_abort"]',
    "def prepare_interrupt(self, thread_id: str, expected_turn_id: str | None = None,",
    "*, interrupt: bool = True) -> dict | None:",
    "job = self.active.get(thread_id)",
    "if job is None:",
    "return None",
    'if expected_turn_id and expected_turn_id != job["turnId"]:',
    'raise RpcError(-32004, "回合已变化；请刷新后再中断")',
    'job["cancel"].set()',
    "self._claim_abort_locked(job, interrupt=interrupt)",
    "def interrupt(self, thread_id: str, expected_turn_id: str | None = None) -> bool:",
    "job = self.prepare_interrupt(thread_id, expected_turn_id)",
    "return False",
    'job["_shutdown_abort"].start()',
    "return True",
    "def cancel_all(self, *, interrupt: bool = True) -> None:",
    "self.closed = True",
    "self._capacity_wake.set()",
    "for job in self.jobs.values():",
    'job["cancel"].set()',
    "self._claim_abort_locked(job, interrupt=interrupt)",
    "def request_stop_aborts(self) -> None:",
    'aborts = [job["_shutdown_abort"] for job in self.jobs.values() if "_shutdown_abort" in job]',
    "for abort in aborts:",
    "abort.start()",
    "def wait_for_stop(self, deadline: float) -> None:",
    'workers = [job.get("worker") for job in self.jobs.values()]',
    "workers.append(self._capacity_worker)",
    'workers.extend(job["_shutdown_abort"].worker for job in self.jobs.values()',
    "join_until(workers, deadline)",
    "def stop(self, *, deadline: float | None = None) -> None:",
    "deadline = time.monotonic() + 2 if deadline is None else deadline",
    "self.cancel_all(interrupt=True)",
    "self.request_stop_aborts()",
    "self.wait_for_stop(deadline)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _class_source(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少类 {name}")


def _method(tree: ast.Module, source: str, owner: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == owner:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 {owner}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_runtime_capacity() -> int:
    source = _read(RUNTIME)
    tree = ast.parse(source)
    owner = _class_source(tree, source, "RuntimeManager")
    start = _method(tree, source, "RuntimeManager", "start_capacity_notifications")
    run = _method(tree, source, "RuntimeManager", "_run_capacity_notifications")
    admission = _method(tree, source, "RuntimeManager", "check_admission")
    reserve = _method(tree, source, "RuntimeManager", "reserve")
    release = _method(tree, source, "RuntimeManager", "release")
    retire = _method(tree, source, "RuntimeManager", "_retire_locked")
    abort_done = _method(tree, source, "RuntimeManager", "_abort_done")
    claim = _method(tree, source, "RuntimeManager", "_claim_abort_locked")
    prepare = _method(tree, source, "RuntimeManager", "prepare_interrupt")
    cancel = _method(tree, source, "RuntimeManager", "cancel_all")
    stop_aborts = _method(tree, source, "RuntimeManager", "request_stop_aborts")
    wait_stop = _method(tree, source, "RuntimeManager", "wait_for_stop")
    stop = _method(tree, source, "RuntimeManager", "stop")
    checked = _ordered(CLASS_ORDER, owner, RUNTIME)
    # 关闭标志只由 cancel_all 写入一次。
    if owner.count("self.closed = True") != 1:
        raise ValueError(f"{RUNTIME} 的关闭标志必须只由 cancel_all 写入")
    checked += 1
    # 准入检查必须在 reserve 的锁内执行，准入顺序固定。
    if reserve.count("            self.check_admission(thread_id)") != 1:
        raise ValueError(f"{RUNTIME} 的预留必须在锁内重复准入检查")
    checked += 1
    if admission.count('"TURN_CONCURRENCY_LIMIT"') != 1 or admission.count('"TURN_OWNER_LIMIT"') != 1:
        raise ValueError(f"{RUNTIME} 的准入必须区分会话上限与 owner 上限")
    checked += 1
    # 释放与回收都必须做对象身份比较，不能按 id 直接删除。
    if release.count("is job") != 1 or release.count("self.active.pop(") != 1:
        raise ValueError(f"{RUNTIME} 的释放必须比较对象身份")
    checked += 1
    if retire.count("is job") != 1 or retire.count("self.jobs.pop(") != 1:
        raise ValueError(f"{RUNTIME} 的回收必须比较对象身份")
    checked += 1
    if retire.count('abort is None or abort.done.is_set()') != 1:
        raise ValueError(f"{RUNTIME} 的回收必须等待 abort 结束")
    checked += 1
    # abort 认领幂等：同一回合只创建一次，回调绑定该回合。
    if claim.count('if "_shutdown_abort" not in job:') != 1:
        raise ValueError(f"{RUNTIME} 的 abort 认领必须幂等")
    checked += 1
    if claim.count("TrackedAbort(") != 1 or claim.count("self._abort_done(job)") != 1:
        raise ValueError(f"{RUNTIME} 的 abort 认领必须绑定回合回收")
    checked += 1
    # 中断只做准备与认领，实际派发在 interrupt 中完成。
    if prepare.count(".start()") != 0:
        raise ValueError(f"{RUNTIME} 的中断准备不得派发 abort")
    checked += 1
    if '"turn-abort"' not in claim:
        raise ValueError(f"{RUNTIME} 的 abort 线程必须使用固定名称")
    checked += 1
    # request_stop_aborts 在锁外启动，避免回调重入。
    if stop_aborts.count("\n        for abort in aborts:") != 1:
        raise ValueError(f"{RUNTIME} 的停止派发必须在锁外遍历快照")
    checked += 1
    if stop_aborts.count("\n            abort.start()") != 1:
        raise ValueError(f"{RUNTIME} 的停止派发必须在锁外启动")
    checked += 1
    # wait_for_stop 在锁外等待 worker。
    if wait_stop.count("\n        join_until(workers, deadline)") != 1:
        raise ValueError(f"{RUNTIME} 的停止等待必须在锁外进行")
    checked += 1
    if wait_stop.count("self._capacity_worker") != 1:
        raise ValueError(f"{RUNTIME} 的停止等待必须包含容量通知 worker")
    checked += 1
    # 默认停止窗口固定 2 秒，顺序固定为取消、派发、等待。
    if stop.count("time.monotonic() + 2") != 1:
        raise ValueError(f"{RUNTIME} 的默认停止窗口必须为 2 秒")
    checked += 1
    # 容量通知 worker：守护线程、关闭后不再回调、回调异常不结束循环。
    if start.count("daemon=True") != 1 or start.count("_capacity_worker_done.clear()") != 1:
        raise ValueError(f"{RUNTIME} 的容量通知 worker 必须是守护线程并复位完成事件")
    checked += 1
    if run.count("                if self.closed:") != 1:
        raise ValueError(f"{RUNTIME} 的容量通知必须在锁内检查关闭")
    checked += 1
    if run.count("except Exception:") != 1 or run.count("pass") != 1:
        raise ValueError(f"{RUNTIME} 的容量通知必须吞掉回调异常")
    checked += 1
    if run.count("self._capacity_worker_done.set()") != 1:
        raise ValueError(f"{RUNTIME} 的容量通知退出必须标记完成")
    checked += 1
    # 只有回收成功才唤醒容量通知。
    if abort_done.count("\n            self._capacity_wake.set()") != 1:
        raise ValueError(f"{RUNTIME} 的容量唤醒必须在回收成功分支内")
    checked += 1
    if owner.count("not self.closed") != 1:
        raise ValueError(f"{RUNTIME} 的可用容量必须排除已关闭内核")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_runtime_capacity()
    except (ValueError, SyntaxError) as error:
        print(f"运行时容量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"运行时容量一致：{checked} 项准入、归属与关闭校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
