#!/usr/bin/env python3
"""为 Python 内核发布资产生成 build-info.json 与 SHA256SUMS.txt。

只读取命令行显式列出的普通文件；拒绝符号链接、目录、重复文件名与保留输出名。
摘要按块流式计算，清单按文件名排序，两个输出文件都先写临时文件再原子替换。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CHUNK_BYTES = 1024 * 1024
VERSION_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)+(?:(?:a|b|rc)[0-9]+)?\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}\Z")
BUILT_AT_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
CONTROL_PATTERN = re.compile(r"[\u0000-\u001f\u007f]")
BUILD_INFO_NAME = "build-info.json"
SUMS_NAME = "SHA256SUMS.txt"
RESERVED_NAMES = {BUILD_INFO_NAME, SUMS_NAME}


def fail(message: str) -> None:
    print(f"release-assets: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_built_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not BUILT_AT_PATTERN.fullmatch(value):
        fail("--built-at 必须是 UTC 时间，形如 2026-11-16T04:30:00Z")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        fail("--built-at 不是有效日期时间")
    return value


def artifact_record(path: Path) -> dict[str, object]:
    name = path.name
    if not name:
        fail("资产路径缺少文件名")
    if name in RESERVED_NAMES:
        fail(f"资产文件名与输出文件冲突：{name}")
    if CONTROL_PATTERN.search(name):
        fail(f"资产文件名包含控制字符：{name!r}")
    if "\\" in name:
        fail(f"资产文件名不能包含反斜杠：{name!r}")

    try:
        observed = path.lstat()
    except OSError as exc:
        fail(f"无法读取 {name}：{exc.strerror or exc}")
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISREG(observed.st_mode):
        fail(f"{name} 必须是普通文件，不能是符号链接或目录")

    digest = hashlib.sha256()
    size = 0
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            observed.st_dev,
            observed.st_ino,
        ):
            fail(f"{name} 在读取期间被替换")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            while chunk := handle.read(CHUNK_BYTES):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        fail(f"无法读取 {name}：{exc.strerror or exc}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    return {"name": name, "bytes": size, "sha256": digest.hexdigest()}


def stage_outputs(out_dir: Path, contents: dict[str, str]) -> None:
    staged: list[tuple[str, Path]] = []
    try:
        for name, content in contents.items():
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{name}.", suffix=".tmp", dir=str(out_dir)
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o644)
            except BaseException:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
            staged.append((name, Path(temporary)))
        for name, temporary in staged:
            os.replace(temporary, out_dir / name)
    except BaseException:
        for _, temporary in staged:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="生成内核发布资产清单 build-info.json 与 SHA256SUMS.txt"
    )
    parser.add_argument("--version", required=True, help="Python 包版本，如 0.2.0rc56")
    parser.add_argument("--commit", required=True, help="40 位十六进制源码提交")
    parser.add_argument("--out-dir", required=True, help="已存在且用于写入清单的目录")
    parser.add_argument("--built-at", help="固定构建时间（UTC），用于复核")
    parser.add_argument("artifacts", nargs="+", help="参与清单的 wheel / sdist 等普通文件")
    args = parser.parse_args()

    if not VERSION_PATTERN.fullmatch(args.version):
        fail("--version 不是有效版本，如 0.2.0rc56")
    if not COMMIT_PATTERN.fullmatch(args.commit):
        fail("--commit 必须是 40 位十六进制提交")
    commit = args.commit.lower()
    built_at = parse_built_at(args.built_at)

    out_dir = Path(args.out_dir)
    try:
        out_stat = out_dir.lstat()
    except OSError as exc:
        fail(f"无法读取输出目录 {out_dir}：{exc.strerror or exc}")
    if stat.S_ISLNK(out_stat.st_mode) or not stat.S_ISDIR(out_stat.st_mode):
        fail(f"输出目录必须是已存在的目录，不能是符号链接：{out_dir}")

    records = [artifact_record(Path(value)) for value in args.artifacts]
    records.sort(key=lambda record: str(record["name"]))
    names = [str(record["name"]) for record in records]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        fail(f"资产文件名重复：{', '.join(duplicates)}")

    build_info = {
        "schemaVersion": 1,
        "name": "boss-harness",
        "version": args.version,
        "sourceCommit": commit,
        "builtAt": built_at,
        "pythonVersion": platform.python_version(),
        "artifacts": records,
    }
    sums = "".join(f"{record['sha256']}  {record['name']}\n" for record in records)
    contents = {
        BUILD_INFO_NAME: json.dumps(build_info, ensure_ascii=False, indent=2) + "\n",
        SUMS_NAME: sums,
    }

    try:
        stage_outputs(out_dir, contents)
    except OSError as exc:
        fail(f"无法写入输出目录 {out_dir}：{exc.strerror or exc}")

    print(f"已生成 {BUILD_INFO_NAME} 与 {SUMS_NAME}，共 {len(records)} 个资产")
    for record in records:
        print(f"{record['sha256']}  {record['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
