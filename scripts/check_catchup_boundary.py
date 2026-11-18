#!/usr/bin/env python3
"""核对补领转向的请求边界提交，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = "harness/src/boss_harness/agent.py"
APPLICATION = "harness/src/boss_harness/application.py"
RUN_FRAGMENTS = (
    "steering_batches = [staged[0]] if staged is not None and staged[0] else []",
    "commits: list[Callable[[], None]] = []",
    "commits.append(staged[1])",
    "catch_up, catch_up_commit = self.stage_steering()",
    "steering_batches.append(catch_up)",
    "commits.append(catch_up_commit)",
    "for commit in commits:",
    "if steering_batches and self.request_preparer is not None:",
)
FAILURE_FRAGMENTS = (
    "except ContextBudgetExceeded as exc:",
    "self._record_preparation(thread_id, request, exc.budget)",
    "except ContextCompactionFailed as exc:",
    "return self._context_failed(thread_id, exc)",
    "except ModelRequestRejected as exc:",
    "return self._request_rejected(thread_id, exc)",
)
APPLICATION_FRAGMENTS = (
    'entry.get("type") == "context_budget" and isinstance(payload, dict)',
    "payload.get(\"turnId\") == source_turn_id",
    'return fail("CONTINUATION_STEERING_OUTSIDE_BOUNDARY",'
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少函数 {name}")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_catchup_boundary() -> tuple[int, int]:
    agent = _read(AGENT)
    application = _read(APPLICATION)
    tree = ast.parse(agent)
    run = _function(tree, agent, "run")
    preparation = _function(tree, agent, "_record_preparation")
    plan = _function(ast.parse(application), application, "_turn_continuation_plan")
    checked = _expect(RUN_FRAGMENTS, run, "TurnRunner.run")
    if "steering_applied = bool(staged and staged[0])" in run:
        raise ValueError("补领转向不能再按首批结果单独决定是否提交边界")
    checked += 1
    checked += _expect(FAILURE_FRAGMENTS, run, "请求准备失败路径")
    checked += _expect(APPLICATION_FRAGMENTS, plan, "续接边界预检")
    checked += _expect(('snapshot["requestFingerprint"] = request_fingerprint(self.config.provider, request)',
                        'snapshot["steeringApplied"] = True'), preparation, "_record_preparation")
    return 2, checked


def main() -> int:
    try:
        modules, guards = check_catchup_boundary()
    except (ValueError, SyntaxError) as error:
        print(f"补领转向边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"补领转向边界一致：{modules} 个模块、{guards} 项提交与拒绝防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
