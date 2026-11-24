#!/usr/bin/env python3
"""核对工具来源查询时间的解析与展示。

`toolSource.ts` 复用共享包的严格 ISO 解析，避免 `new Date` 把 `"1"`、只有日期或
本地时间当成有效时刻；UTC 文本省略整秒的 `.000`，本机时区标签按 `YYYY-MM-DD HH:mm`
输出。真实 `timeFormat.ts` 复制到临时目录并改写共享包导入后，由 Node 在 `TZ=UTC`
下直接加载真实模块执行用例。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/toolSource.ts"
FORMAT = "apps/desktop/src/renderer/src/data/timeFormat.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import { formatLocalDateTime, parseIsoDateTime } from "./timeFormat";',
    "export function toolQueriedAt(value: unknown): Date | null {",
    "return parseIsoDateTime(value);",
    "export function toolQueriedAtText(value: unknown): string | null {",
    'return iso.endsWith(".000Z") ? `${iso.slice(0, -5)}Z` : iso;',
    "export function toolQueriedAtLabel(value: unknown): string | null {",
)

FORMAT_FRAGMENTS = (
    'import { formatLocalDate, parseIsoDateTime } from "@boss-harness/shared";',
    "export { parseIsoDateTime };",
    "export function formatLocalDateTime(at: Date): string {",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const m = await import(pathToFileURL(process.argv[1]).href);
const iso = "2026-11-24T10:30:00Z";
const at = m.toolQueriedAt(iso);
const cases = [
  at instanceof Date && at.toISOString() === "2026-11-24T10:30:00.000Z",
  m.toolQueriedAt("2026-11-24T10:30:00.123Z")?.toISOString() === "2026-11-24T10:30:00.123Z",
  m.toolQueriedAt(" 2026-11-24T10:30:00Z ")?.toISOString() === "2026-11-24T10:30:00.000Z",
  m.toolQueriedAt("1") === null,
  m.toolQueriedAt("2026-11-24") === null,
  m.toolQueriedAt("2026-11-24T10:30:00") === null,
  m.toolQueriedAt(42) === null && m.toolQueriedAt(null) === null && m.toolQueriedAt(undefined) === null,
  m.toolQueriedAtText(iso) === "2026-11-24T10:30:00Z",
  m.toolQueriedAtText("2026-11-24T10:30:00.123Z") === "2026-11-24T10:30:00.123Z",
  m.toolQueriedAtText("1") === null,
  m.toolQueriedAtLabel(iso) === "2026-11-24 10:30",
  m.toolQueriedAtLabel("2026-11-24") === null,
];
process.stdout.write(JSON.stringify({ cases }));
"""

EXPECTED_CASES = (True,) * 12
LABELS = {"cases": "用例"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "timeFormat.ts").write_text(
            _read(FORMAT).replace('"@boss-harness/shared"', f'"{(ROOT / SHARED).as_uri()}"'),
            encoding="utf-8",
        )
        target = folder / "toolSource.ts"
        target.write_text(
            _read(TARGET).replace('from "./timeFormat"', 'from "./timeFormat.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
                env={**os.environ, "TZ": "UTC"},
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 工具来源时间试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 工具来源时间试算失败，请核对 Node.js 24+ 与 toolSource.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的工具来源时间结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"工具来源时间{label}数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"工具来源时间{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_tool_source.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_tool_source.py")
    if "共 9 项结构、12 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_tool_source.py 检查 9 项结构、12 项行为")
    return 2


def check_tool_source() -> tuple[int, int]:
    structure = (_expect(FRAGMENTS, _read(TARGET), TARGET)
                 + _expect(FORMAT_FRAGMENTS, _read(FORMAT), FORMAT))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_tool_source()
    except (OSError, ValueError) as error:
        print(f"工具来源时间核对失败，{error}", file=sys.stderr)
        return 2
    print(f"工具来源时间一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
