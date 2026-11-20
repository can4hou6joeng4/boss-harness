#!/usr/bin/env python3
"""核对首页草稿的填充意图与技能并入。

工作区模板入口此前会直接重置草稿，静默清空正文、附件与已选技能。现在
正文、附件、技能、正在读取附件与提交中都算「有未发送内容」；模板只有在
草稿为空或与模板完全一致时才直接应用。技能入口只并入技能，已选或已达
10 项时原样返回。这里固定这些约定，避免覆盖用户输入。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HOME = "apps/desktop/src/renderer/src/data/homeDraftFill.ts"

FRAGMENTS = (
    'import type { ComposerDraft } from "./composerDraft";',
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
    "if (current.includes(skillId) || current.length >= 10) return draft;",
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
        "if (current.includes(skillId) || current.length >= 10) return draft;",
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


def check_home_draft() -> int:
    source = _read(HOME)
    checked = 0
    checked += _expect(FRAGMENTS, source, HOME)
    for group in ORDERED:
        checked += _ordered(group, source, HOME)
    # 反向断言：读取或提交期间必须确认；技能上限必须包含第 10 项；
    # 重复技能不得追加。
    if 'if (draft.pendingReads > 0 || draft.submitting) return "apply";' in source:
        raise ValueError(f"{HOME} 的读取或提交期间必须确认覆盖")
    if "current.length > 10" in source:
        raise ValueError(f"{HOME} 的技能上限必须包含第 10 项")
    if "current.includes(skillId) ||" not in source:
        raise ValueError(f"{HOME} 的重复技能必须原样返回")
    return checked + 3


def main() -> int:
    try:
        checked = check_home_draft()
    except ValueError as error:
        print(f"首页草稿核对失败，{error}", file=sys.stderr)
        return 2
    print(f"首页草稿一致：{checked} 项填充意图与技能并入")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
