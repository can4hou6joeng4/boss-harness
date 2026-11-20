#!/usr/bin/env python3
"""核对会话导出 JSON 的分组结构与严格编码。

JSON 导出供下游脚本读取：回合前的条目必须留在 `beforeFirstTurn`，其余条目追加到
最近回合的 `entries`；文档要带 `schema` 标识、脱敏标记、来源说明、截断与字节预算。
编码必须拒绝非有限数值与过深嵌套，并降级为可读的 `ValueError`，而不是让内部错误
逃逸。这里固定这些结构、顺序、schema 形式与降级文案，避免新增字段悄悄破坏导出契约。
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"

EXPORT_FRAGMENTS = (
    'EXPORT_SCHEMA = "boss-harness-session-export/1"',
    '"schema": EXPORT_SCHEMA',
    "_render_json(meta: dict, units: list[tuple[str, dict]], counts: dict, total_units: int,",
    "turns: list[dict] = []",
    "preamble: list[dict] = []",
    'if unit["kind"] == "turn":',
    'turns.append({**unit, "entries": []})',
    "elif turns:",
    'turns[-1]["entries"].append(unit)',
    "preamble.append(unit)",
    # 文档结构：meta 展开、四项脱敏标记、计数、三类来源与条目分组。
    'document = {**meta, "redaction": {"marks": {"secret": SECRET_MARK, "environment": ENV_MARK,',
    '"path": PATH_MARK, "personalInfo": PII_MARK},',
    '"counts": dict(counts)},',
    '"origins": {"user": "用户输入", "model": "模型判断", "platform": "平台事实（工具结果）"},',
    '"beforeFirstTurn": preamble, "turns": turns, "queue": queue,',
    '"truncated": len(units) < total_units,',
    '"exportedEntries": len(units), "totalEntries": total_units, "maxBytes": max_bytes}',
    # 严格编码：保留中文、两空格缩进、非 JSON 值降级为字符串、拒绝 NaN / Infinity。
    'return json.dumps(document, ensure_ascii=False, indent=2, default=str, allow_nan=False) + "\\n"',
    "except RecursionError:",
    'raise ValueError("导出内容嵌套过深，无法编码为 JSON，已停止导出") from None',
    "except ValueError:\n        # 非有限数值会让严格 JSON 解析器拒绝整份文档",
    'raise ValueError("导出内容包含无法编码的非有限数值，已停止导出") from None',
    # 三种格式共用同一分发入口。
    'render = {"markdown": _render_markdown, "json": _render_json, "html": _render_html}[fmt]',
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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_export_json() -> int:
    export = _read(EXPORT)
    checked = 0
    checked += _expect(EXPORT_FRAGMENTS, export, EXPORT)
    # 分组：回合前条目单独保存，回合条目追加到最近一个回合。
    checked += _ordered(
        (
            "turns: list[dict] = []",
            "preamble: list[dict] = []",
            'if unit["kind"] == "turn":',
            'turns.append({**unit, "entries": []})',
            "elif turns:",
            'turns[-1]["entries"].append(unit)',
            "preamble.append(unit)",
        ),
        export,
        EXPORT,
    )
    # 文档字段：meta、脱敏、来源、分组、截断与预算按固定顺序组装。
    checked += _ordered(
        (
            'document = {**meta, "redaction": {"marks": {"secret": SECRET_MARK, "environment": ENV_MARK,',
            '"path": PATH_MARK, "personalInfo": PII_MARK},',
            '"counts": dict(counts)},',
            '"origins": {"user": "用户输入", "model": "模型判断", "platform": "平台事实（工具结果）"},',
            '"beforeFirstTurn": preamble, "turns": turns, "queue": queue,',
            '"truncated": len(units) < total_units,',
            '"exportedEntries": len(units), "totalEntries": total_units, "maxBytes": max_bytes}',
            "return json.dumps(document, ensure_ascii=False, indent=2, default=str, allow_nan=False)",
        ),
        export,
        EXPORT,
    )
    # 降级：过深嵌套与非有限数值分别转成可读错误。
    checked += _ordered(
        (
            "except RecursionError:",
            'raise ValueError("导出内容嵌套过深，无法编码为 JSON，已停止导出") from None',
            "except ValueError:\n        # 非有限数值会让严格 JSON 解析器拒绝整份文档",
            'raise ValueError("导出内容包含无法编码的非有限数值，已停止导出") from None',
        ),
        export,
        EXPORT,
    )
    # schema 标识：常量必须是「名称/整数版本」，meta 只引用常量而不是另写字面量。
    match = re.search(r'EXPORT_SCHEMA = "([^"]+)"', export)
    if not match or not re.fullmatch(r"[a-z0-9-]+/\d+", match.group(1)):
        raise ValueError(f"{EXPORT} 的 EXPORT_SCHEMA 必须是「名称/整数版本」形式")
    if '"schema": "boss-harness-session-export' in export:
        raise ValueError(f"{EXPORT} 的 meta 必须引用 EXPORT_SCHEMA，不得另写 schema 字面量")
    # 反向断言：不得重新允许 NaN / Infinity 或 ASCII 转义，也不得绕过参数直接编码。
    for forbidden in ("allow_nan=True", "ensure_ascii=True", "json.dumps(document)", "default=repr"):
        if forbidden in export:
            raise ValueError(f"{EXPORT} 的 JSON 导出不得包含 {forbidden}")
    return checked + 3


def main() -> int:
    try:
        checked = check_export_json()
    except ValueError as error:
        print(f"导出 JSON 结构核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 JSON 结构一致：{checked} 项分组、字段、编码与降级防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
