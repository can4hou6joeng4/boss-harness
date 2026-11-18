#!/usr/bin/env python3
"""核对内核与桌面的搜索归一化在全部 Unicode 码点上一致。"""

from __future__ import annotations

import argparse
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

NODE_BLOCK_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { caseFold } = await import(pathToFileURL(process.argv[1]).href);
const start = Number(process.argv[2]);
const result = {};
for (let cp = start; cp < start + 0x1000; cp += 1) {
  if (cp >= 0xD800 && cp <= 0xDFFF) continue;
  let folded = "";
  for (const char of String.fromCodePoint(cp).normalize("NFKC")) folded += caseFold(char);
  result[cp.toString(16)] = folded;
}
process.stdout.write(JSON.stringify(result));
"""


def _python_fold(char: str) -> str:
    return (search_unicode.search_normalize(char)
            if search_unicode.needs_extra(char)
            else unicodedata.normalize("NFKC", char).casefold())


def _python_blocks() -> dict[int, str]:
    digests = {}
    for cp in range(0x110000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        digests.setdefault(cp // BLOCK, hashlib.sha256()).update(
            f"{cp:x}={_python_fold(chr(cp))}\n".encode("utf-8"))
    return {block: digest.hexdigest() for block, digest in digests.items()}


def _node_output(script: str, *arguments: str) -> dict:
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "--no-warnings", "-e", script,
             str(ROOT / CASE_FOLD), *arguments],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        raise ValueError("无法运行 node，请安装 Node.js 24+") from None
    except (OSError, subprocess.CalledProcessError):
        raise ValueError("Node 搜索归一化试算失败，请核对 Node.js 24+ 与 caseFold.ts") from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的归一化结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回按码点组织的结果")
    return payload


def _node_blocks() -> dict[int, str]:
    blocks = _node_output(NODE_SCRIPT)
    try:
        parsed = {int(block): digest for block, digest in blocks.items()}
    except (TypeError, ValueError):
        raise ValueError("Node 返回了无效的码点分块编号") from None
    if set(parsed) != set(BLOCKS):
        raise ValueError("Node 未返回完整的归一化码点分块")
    return parsed


def _node_block(block: int) -> dict[int, str]:
    values = _node_output(NODE_BLOCK_SCRIPT, str(block * BLOCK))
    try:
        parsed = {int(cp, 16): folded for cp, folded in values.items()}
    except (TypeError, ValueError):
        raise ValueError("Node 返回了无效的码点") from None
    if any(not isinstance(folded, str) for folded in parsed.values()):
        raise ValueError("Node 返回了无效的归一化结果")
    expected = {cp for cp in range(block * BLOCK, min((block + 1) * BLOCK, 0x110000))
                if not 0xD800 <= cp <= 0xDFFF}
    if set(parsed) != expected:
        raise ValueError("Node 未返回分块内全部码点")
    return parsed


def _python_block(block: int) -> dict[int, str]:
    return {cp: _python_fold(chr(cp))
            for cp in range(block * BLOCK, min((block + 1) * BLOCK, 0x110000))
            if not 0xD800 <= cp <= 0xDFFF}


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
        raise ValueError(f"搜索归一化在 {ranges}{suffix} 不一致；"
                         f"用 --block 0x{mismatched[0]:X} 查看码点明细")
    return COMPARED


def report_block(block: int) -> int:
    python_values = _python_block(block)
    node_values = _node_block(block)
    mismatched = [cp for cp in sorted(python_values) if python_values[cp] != node_values.get(cp)]
    start, end = block * BLOCK, min((block + 1) * BLOCK, 0x110000) - 1
    if not mismatched:
        print(f"分块 U+{start:04X}–U+{end:04X} 一致：{len(python_values)} 个码点")
        return 0
    for cp in mismatched[:20]:
        print(f"U+{cp:04X}: Python {python_values[cp]!r} / Node {node_values.get(cp)!r}", file=sys.stderr)
    suffix = "" if len(mismatched) <= 20 else f"，另有 {len(mismatched) - 20} 个"
    print(f"分块 U+{start:04X}–U+{end:04X} 不一致：{len(mismatched)} 个码点{suffix}", file=sys.stderr)
    return 2


def _block_argument(value: str) -> int:
    try:
        block = int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError("分块编号须为十进制或 0x 前缀十六进制整数") from None
    if block not in BLOCKS:
        raise argparse.ArgumentTypeError(f"分块编号须在 0 到 {len(BLOCKS) - 1} 之间")
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核对内核与桌面的搜索归一化")
    parser.add_argument("--block", type=_block_argument, help="只比较指定 0x1000 分块并列出不一致码点")
    args = parser.parse_args(argv)
    try:
        if args.block is not None:
            return report_block(args.block)
        compared = check_search_unicode()
    except ValueError as error:
        print(f"搜索归一化核对失败，{error}", file=sys.stderr)
        return 2
    print(f"搜索归一化一致：{compared} 个码点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
