#!/usr/bin/env python3
"""用真实 stdio 内核核对畸形帧后的存活与有序退出。

`check_rpc.py` 在模块层核对解码和响应降级，`check_termination.py` 用真实进程核对
信号关闭；两者都不覆盖「一条坏帧之后同一进程还能否继续服务」。桌面与嵌入方共用
一个 stdio 内核进程，读取循环把坏帧误判成致命错误会让会话无预警断开。这里以临时
状态目录启动真实内核（`--provider none`），完成握手后逐条发送畸形帧：解析类错误
必须是 `-32700` / `id=null`，语义类错误保留请求 id，每种之后都能继续完成一次合法
`thread/list`；最后一条超过 8 MiB 的帧按设计回 `-32600` 并有序退出。全程不调用
模型、招聘平台或真实状态目录。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
DOC_FRAGMENT = "scripts/check_malformed_frames.py` 用真实 stdio 内核进程核对畸形帧后的存活"

#: 解析失败的帧：错误 id 必须为空，不能猜一个可能属于其他请求的编号。
PARSE_CASES: tuple[tuple[str, bytes], ...] = (
    ("截断的 JSON", b'{"jsonrpc":\n'),
    ("非法 UTF-8 字节", b'{"jsonrpc":"2.0","id":2,"method":"thread/list","params":{"a":"\xff"}}\n'),
    ("NaN 常量", b'{"jsonrpc":"2.0","id":3,"method":"thread/list","params":{"a":NaN}}\n'),
    ("重复键", b'{"jsonrpc":"2.0","id":4,"id":5,"method":"thread/list","params":{}}\n'),
    ("超过 64 层嵌套", b'{"jsonrpc":"2.0","id":6,"method":"thread/list","params":'
     + b"[" * 66 + b"0" + b"]" * 66 + b"}\n"),
    ("孤立代理项", b'{"jsonrpc":"2.0","id":7,"method":"thread/list","params":{"a":"\\ud800"}}\n'),
)

#: 可解析但语义非法的请求：错误必须关联原请求 id。
REQUEST_CASES: tuple[tuple[str, bytes, int, int], ...] = (
    ("未知方法", b'{"jsonrpc":"2.0","id":8,"method":"no/such","params":{}}\n', 8, -32601),
    ("params 非对象", b'{"jsonrpc":"2.0","id":9,"method":"thread/list","params":[1]}\n', 9, -32602),
)

OVERSIZED = b'{"jsonrpc":"2.0","id":10,"method":"thread/list","params":{"a":"' + b"x" * (8 * 1024 * 1024 + 16) + b'"}}\n'


class KernelProbe:
    """持有子进程、临时状态目录与已读出的 stdout 缓冲。"""

    def __init__(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="boss-harness-malformed-")
        state = Path(self.directory.name) / "state"
        env = os.environ.copy()
        env["BOSS_HARNESS_PROVIDER"] = "none"
        source = str(ROOT / "harness" / "src")
        env["PYTHONPATH"] = os.pathsep.join([source, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "boss_harness", "--provider", "none", "--state-dir", str(state)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        )
        self.buffer = b""

    def send(self, raw: bytes) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(raw)
        self.process.stdin.flush()

    def read(self, timeout: float = 20.0) -> dict:
        assert self.process.stdout is not None
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("内核没有在期限内回包")
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(self.process.stdout.fileno(), 64 * 1024)
            if not chunk:
                raise AssertionError("内核在回包前关闭了 stdout")
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        frame = json.loads(line.decode("utf-8"))
        if not isinstance(frame, dict):
            raise AssertionError("回包不是 JSON 对象")
        return frame

    def finish(self) -> tuple[int, str]:
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            code = self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            code = self.process.wait(timeout=20)
        assert self.process.stderr is not None
        stderr = self.process.stderr.read().decode("utf-8", "replace")
        self.directory.cleanup()
        return code, stderr


def _expect(condition: bool, label: str) -> int:
    if not condition:
        raise AssertionError(f"畸形帧存活核对失败：{label}")
    return 1


def _error(frame: dict, code: int, request_id: object, label: str) -> int:
    error = frame.get("error")
    checked = _expect(isinstance(error, dict) and "result" not in frame, f"{label} 只有错误帧")
    checked += _expect(error.get("code") == code, f"{label} 错误码为 {code}")
    checked += _expect(frame.get("id") == request_id, f"{label} 错误 id 为 {request_id!r}")
    return checked


def _alive(probe: KernelProbe, request_id: int, label: str) -> int:
    probe.send(f'{{"jsonrpc":"2.0","id":{request_id},"method":"thread/list","params":{{}}}}\n'.encode("ascii"))
    frame = probe.read()
    checked = _expect(frame.get("id") == request_id, f"{label} 后合法请求的 id")
    result = frame.get("result")
    checked += _expect(isinstance(result, dict) and result.get("threads") == [], f"{label} 后仍能读取会话")
    return checked


def check() -> int:
    docs = (ROOT / DOCS).read_text(encoding="utf-8")
    checked = _expect(DOC_FRAGMENT in docs, f"{DOCS} 需登记真实进程畸形帧核对")
    probe = KernelProbe()
    try:
        probe.send(b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":'
                   b'{"protocolVersion":"0.2.0","clientInfo":{"name":"malformed-probe","version":"1"},"capabilities":{}}}\n')
        initialized = probe.read()
        checked += _expect(initialized.get("id") == 1, "握手 id")
        result = initialized.get("result")
        checked += _expect(isinstance(result, dict) and result.get("protocolVersion") == "0.2.0",
                           "握手回执协议版本")
        probe.send(b'{"jsonrpc":"2.0","method":"initialized"}\n')
        for index, (label, raw) in enumerate(PARSE_CASES):
            probe.send(raw)
            checked += _error(probe.read(), -32700, None, label)
            checked += _alive(probe, 100 + index, label)
        for index, (label, raw, request_id, code) in enumerate(REQUEST_CASES):
            probe.send(raw)
            checked += _error(probe.read(), code, request_id, label)
            checked += _alive(probe, 200 + index, label)
        probe.send(OVERSIZED)
        checked += _error(probe.read(), -32600, None, "超过 8 MiB 的帧")
        code, stderr = probe.finish()
        checked += _expect(code == 0, "超长帧后有序退出")
        checked += _expect("Traceback" not in stderr and "Unhandled exception" not in stderr,
                           "超长帧后 stderr 没有回溯")
        return checked
    except BaseException:
        # 失败时也要回收进程与临时目录，避免探针把失败放大成悬挂的子进程。
        try:
            if probe.process.poll() is None:
                probe.process.kill()
            probe.process.wait(timeout=20)
            probe.directory.cleanup()
        except Exception:
            pass
        raise


def main() -> int:
    try:
        checked = check()
    except (AssertionError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 2
    print(f"畸形帧存活一致：{checked} 项协议错误与恢复校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
