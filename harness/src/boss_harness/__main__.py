"""CLI composition root for the independent recruitment app-server."""
from __future__ import annotations

import argparse
import os
import json
import signal
import select
import socket
import sys
from pathlib import Path
from typing import Any

from boss_harness import __version__
from boss_harness.application import ApplicationService as Harness, _approval_timeout
from boss_harness.models import DEFAULT_MODEL, ModelConfig, build_provider, resolve_config
from boss_harness.models.config_errors import ModelConfigError
from boss_harness.models.secret import redact_secrets
from boss_harness.rpc import JsonRpcServer, describe_failure
from boss_harness.tools.boss_cli import request_process_stop, resolve_browser_source_override

# 终止信号到达后留给关闭流程的最长时间。关闭自身共享两秒期限，这里只兜住卡死：
# 到期由定时器信号的系统默认动作结束进程，终止信号不会变成停不掉进程的请求。
TERMINATION_HARD_LIMIT_SECONDS = 5.0
_TERMINATION_SIGNALS = ("SIGTERM", "SIGHUP", "SIGINT")


class _SignalAwareStdin:
    """同时等 stdin 与信号唤醒字节，避免信号落到工作线程后主线程一直阻塞。"""

    def __init__(self, source: Any, wakeup: socket.socket) -> None:
        self.source = source
        self._fd = source.fileno()
        self._wakeup = wakeup
        self._buffer = bytearray()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.source, name)

    def readline(self, limit: int = -1) -> str:
        if limit == 0:
            return ""
        while True:
            newline = self._buffer.find(b"\n")
            end = newline + 1 if newline >= 0 else len(self._buffer)
            if limit > 0:
                end = min(end, limit)
            if newline >= 0 or (limit > 0 and len(self._buffer) >= limit):
                raw = bytes(self._buffer[:end])
                del self._buffer[:end]
                return raw.decode("utf-8", errors="surrogateescape")
            # 信号处理函数只在主线程执行。set_wakeup_fd 的字节在 C 层写入，
            # 即使信号落到工作线程也会使这里返回，从而运行待处理的 Python handler。
            ready, _, _ = select.select([self._fd, self._wakeup], [], [])
            if self._wakeup in ready:
                self._wakeup.recv(65536)
            if self._fd in ready:
                size = min(65536, limit - len(self._buffer)) if limit > 0 else 65536
                chunk = os.read(self._fd, size)
                if not chunk:
                    raw = bytes(self._buffer)
                    self._buffer.clear()
                    return raw.decode("utf-8", errors="surrogateescape")
                self._buffer.extend(chunk)


class _TerminationSignals:
    """终止信号与标准输入结束走同一套关闭流程，关闭完成后仍以该信号的默认动作结束。

    处理器运行在主线程任意两条字节码之间，所以只写标记、不取锁：置位进程级停止
    标记（不再启动上游 CLI，在途调用终止进程组）、设定强制期限，再请求读取循环停止。
    只有阻塞中的读取会被打断，正在执行的请求处理与已经开始的关闭不受影响。
    """

    def __init__(self, server: JsonRpcServer) -> None:
        self._server = server
        self._previous: dict[int, Any] = {}
        self._limit_armed = False
        self._input: _SignalAwareStdin | None = None
        self._wakeup: tuple[socket.socket, socket.socket] | None = None
        self._previous_wakeup_fd = -1
        self.signum: int | None = None

    def __enter__(self) -> "_TerminationSignals":
        if os.name != "posix":
            # 其他平台的信号投递方式不同，也没有可作强制期限的定时器信号：保持原有行为。
            return self
        for name in _TERMINATION_SIGNALS:
            signum = getattr(signal, name)
            try:
                previous = signal.getsignal(signum)
                # 启动时已被忽略的信号保持忽略（例如 nohup）；不是由 Python 安装的处理器
                # 无法原样恢复，同样不接管。
                if previous is None or previous == signal.SIG_IGN:
                    continue
                signal.signal(signum, self._on_signal)
            except (OSError, ValueError):
                # 只有主线程能安装处理器；嵌入到其他线程运行时保持系统默认行为。
                continue
            self._previous[int(signum)] = previous
        if self._previous:
            self._install_input_wakeup()
        return self

    def _install_input_wakeup(self) -> None:
        reader: socket.socket | None = None
        writer: socket.socket | None = None
        try:
            reader, writer = socket.socketpair()
            reader.setblocking(False)
            writer.setblocking(False)
            source = _SignalAwareStdin(sys.stdin, reader)
            previous_fd = signal.set_wakeup_fd(writer.fileno(), warn_on_full_buffer=False)
        except (AttributeError, OSError, TypeError, ValueError):
            # 注入的内存输入没有 fileno；非主线程也不允许设置信号唤醒 fd。
            for endpoint in (reader, writer):
                if endpoint is not None:
                    endpoint.close()
            return
        self._previous_wakeup_fd = previous_fd
        self._wakeup = (reader, writer)
        self._input = source
        sys.stdin = source

    def __exit__(self, *_exc_info: object) -> None:
        if self._wakeup is not None:
            signal.set_wakeup_fd(self._previous_wakeup_fd)
            if sys.stdin is self._input:
                sys.stdin = self._input.source
            for endpoint in self._wakeup:
                endpoint.close()
            self._wakeup = None
            self._input = None
        # 收到过信号时进程即将结束：保留处理器，重复信号继续被吸收而不是打断收尾。
        if self.signum is not None:
            return
        for signum, previous in self._previous.items():
            try:
                signal.signal(signum, previous)
            except (OSError, ValueError):
                pass
        self._previous.clear()

    def _on_signal(self, signum: int, _frame: object) -> None:
        # 每一步都可以重复执行，不以「是否第一个信号」整体把关：另一个信号的处理器可能
        # 插在这里任意两步之间运行，它末尾的异常会让本次调用余下的步骤不再执行。
        if self.signum is None:
            self.signum = signum
        request_process_stop()
        if not self._limit_armed:
            # 先设定再记账：被打断时宁可重设一次，也不能留下没有期限的关闭。
            self._arm_hard_limit()
            self._limit_armed = True
        # 放在最后：它可能以异常打断阻塞中的读取。
        self._server.request_stop()

    @staticmethod
    def _arm_hard_limit() -> None:
        # 定时器信号恢复为系统默认动作并解除阻塞，由操作系统直接结束进程，不依赖主线程
        # 回到解释器；启动环境留下的忽略或阻塞设置不会让期限失效。
        try:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
            signal.setitimer(signal.ITIMER_REAL, TERMINATION_HARD_LIMIT_SECONDS)
        except (OSError, ValueError):
            pass

    def conclude(self) -> int:
        """关闭流程结束后调用：没有收到信号时返回 0，否则以该信号的默认动作结束进程。"""
        signum = self.signum
        if signum is None:
            return 0
        try:
            print(f"[harness] 收到 {signal.Signals(signum).name}，已按关闭流程停止", file=sys.stderr, flush=True)
        except (OSError, ValueError):
            # 终端挂断后 stderr 可能已不可写；诊断行丢失不影响结束方式。
            pass
        # 上级进程看到的结束方式与信号未被处理时相同；默认动作不经过解释器收尾。
        try:
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
        except (OSError, ValueError):
            pass
        return 128 + signum


