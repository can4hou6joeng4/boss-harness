#!/usr/bin/env python3
"""对照会话元数据更新与归档的字段、上限与幂等口径。

`_validate_changes` 把 `project_id` 规范化为 `projectId` 并按七个字段的白名单
逐个校验；`update_thread` 只在非空时追加 `thread_info` 记录；`archive_thread`
在锁内把未裁决的待审批标记为 `expired` 后写入 `{"archived": true}`，重复归档
幂等；`unarchive_thread` 只在已归档时写记录。本脚本在临时目录构造 `SessionStore`
做行为对照并扫描源码；不访问网络、模型或招聘平台。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SESSION = "harness/src/boss_harness/session.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.session import REASONING_EFFORTS, SessionStore  # noqa: E402

VALIDATE_ORDER = (
    "def _validate_changes(changes: dict) -> dict:",
    "changes = dict(changes)",
    'if "project_id" in changes:',
    'if "projectId" in changes:',
    'raise ValueError("projectId 不可重复提供")',
    'changes["projectId"] = changes.pop("project_id")',
    'if set(changes) - {"title", "projectId", "provider", "model", "cwd", "toolPolicy", "reasoningEffort"}:',
    'raise ValueError("会话元数据包含不支持的更新字段")',
    "for key, value in changes.items():",
    'if key == "toolPolicy" and (not isinstance(value, str) or value not in {"readOnly", "approval"}):',
    'raise ValueError("toolPolicy 必须是 readOnly 或 approval")',
    'if key == "reasoningEffort" and value is not None and value not in REASONING_EFFORTS:',
    'raise ValueError("reasoningEffort 档位无效")',
    'if key == "title" and (not isinstance(value, str) or len(value) > MAX_THREAD_TITLE_CHARS):',
    'if key == "provider" and (not isinstance(value, str) or not value',
    "or len(value) > 64 or any(char.isspace() for char in value)):",
    'raise ValueError("provider 必须是非空 provider id")',
    'if key in {"projectId", "cwd"} and value is not None and not isinstance(value, str):',
    'if key == "projectId" and isinstance(value, str) and len(value) > MAX_PROJECT_ID_CHARS:',
    'if key == "model" and value is not None and not isinstance(value, (str, dict)):',
    'raise ValueError("model 必须是字符串、对象或 null")',
    "_json(changes)",
    "return changes",
)
UPDATE_ORDER = (
    "def update_thread(self, thread_id: str, **changes: Any) -> dict:",
    "changes = self._validate_changes(changes)",
    "if changes:",
    'self.append(thread_id, Entry(type="thread_info", parent_id=self.last_entry_id(thread_id), payload=changes))',
    "return self.get_thread(thread_id)",
)
ARCHIVE_ORDER = (
    "def archive_thread(self, thread_id: str) -> dict:",
    "with self._lock:",
    "thread = self.get_thread(thread_id)",
    'if not thread["archived"]:',
    "entries = self.read_entries(thread_id)",
    "for item in self._project_items(thread_id, entries):",
    'approval = item.get("approval")',
    'if (item.get("executionState") == "pending_approval"',
    'and isinstance(approval, dict) and not approval.get("decision")',
    "and self._valid_approval_item(item, pending_only=False)):",
    'self._append_approval_decision(thread_id, item, "expired", live_owner=False)',
    'payload={"archived": True}',
    "return self.get_thread(thread_id)",
)
UNARCHIVE_ORDER = (
    "def unarchive_thread(self, thread_id: str) -> dict:",
    'if self.get_thread(thread_id)["archived"]:',
    'payload={"archived": False}',
    "return self.get_thread(thread_id)",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, class_name: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少 {class_name}.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_error(action, message: str, label: str) -> None:
    try:
        action()
    except ValueError as error:
        if message not in str(error):
            raise ValueError(f"{label} 错误信息变化：{error}") from None
        return
    raise ValueError(f"{label} 必须被拒绝")


def check_thread_meta() -> int:
    source = _read(SESSION)
    tree = ast.parse(source)
    validate = _method(tree, source, "SessionStore", "_validate_changes")
    update = _method(tree, source, "SessionStore", "update_thread")
    archive = _method(tree, source, "SessionStore", "archive_thread")
    unarchive = _method(tree, source, "SessionStore", "unarchive_thread")
    checked = _ordered(VALIDATE_ORDER, validate, SESSION)
    checked += _ordered(UPDATE_ORDER, update, SESSION)
    checked += _ordered(ARCHIVE_ORDER, archive, SESSION)
    checked += _ordered(UNARCHIVE_ORDER, unarchive, SESSION)
    # 白名单恰好七个字段，规范化先于白名单。
    if validate.count('"title", "projectId", "provider", "model", "cwd", "toolPolicy", "reasoningEffort"') != 1:
        raise ValueError(f"{SESSION} 的会话元数据白名单必须恰好七个字段")
    checked += 1
    if validate.index('changes["projectId"] = changes.pop("project_id")') > validate.index("if set(changes) - {"):
        raise ValueError(f"{SESSION} 的 project_id 必须先去重再进白名单")
    checked += 1
    if validate.count("_json(changes)") != 1 or validate.index("_json(changes)") < validate.index("for key, value in changes.items():"):
        raise ValueError(f"{SESSION} 的元数据必须在逐字段校验后验证可序列化")
    checked += 1
    # 空更新不写记录；归档与恢复各自只在状态变化时写一条。
    if update.count("if changes:") != 1 or update.count("self.append(") != 1:
        raise ValueError(f"{SESSION} 的元数据更新只在非空时写记录")
    checked += 1
    if archive.count('if not thread["archived"]:') != 1:
        raise ValueError(f"{SESSION} 的归档必须在未归档时写入")
    checked += 1
    if archive.count("self._append_approval_decision(thread_id, item, \"expired\", live_owner=False)") != 1:
        raise ValueError(f"{SESSION} 的归档必须结算未裁决审批")
    checked += 1
    if unarchive.count('payload={"archived": False}') != 1 or "for " in unarchive:
        raise ValueError(f"{SESSION} 的恢复只在已归档时写一条记录")
    checked += 1
    for fragment in ("def update_thread(", "def archive_thread(", "def unarchive_thread("):
        if source.count(fragment) != 1:
            raise ValueError(f"{SESSION} 必须只定义一处：{fragment}")
        checked += 1
    for fragment in ("archive = archive_thread", "unarchive = unarchive_thread"):
        if source.count(fragment) != 1:
            raise ValueError(f"{SESSION} 必须保留别名：{fragment}")
        checked += 1
    # 行为：更新、上限、枚举与归档幂等。
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "sessions"
        store = SessionStore(root)
        try:
            thread_id = store.create("初始")["id"]
            before = len(store.read_entries(thread_id))
            if store.update_thread(thread_id)["title"] != "初始" or len(store.read_entries(thread_id)) != before:
                raise ValueError("空更新不得写入记录")
            checked += 1
            updated = store.update_thread(thread_id, title="新的", project_id="p1")
            if updated["title"] != "新的" or updated.get("projectId") != "p1":
                raise ValueError("标题与项目更新必须生效")
            checked += 1
            last = store.read_entries(thread_id)[-1]
            if last.get("type") != "thread_info" or last.get("payload", {}).get("projectId") != "p1":
                raise ValueError("元数据更新必须写入 thread_info 记录")
            checked += 1
            if "project_id" in last.get("payload", {}):
                raise ValueError("project_id 必须规范化为 projectId")
            checked += 1
            for label, changes, message in (
                ("重复项目", {"project_id": "a", "projectId": "b"}, "projectId 不可重复提供"),
                ("未知字段", {"unknown": 1}, "会话元数据包含不支持的更新字段"),
                ("身份字段", {"id": "x"}, "会话元数据包含不支持的更新字段"),
                ("创建时间", {"createdAt": "x"}, "会话元数据包含不支持的更新字段"),
                ("归档标记", {"archived": True}, "会话元数据包含不支持的更新字段"),
                ("工具策略", {"toolPolicy": "all"}, "toolPolicy 必须是 readOnly 或 approval"),
                ("推理档位", {"reasoningEffort": "turbo"}, "reasoningEffort 档位无效"),
                ("标题超长", {"title": "x" * 501}, "title 必须是最多 500 字符的字符串"),
                ("标题非字符串", {"title": 3}, "title 必须是最多 500 字符的字符串"),
                ("provider 为空", {"provider": ""}, "provider 必须是非空 provider id"),
                ("provider 含空白", {"provider": "a b"}, "provider 必须是非空 provider id"),
                ("provider 超长", {"provider": "p" * 65}, "provider 必须是非空 provider id"),
                ("项目编号超长", {"projectId": "x" * 201}, "projectId 必须是最多 200 字符的字符串"),
                ("cwd 类型", {"cwd": 3}, "cwd 必须是字符串或 null"),
                ("model 类型", {"model": 3}, "model 必须是字符串、对象或 null"),
            ):
                _expect_error(lambda changes=changes: store.update_thread(thread_id, **changes), message, label)
                checked += 1
            if store.update_thread(thread_id, title="x" * 500)["title"] != "x" * 500:
                raise ValueError("标题恰好 500 字符必须被接受")
            checked += 1
            for policy in ("readOnly", "approval"):
                if store.update_thread(thread_id, toolPolicy=policy).get("toolPolicy") != policy:
                    raise ValueError("工具策略必须接受 readOnly 与 approval")
                checked += 1
            effort = REASONING_EFFORTS[0]
            if store.update_thread(thread_id, reasoningEffort=effort).get("reasoningEffort") != effort:
                raise ValueError("推理档位必须接受已知枚举")
            checked += 1
            if store.update_thread(thread_id, reasoningEffort=None).get("reasoningEffort") is not None:
                raise ValueError("推理档位必须接受 null")
            checked += 1
            if store.update_thread(thread_id, projectId=None).get("projectId") is not None:
                raise ValueError("项目编号必须接受 null")
            checked += 1
            if store.update_thread(thread_id, cwd=None).get("cwd") is not None:
                raise ValueError("cwd 必须接受 null")
            checked += 1
            if store.update_thread(thread_id, model={"id": "m"}).get("model") != {"id": "m"}:
                raise ValueError("model 必须接受对象")
            checked += 1
            if store.update_thread(thread_id, model="m").get("model") != "m":
                raise ValueError("model 必须接受字符串")
            checked += 1
            try:
                store.update_thread(thread_id, model={"value": object()})
            except TypeError:
                checked += 1
            else:
                raise ValueError("不可序列化的元数据必须被拒绝")
            _expect_error(lambda: store.update_thread("000000000000", title="x"), "会话不存在", "会话不存在")
            checked += 1
            if store.archive_thread(thread_id)["archived"] is not True:
                raise ValueError("归档必须生效")
            checked += 1
            archived_entries = len(store.read_entries(thread_id))
            last = store.read_entries(thread_id)[-1]
            if last.get("type") != "thread_info" or last.get("payload", {}).get("archived") is not True:
                raise ValueError("归档必须写入 archived 记录")
            checked += 1
            if store.archive_thread(thread_id)["archived"] is not True or len(store.read_entries(thread_id)) != archived_entries:
                raise ValueError("重复归档必须幂等")
            checked += 1
            if store.unarchive_thread(thread_id)["archived"] is not False:
                raise ValueError("恢复归档必须生效")
            checked += 1
            restored_entries = len(store.read_entries(thread_id))
            if restored_entries != archived_entries + 1:
                raise ValueError("恢复归档必须只写一条记录")
            checked += 1
            if store.unarchive_thread(thread_id)["archived"] is not False or len(store.read_entries(thread_id)) != restored_entries:
                raise ValueError("重复恢复必须幂等")
            checked += 1
            if store.archive(thread_id)["archived"] is not True or store.unarchive(thread_id)["archived"] is not False:
                raise ValueError("归档别名必须与完整方法一致")
            checked += 1
        finally:
            store.close()
    return checked


def main() -> int:
    try:
        checked = check_thread_meta()
    except (ValueError, SyntaxError) as error:
        print(f"会话元数据核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话元数据一致：{checked} 项字段、上限与归档校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
