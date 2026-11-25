#!/usr/bin/env python3
"""核对终止信号的关闭路径：先完成关闭流程并终止在途的招聘 CLI，再以该信号的默认动作结束。

内核收到 SIGTERM、SIGHUP 或 SIGINT 时不再立即消失：信号处理器只置位标记并打断阻塞中的
读取，随后走与标准输入结束相同的关闭流程；招聘 CLI 在独立进程组中运行，由持有它的调用
线程终止。关闭完成后进程仍以该信号的默认动作结束，上级进程观察到的结束方式不变。

读取循环的可打断范围在进程内用替身输入核对：停止请求只打断读取本身，不打断正在执行的
请求处理，也不会因为落在核对与读取之间而丢失。其余场景启动真实的 stdio 内核进程
（`--provider none`，不联网、不调用模型或真实招聘 CLI），招聘 CLI 换成临时目录里的
shell 脚本：它经一条命名管道报告启动与收到的信号，管道读到结束即说明它的进程全部结束，
不靠等待时长推断。
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
import io
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "harness/src"
sys.path.insert(0, str(SOURCE))

from boss_harness import __main__ as entry  # noqa: E402
from boss_harness.protocol import PROTOCOL_VERSION  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402

TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
UPSTREAM = "UPSTREAM.md"
DOCUMENTS = (
    (TECHNICAL_REFERENCE, (
        "内核收到 `SIGTERM`、`SIGHUP` 或 `SIGINT` 时走与标准输入结束相同的关闭流程",
        "信号只打断阻塞中的读取，不打断正在执行的请求处理",
        "关闭完成后进程仍以该信号的默认动作结束",
        "启动时已被忽略的信号保持忽略",
        "信号到达 5 秒后关闭仍未完成时，进程由定时器信号（`SIGALRM`）的默认动作结束",
        "`SIGKILL` 无法处理",
        "空闲时收到 `SIGTERM`",
    )),
    (USER_GUIDE, (
        "用 `SIGTERM`、`SIGHUP` 或 `Ctrl+C` 停止内核时，内核先终止进行中的招聘 CLI 调用并写完会话记录，再结束进程",
        "`kill -9` 不经过这段流程",
    )),
    (UPSTREAM, (
        "packages/coding-agent/src/modes/rpc/rpc-mode.ts",
        "处理器只写标记并打断阻塞中的读取",
    )),
)
NOTICE = "[harness] 收到 {}，已按关闭流程停止"
REPLY_SECONDS = 20.0
EXIT_SECONDS = 15.0
CLI_SECONDS = 5.0
# 招聘 CLI 的替身：只向命名管道报告自己的状态。写入端由它和它的子进程持有，
# 读到结束就是这些进程已全部结束；最多运行约 20 秒，不会留下长期存活的进程。
# 先装好 SIGTERM 的处理再报告启动：检查读到启动行之后才发信号，每次终止都会被记到。
CLI_SCRIPT = """#!/bin/sh
exec 3>"$PROBE_PIPE"
trap 'printf "T\\n" >&3; [ "$PROBE_STUBBORN" = 1 ] || exit 143' TERM
printf 'S %s\\n' "$$" >&3
count=0
while [ "$count" -lt 200 ]; do
  sleep 0.1
  count=$((count + 1))
