#!/usr/bin/env python3
"""核对应用输入与环境默认值的边界。

`application.py` 的审批期限、过期清扫退避、steering 模式、分支视图、非空文本
参数、工作区相对路径、技能目录回退与检查点回合归属决定启动默认值和 RPC 入参
边界。这里既静态固定关键分支，也直接调用九个辅助函数核对结果与错误文案。
不启动服务、不访问网络，临时目录只用于技能目录回退。
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/application.py"

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness.application import (  # noqa: E402
    DEFAULT_APPROVAL_TIMEOUT_SECONDS,
    _approval_expiry_delay,
    _branch_view,
    _record_checkpoint_turn,
    _relative_workspace_path,
    _skill_catalog_root,
    _steering_mode_value,
    _text,
    approval_timeout_from_environment,
    steering_mode_from_environment,
)

ENVIRONMENT_FRAGMENTS = (
    "DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300.0",
    'raw = source.get("BOSS_HARNESS_APPROVAL_TIMEOUT")',
    "if raw is None or not raw.strip():",
    "_ASCII_FLOAT = re.compile(",
    "if _ASCII_FLOAT.fullmatch(text) is None:",
    "if math.isfinite(value) and value > 0:",
    'raw = os.environ.get("BOSS_HARNESS_STEERING_MODE")',
    'if raw is None or raw == "":',
    "if raw not in STEERING_MODES:",
    'return "all"',
)
DELAY_FRAGMENTS = (
    "delay = 5.0 if deadline is None else min(5.0, max(0.05, deadline - time.time()))",
    "attempts = min(max(failures.values()), 7)",
    "delay = max(delay, min(60.0, 0.5 * (2 ** attempts)))",
)
INPUT_FRAGMENTS = (
    'view = (params or {}).get("view", "log")',
    'if not isinstance(view, str) or view not in {"log", "branch"}:',
    'raise ValueError("view 必须是 log 或 branch")',
    'value = (params or {}).get(key)',
    "if not isinstance(value, str) or not value.strip() or len(value) > maximum:",
    'raise ValueError(f"{key} 必须是非空字符串（最多 {maximum} 字符）")',
)
PATH_FRAGMENTS = (
    'legacy = workspace / ".boss-cli" / "skills"',
    'preferred = workspace / ".boss-harness" / "skills"',
    "return legacy if legacy.is_dir() and not preferred.is_dir() else preferred",
    "return path.relative_to(workspace).as_posix()",
    "except ValueError:\n        return path.name",
)
CHECKPOINT_FRAGMENTS = (
    "candidate = (turn_id if isinstance(turn_id, str)",
    'and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", turn_id) else "")',
    "if candidate in values or len(values) < 2:",
    "values.add(candidate)",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _expect_value(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}：期望 {expected!r}，实际 {actual!r}")


def _expect_error(call, message: str, label: str) -> None:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(f"{label}：文案 {str(error)!r} != {message!r}") from None
        return
    raise ValueError(f"{label}：未抛出 ValueError")


def _behavior_checks() -> int:
    checked = 0
    default = DEFAULT_APPROVAL_TIMEOUT_SECONDS
    # 审批期限：未设置 / 空白视为有效默认，非有限、非正与无法解析回退默认且标记无效。
    for environ, expected in (
        ({}, (default, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": ""}, (default, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "   "}, (default, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "30"}, (30.0, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "0.5"}, (0.5, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "1e3"}, (1000.0, True)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "0"}, (default, False)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "-1"}, (default, False)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "nan"}, (default, False)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "inf"}, (default, False)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "abc"}, (default, False)),
        # Unicode 16.0 新增数字（如 U+10D44）在 3.14 的 float 上可解析；只接受 ASCII 文法。
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "\U00010D44"}, (default, False)),
        ({"BOSS_HARNESS_APPROVAL_TIMEOUT": "４"}, (default, False)),
    ):
        _expect_value(approval_timeout_from_environment(environ), expected, f"审批期限 {environ!r}")
        checked += 1
    # 清扫等待：无截止时间 5 秒，过去截止时间 0.05 秒，连续失败按 2 的幂退避并封顶 60 秒。
    for deadline, failures, expected in (
        (None, {}, 5.0),
        (time.time() + 100, {}, 5.0),
        (time.time() - 100, {}, 0.05),
        (None, {"a": 1}, 5.0),
        (None, {"a": 2}, 5.0),
        (None, {"a": 3}, 5.0),
        (None, {"a": 4}, 8.0),
        (None, {"a": 5}, 16.0),
        (None, {"a": 10}, 60.0),
        (None, {"a": 1, "b": 3}, 5.0),
        (time.time() - 100, {"a": 1}, 1.0),
        (None, {"a": 0}, 5.0),
    ):
        _expect_value(_approval_expiry_delay(deadline, failures), expected, f"清扫等待 {deadline!r} {failures!r}")
        checked += 1
    # steering 模式：只接受两个精确值，非法值不回显原始输入。
    _expect_value(_steering_mode_value("all"), "all", "steering all")
    checked += 1
    _expect_value(_steering_mode_value("one-at-a-time"), "one-at-a-time", "steering one")
    checked += 1
    for value in ("ALL", "", None, 1, True):
        _expect_error(
            lambda value=value: _steering_mode_value(value),
            "steering_mode 必须是 all 或 one-at-a-time",
            f"steering 非法 {value!r}",
        )
        checked += 1
    original = os.environ.pop("BOSS_HARNESS_STEERING_MODE", None)
    try:
        _expect_value(steering_mode_from_environment(), "all", "环境未设置")
        checked += 1
        os.environ["BOSS_HARNESS_STEERING_MODE"] = ""
        _expect_value(steering_mode_from_environment(), "all", "环境为空")
        checked += 1
        os.environ["BOSS_HARNESS_STEERING_MODE"] = "one-at-a-time"
        _expect_value(steering_mode_from_environment(), "one-at-a-time", "环境指定")
        checked += 1
        for raw in ("two", " all "):
            os.environ["BOSS_HARNESS_STEERING_MODE"] = raw
            _expect_error(
                steering_mode_from_environment,
                "BOSS_HARNESS_STEERING_MODE 必须是 all 或 one-at-a-time",
                f"环境非法 {raw!r}",
            )
            checked += 1
    finally:
        os.environ.pop("BOSS_HARNESS_STEERING_MODE", None)
        if original is not None:
            os.environ["BOSS_HARNESS_STEERING_MODE"] = original
    # 分支视图：缺省 log；只接受 log / branch，其他键不影响。
    for params, expected in (
        (None, False),
        ({}, False),
        ({"view": "log"}, False),
        ({"view": "branch"}, True),
        ({"view": "branch", "x": 1}, True),
    ):
        _expect_value(_branch_view(params), expected, f"分支视图 {params!r}")
        checked += 1
    for value in ("x", 1, None):
        _expect_error(
            lambda value=value: _branch_view({"view": value}),
            "view 必须是 log 或 branch",
            f"分支视图非法 {value!r}",
        )
        checked += 1
    # 非空文本：保留首尾空白，上限按字符数且含等号，错误文案带键与上限。
    _expect_value(_text({"name": "x"}, "name"), "x", "文本正常")
    checked += 1
    _expect_value(_text({"name": " x "}, "name"), " x ", "文本不裁剪")
    checked += 1
    _expect_value(_text({"name": "x" * 10}, "name", maximum=10), "x" * 10, "文本上限含等号")
    checked += 1
    for params, label in (
        (None, "文本缺参数"),
        ({}, "文本缺键"),
        ({"name": ""}, "文本空串"),
        ({"name": "  "}, "文本空白"),
        ({"name": 1}, "文本非字符串"),
        ({"name": "x" * 11}, "文本超限"),
    ):
        _expect_error(
            lambda params=params: _text(params, "name", maximum=10),
            "name 必须是非空字符串（最多 10 字符）",
            label,
        )
        checked += 1
    # 工作区相对路径：内部用 POSIX 相对路径，外部只给目录名。
    workspace = Path("/tmp/ws")
    _expect_value(_relative_workspace_path(workspace / "a" / "b", workspace), "a/b", "工作区内")
    checked += 1
    _expect_value(_relative_workspace_path(workspace, workspace), ".", "工作区自身")
    checked += 1
    _expect_value(_relative_workspace_path(Path("/tmp/other/file.txt"), workspace), "file.txt", "工作区外")
    checked += 1
    _expect_value(_relative_workspace_path(Path("a/b"), Path("a")), "b", "相对路径")
    checked += 1
    # 技能目录：新目录优先，仅旧目录存在时回退；文件占位不算目录。
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        legacy = root / ".boss-cli" / "skills"
        preferred = root / ".boss-harness" / "skills"
        _expect_value(_skill_catalog_root(root), preferred, "都不存在用新目录")
        checked += 1
        legacy.parent.mkdir(parents=True)
        legacy.write_text("x", encoding="utf-8")
        _expect_value(_skill_catalog_root(root), preferred, "旧路径仅文件不回退")
        checked += 1
        legacy.unlink()
        legacy.mkdir(parents=True)
        _expect_value(_skill_catalog_root(root), legacy, "仅旧目录回退")
        checked += 1
        preferred.mkdir(parents=True)
        _expect_value(_skill_catalog_root(root), preferred, "两者都存在用新目录")
        checked += 1
        legacy.rmdir()
        _expect_value(_skill_catalog_root(root), preferred, "仅新目录")
        checked += 1
        legacy.write_text("x", encoding="utf-8")
        _expect_value(_skill_catalog_root(root), preferred, "旧路径是文件")
        checked += 1
        legacy.unlink()
        preferred.rmdir()
        preferred.write_text("x", encoding="utf-8")
        legacy.mkdir()
        _expect_value(_skill_catalog_root(root), legacy, "新路径是文件时回退")
        checked += 1
    # 检查点归属：每个任务最多两个不同回合，重复不占位，非法 id 归为空串。
    turns: dict[str, set[str]] = {}
    _record_checkpoint_turn(turns, "j", "t1")
    _expect_value(turns, {"j": {"t1"}}, "记录首个")
    checked += 1
    _record_checkpoint_turn(turns, "j", "t1")
    _expect_value(turns, {"j": {"t1"}}, "重复不增")
    checked += 1
    _record_checkpoint_turn(turns, "j", "t2")
    _expect_value(turns, {"j": {"t1", "t2"}}, "记录第二个")
    checked += 1
    _record_checkpoint_turn(turns, "j", "t3")
    _expect_value(turns, {"j": {"t1", "t2"}}, "第三个丢弃")
    checked += 1
    _record_checkpoint_turn(turns, "j", "bad id")
    _expect_value(turns, {"j": {"t1", "t2"}}, "满额后非法丢弃")
    checked += 1
    _record_checkpoint_turn(turns, "k", "a" * 128)
    _expect_value(turns["k"], {"a" * 128}, "128 字符接受")
    checked += 1
    _record_checkpoint_turn(turns, "l", "a" * 129)
    _expect_value(turns["l"], {""}, "129 字符归空")
    checked += 1
    _record_checkpoint_turn(turns, "m", "bad id")
    _expect_value(turns["m"], {""}, "非法归空")
    checked += 1
    return checked


def check_application_helpers() -> int:
    module = _read(MODULE)
    checked = 0
    for fragments in (ENVIRONMENT_FRAGMENTS, DELAY_FRAGMENTS, INPUT_FRAGMENTS,
                      PATH_FRAGMENTS, CHECKPOINT_FRAGMENTS):
        checked += _expect(fragments, module, MODULE)
    checked += _behavior_checks()
    return checked + 1


def main() -> int:
    try:
        checked = check_application_helpers()
    except ValueError as error:
        print(f"应用输入边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"应用输入边界一致：{checked} 项环境默认、输入与路径防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
