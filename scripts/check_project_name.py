#!/usr/bin/env python3
"""核对项目显示名称的码点上限。

`projectName.ts` 按 Unicode 码点限制本机项目显示名称：HTML `maxLength` 按 UTF-16
码元计数，含表情的名称会被提前拒绝。这里静态核对模块契约，并在临时目录改写共享
包导入后由 Node 加载真实模块，覆盖边界、表情与空白名称。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/projectName.ts"
SHARED = "packages/shared/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import { codePointLength } from "@boss-harness/shared";',
    "/** 本机项目显示名称上限，按 Unicode 码点计数；HTML `maxLength` 按 UTF-16 码元，需放宽到 2 倍。 */",
    "export const PROJECT_NAME_MAX_LENGTH = 60;",
    "/** 项目显示名称是否超过上限；超限时界面提示并禁用提交。 */",
    "export function projectNameTooLong(name: string): boolean {",
    "return codePointLength(name) > PROJECT_NAME_MAX_LENGTH;",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { PROJECT_NAME_MAX_LENGTH, projectNameTooLong } = await import(pathToFileURL(process.argv[1]).href);
const result = {
  limit: [PROJECT_NAME_MAX_LENGTH],
  cases: [
    projectNameTooLong(""),
    projectNameTooLong("a".repeat(59)),
    projectNameTooLong("a".repeat(60)),
    projectNameTooLong("a".repeat(61)),
    projectNameTooLong("🙂".repeat(60)),
    projectNameTooLong("🙂".repeat(61)),
    projectNameTooLong("x".repeat(59) + "🙂"),
    projectNameTooLong("x".repeat(60) + "🙂"),
    projectNameTooLong(" ".repeat(60)),
    projectNameTooLong(" ".repeat(61)),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_LIMIT = (60,)
EXPECTED_CASES = (False, False, False, True, False, True, False, True, False, True)
LABELS = {"limit": "上限", "cases": "判定"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "projectName.ts"
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
            raise ValueError("Node 项目名称试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 项目名称试算失败，请核对 Node.js 24+ 与 projectName.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的项目名称结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"项目名称{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"项目名称{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["limit"], EXPECTED_LIMIT, LABELS["limit"])
            + _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_project_name.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_project_name.py")
    if "共 6 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_project_name.py 检查 6 项结构、11 项行为")
    return 2


def check_project_name() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_project_name()
    except (OSError, ValueError) as error:
        print(f"项目名称规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"项目名称规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
