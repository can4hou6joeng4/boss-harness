#!/usr/bin/env python3
"""核对会话导出的原子写入与失败诊断。

导出把脱敏后的会话写到用户选择的位置。覆盖保存不能在写入前截断目标，临时文件
必须与目标同目录、独占创建并默认 0600；写入、刷新、收紧权限、关闭之后要再次
核对目标身份，确认没有在保存期间被换成链接或其他文件，才允许原子替换。失败
提示只保留 errno，不回显系统路径。Node 24 行为检查用注入文件系统覆盖失败后的
句柄关闭、临时副本清理与原始错误保留。
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WRITE = "apps/desktop/src/main/sessionExportWrite.ts"
ERRORS = "apps/desktop/src/main/exportErrors.ts"
HARNESS = "apps/desktop/src/main/harness.ts"

WRITE_FRAGMENTS = (
    "const NO_FOLLOW = typeof constants.O_NOFOLLOW === \"number\" ? constants.O_NOFOLLOW : 0;",
    "constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | NO_FOLLOW, mode);",
    "return `.boss-harness-export-${randomUUID()}.tmp`;",
    "function targetChangedFailure(): never {",
    'throw new Error("targetChanged");',
    "if (before === null || after === null) return before === after;",
    "return before.dev === after.dev && before.ino === after.ino &&",
    "(before.ctimeMs === undefined || after.ctimeMs === undefined || before.ctimeMs === after.ctimeMs);",
    'if ((error as NodeJS.ErrnoException)?.code === "ENOENT") return null;',
    "const path = join(directory, name);",
    'if (error?.code === "ELOOP") throw new Error("symlink");',
    "export async function writeSessionExport(filePath: string, content: string,",
    "const existing = await ops.lstat(filePath);",
    'if (existing?.isSymbolicLink()) throw new Error("symlink");',
    "const temporary = await ops.createTemporary(dirname(filePath), sessionExportTemporaryName(), 0o600).catch(openFailure);",
    "let closed = false;",
    "let committed = false;",
    "permissionError = error;",
    "await temporary.handle.write(content);",
    "await temporary.handle.sync();",
    "await temporary.handle.chmod(0o600);",
    "await temporary.handle.close();\n    closed = true;",
    "if (!sameTarget(existing, await ops.lstat(filePath))) targetChangedFailure();",
    "await ops.rename(temporary.path, filePath);",
    "committed = true;",
    "if (!committed) {",
    "await ops.remove(temporary.path).catch(() => {});",
    "permissionsUnchanged: false",
    "if (!closed) {",
    "await temporary.handle.close().catch(() => {});",
)
ERROR_FRAGMENTS = (
    'if (typeof value?.code === "string" && value.code) return `无法写入所选文件（${value.code}），请换一个位置重试`;',
    'if (value?.message === "symlink") return "所选路径是符号链接，请换一个普通文件位置重试";',
    'if (value?.message === "targetChanged") return "所选文件在保存期间发生变化，请确认后重试";',
    'return "无法写入所选文件，请换一个位置重试";',
)
HARNESS_FRAGMENTS = (
    "defaultPath: join(app.getPath(\"downloads\"), sessionExportFileName(request)),",
    'properties: ["createDirectory", "showOverwriteConfirmation"],',
    "const written = await writeSessionExport(choice.filePath, exported.content).catch((error: unknown) => {",
    "const message = sessionExportWriteError(error);",
    'console.error("session export write failed", message);',
    "if (written.permissionError) {",
    'console.error("session export permission update failed", sessionExportWriteError(written.permissionError));',
    "return { saved: true, fileName: basename(choice.filePath), bytes: Buffer.byteLength(exported.content, \"utf8\"),",
)


DRIVER = """\
import { writeSessionExport, type SessionExportFileSystem } from "./writer.ts";

