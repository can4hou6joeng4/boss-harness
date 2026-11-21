#!/usr/bin/env python3
"""核对 provider 用量汇总的校验、来源、任务与缓存估算边界。

usage.py 决定 thread/usage/read 与导出的计数：只有类型、范围与 provider 语义
都可验证的记录才计入合计，来源标识有界，费用不可知，缓存未命中只按 Pi 口径
估算。任一校验、来源上限、任务元数据或缓存口径被删改不会触发构建失败，因此
既静态固定关键片段，也直接构造用量记录核对归一化、汇总、任务与估算结果。
不访问网络、模型或招聘平台。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/usage.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.usage import (  # noqa: E402
    CACHE_MISS_FLOOR,
    MAX_PROVENANCE_ITEMS,
    MAX_REQUEST_TOKENS,
    MAX_SUMMARY_JOBS,
    bounded_identifier,
    summarize_usage,
    verify_usage,
)

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
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"用量汇总行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _usage(provider: str = "openai", model: str = "model-a", **values) -> dict:
    usage = {"input": 100, "output": 10, "cache_read": 0, "cache_write": 0}
    usage.update(values)
    return {"provider": provider, "model": model, "usage": usage}


def _entry(kind: str, **payload) -> dict:
    return {"type": kind, "payload": payload}


def _behavior_checks() -> int:
    checked = 0

    checked += _expect_value(
        verify_usage("google", {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0}),
        (None, "unknownProvider"), "未知 provider")
    checked += _expect_value(
        verify_usage(None, {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0}),
        (None, "unknownProvider"), "非字符串 provider")
    checked += _expect_value(verify_usage("openai", None), (None, "missing"), "缺失 usage")
    checked += _expect_value(verify_usage("openai", []), (None, "invalidType"), "非对象 usage")
    checked += _expect_value(
        verify_usage("openai", {"input": 1, "output": 1, "cache_read": 0}),
        (None, "invalidType"), "缺少字段")
    checked += _expect_value(
        verify_usage("openai", {"input": True, "output": 1, "cache_read": 0, "cache_write": 0}),
        (None, "invalidType"), "布尔字段")
    checked += _expect_value(
        verify_usage("openai", {"input": 1.0, "output": 1, "cache_read": 0, "cache_write": 0}),
        (None, "invalidType"), "浮点字段")
    checked += _expect_value(
        verify_usage("openai", {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0,
                                "reasoning": "1"}),
        (None, "invalidType"), "reasoning 类型")
    checked += _expect_value(
        verify_usage("openai", {"input": -1, "output": 0, "cache_read": 0, "cache_write": 0}),
        (None, "negative"), "负输入")
    checked += _expect_value(
        verify_usage("openai", {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0,
                                "reasoning": -1}),
        (None, "negative"), "负 reasoning")
    checked += _expect_value(
        verify_usage("openai", {"input": MAX_REQUEST_TOKENS + 1, "output": 0, "cache_read": 0,
                                "cache_write": 0}),
        (None, "outOfRange"), "单字段超限")
    checked += _expect_value(
        verify_usage("openai", {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0,
                                "reasoning": MAX_REQUEST_TOKENS + 1}),
        (None, "outOfRange"), "reasoning 超限")
    checked += _expect_value(
        verify_usage("openai", {"input": 10, "output": 1, "cache_read": 11, "cache_write": 0}),
        (None, "inconsistent"), "缓存大于输入")
    checked += _expect_value(
        verify_usage("openai", {"input": 10, "output": 5, "cache_read": 0, "cache_write": 0,
                                "reasoning": 6}),
        (None, "inconsistent"), "reasoning 大于输出")
    checked += _expect_value(
        verify_usage("openai", {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}),
        (None, "zero"), "全零记录")
    checked += _expect_value(
        verify_usage("openai", {"input": 100, "output": 30, "cache_read": 20, "cache_write": 5,
                                "reasoning": 10}),
        ({"promptTokens": 100, "uncachedInputTokens": 80, "outputTokens": 30,
          "cacheReadTokens": 20, "cacheWriteTokens": None, "reasoningTokens": 10}, None),
        "OpenAI 归一化")
    checked += _expect_value(
        verify_usage("openai", {"input": 100, "output": 0, "cache_read": 100, "cache_write": 0}),
        ({"promptTokens": 100, "uncachedInputTokens": 0, "outputTokens": 0,
          "cacheReadTokens": 100, "cacheWriteTokens": None, "reasoningTokens": None}, None),
        "OpenAI 全缓存命中")
    checked += _expect_value(
        verify_usage("openai", {"input": MAX_REQUEST_TOKENS, "output": 0, "cache_read": 0,
                                "cache_write": 0}),
        ({"promptTokens": MAX_REQUEST_TOKENS, "uncachedInputTokens": MAX_REQUEST_TOKENS,
          "outputTokens": 0, "cacheReadTokens": 0, "cacheWriteTokens": None,
          "reasoningTokens": None}, None), "OpenAI 上限边界")
    checked += _expect_value(
        verify_usage("anthropic", {"input": 100, "output": 30, "cache_read": 20,
                                   "cache_write": 5, "reasoning": 7}),
        ({"promptTokens": 125, "uncachedInputTokens": 100, "outputTokens": 30,
          "cacheReadTokens": 20, "cacheWriteTokens": 5, "reasoningTokens": None}, None),
        "Anthropic 归一化")
    checked += _expect_value(
        verify_usage("anthropic", {"input": MAX_REQUEST_TOKENS, "output": 0, "cache_read": 1,
                                   "cache_write": 0}),
        (None, "outOfRange"), "Anthropic 合计超限")
    checked += _expect_value(
        verify_usage("anthropic", {"input": 1, "output": 1, "cache_read": 0, "cache_write": 0,
                                   "reasoning": 5}),
        ({"promptTokens": 1, "uncachedInputTokens": 1, "outputTokens": 1,
          "cacheReadTokens": 0, "cacheWriteTokens": 0, "reasoningTokens": None}, None),
        "Anthropic 忽略 reasoning")
    checked += _expect_value(
        verify_usage("anthropic", {"input": 0, "output": 30, "cache_read": 0, "cache_write": 0}),
        ({"promptTokens": 0, "uncachedInputTokens": 0, "outputTokens": 30,
          "cacheReadTokens": 0, "cacheWriteTokens": 0, "reasoningTokens": None}, None),
        "Anthropic 空提示")
    checked += _expect_value(
        verify_usage("anthropic", {"input": 0, "output": 0, "cache_read": 0, "cache_write": 5}),
        ({"promptTokens": 5, "uncachedInputTokens": 0, "outputTokens": 0,
          "cacheReadTokens": 0, "cacheWriteTokens": 5, "reasoningTokens": None}, None),
        "Anthropic 仅缓存写")

    checked += _expect_value(bounded_identifier(""), None, "空标识")
    checked += _expect_value(bounded_identifier(1), None, "非字符串标识")
    checked += _expect_value(bounded_identifier("t" * 128), "t" * 128, "标识长度边界")
    checked += _expect_value(bounded_identifier("t" * 129), None, "标识超长")
    checked += _expect_value(bounded_identifier("\ud800"), "�", "标识代理项降级")
    checked += _expect_value(bounded_identifier(" "), " ", "标识保留空白")

    empty = summarize_usage([])
    checked += _expect_value(
        (empty["turns"], empty["summaryTasks"]["requests"], empty["totals"]["requests"],
         empty["summaryJobCount"], empty["summaryJobsTruncated"], empty["summaryJobs"]),
        ([], 0, 0, 0, False, []), "空汇总")
    checked += _expect_value(
        empty["cacheWaste"], {"missedTokens": 0, "missCount": 0}, "空缓存估算")

    single = summarize_usage([_entry("model_usage", turnId="t1", **_usage())])
    bucket = single["turns"][0]
    checked += _expect_value(
        (len(single["turns"]), bucket["turnId"], bucket["requests"], bucket["verifiedRequests"],
         bucket["unverifiedRequests"], bucket["unreportedRequests"], bucket["unverifiedReasons"],
         bucket["providers"], bucket["models"]),
        (1, "t1", 1, 1, 0, 0, {}, ["openai"], ["model-a"]), "单请求桶")
    checked += _expect_value(
        (bucket["promptTokens"], bucket["uncachedInputTokens"], bucket["outputTokens"],
         bucket["cacheReadTokens"], bucket["cacheWriteTokens"], bucket["reasoningTokens"],
         bucket["costUsd"], bucket["costSource"]),
        (100, 100, 10, 0, None, None, None, "unavailable"), "单请求字段")
    checked += _expect_value(
        (single["totals"]["promptTokens"], single["totals"]["outputTokens"],
         single["totals"]["requests"]),
        (100, 10, 1), "单请求合计")
    checked += _expect_value("cacheWaste" in single, True, "日志视图缓存估算")

    accumulated = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(cache_read=20)),
        _entry("model_usage", turnId="t1", **_usage(cache_read=5, output=4)),
    ])
    bucket = accumulated["turns"][0]
    checked += _expect_value(
        (bucket["requests"], bucket["verifiedRequests"], bucket["promptTokens"],
         bucket["outputTokens"], bucket["cacheReadTokens"]),
        (2, 2, 200, 14, 25), "同回合累计")

    missing = summarize_usage(
        [_entry("model_usage", turnId="t1", provider="openai", model="m", usage=None)])
    bucket = missing["turns"][0]
    checked += _expect_value(
        (bucket["unverifiedRequests"], bucket["unreportedRequests"], bucket["unverifiedReasons"],
         bucket["verifiedRequests"], bucket["promptTokens"]),
        (1, 1, {"missing": 1}, 0, 0), "缺失用量原因")

    broken = summarize_usage(
        [_entry("model_usage", turnId="t1", provider="openai", model="m", usage=[])])
    bucket = broken["turns"][0]
    checked += _expect_value(
        (bucket["unverifiedReasons"], bucket["unreportedRequests"]),
        ({"invalidType": 1}, 0), "类型错误不记未上报")

    skipped = summarize_usage([
        _entry("model_usage", turnId=None, **_usage()),
        _entry("model_usage", turnId=5, **_usage()),
        {"type": "model_usage", "payload": None},
        {"type": "message", "payload": {}},
    ])
    checked += _expect_value(
        (skipped["turns"], skipped["totals"]["requests"]), ([], 0), "无效回合跳过")

    filtered = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage()),
         _entry("model_usage", turnId="t2", **_usage(output=99))],
        active_turn_ids={"t1"})
    checked += _expect_value(
        ([item["turnId"] for item in filtered["turns"]], filtered["totals"]["outputTokens"],
         "cacheWaste" in filtered), (["t1"], 10, False), "分支视图过滤")
    branch_tasks = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage()),
         _entry("context_summary_usage", **_usage())],
        active_turn_ids={"t2"})
    checked += _expect_value(
        (branch_tasks["turns"], branch_tasks["summaryTasks"]["requests"]), ([], 1),
        "分支视图仍计摘要任务")

    summarized = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage()),
        _entry("context_summary_usage", **_usage(input=50, output=5)),
    ])
    checked += _expect_value(
        (summarized["summaryTasks"]["requests"], summarized["summaryTasks"]["verifiedRequests"],
         summarized["summaryTasks"]["promptTokens"], "providers" in summarized["summaryTasks"]),
        (1, 1, 50, False), "摘要任务桶")
    checked += _expect_value(
        (summarized["totals"]["requests"], summarized["totals"]["promptTokens"],
         summarized["totals"]["outputTokens"], len(summarized["turns"])),
        (2, 150, 15, 1), "摘要计入合计")

    summary_bad = summarize_usage(
        [_entry("context_summary_usage", provider="openai", model="m", usage=None)])
    checked += _expect_value(
        (summary_bad["summaryTasks"]["unverifiedReasons"], summary_bad["totals"]["requests"]),
        ({"missing": 1}, 1), "摘要未验证原因")

    capped = summarize_usage(
        [_entry("model_usage", turnId="t1", provider=f"p{index}", model=f"m{index}", usage=None)
         for index in range(10)])["turns"][0]
    checked += _expect_value(
        (capped["providers"], capped["models"], capped["unverifiedRequests"]),
        ([f"p{index}" for index in range(MAX_PROVENANCE_ITEMS)],
         [f"m{index}" for index in range(MAX_PROVENANCE_ITEMS)], 10), "来源上限")

    provenance = summarize_usage([
        _entry("model_usage", turnId="t1", provider="p" * 64, model="m" * 200, usage=None),
        _entry("model_usage", turnId="t1", provider="p" * 64, model="m" * 200, usage=None),
        _entry("model_usage", turnId="t1", provider="p" * 65, model="m" * 201, usage=None),
        _entry("model_usage", turnId="t1", provider="a\ud800", model="", usage=None),
    ])["turns"][0]
    checked += _expect_value(
        (provenance["providers"], provenance["models"]),
        (["p" * 64, "a�"], ["m" * 200]), "来源去重与降级")

    jobs = summarize_usage([
        _entry("context_summary_usage", jobId="j1", **_usage(input=50)),
        _entry("context_checkpoint", summaryJobId="j1", turnId="t3", throughTurnId="t2",
               reason="threshold", origin="user"),
        _entry("context_summary_usage", jobId="j2", **_usage(input=20)),
        _entry("branch_summary", summaryJobId="j2", targetTurnId="t9"),
    ])
    by_id = {job["jobId"]: job for job in jobs["summaryJobs"]}
    checked += _expect_value(
        (jobs["summaryJobCount"], jobs["summaryJobsTruncated"], len(by_id)), (2, False, 2),
        "任务计数")
    checked += _expect_value(
        (by_id["j1"]["kind"], by_id["j1"]["turnId"], by_id["j1"]["throughTurnId"],
         by_id["j1"]["reason"], by_id["j1"]["origin"], by_id["j1"]["promptTokens"]),
        ("compaction", "t3", "t2", "threshold", "user", 50), "压缩任务元数据")
    checked += _expect_value(
        (by_id["j2"]["kind"], by_id["j2"]["turnId"], by_id["j2"]["throughTurnId"],
         by_id["j2"]["reason"], by_id["j2"]["origin"], by_id["j2"]["promptTokens"]),
        ("branchSummary", "t9", None, None, "model", 20), "分支摘要元数据")
    checked += _expect_value(
        (by_id["j1"]["providers"], by_id["j1"]["models"]), (["openai"], ["model-a"]),
        "任务来源")

    merged_job = summarize_usage([
        _entry("context_checkpoint", summaryJobId="j3", turnId="t1", reason="budget"),
        _entry("context_checkpoint", summaryJobId="j3", throughTurnId="t0", reason="overflow"),
        _entry("context_summary_usage", jobId="j3", **_usage()),
    ])["summaryJobs"][0]
    checked += _expect_value(
        (merged_job["turnId"], merged_job["throughTurnId"], merged_job["reason"],
         merged_job["origin"]),
        ("t1", "t0", "budget", None), "任务元数据补充")

    invalid_job = summarize_usage([
        _entry("context_checkpoint", summaryJobId="j4", reason="manual", origin="system"),
        _entry("context_summary_usage", jobId="j4", **_usage()),
    ])["summaryJobs"][0]
    checked += _expect_value(
        (invalid_job["reason"], invalid_job["origin"], invalid_job["turnId"]),
        (None, None, None), "任务元数据白名单")

    active = summarize_usage([
        _entry("context_summary_usage", jobId="j1", **_usage()),
        _entry("context_summary_usage", jobId="j2", **_usage()),
    ], active_job_id="j1")
    checked += _expect_value(
        [(job["jobId"], job.get("active")) for job in active["summaryJobs"]],
        [("j1", True), ("j2", None)], "活动任务标记")
    absent = summarize_usage(
        [_entry("context_summary_usage", jobId="j1", **_usage())], active_job_id="other")
    checked += _expect_value("active" in absent["summaryJobs"][0], False, "非当前任务不标记")

    many = summarize_usage(
        [_entry("context_summary_usage", jobId=f"j{index}", **_usage())
         for index in range(MAX_SUMMARY_JOBS + 1)])
    checked += _expect_value(
        (many["summaryJobCount"], len(many["summaryJobs"]), many["summaryJobsTruncated"],
         many["summaryJobs"][0]["jobId"], many["summaryJobs"][-1]["jobId"]),
        (MAX_SUMMARY_JOBS + 1, MAX_SUMMARY_JOBS, True, "j1", f"j{MAX_SUMMARY_JOBS}"), "任务截断")
    exact = summarize_usage(
        [_entry("context_summary_usage", jobId=f"j{index}", **_usage())
         for index in range(MAX_SUMMARY_JOBS)])
    checked += _expect_value(
        (exact["summaryJobCount"], exact["summaryJobsTruncated"]), (MAX_SUMMARY_JOBS, False),
        "任务上限边界")

    bad_job = summarize_usage([
        _entry("context_summary_usage", jobId="j" * 129, **_usage()),
        _entry("context_summary_usage", **_usage()),
    ])
    checked += _expect_value(
        (bad_job["summaryJobCount"], bad_job["totals"]["requests"]), (0, 2), "无效任务号不进桶")

    policy = {"enabled": True, "triggerPercent": 80, "keepRecentTokens": 5000}
    with_policy = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage())], turn_policies={"t1": policy})
    checked += _expect_value(with_policy["turns"][0]["compactionPolicy"], policy, "压缩策略附加")
    degraded = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage())],
        turn_policies={"t1": {"enabled": True, "model": "\ud800"}})
    checked += _expect_value(
        degraded["turns"][0]["compactionPolicy"], {"enabled": True, "model": "�"},
        "压缩策略降级")
    invalid_policy = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage())],
        turn_policies={"t1": {"triggerPercent": 0}})
    checked += _expect_value(
        "compactionPolicy" in invalid_policy["turns"][0], False, "非法策略省略")
    other_policy = summarize_usage(
        [_entry("model_usage", turnId="t1", **_usage())], turn_policies={"t2": policy})
    checked += _expect_value(
        "compactionPolicy" in other_policy["turns"][0], False, "仅匹配回合")

    miss = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(miss, {"missedTokens": 5000, "missCount": 1}, "缓存未命中累计")
    floor = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1",
               **_usage(input=5000, output=1, cache_read=5000 - CACHE_MISS_FLOOR)),
    ])["cacheWaste"]
    checked += _expect_value(floor, {"missedTokens": 0, "missCount": 0}, "噪声下限不计")
    above = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1",
               **_usage(input=5000, output=1, cache_read=5000 - CACHE_MISS_FLOOR - 1)),
    ])["cacheWaste"]
    checked += _expect_value(
        above, {"missedTokens": CACHE_MISS_FLOOR + 1, "missCount": 1}, "超过下限计一次")
    shrunk = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=10000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1", **_usage(input=3000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(shrunk, {"missedTokens": 3000, "missCount": 1}, "前缀缩短取较小值")
    repeated = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(repeated, {"missedTokens": 10000, "missCount": 2}, "连续未命中累计")
    broken_baseline = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("model_usage", turnId="t1", provider="openai", model="m", usage=None),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])
    checked += _expect_value(
        broken_baseline["cacheWaste"], {"missedTokens": 5000, "missCount": 1},
        "无效记录不重置基线")
    checked += _expect_value(
        broken_baseline["turns"][0]["unverifiedRequests"], 1, "无效记录仍计数")
    reset = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("context_checkpoint", turnId="t1", reason="threshold"),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(reset, {"missedTokens": 0, "missCount": 0}, "检查点重置基线")
    branch_reset = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1, cache_read=1)),
        _entry("branch_summary", targetTurnId="t1"),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(
        branch_reset, {"missedTokens": 0, "missCount": 0}, "分支摘要重置基线")
    zero_prompt = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=0, output=1, cache_write=5)),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(zero_prompt, {"missedTokens": 0, "missCount": 0}, "空提示不作基线")
    uncached = summarize_usage([
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
        _entry("model_usage", turnId="t1", **_usage(input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(uncached, {"missedTokens": 0, "missCount": 0}, "无缓存上报不估算")
    anthropic_cache = summarize_usage([
        _entry("model_usage", turnId="t1",
               **_usage(provider="anthropic", input=5000, output=1, cache_write=1)),
        _entry("model_usage", turnId="t1",
               **_usage(provider="anthropic", input=5000, output=1)),
    ])["cacheWaste"]
    checked += _expect_value(
        anthropic_cache, {"missedTokens": 5000, "missCount": 1}, "写缓存视为已上报")
    return checked


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
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_usage()
    except (ValueError, OSError) as error:
        print(f"用量汇总核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量汇总一致：{checked} 项结构、行为与缓存估算校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
