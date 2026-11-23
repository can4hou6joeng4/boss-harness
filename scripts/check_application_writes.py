#!/usr/bin/env python3
"""核对应用写入入口：压缩设置、技能写与工作区说明。

`config/autoCompaction/set` 只允许在 default / stored 来源下写盘，环境或显式
来源以带 `code` 的 `-32004` 拒绝；`skills/create|write|delete` 校验参数集合、
id 规则、正文上限与读取摘要，摘要不一致时不覆盖外部修改；`context/instructions/write`
只写首选路径，并把内容错误与系统错误映射成不同的 `WORKSPACE_INSTRUCTIONS_*`。
这里在临时工作区与状态目录中真实构造 `ApplicationService`（`provider=none`），
逐项验证拒绝分支与落盘结果；静态部分锁定这些分支的源码顺序。
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.application import ApplicationService  # noqa: E402
from boss_harness.compaction import CompactionPolicy  # noqa: E402
from boss_harness.models.provider import ModelConfig  # noqa: E402
from boss_harness.rpc import JsonRpcServer  # noqa: E402

MODULE = "harness/src/boss_harness/application.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
ENVIRONMENT_KEYS = (
    "BOSS_HARNESS_COMPACTION", "BOSS_HARNESS_PROVIDER", "BOSS_HARNESS_MODEL",
    "BOSS_HARNESS_EFFORT", "BOSS_HARNESS_MAX_MODEL_REQUESTS", "BOSS_HARNESS_STEERING",
    "BOSS_HARNESS_APPROVAL_TIMEOUT", "BOSS_HARNESS_ATTACHMENT_MAX_BYTES",
    "BOSS_HARNESS_ATTACHMENT_MAX_OBJECTS", "BOSS_CLI_BIN", "BOSS_CLI_DATA_DIR",
    "BOSS_HARNESS_BROWSER_SOURCE", "BOSS_HARNESS_MODEL_CALLS_DISABLED",
)
SKILL = "---\nname: Demo\ndescription: 演示技能\n---\n\n正文内容"
COMPACTION_SET = (
    '        if self._auto_compaction_source == "environment":',
    '            raise RpcError(-32004, "自动压缩默认策略由 BOSS_HARNESS_COMPACTION 管理，未写入配置文件",',
    '                           {"code": "AUTO_COMPACTION_ENV_MANAGED"})',
    '        if self._auto_compaction_source == "explicit":',
    '            raise RpcError(-32004, "该内核实例的自动压缩策略由调用方显式指定，不能写入配置文件",',
    '                           {"code": "AUTO_COMPACTION_EXPLICIT"})',
    '        required = {"enabled", "triggerPercent", "keepRecentTokens"}',
    "        if set(params) != required:",
    '            raise ValueError("自动压缩设置必须且只能包含 enabled、triggerPercent、keepRecentTokens")',
    "        policy = self.compaction_policy.override(params)",
    "        with self._policy_lock:",
    "            save_auto_compaction(self.state_dir, params)",
    "            self.compaction_policy = policy",
    '            self._auto_compaction_source = "stored"',
    '        return {"autoCompaction": self.compaction_policy.describe(),',
    '                "autoCompactionSource": self._auto_compaction_source}',
)
SKILLS = (
    ("on_skills_create", (
        '        if set(params) != {"id", "content"}:',
        '            raise ValueError("skills/create 只接受 id 与 content")',
        '            skill = self.skills.create(params.get("id"), params.get("content"))',
        "        except ValueError as exc:",
        '            raise RpcError(-32004, str(exc), {"code": "SKILL_CREATE_INVALID"}) from None',
        "        except OSError as exc:",
        '            raise RpcError(-32004, f"技能创建失败：{exc}", {"code": "SKILL_CREATE_FAILED"}) from None',
        '        return {"skill": skill, "root": self.skills_root}',
    )),
    ("on_skills_write", (
        '        if set(params) != {"id", "content", "expectedDigest"}:',
        '            raise ValueError("skills/write 只接受 id、content 与 expectedDigest")',
        '            skill = self.skills.replace(params.get("id"), params.get("content"),',
        '                                        params.get("expectedDigest"))',
        "        except ValueError as exc:",
        '            raise RpcError(-32004, str(exc), {"code": "SKILL_WRITE_INVALID"}) from None',
        "        except OSError as exc:",
        '            raise RpcError(-32004, f"技能写入失败：{exc}", {"code": "SKILL_WRITE_FAILED"}) from None',
        '        return {"skill": skill, "root": self.skills_root}',
    )),
    ("on_skills_delete", (
        '        if set(params) != {"id", "expectedDigest"}:',
        '            raise ValueError("skills/delete 只接受 id 与 expectedDigest")',
        '            removed = self.skills.delete(params.get("id"), params.get("expectedDigest"))',
        "        except ValueError as exc:",
        '            raise RpcError(-32004, str(exc), {"code": "SKILL_DELETE_INVALID"}) from None',
        "        except OSError as exc:",
        '            raise RpcError(-32004, f"技能删除失败：{exc}", {"code": "SKILL_DELETE_FAILED"}) from None',
        '        return {"id": removed["id"], "root": self.skills_root}',
    )),
)
INSTRUCTIONS = (
    '        if set(params) != {"content"}:',
    '            raise ValueError("context/instructions/write 只接受 content")',
    '            return self.workspace_instructions.write_text(params.get("content"))',
    "        except ValueError as exc:",
    '            raise RpcError(-32004, str(exc), {"code": "WORKSPACE_INSTRUCTIONS_INVALID"}) from None',
    "        except OSError as exc:",
    '            raise RpcError(-32004, f"工作区说明写入失败：{exc}",',
    '                           {"code": "WORKSPACE_INSTRUCTIONS_WRITE_FAILED"}) from None',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _tree(relative: str) -> ast.Module:
    try:
        return ast.parse(_read(relative))
    except SyntaxError:
        raise ValueError(f"无法解析 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ApplicationService":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"application.py 缺少 ApplicationService.{name}")


def _check_structures() -> int:
    source = _read(MODULE)
    tree = _tree(MODULE)
    checked = 0
    body = _method(tree, source, "on_config_auto_compaction_set")
    position = -1
    for fragment in COMPACTION_SET:
        found = body.find(fragment, position + 1)
        if found < 0:
            raise ValueError(f"ApplicationService.on_config_auto_compaction_set 的顺序缺少：{fragment}")
        position = found
        checked += 1
    for name, fragments in SKILLS:
        body = _method(tree, source, name)
        position = -1
        for fragment in fragments:
            found = body.find(fragment, position + 1)
            if found < 0:
                raise ValueError(f"ApplicationService.{name} 的顺序缺少：{fragment}")
            position = found
            checked += 1
    body = _method(tree, source, "on_context_instructions_write")
    position = -1
    for fragment in INSTRUCTIONS:
        found = body.find(fragment, position + 1)
        if found < 0:
            raise ValueError(f"ApplicationService.on_context_instructions_write 的顺序缺少：{fragment}")
        position = found
        checked += 1
    return checked


@contextmanager
def _clean_environment(overrides: dict[str, str] | None = None):
    with patch.dict(os.environ, {}, clear=False):
        for name in ENVIRONMENT_KEYS:
            os.environ.pop(name, None)
        if overrides:
            os.environ.update(overrides)
        yield


class _Workspace:
    def __init__(self, directory: str) -> None:
        self.root = Path(directory)
        self.state = self.root / "state"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()

    def service(self, **kwargs) -> ApplicationService:
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, self.state, ModelConfig(provider="none", model="none"),
                                     None, workspace=self.workspace, **kwargs)
        service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                               "protocolVersion": "0.2.0"})
        service.on_initialized(None)
        return service


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"写入入口行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"写入入口行为变化 {label}：期望 {message!r}，实际 {str(error)!r}") from None
        return 1
    raise ValueError(f"写入入口行为变化 {label}：期望 ValueError，实际未抛出")


def _expect_rpc(call, code: int, message: str, data: dict, label: str) -> int:
    try:
        call()
    except Exception as error:  # noqa: BLE001 - 区分 RpcError 与普通错误
        if type(error).__name__ != "RpcError" or error.code != code or str(error) != message or error.data != data:
            raise ValueError(
                f"写入入口行为变化 {label}：期望 ({code}, {message!r}, {data!r})，"
                f"实际 ({type(error).__name__}, {getattr(error, 'code', None)}, "
                f"{str(error)!r}, {getattr(error, 'data', None)!r})") from None
        return 1
    raise ValueError(f"写入入口行为变化 {label}：期望 RpcError({code})，实际未抛出")


SETTINGS = {"enabled": False, "triggerPercent": 60, "keepRecentTokens": 12_000}


def _compaction_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            checked += _expect_value(service._auto_compaction_source, "default", "默认来源")
            checked += _expect_error(
                lambda: service.on_config_auto_compaction_set({"enabled": True}),
                "自动压缩设置必须且只能包含 enabled、triggerPercent、keepRecentTokens", "字段缺失")
            checked += _expect_error(
                lambda: service.on_config_auto_compaction_set({**SETTINGS, "extra": 1}),
                "自动压缩设置必须且只能包含 enabled、triggerPercent、keepRecentTokens", "多余字段")
            checked += _expect_error(
                lambda: service.on_config_auto_compaction_set({**SETTINGS, "enabled": "yes"}),
                "自动压缩 enabled 必须是布尔值", "布尔类型")
            checked += _expect_error(
                lambda: service.on_config_auto_compaction_set({**SETTINGS, "triggerPercent": 0}),
                "自动压缩 triggerPercent 必须是 1 到 100 的整数", "触发比例")
            checked += _expect_error(
                lambda: service.on_config_auto_compaction_set({**SETTINGS, "keepRecentTokens": 0}),
                "自动压缩 keepRecentTokens 必须是 1 到 1000000 的整数", "保留额度")
            checked += _expect_value(service._auto_compaction_source, "default", "拒绝后来源不变")
            result = service.on_config_auto_compaction_set(SETTINGS)
            checked += _expect_value(result, {"autoCompaction": {**SETTINGS, "provider": None,
                                                                 "model": None, "effort": None},
                                             "autoCompactionSource": "stored"}, "保存结果")
            config = service.on_config_read({})
            checked += _expect_value((config["autoCompactionSource"], config["autoCompaction"]),
                                     ("stored", {**SETTINGS, "provider": None, "model": None,
                                                 "effort": None}), "配置读取")
        finally:
            service.close()
        reloaded = workspace.service()
        try:
            checked += _expect_value(reloaded._auto_compaction_source, "stored", "重载来源")
            checked += _expect_value(reloaded.compaction_policy.describe(),
                                     {**SETTINGS, "provider": None, "model": None, "effort": None},
                                     "重载策略")
        finally:
            reloaded.close()
    with TemporaryDirectory() as directory, _clean_environment(
            {"BOSS_HARNESS_COMPACTION": '{"enabled": false}'}):
        service = _Workspace(directory).service()
        try:
            checked += _expect_rpc(
                lambda: service.on_config_auto_compaction_set(SETTINGS), -32004,
                "自动压缩默认策略由 BOSS_HARNESS_COMPACTION 管理，未写入配置文件",
                {"code": "AUTO_COMPACTION_ENV_MANAGED"}, "环境来源拒绝")
        finally:
            service.close()
    with TemporaryDirectory() as directory, _clean_environment():
        service = _Workspace(directory).service(compaction_policy=CompactionPolicy())
        try:
            checked += _expect_rpc(
                lambda: service.on_config_auto_compaction_set(SETTINGS), -32004,
                "该内核实例的自动压缩策略由调用方显式指定，不能写入配置文件",
                {"code": "AUTO_COMPACTION_EXPLICIT"}, "显式来源拒绝")
        finally:
            service.close()
    return checked


def _skill_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            created = service.on_skills_create({"id": "demo", "content": SKILL})
            checked += _expect_value(set(created), {"skill", "root"}, "创建结果键")
            checked += _expect_value(created["root"], ".boss-harness/skills", "技能根")
            checked += _expect_value({key: created["skill"][key] for key in ("id", "name", "description",
                                                                           "bytes")},
                                     {"id": "demo", "name": "Demo", "description": "演示技能",
                                      "bytes": len(SKILL.encode("utf-8"))}, "技能描述")
            read = service.on_skills_read({"id": "demo"})
            checked += _expect_value(set(read), {"id", "name", "description", "digest", "bytes",
                                                 "content", "limitBytes", "root"}, "读取键")
            checked += _expect_value((read["content"], read["limitBytes"]), (SKILL, 65536), "读取正文")
            for params, message, label in (
                ({"id": "Demo", "content": SKILL},
                 "技能 id 只能包含小写字母、数字、下划线与连字符，且不超过 64 字符", "大写 id"),
                ({"id": "../demo", "content": SKILL},
                 "技能 id 只能包含小写字母、数字、下划线与连字符，且不超过 64 字符", "越界 id"),
                ({"id": "a" * 65, "content": SKILL},
                 "技能 id 只能包含小写字母、数字、下划线与连字符，且不超过 64 字符", "超长 id"),
                ({"id": "demo", "content": 1}, "技能正文必须是字符串", "正文类型"),
                ({"id": "demo", "content": "   "}, "技能正文不能为空", "正文空白"),
                ({"id": "demo", "content": "x" * (64 * 1024 + 1)},
                 "技能正文不得超过 65536 字节", "正文上限"),
                ({"id": "demo", "content": SKILL}, "同名技能已存在，不会覆盖", "同名拒绝"),
            ):
                checked += _expect_rpc(
                    lambda params=params: service.on_skills_create(params), -32004, message,
                    {"code": "SKILL_CREATE_INVALID"}, label)
            checked += _expect_error(
                lambda: service.on_skills_create({"id": "demo"}), "skills/create 只接受 id 与 content",
                "创建参数")
            checked += _expect_error(
                lambda: service.on_skills_write({"id": "demo", "content": SKILL}),
                "skills/write 只接受 id、content 与 expectedDigest", "写入参数")
            checked += _expect_rpc(
                lambda: service.on_skills_write({"id": "demo", "content": SKILL, "expectedDigest": "0" * 64}),
                -32004, "技能内容已变化，请刷新后重试", {"code": "SKILL_WRITE_INVALID"}, "摘要不一致")
            checked += _expect_rpc(
                lambda: service.on_skills_write({"id": "demo", "content": SKILL, "expectedDigest": "bad"}),
                -32004, "技能摘要格式无效", {"code": "SKILL_WRITE_INVALID"}, "摘要格式")
            updated = service.on_skills_write({"id": "demo", "content": SKILL + "\n更多",
                                               "expectedDigest": read["digest"]})
            checked += _expect_value(updated["skill"]["bytes"], len((SKILL + "\n更多").encode("utf-8")),
                                     "更新字节数")
            checked += _expect_error(
                lambda: service.on_skills_delete({"id": "demo"}), "skills/delete 只接受 id 与 expectedDigest",
                "删除参数")
            checked += _expect_rpc(
                lambda: service.on_skills_delete({"id": "demo", "expectedDigest": "0" * 64}), -32004,
                "技能内容已变化，请刷新后重试", {"code": "SKILL_DELETE_INVALID"}, "删除摘要不一致")
            (workspace.workspace / ".boss-harness" / "skills" / "demo" / "extra.txt").write_text(
                "extra", encoding="utf-8")
            checked += _expect_rpc(
                lambda: service.on_skills_delete({"id": "demo",
                                                  "expectedDigest": updated["skill"]["digest"]}), -32004,
                "技能目录还包含其他文件，请先手动清理后再删除", {"code": "SKILL_DELETE_INVALID"},
                "删除含额外文件")
            (workspace.workspace / ".boss-harness" / "skills" / "demo" / "extra.txt").unlink()
            deleted = service.on_skills_delete({"id": "demo",
                                                "expectedDigest": updated["skill"]["digest"]})
            checked += _expect_value(deleted, {"id": "demo", "root": ".boss-harness/skills"}, "删除结果")
            checked += _expect_value(service.on_skills_list({})["skills"], [], "删除后列表")
        finally:
            service.close()
    return checked


def _instructions_checks() -> int:
    checked = 0
    with TemporaryDirectory() as directory, _clean_environment():
        workspace = _Workspace(directory)
        service = workspace.service()
        try:
            checked += _expect_error(
                lambda: service.on_context_instructions_write({"text": "x"}),
                "context/instructions/write 只接受 content", "写入参数")
            checked += _expect_rpc(
                lambda: service.on_context_instructions_write({"content": 1}), -32004,
                "工作区说明必须是字符串", {"code": "WORKSPACE_INSTRUCTIONS_INVALID"}, "内容类型")
            checked += _expect_rpc(
                lambda: service.on_context_instructions_write({"content": "x" * (8 * 1024 + 1)}), -32004,
                "工作区说明超过 8192 字节上限", {"code": "WORKSPACE_INSTRUCTIONS_INVALID"}, "内容上限")
            written = service.on_context_instructions_write({"content": "工作区说明"})
            checked += _expect_value(written, {"path": ".boss-harness/CONTEXT.md", "bytes": 15,
                                               "status": "loaded", "limitBytes": 8192}, "写入结果")
            read = service.on_context_instructions_read({})
            checked += _expect_value((read["content"], read["status"], read["pathPreferred"]),
                                     ("工作区说明", "loaded", ".boss-harness/CONTEXT.md"), "读回")
            with patch.object(service.workspace_instructions, "write_text",
                              side_effect=OSError("disk full")):
                checked += _expect_rpc(
                    lambda: service.on_context_instructions_write({"content": "x"}), -32004,
                    "工作区说明写入失败：disk full",
                    {"code": "WORKSPACE_INSTRUCTIONS_WRITE_FAILED"}, "写入失败")
        finally:
            service.close()
    return checked


def _behavior_checks() -> int:
    checked = 0
    checked += _compaction_checks()
    checked += _skill_checks()
    checked += _instructions_checks()
    return checked


def check_writes() -> int:
    reference = _read(TECHNICAL_REFERENCE)
    for marker in ("check_application_writes.py", "### `check_application_writes.py`",
                   "应用写入入口"):
        if marker not in reference:
            raise ValueError(f"技术参考缺少写入入口检查说明：{marker}")
    structural = _check_structures()
    behavioral = _behavior_checks()
    return structural, behavioral


def main() -> int:
    try:
        structural, behavioral = check_writes()
    except ValueError as error:
        print(error)
        return 1
    print(f"应用写入入口一致：{structural} 项结构、{behavioral} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
