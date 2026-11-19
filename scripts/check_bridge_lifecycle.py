#!/usr/bin/env python3
"""核对宿主工具桥的幂等清理边界。

bridge_lifecycle.py 决定桥接实例何时执行 close / dispose：同一对象只清理一次，
死引用在扫描时剔除，钩子在锁外调用，清理异常只记录类型名。任一规则被放宽都会
导致重复关闭或泄漏异常文本，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/bridge_lifecycle.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

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
    except ValueError as error:
        print(f"工具桥清理核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具桥清理一致：{checked} 项幂等与异常防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
