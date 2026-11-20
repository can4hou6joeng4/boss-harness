#!/usr/bin/env python3
"""核对用量 CSV 导出的公式防护、RFC 4180 转义与未知字段语义。

用量弹窗的「复制 CSV」会把已经加载的用量写进剪贴板，通常粘贴到电子表格。
单元格必须以单引号压制会被当成公式的前缀，含分隔符或换行时按 RFC 4180
加引号并翻倍内部双引号；没有已验证请求时不能把未知写成 0，费用没有价目
来源不输出。这里固定这些安全与格式契约，避免重构把防护或行序改掉。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORT = "apps/desktop/src/renderer/src/data/usageReport.ts"

FRAGMENTS = (
    'import { safeSlice } from "@boss-harness/shared";',
    "export const USAGE_REASONS: Record<string, string> = {",
    'missing: "未上报用量", invalidType: "字段类型错误", negative: "含负数", outOfRange: "超出合理范围",',
    'inconsistent: "字段互相矛盾", zero: "全部为零", unknownProvider: "未知 provider",',
    "export const USAGE_JOB_REASONS: Record<string, string> = {",
    'threshold: "触达阈值", budget: "预算不足", overflow: "上下文溢出",',
    'if (job.kind === "branchSummary") return "分支摘要";',
    'if (job.kind === "compaction") return job.reason ? "自动压缩" : "手动压缩";',
    'return job.origin === "user" ? "用户摘要" : job.origin === "model" ? "模型摘要" : "摘要任务";',
    "return bucket.unreportedRequests ?? 0;",
    "return bucket.verifiedRequests === 0 || value === null ? null : value;",
    "const known = Object.prototype.hasOwnProperty.call(USAGE_REASONS, reason) ? USAGE_REASONS[reason] : undefined;",
    "return known ?? reason;",
    'const value = (text ?? "").replace(/\\s+/g, " ").trim();',
    "if (!value) return fallback;",
    'return value.length > 40 ? safeSlice(value, 40) + "…" : value;',
    "export const USAGE_CSV_COLUMNS = [",
    '"类别", "回合", "说明", "模型", "provider", "请求", "计入请求", "未计入请求", "未上报请求",',
    '"输入", "未缓存输入", "缓存读取", "缓存写入", "输出", "推理", "未计入原因",',
    "] as const;",
    "const FORMULA_PREFIX = /^[=+\\-@\\t\\r]/;",
    'if (value === null || value === "") return "";',
    "const text = String(value);",
    "const safe = FORMULA_PREFIX.test(text) ? `'${text}` : text;",
    'return /[",\\r\\n]/.test(safe) ? `"${safe.replace(/"/g, \'""\')}"` : safe;',
    "const emptyRow = (): Cell[] => Array.from({ length: USAGE_CSV_COLUMNS.length }, () => null);",
    "cells[0] = category;",
    "cells[2] = note;",
    "const reasonText = usageReasonEntries(bucket).map(({ label, count }) => `${label} ${count} 次`).join(\"、\");",
    "const jobs = data.summaryJobs ?? [];",
    "const timing = turnTimingLabel(turn);",
    'const note = [usageClip(context.inputOf(turn.turnId), turn.turnId), timing ?? ""].filter(Boolean).join(" · ");',
    'note: data.view === "branch" ? "当前分支（只统计当前分支上的回合）" : "全部记录（包含已切离分支上的回合）",',
    "const total = data.summaryJobCount ?? jobs.length;",
)

ORDERED = (
    # 摘要任务明细说明列的组成顺序：来源、原因、当前生效、覆盖回合，空段不输出。
    (
        "usageJobSource(job),",
        "job.reason ? USAGE_JOB_REASONS[job.reason] ?? job.reason : \"\",",
        'job.active ? "当前生效" : "",',
        'job.throughTurnId && job.throughTurnId !== job.turnId ? `摘要至 ${context.turnLabel(job.throughTurnId)}` : "",',
        '.filter(Boolean).join(" · ") || job.jobId;',
    ),
    # 合计行字段顺序必须与表头一致。
    (
        "options.category,",
        'options.turn ?? "",',
        'options.note ?? "",',
        '(options.models ?? []).join("、"),',
        '(options.providers ?? []).join("、"),',
        "bucket.requests,",
        "bucket.verifiedRequests,",
        "bucket.unverifiedRequests,",
        "usageUnreported(bucket),",
        "usageAmount(bucket, bucket.promptTokens),",
        "usageAmount(bucket, bucket.uncachedInputTokens),",
        "usageAmount(bucket, bucket.cacheReadTokens),",
        "usageAmount(bucket, bucket.cacheWriteTokens),",
        "usageAmount(bucket, bucket.outputTokens),",
        "usageAmount(bucket, bucket.reasoningTokens),",
        "reasonText,",
    ),
    # 行序：合计、缓存未命中、摘要任务、明细、每回合，最后是两类截断说明。
    (
        "rows.push(bucketRow(data.totals, {",
        "if (data.cacheWaste) {",
        'rows.push(noteRow("缓存未命中",',
        "if (data.summaryTasks.requests > 0) {",
        'rows.push(bucketRow(data.summaryTasks, { category: "摘要任务合计"',
        "for (const job of jobs) {",
        "rows.push(bucketRow(job, {",
        "for (const turn of data.turns) {",
        "rows.push(bucketRow(turn, {",
        "if (data.truncated) {",
        'rows.push(noteRow("说明", `每回合用量仅包含前 ${data.turns.length} 个，共 ${data.turnCount} 个有记录的回合`));',
        "if (data.summaryJobsTruncated) {",
        'rows.push(noteRow("说明", `摘要任务明细仅包含最近 ${jobs.length} 个，共 ${total} 个`));',
        'const lines = [USAGE_CSV_COLUMNS.join(","), ...rows.map(row => row.map(cell).join(","))];',
        'return lines.join("\\r\\n") + "\\r\\n";',
    ),
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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_usage_report() -> int:
    report = _read(REPORT)
    checked = 0
    checked += _expect(FRAGMENTS, report, REPORT)
    for group in ORDERED:
        checked += _ordered(group, report, REPORT)
    # 反向断言：公式前缀只认一份正则；单元格不得直接返回原文；原因键不得绕过自有属性检查；
    # 费用没有价目来源，不得出现在表头。
    if report.count("FORMULA_PREFIX") != 2:
        raise ValueError(f"{REPORT} 的 FORMULA_PREFIX 只能声明一次并在 cell 中判断一次")
    if "return String(value)" in report:
        raise ValueError(f"{REPORT} 的单元格必须经过公式前缀与 RFC 4180 转义，不得直接返回原文")
    if re.search(r"USAGE_REASONS\[reason\]\s*\?\?\s*reason", report):
        raise ValueError(f"{REPORT} 的原因键必须先用 hasOwnProperty 判定，不得直接读取原型链")
    columns = re.search(r"USAGE_CSV_COLUMNS = \[(.*?)\] as const;", report, re.DOTALL)
    if not columns:
        raise ValueError(f"{REPORT} 缺少 USAGE_CSV_COLUMNS 定义")
    if "费用" in columns.group(1) or "cost" in columns.group(1).lower():
        raise ValueError(f"{REPORT} 不输出费用列：没有价目来源")
    return checked + 3


def main() -> int:
    try:
        checked = check_usage_report()
    except ValueError as error:
        print(f"用量 CSV 核对失败，{error}", file=sys.stderr)
        return 2
    print(f"用量 CSV 一致：{checked} 项公式防护、转义与未知字段语义")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
