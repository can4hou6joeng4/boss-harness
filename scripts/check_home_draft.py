#!/usr/bin/env python3
"""核对首页草稿的填充意图与技能并入。

工作区模板入口此前会直接重置草稿，静默清空正文、附件与已选技能。现在
正文、附件、技能、正在读取附件与提交中都算「有未发送内容」；模板只有在
草稿为空或与模板完全一致时才直接应用。技能入口只并入技能，已选或已达
每回合上限 `MAX_TURN_SKILLS` 时原样返回。这里固定这些约定，避免覆盖用户
输入。行为侧把真实 `homeDraftFill.ts`、`composerDraft.ts` 与共享
`shared/index.ts` 复制到临时目录、改写导入，由 Node 直接加载驱动内容
判定、填充意图与技能并入的边界。
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
HOME = "apps/desktop/src/renderer/src/data/homeDraftFill.ts"
COMPOSER_DRAFT = "apps/desktop/src/renderer/src/data/composerDraft.ts"
SHARED = "packages/shared/src/index.ts"

HOME_IMPORT = 'import { MAX_TURN_SKILLS, type ComposerDraft } from "./composerDraft";'
LIMIT_LINE = "if (current.includes(skillId) || current.length >= MAX_TURN_SKILLS) return draft;"

EXPECTED = 36

NODE_SCRIPT = """\
import { homeDraftHasContent, templateFillIntent, withHomeDraftSkill } from "./homeDraftFill.ts";
import { MAX_TURN_SKILLS } from "./composerDraft.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);
const draft = (overrides: Record<string, unknown> = {}): any => ({
  id: "d1",
  text: "",
  textVersion: 0,
  attachments: [],
  skillIds: [],
  pendingReads: 0,
  submitting: false,
  ...overrides,
});
const file = { id: "a1", name: "简历.pdf" };
const skills = (total: number): string[] => Array.from({ length: total }, (_, index) => `s${index}`);

expect("空草稿无内容", homeDraftHasContent(draft()) === false);
expect("空白正文不算内容", homeDraftHasContent(draft({ text: "  \\n\\t " })) === false);
expect("有正文算内容", homeDraftHasContent(draft({ text: " a " })) === true);
expect("有附件算内容", homeDraftHasContent(draft({ attachments: [file] })) === true);
expect("有技能算内容", homeDraftHasContent(draft({ skillIds: ["s"] })) === true);
expect("缺省技能列表不算内容", homeDraftHasContent(draft({ skillIds: undefined })) === false);
expect("正在读取附件算内容", homeDraftHasContent(draft({ pendingReads: 1 })) === true);
expect("提交中算内容", homeDraftHasContent(draft({ submitting: true })) === true);

expect("空草稿直接应用", templateFillIntent(draft(), "模板") === "apply");
expect("空白草稿直接应用", templateFillIntent(draft({ text: "   " }), "模板") === "apply");
expect("读取中空草稿也要确认", templateFillIntent(draft({ pendingReads: 1 }), "模板") === "confirm");
expect("提交中空草稿也要确认", templateFillIntent(draft({ submitting: true }), "模板") === "confirm");
expect(
  "读取中同文也要确认",
  templateFillIntent(draft({ text: "模板", pendingReads: 1 }), "模板") === "confirm",
);
expect(
  "提交中同文也要确认",
  templateFillIntent(draft({ text: "模板", submitting: true }), "模板") === "confirm",
);
expect("不同正文需确认", templateFillIntent(draft({ text: "别的" }), "模板") === "confirm");
expect("同文直接应用", templateFillIntent(draft({ text: "模板" }), "模板") === "apply");
expect(
  "同文忽略首尾空白",
  templateFillIntent(draft({ text: "  模板 " }), "模板\\n") === "apply",
);
expect("内部空白不同算不同正文", templateFillIntent(draft({ text: "a  b" }), "a b") === "confirm");
expect(
  "同文但有附件需确认",
  templateFillIntent(draft({ text: "模板", attachments: [file] }), "模板") === "confirm",
);
expect(
  "同文但有技能需确认",
  templateFillIntent(draft({ text: "模板", skillIds: ["s"] }), "模板") === "confirm",
);
expect("仅有附件需确认", templateFillIntent(draft({ attachments: [file] }), "模板") === "confirm");
expect("仅有技能需确认", templateFillIntent(draft({ skillIds: ["s"] }), "模板") === "confirm");
expect(
  "同文且缺省技能列表直接应用",
  templateFillIntent(draft({ text: "模板", skillIds: undefined }), "模板") === "apply",
);

