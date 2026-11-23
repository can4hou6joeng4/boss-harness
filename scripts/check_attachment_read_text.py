#!/usr/bin/env python3
"""核对附件文本读取与失败提示。

渲染层 `attachmentRead.ts` 逐个读取文件文本，单个失败不拖累同批其余文件，并生成
失败提示。这里静态核对模块契约，并在临时目录改写共享包导入后由 Node 加载真实
模块，覆盖成功顺序、失败隔离、原因归一化与截断、提示计数与重试文案。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/attachmentRead.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "/** 附件读取：逐个文件读取文本，单个失败不拖累同批其余文件，并把原因带回界面。 */",
    'import { safeSlice } from "@boss-harness/shared";',
    "export interface ReadAttachment { id: string; name: string; text: string; size: number }",
    "export interface AttachmentFailure { name: string; reason: string }",
    "const MAX_REASON_LENGTH = 80;",
    "const MAX_LISTED_FAILURES = 3;",
    "function failureReason(error: unknown): string {",
    'const message = error instanceof Error ? error.message : typeof error === "string" ? error : "";',
    'return trimmed ? safeSlice(trimmed, MAX_REASON_LENGTH) : "无法读取";',
    "export async function readTextAttachments(",
    "return { added: { id: makeId(), name: file.name, text: await file.text(), size: file.size } };",
    'if ("added" in result) added.push(result.added);',
    "/** 失败提示：列出前几个失败文件与原因，并说明同批成功项是否已添加。 */",
    "export function attachmentFailureNotice(failures: readonly AttachmentFailure[], addedCount: number): string {",
    "const listed = failures.slice(0, MAX_LISTED_FAILURES).map(failure => `${failure.name}（${failure.reason}）`).join(\"、\");",
    "const rest = failures.length > MAX_LISTED_FAILURES ? `等 ${failures.length} 个文件` : \"\";",
    "const kept = addedCount > 0 ? `；其余 ${addedCount} 个文件已添加` : \"\";",
    'const retry = failures.length > 1 ? "这些文件" : "该文件";',
    "return `未能读取 ${listed}${rest}${kept}。请重新选择${retry}。`;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { readTextAttachments, attachmentFailureNotice } = await import(pathToFileURL(process.argv[1]).href);
let counter = 0;
const makeId = () => `id-${++counter}`;
const file = (name, text, size, error) => ({
  name,
  size,
  text: async () => {
    if (error !== undefined) throw error;
    return text;
  },
});
const run = async files => {
  counter = 0;
  const out = await readTextAttachments(files, makeId);
  return {
    added: out.added.map(item => [item.id, item.name, item.text, item.size]),
    failures: out.failures.map(item => [item.name, item.reason]),
  };
};
const notice = (pairs, addedCount) => attachmentFailureNotice(pairs.map(([name, reason]) => ({ name, reason })), addedCount);
const result = {
  reads: [
    await run([]),
    await run([file("a.txt", "hello", 5)]),
    await run([file("a.txt", "hello", 5), file("b.md", "world", 7)]),
    await run([file("a.txt", "hello", 5), file("bad.txt", "", 0, new Error("权限不足"))]),
    await run([file("bad.txt", "", 0, "boom")]),
    await run([file("bad.txt", "", 0, 42)]),
    await run([file("bad.txt", "", 0, new Error(""))]),
    await run([file("bad.txt", "", 0, new Error("   "))]),
    await run([file("bad.txt", "", 0, new Error("x".repeat(100)))]),
    await run([file("bad.txt", "", 0, new Error("🙂".repeat(100)))]),
    await run([file("bad.txt", "", 0, new Error("x".repeat(79) + "🙂"))]),
    await run([file("b.txt", "", 0, new Error("b")), file("a.txt", "", 0, new Error("a"))]),
    await run([file("ok.txt", "data", 4), file("bad1.txt", "", 0, new Error("e1")), file("bad2.txt", "", 0, new Error("e2"))]),
  ],
  notices: [
    notice([["a.txt", "boom"]], 0),
    notice([["a.txt", "boom"]], 2),
    notice([["a.txt", "x"], ["b.txt", "y"]], 0),
    notice([["a.txt", "x"], ["b.txt", "y"], ["c.txt", "z"]], 2),
    notice([["a.txt", "x"], ["b.txt", "y"], ["c.txt", "z"], ["d.txt", "w"]], 0),
    notice([["a.txt", "x"], ["b.txt", "y"], ["c.txt", "z"], ["d.txt", "w"], ["e.txt", "v"]], 1),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_READS = (
    {"added": [], "failures": []},
    {"added": [["id-1", "a.txt", "hello", 5]], "failures": []},
    {"added": [["id-1", "a.txt", "hello", 5], ["id-2", "b.md", "world", 7]], "failures": []},
    {"added": [["id-1", "a.txt", "hello", 5]], "failures": [["bad.txt", "权限不足"]]},
    {"added": [], "failures": [["bad.txt", "boom"]]},
    {"added": [], "failures": [["bad.txt", "无法读取"]]},
    {"added": [], "failures": [["bad.txt", "无法读取"]]},
    {"added": [], "failures": [["bad.txt", "无法读取"]]},
    {"added": [], "failures": [["bad.txt", "x" * 80]]},
    {"added": [], "failures": [["bad.txt", "🙂" * 40]]},
    {"added": [], "failures": [["bad.txt", "x" * 79]]},
    {"added": [], "failures": [["b.txt", "b"], ["a.txt", "a"]]},
    {"added": [["id-1", "ok.txt", "data", 4]], "failures": [["bad1.txt", "e1"], ["bad2.txt", "e2"]]},
)
EXPECTED_NOTICES = (
    "未能读取 a.txt（boom）。请重新选择该文件。",
    "未能读取 a.txt（boom）；其余 2 个文件已添加。请重新选择该文件。",
    "未能读取 a.txt（x）、b.txt（y）。请重新选择这些文件。",
    "未能读取 a.txt（x）、b.txt（y）、c.txt（z）；其余 2 个文件已添加。请重新选择这些文件。",
    "未能读取 a.txt（x）、b.txt（y）、c.txt（z）等 4 个文件。请重新选择这些文件。",
    "未能读取 a.txt（x）、b.txt（y）、c.txt（z）等 5 个文件；其余 1 个文件已添加。请重新选择这些文件。",
)
LABELS = {"reads": "读取", "notices": "提示"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "attachmentRead.ts"
        target.write_text(
            _read(TARGET).replace('from "@boss-harness/shared"', f'from "{(ROOT / SHARED).as_uri()}"'),
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
            raise ValueError("Node 附件读取试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 附件读取试算失败，请核对 Node.js 24+ 与 attachmentRead.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的附件读取结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"附件读取{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"附件读取{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["reads"], EXPECTED_READS, LABELS["reads"])
            + _compare(payload["notices"], EXPECTED_NOTICES, LABELS["notices"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_attachment_read_text.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_attachment_read_text.py")
    if "共 19 项结构、19 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_attachment_read_text.py 检查 19 项结构、19 项行为")
    return 2


def check_attachment_read_text() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_attachment_read_text()
    except (OSError, ValueError) as error:
        print(f"附件读取规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"附件读取规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
