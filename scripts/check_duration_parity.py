#!/usr/bin/env python3
"""核对会话导出与桌面界面的时长文案是否保持同一口径。

内核 `session_export._duration_text` 与会话导出共用同一实现；桌面通知、回合耗时与
界面共用 `packages/shared` 的 `formatDurationMs`。两处必须同样按毫秒四舍五入到秒，
使用相同的秒 / 分 / 小时阈值、剩余秒与剩余分分支和中文标签，否则同一次回合在导出
与界面会显示不同耗时。这里同时直接调用内核侧函数核对取整与分支。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"
SHARED = "packages/shared/src/index.ts"
TURN = "apps/desktop/src/main/turnNotification.ts"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import _duration_text  # noqa: E402

EXPORT_FRAGMENTS = (
    "def _duration_text(ms: int) -> str:",
    "shared ``formatDurationMs``",
    "seconds = (ms + 500) // 1000",
    "if seconds < 1:\n        return \"不足 1 秒\"",
    "return f\"{seconds} 秒\"",
    "minutes, rest = divmod(seconds, 60)",
    "return f\"{minutes} 分 {rest} 秒\" if rest else f\"{minutes} 分\"",
    "hours, tail = divmod(minutes, 60)",
    "return f\"{hours} 小时 {tail} 分\" if tail else f\"{hours} 小时\"",
)
SHARED_FRAGMENTS = (
    "export function formatDurationMs(ms: number): string {",
    "const seconds = Math.round(ms / 1000);",
    "if (seconds < 1) return \"不足 1 秒\";",
    "if (seconds < 60) return `${seconds} 秒`;",
    "const minutes = Math.floor(seconds / 60), rest = seconds % 60;",
    "if (minutes < 60) return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;",
    "const hours = Math.floor(minutes / 60), tail = minutes % 60;",
    "return tail ? `${hours} 小时 ${tail} 分` : `${hours} 小时`;",
)
TURN_FRAGMENTS = (
    "export const formatTurnDuration = formatDurationMs;",
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


def _expect_value(actual: str, expected: str, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"时长文案行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _behavior_checks() -> int:
    checked = _expect_value(_duration_text(0), "不足 1 秒", "0 毫秒")
    checked += _expect_value(_duration_text(499), "不足 1 秒", "499 毫秒")
    checked += _expect_value(_duration_text(500), "1 秒", "500 毫秒进位")
    checked += _expect_value(_duration_text(999), "1 秒", "999 毫秒")
    checked += _expect_value(_duration_text(1000), "1 秒", "1000 毫秒")
    checked += _expect_value(_duration_text(1499), "1 秒", "1499 毫秒")
    checked += _expect_value(_duration_text(1500), "2 秒", "1500 毫秒进位")
    checked += _expect_value(_duration_text(59000), "59 秒", "59 秒")
    checked += _expect_value(_duration_text(59499), "59 秒", "59.499 秒")
    checked += _expect_value(_duration_text(59500), "1 分", "59.5 秒进位")
    checked += _expect_value(_duration_text(60499), "1 分", "1 分以下")
    checked += _expect_value(_duration_text(60500), "1 分 1 秒", "1 分 1 秒")
    checked += _expect_value(_duration_text(89999), "1 分 30 秒", "90 秒")
    checked += _expect_value(
        _duration_text(3598499), "59 分 58 秒", "59 分 58 秒")
    checked += _expect_value(
        _duration_text(3598500), "59 分 59 秒", "59 分 59 秒")
    checked += _expect_value(
        _duration_text(3599499), "59 分 59 秒", "59 分 59 秒上限")
    checked += _expect_value(_duration_text(3599500), "1 小时", "60 分进位")
    checked += _expect_value(
        _duration_text(3604999), "1 小时", "小时分支只保留整分")
    checked += _expect_value(_duration_text(3660000), "1 小时 1 分", "1 小时 1 分")
    checked += _expect_value(_duration_text(7200000), "2 小时", "2 小时")
    checked += _expect_value(_duration_text(-1), "不足 1 秒", "负 1 毫秒")
    checked += _expect_value(_duration_text(-1000), "不足 1 秒", "负 1 秒")
    checked += _expect_value(
        _duration_text(10**12), "277777 小时 46 分", "极大值")
    return checked


def check_duration_parity() -> int:
    export = _read(EXPORT)
    shared = _read(SHARED)
    turn = _read(TURN)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    checked += _expect(SHARED_FRAGMENTS, shared, SHARED)
    checked += _expect(TURN_FRAGMENTS, turn, TURN)
    # 内核：取整 → 不足 1 秒 → 秒 → 分（剩余秒）→ 小时（剩余分）。
    checked += _ordered(
        (
            "seconds = (ms + 500) // 1000",
            "if seconds < 1:",
            "return f\"{seconds} 秒\"",
            "minutes, rest = divmod(seconds, 60)",
            "return f\"{minutes} 分 {rest} 秒\" if rest else f\"{minutes} 分\"",
            "hours, tail = divmod(minutes, 60)",
            "return f\"{hours} 小时 {tail} 分\" if tail else f\"{hours} 小时\"",
        ),
        export,
        EXPORT,
    )
    # 桌面：取整 → 不足 1 秒 → 秒 → 分（剩余秒）→ 小时（剩余分）。
    checked += _ordered(
        (
            "const seconds = Math.round(ms / 1000);",
            "if (seconds < 1) return \"不足 1 秒\";",
            "if (seconds < 60) return `${seconds} 秒`;",
            "const minutes = Math.floor(seconds / 60), rest = seconds % 60;",
            "if (minutes < 60) return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;",
            "const hours = Math.floor(minutes / 60), tail = minutes % 60;",
            "return tail ? `${hours} 小时 ${tail} 分` : `${hours} 小时`;",
        ),
        shared,
        SHARED,
    )
    # 两侧标签必须同时存在。
    for label in ("不足 1 秒", " 秒", " 分 ", " 小时 "):
        if label not in export:
            raise ValueError(f"{EXPORT} 缺少时长标签：{label}")
        if label not in shared:
            raise ValueError(f"{SHARED} 缺少时长标签：{label}")
        checked += 1
    # 内核导出至少四处调用同一个时长函数（定义之外）。
    calls = export.count("_duration_text(")
    if calls < 5:
        raise ValueError(f"{EXPORT} 的 _duration_text 调用点不足：{calls}")
    checked += 1
    # 反向断言：两侧不得改用其它取整方式。
    if "round(ms / 1000)" in export or "int(ms / 1000)" in export:
        raise ValueError(f"{EXPORT} 的时长必须按 (ms + 500) // 1000 取整")
    if "const seconds = Math.floor(ms / 1000);" in shared:
        raise ValueError(f"{SHARED} 的时长必须按 Math.round(ms / 1000) 取整")
    return checked + 1 + _behavior_checks()


def main() -> int:
    try:
        checked = check_duration_parity()
    except ValueError as error:
        print(f"时长文案双端核对失败，{error}", file=sys.stderr)
        return 2
    print(f"时长文案双端一致：{checked} 项取整、阈值、标签与行为防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
