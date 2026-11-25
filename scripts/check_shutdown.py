#!/usr/bin/env python3
"""核对关闭等待预算与中止线程的所有权边界。

shutdown.py 的 TrackedAbort 只发信号，不执行内联中止；收尾幂等且只跑一次；
两秒预算由 runtime / application / connections 各自兑现。任一规则被放宽都不会
触发构建失败，因此静态固定。

摘要任务让出会话之后还要写完终态事件。这段收尾由临时目录里的真实 ApplicationService
与自写替身线路驱动：闸门挡在终态事件写入之前，核对关闭等待、状态目录归属与会话占用
三者的边界。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/shutdown.py"
RUNTIME = "harness/src/boss_harness/runtime.py"
APPLICATION = "harness/src/boss_harness/application.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.models.types import AssistantMessage, StreamEvent, TextBlock  # noqa: E402
from boss_harness.ownership import StateDirectoryOwner  # noqa: E402
from boss_harness.rpc import JsonRpcServer, RpcError  # noqa: E402
from boss_harness.session import Entry  # noqa: E402
from boss_harness.shutdown import TrackedAbort, join_until  # noqa: E402

ENVIRONMENT_PREFIXES = ("BOSS_HARNESS_", "BOSS_CLI_", "ANTHROPIC_")
GATE_SECONDS = 10
CLOSER = "probe-close"

CONSTANT_FRAGMENTS = (
    # 两秒预算属于内核关闭策略，不得下沉到 provider 传输层。
    "The two-second policy belongs to this harness, not to the provider transport.",
    "class TrackedAbort:",
    "def join_until(workers: Iterable[threading.Thread | None], deadline: float) -> None:",
)
FIELD_FRAGMENTS = (
    "self.done = threading.Event()",
    "self.worker: threading.Thread | None = None",
    "self._lock = threading.Lock()",
    "self._finish_lock = threading.Lock()",
    "self._started = False",
    "self._finished = False",
)
RUN_FRAGMENTS = (
    # 显式 callback 优先于 provider 的 request_abort；缺失时静默跳过。
    "if self.callback is not None:",
    'abort = getattr(self.provider, "request_abort", None)',
    "if callable(abort):",
    "abort()",
    "except Exception:",
    "finally:\n            self._finish()",
)
FINISH_FRAGMENTS = (
    "with self._finish_lock:",
    "if self._finished:",
    "self._finished = True",
    "self.done.set()",
    "self.on_done()",
)
START_FRAGMENTS = (
    "with self._lock:",
    "if self._started:",
    "self._started = True",
    "worker = threading.Thread(target=self._run, daemon=True, name=self.name)",
    "worker.start()",
    'if "worker" not in locals() or worker.ident is None:',
    "self.worker = None",
    "if failed:",
    # 启动失败只退休记账，绝不回退为无界的同步 abort 钩子。
    "# Never replace failed dispatch with an unbounded inline abort hook.",
    "# on_done only retires bookkeeping and can safely run here.\n            self._finish()",
)
JOIN_FRAGMENTS = (
    "seen: set[int] = set()",
    "if (worker is None or worker is threading.current_thread() or worker.ident is None",
    "or id(worker) in seen):",
    "seen.add(id(worker))",
    "worker.join(max(0, deadline - time.monotonic()))",
)
RUNTIME_FRAGMENTS = (
    "from boss_harness.shutdown import TrackedAbort, join_until",
    'name="turn-abort"',
    'callback=job["runner"].interrupt if interrupt else None',
    "deadline = time.monotonic() + 2 if deadline is None else deadline\n",
    "join_until(workers, deadline)",
)
APPLICATION_FRAGMENTS = (
    "from boss_harness.shutdown import TrackedAbort, join_until",
    'name="compaction-abort"',
    "deadline = time.monotonic() + 2\n",
    "self._shutdown_deadline = (deadline if self._shutdown_deadline is None",
    "else min(self._shutdown_deadline, deadline))",
    "self._shutdown_preparing += 1",
    "self.runtimes.cancel_all(interrupt=False)",
    # 先派发所有取消，再触碰可能阻塞的中止钩子；期间准入保持冻结。
    "self.connections.prepare_close()\n            self.connections.request_stop_aborts()\n"
    "            self._request_compaction_aborts()\n            self.runtimes.request_stop_aborts()",
    "self._shutdown_preparing -= 1",
    # 等待顺序固定：连接、摘要、业务回合、审批线程、follow-up。
    "self.connections.wait_for_stop(deadline)\n        self._wait_compaction_jobs(deadline)\n"
    "        self.runtimes.wait_for_stop(deadline)\n"
    "        join_until([self._approval_expiry_thread], deadline)",
    "join_until(follow_up_workers, deadline)",
    'self.events.emit_until("kernel/shutdown", {"state": "stopping"}, deadline=deadline)',
    "self.lifecycle_hooks.close(deadline)",
    "self.snapshots.close()",
)
TAIL_FRAGMENTS = (
    # 登记在运行时锁内完成：等待方每轮的快照不会与之交错。
    'tail = {"owner": threading.get_ident(), "done": threading.Event()}\n'
    "        with self.runtimes.lock:\n            self._compaction_tails[id(tail)] = tail",
    # 摘除与置位同锁：等待方醒来时登记已经消失，随后的空闲判断不会被旧登记挡住。
    'with self.runtimes.lock:\n            self._compaction_tails.pop(id(tail), None)\n'
    '            tail["done"].set()',
    # 每轮重取快照：中止线程可能在工作线程让出任务之后才登记自己的收尾。
    "while time.monotonic() < deadline:\n            with self.runtimes.lock:\n"
    '                pending = [tail["done"] for tail in self._compaction_tails.values()',
    # 关闭若运行在收尾所在的线程上，不能等待自己。
    'if tail["owner"] != current]',
)
# 收尾登记先于任务让出会话：让出会回收 worker 与 abort 引用，其间不能有无人持有的空档；
# 释放放在 finally，收尾中途抛错也不能让状态目录一直被占用。
TAIL_ORDER = (
    "tail = self._retain_compaction_tail()",
    "released = self._retire_compaction_locked(job)",
    "finally:\n            self._release_compaction_tail(tail)",
)
TAIL_METHODS = ("_finish_compaction", "_compaction_abort_done")
CONNECTIONS_FRAGMENTS = (
    "from boss_harness.shutdown import join_until",
    "deadline = time.monotonic() + 2 if deadline is None else deadline\n",
    "# Never join while holding the lock needed by worker finalization.",
    "self.prepare_close()\n        self.request_stop_aborts()\n        self.wait_for_stop(deadline)",
    "join_until(workers, deadline)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "关闭内核时，应用先冻结准入，并为业务回合、摘要任务和连接检查统一置位取消，再异步分发各自的中止。所有 worker 与 abort 共享同一个最多两秒的等待期限"),
    (TECHNICAL_REFERENCE, "`turn/interrupt` 和 `context/compact/abort` 返回的是取消请求确认，不表示 worker 或供应商连接已经退出。"),
    (TECHNICAL_REFERENCE, "摘要任务让出会话之后，终态事件、队列通知与后续唤醒仍由原线程写完：这段收尾不占用会话"),
    (USER_GUIDE, "「停止并退出」会中断运行中的回合"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _method(source: str, name: str) -> str:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "ApplicationService":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    return ast.get_source_segment(source, child) or ""
    raise ValueError(f"{APPLICATION} 缺少 ApplicationService.{name}")


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"关闭等待预算行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _await(event: threading.Event, label: str) -> None:
    if not event.wait(GATE_SECONDS):
        raise ValueError(f"关闭等待预算行为变化 {label}：{GATE_SECONDS} 秒内没有到达预期位置")


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def request_abort(self) -> None:
        self.calls += 1


class _CountingThread(threading.Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.joins = 0

    def join(self, timeout=None):
        self.joins += 1
        return super().join(timeout)


def _raise_abort() -> None:
    raise RuntimeError("中止失败")


def _behavior_checks() -> int:
    checked = 0
    provider = _Provider()
    events: list[str] = []
    guard = TrackedAbort(provider, lambda: events.append("done"), name="turn-abort",
                         callback=lambda: events.append("callback"))
    checked += _expect_value(guard.start(), None, "启动返回")
    checked += _expect_value(guard.done.wait(2), True, "显式回调完成")
    checked += _expect_value(events, ["callback", "done"], "回调优先与收尾")
    checked += _expect_value(provider.calls, 0, "provider 不参与")
    checked += _expect_value((guard.worker.daemon, guard.worker.name), (True, "turn-abort"),
                             "工作线程属性")
    guard.start()
    checked += _expect_value(events, ["callback", "done"], "重复启动不重跑")

    provider = _Provider()
    guard = TrackedAbort(provider, lambda: None, name="provider-abort")
    guard.start()
    checked += _expect_value(guard.done.wait(2), True, "provider 兜底完成")
    checked += _expect_value(provider.calls, 1, "provider 兜底调用")

    guard = TrackedAbort(object(), lambda: None, name="no-hook")
    guard.start()
    checked += _expect_value(guard.done.wait(2), True, "缺少钩子正常收尾")

    finished: list[int] = []
    guard = TrackedAbort(_Provider(), lambda: finished.append(1), name="raising",
                         callback=_raise_abort)
    guard.start()
    checked += _expect_value(guard.done.wait(2), True, "回调异常仍置位")
    checked += _expect_value(finished, [1], "回调异常仍收尾")

    guard = TrackedAbort(_Provider(), _raise_abort, name="bad-done", callback=lambda: None)
    guard.start()
    checked += _expect_value(guard.done.wait(2), True, "收尾异常仍置位")
    checked += _expect_value(guard._finished, True, "收尾异常仍记账")

    calls: list[int] = []
    guard = TrackedAbort(_Provider(), lambda: calls.append(1), name="idempotent")
    guard._finish()
    guard._finish()
    checked += _expect_value(calls, [1], "收尾只执行一次")
    checked += _expect_value(guard.done.is_set(), True, "直接收尾置位")

    calls = []
    guard = TrackedAbort(_Provider(), lambda: None, name="concurrent",
                         callback=lambda: calls.append(1))
    starters = [threading.Thread(target=guard.start) for _ in range(8)]
    for starter in starters:
        starter.start()
    for starter in starters:
        starter.join()
    checked += _expect_value(guard.done.wait(2), True, "并发启动完成")
    checked += _expect_value(calls, [1], "并发启动只派发一次")

    current = threading.current_thread()
    unstarted = _CountingThread(target=lambda: None, name="unstarted", daemon=True)
    finished_thread = _CountingThread(target=lambda: None, name="finished", daemon=True)
    finished_thread.start()
    finished_thread.join()
    finished_thread.joins = 0
    started = time.monotonic()
    checked += _expect_value(join_until(
        [None, current, unstarted, finished_thread, finished_thread], started + 0.2), None,
        "等待返回")
    checked += _expect_value(time.monotonic() - started < 1.0, True, "跳过不等待")
    checked += _expect_value(unstarted.joins, 0, "未启动不 join")
    checked += _expect_value(finished_thread.joins, 1, "重复线程只 join 一次")

    release = threading.Event()
    blocked = _CountingThread(target=release.wait, name="blocked", daemon=True)
    blocked.start()
    started = time.monotonic()
    join_until([blocked], started + 0.05)
    elapsed = time.monotonic() - started
    alive_at_deadline = blocked.is_alive()
    # 先释放测试线程再断言：失败路径也不能留下非守护线程拖住进程退出。
    release.set()
    blocked.join(2)
    checked += _expect_value(elapsed >= 0.01, True, "等待到截止时间")
    checked += _expect_value(elapsed < 0.5, True, "截止时间上限")
    checked += _expect_value(alive_at_deadline, True, "截止后不等待存活线程")
    checked += _expect_value(blocked.is_alive(), False, "释放后退出")
    return checked


@contextmanager
def _clean_environment(directory: str):
    # 线路发现与工具桥会读环境变量：摘要场景只用传入的替身线路，也不解析真实 CLI。
    with patch.dict(os.environ, {}, clear=False):
        for name in [key for key in os.environ if key.startswith(ENVIRONMENT_PREFIXES)]:
            os.environ.pop(name, None)
        os.environ["BOSS_CLI_BIN"] = str(Path(directory) / "no-such-cli")
        yield


class _SummaryProvider:
    """摘要线路替身：不联网；可在流内与中止钩子处停住，用来固定线程时序。"""

    id = "probe"

    def __init__(self, *, hold: bool = False) -> None:
        self.streaming, self.aborting = threading.Event(), threading.Event()
        self.stream_gate, self.abort_gate = threading.Event(), threading.Event()
        if not hold:
            self.stream_gate.set()
            self.abort_gate.set()

    def stream(self, request):
        self.streaming.set()
        self.stream_gate.wait(GATE_SECONDS)
        yield StreamEvent(type="done", message=AssistantMessage(blocks=(TextBlock(text="摘要正文"),)))

    def request_abort(self) -> None:
        self.aborting.set()
        self.abort_gate.wait(GATE_SECONDS)


class _Kernel:
    """临时状态目录里的真实 ApplicationService；闸门挡在摘要终态事件写入之前。"""

    def __init__(self, directory: str, terminal: str, provider: _SummaryProvider) -> None:
        root = Path(directory)
        self.state = root / "state"
        (root / "workspace").mkdir()
        self.terminal, self.provider = terminal, provider
        self.entered, self.release = threading.Event(), threading.Event()
        self.job_id = ""
        server = JsonRpcServer()
        server._out = io.StringIO()
        self.service = ApplicationService(server, self.state, ModelConfig(provider="openai", model="m1"),
                                          None, provider_factory=lambda config: provider,
                                          workspace=root / "workspace")
        emit = self.service.events.emit

        def gated(method, params=None, **kwargs):
            if method == terminal and not self.release.is_set():
                self.entered.set()
                self.release.wait(GATE_SECONDS)
            return emit(method, params, **kwargs)

        self.service.events.emit = gated

    def start(self) -> None:
        service = self.service
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                               "protocolVersion": "0.2.0"})
        service.on_initialized(None)
        self.thread_id = service.on_thread_start({})["thread"]["id"]
        service.sessions.record_turn(self.thread_id, "turn-1", "completed")
        service.sessions.append(self.thread_id, Entry(type="item", payload={
            "kind": "userMessage", "text": "你好", "turnId": "turn-1"}))
        self.job_id = service.on_context_compact_start(
            {"threadId": self.thread_id, "throughTurnId": "turn-1"})["jobId"]

    def status(self) -> str:
        return self.service.on_context_compact_read({"jobId": self.job_id})["status"]

    def archived(self) -> object:
        try:
            return self.service.on_thread_archive({"threadId": self.thread_id})["thread"]["archived"]
        except RpcError as error:
            return f"{error.code} {error}"

    def owner_free(self) -> bool:
        try:
            owner = StateDirectoryOwner(self.state)
        except OSError:
            return False
        owner.close()
        return True

    def logged(self) -> bool:
        try:
            lines = (self.state / "events.jsonl").read_bytes().splitlines()
        except OSError:
            return False
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if (record.get("method") == self.terminal
                    and (record.get("params") or {}).get("jobId") == self.job_id):
                return True
        return False

    def close(self) -> tuple[threading.Thread, dict]:
        """在另一条线程上关闭内核，并在 close() 返回的那一刻记录落盘与归属状态。"""
        outcome: dict = {}

        def run() -> None:
            started = time.monotonic()
            self.service.close()
            outcome.update(seconds=time.monotonic() - started, logged=self.logged(),
                           free=self.owner_free())

        closer = threading.Thread(target=run, name=CLOSER, daemon=True)
        closer.start()
        return closer, outcome

    def await_free(self) -> bool:
        deadline = time.monotonic() + GATE_SECONDS
        while time.monotonic() < deadline:
            if self.owner_free():
                return True
            time.sleep(0.01)
        return False

    def shutdown(self) -> None:
        # 失败路径也要放开全部闸门并等线程退出：临时目录不能在仍有写入者时被清理。
        for gate in (self.release, self.provider.stream_gate, self.provider.abort_gate):
            gate.set()
        try:
            self.service.close()
        finally:
            for thread in threading.enumerate():
                if thread.name.startswith(("compact-", "compaction-abort", CLOSER)):
                    thread.join(GATE_SECONDS)


def _close_window(outcome: dict) -> str:
    seconds = outcome.get("seconds")
    if seconds is None:
        return "期限后仍未返回"
    if seconds < 1.5:
        return f"提前返回（{seconds:.2f} 秒）"
    return "按期限返回"


def _tail_wait_checks() -> int:
    """收尾在期限内结束：关闭等到终态事件写完才返回，其间会话不被占用。"""
    checked = 0
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory, _clean_environment(directory):
        kernel = _Kernel(directory, "context/compactionCompleted", _SummaryProvider())
        try:
            kernel.start()
            _await(kernel.entered, "摘要终态事件")
            checked += _expect_value(kernel.status(), "completed", "收尾期间终态已公开")
            checked += _expect_value(kernel.archived(), True, "收尾不占用会话")
            closer, outcome = kernel.close()
            closer.join(0.2)
            blocked = closer.is_alive()
            kernel.release.set()
            closer.join(GATE_SECONDS)
            checked += _expect_value((blocked, outcome.get("logged")), (True, True),
                                     "关闭等待收尾且返回前终态已落盘")
            checked += _expect_value(outcome.get("free"), True, "关闭返回时状态目录已释放")
        finally:
            kernel.shutdown()
    return checked


def _tail_deadline_checks() -> int:
    """收尾超过共享期限：关闭照常返回，状态目录留到收尾结束才释放。"""
    checked = 0
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory, _clean_environment(directory):
        kernel = _Kernel(directory, "context/compactionCompleted", _SummaryProvider())
        try:
            kernel.start()
            _await(kernel.entered, "摘要终态事件")
            closer, outcome = kernel.close()
            closer.join(6)
            checked += _expect_value(_close_window(outcome), "按期限返回", "收尾超过期限")
            checked += _expect_value(outcome.get("free"), False, "期限后状态目录仍由收尾持有")
            kernel.release.set()
            checked += _expect_value(kernel.await_free(), True, "收尾结束后释放状态目录")
        finally:
            kernel.shutdown()
    return checked


def _tail_abort_checks() -> int:
    """中止钩子晚于工作线程结束：终态事件由中止线程写出，关闭同样等待。"""
    checked = 0
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory, _clean_environment(directory):
        provider = _SummaryProvider(hold=True)
        kernel = _Kernel(directory, "context/compactionFailed", provider)
        try:
            kernel.start()
            _await(provider.streaming, "摘要请求")
            worker = next((thread for thread in threading.enumerate()
                           if thread.name == f"compact-{kernel.job_id[:8]}"), None)
            kernel.service.on_context_compact_abort({"jobId": kernel.job_id})
            _await(provider.aborting, "中止钩子")
            # 中止钩子仍挂起时任务无法让出：工作线程先退出，终态事件留给中止线程。
            provider.stream_gate.set()
            if worker is None:
                raise ValueError("关闭等待预算行为变化 摘要工作线程：没有找到 compact- 线程")
            worker.join(GATE_SECONDS)
            provider.abort_gate.set()
            _await(kernel.entered, "中止线程上的终态事件")
            closer, outcome = kernel.close()
            closer.join(0.2)
            blocked = closer.is_alive()
            kernel.release.set()
            closer.join(GATE_SECONDS)
            checked += _expect_value((blocked, outcome.get("logged")), (True, True),
                                     "关闭等待中止线程上的收尾")
        finally:
            kernel.shutdown()
    return checked


def check_shutdown() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(FIELD_FRAGMENTS, module, MODULE)
    checked += _expect(RUN_FRAGMENTS, module, MODULE)
    checked += _expect(FINISH_FRAGMENTS, module, MODULE)
    checked += _expect(START_FRAGMENTS, module, MODULE)
    checked += _expect(JOIN_FRAGMENTS, module, MODULE)
    # 收尾必须先占锁判重，再置位 done，最后才执行 on_done。
    checked += _ordered(
        (
            "with self._finish_lock:",
            "if self._finished:",
            "self._finished = True",
            "self.done.set()",
            "self.on_done()",
        ),
        module,
        MODULE,
    )
    # 启动只许一次：标记、建线程、启动、失败清理的顺序不可回退。
    checked += _ordered(
        (
            "if self._started:",
            "self._started = True",
            "worker.start()",
            'if "worker" not in locals() or worker.ident is None:',
            "self.worker = None",
            "# on_done only retires bookkeeping and can safely run here.\n            self._finish()",
        ),
        module,
        MODULE,
    )
    # 中止线程先跑 callback，再回退 request_abort，最后必须走 finally 收尾。
    checked += _ordered(
        (
            "if self.callback is not None:",
            'abort = getattr(self.provider, "request_abort", None)',
            "finally:\n            self._finish()",
        ),
        module,
        MODULE,
    )
    runtime = _read(RUNTIME)
    checked += _expect(RUNTIME_FRAGMENTS, runtime, RUNTIME)
    application = _read(APPLICATION)
    checked += _expect(APPLICATION_FRAGMENTS, application, APPLICATION)
    # 关闭顺序：冻结准入 → 取消派发 → 各域等待 → 关闭钩子与快照。
    checked += _ordered(
        (
            "self._shutdown_preparing += 1",
            "self.runtimes.cancel_all(interrupt=False)",
            "self.connections.prepare_close()",
            "self.connections.request_stop_aborts()",
            "self._shutdown_preparing -= 1",
            "self.connections.wait_for_stop(deadline)",
            "self.runtimes.wait_for_stop(deadline)",
            "self.lifecycle_hooks.close(deadline)\n        self.snapshots.close()",
        ),
        application,
        APPLICATION,
    )
    checked += _expect(TAIL_FRAGMENTS, application, APPLICATION)
    for name in TAIL_METHODS:
        checked += _ordered(TAIL_ORDER, _method(application, name), f"{APPLICATION} 的 {name}")
    connections = _read(CONNECTIONS)
    checked += _expect(CONNECTIONS_FRAGMENTS, connections, CONNECTIONS)
    # 启动失败不得同步执行中止钩子，join 不得无期限。
    if "self._run()" in module:
        raise ValueError(f"{MODULE} 禁止在启动失败时内联执行中止")
    if "worker.join()" in module:
        raise ValueError(f"{MODULE} 的 join 必须受共享期限约束")
    if "daemon=False" in module:
        raise ValueError(f"{MODULE} 的中止线程必须为守护线程")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_shutdown()
        scenarios = sum((_behavior_checks(), _tail_wait_checks(), _tail_deadline_checks(),
                         _tail_abort_checks()))
    except (ValueError, OSError) as error:
        print(f"关闭等待预算核对失败，{error}", file=sys.stderr)
        return 2
    print(f"关闭等待预算一致：{checked} 项中止与等待防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
