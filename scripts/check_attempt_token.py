#!/usr/bin/env python3
"""核对在途请求标记的推进、作废与比较。

弹窗等待异步结果期间可以被关闭、重新打开或发起新请求；旧请求返回时
只在与当前标记一致时才允许写回。开始提交与关闭弹窗都推进标记，标记
从 0 起算，`attemptCurrent` 做严格相等比较。结构侧固定这些语义；行为侧
把真实模块复制到临时目录，由 Node 直接加载并驱动推进、作废与比较。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
ATTEMPT = "apps/desktop/src/renderer/src/data/attemptToken.ts"

EXPECTED = 12

NODE_SCRIPT = """\
import {
  attemptCurrent,
  createAttemptToken,
  invalidateAttempts,
  startAttempt,
} from "./attemptToken.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

const tracker = createAttemptToken();
expect("新建标记为 0", tracker.current === 0);
const first = startAttempt(tracker);
expect("开始提交返回最新标记", first === 1 && tracker.current === 1);
expect("当前标记可用", attemptCurrent(tracker, first) === true);
expect("旧标记不可用", attemptCurrent(tracker, 0) === false);
const second = startAttempt(tracker);
expect(
  "连续开始持续递增",
  second === 2 && attemptCurrent(tracker, first) === false && attemptCurrent(tracker, second) === true,
);
invalidateAttempts(tracker);
expect("作废推进标记", tracker.current === 3 && attemptCurrent(tracker, second) === false);
const third = startAttempt(tracker);
expect("作废后可继续提交", third === 4 && attemptCurrent(tracker, third) === true);
expect("开始提交不重置标记", tracker.current === 4);
const other = createAttemptToken();
expect("新实例从 0 开始", other.current === 0 && attemptCurrent(other, 0) === true);
expect("实例互不影响", startAttempt(other) === 1 && tracker.current === 4);
const detached = { current: 7 };
expect("外部标记按当前值比较", attemptCurrent(detached, 7) === true && attemptCurrent(detached, 6) === false);
expect(
  "严格相等不放宽",
  attemptCurrent(tracker, 4) === true && attemptCurrent(tracker, 5) === false && attemptCurrent(tracker, 3) === false,
);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export type AttemptToken = { current: number };",
    "export function createAttemptToken(): AttemptToken {",
    "return { current: 0 };",
    "export function startAttempt(tracker: AttemptToken): number {",
    "tracker.current += 1;",
    "return tracker.current;",
    "export function invalidateAttempts(tracker: AttemptToken): void {",
    "export function attemptCurrent(tracker: AttemptToken, token: number): boolean {",
    "return token === tracker.current;",
)

ORDERED = (
    # 新建：标记从 0 起算。
    (
        "export function createAttemptToken(): AttemptToken {",
        "return { current: 0 };",
    ),
    # 开始提交：推进后返回新标记。
    (
        "export function startAttempt(tracker: AttemptToken): number {",
        "tracker.current += 1;",
        "return tracker.current;",
    ),
    # 作废：只推进标记。
    (
        "export function invalidateAttempts(tracker: AttemptToken): void {",
        "tracker.current += 1;",
    ),
    # 当前判断：严格相等。
    (
        "export function attemptCurrent(tracker: AttemptToken, token: number): boolean {",
        "return token === tracker.current;",
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
    checked += _expect(FRAGMENTS, source, ATTEMPT)
    for group in ORDERED:
        checked += _ordered(group, source, ATTEMPT)
    # 反向断言：开始与作废都要推进；开始不得重置；比较不得放宽。
    if source.count("tracker.current += 1;") != 2:
        raise ValueError(f"{ATTEMPT} 的开始与作废都必须推进标记")
    if "tracker.current = 0" in source:
        raise ValueError(f"{ATTEMPT} 的开始提交不得重置标记")
    if "token <=" in source:
        raise ValueError(f"{ATTEMPT} 的当前判断必须是严格相等")
    return checked + 3


def _check_behaviors() -> int:
    source = _read(ATTEMPT)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "attemptToken.ts").write_text(source, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("在途标记行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"在途标记行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_attempt_token.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_attempt_token.py")
    if "共 21 项结构、12 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_attempt_token.py 检查 21 项结构、12 项行为")
    return 2


def check_attempt_token() -> tuple[int, int]:
    source = _read(ATTEMPT)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_attempt_token()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"在途标记核对失败，{error}", file=sys.stderr)
        return 2
    print(f"在途标记一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
