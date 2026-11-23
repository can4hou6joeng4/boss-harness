#!/usr/bin/env python3
"""核对队列项自动压缩覆盖的标签与说明。

`queueCompaction.ts` 把回合的自动压缩策略压成队列项标签与悬浮说明：标签按
「关闭 > 阈值 > 开启 > 覆盖」取最重要的一条，说明行按启用、阈值、保留量与摘要
线路依次拼接。这里静态核对模块契约，并由 Node 直接加载真实模块执行字段边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/shell/queueCompaction.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { AutoCompactionPolicy } from "@boss-harness/protocol";',
    "type CompactionFacts = Partial<AutoCompactionPolicy>;",
    "export const compactionLabel = (policy: CompactionFacts): string => {",
    "export const compactionTitle = (policy: CompactionFacts): string => {",
    'if (policy.enabled === false) return "压缩关闭";',
    'return facts.length ? facts.join("；") : "本回合沿用内核默认自动压缩策略";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { compactionLabel, compactionTitle } = await import(pathToFileURL(process.argv[1]).href);
const labels = [
  {},
  { enabled: false },
  { enabled: true },
  { triggerPercent: 80 },
  { enabled: false, triggerPercent: 80 },
  { enabled: true, triggerPercent: 70 },
  { triggerPercent: 0 },
];
const titles = [
  {},
  { enabled: true },
  { enabled: false },
  { triggerPercent: 85 },
  { keepRecentTokens: 12000 },
  { enabled: true, triggerPercent: 80, keepRecentTokens: 8000 },
  { provider: "openai" },
  { model: "gpt-5" },
  { effort: "high" },
  { provider: "anthropic", model: "claude-sonnet-5-5", effort: "low" },
  { enabled: false, provider: "openai" },
];
process.stdout.write(JSON.stringify({
  labels: labels.map((p) => compactionLabel(p)),
  titles: titles.map((p) => compactionTitle(p)),
}));
"""

EXPECTED_LABELS = (
    "压缩覆盖", "压缩关闭", "压缩开启", "压缩 80%",
    "压缩关闭", "压缩 70%", "压缩 0%",
)
EXPECTED_TITLES = (
    "本回合沿用内核默认自动压缩策略",
    "启用自动压缩",
    "关闭自动压缩",
    "触发阈值 85%",
    "保留最近 12000 token",
    "启用自动压缩；触发阈值 80%；保留最近 8000 token",
    "摘要线路 openai / 默认模型",
    "摘要线路 默认线路 / gpt-5",
    "摘要线路 默认线路 / 默认模型 · high",
    "摘要线路 anthropic / claude-sonnet-5-5 · low",
    "关闭自动压缩；摘要线路 openai / 默认模型",
)
LABELS = {"labels": "标签", "titles": "说明"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "queueCompaction.ts"
        target.write_text(_read(TARGET), encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 压缩覆盖试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 压缩覆盖试算失败，请核对 Node.js 24+ 与 queueCompaction.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的压缩覆盖结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"压缩覆盖{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"压缩覆盖{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["labels"], EXPECTED_LABELS, LABELS["labels"])
            + _compare(payload["titles"], EXPECTED_TITLES, LABELS["titles"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_compaction.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_compaction.py")
    if "共 6 项结构、18 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_compaction.py 检查 6 项结构、18 项行为")
    return 2


def check_queue_compaction() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_compaction()
    except (OSError, ValueError) as error:
        print(f"压缩覆盖标签核对失败，{error}", file=sys.stderr)
        return 2
    print(f"压缩覆盖标签一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
