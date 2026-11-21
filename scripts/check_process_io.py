#!/usr/bin/env python3
"""对照子进程输出捕获的溢出、失败与收尾口径。

`BoundedProcessOutput` 用三个 daemon 线程读取 stdout / stderr 并向 stdin 写入：
读取在共享字节上限处设置 `overflow` 并停止，任一操作抛异常设置 `failed`，全部
线程结束后设置 `done`；`join` 只做有界等待，`alive` 报告是否仍有已启动且存活
的线程，`close_unstarted` 只关闭尚未启动线程对应的管道。本脚本用本地 Python
子进程与自定义流做行为对照，不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/process_io.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.process_io import BoundedProcessOutput  # noqa: E402

READ_ORDER = (
    "while not self.overflow.is_set():",
    "chunk = stream.read1(self.CHUNK_BYTES)",
    "if not chunk:",
    "with self._lock:",
    "if self.overflow.is_set():",
    "if self._bytes + len(chunk) > self._limit:",
    "self.overflow.set()",
    "self._bytes += len(chunk)",
    "destination.extend(chunk)",
    "stream.close()",
)

RUN_ORDER = (
    "try:",
    "operation(*args)",
    "except Exception:",
    "with self._lock:",
    "self.failed = True",
    "finally:",
    "self._remaining -= 1",
    "if self._remaining == 0:",
    "self.done.set()",
)

WRITE_ORDER = (
    'stream.write(text.encode("utf-8"))',
    "stream.flush()",
    "except BrokenPipeError:",
    "pass",
    "finally:",
    "stream.close()",
)

JOIN_ORDER = (
    "for thread in self._threads:",
    "if thread.ident is not None:",
    "thread.join(timeout)",
    "return not self.alive()",
)

ALIVE_ORDER = (
    "return any(thread.ident is not None and thread.is_alive() for thread in self._threads)",
)

CLOSE_ORDER = (
    "for thread, stream in zip(self._threads, self._pipes):",
    "if thread.ident is None:",
    "stream.close()",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BoundedProcessOutput":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 BoundedProcessOutput.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"进程输出捕获行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


class _Recorder:
    """按块返回固定字节的读取流，可注入异常。"""

    def __init__(self, payload: bytes = b"", *, error: Exception | None = None,
                 chunk: int | None = None) -> None:
        self.payload = payload
        self.error = error
        self.chunk = chunk
        self.closed = False

    def read1(self, size: int) -> bytes:
        if self.error is not None:
            raise self.error
        take = size if self.chunk is None else min(size, self.chunk)
        data, self.payload = self.payload[:take], self.payload[take:]
        return data

    def close(self) -> None:
        self.closed = True


class _Writer:
    def __init__(self) -> None:
        self.data = b""
        self.flushed = False
        self.closed = False

    def write(self, chunk: bytes) -> None:
        self.data += chunk

    def flush(self) -> None:
        self.flushed = True

    def close(self) -> None:
        self.closed = True


class _BrokenWriter(_Writer):
    def write(self, chunk: bytes) -> None:
        raise BrokenPipeError()


class _Blocking:
    def __init__(self) -> None:
        self.gate = threading.Event()
        self.closed = False

    def read1(self, size: int) -> bytes:
        self.gate.wait(5)
        return b""

    def close(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(self, stdout, stderr, stdin=None) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.stdin = stdin


def check_process_io() -> int:
    source = _read(MODULE)
    tree = ast.parse(source)
    checked = _ordered(READ_ORDER, _method(tree, source, "_read"), "_read")
    checked += _ordered(RUN_ORDER, _method(tree, source, "_run"), "_run")
    checked += _ordered(WRITE_ORDER, _method(tree, source, "_write"), "_write")
    checked += _ordered(JOIN_ORDER, _method(tree, source, "join"), "join")
    checked += _ordered(ALIVE_ORDER, _method(tree, source, "alive"), "alive")
    checked += _ordered(CLOSE_ORDER, _method(tree, source, "close_unstarted"), "close_unstarted")
    init = _method(tree, source, "__init__")
    checked += _ordered((
        "CHUNK_BYTES = 64 * 1024",
    ), source, "CHUNK_BYTES")
    checked += _ordered((
        "self._remaining = 2 + (stdin is not None)",
        'threading.Thread(target=self._run, args=(self._read, process.stdout, self.stdout)',
        'threading.Thread(target=self._run, args=(self._read, process.stderr, self.stderr)',
        "self._threads.append(threading.Thread(target=self._run,",
        "args=(self._write, process.stdin, stdin)",
        "self._pipes = [process.stdout, process.stderr] + ([process.stdin] if stdin is not None else [])",
    ), init, "__init__")
    if BoundedProcessOutput.CHUNK_BYTES != 64 * 1024:
        raise ValueError(f"{MODULE} 的分块上限必须是 64 KiB")
    checked += 1
    # 行为：两条读取流聚合到各自缓冲，全部结束后 done 置位。
    stdout, stderr = _Recorder(b"out"), _Recorder(b"err")
    guard = BoundedProcessOutput(_FakeProcess(stdout, stderr), None, 1024)
    guard.start()
    joined = guard.join(2)
    checked += _expect((bytes(guard.stdout), bytes(guard.stderr), guard.overflow.is_set(),
                        guard.failed, guard.done.is_set(), joined, guard.alive()),
                       (b"out", b"err", False, False, True, True, False), "流聚合")
    # 行为：标准输入按 UTF-8 写入真实子进程并读回。
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    guard = BoundedProcessOutput(process, "你好", 1024)
    guard.start()
    joined = guard.join(5)
    try:
        process.wait(timeout=5)
        waited = True
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        waited = False
    checked += _expect((bytes(guard.stdout), guard.failed, joined, guard.done.is_set(), waited),
                       ("你好".encode("utf-8"), False, True, True, True), "标准输入往返")
    # 行为：跨块累计超过上限时停止读取，不写入超限块。
    guard = BoundedProcessOutput(_FakeProcess(_Recorder(b"x" * 80, chunk=30), _Recorder()), None, 50)
    guard.start()
    guard.join(2)
    checked += _expect((guard.overflow.is_set(), bytes(guard.stdout), len(guard.stdout) <= 50),
                       (True, b"x" * 30, True), "跨块溢出")
    guard = BoundedProcessOutput(_FakeProcess(_Recorder(b"x" * 80), _Recorder()), None, 50)
    guard.start()
    guard.join(2)
    checked += _expect((guard.overflow.is_set(), bytes(guard.stdout)), (True, b""), "单块溢出")
    # 行为：读取异常置 failed，其他流仍完成，done 只在线程全部结束后置位。
    guard = BoundedProcessOutput(_FakeProcess(_Recorder(error=OSError("broken")),
                                              _Recorder(b"ok")), None, 1024)
    guard.start()
    joined = guard.join(2)
    checked += _expect((guard.failed, bytes(guard.stdout), bytes(guard.stderr),
                        guard.done.is_set(), joined), (True, b"", b"ok", True, True), "读取失败")
    # 行为：标准输入写入后冲刷并关闭，断管被容忍且不标记失败。
    writer = _Writer()
    guard = BoundedProcessOutput(_FakeProcess(_Recorder(), _Recorder(), writer), "hi", 1024)
    guard.start()
    guard.join(2)
    checked += _expect((writer.data, writer.flushed, writer.closed, guard.failed),
                       (b"hi", True, True, False), "标准输入写入")
    writer = _BrokenWriter()
    guard = BoundedProcessOutput(_FakeProcess(_Recorder(), _Recorder(), writer), "hi", 1024)
    guard.start()
    guard.join(2)
    checked += _expect((guard.failed, writer.closed, guard.done.is_set()), (False, True, True),
                       "断管容忍")
    # 行为：join 有界等待，未停止时 alive 为真，释放后正常收尾。
    blocking = _Blocking()
    guard = BoundedProcessOutput(_FakeProcess(blocking, _Recorder()), None, 1024)
    guard.start()
    checked += _expect(guard.join(0.05), False, "有界等待")
    checked += _expect(guard.alive(), True, "超时仍存活")
    blocking.gate.set()
    checked += _expect(guard.join(5), True, "释放后收尾")
    checked += _expect((guard.alive(), guard.done.is_set(), blocking.closed),
                       (False, True, True), "收尾状态")
    # 行为：close_unstarted 只关闭未启动线程对应的管道。
    stdout, stderr, writer = _Recorder(), _Recorder(), _Writer()
    guard = BoundedProcessOutput(_FakeProcess(stdout, stderr, writer), "x", 1024)
    guard.close_unstarted()
    checked += _expect((stdout.closed, stderr.closed, writer.closed), (True, True, True),
                       "未启动关闭")
    return checked


def main() -> int:
    try:
        checked = check_process_io()
    except (ValueError, SyntaxError) as error:
        print(f"进程输出捕获核对失败，{error}", file=sys.stderr)
        return 2
    print(f"进程输出捕获一致：{checked} 项溢出、失败与收尾校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
