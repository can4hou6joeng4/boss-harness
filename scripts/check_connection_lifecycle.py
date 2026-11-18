#!/usr/bin/env python3
"""核对连接检查的取消、归属与关闭边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONNECTIONS = "harness/src/boss_harness/connections.py"
APPLICATION = "harness/src/boss_harness/application.py"
EXPECTED_FIELDS = {
    "cancel": "threading.Event",
    "provider": "Provider | None",
    "worker_done": "bool",
    "abort_started": "bool",
    "abort_pending": "bool",
    "abort_worker": "threading.Thread | None",
}
METHOD_FRAGMENTS = {
    "start": (
        "if self.closed or busy or self.report[key][\"state\"] == \"disabled\":",
        "self.report[key].pop(\"requestRejected\", None)",
        "worker = threading.Thread(target=self._run, args=(key, cancel), daemon=True",
        "self.active[key] = worker, cancel",
        'self._set(key, state="checking", summary="检查中…", code=None, checkedAt=None)',
        "if worker is None or worker.ident is None:",
        'self._set(key, state="failed", code="CHECK_FAILED",',
    ),
    "_current_model_locked": (
        "self._model_check is job",
        "active is not None",
        "active[1] is job.cancel",
    ),
    "_retire_model_locked": (
        "job.worker_done and not job.abort_pending",
        "self.active.pop(\"model\", None)",
        "self._model_check = None",
        "job.provider = None",
    ),
    "_abort_model": (
        'abort = getattr(provider, "request_abort", None)',
        "job.abort_pending = False",
        "self._retire_model_locked(job)",
        "self._notify_idle()",
    ),
    "_request_model_abort_locked": (
        "job.provider is None or job.abort_started",
        "job.abort_started = job.abort_pending = True",
        'name="connection-model-abort"',
        "worker is None or worker.ident is None",
        "job.abort_started = job.abort_pending = False",
    ),
    "_expire_model": (
        "job.cancel.is_set()",
        'self.report["model"]["state"] != "checking"',
        "job.cancel.set()",
        'code="CHECK_TIMEOUT"',
        "self._request_model_abort_locked(job)",
    ),
    "prepare_close": (
        "self.closed = True",
        "if self.login_cancel:",
        "for _, cancel in self.active.values():",
        "job is not None and self._current_model_locked(job)",
        'code="CANCELLED"',
    ),
    "wait_for_stop": (
        "workers = [worker for worker, _ in self.active.values()]",
        "if job is not None and job.abort_worker is not None:",
        "workers.append(job.abort_worker)",
        "join_until(workers, deadline)",
    ),
    "close": (
        "self.prepare_close()",
        "self.request_stop_aborts()",
        "self.wait_for_stop(deadline)",
    ),
}
APPLICATION_FRAGMENTS = (
    "self.connections.on_idle = self._close_application_resources_if_idle",
    "self.runtimes.on_idle = self._close_application_resources_if_idle",
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
        if isinstance(node, ast.ClassDef) and node.name == "ConnectionChecks":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"connections.py 缺少 ConnectionChecks.{name}")


def _model_check(tree: ast.Module, source: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_ModelCheck":
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError("connections.py 缺少 _ModelCheck")


def check_connection_lifecycle() -> tuple[int, int]:
    source = _read(CONNECTIONS)
    tree = _tree(CONNECTIONS)
    checked = 0
    model_source = _model_check(tree, source)
    for field, annotation in EXPECTED_FIELDS.items():
        if f"{field}: {annotation}" not in model_source:
            raise ValueError(f"_ModelCheck 缺少字段 {field}: {annotation}")
        checked += 1
    for name, fragments in METHOD_FRAGMENTS.items():
        body = _method(tree, source, name)
        missing = [fragment for fragment in fragments if fragment not in body]
        if missing:
            raise ValueError(f"ConnectionChecks.{name} 缺少：" + "、".join(missing))
        checked += len(fragments)
    application = _read(APPLICATION)
    for fragment in APPLICATION_FRAGMENTS:
        if fragment not in application:
            raise ValueError(f"application.py 缺少空闲回收挂载：{fragment}")
        checked += 1
    body = _method(tree, source, "_run")
    if body.count("self.bridge_lifecycle.close(bridge)") < 1:
        raise ValueError("_run 必须在全部 CLI / 平台桥接结束路径释放工具桥")
    if "job.worker_done = True" not in body or "self._notify_idle()" not in body:
        raise ValueError("_run 必须提交 worker_done 并通知空闲回收")
    checked += 2
    return len(METHOD_FRAGMENTS), checked


def main() -> int:
    try:
        methods, guards = check_connection_lifecycle()
    except ValueError as error:
        print(f"连接检查生命周期核对失败，{error}", file=sys.stderr)
        return 2
    print(f"连接检查生命周期一致：{methods} 个关键方法、{guards} 项取消与回收防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
