#!/usr/bin/env python3
"""核对桌面快捷键匹配与键位文案的平台规则。

`shortcuts.ts` 决定 ⌘ / Ctrl 组合是否触发：只接受当前平台的主修饰键、
另一平台修饰键一律拒绝；字母键精确匹配 Shift，符号键在未声明 Shift 时
放宽以兼容德语、法语布局；Windows 的 AltGr 报告为 Ctrl+Alt，只有带
AltGraph 标记且未声明 Alt 时放行；macOS 的 Option+字母会改写 `key`，
需要按物理键位兜底。`shortcutLabels.ts` 则按平台渲染说明文案。这里用
Node 直接调用两个模块，逐项核对上述规则。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SHORTCUTS = "apps/desktop/src/renderer/src/data/shortcuts.ts"
LABELS = "apps/desktop/src/renderer/src/data/shortcutLabels.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

SHORTCUTS_FRAGMENTS = (
    "export function resolveCommandPlatform(platform: string | undefined | null): CommandPlatform {",
    'value === "darwin" || value.startsWith("mac") ? "mac" : "other"',
    "export function isCommandChord(",
    'const command = platform === "mac" ? event.metaKey : event.ctrlKey;',
    'const foreign = platform === "mac" ? event.ctrlKey : event.metaKey;',
    "const symbolKey = key.length === 1 && !/[a-z]/i.test(key);",
    'const altGraph = platform === "other" && symbolKey && modifiers.alt === undefined',
    'event.getModifierState("AltGraph") === true',
    'const altLetter = platform === "mac" && modifiers.alt === true && /^[a-z]$/i.test(key)',
    "return !foreign && command",
    "export function isNotificationsShortcut(",
    "return isCommandChord(event, \"a\", { shift: true }, platform);",
)
LABELS_FRAGMENTS = (
    "const MODIFIER_LABELS: ReadonlyArray<readonly [string, string]> = [",
    '["⌘", "Ctrl+"],',
    '["⌥", "Alt+"],',
    '["⇧", "Shift+"],',
    'return replaced.replace(/\\+ /g, "+").replace(/\\+$/, "");',
    "export function currentShortcutLabel(label: string): string {",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { isCommandChord, resolveCommandPlatform } = await import(pathToFileURL(process.argv[1]).href);
const { shortcutKeyLabel } = await import(pathToFileURL(process.argv[2]).href);
function ev(key, mods = {}) {
  return { key, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, ...mods };
}
const results = {
  platform: [
    resolveCommandPlatform("darwin"),
    resolveCommandPlatform("MacIntel"),
    resolveCommandPlatform("win32"),
    resolveCommandPlatform("linux"),
    resolveCommandPlatform(undefined),
    resolveCommandPlatform(null),
  ],
  chords: [
    isCommandChord(ev("b", { metaKey: true }), "b", {}, "mac"),
    isCommandChord(ev("b", { ctrlKey: true }), "b", {}, "mac"),
    isCommandChord(ev("b", { metaKey: true, shiftKey: true }), "b", {}, "mac"),
    isCommandChord(ev("∫", { metaKey: true, altKey: true, code: "KeyB" }), "b", { alt: true }, "mac"),
    isCommandChord(ev("[", { metaKey: true }), "[", {}, "mac"),
    isCommandChord(ev("[", { metaKey: true, shiftKey: true }), "[", {}, "mac"),
    isCommandChord(ev("[", { ctrlKey: true }), "[", {}, "mac"),
    isCommandChord(ev("[", { ctrlKey: true, altKey: true, getModifierState: (name) => name === "AltGraph" }), "[", {}, "other"),
    isCommandChord(ev("[", { ctrlKey: true, altKey: true }), "[", {}, "other"),
    isCommandChord(ev("k", { ctrlKey: true }), "k", {}, "other"),
    isCommandChord(ev("k", { metaKey: true }), "k", {}, "other"),
    isCommandChord(ev("Enter", { metaKey: true }), "enter", {}, "mac"),
  ],
  labels: [
    shortcutKeyLabel("⌘⇧K", "other"),
    shortcutKeyLabel("⌘", "other"),
    shortcutKeyLabel("⌘[ / ⌘]", "other"),
    shortcutKeyLabel("Esc Esc", "other"),
    shortcutKeyLabel("⌘⇧K", "mac"),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_PLATFORM = ("mac", "mac", "other", "other", "other", "other")
EXPECTED_CHORDS = (True, False, False, True, True, True, False, True, False, True, False, True)
EXPECTED_LABELS = ("Ctrl+Shift+K", "Ctrl", "Ctrl+[ / Ctrl+]", "Esc Esc", "⌘⇧K")


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # shortcutLabels.ts 以无扩展名相对路径导入 shortcuts；Node 的类型剥离只解析显式
    # 扩展名，所以复制到临时目录并把导入改成 file URL，不修改仓库源文件。
    labels_source = _read(LABELS).replace(
        'from "./shortcuts"',
        f'from "{(ROOT / SHORTCUTS).as_uri()}"',
    )
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory) / "shortcutLabels.ts"
        temp.write_text(labels_source, encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
                 str(ROOT / SHORTCUTS), str(temp)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 快捷键试算失败，请核对 Node.js 24+ 与 shortcuts.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的快捷键结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回快捷键矩阵")
    for key in ("platform", "chords", "labels"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"快捷键{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"快捷键{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["platform"], EXPECTED_PLATFORM, "平台")
    checked += _compare(payload["chords"], EXPECTED_CHORDS, "组合")
    checked += _compare(payload["labels"], EXPECTED_LABELS, "文案")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_shortcuts.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_shortcuts.py")
    if "共 18 项结构、23 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_shortcuts.py 检查 18 项结构、23 项行为")
    return 2


def check_shortcuts() -> tuple[int, int]:
    shortcuts = _read(SHORTCUTS)
    labels = _read(LABELS)
    structure = _expect(SHORTCUTS_FRAGMENTS, shortcuts, SHORTCUTS)
    structure += _expect(LABELS_FRAGMENTS, labels, LABELS)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_shortcuts()
    except (OSError, ValueError) as error:
        print(f"快捷键规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"快捷键规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
