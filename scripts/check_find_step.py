#!/usr/bin/env python3
"""核对会话内查找的游标位点与循环跳转。

查找按「处」跳转：同一条消息内的思考块、工具块与最终答复可能命中同一个词，
游标要能逐处前进并在两端循环；每条匹配消息至少算一处，否则界面没渲染出
高亮区间的命中会变得不可达。这里固定位点数下限、游标夹取、跨消息循环与
全局序号的累加方式，避免状态行的「第 N / M 处」与实际跳转对不上。行为侧
把真实 `findStep.ts` 复制到临时目录，由 Node 直接加载驱动位点、夹取、步进
与全局序号。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
STEP = "apps/desktop/src/renderer/src/data/findStep.ts"

EXPECTED = 31

NODE_SCRIPT = """\
import {
  clampFindCursor,
  findCursorPosition,
  findStepTotal,
  findSteps,
  stepFindCursor,
} from "./findStep.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);
const cursor = (message: number, offset: number): any => ({ message, offset });

const counts = [0, -3, 2.9, 1];
expect("位数至少一处", same(findSteps(counts), [1, 1, 2, 1]));
expect("位点输入不被修改", same(counts, [0, -3, 2.9, 1]));
expect(
  "非有限值按零",
  same(findSteps([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]), [1, 1, 1]),
);
expect("空列表位点为空", same(findSteps([]), []));
expect("位点总数", findStepTotal([2, 3]) === 5);
expect("总数至少一条一处", findStepTotal([0, 0]) === 2);
expect("空列表总数为零", findStepTotal([]) === 0);

expect("空列表收敛到空游标", same(clampFindCursor(cursor(3, 4), []), { message: 0, offset: 0 }));
expect("负值收敛到零", same(clampFindCursor(cursor(-2, -1), [2, 3]), { message: 0, offset: 0 }));
expect("消息下标夹到最后一条", same(clampFindCursor(cursor(9, 0), [2, 3]), { message: 1, offset: 0 }));
expect("位点夹到该消息末尾", same(clampFindCursor(cursor(1, 99), [2, 3]), { message: 1, offset: 2 }));
expect("小数向下取整", same(clampFindCursor(cursor(1.9, 1.7), [2, 3]), { message: 1, offset: 1 }));
expect(
  "非有限游标收敛到零",
  same(clampFindCursor(cursor(Number.NaN, Number.POSITIVE_INFINITY), [2, 3]), {
    message: 0,
    offset: 0,
  }),
);
const rawCursor = cursor(9, 1);
clampFindCursor(rawCursor, [2, 3]);
expect("收敛不修改输入", same(rawCursor, { message: 9, offset: 1 }));

expect("空列表步进仍是空游标", same(stepFindCursor(cursor(0, 0), [], 1), { message: 0, offset: 0 }));
expect("段内前进", same(stepFindCursor(cursor(0, 0), [3], 1), { message: 0, offset: 1 }));
expect("段内后退", same(stepFindCursor(cursor(0, 2), [3], -1), { message: 0, offset: 1 }));
expect("跨消息前进", same(stepFindCursor(cursor(0, 2), [3, 2], 1), { message: 1, offset: 0 }));
expect("跨消息后退", same(stepFindCursor(cursor(1, 0), [3, 2], -1), { message: 0, offset: 2 }));
expect("末尾前进回到首条首位", same(stepFindCursor(cursor(1, 0), [2, 1], 1), { message: 0, offset: 0 }));
expect("首条后退回到末条末位", same(stepFindCursor(cursor(0, 0), [2, 1], -1), { message: 1, offset: 0 }));
expect("非法游标先收敛", same(stepFindCursor(cursor(5, 9), [2, 2], 1), { message: 0, offset: 0 }));
expect(
  "步进先收敛越界游标",
  same(stepFindCursor(cursor(3, 0), [2, 2], 1), { message: 1, offset: 1 }),
);
const stepCursor = cursor(0, 0);
stepFindCursor(stepCursor, [2, 2], 1);
expect("步进不修改输入", same(stepCursor, { message: 0, offset: 0 }));

expect("空列表序号为零", findCursorPosition(cursor(2, 3), []) === 0);
expect("首位序号为零", findCursorPosition(cursor(0, 0), [2, 3]) === 0);
expect("跨消息序号累加", findCursorPosition(cursor(1, 1), [2, 3]) === 3);
expect("非法游标序号先收敛", findCursorPosition(cursor(9, 9), [2, 3]) === 4);
expect("末位序号等于总数减一", findCursorPosition(cursor(2, 0), [1, 1, 1]) === 2);

