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
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "harness/src/boss_harness/runtime.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.rpc import RpcError  # noqa: E402
from boss_harness.runtime import RuntimeManager  # noqa: E402
from boss_harness.shutdown import TrackedAbort  # noqa: E402

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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"运行时容量行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_rpc(call, code: int, message: str, data, label: str) -> int:
    try:
        call()
    except RpcError as error:
        checked = _expect_value(error.code, code, f"{label}错误码")
        checked += _expect_value(str(error), message, f"{label}文案")
        checked += _expect_value(error.data, data, f"{label}数据")
        return checked
    raise ValueError(f"运行时容量行为变化 {label}：期望 RpcError，实际未抛出")


def _wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def request_abort(self) -> None:
        self.calls += 1


class _Runner:
    def __init__(self) -> None:
        self.provider = _Provider()
        self.interrupted = 0

    def interrupt(self) -> None:
        self.interrupted += 1


def _behavior_checks() -> int:
    checked = 0
    runner = _Runner()
    manager = RuntimeManager(capacity=2)
    checked += _expect_value((manager.capacity, manager.owner_capacity), (2, 4), "容量与归属上限")
    checked += _expect_value(manager.has_capacity(), True, "初始可用")
    first = manager.reserve("thread-1", "一", runner)
    manager.reserve("thread-2", "二", runner)
    checked += _expect_value((manager.active["thread-1"] is first,
                              manager.jobs[first["turnId"]] is first), (True, True), "预留登记")
    checked += _expect_value(first["input"], "一", "预留输入")
    checked += _expect_value(manager.has_capacity(), False, "满容量不可用")
    checked += _expect_rpc(lambda: manager.check_admission("thread-3"), -32005,
                           "已达到并发会话上限",
                           {"code": "TURN_CONCURRENCY_LIMIT", "limit": 2}, "会话上限")
    checked += _expect_rpc(lambda: manager.reserve("thread-1", "再次", runner), -32004,
                           "该会话已有回合运行", {"turnId": first["turnId"]}, "会话重复")

    owner = RuntimeManager(capacity=1)
    owner.jobs.update({"fake-1": {"turnId": "fake-1"}, "fake-2": {"turnId": "fake-2"}})
    checked += _expect_value(owner.has_capacity(), False, "归属上限不可用")
    checked += _expect_rpc(lambda: owner.check_admission("thread-x"), -32005,
                           "仍在执行或收尾的回合已达到内核资源上限",
                           {"code": "TURN_OWNER_LIMIT", "limit": 2}, "归属上限")

    closed = RuntimeManager(capacity=2)
    job = closed.reserve("thread-1", "关闭", runner)
    claim = closed._claim_abort_locked(job, interrupt=False)
    closed.cancel_all(interrupt=False)
    checked += _expect_value(closed.closed, True, "关闭标志")
    checked += _expect_value(job["cancel"].is_set(), True, "关闭置位取消")
    checked += _expect_value(closed.has_capacity(), False, "关闭后不可用")
    checked += _expect_rpc(lambda: closed.check_admission("thread-2"), -32003,
                           "内核正在关闭", None, "关闭拒绝")
    closed.finish(job)
    checked += _expect_value(job["turnId"] in closed.jobs, True, "abort 未完成保留")
    claim._finish()
    checked += _expect_value(job["turnId"] not in closed.jobs, True, "abort 完成后回收")

    manager = RuntimeManager(capacity=2)
    old = manager.reserve("thread", "旧", runner)
    replacement = {"threadId": "thread", "turnId": "new"}
    manager.active["thread"] = replacement
    manager.release(old)
    checked += _expect_value(manager.active["thread"] is replacement, True, "旧回合不释放新槽位")
    manager.release(replacement)
    checked += _expect_value("thread" in manager.active, False, "同对象释放")

    manager = RuntimeManager(capacity=2)
    idle: list[int] = []
    manager.on_idle = lambda: idle.append(1)
    job = manager.reserve("thread", "x", runner)
    manager.finish(job)
    checked += _expect_value((job["_worker_done"], job["turnId"] not in manager.jobs),
                             (True, True), "无 abort 回收")
    checked += _expect_value(idle, [1], "回收通知 idle")
    job = manager.reserve("thread-2", "x", runner)
    abort = manager._claim_abort_locked(job, interrupt=False)
    manager.finish(job)
    checked += _expect_value(job["turnId"] in manager.jobs, True, "abort 未完成保留")
    abort._finish()
    checked += _expect_value(job["turnId"] in manager.jobs, False, "abort 完成后回收")

    manager = RuntimeManager(capacity=2)
    runner = _Runner()
    job = manager.reserve("thread", "x", runner)
    checked += _expect_value(manager.prepare_interrupt("missing"), None, "未知会话")
    checked += _expect_rpc(lambda: manager.prepare_interrupt("thread", "other"), -32004,
                           "回合已变化；请刷新后再中断", None, "回合变化")
    prepared = manager.prepare_interrupt("thread", job["turnId"])
    checked += _expect_value(prepared is job, True, "准备返回回合")
    checked += _expect_value(job["cancel"].is_set(), True, "准备置位取消")
    claim = job["_shutdown_abort"]
    checked += _expect_value(isinstance(claim, TrackedAbort), True, "认领中止")
    checked += _expect_value(manager.prepare_interrupt("thread")["_shutdown_abort"] is claim, True,
                             "重复认领同一中止")
    checked += _expect_value(claim.callback, runner.interrupt, "中断回调绑定")
    checked += _expect_value(manager.interrupt("missing"), False, "未知中断返回假")
    checked += _expect_value(manager.interrupt("thread"), True, "中断派发")
    checked += _expect_value(claim.done.wait(2), True, "中断完成")
    checked += _expect_value(runner.interrupted, 1, "中断回调一次")
    checked += _expect_value(claim.worker.name, "turn-abort", "中止线程名称")
    checked += _expect_value(runner.provider.calls, 0, "provider 不参与")

    manager = RuntimeManager(capacity=2)
    runner = _Runner()
    job = manager.reserve("thread", "x", runner)
    manager.cancel_all(interrupt=False)
    claim = job["_shutdown_abort"]
    checked += _expect_value(claim.callback, None, "关闭不绑定中断")
    checked += _expect_value(job["cancel"].is_set(), True, "关闭置位取消")
    manager.request_stop_aborts()
    manager.request_stop_aborts()
    checked += _expect_value(claim.done.wait(2), True, "停止派发完成")
    checked += _expect_value(runner.interrupted, 0, "关闭不执行中断")
    checked += _expect_value(job["turnId"] in manager.jobs, True, "未完成回合保留")
    manager.finish(job)
    checked += _expect_value(job["turnId"] in manager.jobs, False, "完成后回收")

    manager = RuntimeManager(capacity=1)
    wakes: list[int] = []
    checked += _expect_value(manager.capacity_notifications_stopped, True, "初始已停止")
    manager.start_capacity_notifications(lambda: wakes.append(1))
    checked += _expect_value(manager.capacity_notifications_stopped, False, "启动后未停止")
    try:
        manager.start_capacity_notifications(lambda: None)
    except RuntimeError as error:
        checked += _expect_value(str(error), "容量通知 worker 已启动或内核已关闭", "重复启动拒绝")
    else:
        raise ValueError("运行时容量行为变化 重复启动：期望 RuntimeError，实际未抛出")
    manager._capacity_wake.set()
    checked += _expect_value(_wait_until(lambda: bool(wakes)), True, "容量唤醒回调")
    checked += _expect_value(wakes, [1], "容量回调一次")
    manager.cancel_all(interrupt=False)
    checked += _expect_value(_wait_until(lambda: manager.capacity_notifications_stopped), True,
                             "关闭后停止")
    manager._capacity_wake.set()
    time.sleep(0.05)
    checked += _expect_value(wakes, [1], "关闭后不再回调")

    manager = RuntimeManager(capacity=2)
    runner = _Runner()
    job = manager.reserve("thread", "x", runner)
    manager.start_capacity_notifications(lambda: None)
    manager.stop(deadline=time.monotonic() + 1)
    checked += _expect_value(manager.closed, True, "停止关闭内核")
    checked += _expect_value(job["_shutdown_abort"].done.is_set(), True, "停止完成中止")
    checked += _expect_value(manager.capacity_notifications_stopped, True, "停止回收 worker")

    manager = RuntimeManager(capacity=2)
    release = threading.Event()
    worker = threading.Thread(target=release.wait, daemon=True, name="turn-worker")
    worker.start()
    job = manager.reserve("thread", "x", _Runner())
    job["worker"] = worker
    started = time.monotonic()
    manager.wait_for_stop(started + 0.05)
    elapsed = time.monotonic() - started
    alive_at_deadline = worker.is_alive()
    release.set()
    worker.join(2)
    checked += _expect_value(elapsed < 0.5, True, "等待截止上限")
    checked += _expect_value(alive_at_deadline, True, "不等待存活 worker")
    return checked


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
        scenarios = _behavior_checks()
    except (ValueError, SyntaxError) as error:
        print(f"运行时容量核对失败，{error}", file=sys.stderr)
        return 2
    print(f"运行时容量一致：{checked} 项准入、归属与关闭校验、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