done
"""


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"终止信号行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_documents() -> int:
    checked = 0
    for relative, fragments in DOCUMENTS:
        try:
            text = (ROOT / relative).read_text(encoding="utf-8")
        except OSError:
            raise ValueError(f"无法读取 {relative}") from None
        for fragment in fragments:
            if fragment not in text:
                raise ValueError(f"{relative} 缺少终止信号口径：{fragment}")
            checked += 1
    return checked


# ---- 进程内：读取循环的可打断范围 ----

class _Input:
    """替身标准输入：第一次读取时先执行一个动作，再按顺序交出各帧，最后是输入结束。"""

    def __init__(self, frames: list[str], action=None) -> None:
        self._frames = list(frames)
        self._action = action
        self.reads = 0

    def readline(self, _limit: int = -1) -> str:
        self.reads += 1
        if self.reads == 1 and self._action is not None:
            self._action()
        return self._frames.pop(0) if self._frames else ""


class _StopBeforeMark(JsonRpcServer):
    """在读取标记置位之前请求停止：相当于信号恰好落在上一帧处理完与进入读取之间。"""

    def __setattr__(self, name: str, value) -> None:
        if name == "_reading" and value is True and not self._stop_requested:
            self.request_stop()
        super().__setattr__(name, value)


def _server(kind=JsonRpcServer) -> tuple[JsonRpcServer, io.StringIO]:
    server = kind()
    out = io.StringIO()
    server._out = out
    server.register("echo", lambda _params: {})
    return server, out


def _request(request_id: int, method: str = "echo") -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method}) + "\n"


def _replies(out: io.StringIO) -> list:
    return [json.loads(line).get("id") for line in out.getvalue().splitlines() if line]


def _serve(server: JsonRpcServer, source: _Input) -> str | None:
    """用替身输入跑完读取循环；返回逃出循环的异常类型名，正常返回时为 None。"""
    saved = sys.stdin
    sys.stdin = source
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as error:  # noqa: BLE001 - 打断读取用的异常不属于 Exception
        return type(error).__name__
    finally:
        sys.stdin = saved
    return None


def _outcome(action) -> str | None:
    """执行一个动作；返回它抛出的异常类型名，没有抛出时为 None。"""
    try:
        action()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as raised:  # noqa: BLE001
        return type(raised).__name__
    return None


def _read_loop_checks() -> int:
    checked = 0
    # 读取期间请求停止（信号处理器就运行在读取线程里）：读取被打断，循环按输入结束收尾。
    server, out = _server()
    source = _Input([_request(1)], server.request_stop)
    escaped = _serve(server, source)
    checked += _expect_value((escaped, server._closed, source.reads, _replies(out)), (None, True, 1, []),
                             "读取期间请求停止")

    # 请求处理期间请求停止：当前请求照常回包，循环在读取下一帧之前结束。
    server, out = _server()
    server.register("stop", lambda _params: server.request_stop() or {})
    source = _Input([_request(1, "stop"), _request(2)])
    escaped = _serve(server, source)
    checked += _expect_value((escaped, server._closed, source.reads, _replies(out)), (None, True, 1, [1]),
                             "请求处理期间请求停止")

    # 停止请求落在上一帧处理完与进入读取之间：先标记再核对，不会带着请求进入阻塞读取。
    server, out = _server(_StopBeforeMark)
    source = _Input([_request(1)])
    escaped = _serve(server, source)
    checked += _expect_value((escaped, server._closed, source.reads, _replies(out)), (None, True, 0, []),
                             "停止请求落在核对与读取之间")

    # 同一次读取里重复请求：只打断一次，随后的关闭流程不会再被打断。
    server, out = _server()
    raised: list = []
    source = _Input([], lambda: raised.extend(_outcome(server.request_stop) for _ in range(2)))
    escaped = _serve(server, source)
    checked += _expect_value((escaped, raised), (None, ["_ReadInterrupted", None]), "重复请求只打断一次")

    # 其他线程请求停止：不向调用线程抛异常，已经读到的帧照常处理后循环结束。
    server, out = _server()
    raised = []

    def from_other_thread() -> None:
        worker = threading.Thread(target=lambda: raised.append(_outcome(server.request_stop)))
        worker.start()
        worker.join()

    source = _Input([_request(1), _request(2)], from_other_thread)
    escaped = _serve(server, source)
    checked += _expect_value((escaped, raised, source.reads, _replies(out)), (None, [None], 1, [1]),
                             "其他线程请求停止")
    return checked


# ---- 进程内：处理器的安装与恢复 ----

@contextmanager
def _signal_settings(handlers: dict, blocked: tuple = ()):
    """临时换上一组信号设置，结束时还原；只在主线程使用。"""
    saved = {}
    mask = None
    try:
        for signum, handler in handlers.items():
            saved[signum] = signal.signal(signum, handler)
        if blocked:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
        yield
    finally:
        if mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        for signum, handler in saved.items():
            if handler is not None:
                signal.signal(signum, handler)


def _known_dispositions():
    """检查进程自己可能运行在忽略某些信号的环境里（后台作业、nohup）：先换成确定的设置，结束时还原。

    其余被忽略的信号（后台作业的 SIGQUIT、解释器自己忽略的 SIGPIPE 等）也临时恢复默认动作：
    内核不接管启动时已被忽略的信号，留着它们就看不出内核多接管了哪一种。
    """
    settings = {item: signal.SIG_DFL for item in signal.Signals
                if item not in (signal.SIGKILL, signal.SIGSTOP) and signal.getsignal(item) == signal.SIG_IGN}
    settings.update({signal.SIGTERM: signal.SIG_DFL, signal.SIGHUP: signal.SIG_DFL,
                     signal.SIGINT: signal.default_int_handler})
    return _signal_settings(settings)


def _reading_server() -> JsonRpcServer:
    """读取线程正停在读取里的服务端：此时请求停止会以异常打断读取。"""
    server = JsonRpcServer()
    server._reader, server._reading = threading.get_ident(), True
    return server


def _handled(termination) -> list[str]:
    return sorted(item.name for item in signal.Signals if signal.getsignal(item) == termination._on_signal)


def _handler_checks() -> int:
    checked = 0
    server = JsonRpcServer()
    checked += _expect_value(entry.TERMINATION_HARD_LIMIT_SECONDS, 5.0, "强制期限秒数")
    with _known_dispositions():
        before = {item: signal.getsignal(item) for item in signal.Signals}
        with entry._TerminationSignals(server) as termination:
            handled = _handled(termination)
        restored = {item: signal.getsignal(item) for item in signal.Signals} == before
        checked += _expect_value((handled, restored), (["SIGHUP", "SIGINT", "SIGTERM"], True),
                                 "接管三种终止信号，未收到信号时退出即恢复")

        # 收到过信号之后进程即将结束：处理器保留到最后，重复信号不会落回默认动作。
        termination = entry._TerminationSignals(server)
        with termination:
            termination.signum = int(signal.SIGTERM)
        checked += _expect_value(_handled(termination), ["SIGHUP", "SIGINT", "SIGTERM"],
                                 "收到过信号后保留处理器")

    # 只有主线程能安装处理器：在其他线程进入时保持原有行为，不抛异常。
    with _known_dispositions():
        outcome: list = []

        def enter() -> None:
            def run() -> None:
                with entry._TerminationSignals(server) as termination:
                    outcome.append(_handled(termination))
            outcome.append(_outcome(run))

        worker = threading.Thread(target=enter)
        worker.start()
        worker.join()
        checked += _expect_value(outcome, [[], None], "非主线程进入时不接管也不报错")

    # 其他平台没有这三种信号的同等语义，也没有可作强制期限的定时器信号：完全不接管。
    with _known_dispositions(), patch.object(os, "name", "nt"):
        with entry._TerminationSignals(server) as termination:
            handled = _handled(termination)
    checked += _expect_value(handled, [], "非 POSIX 平台不接管信号")

    # 打断读取的调用可能以异常返回，所以排在最后：此时停止标记与强制期限都已经就位。
    # 两者换成记录用的替身，检查进程自己不置位停止标记，也不启动定时器。
    reading = _reading_server()
    order: list[str] = []
    interrupt = reading.request_stop

    def stop_reading() -> None:
        order.append("打断读取")
        interrupt()

    reading.request_stop = stop_reading
    termination = entry._TerminationSignals(reading)
    with patch.object(entry, "request_process_stop", lambda: order.append("进程级停止标记")), \
            patch.object(entry._TerminationSignals, "_arm_hard_limit",
                         staticmethod(lambda: order.append("强制期限"))):
        raised = _outcome(lambda: termination._on_signal(int(signal.SIGTERM), None))
    checked += _expect_value((order, termination.signum, raised),
                             (["进程级停止标记", "强制期限", "打断读取"], int(signal.SIGTERM), "_ReadInterrupted"),
                             "处理器先置位停止标记与强制期限，最后才打断读取")

    # 另一个信号的处理器插在两步之间运行并打断读取时，先到的那次调用余下的步骤不再执行。
    # 这里让它插在最不利的位置——先到的调用正要设定期限、还没设定：后到的那次调用自己
    # 补齐停止标记与强制期限，结束方式仍由先到的信号决定。
    termination = entry._TerminationSignals(_reading_server())
    order = []
    nested: list = []

    def arm() -> None:
        if not nested:
            nested.append(True)
            termination._on_signal(int(signal.SIGHUP), None)
        order.append("强制期限")

    with patch.object(entry, "request_process_stop", lambda: order.append("进程级停止标记")), \
            patch.object(entry._TerminationSignals, "_arm_hard_limit", staticmethod(arm)):
        raised = _outcome(lambda: termination._on_signal(int(signal.SIGTERM), None))
    checked += _expect_value((order, termination.signum, raised),
                             (["进程级停止标记", "进程级停止标记", "强制期限"], int(signal.SIGTERM), "_ReadInterrupted"),
                             "处理器被另一个信号的处理器打断时仍设定强制期限")
    return checked


# ---- 真实进程 ----

class _Cli:
    """招聘 CLI 替身的观察端：读到启动行之后，管道读到结束就是它的进程已全部结束。"""

    def __init__(self, path: Path) -> None:
        os.mkfifo(path)
        self._fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self._buffer = b""
        self.pid: int | None = None
        self.signals = 0
        self.gone = False

    def _pump(self, done, seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        while not done():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            readable, _, _ = select.select([self._fd], [], [], min(remaining, 0.05))
            if not readable:
                continue
            try:
                chunk = os.read(self._fd, 4096)
            except BlockingIOError:
                continue
            if chunk:
                self._buffer += chunk
                while b"\n" in self._buffer:
                    line, _, self._buffer = self._buffer.partition(b"\n")
                    if line.startswith(b"S "):
                        self.pid = int(line[2:])
                    elif line == b"T":
                        self.signals += 1
            elif self.pid is None:
                # 还没有写入方打开管道：此时读到的结束不代表进程结束。
                time.sleep(0.01)
            else:
                self.gone = True
        return True

    def wait_started(self, seconds: float) -> bool:
        return self._pump(lambda: self.pid is not None, seconds)

    def wait_gone(self, seconds: float) -> bool:
        return self._pump(lambda: self.gone, seconds)

    def close(self) -> None:
        # 失败路径上可能留下仍在运行的替身：管道尚未读到结束说明进程号仍属于它。
        self._pump(lambda: self.gone, 0.05 if self.pid is not None else 0.3)
        if self.pid is not None and not self.gone:
            for stop in (os.killpg, os.kill):
                try:
                    stop(self.pid, signal.SIGKILL)
                except OSError:
                    pass
        os.close(self._fd)


class _Exit:
    """在后台等待内核结束并记下时刻，主线程可以同时驱动其他场景。"""

    def __init__(self, process: subprocess.Popen) -> None:
        self.code: int | None = None
        self.at: float | None = None
        self._thread = threading.Thread(target=self._wait, args=(process,), daemon=True)
        self._thread.start()

    def _wait(self, process: subprocess.Popen) -> None:
        code = process.wait()
        self.at = time.monotonic()
        self.code = code

    def join(self, seconds: float) -> int | None:
        self._thread.join(seconds)
        return self.code


class _Kernel:
    """真实的 stdio 内核进程；标准输出只在等待回包时按期限读取。"""

    def __init__(self, base: Path, *, stubborn: bool = False, ignored: tuple = (), blocked: tuple = ()) -> None:
        environment = {
            "PATH": "/usr/bin:/bin", "HOME": str(base / "home"), "PYTHONPATH": str(SOURCE),
            "PYTHONIOENCODING": "utf-8", "BOSS_CLI_BIN": str(base / "boss"),
            "BOSS_CLI_DATA_DIR": str(base / "cli-data"), "PROBE_PIPE": str(base / "cli.pipe"),
            "PROBE_STUBBORN": "1" if stubborn else "0",
        }
        if os.environ.get("PYTHONDONTWRITEBYTECODE"):
            environment["PYTHONDONTWRITEBYTECODE"] = os.environ["PYTHONDONTWRITEBYTECODE"]

        # 忽略与默认动作、信号屏蔽都随 fork 与 exec 继承：启动期间临时换上要让内核继承的
        # 设置，内核便从确定的状态开始，不受检查进程所处环境里的忽略设置影响。
        inherited = {signum: signal.SIG_IGN if signum in ignored else signal.SIG_DFL
                     for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGALRM)}
        self._log = base / f"stderr-{len(list(base.glob('stderr-*.log')))}.log"
        with open(self._log, "wb") as log, _signal_settings(inherited, blocked):
            self.process = subprocess.Popen(
                [sys.executable, "-m", "boss_harness", "--provider", "none", "--state-dir", str(base / "state")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, env=environment,
                cwd=str(base / "workspace"), start_new_session=True)
        self._out = self.process.stdout.fileno()
        self._buffer = b""
        self._next_id = 0

    def send(self, frame: dict) -> None:
        try:
            self.process.stdin.write((json.dumps(frame) + "\n").encode("utf-8"))
            self.process.stdin.flush()
        except OSError:
            raise ValueError(f"内核已结束，无法发送 {frame.get('method')}") from None

    def _fill(self, deadline: float, what: str) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError(f"内核没有在期限内回应 {what}")
        readable, _, _ = select.select([self._out], [], [], remaining)
        if readable:
            chunk = os.read(self._out, 4096)
            if not chunk:
                raise ValueError(f"内核在回应 {what} 之前结束")
            self._buffer += chunk

    def call(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        frame = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            frame["params"] = params
        self.send(frame)
        deadline = time.monotonic() + REPLY_SECONDS
        while True:
            while b"\n" not in self._buffer:
                self._fill(deadline, method)
            line, _, self._buffer = self._buffer.partition(b"\n")
            reply = json.loads(line)
            if reply.get("id") == self._next_id and "method" not in reply:
                if "error" in reply:
                    raise ValueError(f"内核拒绝了 {method}：{reply['error'].get('message')}")
                return reply["result"]

    def wait_partial(self, opening: bytes) -> None:
        """读到一帧尚未写完、以 opening 开头的回包为止：此时内核正停在这一帧的写出里。"""
        deadline = time.monotonic() + REPLY_SECONDS
        while True:
            while b"\n" in self._buffer:
                self._buffer = self._buffer.partition(b"\n")[2]
            if self._buffer.startswith(opening):
                return
            self._fill(deadline, "超长回包")

    def close_input(self) -> None:
        self.process.stdin.close()

    def wait(self, seconds: float) -> int | None:
        try:
            return self.process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return None

    def diagnostics(self) -> list[str]:
        """stderr 中启动行之外的内容。"""
        lines = self._log.read_text(encoding="utf-8", errors="replace").splitlines()
        return [line for line in lines if not line.startswith("[harness] listening on stdio")]

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        for stream in (self.process.stdin, self.process.stdout):
            try:
                stream.close()
            except OSError:
                pass


@contextmanager
def _session(*, stubborn: bool = False, ignored: tuple = (), blocked: tuple = ()):
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for name in ("home", "workspace", "cli-data"):
            (base / name).mkdir()
        script = base / "boss"
        script.write_text(CLI_SCRIPT, encoding="utf-8")
        script.chmod(0o755)
        cli = _Cli(base / "cli.pipe")
        kernel = _Kernel(base, stubborn=stubborn, ignored=ignored, blocked=blocked)
        try:
            yield base, kernel, cli
        finally:
            kernel.stop()
            cli.close()


def _handshake(kernel: _Kernel) -> None:
    kernel.call("initialize", {"clientInfo": {"name": "check", "version": "1"},
                               "protocolVersion": PROTOCOL_VERSION})
    kernel.send({"jsonrpc": "2.0", "method": "initialized"})


def _start_cli_call(kernel: _Kernel, cli: _Cli) -> str:
    """握手后经确定性路径发起一次只读的招聘 CLI 调用，等替身报告启动；返回会话标识。"""
    _handshake(kernel)
    thread_id = kernel.call("thread/start", {})["thread"]["id"]
    kernel.call("turn/start", {"threadId": thread_id, "input": "/status"})
    if not cli.wait_started(REPLY_SECONDS):
        raise ValueError("招聘 CLI 的替身没有被启动")
    return thread_id


def _stopped(kernel: _Kernel, cli: _Cli, code: int | None) -> dict:
    return {"结束方式": code, "stderr": kernel.diagnostics(),
            "招聘 CLI 已结束、收到的 SIGTERM 次数": (cli.wait_gone(CLI_SECONDS), cli.signals)}


def _expected(signum: signal.Signals) -> dict:
    return {"结束方式": -signum, "stderr": [NOTICE.format(signum.name)],
            "招聘 CLI 已结束、收到的 SIGTERM 次数": (True, 1)}


def _terminate_checks() -> int:
    """SIGTERM：关闭流程走完，在途调用结算为已取消，然后才以该信号结束。"""
    with _session() as (base, kernel, cli):
        thread_id = _start_cli_call(kernel, cli)
        kernel.process.send_signal(signal.SIGTERM)
        actual = _stopped(kernel, cli, kernel.wait(EXIT_SECONDS))
        restarted = _Kernel(base)
        try:
            _handshake(restarted)
            read = restarted.call("thread/read", {"threadId": thread_id})
            actual["重启后的工具条目"] = [(item.get("executionState"), item.get("errorCode"))
                                  for item in read["items"] if item.get("kind") == "toolCall"]
        except ValueError as error:
            # 前一个内核没有按预期结束时这里也读不到会话：连同其余结果一起报告。
            actual["重启后的工具条目"] = str(error)
        finally:
            restarted.stop()
        expected = dict(_expected(signal.SIGTERM), 重启后的工具条目=[("failed", "CANCELLED")])
        return _expect_value(actual, expected, "工具调用进行中收到 SIGTERM")


def _idle_checks() -> int:
    """没有在途回合时收到 SIGTERM：没有 CLI 可终止，仍走关闭流程并以该信号结束。"""
    with _session() as (_base, kernel, cli):
        _handshake(kernel)
        kernel.process.send_signal(signal.SIGTERM)
        actual = {"结束方式": kernel.wait(EXIT_SECONDS), "stderr": kernel.diagnostics(),
                  "假招聘 CLI 从未启动": (cli.gone, cli.signals)}
        expected = {"结束方式": -signal.SIGTERM, "stderr": [NOTICE.format("SIGTERM")],
                    "假招聘 CLI 从未启动": (False, 0)}
        return _expect_value(actual, expected, "空闲时收到 SIGTERM")


def _eofterm_checks() -> int:
    """结束标准输入后立刻收到 SIGTERM：两条关闭路径重合，在途 CLI 仍被终止。"""
    with _session() as (_base, kernel, cli):
        _start_cli_call(kernel, cli)
        kernel.close_input()
        try:
            kernel.process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            # 极快关闭时进程可能已经退出；让下面的断言按实际结束方式报告。
            pass
        return _expect_value(_stopped(kernel, cli, kernel.wait(EXIT_SECONDS)),
                             _expected(signal.SIGTERM), "结束标准输入后立即收到 SIGTERM")


def _interrupt_checks() -> int:
    """SIGINT：同一条关闭路径，不靠任意位置抛出的 KeyboardInterrupt，stderr 没有回溯。"""
    with _session() as (_base, kernel, cli):
        _start_cli_call(kernel, cli)
        kernel.process.send_signal(signal.SIGINT)
        return _expect_value(_stopped(kernel, cli, kernel.wait(EXIT_SECONDS)), _expected(signal.SIGINT),
                             "工具调用进行中收到 SIGINT")


def _repeated_checks() -> int:
    """招聘 CLI 不理会 SIGTERM 时关闭需要半秒以上：其间到达的第二个信号既不打断关闭，也不改变结束方式。"""
    with _session(stubborn=True) as (_base, kernel, cli):
        _start_cli_call(kernel, cli)
        kernel.process.send_signal(signal.SIGHUP)
        time.sleep(0.15)
        kernel.process.send_signal(signal.SIGTERM)
        return _expect_value(_stopped(kernel, cli, kernel.wait(EXIT_SECONDS)), _expected(signal.SIGHUP),
                             "关闭期间到达第二个信号")


def _ignored_checks() -> int:
    """启动时已被忽略的 SIGHUP（例如 nohup）保持忽略；结束标准输入的关闭路径不变。"""
    with _session(ignored=(signal.SIGHUP,)) as (_base, kernel, cli):
        thread_id = _start_cli_call(kernel, cli)
        kernel.process.send_signal(signal.SIGHUP)
        try:
            read = kernel.call("thread/read", {"threadId": thread_id})
            serving = (read["thread"]["id"] == thread_id, read.get("activeTurnId") is not None)
        except ValueError as error:
            # 内核被这个信号停掉时读不到会话：连同其余结果一起报告。
            serving = str(error)
        cli.wait_gone(0.05)
        checked = _expect_value(
            {"仍在应答、回合仍在进行": serving, "招聘 CLI 已结束、收到的 SIGTERM 次数": (cli.gone, cli.signals)},
            {"仍在应答、回合仍在进行": (True, True), "招聘 CLI 已结束、收到的 SIGTERM 次数": (False, 0)},
            "启动时已被忽略的 SIGHUP")
        kernel.close_input()
        checked += _expect_value(
            _stopped(kernel, cli, kernel.wait(EXIT_SECONDS)),
            {"结束方式": 0, "stderr": [], "招聘 CLI 已结束、收到的 SIGTERM 次数": (True, 1)},
            "结束标准输入")
        return checked


class _Wedged:
    """关闭无法开始的情形：主线程停在一帧写不出去的回包里，此时收到 SIGTERM。

    信号不打断正在执行的请求处理，所以读取循环不会结束；招聘 CLI 仍由调用线程按进程级
    停止标记终止，进程则在强制期限到达时由定时器信号的默认动作结束。这个内核启动时
    定时器信号既被忽略又被阻塞，期限仍然生效说明内核自己恢复了默认动作并解除了阻塞。
    等待期限的几秒里主线程继续驱动其他场景。
    """

    def __init__(self, stack) -> None:
        alarm = (signal.SIGALRM,)
        _base, self._kernel, self._cli = stack.enter_context(_session(ignored=alarm, blocked=alarm))

    def begin(self) -> int:
        kernel, cli = self._kernel, self._cli
        _start_cli_call(kernel, cli)
        # 回包带着请求里的 id：两兆字节的 id 让这一帧远大于管道容量，而这里不再读取它。
        kernel.send({"jsonrpc": "2.0", "id": "x" * (2 * 1024 * 1024), "method": "probe/wedge"})
        kernel.wait_partial(b'{"jsonrpc": "2.0", "id": "' + b"x" * 64)
        self._exit = _Exit(kernel.process)
        self._signalled = time.monotonic()
        kernel.process.send_signal(signal.SIGTERM)
        limit = entry.TERMINATION_HARD_LIMIT_SECONDS
        return _expect_value((cli.wait_gone(limit / 2), cli.signals), (True, 1),
                             "主线程无法开始关闭时仍终止在途的招聘 CLI")

    def finish(self) -> int:
        limit = entry.TERMINATION_HARD_LIMIT_SECONDS
        code = self._exit.join(max(0.0, self._signalled + limit + EXIT_SECONDS - time.monotonic()))
        elapsed = None if self._exit.at is None else self._exit.at - self._signalled
        # 定时器不会提前到期；上界留到两倍期限，只为容纳检查进程自己被调度得晚。
        on_time = elapsed is not None and limit - 0.5 <= elapsed < limit * 2
        return _expect_value(
            {"结束方式": code, "在强制期限到达时结束": on_time},
            {"结束方式": -signal.SIGALRM, "在强制期限到达时结束": True},
            "关闭无法完成时的强制期限" + ("" if elapsed is None else f"（信号后 {elapsed:.1f} 秒结束）"))


def _process_checks() -> int:
    checked = _terminate_checks()
    checked += _idle_checks()
    checked += _eofterm_checks()
    with ExitStack() as stack:
        wedged = _Wedged(stack)
        checked += wedged.begin()
        checked += _interrupt_checks()
        checked += _repeated_checks()
        checked += _ignored_checks()
        checked += wedged.finish()
    return checked


def check_termination() -> tuple[int, int, int]:
    documents = _check_documents()
    behaviors = _read_loop_checks() + _handler_checks()
    return behaviors, _process_checks(), documents


def main() -> int:
    try:
        behaviors, scenarios, documents = check_termination()
    except ValueError as error:
        print(f"终止信号路径核对失败，{error}", file=sys.stderr)
        return 2
    print(f"终止信号路径一致：{behaviors} 项进程内行为、{scenarios} 项真实进程结果、{documents} 处文档口径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