const target = { dev: 1, ino: 2, isFile: () => true, isSymbolicLink: () => false };
const scenarios: Array<[string, string?, boolean?]> = [
  ["success"], ["targetChanged"], ["lookupFailed", "recheck"],
  ["writeFailed", "write"], ["syncFailed", "sync"], ["closeFailed", "close"],
  ["renameFailed", "rename"], ["cleanupFailed", "write", true],
];
const results = [];
for (const [scenario, failAt, failCleanup] of scenarios) {
  const events: string[] = [];
  const failure = new Error("原始错误");
  let failed = false;
  let lookups = 0;
  function record(operation: string): void {
    events.push(operation);
    if (failAt === operation && !failed) {
      failed = true;
      throw failure;
    }
    if (failCleanup && (operation === "close" || operation === "remove")) {
      throw new Error("清理失败");
    }
  }
  const fs: SessionExportFileSystem = {
    async lstat() {
      lookups += 1;
      if (lookups === 1) return target;
      record("recheck");
      return scenario === "targetChanged" ? { ...target, ino: 3 } : target;
    },
    async createTemporary() {
      return {
        path: "/synthetic/export.tmp",
        handle: {
          async write() { record("write"); },
          async sync() { record("sync"); },
          async chmod() { record("chmod"); },
          async close() { record("close"); },
        },
      };
    },
    async rename() { record("rename"); },
    async remove() { record("remove"); },
  };
  let result = "saved";
  try {
    await writeSessionExport("/synthetic/session.md", "合成导出内容", fs);
  } catch (error) {
    result = error === failure ? "original" : (error as Error).message;
  }
  results.push([scenario, result, events]);
}
console.log(JSON.stringify(results));
"""


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def _check_behaviors() -> int:
    with tempfile.TemporaryDirectory(prefix="boss-export-write-") as folder:
        base = Path(folder)
        (base / "writer.ts").write_text(_read(WRITE), encoding="utf-8")
        (base / "driver.ts").write_text(DRIVER, encoding="utf-8")
        completed = subprocess.run(
            ["node", "driver.ts"], cwd=base, capture_output=True, text=True, timeout=30, check=False
        )
    if completed.returncode != 0:
        raise ValueError(f"导出写入行为检查失败：{completed.stderr.strip()}")
    try:
        actual = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("导出写入行为检查输出格式错误") from error
    expected = [
        ["success", "saved", ["write", "sync", "chmod", "close", "recheck", "rename"]],
        ["targetChanged", "targetChanged", ["write", "sync", "chmod", "close", "recheck", "remove"]],
        ["lookupFailed", "original", ["write", "sync", "chmod", "close", "recheck", "remove"]],
        ["writeFailed", "original", ["write", "close", "remove"]],
        ["syncFailed", "original", ["write", "sync", "close", "remove"]],
        ["closeFailed", "original", ["write", "sync", "chmod", "close", "close", "remove"]],
        ["renameFailed", "original", ["write", "sync", "chmod", "close", "recheck", "rename", "remove"]],
        ["cleanupFailed", "original", ["write", "close", "remove"]],
    ]
    if not isinstance(actual, list) or len(actual) != len(expected):
        raise ValueError("导出写入行为检查场景数量不符")
    for observed, wanted in zip(actual, expected):
        if observed != wanted:
            raise ValueError(f"导出写入行为不符 {wanted[0]}：期望 {wanted!r}，实际 {observed!r}")
    return len(expected)


def check_export_write() -> int:
    write = _read(WRITE)
    errors = _read(ERRORS)
    harness = _read(HARNESS)
    checked = 0
    checked += _expect(WRITE_FRAGMENTS, write, WRITE)
    checked += _expect(ERROR_FRAGMENTS, errors, ERRORS)
    checked += _expect(HARNESS_FRAGMENTS, harness, HARNESS)
    # 临时文件：写入、刷新、收紧权限、关闭、复核目标身份、原子替换。
    checked += _ordered(
        (
            "await temporary.handle.write(content);",
            "await temporary.handle.sync();",
            "await temporary.handle.chmod(0o600);",
            "await temporary.handle.close();\n    closed = true;",
            "if (!sameTarget(existing, await ops.lstat(filePath))) targetChangedFailure();",
            "await ops.rename(temporary.path, filePath);",
        ),
        write,
        WRITE,
    )
    # 清理路径独立于句柄关闭状态，只有完成替换才保留导出结果。
    checked += _ordered(
        (
            "await ops.rename(temporary.path, filePath);",
            "committed = true;",
            "} finally {",
            "if (!closed) {",
            "await temporary.handle.close().catch(() => {});",
            "if (!committed) {",
            "await ops.remove(temporary.path).catch(() => {});",
        ),
        write,
        WRITE,
    )
    # 反向断言：导出总是新 inode，不得声称沿用旧权限；响应不得回显完整路径。
    if "permissionsUnchanged: true" in write:
        raise ValueError(f"{WRITE} 的原子替换不得声称沿用旧权限")
    if "fileName: choice.filePath" in harness:
        raise ValueError(f"{HARNESS} 的导出回执不得回显完整路径")
    return checked + _check_behaviors() + 1


def main() -> int:
    try:
        checked = check_export_write()
    except ValueError as error:
        print(f"会话导出写入核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话导出写入一致：{checked} 项原子替换与诊断防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
