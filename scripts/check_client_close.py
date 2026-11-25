#!/usr/bin/env python3
"""核对桌面端断开内核时的关闭升级时序（真实内核进程）。

`packages/app-client` 的 `HarnessClient.dispose()` 先结束标准输入，2.5 秒后发
`SIGTERM`，再过 1 秒发 `SIGKILL`。这里用真实的内核进程与假招聘 CLI 走一遍：
正常关闭在内核自己的关闭流程里完成，假 CLI 被终止；内核不理会 `SIGTERM` 时
按两个期限依次升级，最终由 `SIGKILL` 收尾；内核已自行退出时关闭立即完成。
任何一步顺序或期限改变都会让外壳卡在等不到进程退出的状态。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CLIENT = "packages/app-client/src/index.ts"
SOURCE = ROOT / "harness/src"
DOCS = "docs/TECHNICAL_REFERENCE.md"

# 关闭卡住时的期限由客户端常量决定；网络与调度抖动只放宽上界，不放宽下界。
GRACEFUL_SECONDS = 2.5
FORCE_SECONDS = 1.0
CLOSE_UPPER_MS = 5_200
CLI_SCRIPT = """#!/bin/sh
exec 3>>"$PROBE_MARKER"
printf 'started\\n' >&3
trap 'printf "term\\n" >&3; exit 143' TERM
i=0
while [ $i -lt 200 ]; do sleep 0.1; i=$((i + 1)); done
"""
STUBBORN_KERNEL = """import signal
import sys
import time
marker = sys.argv[1]
def note(text):
    with open(marker, "a") as handle:
        handle.write("%s %.3f\\n" % (text, time.time()))
note("started")
def term(signum, frame):
    note("term")
signal.signal(signal.SIGTERM, term)
while True:
    time.sleep(0.05)
"""
EXITED_KERNEL = """import sys
import time
with open(sys.argv[1], "a") as handle:
    handle.write("started %.3f\\n" % time.time())
time.sleep(0.3)
"""
NODE_DRIVER = """\
import { readFileSync } from "node:fs";
import { HarnessClient } from "./index.ts";

