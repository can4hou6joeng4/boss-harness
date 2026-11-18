#!/usr/bin/env python3
"""核对内核与桌面的搜索归一化在全部 Unicode 码点上一致。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CASE_FOLD = "apps/desktop/src/renderer/src/data/caseFold.ts"
BLOCK = 0x1000
BLOCKS = range(0x110000 // BLOCK)
COMPARED = 0x110000 - (0xE000 - 0xD800)

sys.path.insert(0, str(ROOT / "harness/src"))
from boss_harness import search_unicode  # noqa: E402

NODE_SCRIPT = r"""
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";
const { caseFold } = await import(pathToFileURL(process.argv[1]).href);
const blocks = {};
for (let cp = 0; cp <= 0x10FFFF; cp += 1) {
  if (cp >= 0xD800 && cp <= 0xDFFF) continue;
  let folded = "";
  for (const char of String.fromCodePoint(cp).normalize("NFKC")) folded += caseFold(char);
  (blocks[cp >> 12] ??= createHash("sha256")).update(`${cp.toString(16)}=${folded}\n`, "utf8");
}
const result = {};
for (const [block, digest] of Object.entries(blocks)) result[block] = digest.digest("hex");
process.stdout.write(JSON.stringify(result));
"""


def _python_blocks() -> dict[int, str]:
    digests = {}
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        char = chr(cp)
        folded = (search_unicode.search_normalize(char)
                  if search_unicode.needs_extra(char)
                  else unicodedata.normalize("NFKC", char).casefold())
        digests.setdefault(cp // BLOCK, hashlib.sha256()).update(f"{cp:x}={folded}\n".encode("utf-8"))
    return {block: digest.hexdigest() for block, digest in digests.items()}


def _node_blocks() -> dict[int, str]:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT,
             str(ROOT / CASE_FOLD)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        blocks = json.loads(result.stdout)
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError, ValueError):
        raise ValueError("Node 搜索归一化试算失败，请核对 Node.js 24+ 与 caseFold.ts") from None
    if not isinstance(blocks, dict):
        raise ValueError("Node 未返回按码点分块组织的归一化结果")
    try:
        parsed = {int(block): digest for block, digest in blocks.items()}
    except ValueError:
        raise ValueError("Node 返回了无效的码点分块编号") from None
    if set(parsed) != set(BLOCKS):
        raise ValueError("Node 未返回完整的归一化码点分块")
    return parsed


def check_search_unicode() -> int:
    python_blocks = _python_blocks()
    node_blocks = _node_blocks()
    mismatched = [block for block in BLOCKS if python_blocks.get(block) != node_blocks.get(block)]
    if mismatched:
        ranges = "、".join(
            f"U+{block * BLOCK:04X}–U+{min((block + 1) * BLOCK, 0x110000) - 1:04X}"
            for block in mismatched[:8]
        )
        suffix = "" if len(mismatched) <= 8 else f" 等 {len(mismatched)} 个分块"
        raise ValueError(f"搜索归一化在 {ranges}{suffix} 不一致")
    return COMPARED


def main() -> int:
    try:
        compared = check_search_unicode()
    except ValueError as error:
        print(f"搜索归一化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索归一化一致：{compared} 个码点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
