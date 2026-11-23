#!/usr/bin/env python3
"""核对资料库文件与工具来源的整理规则。

`libraryFiles.ts` 把会话消息里的文件变更与工具来源收敛成可渲染的列表：路径拆分
兼容斜杠、扩展名标签有界，同路径 / 同 ref 只保留首次来源并累计可用计数，来源按
有效时间倒序、坏时间按 ref 兜底，筛选统一做 NFKC、小写与裁剪。这里在临时目录
改写工具时间为确定性 stub 后用 Node 加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = "apps/desktop/src/renderer/src/data/libraryFiles.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

FRAGMENTS = (
    "export function splitLibraryPath(path: string): { directory: string; name: string } {",
    'const trimmed = typeof path === "string" ? path.trim() : "";',
    'if (!trimmed) return { directory: "", name: "" };',
    'const index = Math.max(trimmed.lastIndexOf("/"), trimmed.lastIndexOf("\\\\"));',
    "if (index < 0) return { directory: \"\", name: trimmed };",
    "return { directory: trimmed.slice(0, index), name: trimmed.slice(index + 1) };",
    "export function libraryFileKind(name: string): string {",
    'const value = typeof name === "string" ? name.trim() : "";',
    "if (dot <= 0 || dot === value.length - 1) return \"FILE\";",
    'if (!/^[A-Za-z0-9]{1,8}$/.test(extension)) return "FILE";',
    "return extension.toUpperCase();",
    "return Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0;",
    "export function collectLibraryFiles(messages: MessageItem[]): LibraryFile[] {",
    "const byPath = new Map<string, LibraryFile>();",
    "const path = typeof file.name === \"string\" ? file.name.trim() : \"\";",
    "if (!path) continue;",
    "existing.additions += finiteCount(file.additions);",
    "existing.deletions += finiteCount(file.deletions);",
    "existing.occurrences += 1;",
    "kind: libraryFileKind(name),",
    "messageId: message.id,",
    "turnId: message.turnId,",
    "return [...byPath.values()].sort((left, right) =>",
    "left.path < right.path ? -1 : left.path > right.path ? 1 : 0);",
    "export function collectLibrarySources(messages: MessageItem[]): LibrarySource[] {",
    "const byRef = new Map<string, LibrarySource>();",
    "const ref = typeof source.ref === \"string\" ? source.ref.trim() : \"\";",
    "if (!ref || byRef.has(ref)) continue;",
    'const tool = typeof source.tool === "string" && source.tool.trim() ? source.tool.trim() : "未知工具";',
    "queriedAt: typeof source.queriedAt === \"string\" ? source.queriedAt : \"\",",
    "const leftTime = toolQueriedAt(left.queriedAt)?.getTime();",
    "const rightTime = toolQueriedAt(right.queriedAt)?.getTime();",
    "if (leftValid && rightValid && leftTime !== rightTime) return rightTime - leftTime;",
    "if (leftValid !== rightValid) return leftValid ? -1 : 1;",
    "return left.ref < right.ref ? -1 : left.ref > right.ref ? 1 : 0;",
    "return (typeof value === \"string\" ? value : \"\").normalize(\"NFKC\").toLowerCase().trim();",
    "export function filterLibraryFiles(files: LibraryFile[], query: string): LibraryFile[] {",
    "return files.filter(file => normalizeQuery(file.path).includes(needle));",
    "export function filterLibrarySources(sources: LibrarySource[], query: string): LibrarySource[] {",
    "return sources.filter(source => normalizeQuery(`${source.ref} ${source.tool}`).includes(needle));",
    "export function formatSourceQueriedAt(value: string): string {",
    'if (!trimmed) return "查询时间未知";',
    "return toolQueriedAtLabel(trimmed) ?? trimmed;",
    "export function shortLibraryId(value: string): string {",
    "return trimmed.length > 12 ? `${trimmed.slice(0, 8)}…` : trimmed;",
)

STUB = r"""
export function toolQueriedAt(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) return null;
  const time = Date.parse(value);
  return Number.isNaN(time) ? null : new Date(time);
}
export function toolQueriedAtLabel(value) {
  const at = toolQueriedAt(value);
  return at ? `TIME ${at.toISOString()}` : null;
}
"""

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const {
  splitLibraryPath, libraryFileKind, collectLibraryFiles, collectLibrarySources,
  filterLibraryFiles, filterLibrarySources, formatSourceQueriedAt, shortLibraryId,
} = await import(pathToFileURL(process.argv[1]).href);
const pathView = value => splitLibraryPath(value);
const fileView = file => [
  file.path, file.name, file.directory, file.kind, file.messageId, file.turnId ?? "",
  file.additions, file.deletions, file.occurrences,
].join("|");
const sourceView = source => [
  source.ref, source.tool, source.queriedAt, source.messageId, source.turnId ?? "",
].join("|");
const message = (id, files = [], source) => ({
  id, turnId: `turn-${id}`,
  diffSummary: { initialFiles: files, extraFiles: [] },
  toolUse: source ? { source } : undefined,
});
const file = (name, additions = 1, deletions = 0) => ({ name, additions, deletions });
const source = (ref, tool = "search", queriedAt = "") => ({ ref, tool, queriedAt });
const sampleFiles = collectLibraryFiles([
  message("m1", [file("/a/Import.ts", 2, 1), file("b.md")]),
  message("m2", [file("/a/Import.ts", 3, 2)]),
]);
const sampleSources = collectLibrarySources([
  message("m1", [], source("r1", "search", "2026-01-02T03:04:05Z")),
  message("m2", [], source("r2", "fetch", "2026-01-03T00:00:00Z")),
  message("m3", [], source("r3", "search", "bad")),
]);
const result = {
  paths: [
    pathView("/a/b/File.ts"),
    pathView("\\a\\b\\File.ts"),
    pathView("/a/b\\File.ts"),
    pathView("File.ts"),
    pathView("  /a/b/File.ts  "),
    pathView(""),
    pathView(42),
    pathView("/"),
  ],
  kinds: [
    "a.ts", ".ts", "a.", "a.tar.gz", "a.123", "a.tsx-long", "a.ABC", "",
  ].map(libraryFileKind),
  files: [
    collectLibraryFiles([]).map(fileView),
    collectLibraryFiles([message("m1", [file("a.ts", 2, 1)])]).map(fileView),
    collectLibraryFiles([
      message("m1", [file("/a/Import.ts", 2, 1)]),
      message("m2", [file("/a/Import.ts", 3, 2)]),
    ]).map(fileView),
    collectLibraryFiles([{ id: "m1", turnId: "t1", diffSummary: {
      initialFiles: [file("a.ts", 1, 1)], extraFiles: [file("a.ts", 2, 2)],
    } }]).map(fileView),
    collectLibraryFiles([message("m1", [file("a.ts", -1, Number.NaN)])]).map(fileView),
    collectLibraryFiles([message("m1", [file(""), file("   ")])]).map(fileView),
    collectLibraryFiles([message("m1", [file("b.md"), file("a.ts")])]).map(fileView),
  ],
  sources: [
    collectLibrarySources([]).map(sourceView),
    collectLibrarySources([message("m1", [], source("r1"))]).map(sourceView),
    collectLibrarySources([
      message("m1", [], source("r1", "search")),
      message("m2", [], source("r1", "fetch")),
    ]).map(sourceView),
    collectLibrarySources([message("m1", [], source("r1", "  "))]).map(sourceView),
    collectLibrarySources([
      message("m1", [], source("r1", "search", "bad")),
      message("m2", [], source("r2", "fetch", "2026-01-02T03:04:05Z")),
    ]).map(sourceView),
    collectLibrarySources([
      message("m1", [], source("r2", "search", "2026-01-02T03:04:05Z")),
      message("m2", [], source("r1", "fetch", "2026-01-02T03:04:05Z")),
    ]).map(sourceView),
    collectLibrarySources([message("m1", [], source("r1", "search", 42))]).map(sourceView),
    collectLibrarySources([
      message("m1", [], source("r1", "search", "2026-01-02T03:04:05Z")),
      message("m2", [], source("r2", "fetch", "2026-01-03T00:00:00Z")),
    ]).map(sourceView),
  ],
  filters: [
    filterLibraryFiles(sampleFiles, "").map(file => file.path),
    filterLibraryFiles(sampleFiles, "ＩＭＰＯＲＴ").map(file => file.path),
    filterLibraryFiles(sampleFiles, "Ｂ.ＭＤ").map(file => file.path),
    filterLibraryFiles(sampleFiles, "missing").map(file => file.path),
    filterLibrarySources(sampleSources, "Fetch").map(source => source.ref),
    filterLibrarySources(sampleSources, "Ｒ１").map(source => source.ref),
  ],
  views: [
    formatSourceQueriedAt(""),
    formatSourceQueriedAt("2026-01-02T03:04:05Z"),
    formatSourceQueriedAt("bad"),
    formatSourceQueriedAt(42),
    shortLibraryId(""),
    shortLibraryId("123456789012"),
    shortLibraryId("1234567890123"),
    shortLibraryId("  12345  "),
  ],
};
process.stdout.write(JSON.stringify(result));
"""

