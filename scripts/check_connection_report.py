#!/usr/bin/env python3
"""核对连接报告的字段投影与渲染层解析边界，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = "harness/src/boss_harness/application.py"
CONNECTIONS = "harness/src/boss_harness/connections.py"
PROTOCOL = "packages/protocol/src/index.ts"
REPORT = "apps/desktop/src/renderer/src/data/connectionReport.ts"
BRIDGE = "apps/desktop/src/renderer/src/data/harnessBridge.ts"
SECURITY = "apps/desktop/src/main/security.ts"
STATES = frozenset({"unchecked", "checking", "ready", "failed", "blocked", "disabled"})
BROWSER_SOURCES = frozenset({"inherit", "auto", "existing-browser", "stored-cookie"})
AUTH_STATES = frozenset({"complete", "partial", "broken", "missing", "unknown"})
TEXT_FIELDS = frozenset({"provider", "model", "binarySource"})
OPTIONAL_FIELDS = frozenset({"checkedAt", "code", "requestRejected"})
PROTOCOL_FIELDS = STATES | BROWSER_SOURCES | AUTH_STATES | TEXT_FIELDS | OPTIONAL_FIELDS | frozenset({
    "state", "summary", "authState", "browserSourcePolicy", "ConnectionCheck", "ConnectionReport",
})
REPORT_FRAGMENTS = (
    "const SUMMARY_LIMIT = 4096;",
    "const CODE_LIMIT = 120;",
    "const NAME_LIMIT = 200;",
    "const TIME_LIMIT = 64;",
    'new Set(["unchecked", "checking", "ready", "failed", "blocked", "disabled"])',
    'new Set(["inherit", "auto", "existing-browser", "stored-cookie"])',
    'new Set(["complete", "partial", "broken", "missing", "unknown"])',
    'const TEXT_FIELDS = ["provider", "model", "binarySource"] as const;',
    "if (typeof raw.state !== \"string\" || !STATES.has(raw.state)) return null;",
    "if (typeof raw.summary !== \"string\" || raw.summary.length > SUMMARY_LIMIT) return null;",
    "typeof raw.checkedAt !== \"string\" || raw.checkedAt.length > TIME_LIMIT",
    "typeof raw.code !== \"string\" || raw.code.length > CODE_LIMIT",
    "if (typeof text !== \"string\" || text.length > NAME_LIMIT) return null;",
    "if (typeof raw.authState !== \"string\" || !AUTH_STATES.has(raw.authState)) return null;",
    "if (typeof raw.browserSourcePolicy !== \"string\" || !BROWSER_SOURCES.has(raw.browserSourcePolicy)) return null;",
    "if (typeof raw.requestRejected !== \"boolean\") return null;",
    "if (!cli || !model || !platform) return null;",
)
APPLICATION_FRAGMENTS = (
    '"connection/read": lambda p: self.connections.read(),',
    '"connection/check": lambda p: self.connections.start(_text(p, "target")),',
)
CONNECTIONS_FRAGMENTS = (
    "report = deepcopy(self.report)",
    "return report",
    'self.report["cli"]',
    'self.report["model"]',
    'self.report["platform"]',
    'self.report["cli"]["browserSourcePolicy"] = browser_source_policy',
    'self.report["platform"]["browserSourcePolicy"] = browser_source_policy',
)
BRIDGE_FRAGMENTS = (
    "export async function connectionReport(target?: ConnectionTarget)",
    "ClientMethods.connectionCheck : ClientMethods.connectionRead",
    "connectionReportOf(response)",
    'if (!report) throw new Error("连接检查回执无法识别");',
)
SECURITY_FRAGMENTS = (
    '"connection/read", "connection/check",',
    'if (payload.method === "connection/check"',
    '[["local", "model", "platform"].includes(params.target)'.replace('[[', '['),
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def check_connection_report() -> tuple[int, int]:
    checked = 0
    checked += _expect(REPORT_FRAGMENTS, _read(REPORT), "connectionReport.ts")
    checked += _expect(APPLICATION_FRAGMENTS, _read(APPLICATION), "application.py")
    checked += _expect(CONNECTIONS_FRAGMENTS, _read(CONNECTIONS), "connections.py")
    checked += _expect(BRIDGE_FRAGMENTS, _read(BRIDGE), "harnessBridge.ts")
    checked += _expect(SECURITY_FRAGMENTS, _read(SECURITY), "security.ts")
    protocol = _read(PROTOCOL)
    start = protocol.find("export interface ConnectionCheck {")
    end = protocol.find("export interface PlatformLoginStatus", start)
    if start < 0 or end < 0:
        raise ValueError("协议缺少 ConnectionCheck 段")
    block = protocol[start:end]
    for value in sorted(STATES | BROWSER_SOURCES):
        if f'"{value}"' not in block:
            raise ValueError(f"协议 ConnectionCheck 缺少枚举值 {value}")
        checked += 1
    if "authState?: string;" not in block:
        raise ValueError("authState 在协议中保持有界字符串，由渲染层白名单收口")
    checked += 1
    for field in sorted(TEXT_FIELDS | OPTIONAL_FIELDS):
        if f"{field}?:" not in block:
            raise ValueError(f"协议 ConnectionCheck 缺少可选字段 {field}")
        checked += 1
    if "cli: ConnectionCheck; model: ConnectionCheck; platform: ConnectionCheck" not in block:
        raise ValueError("ConnectionReport 必须固定三张卡片")
    checked += 1
    return 5, checked


def main() -> int:
    try:
        paths, guards = check_connection_report()
    except ValueError as error:
        print(f"连接报告字段边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"连接报告字段边界一致：{paths} 条读取路径、{guards} 项字段与投影防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
