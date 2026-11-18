#!/usr/bin/env python3
"""核对发布资产清单的静态守卫与工作流接入，成功时输出核对项数量。"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/release_assets.py"
WORKFLOW = ".github/workflows/build.yml"
CONSTANTS = {
    "CHUNK_BYTES": 1024 * 1024,
    "MANIFEST_SCHEMA_VERSION": 2,
}
FRAGMENTS = (
    'BUILD_INFO_NAME = "build-info.json"',
    'SUMS_NAME = "SHA256SUMS.txt"',
    'RESERVED_NAMES = {BUILD_INFO_NAME, SUMS_NAME}',
    'COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}\\Z")',
    'BUILT_AT_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\\Z")',
    "parse_wheel_filename(",
    "parse_sdist_filename(",
    "canonicalize_name(actual_name, validate=True)",
    "if normalized_name != expected_name:",
    "if dist_info.casefold() != expected_dist_info.casefold():",
    "if len(roots) != 1:",
    "if root != name[:-len(\".tar.gz\")]:",
    'm.name == f"{root}/PKG-INFO"',
    'm.name == f"{root}/pyproject.toml"',
    "if Version(actual_version) != expected_version:",
    "if Version(project_version) != expected_version:",
    'if name.casefold() in {reserved.casefold() for reserved in RESERVED_NAMES}:',
    "if CONTROL_PATTERN.search(name):",
    'if "\\\\" in name:',
    "if path.parent.samefile(out_dir) is False:",
    "if stat.S_ISLNK(observed.st_mode) or not stat.S_ISREG(observed.st_mode):",
    'os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))',
    "(opened.st_dev, opened.st_ino) != (",
    "with os.fdopen(descriptor, \"rb\") as handle:",
    "while chunk := handle.read(CHUNK_BYTES):",
    "handle.seek(0)",
    "verify_artifact_identity(handle, name, package_name, version)",
    "names = [str(record[\"name\"]) for record in records]",
    "folded = [name.casefold() for name in names]",
    "if duplicates:",
    "required = {\"schemaVersion\", \"name\", \"version\", \"sourceCommit\", \"builtAt\",",
    "if type(build_info[\"schemaVersion\"]) is not int",
    "if not COMMIT_PATTERN.fullmatch(str(build_info[\"sourceCommit\"])):",
    're.fullmatch(r"[0-9a-f]{64}", record["sha256"])',
    "BUILD_INFO_NAME: build_info_bytes.decode(\"utf-8\")",
    "hashlib.sha256(build_info_bytes).hexdigest()",
    "stage_outputs(out_dir, contents)",
    "os.chmod(temporary, 0o644)",
    "os.replace(temporary, out_dir / name)",
)
WORKFLOW_FRAGMENTS = (
    "python scripts/release_assets.py \\",
    '--version "$SOURCE_VERSION" \\',
    '--commit "$GITHUB_SHA" \\',
    '--source-ref "$GITHUB_REF" \\',
    "--out-dir dist/python \\",
    "dist/python/*.whl dist/python/*.tar.gz",
    "sha256sum -c SHA256SUMS.txt",
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    values: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value
    return values


def _int_value(node: ast.expr, values: dict[str, ast.expr]) -> int:
    if isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _int_value(node.left, values) * _int_value(node.right, values)
    if isinstance(node, ast.Name) and node.id in values:
        return _int_value(values[node.id], values)
    raise ValueError("发布资产常量必须是正整数表达式")


def check_release_assets() -> tuple[int, int]:
    try:
        tree = ast.parse(_read(SCRIPT))
    except SyntaxError:
        raise ValueError(f"无法解析 {SCRIPT}") from None
    values = _assigned(tree)
    for name, expected in CONSTANTS.items():
        if name not in values:
            raise ValueError(f"{SCRIPT} 缺少 {name}")
        if _int_value(values[name], values) != expected:
            raise ValueError(f"{SCRIPT} 的 {name} 必须是 {expected}")
    source = _read(SCRIPT)
    missing = [fragment for fragment in FRAGMENTS if fragment not in source]
    if missing:
        raise ValueError("发布资产守卫缺少：" + "、".join(missing))
    workflow = _read(WORKFLOW)
    missing = [fragment for fragment in WORKFLOW_FRAGMENTS if fragment not in workflow]
    if missing:
        raise ValueError("CI 发布资产校验步骤缺少：" + "、".join(missing))
    return len(CONSTANTS), len(FRAGMENTS) + len(WORKFLOW_FRAGMENTS)


def main() -> int:
    try:
        constants, guards = check_release_assets()
    except ValueError as error:
        print(f"发布资产边界核对失败，{error}", file=sys.stderr)
        return 2
    print(f"发布资产边界一致：{constants} 个常量、{guards} 项清单与工作流防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
