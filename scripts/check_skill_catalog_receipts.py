#!/usr/bin/env python3
"""核对桌面技能目录回执的条目、唯一标识与读取结果。

`skillCatalog.ts` 把 `skills/list` 条目和 `skills/read` 回执收敛成可渲染的事实：
标识、名称、描述、摘要都有长度边界，字节数与上限必须是非负 / 正整数，可选截断
标记必须是布尔；同目录标识必须唯一，读取回执的标识必须与请求一致。这里用 Node
直接加载真实模块逐项核对这些分支。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/skillCatalog.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "const ID_LIMIT = 200;",
    "const NAME_LIMIT = 200;",
    "const DESCRIPTION_LIMIT = 2000;",
    "const DIGEST_LIMIT = 128;",
    "export function skillDescriptorOf(value: unknown): SkillDescriptor | null {",
    'if (!value || typeof value !== "object" || Array.isArray(value)) return null;',
    'if (typeof raw.id !== "string" || raw.id.length === 0 || raw.id.length > ID_LIMIT) return null;',
    'if (typeof raw.name !== "string" || raw.name.length > NAME_LIMIT) return null;',
    'if (typeof raw.description !== "string" || raw.description.length > DESCRIPTION_LIMIT) return null;',
    'if (typeof raw.digest !== "string" || raw.digest.length === 0 || raw.digest.length > DIGEST_LIMIT) return null;',
    "if (!Number.isSafeInteger(raw.bytes) || (raw.bytes as number) < 0) return null;",
    'if (raw.nameTruncated !== undefined && typeof raw.nameTruncated !== "boolean") return null;',
    'if (raw.descriptionTruncated !== undefined && typeof raw.descriptionTruncated !== "boolean") return null;',
    "id: raw.id,",
    "name: raw.name,",
    "description: raw.description,",
    "digest: raw.digest,",
    "bytes: raw.bytes as number,",
    "...(raw.nameTruncated === true ? { nameTruncated: true } : {}),",
    "...(raw.descriptionTruncated === true ? { descriptionTruncated: true } : {}),",
    "export function uniqueSkillIds(items: { id: string }[]): boolean {",
    "return new Set(items.map(item => item.id)).size === items.length;",
    "export function skillReadOf(value: unknown, expectedId: string): SkillReadResponse | null {",
    "const descriptor = skillDescriptorOf(value);",
    "if (!descriptor || descriptor.id !== expectedId) return null;",
    'if (typeof raw.content !== "string") return null;',
    "if (!Number.isSafeInteger(raw.limitBytes) || (raw.limitBytes as number) <= 0) return null;",
    'const root = typeof raw.root === "string" ? raw.root : undefined;',
    "return { ...descriptor, content: raw.content, limitBytes: raw.limitBytes as number,",
    "...(root !== undefined ? { root } : {}) };",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { skillDescriptorOf, uniqueSkillIds, skillReadOf } =
  await import(pathToFileURL(process.argv[1]).href);
const base = () => ({
  id: "skill-1", name: "技能", description: "说明", digest: "d1", bytes: 100,
});
const read = over => skillReadOf({ ...base(), content: "正文", limitBytes: 4096, ...over }, "skill-1");
const result = {
  descriptors: [
    skillDescriptorOf(null),
    skillDescriptorOf([]),
    skillDescriptorOf({}),
    skillDescriptorOf(base()),
    skillDescriptorOf({ ...base(), id: "" }),
    skillDescriptorOf({ ...base(), id: "s".repeat(201) }),
    skillDescriptorOf({ ...base(), name: "n".repeat(201) }),
    skillDescriptorOf({ ...base(), description: "d".repeat(2001) }),
    skillDescriptorOf({ ...base(), digest: "" }),
    skillDescriptorOf({ ...base(), digest: "d".repeat(129) }),
    skillDescriptorOf({ ...base(), bytes: -1 }),
    skillDescriptorOf({ ...base(), bytes: 1.5 }),
    skillDescriptorOf({ ...base(), bytes: "100" }),
    skillDescriptorOf({ ...base(), nameTruncated: true, descriptionTruncated: true }),
    skillDescriptorOf({ ...base(), nameTruncated: false, descriptionTruncated: false }),
    skillDescriptorOf({ ...base(), nameTruncated: "yes" }),
    skillDescriptorOf({ ...base(), descriptionTruncated: "yes" }),
    skillDescriptorOf({ ...base(), extra: "ignored" }),
  ],
  unique: [
    uniqueSkillIds([]),
    uniqueSkillIds([{ id: "a" }, { id: "b" }]),
    uniqueSkillIds([{ id: "a" }, { id: "a" }]),
    uniqueSkillIds([{ id: "a" }, { id: "b" }, { id: "a" }]),
  ],
  reads: [
    read({}),
    skillReadOf({ ...base(), content: "正文", limitBytes: 4096 }, "skill-2"),
    read({ content: undefined }),
    read({ content: 42 }),
    read({ limitBytes: 0 }),
    read({ limitBytes: -1 }),
    read({ limitBytes: 1.5 }),
    read({ limitBytes: undefined }),
    read({ root: ".boss-cli/skills" }),
    read({ root: undefined }),
    read({ root: 42 }),
    read({ digest: "" }),
    read({ extra: "ignored" }),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

BASE = {"id": "skill-1", "name": "技能", "description": "说明", "digest": "d1", "bytes": 100}
TRUNCATED = {**BASE, "nameTruncated": True, "descriptionTruncated": True}
UNTRUNCATED = BASE
EXPECTED_DESCRIPTORS = (
    None, None, None,
    BASE, None, None, None, None, None, None, None, None, None,
    TRUNCATED, UNTRUNCATED, None, None, BASE,
)
EXPECTED_UNIQUE = (True, True, False, False)
READ_BASE = {**BASE, "content": "正文", "limitBytes": 4096}
EXPECTED_READS = (
    READ_BASE,
    None, None, None, None, None, None, None,
    {**READ_BASE, "root": ".boss-cli/skills"},
    READ_BASE, READ_BASE, None, READ_BASE,
)


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
        raise ValueError("Node 技能目录试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 技能目录试算失败，请核对 Node.js 24+ 与 skillCatalog.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的技能目录结果") from None
    for key in ("descriptors", "unique", "reads"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"技能目录{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"技能目录{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["descriptors"], EXPECTED_DESCRIPTORS, "条目")
    checked += _compare(payload["unique"], EXPECTED_UNIQUE, "唯一标识")
    checked += _compare(payload["reads"], EXPECTED_READS, "读取回执")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_skill_catalog_receipts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_skill_catalog_receipts.py")
    if "共 30 项结构、35 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_skill_catalog_receipts.py 检查 30 项结构、35 项行为")
    return 2


def check_skill_catalog_receipts() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_skill_catalog_receipts()
    except (OSError, ValueError) as error:
        print(f"技能目录规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能目录规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
