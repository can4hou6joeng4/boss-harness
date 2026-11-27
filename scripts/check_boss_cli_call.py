#!/usr/bin/env python3
"""核对上游 CLI 子进程边界：取消、超时、输出上限、信封契约与暂停码投影。

`BossCliTool.call` 是领域工具唯一的进程边界：拼接 `--json` / `--data-dir` /
`--browser-source`，启动子进程并并发读取输出、写入 stdin，在取消、超时与
16 MiB 输出上限时终止进程组，然后校验 UTF-8、严格 JSON、七键信封与退出码，
最后把 `hr chat` 的摘要补取暂停码投影成失败。内核收到终止信号时置位的进程级
停止标记与取消事件走同一处判断：不再启动 CLI，在途调用按取消终止进程组。

这里在临时目录写入假 CLI 脚本，驱动真实 `BossCliTool.call`（不联网、不调用
真实 CLI），逐类验证进程生命周期与信封契约；静态部分锁定参数拼接、启动、
监督、收尾、解码、信封与暂停投影的关键分支。
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import os
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/tools/boss_cli.py"
#: 中途取消线程内部的 `probe.call` 上限是 30 秒；这里留出调度余量，
#: 超时先给出明确失败，不访问尚未写入的结果列表。
CANCEL_JOIN_SECONDS = 35.0
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.tools import boss_cli  # noqa: E402
from boss_harness.tools.boss_cli import BossCliTool  # noqa: E402

CLI_SCRIPT = '''#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time

mode = os.environ.get("PROBE_MODE", "")
marker = os.environ.get("PROBE_MARKER")
if marker:
    with open(marker, "a", encoding="utf-8") as handle:
        handle.write(" ".join(sys.argv[1:]) + "\\n")


def envelope(**overrides):
    value = {"ok": True, "schema_version": "1.0", "command": "status", "data": {},
             "pagination": None, "error": None, "hints": None}
    value.update(overrides)
    return value


if mode == "argv":
    stdin_text = ""
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read()
    print(json.dumps(envelope(data={"argv": sys.argv[1:], "stdin": stdin_text}),
                     ensure_ascii=False))
elif mode == "sleep":
    time.sleep(30)
elif mode == "overflow":
    sys.stdout.write("x" * (17 * 1024 * 1024))
    sys.stdout.flush()
elif mode == "empty":
    pass
elif mode == "binary":
    sys.stdout.buffer.write(b"\\xff\\xfe")
    sys.stdout.flush()
elif mode == "bad-json":
    print("not json")
elif mode == "strict":
    print('{"a": NaN}')
elif mode == "envelope":
    with open(os.environ["PROBE_ENVELOPE"], encoding="utf-8") as handle:
        sys.stdout.write(handle.read())
    sys.stdout.flush()
    exit_code = os.environ.get("PROBE_EXIT")
    if exit_code is not None:
        sys.exit(int(exit_code))
elif mode == "daemon":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    print(json.dumps(envelope()))
'''

ARGV = (
    '        argv = [self.binary, "--json"]',
    '            argv += ["--data-dir", self.data_dir]',
    '            argv += ["--browser-source", self.browser_source]',
    "        argv += list(args)",
)
CANCEL_START = (
    "        if self._stop_requested():",
    '            return failure("CANCELLED", "操作已停止，未启动 CLI")',
)
SPAWN = (
    "            proc = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,",
    "                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,",
    '                                    start_new_session=os.name == "posix", shell=False)',
    "        except OSError:",
    '            return failure("CLI_ERROR", "上游 CLI 不可执行，请检查 BOSS_CLI_BIN")',
    "        except ValueError:",
    '            return failure("CLI_ARGUMENT_ERROR", "工具参数无法作为命令行参数传递，CLI 未启动；本次操作未发出，请修正参数后重新发起新回合。")',
)
SUPERVISE = (
    "            output = BoundedProcessOutput(proc, stdin, MAX_CLI_OUTPUT_BYTES)",
    "            cancelled = self._stop_requested()",
    "            if cancelled or output.overflow.is_set() or output.failed or time.monotonic() >= deadline:",
    '                code = "CANCELLED" if cancelled else "TOOL_TIMEOUT"',
    '                return failure(code, "CLI 已停止；已发出的操作可能生效，请先核对平台状态，不要直接重试。")',
    "            if output.done.is_set() and proc.poll() is not None:",
    "                elif time.monotonic() - exited_at >= CHILD_EXIT_DRAIN_SECONDS:",
    "            output.overflow.wait(min(0.1, max(0.001, deadline - time.monotonic())))",
)
OUTPUT_LIMIT = (
    "        def output_limit_failure() -> ToolResult:",
    '            return failure("CLI_OUTPUT_LIMIT", f"CLI 标准输出与错误输出合计超过 {MAX_CLI_OUTPUT_BYTES} 字节，结果不完整，已停止；请先核对已发出的操作，不要自动重试。")',
    "        if output.overflow.is_set():",
    "            return output_limit_failure()",
)
DECODE = (
    '            stdout = output.stdout.decode("utf-8")',
    "        except UnicodeDecodeError:",
    '            return failure("CLI_ERROR", "CLI 输出不是有效 UTF-8")',
    "        if not stdout:",
    '                error={"code": "CLI_ERROR", "message": redact_secrets(stderr.strip()[:400]) or "无输出"},',
)
ENVELOPE = (
    "            envelope = _decode_cli_envelope(stdout)",
    "        except json.JSONDecodeError:",
    '            return failure("CLI_ERROR", "stdout 不是 JSON 信封")',
    "        except (ValueError, RecursionError):",
    '            return failure("CLI_CONTRACT_ERROR", "stdout 不是严格 JSON 信封，请核对上游版本")',
    '        keys = {"ok", "schema_version", "command", "data", "pagination", "error", "hints"}',
    '                or proc.returncode != (0 if envelope["ok"] else 1)',
    '                or (envelope["hints"] is not None and not isinstance(envelope["hints"], dict))',
    '                or (envelope["pagination"] is not None and not isinstance(envelope["pagination"], dict))',
    '                or (envelope["ok"] and envelope["error"] is not None)',
    '            return failure("CLI_CONTRACT_ERROR", "上游输出不符合 v1 七键信封或退出码契约，请核对上游版本")',
)
PAUSE = (
    '        if ok and args[:2] == ("hr", "chat") and envelope["command"] == "recruiter-chat":',
    '            code = summaries.get("last_messages_error_code") if type(summaries) is dict else None',
    "            if type(code) is str and code in PAUSE_CODES:",
    '                "recovery_action": "请先核对已取得结果，处理平台登录、验证或访问限制后，再明确发起后续任务；不要自动重试。",',
)
RESULT = (
    "        return ToolResult(",
    "            ok=ok,",
    "            raw=stdout,",
)
TERMINATE = (
    '                if os.name == "posix":',
    "                    os.killpg(proc.pid, sig)",
    "            proc.wait(timeout=0.5)",
    "        stop(signal.SIGKILL)",
)
PROBES = (
    ("argv", ARGV),
    ("cancel_start", CANCEL_START),
    ("spawn", SPAWN),
    ("supervise", SUPERVISE),
    ("output_limit", OUTPUT_LIMIT),
    ("decode", DECODE),
    ("envelope", ENVELOPE),
    ("pause", PAUSE),
    ("result", RESULT),
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _tree(relative: str) -> ast.Module:
    try:
        return ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BossCliTool":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"boss_cli.py 缺少 BossCliTool.{name}")


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"CLI 子进程行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _check_structures() -> int:
    source = _read(MODULE)
    tree = _tree(MODULE)
    body = _method(tree, source, "call")
    checked = 0
    for name, fragments in PROBES:
        for fragment in fragments:
            if fragment not in body:
                raise ValueError(f"BossCliTool.call 的 {name} 分支缺少：{fragment}")
            checked += 1
    terminate = _method(tree, source, "_terminate")
    for fragment in TERMINATE:
        if fragment not in terminate:
            raise ValueError(f"BossCliTool._terminate 缺少：{fragment}")
        checked += 1
    return checked


class _Probe:
    def __init__(self, directory: str) -> None:
        self.directory = Path(directory)
        self.script = self.directory / "boss"
        self.script.write_text(CLI_SCRIPT, encoding="utf-8")
        self.script.chmod(0o755)
        self.marker = self.directory / "marker"
        self.envelope_path = self.directory / "envelope.json"

    def tool(self, *, data_dir: str | None = None, browser_source: str | None = None) -> BossCliTool:
        env = {} if browser_source is None else {"BOSS_HARNESS_BROWSER_SOURCE": browser_source}
        with patch.dict(os.environ, env, clear=False):
            for name in ("BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR"):
                os.environ.pop(name, None)
            if browser_source is None:
                os.environ.pop("BOSS_HARNESS_BROWSER_SOURCE", None)
            return BossCliTool(binary=str(self.script), data_dir=data_dir)

    def call(self, tool: BossCliTool, mode: str, *, envelope: dict | None = None,
             exit_code: int | None = None, args: tuple = ("status",),
             timeout: int = 120, stdin: str | None = None):
        if envelope is not None:
            self.envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        env = {"PROBE_MODE": mode, "PROBE_MARKER": str(self.marker)}
        if envelope is not None:
            env["PROBE_ENVELOPE"] = str(self.envelope_path)
        if exit_code is not None:
            env["PROBE_EXIT"] = str(exit_code)
        with patch.dict(os.environ, env, clear=False):
            return tool.call(*args, timeout=timeout, stdin=stdin)

    def started(self) -> bool:
        return self.marker.exists()


def _envelope(**overrides) -> dict:
    value = {"ok": True, "schema_version": "1.0", "command": "status", "data": {},
             "pagination": None, "error": None, "hints": None}
    value.update(overrides)
    return value


def _argv_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool(data_dir="  /tmp/probe-dir  ")
    result = probe.call(tool, "argv")
    checked += _expect_value(result.ok, True, "合法信封成功")
    checked += _expect_value(result.data["argv"], ["--json", "--data-dir", "/tmp/probe-dir", "status"],
                             "数据目录参数拼接")
    tool = probe.tool(data_dir="   ")
    result = probe.call(tool, "argv")
    checked += _expect_value(result.data["argv"], ["--json", "status"], "空白数据目录不传递")
    tool = probe.tool(browser_source="existing-browser")
    result = probe.call(tool, "argv")
    checked += _expect_value(result.data["argv"], ["--json", "--browser-source", "existing-browser",
                                                   "status"], "浏览器来源参数拼接")
    tool = probe.tool()
    result = probe.call(tool, "argv", args=("status", "extra"), stdin="你好")
    checked += _expect_value(result.data["argv"], ["--json", "status", "extra"], "工具参数拼接")
    checked += _expect_value(result.data["stdin"], "你好", "stdin 写入子进程")
    return checked


def _cancel_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool()
    tool.cancel_event = threading.Event()
    tool.cancel_event.set()
    probe.marker.unlink(missing_ok=True)
    result = probe.call(tool, "argv")
    checked += _expect_value((result.ok, result.error["code"], result.error["message"]),
                             (False, "CANCELLED", "操作已停止，未启动 CLI"), "开始前取消")
    checked += _expect_value(probe.started(), False, "开始前取消未启动 CLI")

    tool = probe.tool()
    tool.cancel_event = threading.Event()
    outcome: list = []

    def run() -> None:
        outcome.append(probe.call(tool, "sleep", timeout=30))

    worker = threading.Thread(target=run)
    worker.start()
    time.sleep(0.5)
    tool.cancel_event.set()
    worker.join(timeout=CANCEL_JOIN_SECONDS)
    if worker.is_alive():
        raise ValueError(f"中途取消的 CLI 调用在 {CANCEL_JOIN_SECONDS:.0f} 秒内没有返回")
    result = outcome[0]
    checked += _expect_value((result.ok, result.error["code"]),
                             (False, "CANCELLED"), "中途取消")
    checked += _expect_value(result.error["message"],
                             "CLI 已停止；已发出的操作可能生效，请先核对平台状态，不要直接重试。",
                             "中途取消文案")

    started = time.monotonic()
    tool = probe.tool()
    result = probe.call(tool, "sleep", timeout=1)
    checked += _expect_value((result.ok, result.error["code"]), (False, "TOOL_TIMEOUT"),
                             "总时限收敛")
    checked += _expect_value(time.monotonic() - started < 10, True, "总时限及时返回")
    return checked


def _process_stop_checks(probe: _Probe) -> int:
    """内核停止时的进程级标记：不依赖调用方是否绑定了取消事件。"""
    checked = 0
    tool = probe.tool()
    probe.marker.unlink(missing_ok=True)
    with patch.object(boss_cli, "_process_stop_requested", True):
        result = probe.call(tool, "argv")
    error = result.error or {}
    checked += _expect_value((result.ok, error.get("code"), error.get("message"), probe.started()),
                             (False, "CANCELLED", "操作已停止，未启动 CLI", False), "内核停止后不启动 CLI")

    outcome: list = []

    def run() -> None:
        outcome.append(probe.call(tool, "sleep", timeout=8))

    # 标记是进程级的：用补丁保存并恢复，置位走真实入口，不留给后面的检查。
    with patch.object(boss_cli, "_process_stop_requested", False):
        worker = threading.Thread(target=run)
        worker.start()
        deadline = time.monotonic() + 5
        while not probe.started() and time.monotonic() < deadline:
            time.sleep(0.02)
        boss_cli.request_process_stop()
        worker.join(timeout=20)
    if not outcome:
        raise ValueError("CLI 子进程行为变化 内核停止时的在途调用：调用没有返回")
    error = outcome[0].error or {}
    checked += _expect_value((outcome[0].ok, error.get("code")), (False, "CANCELLED"),
                             "内核停止时终止没有取消事件的在途调用")
    return checked


def _output_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool()
    result = probe.call(tool, "overflow", timeout=30)
    checked += _expect_value((result.ok, result.error["code"]), (False, "CLI_OUTPUT_LIMIT"),
                             "输出上限")
    checked += _expect_value(result.error["message"].startswith("CLI 标准输出与错误输出合计超过"),
                             True, "输出上限文案")

    result = probe.call(tool, "binary")
    checked += _expect_value((result.error["code"], result.error["message"]),
                             ("CLI_ERROR", "CLI 输出不是有效 UTF-8"), "非 UTF-8 输出")

    result = probe.call(tool, "empty")
    checked += _expect_value((result.error["code"], result.error["message"]),
                             ("CLI_ERROR", "无输出"), "空输出")

    result = probe.call(tool, "bad-json")
    checked += _expect_value((result.error["code"], result.error["message"]),
                             ("CLI_ERROR", "stdout 不是 JSON 信封"), "坏 JSON")

    result = probe.call(tool, "strict")
    checked += _expect_value((result.error["code"], result.error["message"]),
                             ("CLI_CONTRACT_ERROR", "stdout 不是严格 JSON 信封，请核对上游版本"),
                             "严格 JSON 违约")

    tool = probe.tool()
    tool.binary = str(probe.directory / "missing-boss")
    result = probe.call(tool, "argv")
    checked += _expect_value((result.error["code"], result.error["message"]),
                             ("CLI_ERROR", "上游 CLI 不可执行，请检查 BOSS_CLI_BIN"), "不可执行二进制")
    return checked


def _envelope_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool()
    result = probe.call(tool, "envelope", envelope=_envelope(data={"x": 1}))
    checked += _expect_value((result.ok, result.data, result.command), (True, {"x": 1}, "status"),
                             "成功信封")
    checked += _expect_value(result.raw.startswith('{"ok": true'), True, "保留原始输出")

    failure = _envelope(ok=False, error={"code": "TOOL_ERROR", "message": "失败"})
    result = probe.call(tool, "envelope", envelope=failure, exit_code=1)
    checked += _expect_value((result.ok, result.error), (False, failure["error"]), "失败信封")

    contracts = (
        ("缺少信封键", _envelope(), None),
        ("多出信封键", _envelope(extra=True), None),
        ("版本不是 1.x", _envelope(schema_version="2.0"), None),
        ("成功退出码非零", _envelope(), 1),
        ("失败退出码为零", _envelope(ok=False, error={"code": "TOOL_ERROR", "message": "失败"}), 0),
        ("失败缺错误消息", _envelope(ok=False, error={"code": "TOOL_ERROR"}), 1),
        ("hints 不是对象", _envelope(hints=[]), None),
        ("pagination 不是对象", _envelope(pagination=[]), None),
        ("成功携带错误", _envelope(error={"code": "TOOL_ERROR", "message": "失败"}), None),
    )
    for label, envelope, exit_code in contracts:
        if label == "缺少信封键":
            envelope.pop("hints")
        result = probe.call(tool, "envelope", envelope=envelope, exit_code=exit_code)
        checked += _expect_value((result.error["code"], result.error["message"]),
                                 ("CLI_CONTRACT_ERROR",
                                  "上游输出不符合 v1 七键信封或退出码契约，请核对上游版本"), label)
    return checked


def _pause_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool()
    hints = {"summary_sources": {"last_messages_error_code": "RATE_LIMITED"}}
    result = probe.call(tool, "envelope", args=("hr", "chat"),
                        envelope=_envelope(command="recruiter-chat", hints=hints))
    checked += _expect_value(result.ok, False, "暂停码投影为失败")
    checked += _expect_value(result.error["code"], "RATE_LIMITED", "暂停码保留")
    checked += _expect_value(result.error["message"],
                             "已保留本页沟通列表的部分结果；最近消息补取未完成，平台要求暂停。",
                             "暂停文案")
    checked += _expect_value("recovery_action" in result.error, True, "暂停携带恢复建议")

    other = {"summary_sources": {"last_messages_error_code": "OTHER"}}
    result = probe.call(tool, "envelope", args=("hr", "chat"),
                        envelope=_envelope(command="recruiter-chat", hints=other))
    checked += _expect_value(result.ok, True, "非暂停码保持成功")

    result = probe.call(tool, "envelope", args=("hr", "chat"),
                        envelope=_envelope(command="status", hints=hints))
    checked += _expect_value(result.ok, True, "命令不匹配不投影")

    result = probe.call(tool, "envelope", args=("hr", "search"),
                        envelope=_envelope(command="recruiter-chat", hints=hints))
    checked += _expect_value(result.ok, True, "工具不匹配不投影")
    return checked


def _daemon_checks(probe: _Probe) -> int:
    checked = 0
    tool = probe.tool()
    result = probe.call(tool, "daemon", timeout=10)
    checked += _expect_value(result.ok, True, "后代持有管道不误报超时")
    return checked


def _behavior_checks() -> int:
    with tempfile.TemporaryDirectory() as directory:
        probe = _Probe(directory)
        checked = 0
        checked += _argv_checks(probe)
        checked += _cancel_checks(probe)
        checked += _process_stop_checks(probe)
        checked += _output_checks(probe)
        checked += _envelope_checks(probe)
        checked += _pause_checks(probe)
        checked += _daemon_checks(probe)
    return checked


def check_boss_cli_call() -> tuple[int, int]:
    return _check_structures(), _behavior_checks()


def main() -> int:
    try:
        structures, behaviors = check_boss_cli_call()
    except ValueError as error:
        print(f"CLI 子进程边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"CLI 子进程边界一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