const plain = draft({ text: "正文", attachments: [file], pendingReads: 2, submitting: true });
const merged = withHomeDraftSkill(plain, "s1");
expect("并入新技能", same(merged.skillIds, ["s1"]));
expect("并入返回新对象", merged !== plain);
expect(
  "并入保留正文附件与状态",
  merged.text === "正文"
    && merged.attachments === plain.attachments
    && merged.pendingReads === 2
    && merged.submitting === true
    && merged.id === "d1",
);
expect("并入不修改原草稿", same(plain.skillIds, []) && merged.skillIds !== plain.skillIds);
expect(
  "追加到末尾并保持顺序",
  same(withHomeDraftSkill(draft({ skillIds: ["a", "b"] }), "c").skillIds, ["a", "b", "c"]),
);
const chosen = draft({ skillIds: ["a", "b"] });
expect("已选技能原样返回", withHomeDraftSkill(chosen, "a") === chosen);
const full = draft({ skillIds: skills(10) });
expect("已达 10 项原样返回", withHomeDraftSkill(full, "new") === full);
expect("已达上限不修改列表", same(full.skillIds, skills(10)));
expect(
  "9 项仍可并入第 10 项",
  same(withHomeDraftSkill(draft({ skillIds: skills(9) }), "new").skillIds, [...skills(9), "new"]),
);
const atLimit = draft({ skillIds: skills(MAX_TURN_SKILLS) });
expect(
  "上限取自草稿模型常量",
  withHomeDraftSkill(atLimit, "new") === atLimit
    && withHomeDraftSkill(draft({ skillIds: skills(MAX_TURN_SKILLS - 1) }), "new").skillIds.length === MAX_TURN_SKILLS,
);
const over = draft({ skillIds: skills(12) });
expect("超过上限的草稿原样返回", withHomeDraftSkill(over, "new") === over && same(over.skillIds, skills(12)));
const bare = draft({ skillIds: undefined });
expect("缺省技能列表视为空并入", same(withHomeDraftSkill(bare, "s").skillIds, ["s"]));
expect("缺省技能列表不被补写", bare.skillIds === undefined);

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    HOME_IMPORT,
    "export function homeDraftHasContent(draft: ComposerDraft): boolean {",
    "return Boolean(draft.text.trim()) || draft.attachments.length > 0 || (draft.skillIds ?? []).length > 0",
    "|| draft.pendingReads > 0 || draft.submitting;",
    "export function templateFillIntent(draft: ComposerDraft, template: string): \"apply\" | \"confirm\" {",
    'if (draft.pendingReads > 0 || draft.submitting) return "confirm";',
    'if (!homeDraftHasContent(draft)) return "apply";',
    "const sameText = draft.text.trim() === template.trim();",
    'if (sameText && draft.attachments.length === 0 && (draft.skillIds ?? []).length === 0) return "apply";',
    'return "confirm";',
    "export function withHomeDraftSkill(draft: ComposerDraft, skillId: string): ComposerDraft {",
    "const current = draft.skillIds ?? [];",
    LIMIT_LINE,
    "return { ...draft, skillIds: [...current, skillId] };",
)

