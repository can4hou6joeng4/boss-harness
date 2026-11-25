#!/usr/bin/env python3
"""核对退出应用时等待内核关闭：宿主关闭入口与真实进程的关闭升级。

桌面主进程的 `before-quit` 此前只同步调用 `manager.dispose()`，随后进程退出：
`HarnessClient.dispose()` 的 2.5 秒 + 1 秒两级期限挂在事件循环上，主进程一退出
就不再运行，卡住的内核会成为孤儿。`HarnessHostManager.close()` 先关闭所有宿主，
再等待它们的进程与标准输入输出句柄全部关闭；桌面退出路径等它结束才真正退出。

这里用 Node 24 的类型剥离加载真实 `host.ts` 与 `index.ts`，启动真实子进程：
正常内核读到标准输入结束即退出，关闭在 1 秒内完成；不读标准输入、也不理会
`SIGTERM` 的假内核要等两级期限升级到 `SIGKILL`，关闭在 3.3～5.2 秒完成且进程消失。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CLIENT_INDEX = "packages/app-client/src/index.ts"
CLIENT_HOST = "packages/app-client/src/host.ts"
PROTOCOL = "packages/protocol/src/index.ts"
MAIN = "apps/desktop/src/main/harness.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

# 关闭卡住时的两级期限由客户端常量决定；网络与调度抖动只放宽上界，不放宽下界。
GRACEFUL_SECONDS = 2.5
FORCE_SECONDS = 1.0
CLOSE_UPPER_MS = 5_200
NORMAL_UPPER_MS = 1_000
SECOND_UPPER_MS = 200
KERNEL_SCRIPT = """import json
import os
import signal
import sys
import time

marker = os.environ["MARKER"]
with open(marker, "a") as handle:
    handle.write("started %d\\n" % os.getpid())
if os.environ.get("MODE") == "stubborn":
    signal.signal(signal.SIGTERM, lambda *args: None)
for raw in sys.stdin:
    try:
        frame = json.loads(raw)
    except ValueError:
        continue
    if frame.get("method") == "initialize" and "id" in frame:
        print(json.dumps({"jsonrpc": "2.0", "id": frame["id"],
                          "result": {"serverName": "quit-probe",
                                     "protocolVersion": "0.2.0"}}), flush=True)
# 正常内核在标准输入结束时退出；卡住的假内核不读标准输入之后的 EOF，也不理会 SIGTERM。
if os.environ.get("MODE") == "stubborn":
    while True:
        time.sleep(0.05)
"""
NODE_DRIVER = """\
import { readFileSync } from "node:fs";
import { HarnessHostManager } from "./host.ts";

