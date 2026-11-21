#!/usr/bin/env python3
"""核对上下文编辑与摘要检查点的读取边界。

`context.py` 决定持久记录如何进入模型上下文与展示路径：编辑记录在模型路径必须
整体严格校验，在展示路径逐条跳过损坏记录；摘要检查点只信任内核写入的公开字段。
这里固定编辑目标、替换文本上限、`originalInput` 不得绕过编辑投影、编辑入口的
摘要与来源摘要校验、写入锁内先构造响应再落盘，以及检查点的字段白名单、
来源完整性、运行中条目与原始记录一致性，并直接调用编辑、检查点与来源摘要
纯函数核对运行行为。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/context.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.context import (  # noqa: E402
    ContextService, _context_edit, _is_one_of, _public_checkpoint)

CONSTANT_FRAGMENTS = (
    '_FINISHED_TURN_STATUSES = frozenset({"completed", "interrupted", "blocked", "error"})',
    "_CONTEXT_EDIT_MAX_CHARS = 32_000",
    "_CONTEXT_EDIT_MAX_BYTES = 128 * 1024",
    '_PUBLIC_CHECKPOINT_TEXT_LIMITS = {\n    "summary": 32_000, "throughTurnId": 128, "sourceDigest": 64,',
    '_PUBLIC_CHECKPOINT_INT_FIELDS = frozenset({"digestVersion", "modelRequestCount", "sourceCharacters"})',
    "_MAX_PUBLIC_CHECKPOINT_INT = 2 ** 53 - 1",
)
PUBLIC_CHECKPOINT_FRAGMENTS = (
    "for key, limit in _PUBLIC_CHECKPOINT_TEXT_LIMITS.items():",
    "if isinstance(value, str) and len(value) <= limit:",
    "if type(value) is int and 0 <= value <= _MAX_PUBLIC_CHECKPOINT_INT:",
    "return public",
)
EDIT_FRAGMENTS = (
    'if entry.get("type") == "item":',
    "seen_items.add(entry.get(\"id\"))",
    'if (not isinstance(payload, dict) or set(payload) != {"targetItemId", "replacementText"}',
    "or not isinstance(target, str) or not target or target not in seen_items",
    "or (replacement is not None and not isinstance(replacement, str))",
    "(not replacement.strip() or len(replacement) > _CONTEXT_EDIT_MAX_CHARS",
    'or len(replacement.encode("utf-8")) > _CONTEXT_EDIT_MAX_BYTES))):',
    "if strict:",
    "raise ValueError(\"会话上下文编辑记录无效；已停止生成模型上下文\")",
    'edits[target] = {"entryId": entry.get("id"), "replacementText": replacement}',
)
APPLY_FRAGMENTS = (
    "if set(edits) - set(by_id):",
    "raise ValueError(\"会话上下文编辑引用了不存在的条目；已停止生成模型上下文\")",
    'if (not _is_one_of(item.get("kind"), {"userMessage", "agentMessage"})',
    'or not isinstance(item.get("text"), str)):',
    'item.pop("originalInput", None)',
    'item["text"] = edit["replacementText"] or ""',
    'item["contextEdit"] = {"entryId": edit["entryId"],',
    '"excluded": edit["replacementText"] is None}',
    "for target, edit in cls._context_edit_entries(entries, strict=False).items()}",
    'value = item.get("contextEdit")',
    "return value if isinstance(value, dict) else {}",
    'if not _context_edit(item).get("excluded") or _is_one_of(item.get("id"), referenced)]',
    'and not _context_edit(item).get("excluded")]',
)
DIGEST_FRAGMENTS = (
    'value = {key: item.get(key) for key in ("id", "kind", "text", "turnId", "status")}',
    'value["editEntryId"] = edit_entry_id',
    "encoded = _canonical_json_bytes(value)",
    "return hashlib.sha256(encoded).hexdigest()",
)
READ_FRAGMENTS = (
    "if item_id in continuation_item_ids:",
    'reason = "该助手回复包含 Anthropic 工具续接签名；当前版本暂不支持编辑。"',
    "elif item_id in batch_assistant_ids:",
    'reason = "该助手回复与工具调用批次关联；编辑后工具批次无法还原，当前版本暂不支持编辑。"',
    "elif item_id in covered:",
    'reason = "该消息已纳入摘要检查点；请从摘要之后的会话分支继续编辑。"',
    'elif turn is None or not _is_one_of(turn.get("status"), _FINISHED_TURN_STATUSES):',
    'reason = "只能编辑已经结束回合中的消息。"',
    'elif item.get("kind") == "agentMessage" and item.get("status") == "running":',
    'reason = "不能编辑仍在生成的助手消息。"',
    '"canEdit": reason is None, "reason": reason}',
)
EDIT_ENTRY_FRAGMENTS = (
    "if replacement_text is not None and (not isinstance(replacement_text, str)",
    'raise ValueError("替换文本必须为 1 到 32000 字符，且 UTF-8 不超过 128 KiB")',
    'if not isinstance(source_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", source_digest):',
    'raise ValueError("sourceDigest 格式无效")',
    "if not isinstance(item_id, str) or not item_id:",
    "with self.sessions._lock, self.sessions._index.transaction() as connection:",
    "current = self.context_edit_read(thread_id, item_id, entries=entries)",
    'if not current["canEdit"]:',
    'if current["sourceDigest"] != source_digest:',
    'raise ValueError("会话消息或编辑状态已变化，请重新读取后再提交")',
    "result = self.context_edit_read(thread_id, item_id, entries=[*entries, entry.to_dict()])",
    "if validate_response is not None:",
    "validate_response(result)",
    "self.sessions._append_line(self.sessions.path_for(thread_id), entry.to_dict())",
    "self.sessions._index_thread(thread_id, connection)",
)
CHECKPOINT_FRAGMENTS = (
    'checkpoint = {"id": entries[index]["id"], "payload": entries[index]["payload"]}',
    'if (not isinstance(payload.get("summary"), str) or not payload["summary"].strip()',
    'or len(payload["summary"]) > 32_000):',
    'if not isinstance(payload.get("sourceDigest"), str) or re.fullmatch(',
    'raise ValueError("已有摘要的来源记录摘要无效")',
    'if not isinstance(through, str) or through not in positions:',
    'raise ValueError("已有摘要的来源回合不完整")',
    'if any(not _is_one_of(turn.get("status"), _FINISHED_TURN_STATUSES) for turn in prefix):',
    'has_source_ids = "sourceItemIds" in payload',
    'has_source_count = "sourceItemCount" in payload',
    "or (not has_source_ids and not has_source_count)",
    'if any(item.get("status") == "running" for item in selected):',
    "if _canonical_json(original) != _canonical_json(selected):",
    'raise ValueError("已有摘要来源已变化，请先核对并恢复摘要与原始记录的一致性")',
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
            f"上下文编辑行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"上下文编辑行为变化 {label}：期望 {message!r}，实际 {str(error)!r}"
            ) from None
        return 1
    raise ValueError(f"上下文编辑行为变化 {label}：期望 ValueError")


def _item(item_id: str, kind: str = "userMessage", text: str = "原文",
          **extra) -> dict:
    return {"id": item_id, "kind": kind, "text": text, **extra}


def _item_entry(item_id: str) -> dict:
    return {"type": "item", "id": item_id, "payload": {}}


def _edit_entry(entry_id: str, target, replacement, **extra) -> dict:
    return {"type": "context_edit", "id": entry_id,
            "payload": {"targetItemId": target, "replacementText": replacement, **extra}}


def _behavior_checks() -> int:
    checked = 0
    # 检查点白名单：文本字段按上限、整数字段按类型与 2^53-1 边界保留，未知字段剔除。
    checkpoint = {"summary": "s", "throughTurnId": "t", "sourceDigest": "d",
                  "digestVersion": 1, "modelRequestCount": 0,
                  "sourceCharacters": 2 ** 53 - 1, "extra": "x"}
    checked += _expect_value(_public_checkpoint(checkpoint), {
        "summary": "s", "throughTurnId": "t", "sourceDigest": "d",
        "digestVersion": 1, "modelRequestCount": 0,
        "sourceCharacters": 2 ** 53 - 1}, "检查点白名单")
    checked += _expect_value(_public_checkpoint({}), {}, "检查点空对象")
    checked += _expect_value(
        _public_checkpoint({"summary": "x" * 32000}), {"summary": "x" * 32000}, "检查点文本等于上限")
    checked += _expect_value(
        _public_checkpoint({"summary": "x" * 32001, "throughTurnId": "x" * 129,
                            "sourceDigest": "x" * 65}), {}, "检查点文本超限")
    checked += _expect_value(
        _public_checkpoint({"summary": 1, "throughTurnId": None, "sourceDigest": []}),
        {}, "检查点文本类型")
    checked += _expect_value(
        _public_checkpoint({"digestVersion": -1, "modelRequestCount": 2 ** 53,
                            "sourceCharacters": True}), {}, "检查点整数边界")
    checked += _expect_value(
        _public_checkpoint({"digestVersion": 1.0, "modelRequestCount": "1",
                            "sourceCharacters": None}), {}, "检查点整数类型")
    # 类型收窄：集合成员只接受字符串，编辑标注只接受对象。
    checked += _expect_value(_is_one_of("a", frozenset({"a", "b"})), True, "集合成员")
    checked += _expect_value(_is_one_of("c", frozenset({"a", "b"})), False, "集合非成员")
    checked += _expect_value(_is_one_of(1, frozenset({"1"})), False, "集合类型收窄")
    edit = {"entryId": "e", "excluded": False}
    checked += _expect_value(_context_edit({"contextEdit": edit}) is edit, True, "编辑原样返回")
    checked += _expect_value(_context_edit({"contextEdit": "x"}), {}, "编辑非对象")
    checked += _expect_value(_context_edit({}), {}, "编辑缺失")
    # 编辑记录：合法替换与删除都投影；严格报错、宽松跳过。
    entries = [_item_entry("m1"), _item_entry("m2"),
               _edit_entry("e1", "m1", "新文"), _edit_entry("e2", "m2", None)]
    checked += _expect_value(ContextService._context_edit_entries(entries), {
        "m1": {"entryId": "e1", "replacementText": "新文"},
        "m2": {"entryId": "e2", "replacementText": None}}, "编辑映射")
    checked += _expect_error(
        lambda: ContextService._context_edit_entries(
            [_item_entry("m1"), _edit_entry("e1", "m1", "  ")]),
        "会话上下文编辑记录无效；已停止生成模型上下文", "严格坏记录")
    checked += _expect_value(
        ContextService._context_edit_entries(
            [_item_entry("m1"), _edit_entry("bad", "m1", "  "),
             _edit_entry("e1", "m1", "新文")], strict=False),
        {"m1": {"entryId": "e1", "replacementText": "新文"}}, "宽松跳过")
    checked += _expect_error(
        lambda: ContextService._context_edit_entries(
            [_edit_entry("e1", "late", "x"), _item_entry("late")]),
        "会话上下文编辑记录无效；已停止生成模型上下文", "目标先出现")
    bad_entries = (
        ("payload 非对象", {"type": "context_edit", "id": "e", "payload": []}),
        ("payload 多键", {"type": "context_edit", "id": "e", "payload": {
            "targetItemId": "m1", "replacementText": "x", "x": 1}}),
        ("payload 缺键", {"type": "context_edit", "id": "e", "payload": {
            "targetItemId": "m1"}}),
        ("目标为空", _edit_entry("e", "", "x")),
        ("目标非字符串", _edit_entry("e", 1, "x")),
        ("目标不存在", _edit_entry("e", "ghost", "x")),
        ("替换非字符串", _edit_entry("e", "m1", 1)),
    )
    for label, entry in bad_entries:
        checked += _expect_error(
            lambda entry=entry: ContextService._context_edit_entries(
                [_item_entry("m1"), entry]),
            "会话上下文编辑记录无效；已停止生成模型上下文", label)
    checked += _expect_value(
        len(ContextService._context_edit_entries(
            [_item_entry("m1"), _edit_entry("e", "m1", "x" * 32000)])),
        1, "替换 32000 字符")
    checked += _expect_error(
        lambda: ContextService._context_edit_entries(
            [_item_entry("m1"), _edit_entry("e", "m1", "x" * 32001)]),
        "会话上下文编辑记录无效；已停止生成模型上下文", "替换 32001 字符")
    checked += _expect_value(
        ContextService._context_edit_entries(
            [_item_entry("m1"), _edit_entry("e1", "m1", "一"),
             _edit_entry("e2", "m1", "二")]),
        {"m1": {"entryId": "e2", "replacementText": "二"}}, "同目标后写覆盖")
    checked += _expect_value(
        ContextService._context_edit_entries(
            [{"type": "turn", "id": "t"}, _item_entry("m1"),
             _edit_entry("e", "m1", None)]),
        {"m1": {"entryId": "e", "replacementText": None}}, "其他类型忽略")
    # 应用编辑：返回新副本、剔除 originalInput、删除标注 excluded、目标必须可编辑。
    items = [_item("m1", originalInput="raw")]
    copied = ContextService._apply_context_edits(items, [])
    checked += _expect_value(copied, items, "无编辑副本内容")
    checked += _expect_value(copied[0] is items[0], False, "无编辑新副本")
    checked += _expect_value("originalInput" in items[0], True, "输入不被修改")
    checked += _expect_value(
        ContextService._apply_context_edits(
            items, [_item_entry("m1"), _edit_entry("e1", "m1", "新文")]),
        [{"id": "m1", "kind": "userMessage", "text": "新文",
          "contextEdit": {"entryId": "e1", "excluded": False}}], "替换与剔除原始输入")
    removed = ContextService._apply_context_edits(
        items, [_item_entry("m1"), _edit_entry("e1", "m1", None)])
    checked += _expect_value(
        (removed[0]["text"], removed[0]["contextEdit"]),
        ("", {"entryId": "e1", "excluded": True}), "删除标注")
    checked += _expect_error(
        lambda: ContextService._apply_context_edits(
            [_item("m1")], [_item_entry("m2"), _edit_entry("e", "m2", "x")]),
        "会话上下文编辑引用了不存在的条目；已停止生成模型上下文", "目标条目缺失")
    checked += _expect_error(
        lambda: ContextService._apply_context_edits(
            [_item("m1", kind="toolCall")],
            [_item_entry("m1"), _edit_entry("e", "m1", "x")]),
        "会话上下文编辑目标无效；已停止生成模型上下文", "非消息目标")
    checked += _expect_error(
        lambda: ContextService._apply_context_edits(
            [{"id": "m1", "kind": "userMessage", "text": 1}],
            [_item_entry("m1"), _edit_entry("e", "m1", "x")]),
        "会话上下文编辑目标无效；已停止生成模型上下文", "正文非字符串")
    checked += _expect_value(
        ContextService._apply_context_edits(
            [_item("m1", kind="agentMessage")],
            [_item_entry("m1"), _edit_entry("e", "m1", "x")])[0]["contextEdit"],
        {"entryId": "e", "excluded": False}, "助手消息可编辑")
    # 来源摘要：64 位小写十六进制、确定、随正文与编辑编号变化。
    item = _item("m1", text="原文", turnId="t1", status="completed")
    first = ContextService._context_edit_source_digest(item, "e1")
    checked += _expect_value(
        (len(first), first == first.lower(),
         all(character in "0123456789abcdef" for character in first)),
        (64, True, True), "来源摘要格式")
    checked += _expect_value(
        ContextService._context_edit_source_digest(dict(item), "e1"), first, "来源摘要确定")
    checked += _expect_value(
        ContextService._context_edit_source_digest(item, "e2") != first, True, "来源摘要敏感")
    checked += _expect_value(
        ContextService._context_edit_source_digest(item, None) != first, True, "来源摘要空编辑")
    # 检查点来源：sourceItemIds 原样，非字符串拒绝；缺省按 sourceItemCount 截取。
    checked += _expect_value(
        ContextService._checkpoint_source_item_ids(
            {"sourceItemIds": ["a", "b"]}, [_item("x")]), ["a", "b"], "来源 id 列表")
    checked += _expect_error(
        lambda: ContextService._checkpoint_source_item_ids({"sourceItemIds": ["a", 1]}, []),
        "已有摘要的来源记录无效", "来源 id 非字符串")
    checked += _expect_value(
        ContextService._checkpoint_source_item_ids(
            {"sourceItemCount": 2}, [_item("a"), _item("b"), _item("c")]),
        ["a", "b"], "来源计数截取")
    for label, count in (("来源计数为布尔", True), ("来源计数为负", -1), ("来源计数超长", 4)):
        checked += _expect_error(
            lambda count=count: ContextService._checkpoint_source_item_ids(
                {"sourceItemCount": count},
                [_item("a"), _item("b"), _item("c")]),
            "已有摘要的来源记录无效", label)
    # 展示投影：宽松读取并只保留 entryId 与 excluded。
    checked += _expect_value(
        ContextService.context_edit_states(
            [_item_entry("m1"), _edit_entry("bad", "m1", "  "),
             _edit_entry("e1", "m1", None)]),
        {"m1": {"entryId": "e1", "excluded": True}}, "展示投影宽松")
    return checked


def check_context_edits() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (CONSTANT_FRAGMENTS, PUBLIC_CHECKPOINT_FRAGMENTS, EDIT_FRAGMENTS,
                      APPLY_FRAGMENTS, DIGEST_FRAGMENTS, READ_FRAGMENTS,
                      EDIT_ENTRY_FRAGMENTS, CHECKPOINT_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    # 编辑入口：校验现状与摘要，再构造提交后响应；响应校验必须先于落盘。
    checked += _ordered(
        (
            'if not current["canEdit"]:',
            'if current["sourceDigest"] != source_digest:',
            "result = self.context_edit_read(thread_id, item_id, entries=[*entries, entry.to_dict()])",
            "validate_response(result)",
            "self.sessions._append_line(self.sessions.path_for(thread_id), entry.to_dict())",
        ),
        module,
        MODULE,
    )
    # 检查点：摘要与来源摘要、回合完整性、来源条目数、运行中条目、原始记录一致性。
    checked += _ordered(
        (
            'raise ValueError("已有摘要的来源记录摘要无效")',
            'raise ValueError("已有摘要的来源回合不完整")',
            "has_source_ids = \"sourceItemIds\" in payload",
            'if any(item.get("status") == "running" for item in selected):',
            "if _canonical_json(original) != _canonical_json(selected):",
        ),
        module,
        MODULE,
    )
    # 反向断言：展示路径是唯一允许跳过损坏编辑的入口；模型投影不得复用 lenient 读取。
    if module.count("_context_edit_entries(entries, strict=False)") != 1:
        raise ValueError(f"{MODULE} 只有 context_edit_states 可以跳过损坏编辑")
    if module.count('item.get("contextEdit")') != 1:
        raise ValueError(f"{MODULE} 的编辑标注必须经 _context_edit 映射读取")
    return checked + 2 + _behavior_checks()


def main() -> int:
    try:
        checked = check_context_edits()
    except ValueError as error:
        print(f"上下文编辑核对失败，{error}", file=sys.stderr)
        return 2
    print(f"上下文编辑一致：{checked} 项编辑、检查点与摘要防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
