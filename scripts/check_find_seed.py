#!/usr/bin/env python3
"""核对会话内查找沿用选中文本的放行条件。

打开查找时只沿用适合当关键词的选择：焦点不在可编辑控件、单行、去掉首尾
空白后非空、长度按 Unicode 码点不超过 120。这里固定判定顺序与码点计数，
避免把 emoji 等非 BMP 字符按 UTF-16 码元误判超长，或让输入框里的残留选择
覆盖用户刚输入的关键词。行为侧把真实 `findSeed.ts` 与共享 `shared/index.ts`
复制到临时目录、改写导入，由 Node 直接加载驱动标签判定与放行边界。
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
SEED = "apps/desktop/src/renderer/src/data/findSeed.ts"
SHARED = "packages/shared/src/index.ts"

EXPECTED = 23

NODE_SCRIPT = """\
import { FIND_SEED_MAX_LENGTH, findSeedFromSelection, isEditableTarget } from "./findSeed.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}

expect("长度上限常量", FIND_SEED_MAX_LENGTH === 120);
expect("空目标不是可编辑", isEditableTarget(null) === false);
expect("非元素目标不是可编辑", isEditableTarget(42 as any) === false);
expect("标签大小写不敏感", isEditableTarget({ tagName: "INPUT" } as any) === true);
expect("文本域可编辑", isEditableTarget({ tagName: "textarea" } as any) === true);
expect("下拉框可编辑", isEditableTarget({ tagName: "select" } as any) === true);
expect("可编辑属性", isEditableTarget({ tagName: "div", isContentEditable: true } as any) === true);
expect("普通容器不是可编辑", isEditableTarget({ tagName: "div" } as any) === false);
expect("空标签不是可编辑", isEditableTarget({ tagName: "" } as any) === false);
expect("非字符串标签不是可编辑", isEditableTarget({ tagName: 7 } as any) === false);

expect("可编辑上下文不沿用", findSeedFromSelection("hello", { editable: true }) === null);
expect(
  "非字符串不沿用",
  findSeedFromSelection(null) === null
    && findSeedFromSelection(undefined) === null
    && findSeedFromSelection(42 as any) === null,
);
expect("去首尾空白后沿用", findSeedFromSelection("  Hello world  ") === "Hello world");
expect(
  "空选择不沿用",
  findSeedFromSelection("") === null && findSeedFromSelection("   ") === null,
);
expect(
  "多行选择不沿用",
  findSeedFromSelection("a\\nb") === null && findSeedFromSelection("a\\rb") === null,
);
expect("空白包裹的多行不沿用", findSeedFromSelection("  a\\nb  ") === null);
expect("120 码点可沿用", findSeedFromSelection("a".repeat(120)) === "a".repeat(120));
expect("121 码点不沿用", findSeedFromSelection("a".repeat(121)) === null);
expect(
  "空白不计入码点上限",
  findSeedFromSelection("  " + "a".repeat(120) + "  ") === "a".repeat(120),
);
expect("emoji 按码点计数通过", findSeedFromSelection("😀".repeat(120)) === "😀".repeat(120));
expect("emoji 超限不沿用", findSeedFromSelection("😀".repeat(121)) === null);
expect("单字符沿用", findSeedFromSelection("x") === "x");
expect("缺省上下文沿用", findSeedFromSelection(" keyword ") === "keyword");

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    "export const FIND_SEED_MAX_LENGTH = 120;",
    "editable?: boolean;",
    "const element = target as { tagName?: unknown; isContentEditable?: unknown } | null;",
    'if (!element || typeof element.tagName !== "string") return false;',
    "const tag = element.tagName.toLowerCase();",
    'return tag === "input" || tag === "textarea" || tag === "select" || element.isContentEditable === true;',
    "export function findSeedFromSelection(",
    "context: FindSeedContext = {},",
    ": string | null {",
    "if (context.editable) return null;",
    'if (typeof selection !== "string") return null;',
    "const text = selection.trim();",
    "if (!text) return null;",
    "if (/[\\r\\n]/.test(text)) return null;",
    "if (codePointLength(text) > FIND_SEED_MAX_LENGTH) return null;",
    "return text;",
)

ORDERED = (
    # 放行顺序：可编辑控件 → 非字符串 → 去空白 → 空选择 → 多行 → 码点上限 → 沿用。
    (
        "if (context.editable) return null;",
        'if (typeof selection !== "string") return null;',
        "const text = selection.trim();",
        "if (!text) return null;",
        "if (/[\\r\\n]/.test(text)) return null;",
        "if (codePointLength(text) > FIND_SEED_MAX_LENGTH) return null;",
        "return text;",
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


def _rewrite(source: str) -> str:
    rewritten = source.replace(
        'from "@boss-harness/shared";', 'from "./shared.ts";'
    )
    if '"@boss-harness/shared"' in rewritten:
        raise ValueError(f"{SEED} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, SEED)
    for group in ORDERED:
        checked += _ordered(group, source, SEED)
    # 反向断言：长度必须按码点判定；多行校验必须在 trim 之后。
    if "selection.length" in source or "text.length" in source:
        raise ValueError(f"{SEED} 的长度必须按 Unicode 码点计数，不能按 UTF-16 码元")
    if source.index("const text = selection.trim();") > source.index("if (/[\\r\\n]/.test(text)) return null;"):
        raise ValueError(f"{SEED} 必须先去掉首尾空白再判断多行")
    return checked + 2


def _check_behaviors() -> int:
    source = _read(SEED)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "findSeed.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("查找沿用行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"查找沿用行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_find_seed.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_find_seed.py")
    if "共 26 项结构、23 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_find_seed.py 检查 26 项结构、23 项行为")
    return 2


def check_find_seed() -> tuple[int, int]:
    source = _read(SEED)
    structure = _check_structure(source)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_find_seed()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"查找沿用核对失败，{error}", file=sys.stderr)
        return 2
    print(f"查找沿用一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
