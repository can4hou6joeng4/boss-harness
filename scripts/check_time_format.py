#!/usr/bin/env python3
"""核对界面时间格式与会话排序键的严格解析。

界面时间固定为简体中文并按本机时区补零，不能跟随系统区域；会话排序键只接受
完整 ISO 时间，缺失或可疑值按 0 落到列表末尾。结构侧固定补零、非法时间的空串
回退、ISO 包装与排序键的零回退；行为侧把真实 `timeFormat.ts`、`sessionOrder.ts`
与共享 `shared/index.ts` 复制到临时目录、改写导入，由 Node 驱动格式化与排序键。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
TIME = "apps/desktop/src/renderer/src/data/timeFormat.ts"
ORDER = "apps/desktop/src/renderer/src/data/sessionOrder.ts"
SHARED = "packages/shared/src/index.ts"

EXPECTED = 18

NODE_SCRIPT = """\
import {
  formatIsoClock,
  formatIsoDateTime,
  formatLocalClock,
  formatLocalDateTime,
} from "./timeFormat.ts";
import { sessionUpdatedAt } from "./sessionOrder.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

// 本机时区构造，避免用例依赖运行机器的区域设置。
const local = new Date(2026, 0, 5, 4, 7, 9);
expect("日期时间补零", formatLocalDateTime(local) === "2026-01-05 04:07");
expect("日期时间非法为空", formatLocalDateTime(new Date(Number.NaN)) === "");
expect("时刻补零", formatLocalClock(local) === "04:07:09");
expect("时刻非法为空", formatLocalClock(new Date(Number.NaN)) === "");

const utc = new Date("2026-11-05T08:00:00Z");
expect("ISO 日期时间与 Date 一致", formatIsoDateTime("2026-11-05T08:00:00Z") === formatLocalDateTime(utc));
const offset = new Date("2026-11-05T08:00:00.123456+08:00");
expect(
  "ISO 日期时间带毫秒与偏移",
  formatIsoDateTime("2026-11-05T08:00:00.123456+08:00") === formatLocalDateTime(offset),
);
expect("ISO 前后空白被修剪", formatIsoDateTime(" 2026-11-05T08:00:00Z ") === formatLocalDateTime(utc));
expect("只有日期为空", formatIsoDateTime("2026-11-05") === "");
expect("本地空格时间为空", formatIsoDateTime("2026-11-05 08:00:00") === "");
expect("日历越界为空", formatIsoDateTime("2026-02-30T00:00:00Z") === "");
expect("24 时为空", formatIsoDateTime("2026-11-05T24:00:00Z") === "");
expect("非字符串为空", formatIsoDateTime(20261105) === "");

expect("ISO 时刻", formatIsoClock("2026-11-05T08:00:00Z") === formatLocalClock(utc));
expect("ISO 时刻无效为空", formatIsoClock("2026-11-05") === "");

expect("排序键毫秒值", sessionUpdatedAt({ updatedAt: "2026-11-05T08:00:00Z" }) === utc.getTime());
expect(
  "排序键无效为零",
  sessionUpdatedAt({ updatedAt: "2026" }) === 0 && sessionUpdatedAt({ updatedAt: "" }) === 0,
);
expect("排序键缺省为零", sessionUpdatedAt({}) === 0);
expect("排序键本地空格为零", sessionUpdatedAt({ updatedAt: "2026-11-05 08:00:00" }) === 0);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { formatLocalDate, parseIsoDateTime } from "@boss-harness/shared";',
    "export { parseIsoDateTime };",
    'const pad = (part: number) => String(part).padStart(2, "0");',
    "export function formatLocalDateTime(at: Date): string {",
    'if (Number.isNaN(at.getTime())) return "";',
    "return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;",
    "export function formatLocalClock(at: Date): string {",
    "return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;",
    "export function formatIsoDateTime(value: unknown): string {",
    "export function formatIsoClock(value: unknown): string {",
    "return at ? formatLocalDateTime(at) : \"\";",
    "return at ? formatLocalClock(at) : \"\";",
)

ORDER_FRAGMENTS = (
    'import { parseIsoDateTime } from "./timeFormat";',
    "export function sessionUpdatedAt(session: SessionItem): number {",
    "return parseIsoDateTime(session.updatedAt)?.getTime() ?? 0;",
)

ORDERED = (
    # 日期时间：先判非法，再补零输出。
    (
        "export function formatLocalDateTime(at: Date): string {",
        'if (Number.isNaN(at.getTime())) return "";',
        "return `${formatLocalDate(at)} ${pad(at.getHours())}:${pad(at.getMinutes())}`;",
    ),
    # 时刻：先判非法，再补零输出。
    (
        "export function formatLocalClock(at: Date): string {",
        'if (Number.isNaN(at.getTime())) return "";',
        "return `${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;",
    ),
    # ISO 包装：严格解析 → 格式化或空串。
    (
        "export function formatIsoDateTime(value: unknown): string {",
        "const at = parseIsoDateTime(value);",
        "return at ? formatLocalDateTime(at) : \"\";",
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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _rewrite_time(source: str) -> str:
    rewritten = source.replace(
        'import { formatLocalDate, parseIsoDateTime } from "@boss-harness/shared";',
        'import { formatLocalDate, parseIsoDateTime } from "./shared.ts";',
    )
    if 'from "./shared.ts"' not in rewritten:
        raise ValueError(f"{TIME} 的共享导入已变化，需要更新改写")
    return rewritten


def _rewrite_order(source: str) -> str:
    rewritten = source.replace('import type { SessionItem } from "./mockData";\n', "")
    rewritten = rewritten.replace(
        'import { parseIsoDateTime } from "./timeFormat";',
        'import { parseIsoDateTime } from "./timeFormat.ts";',
    )
    if 'from "./timeFormat.ts"' not in rewritten or "mockData" in rewritten:
        raise ValueError(f"{ORDER} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str, order: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, TIME)
    checked += _expect(ORDER_FRAGMENTS, order, ORDER)
    for group in ORDERED:
        checked += _ordered(group, source, TIME)
    # 反向断言：不得跟随系统区域；排序键不得用宽松解析；两个格式化函数都要判 NaN。
    if ".toLocaleString(" in source or ".toLocaleDateString(" in source:
        raise ValueError(f"{TIME} 的时间不得跟随系统区域")
    if "Date.parse(" in order:
        raise ValueError(f"{ORDER} 的排序键必须使用严格 ISO 解析")
    if source.count("Number.isNaN(at.getTime())") != 2:
        raise ValueError(f"{TIME} 的两个格式化函数都必须先判非法时间")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(TIME)
    order = _read(ORDER)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        (folder / "timeFormat.ts").write_text(_rewrite_time(source), encoding="utf-8")
        (folder / "sessionOrder.ts").write_text(_rewrite_order(order), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("时间格式行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"时间格式行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_time_format.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_time_format.py")
    if "共 27 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_time_format.py 检查 27 项结构、18 项行为")
    return 2


def check_time_format() -> tuple[int, int]:
    source = _read(TIME)
    order = _read(ORDER)
    structure = _check_structure(source, order)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_time_format()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"时间格式核对失败，{error}", file=sys.stderr)
        return 2
    print(f"时间格式一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
