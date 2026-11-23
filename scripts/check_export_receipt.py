#!/usr/bin/env python3
"""核对导出保存回执的校验规则。

`exportReceipt.ts` 判断导出回执的统计是否完整、已导出回合数是否自洽。这里静态核对
模块契约，并用 Node 直接加载真实模块覆盖取消回执、文件名上限、计数类型、脱敏统计、
权限标记与原始对象返回等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/exportReceipt.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 导出回执校验：统计必须完整，且已导出回合数不能超过视图声明的总回合数。",
    "export function savedExportResult(value: unknown): SessionExportSaveResult | null {",
    'if (!value || typeof value !== "object") return null;',
    "const raw = value as Record<string, unknown>;",
    "if (raw.saved === false && raw.canceled === true) return { saved: false, canceled: true };",
    "const counts = raw.redactions as Record<string, unknown> | undefined;",
    'const count = (item: unknown): item is number => typeof item === "number" && Number.isSafeInteger(item) && item >= 0;',
    'if (raw.saved !== true || typeof raw.fileName !== "string" || !raw.fileName || raw.fileName.length > 255 ||',
    '!count(raw.bytes) || typeof raw.truncated !== "boolean") return null;',
    "const turnCount = raw.turnCount, exportedTurnCount = raw.exportedTurnCount;",
    "if (!count(turnCount) || !count(exportedTurnCount) || exportedTurnCount > turnCount ||",
    '(raw.toolResults !== "omitted" && raw.toolResults !== "included") || !counts ||',
    '(raw.permissionsUnchanged !== undefined && typeof raw.permissionsUnchanged !== "boolean") ||',
    '!["secrets", "environment", "paths", "personalInfo"].every(key => count(counts[key]))) return null;',
    "return value as SessionExportSaveResult;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { savedExportResult } = await import(pathToFileURL(process.argv[1]).href);
const redactions = { secrets: 1, environment: 2, paths: 3, personalInfo: 4 };
const valid = {
  saved: true, fileName: "export.zip", bytes: 1024, truncated: false,
  turnCount: 5, exportedTurnCount: 4, toolResults: "included",
  redactions, permissionsUnchanged: true,
};
const shape = value => value === null ? null : {
  saved: value.saved,
  canceled: value.canceled ?? null,
  fileNameLength: typeof value.fileName === "string" ? value.fileName.length : null,
  bytes: value.bytes ?? null,
  truncated: value.truncated ?? null,
  turnCount: value.turnCount ?? null,
  exportedTurnCount: value.exportedTurnCount ?? null,
  toolResults: value.toolResults ?? null,
  redactions: value.redactions ? Object.keys(value.redactions).sort() : null,
  permissions: value.permissionsUnchanged ?? null,
  extra: value.extra ?? null,
};
const result = {
  cases: [
    shape(savedExportResult(null)),
    shape(savedExportResult([])),
    shape(savedExportResult("receipt")),
    shape(savedExportResult({ saved: false, canceled: true })),
    shape(savedExportResult({ saved: false, canceled: false })),
    shape(savedExportResult({ saved: true, canceled: true })),
    shape(savedExportResult(valid)),
    shape(savedExportResult({ ...valid, fileName: "" })),
    shape(savedExportResult({ ...valid, fileName: "x".repeat(256) })),
    shape(savedExportResult({ ...valid, fileName: "x".repeat(255) })),
    shape(savedExportResult({ ...valid, bytes: -1 })),
    shape(savedExportResult({ ...valid, bytes: 1.5 })),
    shape(savedExportResult({ ...valid, truncated: "yes" })),
    shape(savedExportResult({ ...valid, saved: "true" })),
    shape(savedExportResult({ ...valid, exportedTurnCount: 6 })),
    shape(savedExportResult({ ...valid, exportedTurnCount: 5 })),
    shape(savedExportResult({ ...valid, toolResults: "unknown" })),
    shape(savedExportResult({ ...valid, redactions: undefined })),
    shape(savedExportResult({ ...valid, redactions: { secrets: 1, environment: 2, paths: 3 } })),
    shape(savedExportResult({ ...valid, redactions: { environment: 2, paths: 3, personalInfo: 4 } })),
    shape(savedExportResult({ ...valid, redactions: { ...redactions, paths: -1 } })),
    shape(savedExportResult({ ...valid, permissionsUnchanged: "yes" })),
    shape(savedExportResult({ ...valid, permissionsUnchanged: undefined })),
    shape(savedExportResult({ ...valid, permissionsUnchanged: false })),
    shape(savedExportResult({ ...valid, extra: true })),
  ],
  identity: [savedExportResult(valid) === valid],
};
process.stdout.write(JSON.stringify(result));
"""


def _ok(*, file_length=10, bytes=1024, truncated=False, turn=5, exported=4,
        tool_results="included", permissions=True, redactions=("environment", "paths", "personalInfo", "secrets"),
        extra=None):
    return {
        "saved": True, "canceled": None, "fileNameLength": file_length, "bytes": bytes,
        "truncated": truncated, "turnCount": turn, "exportedTurnCount": exported,
        "toolResults": tool_results, "redactions": list(redactions), "permissions": permissions,
        "extra": extra,
    }


CANCELED = {
    "saved": False, "canceled": True, "fileNameLength": None, "bytes": None, "truncated": None,
    "turnCount": None, "exportedTurnCount": None, "toolResults": None, "redactions": None,
    "permissions": None, "extra": None,
}
EXPECTED_CASES = (
    None,
    None,
    None,
    CANCELED,
    None,
    None,
    _ok(),
    None,
    None,
    _ok(file_length=255),
    None,
    None,
    None,
    None,
    None,
    _ok(exported=5),
    None,
    None,
    None,
    None,
    None,
    None,
    _ok(permissions=None),
    _ok(permissions=False),
    _ok(extra=True),
)
EXPECTED_IDENTITY = (True,)
LABELS = {"cases": "回执", "identity": "原样返回"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 导出回执试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 导出回执试算失败，请核对 Node.js 24+ 与 exportReceipt.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的导出回执结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"导出{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"导出{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"]) + _compare(payload["identity"], EXPECTED_IDENTITY, LABELS["identity"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_export_receipt.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_export_receipt.py")
    if "共 15 项结构、26 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_export_receipt.py 检查 15 项结构、25 项行为")
    return 2


def check_export_receipt() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_export_receipt()
    except (OSError, ValueError) as error:
        print(f"导出回执规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出回执规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
