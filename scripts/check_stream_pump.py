#!/usr/bin/env python3
"""核对异步流泵的缓冲预算、终止事件与线程收尾边界。

stream_pump.py 把一个异步 SDK 生产器桥接为同步迭代器：事件在入队前按字节与结构
计费，取消、超时与失败都只交付一个终止事件，后台线程在固定名额与固定等待内收尾。
任一放宽都会让事件无界占用内存或让取消结论被覆盖，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/models/stream_pump.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

CONSTANT_FRAGMENTS = (
    "_MAX_BUFFERED_EVENTS = 64\n",
    "_MAX_BUFFERED_BYTES = 4 * 1024 * 1024\n",
    "_MAX_EVENT_BYTES = 2 * 1024 * 1024\n",
    "_MAX_EVENT_NODES = 32768\n",
    "_MAX_ACTIVE_PUMPS = 8\n",
    "_CLEANUP_JOIN_SECONDS = 1.0\n",
    "_ACTIVE_PUMPS = threading.BoundedSemaphore(_MAX_ACTIVE_PUMPS)\n",
)
TEXT_SIZE_FRAGMENTS = (
    "for start in range(0, len(value), 4096):",
    'total += len(value[start:start + 4096].encode("utf-8", errors="replace"))',
    "if total > limit:",
    "return limit + 1",
)
EVENT_SIZE_FRAGMENTS = (
    "def _event_size(value: object, limit: int, *, seen: set[int] | None = None,",
    "if limit < 0:",
    "return 1",
    "if depth > 32:",
    "if nodes[0] > _MAX_EVENT_NODES:",
    "if value is None or type(value) in (bool, int, float):",
    "return sys.getsizeof(value)",
    "if isinstance(value, str):",
    "if isinstance(value, bytes):",
    "identity = id(value)",
    "if identity in seen:",
    "return 0",
    "if isinstance(value, dict):",
    "total = 64",
    "total += 16",
    "if isinstance(value, (list, tuple, set, frozenset)):",
    'attributes = getattr(value, "__dict__", None)',
    'for slot in ("__pydantic_extra__", "__pydantic_private__", "__pydantic_fields_set__"):',
    "return 128",
)
PUBLISH_FRAGMENTS = (
    "size = _event_size(event, _MAX_EVENT_BYTES)",
    "if size > _MAX_EVENT_BYTES:",
    'raise OutputBudgetExceeded("模型流事件超过本地缓冲字节上限")',
    "if self._finished:",
    "raise asyncio.CancelledError",
    "if (self._events.qsize() < _MAX_BUFFERED_EVENTS",
    "and self._buffered_bytes + size <= _MAX_BUFFERED_BYTES):",
    "self._events.put_nowait(_QueuedEvent(event, size))",
    "self._buffered_bytes += size",
    "except queue.Full:",
    "await asyncio.sleep(0.001)",
)
DEADLINE_FRAGMENTS = (
    "aborted = self._cancel_requested",
    "self._deadline_expired = not aborted",
    "self._discard_pending_events()",
    "self._events.put_nowait(StreamAborted() if aborted else StreamDeadlineExceeded())",
    "cancel_task = task is not None and not task.done() and not self._task_cancel_sent",
    "self._task_cancel_sent = True",
    "task.cancel()",
)
FINISH_FRAGMENTS = (
    "def _finish(self, value: object) -> None:",
    "self._events.put_nowait(value)",
)
EXECUTE_FRAGMENTS = (
    "loop.call_later(self._timeout, self._expire_deadline)",
    "except asyncio.CancelledError:",
    "terminal = StreamDeadlineExceeded() if self._deadline_expired else StreamAborted()",
    "except BaseException as exc:",
    "self._finish(exc)",
    "self._finish(StreamDeadlineExceeded() if self._deadline_expired else _END)",
    "deadline.cancel()",
)
RUN_FRAGMENTS = (
    "loop = asyncio.new_event_loop()",
    "asyncio.set_event_loop(loop)",
    "task = loop.create_task(self._execute())",
    "cancel = self._cancel_requested and not self._task_cancel_sent",
    "loop.call_soon(task.cancel)",
    "loop.run_until_complete(task)",
    "loop.run_until_complete(loop.shutdown_asyncgens())",
    "loop.close()",
    "_ACTIVE_PUMPS.release()",
    "self._done.set()",
)
CANCEL_FRAGMENTS = (
    "def cancel(self) -> None:",
    "self._cancel_requested = True",
    "loop, task = self._loop, self._task",
    "loop.call_soon_threadsafe(task.cancel)",
    "except RuntimeError:",
)
CLOSE_FRAGMENTS = (
    "def close(self) -> None:",
    "self.cancel()",
    "if threading.current_thread() is not self._thread:",
    "self._thread.join(timeout=_CLEANUP_JOIN_SECONDS)",
)
NEXT_FRAGMENTS = (
    "value = self._events.get()",
    "if value is _END:",
    "raise StopIteration",
    "if isinstance(value, BaseException):",
    "raise value",
    "if not isinstance(value, _QueuedEvent):",
    'raise RuntimeError("模型流队列中出现无效事件")',
    "self._buffered_bytes = max(0, self._buffered_bytes - value.size)",
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "同步 provider 通过每个请求一个后台线程桥接异步 SDK 流：队列最多 64 个事件、缓冲合计最多 4 MiB、单事件最多 2 MiB，同一进程最多 8 个在途泵"),
    (TECHNICAL_REFERENCE, "取消、超时与失败先丢弃排队事件并只交付一个终止事件，清理等待最多 1 秒"),
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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_stream_pump() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(TEXT_SIZE_FRAGMENTS, module, MODULE)
    checked += _expect(EVENT_SIZE_FRAGMENTS, module, MODULE)
    checked += _expect(PUBLISH_FRAGMENTS, module, MODULE)
    checked += _expect(DEADLINE_FRAGMENTS, module, MODULE)
    checked += _expect(FINISH_FRAGMENTS, module, MODULE)
    checked += _expect(EXECUTE_FRAGMENTS, module, MODULE)
    checked += _expect(RUN_FRAGMENTS, module, MODULE)
    checked += _expect(CANCEL_FRAGMENTS, module, MODULE)
    checked += _expect(CLOSE_FRAGMENTS, module, MODULE)
    checked += _expect(NEXT_FRAGMENTS, module, MODULE)
    # 发布：先计费 → 超限拒绝 → 容量与字节配额 → 入队 → 记账。
    checked += _ordered(
        (
            "size = _event_size(event, _MAX_EVENT_BYTES)",
            "if size > _MAX_EVENT_BYTES:",
            "if (self._events.qsize() < _MAX_BUFFERED_EVENTS",
            "self._events.put_nowait(_QueuedEvent(event, size))",
            "self._buffered_bytes += size",
        ),
        module,
        MODULE,
    )
    # 终止：丢弃排队事件 → 只入队一个终止事件 → 锁外取消任务。
    checked += _ordered(
        (
            "self._finished = True",
            "self._discard_pending_events()",
            "self._events.put_nowait(StreamAborted() if aborted else StreamDeadlineExceeded())",
            "task.cancel()",
        ),
        module,
        MODULE,
    )
    # 线程收尾：异步生成器 → 关闭事件循环 → 释放名额 → 置位完成。
    checked += _ordered(
        (
            "loop.run_until_complete(loop.shutdown_asyncgens())",
            "loop.close()",
            "                    _ACTIVE_PUMPS.release()\n                    self._done.set()",
        ),
        module,
        MODULE,
    )
    # 迭代消费：结束 → 异常 → 非事件拒绝 → 归还字节配额。
    checked += _ordered(
        (
            "if value is _END:",
            "if isinstance(value, BaseException):",
            "if not isinstance(value, _QueuedEvent):",
            "self._buffered_bytes = max(0, self._buffered_bytes - value.size)",
        ),
        module,
        MODULE,
    )
    # 终止事件专用槽位与线程守护：队列比缓冲上限多 1，线程必须 daemon。
    if "queue.Queue(maxsize=_MAX_BUFFERED_EVENTS + 1)" not in module:
        raise ValueError(f"{MODULE} 的终止事件必须保留独立队列槽位")
    if "daemon=True" not in module:
        raise ValueError(f"{MODULE} 的泵线程必须是 daemon")
    if "daemon=False" in module:
        raise ValueError(f"{MODULE} 不得创建非 daemon 泵线程")
    if 'errors="strict"' in module:
        raise ValueError(f"{MODULE} 的文本计费不得因非法字符中断")
    if "self._thread.join()" in module:
        raise ValueError(f"{MODULE} 的清理等待必须有界")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_stream_pump()
    except ValueError as error:
        print(f"模型流泵核对失败，{error}", file=sys.stderr)
        return 2
    print(f"模型流泵一致：{checked} 项缓冲、终止与收尾防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
