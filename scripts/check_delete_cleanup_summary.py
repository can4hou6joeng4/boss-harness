#!/usr/bin/env python3
"""核对删除会话前的本机内容清单。

`deleteCleanup.ts` 汇总删除会话会一并清除的本机内容：未发送正文、附件、已选技能、
正在读取的附件与消息反馈。只统计真实存在的类别，反馈只算当前会话的条目。真实
`uiStorage.ts` 与 `messageFeedback.ts` 复制到临时目录并改写相对导入后，由 Node
直接加载真实模块执行用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/deleteCleanup.ts"
STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"
FEEDBACK = "apps/desktop/src/renderer/src/data/messageFeedback.ts"
DRAFT = "apps/desktop/src/renderer/src/data/composerDraft.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ComposerDraft } from "./composerDraft";',
    'import type { MessageFeedbackStore } from "./messageFeedback";',
    'import { parseFeedbackEntryKey } from "./messageFeedback";',
    "export function deleteCleanupSummary(draft: ComposerDraft | undefined, feedback: MessageFeedbackStore, threadId: string): string[] {",
    'if (draft.text.trim()) parts.push("未发送正文");',
    "if (draft.attachments.length > 0) parts.push(`${draft.attachments.length} 个附件`);",
    "if (skillCount > 0) parts.push(`${skillCount} 项已选技能`);",
    "if (parseFeedbackEntryKey(key)?.[0] === threadId) feedbackCount += 1;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { deleteCleanupSummary } = await import(pathToFileURL(process.argv[1]).href);
const draft = (extra) => ({ id: "d", text: "", textVersion: 1, attachments: [], pendingReads: 0, ...extra });
const attachment = (id) => ({ id, name: id + ".txt", text: "x", size: 1 });
const cases = [
  JSON.stringify(deleteCleanupSummary(undefined, {}, "t1")) === "[]",
  JSON.stringify(deleteCleanupSummary(draft({ text: "   " }), {}, "t1")) === "[]",
  JSON.stringify(deleteCleanupSummary(draft({ text: "hello" }), {}, "t1")) === '["未发送正文"]',
  JSON.stringify(deleteCleanupSummary(draft({ attachments: [attachment("a"), attachment("b")] }), {}, "t1")) === '["2 个附件"]',
  JSON.stringify(deleteCleanupSummary(draft({ skillIds: ["s1"] }), {}, "t1")) === '["1 项已选技能"]',
  JSON.stringify(deleteCleanupSummary(draft({ skillIds: ["s1", "s2", "s3"] }), {}, "t1")) === '["3 项已选技能"]',
  JSON.stringify(deleteCleanupSummary(draft({ pendingReads: 1 }), {}, "t1")) === '["正在读取的附件"]',
  JSON.stringify(deleteCleanupSummary(
    draft({ text: "hi", attachments: [attachment("a"), attachment("b")], skillIds: ["s1"], pendingReads: 2 }), {}, "t1"))
    === '["未发送正文","2 个附件","1 项已选技能","正在读取的附件"]',
  JSON.stringify(deleteCleanupSummary(
    draft({ text: "hi" }),
    { '["t1","m1"]': "up", '["t1","m2"]': "down", '["t2","m1"]': "up" }, "t1"))
    === '["未发送正文","2 条消息反馈"]',
  JSON.stringify(deleteCleanupSummary(draft({ text: "hi" }), { '["t2","m1"]': "up" }, "t1")) === '["未发送正文"]',
  JSON.stringify(deleteCleanupSummary(draft({ text: "hi" }), { bad: "up", '["t1","m1"]': "up" }, "t1"))
    === '["未发送正文","1 条消息反馈"]',
];
process.stdout.write(JSON.stringify({ cases }));
"""

EXPECTED_CASES = (True,) * 11
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
        (folder / "uiStorage.ts").write_text(_read(STORAGE), encoding="utf-8")
        (folder / "messageFeedback.ts").write_text(
            _read(FEEDBACK).replace('from "./uiStorage"', 'from "./uiStorage.ts"'),
            encoding="utf-8",
        )
        target = folder / "deleteCleanup.ts"
        target.write_text(
            _read(TARGET)
            .replace('from "./composerDraft"', f'from "{(ROOT / DRAFT).as_uri()}"')
            .replace('from "./messageFeedback"', 'from "./messageFeedback.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 删除清理清单试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 删除清理清单试算失败，请核对 Node.js 24+ 与 deleteCleanup.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的删除清理清单结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"删除清理清单{label}数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"删除清理清单{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_delete_cleanup_summary.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_delete_cleanup_summary.py")
    if "共 8 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_delete_cleanup_summary.py 检查 8 项结构、11 项行为")
    return 2


def check_delete_cleanup_summary() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_delete_cleanup_summary()
    except (OSError, ValueError) as error:
        print(f"删除清理清单核对失败，{error}", file=sys.stderr)
        return 2
    print(f"删除清理清单一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
