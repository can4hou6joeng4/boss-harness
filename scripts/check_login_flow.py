#!/usr/bin/env python3
"""核对内核扫码登录的凭证校验、命令引用与保存回读边界。

`begin_login` / `cancel_login` / `complete_login` / `_save_login` / `_local_auth`
是内核侧登录流程：官方 Cookie 与 User-Agent 先做格式和大小校验，Cookie 头
与 User-Agent 分别经 `shlex.quote` 进入交给上游的数据，凭证不写入登录状态、
不回显在异常里；保存任务在调用前后检查取消标记，完成后必须回读本地
`status` 才能报告成功。这里按源码顺序固定这些边界，避免校验放宽、命令
拼接或取消失效让登录态在错误状态下被覆盖。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONNECTIONS = "harness/src/boss_harness/connections.py"

READ_ORDER = (
    "def read_login(self) -> dict:",
    "with self.lock:",
    "return _disabled() if self.bridge_factory is None else deepcopy(self.login)",
)
BEGIN_ORDER = (
    "def begin_login(self) -> dict:",
    '"""Host-only control: no credentials, browser access or network here."""',
    "self._require_platform()",
    "if self.closed:",
    'raise ValueError("连接服务已关闭")',
    'if self.login["state"] in {"waiting", "saving"}:',
    "if any(k in self.active for k in (\"cli\", \"platform\", \"login\")):",
    '"code": "CHECK_BUSY"',
    "bridge = self._new_bridge()",
    "available = bridge.available()",
    "self.bridge_lifecycle.close(bridge)",
    "if not available:",
    '"code": "CLI_UNAVAILABLE"',
    "self.login_cancel = threading.Event()",
    'self.login = {"id": uuid.uuid4().hex, "state": "waiting",',
    "return self.read_login()",
)
CANCEL_ORDER = (
    "def cancel_login(self, attempt: str) -> dict:",
    "self._require_platform()",
    'if attempt == self.login.get("id") and self.login["state"] in {"waiting", "saving"}:',
    'saving = self.login["state"] == "saving"',
    "if self.login_cancel:",
    "self.login_cancel.set()",
    'self.login.update(state="cancelled", summary="保存已停止，登录态可能已更新，请手动检查" if saving else "已取消扫码登录")',
    "if saving:",
    'self._set("platform", state="unchecked", code=None, checkedAt=None,',
    'summary="登录保存已取消，请手动核对登录态")',
    "return self.read_login()",
)
COMPLETE_ORDER = (
    "def complete_login(self, params: dict) -> dict:",
    "Only Electron's trusted host supplies official-origin cookies.",
    "The model and renderer allowlists do not expose this method. The payload",
    "is never persisted, emitted as an event, or included in an exception.",
    "self._require_platform()",
    'cookies, user_agent = params.get("cookies"), params.get("userAgent")',
    "if (not isinstance(cookies, dict) or not 1 <= len(cookies) <= 200\n",
    "or not isinstance(user_agent, str) or len(user_agent) > 512\n",
    "or any(ord(c) < 32 or ord(c) == 127 for c in user_agent)",
    "or any(not isinstance(k, str) or not re.fullmatch(",
    'or not isinstance(v, str) or any(ord(c) < 32 or ord(c) == 127 or c == ";" for c in v)',
    "for k, v in cookies.items())",
    'or not cookies.get("wt2")):',
    'raise ValueError("官方登录态格式无效")',
    'cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())',
    'if len(cookie_header.encode("utf-8")) > 64 * 1024:',
    'raise ValueError("官方登录态超过大小限制")',
    "--cookie ",
    "shlex.quote(cookie_header)",
    "--user-agent ",
    "shlex.quote(user_agent)",
    'if self.closed or params.get("id") != self.login.get("id") or self.login["state"] != "waiting":',
    'raise ValueError("扫码登录已结束，请重新打开官方登录窗口")',
    "cancel = self.login_cancel",
    "assert cancel is not None",
    'self.login.update(state="saving", summary="已检测到扫码登录，正在通过上游验证并保存…")',
    'self._set("platform", state="checking", code=None, checkedAt=None, summary="正在验证新的官方登录态…")',
    'worker = threading.Thread(target=self._save_login, args=(payload, cancel), daemon=True, name="platform-login")',
    'self.active["login"] = worker, cancel',
    "worker.start()",
    "if worker is None or worker.ident is None:",
    "cancel.set()",
    'self.active.pop("login", None)',
    'code="LOGIN_SAVE_START_FAILED"',
    "failed_start = True",
    "result = self.read_login()",
    "if failed_start:",
    "self._notify_idle()",
    "return result",
)
SAVE_ORDER = (
    "def _save_login(self, payload: str, cancel: threading.Event) -> None:",
    "bridge = None",
    "if self.bridge_factory is None or cancel.is_set():",
    "return",
    "bridge = self._new_bridge()",
    "bridge.cancel_event = cancel",
    "if cancel.is_set():",
    'result = bridge.call("login", "--curl-file", "-", stdin=payload, timeout=20)',
    'payload = ""',
    "if cancel.is_set():",
    '"state": "ready"',
    'local = bridge.call("status", timeout=15)',
    'data = local.data if local.ok and isinstance(local.data, dict) else {}',
    'auth = _auth_state(data.get("auth_state"))',
    'if not local.ok or data.get("logged_in") is not True or auth in {"broken", "missing"}:',
    '"code": "LOGIN_READBACK_FAILED"',
    'elif auth != "complete":',
    '"code": "LOGIN_INCOMPLETE"',
    'outcome["authState"] = auth',
    "if not cancel.is_set():",
    'self._set("platform", **outcome, checkedAt=_now())',
    'self.login.update(state="succeeded" if outcome["state"] == "ready" else "failed" if outcome["state"] == "unchecked" else outcome["state"],',
    "if bridge is not None:",
    "self.bridge_lifecycle.close(bridge)",
    'active = self.active.get("login")',
    "if active is not None and active[1] is cancel:",
    'self.active.pop("login", None)',
    "self._notify_idle()",
)
LOCAL_ORDER = (
    "def _local_auth(self, bridge, cancel: threading.Event) -> bool:",
    "if cancel.is_set():",
    "return False",
    "if self.bridge_factory is None:",
    'self._set("platform", **_disabled())',
    'result = bridge.call("status", timeout=15)',
    "if cancel.is_set():",
    "if not result.ok:",
    'self._set("platform", **self._error(result), authState="unknown", checkedAt=_now())',
    'auth = _auth_state(data.get("auth_state"))',
    'self._set("platform", authState=auth)',
    'risk = data.get("cdp_risk_lock") or {}',
    'if isinstance(risk, dict) and (risk.get("locked") or risk.get("group_locked")):',
    'code="ENVIRONMENT_RISK_LOCKED"',
    'if data.get("logged_in") is not True or auth == "broken":',
    'code="AUTH_REQUIRED"',
    "return True",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ConnectionChecks":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 ConnectionChecks.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_login_flow() -> int:
    source = _read(CONNECTIONS)
    tree = ast.parse(source)
    read = _method(tree, source, "read_login")
    begin = _method(tree, source, "begin_login")
    cancel = _method(tree, source, "cancel_login")
    complete = _method(tree, source, "complete_login")
    save = _method(tree, source, "_save_login")
    local = _method(tree, source, "_local_auth")
    checked = _ordered(READ_ORDER, read, CONNECTIONS)
    checked += _ordered(BEGIN_ORDER, begin, CONNECTIONS)
    checked += _ordered(CANCEL_ORDER, cancel, CONNECTIONS)
    checked += _ordered(COMPLETE_ORDER, complete, CONNECTIONS)
    checked += _ordered(SAVE_ORDER, save, CONNECTIONS)
    checked += _ordered(LOCAL_ORDER, local, CONNECTIONS)
    # 凭证只经两次 shlex.quote 进入命令文本，且不执行 shell。
    if complete.count("shlex.quote(") != 2:
        raise ValueError(f"{CONNECTIONS} 的登录凭证必须逐项引用")
    checked += 1
    if "shell=True" in complete or "os.system(" in complete:
        raise ValueError(f"{CONNECTIONS} 的登录不得经过 shell")
    checked += 1
    if complete.count("cookie_header") != 3:
        raise ValueError(f"{CONNECTIONS} 的 Cookie 头必须只用于拼接、限长与引用")
    checked += 1
    # 凭证不得写入登录状态或平台报告。
    for line in complete.splitlines() + save.splitlines():
        if "self.login.update(" in line or "self._set(" in line:
            if any(word in line for word in ("cookie", "user_agent", "payload")):
                raise ValueError(f"{CONNECTIONS} 的凭证不得写入状态：{line.strip()}")
    checked += 1
    # Cookie / User-Agent 各只读取一次，请求编号必须与当前登录一致。
    if complete.count('params.get("cookies")') != 1 or complete.count('params.get("userAgent")') != 1:
        raise ValueError(f"{CONNECTIONS} 的登录请求必须各读取一次凭证字段")
    checked += 1
    if 'params.get("id") != self.login.get("id")' not in complete:
        raise ValueError(f"{CONNECTIONS} 的登录保存必须核对请求编号")
    checked += 1
    # 保存任务在调用前、调用后与写回前都要检查取消。
    if save.count("cancel.is_set()") != 5:
        raise ValueError(f"{CONNECTIONS} 的登录保存必须检查五次取消")
    checked += 1
    if save.count('payload = ""') != 1:
        raise ValueError(f"{CONNECTIONS} 的登录保存必须在调用后清空命令文本")
    checked += 1
    # 保存后必须回读本地状态，三档结果都要有固定错误码。
    if save.count('bridge.call("login"') != 1 or "--curl-file" not in save:
        raise ValueError(f"{CONNECTIONS} 的登录必须经 --curl-file 交给上游")
    checked += 1
    if "timeout=20" not in save or 'bridge.call("status", timeout=15)' not in save:
        raise ValueError(f"{CONNECTIONS} 的登录保存与回读必须有固定超时")
    checked += 1
    for code, expected in (("LOGIN_READBACK_FAILED", 1), ("LOGIN_INCOMPLETE", 1),
                           ("LOGIN_SAVE_FAILED", 2)):
        if save.count(code) != expected:
            raise ValueError(f"{CONNECTIONS} 的登录保存必须固定错误码 {code}")
        checked += 1
    # 保存任务的槽位必须按取消标记比较，避免旧任务清掉新任务。
    if save.count("active[1] is cancel") != 1:
        raise ValueError(f"{CONNECTIONS} 的登录槽位必须按取消标记比较")
    checked += 1
    # 本地登录态检查：六处拒绝、风控锁优先于登录态判断。
    if local.count("return False") != 6 or local.count("return True") != 1:
        raise ValueError(f"{CONNECTIONS} 的本地登录检查必须保留六处拒绝")
    checked += 1
    if local.count('data.get("logged_in") is not True') != 1:
        raise ValueError(f"{CONNECTIONS} 的本地登录检查必须要求明确的已登录")
    checked += 1
    if local.count('code="ENVIRONMENT_RISK_LOCKED"') != 1 or local.count('code="AUTH_REQUIRED"') != 1:
        raise ValueError(f"{CONNECTIONS} 的本地登录检查必须区分风控锁与未登录")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_login_flow()
    except (ValueError, SyntaxError) as error:
        print(f"扫码登录流程核对失败，{error}", file=sys.stderr)
        return 2
    print(f"扫码登录流程一致：{checked} 项凭证、保存与回读校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
