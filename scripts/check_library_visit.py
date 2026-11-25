#!/usr/bin/env python3
"""核对资料库文件详情只属于当前一次页面访问。

`libraryVisit.ts` 把页面与文件详情放在同一个状态对象里：页面变化时开启新一次访问并
丢弃旧详情，同一页面同步保持原对象；打开 / 关闭 / 替换详情不修改原状态。结构侧固定
`WorkspacePages` 在渲染期同步页面访问、不再把 `file` 放回跨页面状态；行为侧由 Node
直接加载真实模块核对同页保持、离开丢弃、返回不恢复与幂等同步。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = "apps/desktop/src/renderer/src/data/libraryVisit.ts"
PAGES = "apps/desktop/src/renderer/src/shell/WorkspacePages.tsx"
DOCS = "docs/TECHNICAL_REFERENCE.md"

MODULE_FRAGMENTS = (
    " * 工作区页面切换时 `WorkspacePages` 保持挂载，筛选词因此可以跨页面保留；但文件详情",
    " * 是覆盖页面的临时浮层，只属于打开它的那次资料库访问。把页面与详情放在同一个状态",
    " * 对象里，页面变化时同步出新访问并丢弃旧详情，返回资料库不会自动重开上一次的弹窗。",
    " * 同步必须幂等：同一页面原样返回，调用方据此在渲染期同步而不会陷入循环。",
    "export interface LibraryVisit {",
    "export function syncLibraryVisit(visit: LibraryVisit, page: string): LibraryVisit {",
    "return visit.page === page ? visit : { page, file: null };",
    "export function withLibraryFile(visit: LibraryVisit, file: string | null): LibraryVisit {",
    "return visit.file === file ? visit : { ...visit, file };",
)
PAGES_FRAGMENTS = (
    'import { syncLibraryVisit, withLibraryFile, type LibraryVisit } from "../data/libraryVisit";',
    "const [libraryVisit, setLibraryVisit] = useState<LibraryVisit>(() => ({ page, file: null }));",
    "if (libraryVisit.page !== page) setLibraryVisit(syncLibraryVisit(libraryVisit, page));",
    "const file = libraryVisit.file;",
    "const setFile = (next: string | null) => setLibraryVisit(current => withLibraryFile(current, next));",
)
OLD_STATE = "[file, setFile] = useState"

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { syncLibraryVisit, withLibraryFile } = await import(pathToFileURL(process.argv[1]).href);
const base = { page: "library", file: null };
const opened = withLibraryFile(base, "a.ts");
const away = syncLibraryVisit(opened, "skills");
const returned = syncLibraryVisit(syncLibraryVisit(away, "library"), "library");
const results = [
  ["同一页面保持引用", syncLibraryVisit(base, "library") === base],
  ["打开文件写入路径", opened.file === "a.ts" && opened.page === "library"],
  ["打开不改原对象", base.file === null && opened !== base],
  ["重复打开保持引用", withLibraryFile(opened, "a.ts") === opened],
  ["关闭文件清空路径", withLibraryFile(opened, null).file === null],
  ["替换路径保留页面并在原状态上追加", withLibraryFile(opened, "b.ts").file === "b.ts" && opened.file === "a.ts"],
  ["离开页面丢弃详情", away.page === "skills" && away.file === null],
  ["离开不改写已打开状态", opened.file === "a.ts"],
  ["再次同步保持引用", syncLibraryVisit(away, "skills") === away],
  ["返回资料库不恢复详情", returned.page === "library" && returned.file === null],
].map(([name, ok]) => ({ name, ok }));
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_BEHAVIORS = 10


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _run_node() -> list:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(ROOT / MODULE)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except subprocess.TimeoutExpired:
        raise ValueError("Node 资料库访问试算超时") from None
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
        raise ValueError(
            "Node 资料库访问试算失败，请核对 Node.js 24+ 与 libraryVisit.ts"
            + (f"：{detail[:200]}" if detail else "")
        ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的资料库访问结果") from None
    if not isinstance(payload, list):
        raise ValueError("Node 未返回资料库访问结果列表")
    return payload


def _check_behaviors() -> int:
    payload = _run_node()
    if len(payload) != EXPECTED_BEHAVIORS:
        raise ValueError(f"资料库访问用例数量变化：期望 {EXPECTED_BEHAVIORS}，实际 {len(payload)}")
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError(f"资料库访问第 {index + 1} 个用例格式不符")
        if item.get("ok") is not True:
            raise ValueError(f"资料库访问用例失败：{item['name']}")
    return len(payload)


def _check_structures() -> int:
    checked = _expect(MODULE_FRAGMENTS, _read(MODULE), MODULE)
    checked += _expect(PAGES_FRAGMENTS, _read(PAGES), PAGES)
    if OLD_STATE in _read(PAGES):
        raise ValueError(f"{PAGES} 仍把文件详情放回跨页面状态")
    return checked + 1


def _check_documentation(structures: int, behaviors: int) -> None:
    reference = _read(DOCS)
    if "`check_library_visit.py`" not in reference:
        raise ValueError(f"{DOCS} 缺少 check_library_visit.py 的索引")
    summary = f"共 {structures} 项结构、{behaviors} 项行为"
    if summary not in reference:
        raise ValueError(f"{DOCS} 缺少资料库访问检查的计数：{summary}")


def main() -> int:
    try:
        structures = _check_structures()
        behaviors = _check_behaviors()
        _check_documentation(structures, behaviors)
    except (OSError, ValueError) as error:
        print(f"资料库访问规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"资料库访问规则一致：{structures} 项结构、{behaviors} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