EXPECTED_PATHS = (
    {"directory": "/a/b", "name": "File.ts"},
    {"directory": "\\a\\b", "name": "File.ts"},
    {"directory": "/a/b", "name": "File.ts"},
    {"directory": "", "name": "File.ts"},
    {"directory": "/a/b", "name": "File.ts"},
    {"directory": "", "name": ""},
    {"directory": "", "name": ""},
    {"directory": "", "name": ""},
)
EXPECTED_KINDS = ("TS", "FILE", "FILE", "GZ", "123", "FILE", "ABC", "FILE")
EXPECTED_FILES = (
    [],
    ["a.ts|a.ts||TS|m1|turn-m1|2|1|1"],
    ["/a/Import.ts|Import.ts|/a|TS|m1|turn-m1|5|3|2"],
    ["a.ts|a.ts||TS|m1|t1|3|3|2"],
    ["a.ts|a.ts||TS|m1|turn-m1|0|0|1"],
    [],
    ["a.ts|a.ts||TS|m1|turn-m1|1|0|1", "b.md|b.md||MD|m1|turn-m1|1|0|1"],
)
EXPECTED_SOURCES = (
    [],
    ["r1|search||m1|turn-m1"],
    ["r1|search||m1|turn-m1"],
    ["r1|未知工具||m1|turn-m1"],
    ["r2|fetch|2026-01-02T03:04:05Z|m2|turn-m2", "r1|search|bad|m1|turn-m1"],
    ["r1|fetch|2026-01-02T03:04:05Z|m2|turn-m2", "r2|search|2026-01-02T03:04:05Z|m1|turn-m1"],
    ["r1|search||m1|turn-m1"],
    ["r2|fetch|2026-01-03T00:00:00Z|m2|turn-m2", "r1|search|2026-01-02T03:04:05Z|m1|turn-m1"],
)
EXPECTED_FILTERS = (
    ["/a/Import.ts", "b.md"],
    ["/a/Import.ts"],
    ["b.md"],
    [],
    ["r2"],
    ["r1"],
)
EXPECTED_VIEWS = (
    "查询时间未知", "TIME 2026-01-02T03:04:05.000Z", "bad", "查询时间未知",
    "", "123456789012", "12345678…", "12345",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "libraryFiles.ts"
        stub = Path(directory) / "toolSource.mjs"
        source = _read(TARGET).replace(
            'from "./toolSource"',
            f'from "{stub.as_uri()}"',
        )
        target.write_text(source, encoding="utf-8")
        stub.write_text(STUB, encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 资料库整理试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 资料库整理试算失败，请核对 Node.js 24+ 与 libraryFiles.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的资料库整理结果") from None
    for key in ("paths", "kinds", "files", "sources", "filters", "views"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"资料库整理{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"资料库整理{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["paths"], EXPECTED_PATHS, "路径拆分")
    checked += _compare(payload["kinds"], EXPECTED_KINDS, "扩展名标签")
    checked += _compare(payload["files"], EXPECTED_FILES, "文件汇总")
    checked += _compare(payload["sources"], EXPECTED_SOURCES, "来源汇总")
    checked += _compare(payload["filters"], EXPECTED_FILTERS, "筛选")
    checked += _compare(payload["views"], EXPECTED_VIEWS, "文案与短标识")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_library_files.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_library_files.py")
    if "共 45 项结构、45 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_library_files.py 检查 45 项结构、45 项行为")
    return 2


def check_library_files() -> tuple[int, int]:
    structure = _expect(FRAGMENTS, _read(TARGET), TARGET)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_library_files()
    except (OSError, ValueError) as error:
        print(f"资料库整理规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"资料库整理规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
