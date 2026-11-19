#!/usr/bin/env python3
"""核对 provider 用量汇总的校验、来源与缓存估算边界。

usage.py 决定 thread/usage/read 与导出的计数：只有类型、范围与 provider 语义
都可验证的记录才计入合计，来源标识有界，费用不可知，缓存未命中只按 Pi 口径
估算。任一校验、来源上限或缓存口径被删改不会触发构建失败，因此静态固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/usage.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

CONSTANT_FRAGMENTS = (
    # 数值常量按整行锚定：8 改成 800 之类的后缀扩展不能因前缀相同而通过。
    "MAX_REQUEST_TOKENS = 50_000_000\n",
    '_FIELDS = ("input", "output", "cache_read", "cache_write")\n',
    # 两个线路的缓存语义不同：OpenAI 的缓存 input 是子集，Anthropic 分开计数。
    '"openai": {"cacheRead": True, "cacheWrite": False, "reasoning": True},\n',
    '"anthropic": {"cacheRead": True, "cacheWrite": True, "reasoning": False},\n',
    'SOURCE = "provider-usage"\n',
    "MAX_PROVENANCE_ITEMS = 8\n",
    "MAX_PROVIDER_CHARS = 64\n",
    "MAX_MODEL_CHARS = 200\n",
    "MAX_SUMMARY_JOBS = 50\n",
    "CACHE_MISS_FLOOR = 1024\n",
)
VERIFY_FRAGMENTS = (
    "type(value) is int",
    'return None, "unknownProvider"',
    'return None, "missing"',
    'return None, "invalidType"',
    'return None, "negative"',
    'return None, "outOfRange"',
    'return None, "inconsistent"',
    'return None, "zero"',
    'if values["cache_read"] > values["input"] or (reasoning is not None and reasoning > values["output"]):',
    'prompt = values["input"]',
    'uncached = values["input"] - values["cache_read"]',
    'prompt = values["input"] + values["cache_read"] + values["cache_write"]',
    'uncached = values["input"]',
    'if prompt + values["output"] == 0:',
    # 未上报的字段返回 None，不能把 0 当成事实。
    '"cacheReadTokens": values["cache_read"] if reported["cacheRead"] else None,',
    '"cacheWriteTokens": values["cache_write"] if reported["cacheWrite"] else None,',
    '"reasoningTokens": reasoning if reported["reasoning"] else None,',
    # 没有可信价目来源，费用始终不可用。
    '"costUsd": None, "costSource": "unavailable"}',
)
PROVENANCE_FRAGMENTS = (
    "if len(values) >= MAX_PROVENANCE_ITEMS or not isinstance(value, str):",
    "value = wire_text(value)",
    "if not 0 < len(value) <= limit or value in values:",
)
ADD_FRAGMENTS = (
    'bucket["unverifiedRequests"] += 1',
    'if reason == "missing":',
    'bucket["unreportedRequests"] += 1',
    'bucket["unverifiedReasons"][reason] = bucket["unverifiedReasons"].get(reason, 0) + 1',
    'bucket["verifiedRequests"] += 1',
    'for key in ("promptTokens", "uncachedInputTokens", "outputTokens"):',
    "bucket[key] = (bucket[key] or 0) + normalized[key]",
)
IDENTITY_FRAGMENTS = (
    "if not isinstance(value, str) or not 0 < len(value) <= 128:",
    "return value if value else None",
    '"kind": "branchSummary", "turnId": bounded_identifier(payload.get("targetTurnId")),',
    '"throughTurnId": None, "reason": None, "origin": "model"}',
    'reason if isinstance(reason, str) and reason in {"threshold", "budget", "overflow"} else None,',
    'origin if isinstance(origin, str) and origin in {"user", "model"} else None}',
)
AGGREGATE_FRAGMENTS = (
    # 分支视图含交错放弃的请求，线性基线不成立，只有日志视图估算缓存未命中。
    "track_cache = active_turn_ids is None",
    'if kind in ("context_checkpoint", _BRANCH_SUMMARY):',
    "cache_prev_prompt = None",
    "cache_reported = False",
    "policy = verified_policy((turn_policies or {}).get(turn_id))",
    "policy = {key: wire_text(value) if isinstance(value, str) else value",
    "missed = min(cache_prev_prompt, prompt) - cache_read",
    "if missed > CACHE_MISS_FLOOR:",
    "cache_reported = cache_reported or cache_read + cache_write > 0",
    '"summaryJobs": list(jobs.values())[-MAX_SUMMARY_JOBS:], "summaryJobCount": len(jobs),',
    '"summaryJobsTruncated": len(jobs) > MAX_SUMMARY_JOBS}',
    "if active_job_id is not None and job_id == active_job_id:",
    'bucket["active"] = True',
    "if track_cache:",
    'result["cacheWaste"] = {"missedTokens": cache_missed_tokens, "missCount": cache_miss_count}',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "`unreportedRequests` 必须等于 reason `missing`"),
    (TECHNICAL_REFERENCE, "桌面只取首份并保留最近 50 条，与内核 `[-MAX_SUMMARY_JOBS:]` 同向"),
    (TECHNICAL_REFERENCE, "OpenAI 的缓存 input 是总 input 的子集，Anthropic 的缓存读写字段按独立计数处理，避免重复计算。"),
    (USER_GUIDE, "会话用量遇到损坏的模型来源或回合编号时，仍展示可验证的合法记录"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_usage() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(VERIFY_FRAGMENTS, module, MODULE)
    checked += _expect(PROVENANCE_FRAGMENTS, module, MODULE)
    checked += _expect(ADD_FRAGMENTS, module, MODULE)
    checked += _expect(IDENTITY_FRAGMENTS, module, MODULE)
    checked += _expect(AGGREGATE_FRAGMENTS, module, MODULE)
    # 先按回合过滤再建桶：被过滤的记录不能产生空桶或压缩策略。
    checked += _ordered(
        (
            "if active_turn_ids is not None and turn_id not in active_turn_ids:",
            "bucket = turns.get(turn_id)",
        ),
        module,
        MODULE,
    )
    # 费用没有可信价目来源：任何非 None 的 costUsd 字面量都意味着伪造或回归。
    if '"costUsd": 0' in module or '["costUsd"] = ' in module:
        raise ValueError(f"{MODULE} 的费用必须保持不可用")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_usage()
    except ValueError as error:
        print(f"用量汇总核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量汇总一致：{checked} 项校验、来源与缓存防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
