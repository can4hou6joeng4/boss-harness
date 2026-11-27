#!/usr/bin/env python3
"""核对会话导出 JSON 的分组结构与严格编码。

JSON 导出供下游脚本读取：回合前的条目必须留在 `beforeFirstTurn`，其余条目追加到
最近回合的 `entries`；文档要带 `schema` 标识、脱敏标记、来源说明、截断与字节预算。
编码必须拒绝非有限数值与过深嵌套，并降级为可读的 `ValueError`，而不是让内部错误
逃逸。这里固定这些结构、顺序、schema 形式与降级文案，并直接调用 `_render_json`
核对分组、计数快照与编码结果，避免新增字段悄悄破坏导出契约。
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPORT = "harness/src/boss_harness/session_export.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session_export import (  # noqa: E402
    ENV_MARK,
    EXPORT_SCHEMA,
    PATH_MARK,
    PII_MARK,
    SECRET_MARK,
    _render_json,
)

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
    # 显式深度上限：不依赖 json.dumps 的递归异常（Python 3.14 起行为不同）。
    "_EXPORT_MAX_DEPTH = 256",
    "def _export_json_too_deep(value: Any) -> bool:",
    "if _export_json_too_deep(document):",
    'raise ValueError("导出内容嵌套过深，无法编码为 JSON，已停止导出")',
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


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(
            f"导出 JSON 行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, expected: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != expected:
            raise ValueError(
                f"导出 JSON 行为变化 {label}：期望 {expected!r}，实际 {str(error)!r}")
        return 1
    raise ValueError(f"导出 JSON 行为变化 {label}：期望 ValueError")


def _unit(kind: str, name: str, **extra) -> tuple[str, dict]:
    return kind, {"kind": kind, "name": name, **extra}


def _meta(**overrides) -> dict:
    meta = {"schema": EXPORT_SCHEMA, "title": "会话标题"}
    meta.update(overrides)
    return meta


def _render(meta: dict | None = None, units=(), counts: dict | None = None,
            total_units: int = 0, max_bytes: int = 1024, queue: dict | None = None) -> str:
    return _render_json(
        meta or _meta(),
        list(units),
        counts or {"secrets": 0, "environment": 0, "paths": 0, "personalInfo": 0},
        total_units,
        max_bytes,
        queue or {"totalItems": 0, "items": []},
    )


def _behavior_checks() -> int:
    checked = 0

    raw = _render()
    document = json.loads(raw)
    checked += _expect_value(document["schema"], EXPORT_SCHEMA, "schema")
    checked += _expect_value(
        document["redaction"]["marks"],
        {"secret": SECRET_MARK, "environment": ENV_MARK,
         "path": PATH_MARK, "personalInfo": PII_MARK}, "脱敏标记")
    checked += _expect_value(
        document["origins"],
        {"user": "用户输入", "model": "模型判断", "platform": "平台事实（工具结果）"}, "来源说明")
    checked += _expect_value(raw.endswith("\n"), True, "尾部换行")
    checked += _expect_value("会话标题" in raw, True, "中文不转义")
    checked += _expect_value('\n  "schema"' in raw, True, "两空格缩进")
    checked += _expect_value(
        (list(document)[0], list(document)[1]), ("schema", "title"), "字段顺序")
    checked += _expect_value(document["extra"] if "extra" in document else None, None,
                             "默认无额外字段")

    counts = {"secrets": 1, "environment": 2, "paths": 3, "personalInfo": 4}
    raw = _render(counts=counts)
    counts["secrets"] = 99
    checked += _expect_value(
        json.loads(raw)["redaction"]["counts"],
        {"secrets": 1, "environment": 2, "paths": 3, "personalInfo": 4}, "计数写入")

    units = [
        _unit("userInput", "a"),
        _unit("turn", "t1"),
        _unit("userInput", "b"),
        _unit("tool", "c"),
        _unit("turn", "t2"),
        _unit("tool", "d"),
    ]
    document = json.loads(_render(units=units, total_units=len(units)))
    checked += _expect_value(
        [unit["name"] for unit in document["beforeFirstTurn"]], ["a"], "回合前条目")
    checked += _expect_value(
        [[unit["name"] for unit in turn["entries"]] for turn in document["turns"]],
        [["b", "c"], ["d"]], "回合内条目")
    checked += _expect_value(
        (document["turns"][0]["name"], document["turns"][0]["entries"][0]["kind"]),
        ("t1", "userInput"), "回合记录")
    checked += _expect_value(document["truncated"], False, "未截断标记")
    checked += _expect_value(
        (document["exportedEntries"], document["totalEntries"], document["maxBytes"]),
        (len(units), len(units), 1024), "条目计数")

    document = json.loads(_render(units=units[:1], total_units=2))
    checked += _expect_value(
        (document["truncated"], document["exportedEntries"], document["totalEntries"]),
        (True, 1, 2), "截断计数")
    document = json.loads(_render(units=[_unit("userInput", "only")], total_units=1))
    checked += _expect_value(
        (len(document["beforeFirstTurn"]), document["turns"]), (1, []), "无回合分组")
    document = json.loads(_render(queue={"totalItems": 2, "items": [{"queueId": "q"}]}))
    checked += _expect_value(document["queue"]["totalItems"], 2, "队列快照")
    document = json.loads(_render(_meta(extra=1)))
    checked += _expect_value(document["extra"], 1, "额外字段")
    document = json.loads(_render(_meta(path=Path("/tmp/导出"))))
    checked += _expect_value(document["path"], "/tmp/导出", "非 JSON 值转字符串")
    checked += _expect_value(len(units), 6, "输入条目不变")

    checked += _expect_error(
        lambda: _render(_meta(value=float("nan"))),
        "导出内容包含无法编码的非有限数值，已停止导出", "NaN 拒绝")
    checked += _expect_error(
        lambda: _render(_meta(value=float("inf"))),
        "导出内容包含无法编码的非有限数值，已停止导出", "Infinity 拒绝")
    deep: list = []
    cursor = deep
    for _ in range(3_000):
        child: list = []
        cursor.append(child)
        cursor = child
    checked += _expect_error(
        lambda: _render(_meta(deep=deep)),
        "导出内容嵌套过深，无法编码为 JSON，已停止导出", "深层嵌套拒绝")
    def _nested(depth: int) -> list:
        root: list = []
        cursor = root
        for _ in range(depth - 1):
            child: list = []
            cursor.append(child)
            cursor = child
        return root

    checked += _expect_value(
        json.loads(_render(_meta(value=_nested(256))))["schema"], EXPORT_SCHEMA,
        "深度边界内")
    checked += _expect_error(
        lambda: _render(_meta(value=_nested(257))),
        "导出内容嵌套过深，无法编码为 JSON，已停止导出", "拒绝深度边界外")
    return checked


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
    return checked + 3 + _behavior_checks()


def _documentation_check(checked: int) -> None:
    reference = _read(TECHNICAL_REFERENCE)
    if f"总项数 {checked}。" not in reference:
        raise ValueError(
            f"{TECHNICAL_REFERENCE} 缺少导出 JSON 检查的计数：总项数 {checked}。")


def main() -> int:
    try:
        checked = check_export_json()
        _documentation_check(checked)
    except ValueError as error:
        print(f"导出 JSON 结构核对失败，{error}", file=sys.stderr)
        return 2
    print(f"导出 JSON 结构一致：{checked} 项分组、字段、编码、降级防护与渲染行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
