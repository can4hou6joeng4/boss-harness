#!/usr/bin/env python3
"""对照分支摘要合法性的固定原因、上限与判定顺序。

`branch_summary_issue` 是上下文注入与导出共用的摘要校验：正文必须是
非空字符串且不超过 32000 字符；目标回合要么缺失，要么必须落在参考分支
的位置表里；被放弃回合列表必须是 1 到 200 个、单个最多 128 字符、总长
最多 4096 字符的字符串列表；来源摘要与两个辅助标识只在提供时有界。
返回值是固定的中文原因，供两条读取路径给出同一诊断；本脚本只做纯函数
行为对照并扫描源码，不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import (branch_summary_issue as _kernel_branch_summary_issue,  # noqa: E402
                                  MAX_BRANCH_SUMMARY_CHARS, MAX_BRANCH_SUMMARY_DIGEST_CHARS,
                                  MAX_BRANCH_SUMMARY_TURNS, MAX_BRANCH_SUMMARY_TURN_ID_CHARS,
                                  MAX_BRANCH_SUMMARY_TURN_TOTAL_CHARS)


def branch_summary_issue(payload: dict, positions) -> str | None:
    """内核摘要校验；任何意外异常都折算为明确的检查失败原因。"""
    try:
        return _kernel_branch_summary_issue(payload, positions)
    except (TypeError, AttributeError, KeyError) as error:
        raise ValueError(f"摘要校验抛出意外异常：{error!r}") from None

CHECK_ORDER = (
    "def branch_summary_issue(payload: dict, positions: Mapping[str, int]) -> str | None:",
    'summary, anchor = payload.get("summary"), payload.get("targetTurnId")',
    'abandoned = payload.get("abandonedTurnIds")',
    "if not isinstance(summary, str):",
    'return "摘要正文不是字符串"',
    "if not summary.strip():",
    'return "摘要正文为空"',
    "if len(summary) > MAX_BRANCH_SUMMARY_CHARS:",
    'return f"摘要正文超过 {MAX_BRANCH_SUMMARY_CHARS} 字符"',
    "if anchor is not None and (not isinstance(anchor, str) or anchor not in positions):",
    'return "摘要的目标回合不在当前分支上"',
    "if (not isinstance(abandoned, list) or not abandoned",
    "or len(abandoned) > MAX_BRANCH_SUMMARY_TURNS",
    "or not all(isinstance(turn_id, str)",
    "and len(turn_id) <= MAX_BRANCH_SUMMARY_TURN_ID_CHARS for turn_id in abandoned)",
    "or sum(len(turn_id) for turn_id in abandoned) > MAX_BRANCH_SUMMARY_TURN_TOTAL_CHARS):",
    'return "被放弃回合列表为空或无效"',
    'digest = payload.get("sourceTextDigest")',
    "if digest is not None and (not isinstance(digest, str)",
    "or len(digest) > MAX_BRANCH_SUMMARY_DIGEST_CHARS):",
    'return "摘要来源摘要无效"',
    'for key in ("summaryJobId", "fromTurnId"):',
    "value = payload.get(key)",
    "if value is not None and (not isinstance(value, str)",
    "or len(value) > MAX_BRANCH_SUMMARY_TURN_ID_CHARS):",
    'return "摘要辅助标识无效"',
    "return None",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _function(tree: ast.Module, source: str, name: str) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is not None:
                return segment
    raise ValueError(f"缺少顶层函数 {name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect(reason, message: str | None, label: str) -> None:
    if reason != message:
        raise ValueError(f"{label} 判定变化：期望 {message!r}，实际 {reason!r}")


def check_summary_issue() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    function = _function(tree, source, "branch_summary_issue")
    checked = _ordered(CHECK_ORDER, function, SESSION)
    # 六个固定原因各一次，结尾只返回 None；纯函数不写载荷。
    for message in ("摘要正文不是字符串", "摘要正文为空", "摘要的目标回合不在当前分支上",
                    "被放弃回合列表为空或无效", "摘要来源摘要无效", "摘要辅助标识无效"):
        if function.count(f'return "{message}"') != 1:
            raise ValueError(f"{SESSION} 的摘要原因必须恰好一处：{message}")
        checked += 1
    if function.count("return None") != 1:
        raise ValueError(f"{SESSION} 的摘要校验必须只在结尾返回 None")
    checked += 1
    if "payload[" in function or "payload.update" in function:
        raise ValueError(f"{SESSION} 的摘要校验不得改写载荷")
    checked += 1
    if function.count('for key in ("summaryJobId", "fromTurnId"):') != 1:
        raise ValueError(f"{SESSION} 的辅助标识必须按固定顺序校验")
    checked += 1
    if function.count("MAX_BRANCH_SUMMARY_CHARS") != 2:
        raise ValueError(f"{SESSION} 的摘要正文上限必须同时用于比较与文案")
    checked += 1
    # 判定顺序：正文先于目标回合，目标回合先于列表，列表先于来源摘要。
    if function.index('"摘要正文不是字符串"') > function.index('"摘要的目标回合不在当前分支上"'):
        raise ValueError(f"{SESSION} 的正文判定必须先于目标回合")
    checked += 1
    if function.index('"摘要的目标回合不在当前分支上"') > function.index('"被放弃回合列表为空或无效"'):
        raise ValueError(f"{SESSION} 的目标回合判定必须先于列表")
    checked += 1
    if function.index('"被放弃回合列表为空或无效"') > function.index('"摘要来源摘要无效"'):
        raise ValueError(f"{SESSION} 的列表判定必须先于来源摘要")
    checked += 1
    if function.index('"摘要来源摘要无效"') > function.index('"摘要辅助标识无效"'):
        raise ValueError(f"{SESSION} 的来源摘要判定必须先于辅助标识")
    checked += 1
    # 行为：合法载荷与目标回合。
    positions = {"turn-a": 0, "turn-b": 1}
    base = {"summary": "摘要", "abandonedTurnIds": ["turn-a"]}
    _expect(branch_summary_issue(dict(base), positions), None, "最小合法载荷")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId="turn-b"), positions), None, "目标在分支")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId=None), positions), None, "目标为空")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId="turn-z"), positions),
            "摘要的目标回合不在当前分支上", "目标不在分支")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId=3), positions),
            "摘要的目标回合不在当前分支上", "目标非字符串")
    checked += 1
    _expect(branch_summary_issue(dict(base), {}), None, "空位置表且无目标")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId="turn-a"), {}),
            "摘要的目标回合不在当前分支上", "空位置表有目标")
    checked += 1
    # 行为：摘要正文。
    for label, summary in (("正文缺失", None), ("正文非字符串", 3)):
        _expect(branch_summary_issue(dict(base, summary=summary), positions),
                "摘要正文不是字符串", label)
        checked += 1
    for label, summary in (("正文为空", ""), ("正文仅空白", " \t\n")):
        _expect(branch_summary_issue(dict(base, summary=summary), positions),
                "摘要正文为空", label)
        checked += 1
    _expect(branch_summary_issue(dict(base, summary="x" * MAX_BRANCH_SUMMARY_CHARS), positions),
            None, "正文恰好上限")
    checked += 1
    _expect(branch_summary_issue(dict(base, summary="x" * (MAX_BRANCH_SUMMARY_CHARS + 1)), positions),
            f"摘要正文超过 {MAX_BRANCH_SUMMARY_CHARS} 字符", "正文超限")
    checked += 1
    # 行为：被放弃回合列表。
    for label, abandoned in (
        ("列表缺失", None),
        ("列表非列表", "turn-a"),
        ("列表为空", []),
        ("元素非字符串", ["turn-a", 3]),
        ("元素超长", ["t" * (MAX_BRANCH_SUMMARY_TURN_ID_CHARS + 1)]),
        ("条目超限", ["t"] * (MAX_BRANCH_SUMMARY_TURNS + 1)),
        ("总长超限", ["t" * MAX_BRANCH_SUMMARY_TURN_ID_CHARS] * 40),
    ):
        _expect(branch_summary_issue(dict(base, abandonedTurnIds=abandoned), positions),
                "被放弃回合列表为空或无效", label)
        checked += 1
    _expect(branch_summary_issue(dict(base, abandonedTurnIds=["t"] * MAX_BRANCH_SUMMARY_TURNS), positions),
            None, "列表恰好条数")
    checked += 1
    _expect(branch_summary_issue(
        dict(base, abandonedTurnIds=["t" * MAX_BRANCH_SUMMARY_TURN_ID_CHARS] * 32), positions),
        None, "列表恰好总长")
    checked += 1
    _expect(branch_summary_issue(
        dict(base, abandonedTurnIds=["t" * MAX_BRANCH_SUMMARY_TURN_ID_CHARS] * 33), positions),
        "被放弃回合列表为空或无效", "总长多一条")
    checked += 1
    # 行为：来源摘要与辅助标识。
    for label, digest in (("摘要非字符串", 3), ("摘要超长", "d" * (MAX_BRANCH_SUMMARY_DIGEST_CHARS + 1))):
        _expect(branch_summary_issue(dict(base, sourceTextDigest=digest), positions),
                "摘要来源摘要无效", label)
        checked += 1
    _expect(branch_summary_issue(dict(base, sourceTextDigest="d" * MAX_BRANCH_SUMMARY_DIGEST_CHARS), positions),
            None, "摘要恰好上限")
    checked += 1
    _expect(branch_summary_issue(dict(base, sourceTextDigest=None), positions), None, "摘要为空")
    checked += 1
    for key in ("summaryJobId", "fromTurnId"):
        for label, value in (("非字符串", 3), ("超长", "v" * (MAX_BRANCH_SUMMARY_TURN_ID_CHARS + 1))):
            _expect(branch_summary_issue(dict(base, **{key: value}), positions),
                    "摘要辅助标识无效", f"{key}{label}")
            checked += 1
        _expect(branch_summary_issue(dict(base, **{key: None}), positions), None, f"{key}为空")
        checked += 1
    # 行为：多重错误按顺序返回第一条，且载荷不被改写。
    snapshot = dict(base, summary=None, abandonedTurnIds=[], sourceTextDigest=3)
    original = {key: (list(value) if isinstance(value, list) else value) for key, value in snapshot.items()}
    _expect(branch_summary_issue(snapshot, positions), "摘要正文不是字符串", "正文优先")
    checked += 1
    if snapshot != original:
        raise ValueError("摘要校验不得改写载荷")
    checked += 1
    _expect(branch_summary_issue(dict(base, summary=None, targetTurnId="turn-z"), positions),
            "摘要正文不是字符串", "正文优先于目标回合")
    checked += 1
    _expect(branch_summary_issue(dict(base, targetTurnId="turn-z", abandonedTurnIds=[]), positions),
            "摘要的目标回合不在当前分支上", "目标回合优先于列表")
    checked += 1
    _expect(branch_summary_issue(dict(base, abandonedTurnIds=[], sourceTextDigest=3), positions),
            "被放弃回合列表为空或无效", "列表优先于摘要")
    checked += 1
    _expect(branch_summary_issue(dict(base, abandonedTurnIds=[], summaryJobId=3), positions),
            "被放弃回合列表为空或无效", "列表优先于辅助标识")
    checked += 1
    _expect(branch_summary_issue(dict(base, summary=None, sourceTextDigest=3), positions),
            "摘要正文不是字符串", "正文优先于摘要")
    checked += 1
    _expect(branch_summary_issue(dict(base, sourceTextDigest=3, summaryJobId=3), positions),
            "摘要来源摘要无效", "摘要优先于辅助标识")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_summary_issue()
    except (ValueError, SyntaxError) as error:
        print(f"分支摘要判定核对失败，{error}", file=sys.stderr)
        return 2
    print(f"分支摘要判定一致：{checked} 项原因、上限与顺序校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
