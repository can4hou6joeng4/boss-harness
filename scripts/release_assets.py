#!/usr/bin/env python3
"""为 Python 内核发布资产生成 build-info.json 与 SHA256SUMS.txt。

只读取命令行显式列出的普通文件；拒绝符号链接、目录、重复文件名与保留输出名。
核对输出目录归属和每个 wheel / sdist 内的包名与版本元数据，摘要按块流式计算；
清单按文件名排序，两个输出文件都先写临时文件再原子替换。
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
import tarfile
import tempfile
import tomllib
import zipfile
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path

try:
    from packaging.utils import canonicalize_name
    from packaging.version import InvalidVersion, Version
except ImportError:  # pragma: no cover - packaging 来自构建环境
    canonicalize_name = None  # type: ignore[assignment]
    InvalidVersion = None  # type: ignore[assignment]
    Version = None  # type: ignore[assignment]

CHUNK_BYTES = 1024 * 1024
COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}\Z")
BUILT_AT_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
CONTROL_PATTERN = re.compile(r"[\u0000-\u001f\u007f]")
BUILD_INFO_NAME = "build-info.json"
SUMS_NAME = "SHA256SUMS.txt"
RESERVED_NAMES = {BUILD_INFO_NAME, SUMS_NAME}
MANIFEST_SCHEMA_VERSION = 2


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


def _metadata_identity(data: bytes, name: str) -> tuple[str, str]:
    text = data.decode("utf-8")
    metadata = Parser().parsestr(text, headersonly=True)
    actual_name = metadata.get("Name")
    actual_version = metadata.get("Version")
    if not actual_name or not actual_name.strip():
        fail(f"{name} 缺少 Name 元数据")
    if not actual_version or not actual_version.strip():
        fail(f"{name} 缺少 Version 元数据")
    return actual_name.strip(), actual_version.strip()


def _verify_identity(actual_name: str, actual_version: str, name: str,
                     expected_name: str, expected_version: Version) -> None:
    try:
        normalized_name = canonicalize_name(actual_name, validate=True)
    except Exception as exc:
        fail(f"{name} 的包名无效：{actual_name!r}（{exc}）")
    if normalized_name != expected_name:
        fail(f"{name} 的包名 {actual_name} 与 {expected_name} 不一致")
    try:
        if Version(actual_version) != expected_version:
            fail(f"{name} 的版本 {actual_version} 与 --version {expected_version} 不一致")
    except InvalidVersion:
        fail(f"{name} 的版本元数据无效：{actual_version!r}")


def _project_version_from_pyproject(data: bytes, name: str) -> str:
    try:
        project = tomllib.loads(data.decode("utf-8")).get("project")
        if not isinstance(project, dict):
            fail(f"{name} 的 pyproject.toml 缺少 project 表")
        version = project.get("version")
        if not isinstance(version, str) or not version.strip():
            fail(f"{name} 的 pyproject.toml 缺少 project.version")
        return version.strip()
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        fail(f"无法解析 {name} 的 pyproject.toml：{exc}")


def verify_artifact_identity(handle, name: str, expected_name: str,
                             expected_version: Version) -> None:
    """核对与 SHA-256 同一文件描述符中的包名和版本元数据。"""
    try:
        if name.endswith(".whl"):
            with zipfile.ZipFile(handle) as archive:
                candidates = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
                if len(candidates) != 1:
                    fail(f"{name} 未包含唯一的 METADATA")
                actual_name, actual_version = _metadata_identity(archive.read(candidates[0]), name)
        elif name.endswith(".tar.gz"):
            with tarfile.open(fileobj=handle, mode="r:gz") as archive:
                candidates = [m for m in archive.getmembers()
                              if m.isfile() and m.name.endswith("/PKG-INFO")]
                if len(candidates) != 1:
                    fail(f"{name} 未包含唯一的 PKG-INFO")
                pkg_info = archive.extractfile(candidates[0])
                if pkg_info is None:
                    fail(f"{name} 无法读取 PKG-INFO")
                with pkg_info:
                    actual_name, actual_version = _metadata_identity(pkg_info.read(), name)
                pyprojects = [m for m in archive.getmembers()
                              if m.isfile() and m.name.split("/")[-1] == "pyproject.toml"]
                if len(pyprojects) != 1:
                    fail(f"{name} 未包含唯一的 pyproject.toml")
                pyproject = archive.extractfile(pyprojects[0])
                if pyproject is None:
                    fail(f"{name} 无法读取 pyproject.toml")
                with pyproject:
                    project_version = _project_version_from_pyproject(pyproject.read(), name)
        else:
            return
    except (OSError, UnicodeError, zipfile.BadZipFile, tarfile.TarError) as exc:
        fail(f"无法核对 {name} 的版本元数据：{exc}")
    _verify_identity(actual_name, actual_version, name, expected_name, expected_version)
    if name.endswith(".tar.gz"):
        try:
            if Version(project_version) != expected_version:
                fail(f"{name} 的 pyproject.toml 版本 {project_version} 与 --version {expected_version} 不一致")
        except InvalidVersion:
            fail(f"{name} 的 pyproject.toml 版本无效：{project_version!r}")


def artifact_record(path: Path, out_dir: Path, package_name: str,
                    version: Version) -> dict[str, object]:
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
        if path.parent.samefile(out_dir) is False:
            fail(f"{name} 不在输出目录内")
    except OSError as exc:
        fail(f"无法核对 {name} 的目录归属：{exc.strerror or exc}")

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
            handle.seek(0)
            verify_artifact_identity(handle, name, package_name, version)
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
    parser.add_argument("--version", required=True, help="Python 包版本，如 0.2.0rcN")
    parser.add_argument("--commit", required=True, help="40 位十六进制源码提交")
    parser.add_argument("--out-dir", required=True, help="已存在且用于写入清单的目录")
    parser.add_argument("--built-at", help="固定构建时间（UTC），用于复核")
    parser.add_argument("artifacts", nargs="+", help="参与清单的 wheel / sdist 等普通文件")
    args = parser.parse_args()

    if Version is None or InvalidVersion is None or canonicalize_name is None:
        fail("缺少 packaging 依赖；请在构建环境中安装 packaging")
    try:
        version = Version(args.version)
    except InvalidVersion:
        fail("--version 不是有效版本，如 0.2.0rcN")
    patch = tomllib.loads(Path("harness/pyproject.toml").read_text(encoding="utf-8")).get("project")
    project_name = patch.get("name") if isinstance(patch, dict) else None
    if not isinstance(project_name, str) or not project_name.strip():
        fail("harness/pyproject.toml 缺少 project.name")
    try:
        package_name = canonicalize_name(project_name.strip(), validate=True)
    except Exception as exc:
        fail(f"harness/pyproject.toml 的 project.name 无效：{project_name!r}（{exc}）")
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

    records = [artifact_record(Path(value), out_dir, str(package_name), version)
               for value in args.artifacts]
    records.sort(key=lambda record: str(record["name"]))
    names = [str(record["name"]) for record in records]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        fail(f"资产文件名重复：{', '.join(duplicates)}")

    build_info = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "name": project_name.strip(),
        "version": str(version),
        "sourceCommit": commit,
        "builtAt": built_at,
        "pythonVersion": platform.python_version(),
        "artifacts": records,
    }
    if (build_info["schemaVersion"] != MANIFEST_SCHEMA_VERSION
            or any(not isinstance(record.get("name"), str)
                   or not isinstance(record.get("bytes"), int)
                   or not isinstance(record.get("sha256"), str)
                   for record in records)):
        fail("构建清单契约校验失败")
    build_info_bytes = (json.dumps(build_info, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sums = "".join(f"{record['sha256']}  {record['name']}\n" for record in records)
    sums += f"{hashlib.sha256(build_info_bytes).hexdigest()}  {BUILD_INFO_NAME}\n"
    contents = {
        BUILD_INFO_NAME: build_info_bytes.decode("utf-8"),
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
