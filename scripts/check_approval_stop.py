#!/usr/bin/env python3
"""核对审批等待与工具运行中停止内核的真实进程行为。

`check_termination.py` 用 `--provider none` 启动内核，回合只会走到只读查询，触达不到
审批与工具桥的等待路径。这里把最小假 `anthropic` 模块放在 `PYTHONPATH` 上，让真实内核
（`--provider anthropic`）的第一回合返回一次 `boss_hr_greet` 调用，再由假招聘 CLI 顶替
真实二进制：模块用 `subprocess.Popen` 护栏只允许启动这个假 CLI，不联网、不调用模型。

两个场景都以 `SIGTERM` 结束内核，然后重启读同一会话：

- 审批等待中：已收到 `approval/requested`，假 CLI 从未启动；内核以该信号结束，
  stderr 只有一行关闭说明；重启后最后回合为 `interrupted`，工具项为
  `CANCELLED` / `not_executed`。
- 审批通过、假 CLI 启动后：内核以该信号结束，假 CLI 收到 `SIGTERM` 后消失；
  重启后工具项为 `CANCELLED` / `outcome_unknown`（调用可能已经生效）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "harness/src"
BRIDGE = "harness/src/boss_harness/tools/boss_cli.py"
ENTRY = "harness/src/boss_harness/__main__.py"
DOCS = "docs/TECHNICAL_REFERENCE.md"

# 内核通常在 0.05～0.25 秒内结束；上界只放宽调度抖动，不放宽失败。
# 全量检查套件里假 CLI 的启动曾被调度抖动拖过 10 秒；这里给足安静窗口，
# 超时信息会同时给出实测时长与进程状态，不把「等待不足」误报成工具桥故障。
KERNEL_EXIT_SECONDS = 3.0
CLI_GONE_SECONDS = 2.0
APPROVAL_TOOL_SECONDS = 30.0
APPROVAL_TOOL = "boss_hr_greet"
TOOL_INPUT = {key: "probe-" + key for key in
              ("geek_id", "job_id", "expect_id", "lid", "security_id", "message")}
FAKE_SDK = '''"""最小假 anthropic SDK：只供检查脚本在临时目录中使用，不联网。"""
import json
import os
import subprocess
from types import SimpleNamespace

STUB = os.path.realpath(os.environ.get("PROBE_STUB", "/nonexistent"))
CALLS = {"n": 0}

_popen_init = subprocess.Popen.__init__


def _guarded_init(self, args, *positional, **keywords):
    program = args[0] if isinstance(args, (list, tuple)) else args
    if os.path.realpath(str(program)) != STUB:
        raise OSError("approval-stop probe guard: refused to start %r" % (program,))
    return _popen_init(self, args, *positional, **keywords)


subprocess.Popen.__init__ = _guarded_init


class APIError(Exception):
    pass


class APIStatusError(APIError):
    pass


class APIConnectionError(APIError):
    pass


class RateLimitError(APIError):
    pass


omit = object()


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


def _tool_round():
    return [
        _ns(type="message_start", message=_ns(usage=_ns(input_tokens=40, output_tokens=0))),
        _ns(type="content_block_start", index=0,
            content_block=_ns(type="tool_use", id="call-1",
                              name=os.environ.get("PROBE_TOOL", "boss_status"),
                              input=json.loads(os.environ.get("PROBE_TOOL_INPUT", "{}")))),
        _ns(type="content_block_stop", index=0),
        _ns(type="message_delta", delta=_ns(stop_reason="tool_use"), usage=_ns(output_tokens=9)),
        _ns(type="message_stop"),
    ]


def _final_round(text="本回合完成"):
    return [
        _ns(type="message_start", message=_ns(usage=_ns(input_tokens=60, output_tokens=0))),
        _ns(type="content_block_start", index=0, content_block=_ns(type="text", text=text)),
        _ns(type="content_block_stop", index=0),
        _ns(type="message_delta", delta=_ns(stop_reason="end_turn"), usage=_ns(output_tokens=3)),
        _ns(type="message_stop"),
    ]


class _FakeStream:
    def __init__(self, events):
        self.events = list(events)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


class _FakeMessages:
    async def create(self, **kwargs):
        CALLS["n"] += 1
        if CALLS["n"] == 1 and kwargs.get("tools"):
            return _FakeStream(_tool_round())
        return _FakeStream(_final_round())


class _FakeAsyncAnthropic:
    def __init__(self, **kwargs):
        self.default_headers = {"x-api-key": "probe", "anthropic-version": "2023-06-01"}
        self.messages = _FakeMessages()
        self.beta = SimpleNamespace(messages=self.messages)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeAnthropic:
    def __init__(self, **kwargs):
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
        self.api_key = kwargs.get("api_key") or ""
        self.auth_token = kwargs.get("auth_token") or ""
        self.credentials = None
        self.default_headers = {"x-api-key": "probe", "anthropic-version": "2023-06-01"}

    def close(self):
        pass


Anthropic = _FakeAnthropic
AsyncAnthropic = _FakeAsyncAnthropic
'''
CLI_SCRIPT = """#!/bin/sh
exec 3>>"$PROBE_MARKER"
printf 'started %d\\n' $$ >&3
trap 'printf "term\\n" >&3; exit 143' TERM
i=0
while [ $i -lt 100 ]; do sleep 0.1; i=$((i + 1)); done
"""


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _check_structure() -> int:
    bridge = _read(BRIDGE)
    entry = _read(ENTRY)
    checked = 0
    for fragment in (
        "_process_stop_requested = False",
        "def request_process_stop() -> None:",
        "return _process_stop_requested or (self.cancel_event is not None and self.cancel_event.is_set())",
    ):
        if fragment not in bridge:
            raise ValueError(f"{BRIDGE} 缺少进程级停止标记片段：{fragment}")
        checked += 1
    for fragment in ("request_process_stop()", "self._server.request_stop()", "，已按关闭流程停止"):
        if fragment not in entry:
            raise ValueError(f"{ENTRY} 缺少终止信号片段：{fragment}")
        checked += 1
    # 工具桥的停止标记必须先置位，读取循环的打断放在最后：顺序颠倒会让执行中的调用
    # 看不到标记，工具桥只能在关闭期限里被强行留下。
    handler_at = entry.index("def _on_signal")
    flag_at = entry.index("request_process_stop()", handler_at)
    stop_at = entry.index("self._server.request_stop()", handler_at)
    if not flag_at < stop_at:
        raise ValueError(f"{ENTRY} 的 _on_signal 必须先置位工具桥停止标记、再打断读取")
    return checked + 1


class _Kernel:
    def __init__(self, folder: Path) -> None:
        self.stderr_path = folder / "kernel.stderr.log"
        self.stderr = open(self.stderr_path, "w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "boss_harness", "--state-dir", str(folder / "state")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            env=_kernel_env(folder), cwd=str(folder / "workspace"), start_new_session=True)
        self.frames: "queue.Queue[dict | None]" = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        while True:
            raw = self.process.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if line:
                try:
                    self.frames.put(json.loads(line))
                except ValueError:
                    continue
        self.frames.put(None)

    def send(self, frame: dict) -> None:
        self.process.stdin.write((json.dumps(frame, ensure_ascii=False) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _next(self, method: str, timeout: float) -> dict:
        try:
            message = self.frames.get(timeout=timeout)
        except queue.Empty:
            raise ValueError(f"内核在 {method} 期间没有回帧或通知") from None
        if message is None:
            tail = self.stderr_path.read_text(encoding="utf-8").strip()[-300:]
            raise ValueError(f"内核在 {method} 期间退出：{tail}")
        return message

    def call(self, method: str, params: dict | None = None, timeout: float = 20) -> dict:
        self.next_id += 1
        request_id = self.next_id
        frame = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            frame["params"] = params
        self.send(frame)
        deadline = time.monotonic() + timeout
        while True:
            message = self._next(method, max(0.01, deadline - time.monotonic()))
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise ValueError(f"{method} 失败：{message['error']}")
                return message["result"]

    def wait_notification(self, method: str, timeout: float = 15) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            message = self._next(method, max(0.01, deadline - time.monotonic()))
            if message.get("method") == method:
                return message

    def handshake(self) -> None:
        self.call("initialize", {"clientInfo": {"name": "approval-stop", "version": "1.0"},
                                 "protocolVersion": "0.2.0"})
        self.send({"jsonrpc": "2.0", "method": "initialized"})

    def diagnostics(self) -> list[str]:
        return [line for line in self.stderr_path.read_text(encoding="utf-8").splitlines()
                if not line.startswith("[harness] listening")]

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except OSError:
                self.process.kill()
            self.process.wait(timeout=5)
        self.stderr.close()


def _kernel_env(folder: Path) -> dict:
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(folder / "home"),
        "LANG": "en_US.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": os.pathsep.join((str(folder / "fake"), str(SOURCE))),
        "BOSS_HARNESS_PROVIDER": "anthropic",
        "BOSS_HARNESS_MODEL_RETRY_ATTEMPTS": "1",
        "ANTHROPIC_API_KEY": "probe-key-not-real",
        "ANTHROPIC_BASE_URL": "https://gateway.invalid",
        "BOSS_CLI_BIN": str(folder / "boss"),
        "BOSS_CLI_DATA_DIR": str(folder / "cli-data"),
        "PROBE_STUB": str(folder / "boss"),
        "PROBE_TOOL": APPROVAL_TOOL,
        "PROBE_TOOL_INPUT": json.dumps(TOOL_INPUT),
        "PROBE_MARKER": str(folder / "cli.marker"),
    }
    return environment


def _prepare(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("home", "workspace", "state", "cli-data", "fake"):
        (folder / name).mkdir(exist_ok=True)
    (folder / "fake" / "anthropic.py").write_text(FAKE_SDK, encoding="utf-8")
    cli = folder / "boss"
    cli.write_text(CLI_SCRIPT, encoding="utf-8")
    cli.chmod(0o755)


def _marker_rows(folder: Path) -> list[tuple[str, int]]:
    path = folder / "cli.marker"
    rows: list[tuple[str, int]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(" ")
        try:
            rows.append((key, int(value)))
        except ValueError:
            rows.append((key, 0))
    return rows


def _started_pids(folder: Path) -> list[int]:
    """标记文件先创建、再写入 started 行；只有有效进程号才算启动完成。"""
    return [pid for key, pid in _marker_rows(folder) if key == "started" and pid > 0]


def _wait_exit(process: subprocess.Popen, seconds: float) -> int | str:
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        return "仍未退出"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tool_items(read: dict) -> list[dict]:
    return [
        {key: item.get(key) for key in ("kind", "name", "status", "executionState", "errorCode")
         if item.get(key) is not None}
        for item in read.get("items", [])
        if "tool" in str(item.get("kind", "")).lower()
    ]


def _read_session(folder: Path, thread_id: str) -> dict:
    kernel = _Kernel(folder)
    try:
        kernel.handshake()
        return kernel.call("thread/read", {"threadId": thread_id})
    finally:
        if kernel.process.poll() is None:
            kernel.process.stdin.close()
            if _wait_exit(kernel.process, 10) == "仍未退出":
                kernel.stop()
                raise ValueError("重启后的内核没有在读到会话记录后结束")
        kernel.stderr.close()


def _pending_stop(folder: Path) -> int:
    kernel = _Kernel(folder)
    try:
        kernel.handshake()
        thread_id = kernel.call("thread/start", {})["thread"]["id"]
        kernel.call("turn/start", {"threadId": thread_id, "input": "查看状态"})
        approval = kernel.wait_notification("approval/requested")
        if not approval.get("params", {}).get("approvalId"):
            raise ValueError(f"审批请求缺少 approvalId：{approval}")
        # 未批准之前工具桥不得启动任何可执行文件。
        time.sleep(0.3)
        if (folder / "cli.marker").exists():
            raise ValueError("审批尚未作答，假招聘 CLI 已被启动")
        began = time.monotonic()
        kernel.process.send_signal(signal.SIGTERM)
        code = _wait_exit(kernel.process, KERNEL_EXIT_SECONDS)
        seconds = time.monotonic() - began
        if code != -signal.SIGTERM:
            raise ValueError(f"审批等待中收到 SIGTERM 后内核的结束方式不符：{code!r}")
        if seconds > KERNEL_EXIT_SECONDS:
            raise ValueError(f"审批等待中收到 SIGTERM 后内核没有及时结束：{seconds:.2f} 秒")
        diagnostics = kernel.diagnostics()
        if diagnostics != ["[harness] 收到 SIGTERM，已按关闭流程停止"]:
            raise ValueError(f"审批等待中停止的诊断行不符：{diagnostics}")
        events = folder / "state" / "events.jsonl"
        methods = []
        if events.exists():
            for line in events.read_bytes().splitlines():
                try:
                    methods.append(json.loads(line).get("method"))
                except ValueError:
                    continue
        if "turn/completed" not in methods:
            raise ValueError("审批等待中停止后会话日志缺少回合终态事件")
        read = _read_session(folder, thread_id)
        turns = read.get("turns") or []
        items = _tool_items(read)
        if (turns and turns[-1].get("status") == "interrupted"
                and items == [{"kind": "toolCall", "status": "failed",
                               "executionState": "not_executed", "errorCode": "CANCELLED"}]):
            return 5
        raise ValueError(f"审批等待中停止后的会话结算不符：turns={turns}、items={items}")
    finally:
        kernel.stop()


def _approved_stop(folder: Path) -> int:
    kernel = _Kernel(folder)
    marker = folder / "cli.marker"
    try:
        kernel.handshake()
        thread_id = kernel.call("thread/start", {})["thread"]["id"]
        kernel.call("turn/start", {"threadId": thread_id, "input": "查看状态"})
        approval = kernel.wait_notification("approval/requested")
        answer = kernel.call("approval/respond",
                             {"approvalId": approval["params"]["approvalId"], "approved": True})
        if answer.get("accepted") is not True:
            raise ValueError(f"审批没有被接受：{answer}")
        began = time.monotonic()
        deadline = began + APPROVAL_TOOL_SECONDS
        pids: list[int] = []
        while time.monotonic() < deadline and not pids:
            pids = _started_pids(folder)
            time.sleep(0.01)
        if not pids:
            rows = _marker_rows(folder)
            tail = kernel.stderr_path.read_text(encoding="utf-8").strip()[-300:]
            raise ValueError(
                f"审批通过后假招聘 CLI 未在 {APPROVAL_TOOL_SECONDS:.0f} 秒内启动"
                f"（实测 {time.monotonic() - began:.1f} 秒、标记存在={marker.exists()}、"
                f"标记行={rows}、内核存活={kernel.process.poll() is None}）：{tail}"
            )
        stub_pid = pids[0]
        time.sleep(0.3)
        began = time.monotonic()
        kernel.process.send_signal(signal.SIGTERM)
        code = _wait_exit(kernel.process, KERNEL_EXIT_SECONDS)
        seconds = time.monotonic() - began
        if code != -signal.SIGTERM or seconds > KERNEL_EXIT_SECONDS:
            raise ValueError(f"工具运行中收到 SIGTERM 后内核的结束方式不符：{code!r}、{seconds:.2f} 秒")
        deadline = time.monotonic() + CLI_GONE_SECONDS
        while time.monotonic() < deadline and _alive(stub_pid):
            time.sleep(0.01)
        if _alive(stub_pid):
            raise ValueError("工具运行中停止后假招聘 CLI 仍在运行")
        if "term" not in [key for key, _ in _marker_rows(folder)]:
            raise ValueError("假招聘 CLI 没有收到 SIGTERM")
        read = _read_session(folder, thread_id)
        turns = read.get("turns") or []
        items = _tool_items(read)
        if (turns and turns[-1].get("status") == "interrupted"
                and items == [{"kind": "toolCall", "status": "failed",
                               "executionState": "outcome_unknown", "errorCode": "CANCELLED"}]):
            return 3
        raise ValueError(f"工具运行中停止后的会话结算不符：turns={turns}、items={items}")
    finally:
        kernel.stop()
        for pid in _started_pids(folder):
            try:
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                pass


def _check_behaviors() -> int:
    checked = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        base = Path(directory)
        pending = base / "pending"
        approved = base / "approved"
        for folder in (pending, approved):
            _prepare(folder)
        checked += _pending_stop(pending)
        checked += _approved_stop(approved)
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    checked = 0
    for fragment in ("`check_approval_stop.py`", "审批等待中", "假 `anthropic`", "30 秒"):
        if fragment not in docs:
            raise ValueError(f"{DOCS} 缺少审批停止的说明：{fragment}")
        checked += 1
    return checked


def check_approval_stop() -> tuple[int, int, int]:
    return _check_structure(), _check_behaviors(), _check_documentation()


def main() -> int:
    try:
        structure, behaviors, documents = check_approval_stop()
    except ValueError as error:
        print(f"审批停止核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批等待与工具运行中的停止一致：{structure} 项结构、{behaviors} 项真实进程结果、{documents} 处文档口径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