ORDERED = (
    # 有内容：正文、附件、技能、读取与提交。
    (
        "export function homeDraftHasContent(draft: ComposerDraft): boolean {",
        "return Boolean(draft.text.trim()) || draft.attachments.length > 0 || (draft.skillIds ?? []).length > 0",
        "|| draft.pendingReads > 0 || draft.submitting;",
    ),
    # 模板：读取与提交先确认，空草稿直接应用，同文同附件同技能才直接应用。
    (
        "export function templateFillIntent(draft: ComposerDraft, template: string): \"apply\" | \"confirm\" {",
        'if (draft.pendingReads > 0 || draft.submitting) return "confirm";',
        'if (!homeDraftHasContent(draft)) return "apply";',
        "const sameText = draft.text.trim() === template.trim();",
        'if (sameText && draft.attachments.length === 0 && (draft.skillIds ?? []).length === 0) return "apply";',
        'return "confirm";',
    ),
    # 技能：已选或已达上限原样返回，否则追加并保留草稿。
    (
        "export function withHomeDraftSkill(draft: ComposerDraft, skillId: string): ComposerDraft {",
        "const current = draft.skillIds ?? [];",
        LIMIT_LINE,
        "return { ...draft, skillIds: [...current, skillId] };",
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


def _imports(source: str) -> list[str]:
    return [line for line in source.splitlines() if line.startswith("import ")]


def _rewrite(source: str) -> str:
    # 类型说明符随导入一起去掉，值导入改成显式扩展名，Node 才能直接加载。
    rewritten = source.replace(HOME_IMPORT, 'import { MAX_TURN_SKILLS } from "./composerDraft.ts";', 1)
    if _imports(rewritten) != ['import { MAX_TURN_SKILLS } from "./composerDraft.ts";']:
        raise ValueError(f"{HOME} 的导入结构已变化，需要更新改写")
    return rewritten


def _rewrite_draft(source: str) -> str:
    rewritten = "".join(
        line for line in source.splitlines(keepends=True) if not line.startswith("import type ")
    ).replace('from "@boss-harness/shared";', 'from "./shared.ts";')
    if any(not line.endswith('from "./shared.ts";') for line in _imports(rewritten)):
        raise ValueError(f"{COMPOSER_DRAFT} 的导入结构已变化，需要更新改写")
    return rewritten


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, HOME)
    for group in ORDERED:
        checked += _ordered(group, source, HOME)
    # 反向断言：读取或提交期间必须确认；技能上限必须包含恰好达到上限的那一项，
    # 且只能与 MAX_TURN_SKILLS 比较；重复技能不得追加。
    if 'if (draft.pendingReads > 0 || draft.submitting) return "apply";' in source:
        raise ValueError(f"{HOME} 的读取或提交期间必须确认覆盖")
    if "current.length > MAX_TURN_SKILLS" in source:
        raise ValueError(f"{HOME} 的技能上限必须包含恰好达到上限的那一项")
    if re.search(r"current\.length\s*>=?\s*\d", source):
        raise ValueError(f"{HOME} 的技能上限必须引用 MAX_TURN_SKILLS，不得写成数字")
    if "current.includes(skillId) ||" not in source:
        raise ValueError(f"{HOME} 的重复技能必须原样返回")
    return checked + 4


def _check_behaviors() -> int:
    source = _read(HOME)
    draft_source = _read(COMPOSER_DRAFT)
    shared = _read(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "homeDraftFill.ts").write_text(_rewrite(source), encoding="utf-8")
        (folder / "composerDraft.ts").write_text(_rewrite_draft(draft_source), encoding="utf-8")
        (folder / "shared.ts").write_text(shared, encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("首页草稿行为用例失败：" + detail[:400])
    if f"PASS {EXPECTED}" not in result.stdout:
        raise ValueError(f"首页草稿行为用例数量不符：{result.stdout.strip()}")
    return EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_home_draft.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_home_draft.py")
    if "共 31 项结构、36 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_home_draft.py 检查 31 项结构、36 项行为")
    return 2


def check_home_draft() -> tuple[int, int]:
    structure = _check_structure(_read(HOME))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_home_draft()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"首页草稿核对失败，{error}", file=sys.stderr)
        return 2
    print(f"首页草稿一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