def _failure_text(exc: Exception) -> str:
    """stderr 常被原样贴进 Issue：本地文件错误不带路径，其余文本抹掉凭据形态。"""
    return redact_secrets(describe_failure(exc))


def _default_state_dir() -> Path:
    """内核状态目录：新变量优先，旧变量其次，最后按目录存在性选择默认位置。

    只有空白的取值视为未设置，继续回退下一个来源：否则它会变成名字是空白的相对
    路径，入口的空值校验再以退出码 2 结束，提示却点名用户没有设置的 `--state-dir`。
    """
    for name in ("BOSS_HARNESS_DIR", "BOSS_CLI_HARNESS_DIR"):
        value = os.environ.get(name) or ""
        if value.strip():
            return Path(value)
    preferred = Path.home() / ".boss-harness" / "harness"
    legacy = Path.home() / ".boss-cli" / "harness"
    # 升级后不丢历史会话：新目录尚未建立、而旧目录已存在时沿用旧目录；否则用新路径。
    return legacy if legacy.exists() and not preferred.exists() else preferred


DEFAULT_STATE_DIR = _default_state_dir()


def _build_config(args: argparse.Namespace) -> ModelConfig:
    """命令行 > 环境变量；`--provider none` 可强制不调用模型（仍可调用招聘 CLI）。

    provider 交给 `resolve_config` 一起决定，不能解析完再 `replace`：模型配置的字段会随
    provider 增加，而各线路的端点与凭据来源不同，事后替换会让 `--provider openai` 拿到
    Anthropic 的端点并丢掉 Codex 配置里的凭据。
    `--model` 也先参与解析，使完整显式线路无需读取本地配置。
    """
    explicit = None if args.provider == "auto" else args.provider
    return resolve_config(provider=explicit, model_override=args.model)