const scenario = process.env.SCENARIO ?? "";
const marker = process.env.MARKER ?? "";
const client = new HarnessClient({
  command: process.env.KERNEL_COMMAND ?? "",
  args: JSON.parse(process.env.KERNEL_ARGS ?? "[]"),
  cwd: process.env.KERNEL_CWD,
  env: JSON.parse(process.env.KERNEL_ENV ?? "{}"),
  onDiagnostic: (message) => { diagnostics.push(message); },
});
const messages: string[] = [];
const diagnostics: string[] = [];
client.on("harness/disconnected", (params) => {
  const message = (params as { message?: unknown } | null)?.message;
  messages.push(typeof message === "string" ? message : "");
});
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
async function waitForMarker(timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      if (readFileSync(marker, "utf8").includes("started")) return true;
    } catch {}
    await sleep(20);
  }
  return false;
}
const out: Record<string, unknown> = { scenario };
try {
  client.start();
  if (scenario === "normal") {
    await client.request("initialize", { clientInfo: { name: "close-probe", version: "1.0" }, protocolVersion: "0.2.0" });
    client.notify("initialized");
    const thread = await client.request<{ thread: { id: string } }>("thread/start", {});
    await client.request("turn/start", { threadId: thread.thread.id, input: "/status" });
    out.cliStarted = await waitForMarker(10_000);
  } else {
    out.cliStarted = await waitForMarker(10_000);
  }
  if (scenario === "exited") await sleep(400);
  out.disposeEpoch = Date.now() / 1000;
  const began = performance.now();
  client.dispose();
  await client.waitForClose();
  out.closeMs = Math.round(performance.now() - began);
} catch (error) {
  out.error = String((error as Error)?.message ?? error);
}
out.messages = messages;
out.diagnostics = diagnostics;
process.stdout.write(JSON.stringify(out) + "\\n", () => process.exit(0));
"""


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _check_structure() -> int:
    source = _read(CLIENT)
    checked = 0
    for fragment in (
        'this.#diagnostic("harness did not stop after SIGTERM; sent SIGKILL");',
        '            child.kill("SIGKILL");',
        "if (child.exitCode === null && child.signalCode === null) {",
        "const GRACEFUL_CLOSE_TIMEOUT_MS = 2_500;",
        "const FORCE_KILL_TIMEOUT_MS = 1_000;",
    ):
        if fragment not in source:
            raise ValueError(f"{CLIENT} 缺少关闭升级片段：{fragment}")
        checked += 1
    # 结束标准输入在前，信号升级在后；SIGKILL 只在 SIGTERM 之后、且进程仍未退出时发送。
    end_at = source.index("child.stdin.end();")
    term_at = source.index('child.kill("SIGTERM");')
    kill_at = source.index('child.kill("SIGKILL");')
    guard_at = source.index("if (child.exitCode === null && child.signalCode === null)")
    if not end_at < term_at < guard_at < kill_at:
        raise ValueError(f"{CLIENT} 的关闭顺序必须是先结束标准输入、再 SIGTERM、最后 SIGKILL")
    if "child.kill(\"SIGKILL\");" in source.split("child.stdin.end();", 1)[0]:
        raise ValueError(f"{CLIENT} 不得在结束标准输入之前发送 SIGKILL")
    return checked + 2


def _marker_lines(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, stamp = line.partition(" ")
        rows.append((key, float(stamp) if stamp else 0.0))
    return rows


def _run_scenario(folder: Path, scenario: str, kernel: list[str], kernel_env: dict, marker: Path) -> dict:
    node_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(folder / "home"),
        "TMPDIR": str(folder),
        "SCENARIO": scenario,
        "MARKER": str(marker),
        "KERNEL_COMMAND": kernel[0],
        "KERNEL_ARGS": json.dumps(kernel[1:]),
        "KERNEL_ENV": json.dumps(kernel_env),
        "KERNEL_CWD": str(folder / "workspace"),
    }
    (folder / "workspace").mkdir(exist_ok=True)
    (folder / "home").mkdir(exist_ok=True)
    try:
        result = subprocess.run(["node", str(folder / "driver.ts")], capture_output=True, text=True,
                                timeout=30, env=node_env, cwd=str(folder))
    except subprocess.TimeoutExpired:
        raise ValueError(f"客户端关闭驱动超时（{scenario}）") from None
    if result.returncode != 0:
        raise ValueError(f"客户端关闭驱动失败（{scenario}）：{(result.stderr or result.stdout).strip()[:400]}")
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise ValueError(f"客户端关闭驱动没有输出结果（{scenario}）：{result.stdout.strip()[:200]}")
    return json.loads(lines[-1])


def _kernel_env(folder: Path, cli: Path) -> dict:
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(folder / "home"),
        "PYTHONPATH": str(SOURCE),
        "PYTHONIOENCODING": "utf-8",
        "BOSS_HARNESS_PROVIDER": "none",
        "BOSS_CLI_BIN": str(cli),
        "BOSS_CLI_DATA_DIR": str(folder / "cli-data"),
        "PROBE_MARKER": str(folder / "cli.marker"),
    }
    if os.environ.get("PYTHONDONTWRITEBYTECODE"):
        environment["PYTHONDONTWRITEBYTECODE"] = os.environ["PYTHONDONTWRITEBYTECODE"]
    return environment


def _check_behaviors() -> int:
    checked = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        folder = Path(directory)
        source = _read(CLIENT)
        # 只驱动 HarnessClient：去掉对 host.ts 的再导出，其余源码原样使用。
        for line in ('export { HarnessHostConnection, HarnessHostManager } from "./host";\n',
                     'export type { HarnessConnectionState, HarnessConnectionStatus, HarnessHostOptions } from "./host";\n'):
            source = source.replace(line, "")
        (folder / "index.ts").write_text(source, encoding="utf-8")
        (folder / "driver.ts").write_text(NODE_DRIVER, encoding="utf-8")
        cli = folder / "boss"
        cli.write_text(CLI_SCRIPT, encoding="utf-8")
        cli.chmod(0o755)
        (folder / "cli-data").mkdir(exist_ok=True)

        # 1. 真实内核：结束标准输入后内核自己关闭，假 CLI 被终止。
        marker = folder / "cli.marker"
        result = _run_scenario(
            folder, "normal",
            [sys.executable, "-m", "boss_harness", "--provider", "none", "--state-dir", str(folder / "state")],
            _kernel_env(folder, cli), marker)
        cli_rows = [key for key, _ in _marker_lines(marker)]
        message = (result.get("messages") or [""])[0]
        if result.get("cliStarted") is not True or "term" not in cli_rows:
            raise ValueError(f"客户端正常关闭：假招聘 CLI 没有被启动或没有被终止（{cli_rows}）")
        close = result.get("closeMs")
        if not isinstance(close, int) or close > (GRACEFUL_SECONDS - 0.3) * 1000:
            raise ValueError(f"客户端正常关闭没有在宽限期内完成：{close!r}")
        if message != "harness client disposed":
            raise ValueError(f"客户端正常关闭的断开信息不符：{message!r}")
        checked += 3

        # 2. 内核不理会 SIGTERM：按 2.5 秒与 1 秒两个期限升级，SIGKILL 收尾。
        stub = folder / "stubborn.py"
        stub.write_text(STUBBORN_KERNEL, encoding="utf-8")
        marker = folder / "stubborn.marker"
        result = _run_scenario(folder, "stubborn", [sys.executable, str(stub), str(marker)], {}, marker)
        rows = _marker_lines(marker)
        terms = [stamp for key, stamp in rows if key == "term"]
        dispose = float(result.get("disposeEpoch") or 0)
        delay = terms[0] - dispose if terms else -1.0
        if not (GRACEFUL_SECONDS - 0.3 <= delay <= GRACEFUL_SECONDS + 0.7):
            raise ValueError(f"客户端没有在 2.5 秒时发送 SIGTERM：{delay:.2f} 秒")
        close = result.get("closeMs")
        if not isinstance(close, int) or not (GRACEFUL_SECONDS + FORCE_SECONDS - 0.2) * 1000 <= close <= CLOSE_UPPER_MS:
            raise ValueError(f"客户端没有在 SIGTERM 一秒后由 SIGKILL 收尾：{close!r} 毫秒")
        if "harness did not stop after SIGTERM; sent SIGKILL" not in (result.get("diagnostics") or []):
            raise ValueError(f"客户端强制升级没有留下 SIGKILL 诊断：{result.get('diagnostics')}")
        checked += 3

        # 3. 内核已自行退出：dispose 立即完成，不再发送任何信号。
        exited = folder / "exited.py"
        exited.write_text(EXITED_KERNEL, encoding="utf-8")
        marker = folder / "exited.marker"
        result = _run_scenario(folder, "exited", [sys.executable, str(exited), str(marker)], {}, marker)
        rows = _marker_lines(marker)
        keys = [key for key, _ in rows]
        close = result.get("closeMs")
        messages = result.get("messages")
        if not (keys == ["started"] and isinstance(close, int) and close <= 400
                and messages == ["harness exited (code=0, signal=null)"]):
            raise ValueError(f"客户端已退出进程的关闭不符：marker={keys}、关闭 {close!r} 毫秒、断开信息 {messages!r}")
        checked += 1
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    checked = 0
    for fragment in ("`check_client_close.py`", "2.5 秒", "`SIGKILL`"):
        if fragment not in docs:
            raise ValueError(f"{DOCS} 缺少桌面端关闭升级的说明：{fragment}")
        checked += 1
    return checked


def check_client_close() -> tuple[int, int, int]:
    return _check_structure(), _check_behaviors(), _check_documentation()


def main() -> int:
    try:
        structure, behaviors, documents = check_client_close()
    except ValueError as error:
        print(f"桌面端关闭升级核对失败，{error}", file=sys.stderr)
        return 2
    print(f"桌面端关闭升级一致：{structure} 项结构、{behaviors} 项真实进程结果、{documents} 处文档口径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
