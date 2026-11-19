#!/usr/bin/env python3
"""核对自动压缩设置的有界读取、原子写入与持久边界。

settings.py 决定 config.json 的读取与保存：不可读的配置必须按默认值处理，
保存必须保留无关键、拒绝覆盖损坏文件，并以临时文件 + fsync + 目录同步完成
原子替换。这些边界被删改不会触发构建失败，因此用静态检查固定。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "harness/src/boss_harness/settings.py"
TECHNICAL_REFERENCE = "docs/TECHNICAL_REFERENCE.md"
USER_GUIDE = "docs/USER_GUIDE.md"

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
    except ValueError as error:
        print(f"设置持久化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"设置持久化一致：{checked} 项读取、原子写入与持久防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
