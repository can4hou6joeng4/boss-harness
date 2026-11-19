#!/usr/bin/env python3
"""核对跨包共享工具的时间、截断与定位转发边界。

共享工具同时被渲染层、主进程、导出与通知使用，口径必须唯一：解释器与线路选择只按
去空白后的非空值判断；ISO 时间先做日历校验再交给 `Date`；时长文案与内核导出一致；
代理对截断不切开表情；码点计数与 Python 的 `len()` 一致；IPC 错误只剥固定包装；
定位载荷只在真正交付后清除。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = "packages/shared/src/index.ts"

SHARED_FRAGMENTS = (
    "const trimmed = (configured ?? \"\").trim();",
    "const trimmed = (configured ?? \"\").trim();\n  return trimmed || (venvUsable ? venvPython : \"python3\");",
    "const trimmed = (configured ?? \"\").trim();\n  return trimmed || \"openai\";",
    "return trimmed || (venvUsable ? venvPython : \"python3\");",
    "return trimmed || \"openai\";",
    "const ISO_DATE_TIME = /^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2}):(\\d{2})(?:\\.\\d+)?(?:Z|([+-])(\\d{2}):(\\d{2}))$/;",
    "const MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] as const;",
    "return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);",
    "if (![year, month, day, hour, minute, second, offsetHour, offsetMinute].every(Number.isInteger)) return false;",
    "if (month < 1 || month > 12 || day < 1 || hour > 23 || minute > 59 || second > 59) return false;",
    "if (offsetHour > 23 || offsetMinute > 59) return false;",
    "const monthDays = month === 2 && isLeapYear(year) ? 29 : MONTH_DAYS[month - 1];",
    "return monthDays !== undefined && day <= monthDays;",
    'if (typeof value !== "string") return null;',
    "const parts = ISO_DATE_TIME.exec(trimmed);",
    "if (!parts || !validIsoDateTime(parts)) return null;",
    "const at = new Date(trimmed);",
    "return Number.isNaN(at.getTime()) ? null : at;",
    "if (Number.isNaN(at.getTime())) return \"\";",
    "return `${at.getFullYear()}-${pad2(at.getMonth() + 1)}-${pad2(at.getDate())}`;",
    "const at = parseIsoDateTime(iso);",
    "const reference = Number.isFinite(now) ? now : Date.now();",
    "const seconds = Math.max(0, Math.floor((reference - then) / 1000));",
    'if (seconds < 60) return "刚刚";',
    "if (minutes < 60) return `${minutes} 分钟前`;",
    "if (hours < 24) return `${hours} 小时前`;",
    "if (days < 30) return `${days} 天前`;",
    "return formatLocalDate(new Date(then));",
    "const seconds = Math.round(ms / 1000);",
    'if (seconds < 1) return "不足 1 秒";',
    "if (seconds < 60) return `${seconds} 秒`;",
    "const minutes = Math.floor(seconds / 60), rest = seconds % 60;",
    "if (minutes < 60) return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;",
    "const hours = Math.floor(minutes / 60), tail = minutes % 60;",
    "return tail ? `${hours} 小时 ${tail} 分` : `${hours} 小时`;",
    "const limit = Math.min(Math.floor(end), text.length);",
    "if (!Number.isFinite(limit) || limit <= 0) return \"\";",
    "const last = text.charCodeAt(limit - 1);",
    "return text.slice(0, last >= 0xd800 && last <= 0xdbff ? limit - 1 : limit);",
    "if (code >= 0xd800 && code <= 0xdbff && index + 1 < text.length) {",
    "if (next >= 0xdc00 && next <= 0xdfff) index += 1;",
    "return text.length <= max ? text : `${safeSlice(text, max - 1)}…`;",
    "return message.replace(/^Error invoking remote method '[^']+': (?:Error|HarnessRpcError): /, \"\");",
    "const listeners = new Set<(target: T) => void>();",
    "let pending: { target: T } | null = null;",
    "if (!listeners.size) {",
    "pending = { target };",
    "pending = null;",
    "for (const listener of listeners) listener(target);",
    "listeners.add(listener);",
    "const scheduled = pending;",
    "if (scheduled) {",
    "queueMicrotask(() => {",
    "if (pending !== scheduled || !listeners.size) return;",
    "for (const current of listeners) current(scheduled.target);",
    "return () => { listeners.delete(listener); };",
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


def check_shared_utils() -> int:
    shared = _read(SHARED)
    checked = 0
    checked += _expect(SHARED_FRAGMENTS, shared, SHARED)
    # ISO 解析：外形匹配 → 日历字段校验 → 才交给 Date。
    checked += _ordered(
        (
            "const parts = ISO_DATE_TIME.exec(trimmed);",
            "if (!parts || !validIsoDateTime(parts)) return null;",
            "const at = new Date(trimmed);",
            "return Number.isNaN(at.getTime()) ? null : at;",
        ),
        shared,
        SHARED,
    )
    # 相对时间：从秒开始逐级取整，满 30 天回退本机日期。
    checked += _ordered(
        (
            "const seconds = Math.max(0, Math.floor((reference - then) / 1000));",
            'if (seconds < 60) return "刚刚";',
            "if (minutes < 60) return",
            "if (hours < 24) return",
            "if (days < 30) return",
            "return formatLocalDate(new Date(then));",
        ),
        shared,
        SHARED,
    )
    # 定位转发：无订阅者时缓存；订阅后微任务交付；交付成功才清除。
    checked += _ordered(
        (
            "if (!listeners.size) {",
            "pending = { target };",
            "const scheduled = pending;",
            "queueMicrotask(() => {",
            "if (pending !== scheduled || !listeners.size) return;\n          pending = null;",
        ),
        shared,
        SHARED,
    )
    # 反向断言：不得把时长四舍五入成负值、截断不得切开高代理项、定位缓存不得在交付前清除。
    if "Math.round(ms / 1000)" not in shared:
        raise ValueError(f"{SHARED} 的时长文案必须按毫秒四舍五入")
    if "last >= 0xd800 && last <= 0xdbff ? limit - 1 : limit" not in shared:
        raise ValueError(f"{SHARED} 的截断必须避开代理对")
    if "pending = null;\n      for (const listener of listeners) listener(target);" not in shared:
        raise ValueError(f"{SHARED} 的定位转发必须先清除待回放再交付")
    return checked + 1


def main() -> int:
    try:
        checked = check_shared_utils()
    except ValueError as error:
        print(f"共享工具边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"共享工具边界一致：{checked} 项时间、截断与定位防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
