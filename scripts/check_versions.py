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
STATUS_RELEASE_TAG = re.compile(r"releases/tag/v(\d+\.\d+\.\d+-rc\.\d+)")
CHANGELOG_LINK = re.compile(
    r"https://github\.com/can4hou6joeng4/boss-harness/(?:issues|pull)/[0-9]+")


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


def _published_version() -> str:
    path = "docs/STATUS.md"
    text = _read(path, lambda value: value)
    match = STATUS_RELEASE_TAG.search(text)
    if match is None:
        raise ValueError(f"{path} 缺少最近实际预发布的 tag 链接")
    return match.group(1)


def _entry_bodies(text: str) -> list[tuple[str, str]]:
    parts = CHANGELOG_HEADING.split(text)
    return [(parts[index], parts[index + 2]) for index in range(1, len(parts) - 1, 3)]


def _check_candidate_links(text: str, published: str) -> None:
    boundary = _candidate_key(published)
    missing = [
        version
        for version, body in _entry_bodies(text)
        if _candidate_key(version) > boundary and not CHANGELOG_LINK.search(body)
    ]
    if missing:
        raise ValueError(
            "CHANGELOG.md 的候选条目缺少 Issue 或 PR 链接：" + "、".join(missing))


def _check_changelog(npm_version: str) -> None:
    path = "CHANGELOG.md"
    text = _read(path, lambda value: value)
    entries = CHANGELOG_HEADING.findall(text)
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
    _check_candidate_links(text, _published_version())


def _manifest_paths(root: dict) -> list[str]:
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
    return manifests


def _check_metadata(root: dict, manifests: list[str]) -> None:
    repository = root.get("repository")
    bugs = root.get("bugs")
    engines = root.get("engines")
    expected_url = "https://github.com/can4hou6joeng4/boss-harness.git"
    if root.get("private") is not True:
        raise ValueError("根 package.json 必须保持 private")
    if not isinstance(root.get("description"), str) or not root["description"].strip():
        raise ValueError("根 package.json 缺少非空 description")
    if (not isinstance(repository, dict) or repository.get("type") != "git"
            or repository.get("url") != expected_url):
        raise ValueError("根 package.json 的 repository 必须是项目 Git 地址")
    if root.get("homepage") != "https://github.com/can4hou6joeng4/boss-harness#readme":
        raise ValueError("根 package.json 的 homepage 必须指向项目 README")
    if not isinstance(bugs, dict) or bugs.get("url") != "https://github.com/can4hou6joeng4/boss-harness/issues":
        raise ValueError("根 package.json 的 bugs.url 必须指向项目 issues")
    if not isinstance(engines, dict) or engines.get("node") != ">=24":
        raise ValueError("根 package.json 的 engines.node 必须为 >=24")
    for relative in manifests[1:]:
        manifest = _read(relative, json.loads)
        if not isinstance(manifest, dict):
            raise ValueError(f"{relative} 必须是 JSON 对象")
        if manifest.get("private") is not True:
            raise ValueError(f"{relative} 必须保持 private")
        if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
            raise ValueError(f"{relative} 缺少非空 description")

    config = _read("harness/pyproject.toml", tomllib.loads)
    project = config.get("project") if isinstance(config, dict) else None
    if not isinstance(project, dict):
        raise ValueError("harness/pyproject.toml 缺少 project")
    if project.get("readme") != "README.md":
        raise ValueError("harness/pyproject.toml 的 readme 必须是 README.md")
    if project.get("requires-python") != ">=3.10":
        raise ValueError("harness/pyproject.toml 的 requires-python 必须是 >=3.10")
    # classifiers 是 PyPI 页面展示的支持版本，必须与 CI 实际运行的矩阵一致。
    classifiers = project.get("classifiers")
    if not isinstance(classifiers, list):
        raise ValueError("harness/pyproject.toml 的 classifiers 必须是列表")
    declared = {value.rsplit(" :: ", 1)[-1] for value in classifiers
                if isinstance(value, str) and value.startswith("Programming Language :: Python :: 3.")}
    workflow = _read(".github/workflows/build.yml", lambda value: value)
    matrix = re.search(r"python-version: \[([^\]]+)\]", workflow)
    if matrix is None:
        raise ValueError(".github/workflows/build.yml 缺少 Python 版本矩阵")
    expected = set(re.findall(r"'([0-9]+\.[0-9]+)'", matrix.group(1)))
    if not expected or declared != expected:
        raise ValueError(
            "harness/pyproject.toml 的 Python classifiers 必须与 CI 矩阵一致："
            f"classifiers {sorted(declared)}，矩阵 {sorted(expected)}")
    keywords = project.get("keywords")
    if (not isinstance(keywords, list) or not keywords
            or any(not isinstance(value, str) or not value.strip() for value in keywords)):
        raise ValueError("harness/pyproject.toml 的 keywords 必须是非空字符串列表")
    urls = project.get("urls")
    expected_urls = {
        "Homepage": "https://github.com/can4hou6joeng4/boss-harness",
        "Repository": "https://github.com/can4hou6joeng4/boss-harness",
        "Issues": "https://github.com/can4hou6joeng4/boss-harness/issues",
        "Changelog": "https://github.com/can4hou6joeng4/boss-harness/blob/main/CHANGELOG.md",
    }
    if not isinstance(urls, dict) or any(urls.get(key) != value for key, value in expected_urls.items()):
        raise ValueError("harness/pyproject.toml 的 project.urls 必须指向项目主页 / 仓库 / issues / 变更记录")
    scripts = project.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("boss-harness") != "boss_harness.__main__:main":
        raise ValueError("harness/pyproject.toml 的 boss-harness 入口必须是 boss_harness.__main__:main")
    build = config.get("build-system") if isinstance(config, dict) else None
    if not isinstance(build, dict) or "hatchling>=1.27" not in build.get("requires", []):
        raise ValueError("harness/pyproject.toml 的构建依赖必须包含 hatchling>=1.27")
    if build.get("build-backend") != "hatchling.build":
        raise ValueError("harness/pyproject.toml 的 build-backend 必须是 hatchling.build")
    tool = config.get("tool") if isinstance(config, dict) else None
    hatch = tool.get("hatch") if isinstance(tool, dict) else None
    build = hatch.get("build") if isinstance(hatch, dict) else None
    targets = build.get("targets") if isinstance(build, dict) else None
    wheel = targets.get("wheel") if isinstance(targets, dict) else None
    if not isinstance(wheel, dict) or wheel.get("packages") != ["src/boss_harness"]:
        raise ValueError("harness/pyproject.toml 的 wheel 包路径必须是 src/boss_harness")


def _check_license(root: dict) -> None:
    manifests = _manifest_paths(root)
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
    _check_metadata(root, _manifest_paths(root))

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
