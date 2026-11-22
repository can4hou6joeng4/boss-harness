#!/usr/bin/env python3
"""核对会话导出的时间戳解析、耗时与审批期限展示。

导出回合头部的 `durationMs` 与审批记录的 `deadline` 直接面向用户，输入却来自可被外部
改写的持久记录：无时区时间、反转的起止、`10**400` 这类整数都可能在导出路径上抛出
异常或产生误导性的耗时与期限。这里静态固定三个时间辅助函数的解析、回退与调用点，
并直接调用它们核对无时区、`Z`、偏移、非法值、倒序、跨时区、布尔、非有限与非正期限
的边界。不读写导出文件，也不启动模型或招聘平台。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/session_export.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import (  # noqa: E402
    _deadline_text,
    _parse_timestamp,
    _timestamp_duration,
)

PARSE_FRAGMENTS = (
    "if not isinstance(value, str) or not value:",
    'text = value[:-1] + "+00:00" if value.endswith("Z") else value',
    "except ValueError:\n        return None",
    "return parsed if parsed.tzinfo is not None else None",
)
DURATION_FRAGMENTS = (
    "first, last = _parse_timestamp(start), _parse_timestamp(end)",
    "if first is None or last is None or last < first:",
    "return int(round((last - first).total_seconds() * 1000))",
)
DEADLINE_FRAGMENTS = (
    "if type(value) not in (int, float):",
    "if not math.isfinite(float(value)) or value <= 0:",
    'return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds")',
    "except (OverflowError, OSError, ValueError):",
)
WIRING_FRAGMENTS = (
    'duration = _timestamp_duration(turn.get("startedAt"), turn.get("completedAt"))',
    '**({"durationMs": duration} if duration is not None else {}),',
    'deadline = _deadline_text(approval.get("deadline"))',
    'record["deadline"] = deadline',
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}：期望 {expected!r}，实际 {actual!r}")


def _behavior_checks() -> int:
    checked = 0
    # 解析：只有带时区的 ISO 时间可用；`Z` 与显式偏移等价，朴素时间与非字符串一律未知。
    _expect_value(_parse_timestamp(None), None, "解析 None")
    checked += 1
    _expect_value(_parse_timestamp(""), None, "解析空串")
    checked += 1
    for value in (123, {}, ["2026-01-02T03:04:05Z"]):
        _expect_value(_parse_timestamp(value), None, f"解析非字符串 {value!r}")
        checked += 1
    for value in ("not-a-date", " ", "2026-13-02T03:04:05Z"):
        _expect_value(_parse_timestamp(value), None, f"解析非法时间 {value!r}")
        checked += 1
    _expect_value(_parse_timestamp("2026-01-02T03:04:05"), None, "解析无时区时间")
    checked += 1
    _expect_value(_parse_timestamp("2026-01-02"), None, "解析无时区日期")
    checked += 1
    utc = _parse_timestamp("2026-01-02T03:04:05Z")
    _expect_value(utc, datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc), "解析 Z 后缀")
    checked += 1
    offset = _parse_timestamp("2026-01-02T03:04:05+08:00")
    _expect_value(offset, datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8))),
                  "解析显式偏移")
    checked += 1
    fractional = _parse_timestamp("2026-01-02T03:04:05.500Z")
    _expect_value(fractional, datetime(2026, 1, 2, 3, 4, 5, 500_000, tzinfo=timezone.utc),
                  "解析毫秒后缀")
    checked += 1
    _expect_value(utc.utcoffset(), timedelta(0), "Z 后缀时区")
    checked += 1
    _expect_value(offset.utcoffset(), timedelta(hours=8), "偏移时区")
    checked += 1
    # 耗时：两端都可用且不倒序时才给出毫秒；倒序、朴素值或坏值都未知。
    _expect_value(_timestamp_duration("2026-01-02T03:04:05Z", "2026-01-02T03:04:05Z"), 0, "同时刻耗时")
    checked += 1
    _expect_value(_timestamp_duration("2026-01-02T03:04:05Z", "2026-01-02T03:04:06.500Z"), 1500,
                  "带毫秒耗时")
    checked += 1
    _expect_value(_timestamp_duration("2026-01-02T03:04:05Z", "2026-01-02T03:04:05.001500Z"), 2,
                  "耗时四舍五入")
    checked += 1
    _expect_value(_timestamp_duration("2026-01-02T03:04:05Z", "2026-01-02T11:04:05+08:00"), 0,
                  "跨时区同一时刻")
    checked += 1
    _expect_value(_timestamp_duration("2026-01-02T03:04:06Z", "2026-01-02T03:04:05Z"), None,
                  "倒序耗时")
    checked += 1
    for start, end in (("2026-01-02T03:04:05", "2026-01-02T03:04:06Z"),
                       ("bad", "2026-01-02T03:04:06Z"),
                       ("2026-01-02T03:04:05Z", None),
                       (None, None)):
        _expect_value(_timestamp_duration(start, end), None, f"坏值耗时 {start!r} -> {end!r}")
        checked += 1
    # 期限：只接受有限的 Unix 秒；布尔、非有限、非正与溢出值一律按无期限处理。
    for value in (None, "123", True, False, 0, -1, -1.5,
                  float("nan"), float("inf"), float("-inf"), 10**400, 1e300):
        _expect_value(_deadline_text(value), None, f"无效期限 {value!r}"[:60])
        checked += 1
    _expect_value(_deadline_text(1_700_000_000), "2023-11-14T22:13:20+00:00", "整数期限")
    checked += 1
    _expect_value(_deadline_text(1_700_000_000.9), "2023-11-14T22:13:20+00:00", "小数期限截断")
    checked += 1
    _expect_value(_deadline_text(1.5), "1970-01-01T00:00:01+00:00", "早期期限")
    checked += 1
    return checked


def check_export_timestamps() -> int:
    module = _read(MODULE)
    checked = 0
    for label, fragments in (("解析", PARSE_FRAGMENTS), ("耗时", DURATION_FRAGMENTS),
                             ("期限", DEADLINE_FRAGMENTS), ("调用点", WIRING_FRAGMENTS)):
        checked += _expect(fragments, module, f"{MODULE}（{label}）")
    checked += _behavior_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_export_timestamps()
    except ValueError as error:
        print(f"导出时间戳边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出时间戳边界一致：{checked} 项解析、耗时与期限防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
