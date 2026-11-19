#!/usr/bin/env python3
"""核对关闭等待预算与中止线程的所有权边界。

shutdown.py 的 TrackedAbort 只发信号，不执行内联中止；收尾幂等且只跑一次；
两秒预算由 runtime / application / connections 各自兑现。任一规则被放宽都不会
触发构建失败，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/shutdown.py"
RUNTIME = "harness/src/boss_harness/runtime.py"
APPLICATION = "harness/src/boss_harness/application.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    except ValueError as error:
        print(f"关闭等待预算核对失败，{error}", file=sys.stderr)
        return 2
    print(f"关闭等待预算一致：{checked} 项中止与等待防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
