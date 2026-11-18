#!/usr/bin/env python3
"""核对源码包、变更记录与使用指南的版本，成功时向 stdout 输出 Python 版本。"""

from __future__ import annotations

import ast
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
NUMBER = r"(?:0|[1-9][0-9]*)"
NPM_VERSION = re.compile(rf"({NUMBER}\.{NUMBER}\.{NUMBER})(?:-rc\.({NUMBER}))?")
CHANGELOG_HEADING = re.compile(r"^## (\S+) - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)
CANDIDATE_VERSION = re.compile(rf"({NUMBER})\.({NUMBER})\.({NUMBER})-rc\.({NUMBER})")


def _read(relative: str, parse):
    try:
        return parse((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, ValueError, SyntaxError, RecursionError):
        raise ValueError(f"无法读取或解析 {relative}") from None


def _check_version(actual: object, expected: str, source: str) -> None:
    if actual != expected:
        raise ValueError(f"{source} 的版本不匹配，预期为 {expected}")


def _npm_versions() -> dict:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        result = subprocess.run(
            [npm, "pkg", "get", "version", "--workspaces", "--include-workspace-root", "--json"],
            cwd=ROOT, capture_output=True, check=True,
        )
        versions = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, ValueError):
        raise ValueError("无法从 npm 读取工作区版本，请核对 npm 和根包的 workspaces 配置") from None
    if not isinstance(versions, dict):
        raise ValueError("npm 未返回按包名组织的工作区版本")
    return versions


def _runtime_version() -> str:
    path = "harness/src/boss_harness/__init__.py"
    module = _read(path, ast.parse)
    assignments = []
    for node in module.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == "__version__" for target in targets):
            assignments.append(node.value)
    if len(assignments) == 1:
        value = assignments[0]
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    raise ValueError(f"{path} 必须包含唯一的顶层 __version__ 字符串声明")


def _check_guide(npm_version: str, python_version: str) -> None:
    path = "docs/USER_GUIDE.md"
    expected = f"npm `{npm_version}` / Python `{python_version}`"
    if expected not in _read(path, lambda text: text):
        raise ValueError(f"{path} 的源码版本行不是 {expected}")


def _candidate_key(version: str) -> tuple[int, ...]:
    match = CANDIDATE_VERSION.fullmatch(version)
    if match is None:
        raise ValueError(f"CHANGELOG.md 的版本条目 {version} 不是 MAJOR.MINOR.PATCH-rc.N 形式")
    return tuple(int(part) for part in match.groups())


def _check_changelog(npm_version: str) -> None:
    path = "CHANGELOG.md"
    entries = CHANGELOG_HEADING.findall(_read(path, lambda text: text))
    if not entries:
        raise ValueError(f"{path} 缺少版本条目")
    headings = [version for version, _ in entries]
    if headings[0] != npm_version:
        raise ValueError(f"{path} 的首条版本是 {headings[0]}，预期为 {npm_version}")
    keys = [_candidate_key(version) for version in headings]
    for index in range(1, len(keys)):
        if keys[index] >= keys[index - 1]:
            raise ValueError(
                f"{path} 的版本条目必须严格递减：{headings[index]} 位于 {headings[index - 1]} 之后"
            )
    dates: list[date] = []
    for version, value in entries:
        try:
            dates.append(date.fromisoformat(value))
        except ValueError:
            raise ValueError(f"{path} 的版本条目 {version} 日期不合法：{value}") from None
    for index in range(1, len(dates)):
        if dates[index] > dates[index - 1]:
            raise ValueError(
                f"{path} 的版本条目日期不得晚于上一条："
                f"{headings[index]} 的 {entries[index][1]} 位于 {entries[index - 1][1]} 之后"
            )


def _check_license(root: dict) -> None:
    manifests = ["package.json"]
    patterns = root.get("workspaces")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("package.json 缺少 workspaces")
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("package.json 的 workspaces 必须是字符串列表")
        manifests.extend(
            (path / "package.json").relative_to(ROOT).as_posix()
            for path in sorted(ROOT.glob(pattern))
            if (path / "package.json").is_file()
        )
    for relative in manifests:
        manifest = _read(relative, json.loads)
        license_value = manifest.get("license") if isinstance(manifest, dict) else None
        if license_value != "MIT":
            raise ValueError(f"{relative} 的 license 必须是 MIT")
    config = _read("harness/pyproject.toml", tomllib.loads)
    project = config.get("project") if isinstance(config, dict) else None
    if not isinstance(project, dict):
        raise ValueError("harness/pyproject.toml 缺少 project")
    if project.get("license") != "MIT":
        raise ValueError("harness/pyproject.toml 的 project.license 必须是 MIT")
    if project.get("license-files") != ["LICENSE"]:
        raise ValueError('harness/pyproject.toml 的 project.license-files 必须是 ["LICENSE"]')
    text = _read("LICENSE", lambda value: value)
    if not text.startswith("MIT License"):
        raise ValueError("LICENSE 必须以 MIT License 开头")
    if "Permission is hereby granted, free of charge" not in text:
        raise ValueError("LICENSE 缺少 MIT 许可正文")


def check_versions() -> str:
    root = _read("package.json", json.loads)
    root_name = root.get("name") if isinstance(root, dict) else None
    npm_version = root.get("version") if isinstance(root, dict) else None
    match = NPM_VERSION.fullmatch(npm_version) if isinstance(npm_version, str) else None
    if not isinstance(root_name, str) or not root_name.strip():
        raise ValueError("package.json 缺少根包名称")
    if match is None:
        raise ValueError("package.json 的版本须采用 MAJOR.MINOR.PATCH 或 MAJOR.MINOR.PATCH-rc.N")
    release, candidate = match.groups()
    python_version = release if candidate is None else f"{release}rc{candidate}"
    _check_license(root)

    lock = _read("package-lock.json", json.loads)
    packages = lock.get("packages") if isinstance(lock, dict) else None
    if not isinstance(packages, dict):
        raise ValueError("package-lock.json 缺少 packages 对象")
    _check_version(lock.get("version"), npm_version, "package-lock.json 根字段")
    root_entry = packages.get("")
    _check_version(root_entry.get("version") if isinstance(root_entry, dict) else None,
                   npm_version, 'package-lock.json 的 packages[""]')

    versions = _npm_versions()
    if versions.get(root_name) != npm_version or len(versions) < 2:
        raise ValueError("npm 未返回根包与工作区的有效版本列表")
    for name, version in versions.items():
        if name == root_name:
            continue
        _check_version(version, npm_version, f"工作区 {name} 的 package.json")
        link = packages.get(f"node_modules/{name}")
        target = link.get("resolved") if isinstance(link, dict) and link.get("link") is True else None
        if not isinstance(target, str) or not target:
            raise ValueError(f"package-lock.json 缺少工作区 {name} 的链接")
        entry = packages.get(target)
        _check_version(entry.get("version") if isinstance(entry, dict) else None,
                       npm_version, f"package-lock.json 中工作区 {name} 的记录")

    config = _read("harness/pyproject.toml", tomllib.loads)
    project = config.get("project")
    _check_version(project.get("version") if isinstance(project, dict) else None,
                   python_version, "harness/pyproject.toml 的 project.version")
    _check_version(_runtime_version(), python_version, "harness/src/boss_harness/__init__.py 的 __version__")
    _check_changelog(npm_version)
    _check_guide(npm_version, python_version)
    return python_version


def main() -> int:
    try:
        version = check_versions()
    except ValueError as error:
        print(f"源码版本核对失败，{error}", file=sys.stderr)
        return 2
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