const manager = new HarnessHostManager();
const marker = process.env.MARKER ?? "";
const host = manager.add({
  hostId: "quit-probe",
  client: {
    command: process.env.KERNEL ?? "",
    args: JSON.parse(process.env.KERNEL_ARGS ?? "[]"),
    env: { MARKER: marker, MODE: process.env.MODE ?? "" },
    onDiagnostic: () => {},
  },
  clientInfo: { name: "quit-probe", version: "1.0" },
  supportsReconnect: false,
});
const out: Record<string, unknown> = {};
try {
  const initialized = await host.ensureReady();
  out.serverName = initialized.serverName;
  out.state = host.status().state;
  const began = performance.now();
  await manager.close();
  out.closeMs = Math.round(performance.now() - began);
  out.hostsAfterClose = manager.list().length;
  const again = performance.now();
  await manager.close();
  out.secondCloseMs = Math.round(performance.now() - again);
  const pid = Number((readFileSync(marker, "utf8").split(/\\s+/)[1] ?? "0"));
  try { process.kill(pid, 0); out.kernelAlive = true; } catch { out.kernelAlive = false; }
} catch (error) {
  out.error = String((error as Error)?.message ?? error);
}
process.stdout.write(JSON.stringify(out) + "\\n", () => process.exit(0));
"""


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _check_structure() -> int:
    host = _read(CLIENT_HOST)
    main = _read(MAIN)
    checked = 0
    for fragment in ("async close(): Promise<void> {",
                     "await Promise.all(hosts.map((host) => host.waitForClose()));"):
        if fragment not in host:
            raise ValueError(f"{CLIENT_HOST} 缺少宿主关闭入口片段：{fragment}")
        checked += 1
    # 必须先让每个宿主发起关闭，再等进程句柄收尾；反了就只是空等已在运行的连接。
    close_at = host.index("async close(): Promise<void> {")
    dispose_at = host.index("host.dispose()", close_at)
    wait_at = host.index("host.waitForClose()", close_at)
    if not dispose_at < wait_at:
        raise ValueError(f"{CLIENT_HOST} 的 close() 必须先关闭宿主、再等待进程关闭")
    checked += 1
    if "manager.close()" not in main:
        raise ValueError(f"{MAIN} 的退出路径没有调用 manager.close()")
    if "manager.dispose();" in main:
        raise ValueError(f"{MAIN} 的退出路径仍在直接调用 manager.dispose()")
    checked += 2
    quit_at = main.index('app.on("before-quit"')
    prevent_at = main.index("event.preventDefault()", quit_at)
    close_call_at = main.index("manager.close()", quit_at)
    if not prevent_at < close_call_at:
        raise ValueError(f"{MAIN} 必须先拦住本次退出、再开始关闭宿主")
    checked += 1
    if "if (quitReady) return;" not in main or "quitReady = true; app.quit();" not in main:
        raise ValueError(f"{MAIN} 缺少关闭完成后的退出放行标记")
    checked += 1
    return checked


def _prepare(folder: Path, scenario: str) -> tuple[Path, Path]:
    for name in ("home", "workspace"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    # 只驱动宿主：去掉 index.ts 对 host.ts 的再导出，其余源码原样使用。
    index = _read(CLIENT_INDEX)
    for line in ('export { HarnessHostConnection, HarnessHostManager } from "./host";\n',
                 'export type { HarnessConnectionState, HarnessConnectionStatus, HarnessHostOptions } from "./host";\n'):
        index = index.replace(line, "")
    (folder / "index.ts").write_text(index, encoding="utf-8")
    # Node 的类型剥离不支持 node_modules：把协议源码复制到本地，只改导入路径。
    host = _read(CLIENT_HOST)
    host = host.replace('from "@boss-harness/protocol";', 'from "./protocol.ts";')
    host = host.replace('from "./index";', 'from "./index.ts";')
    (folder / "host.ts").write_text(host, encoding="utf-8")
    (folder / "protocol.ts").write_text(_read(PROTOCOL), encoding="utf-8")
    (folder / "driver.ts").write_text(NODE_DRIVER, encoding="utf-8")
    kernel = folder / "kernel.py"
    kernel.write_text(KERNEL_SCRIPT, encoding="utf-8")
    marker = folder / f"{scenario}.marker"
    return kernel, marker


def _run_scenario(folder: Path, scenario: str) -> dict:
    kernel, marker = _prepare(folder, scenario)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(folder / "home"),
        "TMPDIR": str(folder),
        "MARKER": str(marker),
        "MODE": scenario,
        "KERNEL": sys.executable,
        "KERNEL_ARGS": json.dumps([str(kernel)]),
    }
    try:
        result = subprocess.run(["node", str(folder / "driver.ts")], capture_output=True, text=True,
                                timeout=30, env=env, cwd=str(folder))
    except subprocess.TimeoutExpired:
        raise ValueError(f"退出关闭驱动超时（{scenario}）") from None
    if result.returncode != 0:
        raise ValueError(f"退出关闭驱动失败（{scenario}）：{(result.stderr or result.stdout).strip()[:400]}")
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise ValueError(f"退出关闭驱动没有输出结果（{scenario}）：{result.stdout.strip()[:200]}")
    return json.loads(lines[-1])


def _check_behaviors() -> int:
    checked = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        base = Path(directory)
        normal = _run_scenario(base / "normal", "normal")
        if normal.get("error"):
            raise ValueError(f"正常内核的宿主关闭失败：{normal['error']}")
        close = normal.get("closeMs")
        second = normal.get("secondCloseMs")
        if normal.get("serverName") != "quit-probe" or normal.get("state") != "ready":
            raise ValueError(f"正常内核没有完成握手：{normal}")
        checked += 1
        if not isinstance(close, int) or close > NORMAL_UPPER_MS:
            raise ValueError(f"正常内核的关闭没有在 1 秒内完成：{close!r} 毫秒")
        checked += 1
        if normal.get("kernelAlive") is not False:
            raise ValueError(f"正常内核在 close() 之后仍在运行：{normal.get('kernelAlive')!r}")
        checked += 1
        if normal.get("hostsAfterClose") != 0 or not isinstance(second, int) or second > SECOND_UPPER_MS:
            raise ValueError(f"宿主关闭后没有清空或重复关闭开销异常：{normal.get('hostsAfterClose')!r}、{second!r}")
        checked += 1

        stubborn = _run_scenario(base / "stubborn", "stubborn")
        if stubborn.get("error"):
            raise ValueError(f"卡住内核的宿主关闭失败：{stubborn['error']}")
        close = stubborn.get("closeMs")
        if not isinstance(close, int) or not (GRACEFUL_SECONDS + FORCE_SECONDS - 0.2) * 1000 <= close <= CLOSE_UPPER_MS:
            raise ValueError(f"卡住的内核没有按两级期限收尾：{close!r} 毫秒")
        checked += 1
        if stubborn.get("kernelAlive") is not False:
            raise ValueError(f"卡住的内核在 close() 之后仍在运行：{stubborn.get('kernelAlive')!r}")
        checked += 1
        if stubborn.get("hostsAfterClose") != 0:
            raise ValueError(f"卡住内核关闭后宿主列表没有清空：{stubborn.get('hostsAfterClose')!r}")
        checked += 1
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    checked = 0
    for fragment in ("`check_quit_close.py`", "退出应用", "`waitForClose()`"):
        if fragment not in docs:
            raise ValueError(f"{DOCS} 缺少退出关闭的说明：{fragment}")
        checked += 1
    return checked


def check_quit_close() -> tuple[int, int, int]:
    return _check_structure(), _check_behaviors(), _check_documentation()


def main() -> int:
    try:
        structure, behaviors, documents = check_quit_close()
    except ValueError as error:
        print(f"退出关闭核对失败，{error}", file=sys.stderr)
        return 2
    print(f"退出关闭一致：{structure} 项结构、{behaviors} 项真实进程结果、{documents} 处文档口径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
