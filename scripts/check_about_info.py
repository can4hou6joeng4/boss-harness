#!/usr/bin/env python3
"""核对关于页的环境信息与诊断文本。

`aboutInfo.ts` 把可能缺失或异常的环境字段规范为可展示文本，并生成固定顺序的条目
与诊断字符串。这里静态核对模块契约，并用 Node 直接加载真实模块覆盖空白回退、
平台名称映射、内核连接状态与诊断文本拼接等边界。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/aboutInfo.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    " * 关于页的环境信息与诊断文本。",
    "export interface AboutEnvironment {",
    "export interface AboutField {",
    'export const ABOUT_UNKNOWN = "未知";',
    "export function aboutValue(value: string | null | undefined): string {",
    'if (typeof value !== "string") return ABOUT_UNKNOWN;',
    "const trimmed = value.trim();",
    "return trimmed || ABOUT_UNKNOWN;",
    "export function aboutPlatformLabel(platform: string | null | undefined): string {",
    "const value = aboutValue(platform);",
    'if (value === "darwin") return "macOS";',
    'if (value === "win32") return "Windows";',
    'if (value === "linux") return "Linux";',
    "export function aboutFields(environment: AboutEnvironment): AboutField[] {",
    'value: environment.kernelConnected ? "已连接" : "未连接"',
    "export function aboutDiagnostics(environment: AboutEnvironment): string {",
    'return ["BOSS Harness 诊断信息", ...aboutFields(environment).map(field => `${field.label}：${field.value}`)].join("\\n");',
    " * 不包含路径、凭据、会话内容或任何本机状态目录。",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { aboutValue, aboutPlatformLabel, aboutFields, aboutDiagnostics } = await import(pathToFileURL(process.argv[1]).href);
const env = {
  appVersion: "0.2.0-rc.700", protocolVersion: "0.2.0", electron: "40.0.0",
  chrome: "140.0.0", node: "24.0.0", platform: "darwin", kernelConnected: true,
};
const pair = field => [field.label, field.value];
const result = {
  values: [
    aboutValue(undefined),
    aboutValue(null),
    aboutValue(42),
    aboutValue(""),
    aboutValue("   "),
    aboutValue(" 1.2.3 "),
    aboutValue("0.2.0"),
  ],
  platforms: [
    aboutPlatformLabel("darwin"),
    aboutPlatformLabel("win32"),
    aboutPlatformLabel("linux"),
    aboutPlatformLabel("freebsd"),
    aboutPlatformLabel(" darwin "),
    aboutPlatformLabel(null),
    aboutPlatformLabel("DARWIN"),
  ],
  fields: [
    aboutFields(env).map(pair),
    aboutFields({ kernelConnected: false }).map(pair),
  ],
  diagnostics: [aboutDiagnostics(env)],
};
process.stdout.write(JSON.stringify(result));
"""

UNKNOWN = "未知"
EXPECTED_VALUES = (UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, "1.2.3", "0.2.0")
EXPECTED_PLATFORMS = ("macOS", "Windows", "Linux", "freebsd", "macOS", UNKNOWN, "DARWIN")
FULL_FIELDS = [
    ["应用版本", "0.2.0-rc.700"],
    ["协议版本", "0.2.0"],
    ["Electron", "40.0.0"],
    ["Chromium", "140.0.0"],
    ["Node", "24.0.0"],
    ["平台", "macOS"],
    ["内核", "已连接"],
]
EMPTY_FIELDS = [
    ["应用版本", UNKNOWN],
    ["协议版本", UNKNOWN],
    ["Electron", UNKNOWN],
    ["Chromium", UNKNOWN],
    ["Node", UNKNOWN],
    ["平台", UNKNOWN],
    ["内核", "未连接"],
]
EXPECTED_FIELDS = (FULL_FIELDS, EMPTY_FIELDS)
EXPECTED_DIAGNOSTICS = (
    "BOSS Harness 诊断信息\n"
    "应用版本：0.2.0-rc.700\n"
    "协议版本：0.2.0\n"
    "Electron：40.0.0\n"
    "Chromium：140.0.0\n"
    "Node：24.0.0\n"
    "平台：macOS\n"
    "内核：已连接",
)
LABELS = {"values": "取值", "platforms": "平台", "fields": "条目", "diagnostics": "诊断文本"}


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
        raise ValueError("Node 关于页试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 关于页试算失败，请核对 Node.js 24+ 与 aboutInfo.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的关于页结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"关于页{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"关于页{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["values"], EXPECTED_VALUES, LABELS["values"])
            + _compare(payload["platforms"], EXPECTED_PLATFORMS, LABELS["platforms"])
            + _compare(payload["fields"], EXPECTED_FIELDS, LABELS["fields"])
            + _compare(payload["diagnostics"], EXPECTED_DIAGNOSTICS, LABELS["diagnostics"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_about_info.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_about_info.py")
    if "共 18 项结构、17 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_about_info.py 检查 18 项结构、17 项行为")
    return 2


def check_about_info() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_about_info()
    except (OSError, ValueError) as error:
        print(f"关于页规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"关于页规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
