#!/usr/bin/env python3
"""核对未确认失败的组合说明。

`confirmationFailure.ts` 把「主操作回执未知」与「重新核对也失败」两条原因组合成
一句说明：主因在前、核对失败在后，末尾附后续处理建议。只报主操作会让用户以为
界面仍在核对。桥接依赖在临时目录以固定桩替代，由 Node 直接加载真实模块执行用例。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/confirmationFailure.ts"
DEPENDENCY = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    'import { harnessErrorText } from "./harnessBridge";',
    " * 实际停在过期状态。两条原因都要给出，并明确不会自动重试。",
    "export function unconfirmedFailure(label: string, primary: unknown, verification: unknown, next: string): string {",
    "return `${label}尚未确认：${harnessErrorText(primary)}；重新核对也失败（${harnessErrorText(verification)}）。${next}`;",
)

DEPENDENCY_FRAGMENTS = (
    "export function harnessErrorText(error: unknown): string {",
    '"无法读取本地内核响应"',
)

STUB = """\
export function harnessErrorText(error: unknown): string {
  const value = error && typeof error === "object"
    ? error as { rpcError?: unknown; code?: unknown; message?: unknown; data?: unknown } : null;
  const data = value?.data && typeof value.data === "object" ? value.data as Record<string, unknown> : null;
  const message = typeof value?.message === "string" && value.message.trim()
    ? value.message.trim() : "无法读取本地内核响应";
  if (value?.rpcError === true && typeof value.code === "number") {
    return `${message}（内核 ${value.code}${typeof data?.code === "string" ? ` / ${data.code}` : ""}）`;
  }
  return message;
}
"""

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const m = await import(pathToFileURL(process.argv[1]).href);
const next = "请稍后重试。";
const basic = m.unconfirmedFailure("删除会话", { message: "socket closed" }, { message: "读取失败" }, next);
const cases = [
  basic === "删除会话尚未确认：socket closed；重新核对也失败（读取失败）。请稍后重试。",
  m.unconfirmedFailure("删除会话", { rpcError: true, code: 409, message: "拒绝" }, { message: "读取失败" }, next)
    === "删除会话尚未确认：拒绝（内核 409）；重新核对也失败（读取失败）。请稍后重试。",
  m.unconfirmedFailure("删除会话", undefined, { message: "读取失败" }, next)
    === "删除会话尚未确认：无法读取本地内核响应；重新核对也失败（读取失败）。请稍后重试。",
  m.unconfirmedFailure("删除会话", { message: "socket closed" },
    { rpcError: true, code: 500, message: "内部错误", data: { code: "X" } }, next)
    === "删除会话尚未确认：socket closed；重新核对也失败（内部错误（内核 500 / X））。请稍后重试。",
  m.unconfirmedFailure("删除会话", 42, { message: "读取失败" }, next)
    === "删除会话尚未确认：无法读取本地内核响应；重新核对也失败（读取失败）。请稍后重试。",
  m.unconfirmedFailure("", { message: "a" }, { message: "b" }, next) === "尚未确认：a；重新核对也失败（b）。请稍后重试。",
  m.unconfirmedFailure("删除会话", { message: "a" }, { message: "b" }, "") === "删除会话尚未确认：a；重新核对也失败（b）。",
  basic.indexOf("socket closed") < basic.indexOf("读取失败"),
  basic.includes("；重新核对也失败（读取失败）。"),
  m.unconfirmedFailure("删除会话", { message: "a" }, { message: "b" }, "  留空处理  ")
    === "删除会话尚未确认：a；重新核对也失败（b）。  留空处理  ",
  m.unconfirmedFailure(" 删除会话 ", { message: "a" }, { message: "b" }, next)
    === " 删除会话 尚未确认：a；重新核对也失败（b）。请稍后重试。",
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
        (Path(directory) / "harnessBridge.ts").write_text(STUB, encoding="utf-8")
        target = Path(directory) / "confirmationFailure.ts"
        target.write_text(
            _read(TARGET).replace('from "./harnessBridge"', 'from "./harnessBridge.ts"'),
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
            raise ValueError("Node 未确认失败说明试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 未确认失败说明试算失败，请核对 Node.js 24+ 与 confirmationFailure.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的未确认失败说明结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"未确认失败说明{label}数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got is not want:
            raise ValueError(f"未确认失败说明{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return _compare(payload["cases"], EXPECTED_CASES, LABELS["cases"])


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_confirmation_failure.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_confirmation_failure.py")
    if "共 6 项结构、11 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_confirmation_failure.py 检查 6 项结构、11 项行为")
    return 2


def check_confirmation_failure() -> tuple[int, int]:
    structure = (_expect(FRAGMENTS, _read(TARGET), TARGET)
                 + _expect(DEPENDENCY_FRAGMENTS, _read(DEPENDENCY), DEPENDENCY))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_confirmation_failure()
    except (OSError, ValueError) as error:
        print(f"未确认失败说明核对失败，{error}", file=sys.stderr)
        return 2
    print(f"未确认失败说明一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
