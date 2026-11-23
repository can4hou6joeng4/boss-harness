#!/usr/bin/env python3
"""核对压缩设置草稿的转换与重置规则。

`compactionDraft.ts` 把内核压缩策略转成面板草稿，并在一次性覆盖被消耗或清除后
回到内核默认值或占位草稿。这里静态核对模块契约，并用 Node 直接加载真实模块，
覆盖占位值、数字转字符串、零值、默认值来源与副本隔离等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/compactionDraft.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { AutoCompactionPolicy } from "@boss-harness/protocol";',
    "export interface AutoCompactionDraft {",
    "enabled: boolean;",
    "triggerPercent: string;",
    "keepRecentTokens: string;",
    "/** 内核默认值尚未读出时的占位草稿；与首次打开面板显示的值一致。 */",
    'export const DEFAULT_AUTO_COMPACTION_DRAFT: AutoCompactionDraft = { enabled: true, triggerPercent: "80", keepRecentTokens: "20000" };',
    "export const autoCompactionDraftFrom = (",
    "): AutoCompactionDraft => ({ enabled: policy.enabled, triggerPercent: String(policy.triggerPercent), keepRecentTokens: String(policy.keepRecentTokens) });",
    " * 覆盖被消耗或清除后的草稿。",
    "export function resetAutoCompactionDraft(",
    "return defaults ? autoCompactionDraftFrom(defaults) : { ...DEFAULT_AUTO_COMPACTION_DRAFT };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { DEFAULT_AUTO_COMPACTION_DRAFT, autoCompactionDraftFrom, resetAutoCompactionDraft } = await import(pathToFileURL(process.argv[1]).href);
const triplet = draft => [draft.enabled, draft.triggerPercent, draft.keepRecentTokens];
const policyA = { enabled: false, triggerPercent: 90, keepRecentTokens: 5000 };
const policyB = { enabled: true, triggerPercent: 0, keepRecentTokens: 0 };
const policyC = { enabled: false, triggerPercent: 95, keepRecentTokens: 10000 };
const fromA = autoCompactionDraftFrom(policyA);
const mutated = resetAutoCompactionDraft(undefined);
mutated.triggerPercent = "1";
const afterMutation = resetAutoCompactionDraft(undefined);
const result = {
  defaults: [triplet(DEFAULT_AUTO_COMPACTION_DRAFT)],
  from: [triplet(fromA), triplet(autoCompactionDraftFrom(policyB))],
  resetDefault: [triplet(resetAutoCompactionDraft(undefined))],
  resetPolicy: [triplet(resetAutoCompactionDraft(policyC))],
  identity: [
    resetAutoCompactionDraft(undefined) !== DEFAULT_AUTO_COMPACTION_DRAFT,
    resetAutoCompactionDraft(undefined) !== resetAutoCompactionDraft(undefined),
    fromA !== policyA,
  ],
  isolation: [triplet(afterMutation)],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_DEFAULTS = ([True, "80", "20000"],)
EXPECTED_FROM = ([False, "90", "5000"], [True, "0", "0"])
EXPECTED_RESET_DEFAULT = ([True, "80", "20000"],)
EXPECTED_RESET_POLICY = ([False, "95", "10000"],)
EXPECTED_IDENTITY = (True, True, True)
EXPECTED_ISOLATION = ([True, "80", "20000"],)
LABELS = {"defaults": "占位", "from": "转换", "resetDefault": "无默认重置",
          "resetPolicy": "有默认重置", "identity": "副本", "isolation": "隔离"}


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
        raise ValueError("Node 压缩设置草稿试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 压缩设置草稿试算失败，请核对 Node.js 24+ 与 compactionDraft.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的压缩设置草稿结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"压缩设置草稿{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"压缩设置草稿{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["defaults"], EXPECTED_DEFAULTS, LABELS["defaults"])
            + _compare(payload["from"], EXPECTED_FROM, LABELS["from"])
            + _compare(payload["resetDefault"], EXPECTED_RESET_DEFAULT, LABELS["resetDefault"])
            + _compare(payload["resetPolicy"], EXPECTED_RESET_POLICY, LABELS["resetPolicy"])
            + _compare(payload["identity"], EXPECTED_IDENTITY, LABELS["identity"])
            + _compare(payload["isolation"], EXPECTED_ISOLATION, LABELS["isolation"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_compaction_draft.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_compaction_draft.py")
    if "共 12 项结构、9 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_compaction_draft.py 检查 12 项结构、9 项行为")
    return 2


def check_compaction_draft() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_compaction_draft()
    except (OSError, ValueError) as error:
        print(f"压缩设置草稿规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"压缩设置草稿规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