def _requested_provider(args: argparse.Namespace) -> str:
    """用户点名的 provider：命令行优先，其次环境变量，未指定时为空串。

    归一化与 `resolve_config` 一致。启动自检与正式启动共用这一个判断，
    「显式 none」的自检结论（`MODEL_DISABLED`）和内核的实际开关才不会各说各话。
    """
    raw = args.provider if args.provider != "auto" else os.environ.get("BOSS_HARNESS_PROVIDER", "")
    normalized = raw.strip().lower()
    return "" if normalized == "auto" else normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="boss-harness", description="BOSS Harness Agent Harness 内核")
    parser.add_argument("--listen", default="stdio://", help="传输端点，当前仅支持 stdio://")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="内核状态目录")
    maintenance = parser.add_mutually_exclusive_group()
    maintenance.add_argument("--repair-state", action="store_true", help="独占状态目录，备份 SQLite 索引后从原始日志重建")
    maintenance.add_argument("--check", action="store_true", help="只读检查本地启动配置，输出脱敏报告（默认 JSON），不联网、不执行业务 CLI")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="--check 的输出格式：json（默认，供程序解析）或 text（终端可读）")
    parser.add_argument("--strict", action="store_true",
                        help="与 --check 一起使用：没有错误但存在警告时返回退出码 1")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "anthropic", "openai", "codex", "none"],
        help="模型供应商；openai 与其别名 codex 走 Responses 线路（显式 BOSS_HARNESS_OPENAI_* 或 Codex 配置），"
             "none 表示整个进程不调用模型、回合走确定性路径（仍可调用招聘 CLI）",
    )
    parser.add_argument("--model", default=None, help=f"模型 id，默认 {DEFAULT_MODEL}")
    parser.add_argument("--version", action="version", version=f"boss-harness {__version__}")
    args = parser.parse_args(argv)

    if args.format != "json" and not args.check:
        parser.error("--format 只能与 --check 一起使用")
    if args.strict and not args.check:
        parser.error("--strict 只能与 --check 一起使用")
    # 空值多半来自脚本里未设置的变量：按字面解析会把状态文件写进当前工作目录，所有模式都先拒绝。
    if not args.state_dir.strip():
        print("[harness] --state-dir 不能为空；省略该参数即使用默认状态目录", file=sys.stderr)
        return 2
    # 端点对所有模式都是前提：自检与索引修复也不应在参数无效时继续，否则自检通过而启动必然失败。
    if args.listen != "stdio://":
        print("[harness] 暂不支持该 --listen 端点；当前仅支持 stdio://", file=sys.stderr)
        return 2

    if args.check:
        from boss_harness.startup_check import render_text, startup_report
        report = startup_report(lambda: _build_config(args), state_dir=Path(args.state_dir),
                                requested_provider=_requested_provider(args), requested_model=args.model)
        print(render_text(report) if args.format == "text" else json.dumps(report, ensure_ascii=False))
        if not report["ok"]:
            return 2
        warned = any(check["status"] == "warning" for check in report["checks"])
        return 1 if args.strict and warned else 0

    if args.repair_state:
        from boss_harness.maintenance import repair_index
        try:
            print(json.dumps(repair_index(Path(args.state_dir)), ensure_ascii=False))
            return 0
        except Exception as exc:
            print(f"[harness] 索引修复失败：{_failure_text(exc)}", file=sys.stderr)
            return 2

    try:
        config = _build_config(args)
        provider = build_provider(config)
    except ModelConfigError as exc:
        print(f"[harness] 模型配置不可用（{exc.code}）：{exc}", file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        # 模型 SDK 是内核依赖：缺包不是配置错误，直接给出仓库已有的安装命令。
        print(f"[harness] 缺少内核运行依赖（{exc.name or '未知模块'}）；先按安装步骤安装内核依赖："
              "uv pip install --python .venv/bin/python -e ./harness", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        # 这里只包住「配置解析 + 构造 provider」两件事，所以宽捕获是安全的：任何失败都意味着
        # 模型线路起不来（缺凭据、缺端点、SDK 拒绝无凭据构造等），应当给出可读信息并以 2 退出。
        print(f"[harness] 模型配置不可用（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        return 2
    # 浏览器来源同样是进程级配置：在入口处校验，错误才能点名变量与可选值。留到工具桥
    # 构造时才失败会被 `_new_bridge` 统一包装成「工具桥工厂无法创建实例」，用户无从排查。
    try:
        resolve_browser_source_override()
    except ValueError as exc:
        print(f"[harness] 浏览器来源配置不可用（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        return 2
    server = JsonRpcServer()
    # 显式 none 是进程级开关：不列出其他线路、不解析摘要线路，整个进程不构造模型传输。
    # 未指定 provider 而自动回退得到的 none 只是没有默认线路，其他已配置线路照常可选。
    model_calls_disabled = _requested_provider(args) == "none"
    try:
        # 构造 Harness 会创建会话目录；state-dir 不可写同样是启动期的配置问题，应当走同一个干净
        # 退出码，而不是把回溯打到 stdout（stdout 只走协议）并以 1 结束。
        harness = Harness(server, Path(args.state_dir), config, provider, provider_factory=build_provider,
                          model_calls_disabled=model_calls_disabled)
    except (OSError, ValueError) as exc:
        print(f"[harness] 启动失败（{type(exc).__name__}）：{_failure_text(exc)}", file=sys.stderr)
        # 固定文字，不带路径或取值：自检不联网、不写入，能把同一条件映射为检查码与处理建议。
        print("[harness] 可用相同参数与环境运行 boss-harness --check，查看本地条件的检查码与处理建议。",
              file=sys.stderr)
        return 2
    bridge = harness.tools
    print(
        f"[harness] listening on stdio, state={args.state_dir}, "
        f"boss binary={bridge.binary} (source={bridge.source}, available={bridge.available()}), "
        f"model provider={harness.config.provider} model={harness.config.model} driven={harness.provider is not None} "
        f"model_calls_disabled={harness.model_calls_disabled}",
        file=sys.stderr,
    )
    termination = _TerminationSignals(server)
    with termination:
        harness.serve_forever()
    return termination.conclude()


if __name__ == "__main__":
    raise SystemExit(main())
