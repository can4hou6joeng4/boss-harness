#!/usr/bin/env python3
"""核对运行中队列模式的技能提示。

`queueSkillNotice.ts` 只在「转向当前回合」确实携带技能时给出固定提示，避免把
已经支持技能的后续回合队列消息也误报为不支持。这里静态核对模块契约，并用 Node
直接加载真实模块覆盖队列开关、意图与技能计数边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/queueSkillNotice.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { QueueIntent } from "./composerDraft";',
    " * 运行中队列模式的技能提示。",
    " * 只有「转向当前回合」会丢弃技能；「排到后续回合」自 `queue/add.skillIds` 起就支持技能，",
    " * 不能再笼统提示「队列消息不支持技能」。",
    "export function queueSkillNotice(queueing: boolean, intent: QueueIntent, skillCount: number): string | null {",
    'if (!queueing || intent !== "steering" || skillCount < 1) return null;',
    'return "转向消息不使用技能；切换为「排到后续回合」或清除已选技能后再发送。";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { queueSkillNotice } = await import(pathToFileURL(process.argv[1]).href);
const run = (queueing, intent, skillCount) => queueSkillNotice(queueing, intent, skillCount);
const result = [
  run(false, "steering", 1),
  run(false, "followUp", 1),
  run(true, "followUp", 1),
  run(true, "steering", 0),
  run(true, "steering", -1),
  run(true, "steering", 1),
  run(true, "steering", 3),
  run(false, "steering", 0),
  run(true, "followUp", 0),
];
process.stdout.write(JSON.stringify(result));
"""

NOTICE = "转向消息不使用技能；切换为「排到后续回合」或清除已选技能后再发送。"
EXPECTED = (
    None, None, None, None, None, NOTICE, NOTICE, None, None,
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / TARGET)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 技能提示试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 技能提示试算失败，请核对 Node.js 24+ 与 queueSkillNotice.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的技能提示结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回技能提示列表")
    return payload


def _compare(actual: list, expected: tuple) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"技能提示用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"技能提示第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    return _compare(_node_matrix(), EXPECTED)


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_queue_skill_notice.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_queue_skill_notice.py")
    if "共 7 项结构、9 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_queue_skill_notice.py 检查 7 项结构、9 项行为")
    return 2


def check_queue_skill_notice() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_queue_skill_notice()
    except (OSError, ValueError) as error:
        print(f"队列技能提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"队列技能提示一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
