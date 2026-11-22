#!/usr/bin/env python3
"""核对宿主工具桥的幂等清理边界。

bridge_lifecycle.py 决定桥接实例何时执行 close / dispose：同一对象只清理一次，
死引用在扫描时剔除，钩子在锁外调用，清理异常只记录类型名。任一规则被放宽都会
导致重复关闭或泄漏异常文本，因此静态固定。
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/bridge_lifecycle.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.bridge_lifecycle import BridgeLifecycle  # noqa: E402

FIELD_FRAGMENTS = (
    "self._lock = threading.RLock()",
    "self._closed: list[weakref.ReferenceType] = []",
)
CLOSE_FRAGMENTS = (
    "if bridge is None:\n            return",
    "with self._lock:",
    "for reference in self._closed:",
    "current = reference()",
    # 已回收的桥不再保留引用，避免清理表无限增长。
    "if current is None:\n                    continue",
    "retained.append(reference)",
    "already_closed = already_closed or current is bridge",
    "self._closed = retained",
    "if already_closed:\n                return",
    "reference = weakref.ref(bridge)",
    "except TypeError:",
    "reference = None",
    "self._closed.append(reference)",
    # 钩子必须在释放清理表锁之后调用，慢 close 不阻塞其他桥。
    'closer = getattr(bridge, "close", None)',
    "if not callable(closer):",
    'closer = getattr(bridge, "dispose", None)',
    "if callable(closer):\n                closer()",
    "except Exception as exc:",
    # 只记录异常类型名：异常消息可能包含路径或凭据。
    '_LOG.warning("tool bridge cleanup failed (%s)", type(exc).__name__)',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "Bridge 可提供同步且应快速返回的 `close()`，或以 `dispose()` 作为兜底"),
    (TECHNICAL_REFERENCE, "重复关闭不会再次调用钩子。清理异常不会改写任务结果。"),
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


class _Bridge:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _Disposable:
    def __init__(self) -> None:
        self.disposed = 0

    def dispose(self) -> None:
        self.disposed += 1


class _Both:
    def __init__(self) -> None:
        self.closed = 0
        self.disposed = 0

    def close(self) -> None:
        self.closed += 1

    def dispose(self) -> None:
        self.disposed += 1


class _Bare:
    pass


class _Raising:
    def __init__(self) -> None:
        self.calls = 0

    def close(self) -> None:
        self.calls += 1
        raise RuntimeError("SECRET-PATH-/tmp/private")


class _NoWeak:
    __slots__ = ("closed",)

    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _Handler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"工具桥清理行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _behavior_checks() -> int:
    checked = 0
    lifecycle = BridgeLifecycle()
    lifecycle.close(None)
    checked += _expect_value(lifecycle._closed, [], "空桥直接返回")

    bridge = _Bridge()
    lifecycle.close(bridge)
    lifecycle.close(bridge)
    checked += _expect_value(bridge.closed, 1, "同一对象只清理一次")
    checked += _expect_value(len(lifecycle._closed), 1, "清理表登记")

    disposable = _Disposable()
    lifecycle.close(disposable)
    lifecycle.close(disposable)
    checked += _expect_value(disposable.disposed, 1, "dispose 兜底一次")

    both = _Both()
    lifecycle.close(both)
    checked += _expect_value((both.closed, both.disposed), (1, 0), "close 优先于 dispose")

    lifecycle.close(_Bare())
    checked += _expect_value(len(lifecycle._closed), 4, "无钩子仍登记")

    logger = logging.getLogger("boss_harness.bridge_lifecycle")
    handler = _Handler()
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        raising = _Raising()
        lifecycle.close(raising)
        lifecycle.close(raising)
        checked += _expect_value(raising.calls, 1, "异常后仍只清理一次")
        checked += _expect_value(len(handler.records), 1, "异常记录一次")
        record = handler.records[0]
        checked += _expect_value(record.levelno, logging.WARNING, "异常记录级别")
        message = record.getMessage()
        checked += _expect_value(message, "tool bridge cleanup failed (RuntimeError)",
                                 "异常记录类型名")
        checked += _expect_value("SECRET-PATH-/tmp/private" in message, False, "异常不落原文")
        checked += _expect_value("SECRET-PATH" in str(record.args), False, "记录参数不含原文")
    finally:
        logger.propagate = previous_propagate
        logger.removeHandler(handler)

    done = threading.Event()
    other = _Bridge()

    class _Probe:
        def close(self) -> None:
            worker = threading.Thread(
                target=lambda: (lifecycle.close(other), done.set()), daemon=True,
                name="bridge-cleanup")
            worker.start()
            done.wait(2)

    lifecycle.close(_Probe())
    checked += _expect_value(done.is_set(), True, "钩子在锁外执行")
    checked += _expect_value(other.closed, 1, "并发清理完成")

    narrow = BridgeLifecycle()
    no_weak = _NoWeak()
    narrow.close(no_weak)
    narrow.close(no_weak)
    checked += _expect_value(no_weak.closed, 2, "不可弱引用不登记")
    checked += _expect_value(narrow._closed, [], "不可弱引用清理表为空")

    pruned = BridgeLifecycle()
    temporary = [_Bridge() for _ in range(50)]
    for item in temporary:
        pruned.close(item)
    del item
    temporary.clear()
    gc.collect()
    survivor = _Bridge()
    pruned.close(survivor)
    checked += _expect_value(len(pruned._closed), 1, "死引用剔除")
    return checked


def check_bridge_lifecycle() -> int:
    module = _read(MODULE)
    checked = _expect(FIELD_FRAGMENTS, module, MODULE)
    checked += _expect(CLOSE_FRAGMENTS, module, MODULE)
    # 先判重再登记，判重发生在锁内；钩子调用必须在锁外。
    checked += _ordered(
        (
            "with self._lock:",
            "if already_closed:",
            "self._closed.append(reference)",
            'closer = getattr(bridge, "close", None)',
            "closer()",
        ),
        module,
        MODULE,
    )
    # 显式 close 优先，缺失时才回退 dispose。
    checked += _ordered(
        (
            'closer = getattr(bridge, "close", None)',
            "if not callable(closer):",
            'closer = getattr(bridge, "dispose", None)',
        ),
        module,
        MODULE,
    )
    # 清理异常必须被吞掉：重新抛出或记录原文都会改变任务结果或泄漏细节。
    if "raise" in module:
        raise ValueError(f"{MODULE} 的清理异常必须收敛")
    if "_LOG.exception(" in module:
        raise ValueError(f"{MODULE} 不得记录清理异常的堆栈")
    if "str(exc)" in module or "repr(exc)" in module:
        raise ValueError(f"{MODULE} 的清理日志不得包含异常原文")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_bridge_lifecycle()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"工具桥清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具桥清理一致：{checked} 项幂等与异常防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
