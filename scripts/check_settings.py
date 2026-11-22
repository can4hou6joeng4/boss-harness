#!/usr/bin/env python3
"""核对自动压缩设置的有界读取、原子写入与持久边界。

settings.py 决定 config.json 的读取与保存：不可读的配置必须按默认值处理，
保存必须保留无关键、拒绝覆盖损坏文件，并以临时文件 + fsync + 目录同步完成
原子替换。检查固定源码结构，并用临时状态目录执行读取、拒绝与保存场景。
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/settings.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.settings import (  # noqa: E402
    CONFIG_FILE,
    _MAX_CONFIG_BYTES,
    _read_object,
    _within_depth,
    load_auto_compaction,
    save_auto_compaction,
)

CONSTANT_FRAGMENTS = (
    'CONFIG_FILE = "config.json"\n',
    'AUTO_COMPACTION_FIELDS = ("enabled", "triggerPercent", "keepRecentTokens")\n',
    "_MAX_CONFIG_BYTES = 256 * 1024\n",
    "_MAX_CONFIG_DEPTH = 64\n",
)
DEPTH_FRAGMENTS = (
    "stack = [(value, 0)]",
    "if depth >= limit:",
    "return False",
    "stack.extend((child, depth + 1) for child in current.values())",
    "stack.extend((child, depth + 1) for child in current)",
)
READ_FRAGMENTS = (
    # 只经私有文件描述符读取：避免按路径二次解析与符号链接。
    "descriptor = open_private_file(path, os.O_RDONLY)",
    "except FileNotFoundError:",
    "if not stat.S_ISREG(os.fstat(descriptor).st_mode):",
    # 只读到上限 + 1 字节；多出的一字节说明超限，不解码半截内容。
    "remaining = _MAX_CONFIG_BYTES + 1",
    "chunk = handle.read(min(remaining, 64 * 1024))",
    "remaining -= len(chunk)",
    "if remaining == 0:",
    'value = json.loads(raw.decode("utf-8"))',
    "except (OSError, UnicodeError, ValueError, RecursionError):",
    "os.close(descriptor)",
    "return value if isinstance(value, dict) and _within_depth(value) else None",
)
FSYNC_FRAGMENTS = (
    'descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))',
    "os.fsync(descriptor)",
    "os.close(descriptor)",
)
SAVE_FRAGMENTS = (
    "verified = verified_policy(fields, AUTO_COMPACTION_FIELDS)",
    "if verified is None or set(verified) != set(AUTO_COMPACTION_FIELDS):",
    'raise ValueError("自动压缩设置必须包含 enabled、triggerPercent、keepRecentTokens")',
    # 已存在但不可读的配置不能被覆盖：那会抹掉未知设置。
    "if path.exists():",
    "if current is None:",
    'raise ValueError("内核配置文件不可读或格式无效，未写入自动压缩设置")',
    'payload = json.dumps({**current, "autoCompaction": verified}, ensure_ascii=False, indent=2) + "\\n"',
    "except (TypeError, ValueError, RecursionError, UnicodeEncodeError):",
    'raise ValueError("内核配置文件包含无法保存的内容，未写入自动压缩设置") from None',
    "if len(encoded) > _MAX_CONFIG_BYTES:",
    'raise ValueError("内核配置文件超过大小上限，未写入自动压缩设置")',
    "state_dir.mkdir(parents=True, exist_ok=True)",
    'descriptor, temporary = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=state_dir)',
    "os.fsync(handle.fileno())",
    "os.replace(temporary, path)",
    "_fsync_directory(state_dir)",
    "os.unlink(temporary)",
    "except OSError:",
)
LOAD_FRAGMENTS = (
    "stored = _read_object(state_dir / CONFIG_FILE)",
    'return verified_policy((stored or {}).get("autoCompaction"), AUTO_COMPACTION_FIELDS)',
)
DOC_FRAGMENTS = (
    (TECHNICAL_REFERENCE, "拒绝未知字段、重复键和无效类型，错误不显示原配置"),
    (USER_GUIDE, "不读取 `config.json` 中的持久自动压缩设置"),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    # 取每个片段的首次出现位置：允许跳过的子序列会漏掉提前插入的重复片段。
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"设置持久化行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        return _expect_value(str(error), message, label)
    raise ValueError(f"设置持久化应拒绝 {label}")


def _nested(levels: int) -> dict:
    value: object = 1
    for _ in range(levels):
        value = {"next": value}
    return value


def _fields(**overrides) -> dict:
    fields = {"enabled": True, "triggerPercent": 70, "keepRecentTokens": 1_200}
    fields.update(overrides)
    return fields


def _behavior_checks() -> int:
    checked = _expect_value(_within_depth(_nested(64)), True, "深度 64 接受")
    checked += _expect_value(_within_depth(_nested(65)), False, "深度 65 拒绝")
    nested_list: object = 1
    for _ in range(65):
        nested_list = [nested_list]
    checked += _expect_value(_within_depth(nested_list), False, "列表深度 65 拒绝")

    with TemporaryDirectory() as directory:
        root = Path(directory)
        checked += _expect_value(_read_object(root / CONFIG_FILE), None, "缺失配置")
        valid = root / "valid"
        valid.mkdir()
        (valid / CONFIG_FILE).write_text('{"theme":"dark","enabled":true}', encoding="utf-8")
        checked += _expect_value(
            _read_object(valid / CONFIG_FILE), {"theme": "dark", "enabled": True}, "有效对象"
        )
        array = root / "array"
        array.mkdir()
        (array / CONFIG_FILE).write_text("[1, 2]", encoding="utf-8")
        checked += _expect_value(_read_object(array / CONFIG_FILE), None, "非对象顶层")
        corrupt = root / "corrupt"
        corrupt.mkdir()
        (corrupt / CONFIG_FILE).write_bytes(b"{")
        checked += _expect_value(_read_object(corrupt / CONFIG_FILE), None, "损坏配置")
        invalid_utf8 = root / "invalid"
        invalid_utf8.mkdir()
        (invalid_utf8 / CONFIG_FILE).write_bytes(b'{"k":"\xff"}')
        checked += _expect_value(_read_object(invalid_utf8 / CONFIG_FILE), None, "非法 UTF-8")
        oversize = root / "oversize"
        oversize.mkdir()
        (oversize / CONFIG_FILE).write_bytes(b'{"k":"' + b"x" * _MAX_CONFIG_BYTES + b'"}')
        checked += _expect_value(_read_object(oversize / CONFIG_FILE), None, "超限配置")
        deep = root / "deep"
        deep.mkdir()
        (deep / CONFIG_FILE).write_text(json.dumps(_nested(65)), encoding="utf-8")
        checked += _expect_value(_read_object(deep / CONFIG_FILE), None, "深层配置")

        checked += _expect_value(load_auto_compaction(root / "missing"), None, "缺失加载")
        loaded = root / "loaded"
        loaded.mkdir()
        (loaded / CONFIG_FILE).write_text(json.dumps({"autoCompaction": _fields()}), encoding="utf-8")
        checked += _expect_value(load_auto_compaction(loaded), _fields(), "合法加载")
        unknown = root / "unknown"
        unknown.mkdir()
        (unknown / CONFIG_FILE).write_text(
            json.dumps({"autoCompaction": {**_fields(), "extra": 1}}), encoding="utf-8"
        )
        checked += _expect_value(load_auto_compaction(unknown), None, "未知字段加载")
        invalid_value = root / "invalid-value"
        invalid_value.mkdir()
        (invalid_value / CONFIG_FILE).write_text(
            json.dumps({"autoCompaction": _fields(triggerPercent=0)}), encoding="utf-8"
        )
        checked += _expect_value(load_auto_compaction(invalid_value), None, "非法值加载")
        partial = root / "partial"
        partial.mkdir()
        (partial / CONFIG_FILE).write_text(
            json.dumps({"autoCompaction": {"enabled": True}}), encoding="utf-8"
        )
        checked += _expect_value(load_auto_compaction(partial), {"enabled": True}, "部分字段加载")
        empty = root / "empty"
        empty.mkdir()
        (empty / CONFIG_FILE).write_text('{"autoCompaction":{}}', encoding="utf-8")
        checked += _expect_value(load_auto_compaction(empty), None, "空对象加载")

        saved = root / "saved"
        save_auto_compaction(saved, _fields())
        checked += _expect_value(load_auto_compaction(saved), _fields(), "保存后加载")
        checked += _expect_value(
            (saved / CONFIG_FILE).read_text(encoding="utf-8").endswith("\n"), True, "保存换行结尾"
        )
        checked += _expect_value(
            sorted(path.name for path in saved.iterdir()), [CONFIG_FILE], "成功无临时残留"
        )

        preserved = root / "preserved"
        preserved.mkdir()
        (preserved / CONFIG_FILE).write_text(
            json.dumps({"theme": "dark", "autoCompaction": _fields(enabled=False)}), encoding="utf-8"
        )
        save_auto_compaction(preserved, _fields())
        stored = json.loads((preserved / CONFIG_FILE).read_text(encoding="utf-8"))
        checked += _expect_value(
            (stored["theme"], stored["autoCompaction"]), ("dark", _fields()), "保留无关键"
        )

        rejected = root / "rejected"
        message = "自动压缩设置必须包含 enabled、triggerPercent、keepRecentTokens"
        checked += _expect_error(
            lambda: save_auto_compaction(rejected, {"enabled": True}), message, "缺少字段"
        )
        checked += _expect_value(rejected.exists(), False, "缺少字段未建目录")
        checked += _expect_error(
            lambda: save_auto_compaction(rejected, {**_fields(), "extra": 1}), message, "未知字段"
        )
        checked += _expect_error(
            lambda: save_auto_compaction(rejected, _fields(triggerPercent=101)), message, "非法值"
        )

        damaged = root / "damaged"
        damaged.mkdir()
        (damaged / CONFIG_FILE).write_bytes(b"{")
        checked += _expect_error(
            lambda: save_auto_compaction(damaged, _fields()),
            "内核配置文件不可读或格式无效，未写入自动压缩设置", "损坏配置保存",
        )
        checked += _expect_value((damaged / CONFIG_FILE).read_bytes(), b"{", "损坏配置保持不变")
        checked += _expect_value(
            sorted(path.name for path in damaged.iterdir()), [CONFIG_FILE], "损坏拒绝无临时残留"
        )

        surrogate = root / "surrogate"
        surrogate.mkdir()
        (surrogate / CONFIG_FILE).write_bytes(b'{"blob":"\\ud800"}')
        checked += _expect_error(
            lambda: save_auto_compaction(surrogate, _fields()),
            "内核配置文件包含无法保存的内容，未写入自动压缩设置", "不可编码保存",
        )
        checked += _expect_value(
            (surrogate / CONFIG_FILE).read_bytes(), b'{"blob":"\\ud800"}', "不可编码配置保持不变"
        )

        large = root / "large"
        large.mkdir()
        (large / CONFIG_FILE).write_text(
            json.dumps({"blob": "x" * (_MAX_CONFIG_BYTES - 64)}), encoding="utf-8"
        )
        checked += _expect_error(
            lambda: save_auto_compaction(large, _fields()),
            "内核配置文件超过大小上限，未写入自动压缩设置", "合并超限保存",
        )
        checked += _expect_value(
            sorted(path.name for path in large.iterdir()), [CONFIG_FILE], "超限拒绝无临时残留"
        )

        nested_state = root / "nested" / "state"
        save_auto_compaction(nested_state, _fields())
        checked += _expect_value(load_auto_compaction(nested_state), _fields(), "新建状态目录")
    return checked


def check_settings() -> int:
    module = _read(MODULE)
    checked = _expect(CONSTANT_FRAGMENTS, module, MODULE)
    checked += _expect(DEPTH_FRAGMENTS, module, MODULE)
    checked += _expect(READ_FRAGMENTS, module, MODULE)
    checked += _expect(FSYNC_FRAGMENTS, module, MODULE)
    checked += _expect(SAVE_FRAGMENTS, module, MODULE)
    checked += _expect(LOAD_FRAGMENTS, module, MODULE)
    # 先落盘文件内容，再原子替换，最后同步目录项；顺序变化会失去持久保证。
    checked += _ordered(
        (
            "os.fsync(handle.fileno())",
            "os.replace(temporary, path)",
            "_fsync_directory(state_dir)",
        ),
        module,
        MODULE,
    )
    # 配置读取必须基于已打开的描述符；按路径读取会在两次解析之间被替换。
    if "read_text(" in module:
        raise ValueError(f"{MODULE} 必须基于描述符读取配置")
    # 保存必须走临时文件 + fsync；直接写目标路径会暴露半截文件。
    if "write_text(" in module:
        raise ValueError(f"{MODULE} 必须经临时文件原子写入")
    for relative, fragment in DOC_FRAGMENTS:
        checked += _expect((fragment,), _read(relative), relative)
    return checked + 1


def main() -> int:
    try:
        checked = check_settings()
        scenarios = _behavior_checks()
    except (ValueError, OSError) as error:
        print(f"设置持久化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"设置持久化一致：{checked} 项读取、原子写入与持久防护、{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
