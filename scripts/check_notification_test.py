#!/usr/bin/env python3
"""核对测试通知的结果解读与状态提示。

`notificationTest.ts` 解读主进程测试通知的返回值，并生成设置页状态提示：只有
明确 `sent: true` 才能说已请求展示，发送失败与无法识别返回值必须分开表述。
这里静态核对模块契约，并用 Node 直接加载真实模块覆盖各种回执形态与文案。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/notificationTest.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "/** 主进程测试通知的返回值解读；未确认的情况不能显示成「已发送」。 */",
    'export type NotificationTestOutcome = "sent" | "unsupported" | "failed" | "unconfirmed";',
    "export function readNotificationTestResult(value: unknown): NotificationTestOutcome {",
    'if (!value || typeof value !== "object") return "unconfirmed";',
    'if (record.sent === true) return "sent";',
    'if (record.sent === false && record.supported === false) return "unsupported";',
    'if (record.sent === false && record.supported === true) return "failed";',
    "export function notificationTestStatus(outcome: NotificationTestOutcome): string {",
    'case "sent": return "已请求系统展示测试通知，请留意桌面提醒。";',
    'case "unsupported": return "当前系统不支持系统通知，审批与回合结束不会弹窗提醒。";',
    'case "failed": return "系统支持通知，但发送请求失败；请检查系统通知权限后重试。";',
    'default: return "测试通知返回了无法识别的结果，未能确认是否展示；请检查本机内核与系统通知权限。";',
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { readNotificationTestResult, notificationTestStatus } = await import(pathToFileURL(process.argv[1]).href);
const result = {
  reads: [
    readNotificationTestResult(null),
    readNotificationTestResult(undefined),
    readNotificationTestResult("sent"),
    readNotificationTestResult([]),
    readNotificationTestResult({ sent: true }),
    readNotificationTestResult({ sent: true, supported: false }),
    readNotificationTestResult({ sent: false, supported: false }),
    readNotificationTestResult({ sent: false, supported: true }),
    readNotificationTestResult({ sent: false }),
    readNotificationTestResult({ supported: false }),
    readNotificationTestResult({ sent: "true" }),
    readNotificationTestResult({ sent: 0, supported: false }),
    readNotificationTestResult({}),
    readNotificationTestResult({ sent: true, extra: true }),
  ],
  status: [
    notificationTestStatus("sent"),
    notificationTestStatus("unsupported"),
    notificationTestStatus("failed"),
    notificationTestStatus("unconfirmed"),
    notificationTestStatus("other"),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_READS = (
    "unconfirmed",
    "unconfirmed",
    "unconfirmed",
    "unconfirmed",
    "sent",
    "sent",
    "unsupported",
    "failed",
    "unconfirmed",
    "unconfirmed",
    "unconfirmed",
    "unconfirmed",
    "unconfirmed",
    "sent",
)
EXPECTED_STATUS = (
    "已请求系统展示测试通知，请留意桌面提醒。",
    "当前系统不支持系统通知，审批与回合结束不会弹窗提醒。",
    "系统支持通知，但发送请求失败；请检查系统通知权限后重试。",
    "测试通知返回了无法识别的结果，未能确认是否展示；请检查本机内核与系统通知权限。",
    "测试通知返回了无法识别的结果，未能确认是否展示；请检查本机内核与系统通知权限。",
)
LABELS = {"reads": "回执", "status": "提示"}


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
        raise ValueError("Node 测试通知试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 测试通知试算失败，请核对 Node.js 24+ 与 notificationTest.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的测试通知结果") from None
    for key in LABELS:
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"测试通知{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"测试通知{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _compare_all(payload: dict) -> int:
    return (_compare(payload["reads"], EXPECTED_READS, LABELS["reads"])
            + _compare(payload["status"], EXPECTED_STATUS, LABELS["status"]))


def _check_behaviors() -> int:
    return _compare_all(_node_matrix())


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_notification_test.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_notification_test.py")
    if "共 12 项结构、19 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_notification_test.py 检查 12 项结构、19 项行为")
    return 2


def check_notification_test() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_notification_test()
    except (OSError, ValueError) as error:
        print(f"测试通知规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"测试通知规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
