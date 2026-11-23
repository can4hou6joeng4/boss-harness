#!/usr/bin/env python3
"""核对本地界面偏好的形状校验。

`preferenceShapes.ts` 校验从 `localStorage` 读回的界面偏好：只保留可安全渲染的
部分，其余回退默认值。这里静态核对模块契约，并用 Node 直接加载真实模块，覆盖
字符串集合去重、映射类型过滤、分组去重与字段校验、布尔映射与布尔偏好回退。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/preferenceShapes.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import type { ProjectFolder } from "./mockData";',
    " * 本地界面偏好的形状校验。",
    " * 其余回退默认值，避免 `includes` / `new Set` / `filter` 在渲染时抛出并白屏。",
    "/** 字符串集合：丢弃非字符串、空串与重复项。 */",
    "export function stringList(value: unknown): string[] {",
    'return [...new Set(value.filter((item): item is string => typeof item === "string" && item.trim().length > 0))];',
    "/** 字符串映射（别名、线程分组）：丢弃非字符串值；数组与原始值视为空。 */",
    "export function stringRecord(value: unknown): Record<string, string> {",
    'return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string"));',
    "/** 本地分组：只保留 id 与名称有效的对象并按 id 去重；会话由内核列表与线程分组映射产生。 */",
    "export function projectFolders(value: unknown): ProjectFolder[] {",
    'if (typeof folder.id !== "string" || !folder.id.trim() || typeof folder.name !== "string" || !folder.name.trim()) return [];',
    "if (seen.has(folder.id)) return [];",
    "return [{ id: folder.id, name: folder.name, sessions: [] }];",
    "/** 布尔映射（折叠状态）：丢弃非布尔值；null、数组与原始值视为空。 */",
    "export function booleanRecord(value: unknown): Record<string, boolean> {",
    'return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, boolean] => typeof entry[1] === "boolean"));',
    "/** 布尔偏好：只有真正的布尔值生效，其余使用默认值。 */",
    "export function booleanPreference(value: unknown, fallback: boolean): boolean {",
    'return typeof value === "boolean" ? value : fallback;',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { stringList, stringRecord, projectFolders, booleanRecord, booleanPreference } = await import(pathToFileURL(process.argv[1]).href);
const folderPairs = value => projectFolders(value).map(folder => [folder.id, folder.name, folder.sessions.length]);
const result = {
  list: [
    stringList(null),
    stringList(["a", "b", "a"]),
    stringList(["a", "", "  ", " b "]),
    stringList([1, "a", null, true, "b"]),
    stringList("nope"),
  ],
  record: [
    stringRecord(null),
    stringRecord([]),
    stringRecord({ a: "1", b: 2, c: "" }),
    stringRecord("x"),
  ],
  folders: [
    folderPairs(null),
    folderPairs([{ id: "1", name: "A" }, { id: "2", name: "B" }]),
    folderPairs([{ id: "1", name: "A" }, { id: "1", name: "B" }, { id: "2", name: "C" }]),
    folderPairs([null, "x", [], { id: "", name: "A" }, { id: "1", name: "  " }, { id: 2, name: "A" }, { id: "1" }, { name: "A" }]),
    folderPairs([{ id: " 1 ", name: " A " }]),
    folderPairs([{ id: "1", name: "A" }, { id: " 1 ", name: "B" }]),
  ],
  booleans: [
    booleanRecord(null),
    booleanRecord({ a: true, b: false, c: 1, d: "true", e: null }),
    booleanRecord([]),
  ],
  preference: [
    booleanPreference(true, false),
    booleanPreference(false, true),
    booleanPreference("true", true),
    booleanPreference(0, false),
    booleanPreference(null, true),
    booleanPreference(undefined, true),
    booleanPreference(1, false),
    booleanPreference("false", false),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_LIST = (
    [],
    ["a", "b"],
    ["a", " b "],
    ["a", "b"],
    [],
)
EXPECTED_RECORD = (
    {},
    {},
    {"a": "1", "c": ""},
    {},
)
EXPECTED_FOLDERS = (
    [],
    [["1", "A", 0], ["2", "B", 0]],
    [["1", "A", 0], ["2", "C", 0]],
    [],
    [[" 1 ", " A ", 0]],
    [["1", "A", 0], [" 1 ", "B", 0]],
)
EXPECTED_BOOLEANS = (
    {},
    {"a": True, "b": False},
    {},
)
EXPECTED_PREFERENCE = (True, False, True, False, True, True, False, False)
LABELS = {"list": "字符串集合", "record": "字符串映射", "folders": "分组",
          "booleans": "布尔映射", "preference": "布尔偏好"}


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
        raise ValueError("Node 本地偏好试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 本地偏好试算失败，请核对 Node.js 24+ 与 preferenceShapes.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的本地偏好结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"本地偏好{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"本地偏好{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["list"], EXPECTED_LIST, LABELS["list"])
            + _compare(payload["record"], EXPECTED_RECORD, LABELS["record"])
            + _compare(payload["folders"], EXPECTED_FOLDERS, LABELS["folders"])
            + _compare(payload["booleans"], EXPECTED_BOOLEANS, LABELS["booleans"])
            + _compare(payload["preference"], EXPECTED_PREFERENCE, LABELS["preference"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_preference_shapes.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_preference_shapes.py")
    if "共 20 项结构、26 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_preference_shapes.py 检查 20 项结构、26 项行为")
    return 2


def check_preference_shapes() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_preference_shapes()
    except (OSError, ValueError) as error:
        print(f"本地偏好规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"本地偏好规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
