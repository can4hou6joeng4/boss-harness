#!/usr/bin/env python3
"""核对工具结果的显式分段读取与整体复制。

`toolResultReads.ts` 按引用逐段读取工具结果：每段核对引用身份、偏移、文本长度、
游标与结束位置；游标状态错误转换为「请重新打开聊天」的提示；整体复制在发起请求前
拒绝超限与非法引用，随后连续读取并在段间核对偏移、数量与取消信号，任一段失败都不
返回部分文本。这里在临时目录改写协议与错误导入，用 Node 直接加载真实模块逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
READS = "apps/desktop/src/renderer/src/data/toolResultReads.ts"
SHARED = "packages/protocol/src/index.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

READ_FRAGMENTS = (
    'import { ClientMethods, type ToolResultReadResponse, type ToolResultReference } from "@boss-harness/protocol";',
    'import { throwIfHarnessRpcError } from "./harnessRpcErrors";',
    "const CHUNK_LIMIT = 16384;",
    'export const STALE_RESULT_RECHECK_NOTICE = "结果版本已变化，请重新打开聊天并核对当前引用后查看";',
    "function isToolResultReference(value: unknown): value is ToolResultReference {",
    'return ref.encoding === "json"',
    '&& /^[a-f0-9]{64}$/.test(ref.sha256)',
    "&& Number.isSafeInteger(ref.byteLength)",
    "&& Number.isSafeInteger(ref.characterLength);",
    "function staleResultError(error: unknown): Error | null {",
    "if (!rpc || rpc.rpcError !== true || rpc.code !== -32011) return null;",
    'if (code !== "STALE_RESULT") return null;',
    "return isToolResultReference((data as Record<string, unknown>).currentRef)",
    "? new Error(STALE_RESULT_RECHECK_NOTICE) : null;",
    "export const MAX_WHOLE_RESULT_CHARS = 1_000_000;",
    "const MIN_WHOLE_CHUNK_CHARS = 1024;",
    "export async function readToolResultChunk(",
    "response = throwIfHarnessRpcError(await requester<ToolResultReadResponse>(ClientMethods.threadItemResultRead, {",
    "threadId: ref.threadId, itemId: ref.itemId, sha256: ref.sha256, cursor, limit: CHUNK_LIMIT,",
    "throw staleResultError(error) ?? error;",
    "const actual = response?.resultRef;",
    '.some(key => actual[key] !== ref[key])) throw new Error("结果版本已变化，请重新打开聊天后查看");',
    'if (typeof response.text !== "string" || !Number.isSafeInteger(response.offset) || response.offset < 0 ||',
    '!Number.isSafeInteger(ref.characterLength) || ref.characterLength < 1 ||',
    '!Number.isSafeInteger(ref.byteLength) || ref.byteLength < ref.characterLength ||',
    '(cursor === undefined ? response.offset !== 0 : response.offset === 0)) throw new Error("结果分段无效");',
    "const length = Array.from(response.text).length;",
    "const end = response.offset + length;",
    "if (length < 1 || length > CHUNK_LIMIT || end > ref.characterLength ||",
    "(response.nextCursor === null ? end !== ref.characterLength :",
    'typeof response.nextCursor !== "string" || !response.nextCursor.startsWith("tr1_") ||',
    "response.nextCursor.length > 2048 || response.nextCursor === cursor || end >= ref.characterLength)) {",
    'throw new Error("结果分段不完整，请重试");',
    "export interface WholeResultReadOptions {",
    "requester?: Requester;",
    "maxChars?: number;",
    "onProgress?: (loaded: number, total: number) => void;",
    "signal?: AbortSignal;",
    "function throwIfCancelled(signal: AbortSignal | undefined): void {",
    'if (signal?.aborted) throw new Error("已取消整体读取");',
    "export async function readWholeToolResult(",
    "const { requester, maxChars = MAX_WHOLE_RESULT_CHARS, onProgress, signal } = options;",
    "throwIfCancelled(signal);",
    "if (!Number.isSafeInteger(ref.characterLength) || ref.characterLength < 1) throw new Error(\"结果引用无效\");",
    "if (!Number.isSafeInteger(maxChars) || maxChars < 1) throw new Error(\"整体复制上限无效\");",
    "throw new Error(`结果共 ${ref.characterLength} 字符，超过整体复制上限 ${maxChars} 字符`);",
    "const chunkBudget = Math.ceil(ref.characterLength / MIN_WHOLE_CHUNK_CHARS) + 8;",
    "while (offset < ref.characterLength) {",
    "const chunk = await readToolResultChunk(ref, cursor, requester);",
    "if (chunk.offset !== offset) throw new Error(\"结果分段偏移不连续，请分段查看\");",
    "const length = Array.from(chunk.text).length;",
    "parts.push(chunk.text);",
    "offset += length;",
    "if (parts.length > chunkBudget) throw new Error(\"结果分段数量异常，请分段查看\");",
    "if (offset > ref.characterLength) throw new Error(\"结果分段超出引用长度，请分段查看\");",
    "onProgress?.(offset, ref.characterLength);",
    "if (offset < ref.characterLength) {",
    "if (!chunk.nextCursor) throw new Error(\"结果分段提前结束，请分段查看\");",
    "cursor = chunk.nextCursor;",
    "return parts.join(\"\");",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const { readToolResultChunk, readWholeToolResult, MAX_WHOLE_RESULT_CHARS, STALE_RESULT_RECHECK_NOTICE } =
  await import(pathToFileURL(process.argv[1]).href);
const HASH = "a".repeat(64);
const ref = (over = {}) => ({ threadId: "t1", itemId: "i1", encoding: "json", sha256: HASH,
  byteLength: 10, characterLength: 8, ...over });
const chunk = (over = {}) => ({ resultRef: ref(), text: "ab", offset: 0, nextCursor: "tr1_1", ...over });
const call = (response, options = {}) => {
  const reference = ref(options.ref ?? {});
  const cursor = options.cursor;
  const request = async () => options.error ? { __harnessRpcError: options.error } : response;
  return readToolResultChunk(reference, cursor, request).then(
    value => [value.text, value.offset, value.nextCursor], error => `bad:${error.message}`);
};
const whole = (reference, options = {}) => readWholeToolResult(reference, options)
  .then(value => ["ok", value], error => `bad:${error.message}`);
const controller = () => new AbortController();
const reply = (texts, cursors = ["tr1_1", "tr1_2", "tr1_3"]) => {
  let index = 0;
  return async () => {
    const current = index;
    index += 1;
    return { resultRef: ref(), text: texts[current], offset: current * 2,
      nextCursor: current < texts.length - 1 ? cursors[current] : null };
  };
};
const abortResponse = (signal, after = 0) => {
  let count = 0;
  return async () => {
    count += 1;
    if (count > after) signal.abort();
    return chunk();
  };
};
const results = {
  constants: [MAX_WHOLE_RESULT_CHARS === 1000000, STALE_RESULT_RECHECK_NOTICE],
  chunk: [
    await call({ resultRef: ref({ characterLength: 3 }), text: "abc", offset: 0, nextCursor: null }, { ref: { characterLength: 3 } }),
    await call(chunk({ text: "cd", offset: 2, nextCursor: "tr1_2" }), { cursor: "tr1_1" }),
    await call(chunk({ resultRef: ref({ sha256: "b".repeat(64) }) })),
    await call({ resultRef: ref(), text: "ab", offset: 0, nextCursor: "tr1_1" }, { ref: { characterLength: 2 } }),
    await call(chunk({ resultRef: ref({ characterLength: 0 }) }), { ref: { characterLength: 0 } }),
    await call(chunk({ text: 5 })),
    await call(chunk({ text: "", nextCursor: null, offset: 8 })),
    await call(chunk({ offset: 2 })),
    await call(chunk({ offset: -1 }), { cursor: "tr1_1" }),
    await call(chunk({ resultRef: ref({ itemId: "i2" }) })),
    await call(chunk({ resultRef: ref({ characterLength: 4 }) })),
    await call(chunk({ text: "ab", nextCursor: null, offset: 7 }), { cursor: "tr1_1" }),
    await call(chunk({ text: "abc", nextCursor: null, offset: 4 }), { cursor: "tr1_1" }),
    await call(chunk({ text: "ab", nextCursor: "bad", offset: 2 }), { cursor: "tr1_1" }),
    await call(chunk({ nextCursor: "x".repeat(2049) })),
    await call(chunk(), { cursor: "tr1_1" }),
    await call(chunk({ text: "cd", offset: 2, nextCursor: "tr1_1" }), { cursor: "tr1_1" }),
    await call(chunk({ text: "ab", nextCursor: "tr1_3", offset: 8 }), { cursor: "tr1_1" }),
  ],
  stale: [
    await call(chunk(), { error: { code: -32012, message: "other", data: { code: "STALE_RESULT", currentRef: ref() } } }),
    await call(chunk(), { error: { code: -32011, message: "stale", data: { code: "OTHER", currentRef: ref() } } }),
    await call(chunk(), { error: { code: -32011, message: "stale", data: { code: "STALE_RESULT", currentRef: ref() } } }),
    await call(chunk(), { error: { code: -32011, message: "stale", data: { code: "STALE_RESULT", currentRef: {} } } }),
    await call(chunk(), { error: { code: -32011, message: "stale" } }),
    await call(chunk(), { error: { code: -32012, message: "other" } }),
  ],
  whole: [
    await (() => { let n = 0; return whole(ref(), { requester: async () => {
      n += 1; return n === 1 ? chunk({ text: "ab", offset: 0, nextCursor: "tr1_1" })
        : chunk({ text: "efgh", offset: 4, nextCursor: null });
    } }); })(),
    await whole(ref(), { requester: reply(["ab", "cd", "efgh"]) }),
    await whole(ref(), { requester: reply(["ab", "cd", "efgh"]), maxChars: 8 }),
    await (() => { const seen = []; return whole(ref(), { requester: reply(["ab", "cd", "efgh"]), onProgress: (loaded, total) => {
      seen.push([loaded, total]);
    } }).then(value => [value, seen]); })(),
    await whole(ref({ characterLength: 9 }), { requester: reply(["ab", "cd", "efgh"]), maxChars: 8 }),
    await whole(ref({ characterLength: 0 }), { requester: reply(["ab"]) }),
    await whole(ref({ characterLength: 1.5 }), { requester: reply(["ab"]) }),
    await whole(ref({ characterLength: 1000001 }), { requester: reply(["ab"]) }),
    await whole(ref(), { requester: reply(["ab"]), maxChars: 7 }),
    await whole(ref(), { requester: reply(["ab"]), maxChars: 0 }),
    await whole(ref(), { requester: reply(["ab"]), maxChars: 1.5 }),
  ],
  abort: [
    await whole(ref(), { requester: async () => chunk({ text: "abcdefgh", nextCursor: null }) }),
    await (() => { const c = controller(); c.abort(); return whole(ref(), { requester: async () => chunk(), signal: c.signal }); })(),
    await (() => { const c = controller(); return whole(ref(), { requester: async () => {
      c.abort(); return chunk({ text: "abcdefgh", nextCursor: null });
    }, signal: c.signal }); })(),
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_CONSTANTS = (True, "结果版本已变化，请重新打开聊天并核对当前引用后查看")
EXPECTED_CHUNK = (
    ["abc", 0, None],
    ["cd", 2, "tr1_2"],
    "bad:结果版本已变化，请重新打开聊天后查看",
    "bad:结果版本已变化，请重新打开聊天后查看",
    "bad:结果分段无效",
    "bad:结果分段无效",
    "bad:结果分段无效",
    "bad:结果分段无效",
    "bad:结果分段无效",
    "bad:结果版本已变化，请重新打开聊天后查看",
    "bad:结果版本已变化，请重新打开聊天后查看",
    "bad:结果分段不完整，请重试",
    "bad:结果分段不完整，请重试",
    "bad:结果分段不完整，请重试",
    "bad:结果分段不完整，请重试",
    "bad:结果分段无效",
    "bad:结果分段不完整，请重试",
    "bad:结果分段不完整，请重试",
)
EXPECTED_STALE = (
    "bad:other",
    "bad:stale",
    "bad:结果版本已变化，请重新打开聊天并核对当前引用后查看",
    "bad:stale",
    "bad:stale",
    "bad:other",
)

EXPECTED_PROGRESS = ([2, 8], [4, 8], [8, 8])
EXPECTED_WHOLE = (
    "bad:结果分段偏移不连续，请分段查看",
    ["ok", "abcdefgh"],
    ["ok", "abcdefgh"],
    [["ok", "abcdefgh"], list(EXPECTED_PROGRESS)],
    "bad:结果共 9 字符，超过整体复制上限 8 字符",
    "bad:结果引用无效",
    "bad:结果引用无效",
    "bad:结果共 1000001 字符，超过整体复制上限 1000000 字符",
    "bad:结果共 8 字符，超过整体复制上限 7 字符",
    "bad:整体复制上限无效",
    "bad:整体复制上限无效",
)
EXPECTED_ABORT = (
    ["ok", "abcdefgh"],
    "bad:已取消整体读取",
    "bad:已取消整体读取",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> tuple[dict, list]:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "toolResultReads.ts"
        source = _read(READS)
        source = source.replace(
            'from "@boss-harness/protocol"',
            f'from "{(ROOT / SHARED).as_uri()}"',
        ).replace(
            'from "./harnessRpcErrors"',
            f'from "{(ROOT / "apps/desktop/src/renderer/src/data/harnessRpcErrors.ts").as_uri()}"',
        )
        target.write_text(source, encoding="utf-8")
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except subprocess.TimeoutExpired:
            raise ValueError("Node 结果读取试算超时") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 结果读取试算失败，请核对 Node.js 24+ 与 toolResultReads.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的结果读取结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回结果读取矩阵")
    for key in ("constants", "chunk", "whole", "stale", "abort"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"结果读取{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"结果读取{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["constants"], EXPECTED_CONSTANTS, "常量")
    checked += _compare(payload["chunk"], EXPECTED_CHUNK, "分段校验")
    checked += _compare(payload["whole"], EXPECTED_WHOLE, "整体读取")
    checked += _compare(payload["stale"], EXPECTED_STALE, "过期引用")
    checked += _compare(payload["abort"], EXPECTED_ABORT, "取消信号")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_result_reads.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_result_reads.py")
    if "共 60 项结构、40 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_result_reads.py 检查 49 项结构、42 项行为")
    return 2


def check_result_reads() -> tuple[int, int]:
    structure = _expect(READ_FRAGMENTS, _read(READS), READS)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_result_reads()
    except (OSError, ValueError) as error:
        print(f"结果读取规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"结果读取规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