let walk: any = cursor(0, 0);
const positions: number[] = [];
for (let index = 0; index < 5; index += 1) {
  positions.push(findCursorPosition(walk, [2, 3]));
  walk = stepFindCursor(walk, [2, 3], 1);
}
expect("连续前进序号递增", same(positions, [0, 1, 2, 3, 4]));
expect("五次前进回到起点", same(walk, { message: 0, offset: 0 }));

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export interface FindCursor {",
    "message: number;",
    "offset: number;",
    "const EMPTY: FindCursor = { message: 0, offset: 0 };",
    "const whole = (value: number): number => (Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0);",
    "return counts.map(count => Math.max(1, whole(count)));",
    "return findSteps(counts).reduce((sum, steps) => sum + steps, 0);",
    "if (!counts.length) return EMPTY;",
    "const steps = findSteps(counts);",
    "const message = Math.min(whole(cursor.message), steps.length - 1);",
    "const offset = Math.min(whole(cursor.offset), (steps[message] ?? 1) - 1);",
    "return { message, offset };",
    "const current = clampFindCursor(cursor, counts);",
    "const next = current.offset + delta;",
    "if (next >= 0 && next < (steps[current.message] ?? 1)) return { message: current.message, offset: next };",
    "const length = steps.length;",
    "const message = (current.message + delta + length * length) % length;",
    "return { message, offset: delta > 0 ? 0 : (steps[message] ?? 1) - 1 };",
    "if (!counts.length) return 0;",
    "const safe = clampFindCursor(cursor, counts);",
    "let position = 0;",
    "for (let index = 0; index < safe.message; index += 1) position += steps[index] ?? 1;",
    "return position + safe.offset;",
)

ORDERED = (
    # 夹取：空列表回退 → 位点数 → 消息下标夹取 → 消息内位点夹取 → 返回。
    (
        "export function clampFindCursor(cursor: FindCursor, counts: readonly number[]): FindCursor {",
        "if (!counts.length) return EMPTY;",
        "const steps = findSteps(counts);",
        "const message = Math.min(whole(cursor.message), steps.length - 1);",
        "const offset = Math.min(whole(cursor.offset), (steps[message] ?? 1) - 1);",
        "return { message, offset };",
    ),
    # 步进：先收敛游标 → 段内前进 → 跨消息循环取模 → 按方向落在首尾。
    (
        "export function stepFindCursor(cursor: FindCursor, counts: readonly number[], delta: 1 | -1): FindCursor {",
        "const current = clampFindCursor(cursor, counts);",
        "const next = current.offset + delta;",
        "if (next >= 0 && next < (steps[current.message] ?? 1)) return { message: current.message, offset: next };",
        "const length = steps.length;",
        "const message = (current.message + delta + length * length) % length;",
        "return { message, offset: delta > 0 ? 0 : (steps[message] ?? 1) - 1 };",
    ),
    # 全局序号：空列表为 0 → 收敛游标 → 逐条累加前面的位数 → 加当前位点。
    (
        "export function findCursorPosition(cursor: FindCursor, counts: readonly number[]): number {",
        "if (!counts.length) return 0;",
        "const safe = clampFindCursor(cursor, counts);",
        "let position = 0;",
        "for (let index = 0; index < safe.message; index += 1) position += steps[index] ?? 1;",
        "return position + safe.offset;",
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


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, STEP)
    for group in ORDERED:
        checked += _ordered(group, source, STEP)
    # 反向断言：数值取整必须向下取整；反向循环不得出现负模；序号必须逐条累加。
    if "Math.round(" in source:
        raise ValueError(f"{STEP} 的位点与游标必须向下取整")
    if "(current.message + delta) % length" in source:
        raise ValueError(f"{STEP} 的反向循环必须在取模前补齐非负")
    if "return safe.message + safe.offset;" in source:
        raise ValueError(f"{STEP} 的全局序号必须累加前面每条消息的位数")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(STEP)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "findStep.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("查找游标行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"查找游标行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_find_step.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_find_step.py")
    if "共 45 项结构、31 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_find_step.py 检查 45 项结构、31 项行为")
    return 2


def check_find_step() -> tuple[int, int]:
    source = _read(STEP)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_find_step()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"查找游标核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找游标一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
