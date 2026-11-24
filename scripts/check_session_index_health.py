#!/usr/bin/env python3
"""核对会话索引健康度的读数与状态文案。

内核会跳过无法解析的会话日志，只在这里暴露；缺失或形状不可信必须显示
「未报告」，不能渲染成告警或正常。这里固定数值校验、零计数与列出 id 的
矛盾判定、id 去重与截断，以及设置页文案的三态，避免把损坏响应当成健康。
行为侧先在临时状态目录中真实构造 `ApplicationService`（`provider=none`，
服务端输出重定向，不联网），写入损坏的会话日志后读取 `config/read`，核对
计数完整、id 按字典序截断到上限；再把真实 `sessionIndexHealth.ts` 复制到
临时目录，由 Node 直接加载，驱动这些真实响应到桌面读数的衔接、读数边界
与文案三态。
"""

from __future__ import annotations

from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DOCS = "docs/TECHNICAL_REFERENCE.md"
HEALTH = "apps/desktop/src/renderer/src/data/sessionIndexHealth.ts"
KERNEL = "harness/src"

# 无法解析的会话日志：首行不是完整 JSON，内核跳过索引并记入诊断。
DAMAGED_LOG = b'{"broken": \n'
# 不符合会话 id 形状（12 位小写十六进制）的文件名，内核不当作会话日志。
FOREIGN_NAMES = ("not-a-thread.jsonl", "a" * 13 + ".jsonl", "A" * 12 + ".jsonl")

KERNEL_EXPECTED = 6
NODE_EXPECTED = 31

NODE_SCRIPT = """\
import { readFileSync } from "node:fs";
import {
  SESSION_INDEX_MAX_IDS,
  readSessionIndexHealth,
  sessionIndexHealthLabel,
} from "./sessionIndexHealth.ts";

let passed = 0;
function expect(label: string, condition: boolean): void {
  if (!condition) {
    console.error(`FAIL ${label}`);
    process.exit(1);
  }
  passed += 1;
}
const same = (a: any, b: any): boolean => JSON.stringify(a) === JSON.stringify(b);
const read = (count: unknown, ids?: unknown): any =>
  readSessionIndexHealth(
    ids === undefined
      ? { unreadableThreadCount: count }
      : { unreadableThreadCount: count, unreadableThreadIds: ids },
  );
const names = (total: number): string[] => Array.from({ length: total }, (_, index) => `id${index}`);

// 内核真实响应：Python 侧在临时状态目录中读取 config/read 后写入，这里只做桌面读数。
const kernel = JSON.parse(readFileSync(process.argv[2], "utf8"));
const labelOf = (config: unknown): string => sessionIndexHealthLabel(readSessionIndexHealth(config));
expect(
  "内核干净状态读成正常",
  same(readSessionIndexHealth(kernel.clean), { count: 0, ids: [] }) && labelOf(kernel.clean) === "正常",
);
expect(
  "内核少量损坏原样读出",
  same(readSessionIndexHealth(kernel.few), { count: kernel.fewIds.length, ids: kernel.fewIds }),
);
expect("内核少量损坏的文案", labelOf(kernel.few) === `${kernel.fewIds.length} 个无法读取`);
expect("内核超过上限时计数完整", (readSessionIndexHealth(kernel.many) as any).count === kernel.total);
expect("内核截断数量与桌面上限一致", kernel.many.unreadableThreadIds.length === SESSION_INDEX_MAX_IDS);
expect("内核超过上限时 id 全部保留", same((readSessionIndexHealth(kernel.many) as any).ids, kernel.manyIds));

// 桌面读数自身的边界；与内核衔接用例重复的输入形状不再另列。
const cap = SESSION_INDEX_MAX_IDS;
expect(
  "非对象返回 null",
  [null, undefined, 42, "x", []].every(value => readSessionIndexHealth(value) === null),
);
const arrayLike: any = [];
arrayLike.unreadableThreadCount = 0;
expect("带属性的数组仍拒绝", readSessionIndexHealth(arrayLike) === null);
expect("缺少计数返回 null", readSessionIndexHealth({}) === null);
expect("计数非数字返回 null", read("3") === null);
expect("计数为小数返回 null", read(1.5) === null);
expect("计数为负返回 null", read(-1) === null);
expect("计数为 NaN 或无穷返回 null", read(Number.NaN) === null && read(Infinity) === null);
expect("计数超出安全整数返回 null", read(2 ** 53) === null);
expect(
  "最大安全整数可用",
  same(read(Number.MAX_SAFE_INTEGER, []), { count: Number.MAX_SAFE_INTEGER, ids: [] }),
);
expect("零计数且无列表", same(read(0), { count: 0, ids: [] }));
expect("零计数却列出 id 判矛盾", read(0, ["a"]) === null);
expect("零计数列出 64 字符 id 仍判矛盾", read(0, ["a".repeat(64)]) === null);
expect(
  "零计数只含非法 id 不算列出",
  same(read(0, ["", 42, null, "a".repeat(65)]), { count: 0, ids: [] }),
);
expect("零计数且列表非数组", same(read(0, "a"), { count: 0, ids: [] }));
expect("有计数去重并保序", same(read(2, ["b", "a", "b", "a"]).ids, ["b", "a"]));
expect("有计数跳过非法 id", same(read(2, ["a", "", 42, null, "b"]).ids, ["a", "b"]));
expect(
  "id 64 字符收集而 65 字符跳过",
  same(read(2, ["a".repeat(64), "b".repeat(65)]).ids, ["a".repeat(64)]),
);
expect("超过上限只保留前几项", same(read(cap + 5, names(cap + 5)).ids, names(cap)));
expect(
  "重复项不占截断名额",
  same(read(2, [...Array.from({ length: cap + 10 }, () => "a"), "b"]).ids, ["a", "b"]),
);
expect(
  "非法项不占截断名额",
  same(read(cap, [...Array.from({ length: cap + 5 }, () => ""), ...names(cap)]).ids, names(cap)),
);
expect("有计数但列表缺失", same(read(2), { count: 2, ids: [] }));
expect("有计数但列表非数组", same(read(2, "a"), { count: 2, ids: [] }));
const reused = ["a", "b"];
expect("结果不复用输入数组", read(2, reused).ids !== reused);
const rawConfig = { unreadableThreadCount: 2, unreadableThreadIds: ["b", "a", "b"] };
const snapshot = JSON.stringify(rawConfig);
readSessionIndexHealth(rawConfig);
expect("输入不被修改", JSON.stringify(rawConfig) === snapshot);
expect("文案未报告", sessionIndexHealthLabel(null) === "未报告");

console.log(`PASS ${passed}`);
"""

FRAGMENTS = (
    "export interface SessionIndexHealth {",
    "count: number;",
    "ids: string[];",
    "export const SESSION_INDEX_MAX_IDS = 20;",
    "const MAX_THREAD_ID_LENGTH = 64;",
    "function isRecord(value: unknown): value is Record<string, unknown> {",
    'return typeof value === "object" && value !== null && !Array.isArray(value);',
    "export function readSessionIndexHealth(config: unknown): SessionIndexHealth | null {",
    "if (!isRecord(config)) return null;",
    "const count = config.unreadableThreadCount;",
    'if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) return null;',
    "const ids: string[] = [];",
    "const raw = config.unreadableThreadIds;",
    "if (count === 0) {",
    "const listed = Array.isArray(raw) && raw.some(value =>",
    'typeof value === "string" && value.length > 0 && value.length <= MAX_THREAD_ID_LENGTH);',
    "return listed ? null : { count, ids };",
    "if (Array.isArray(raw)) {",
    "if (ids.length >= SESSION_INDEX_MAX_IDS) break;",
    'if (typeof value !== "string" || value.length === 0 || value.length > MAX_THREAD_ID_LENGTH) continue;',
    "if (!ids.includes(value)) ids.push(value);",
    "return { count, ids };",
    "export function sessionIndexHealthLabel(health: SessionIndexHealth | null): string {",
    'if (!health) return "未报告";',
    'return health.count > 0 ? `${health.count} 个无法读取` : "正常";',
)

ORDERED = (
    # 读数：对象判定 → 计数校验 → 零计数的矛盾判定 → 有计数时逐条去重截断。
    (
        "export function readSessionIndexHealth(config: unknown): SessionIndexHealth | null {",
        "if (!isRecord(config)) return null;",
        "const count = config.unreadableThreadCount;",
        'if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0) return null;',
        "const raw = config.unreadableThreadIds;",
        "if (count === 0) {",
        "return listed ? null : { count, ids };",
        "if (Array.isArray(raw)) {",
        "if (ids.length >= SESSION_INDEX_MAX_IDS) break;",
        "if (!ids.includes(value)) ids.push(value);",
        "return { count, ids };",
    ),
    # 文案：未报告 → 有计数 → 正常。
    (
        "export function sessionIndexHealthLabel(health: SessionIndexHealth | null): string {",
        'if (!health) return "未报告";',
        'return health.count > 0 ? `${health.count} 个无法读取` : "正常";',
    ),
)


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
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def _check_structure(source: str) -> int:
    checked = 0
    checked += _expect(FRAGMENTS, source, HEALTH)
    for group in ORDERED:
        checked += _ordered(group, source, HEALTH)
    # 反向断言：未报告不能写成正常；去重必须先查再入列；计数不得用浮点校验。
    if 'if (!health) return "正常";' in source:
        raise ValueError(f"{HEALTH} 的未报告状态不能写成正常")
    if "ids.push(value);\n      if (!ids.includes(value))" in source:
        raise ValueError(f"{HEALTH} 的 id 必须先查重再入列")
    if "Number.isInteger(count)" in source:
        raise ValueError(f"{HEALTH} 的计数必须用安全整数校验")
    return checked + 3


@contextmanager
def _clean_environment():
    # 本机的线路、上游与压缩配置不应影响临时内核；退出时恢复原环境。
    with patch.dict(os.environ, {}, clear=False):
        for name in [key for key in os.environ if key.startswith(("BOSS_HARNESS_", "BOSS_CLI_"))]:
            os.environ.pop(name, None)
        yield


def _report(response: dict) -> tuple[object, object]:
    return response.get("unreadableThreadCount"), response.get("unreadableThreadIds")


def _kernel_checks() -> tuple[int, dict]:
    """读取真实 `config/read`；返回断言数量与交给桌面读数的响应。"""
    kernel = str(ROOT / KERNEL)
    if kernel not in sys.path:
        sys.path.insert(0, kernel)
    try:
        from boss_harness.application import MAX_UNREADABLE_THREAD_IDS, ApplicationService
        from boss_harness.models.provider import ModelConfig
        from boss_harness.rpc import JsonRpcServer
    except ImportError as error:
        raise ValueError(f"无法导入内核模块：{error}") from None
    cap = MAX_UNREADABLE_THREAD_IDS
    total = cap + 5
    # 定宽小写十六进制的字典序就是数值序，期望值不依赖内核的排序实现。
    ids = [f"{value:012x}" for value in range(1, total + 1)]
    few = ids[-3:]
    checked = 0
    with tempfile.TemporaryDirectory() as directory, _clean_environment():
        server = JsonRpcServer()
        server._out = io.StringIO()
        service = ApplicationService(server, Path(directory), ModelConfig(provider="none", model="none"), None)
        try:
            service.on_initialize({"clientInfo": {"name": "probe", "version": "1.0"},
                                   "protocolVersion": "0.2.0"})
            service.on_initialized(None)
            root = service.sessions.root
            clean = service.on_config_read({})
            if _report(clean) != (0, []):
                raise ValueError(f"没有损坏日志时内核应报告 0 与空列表，实际 {_report(clean)!r}")
            checked += 1
            for thread_id in few:
                (root / f"{thread_id}.jsonl").write_bytes(DAMAGED_LOG)
            few_response = service.on_config_read({})
            if _report(few_response) != (len(few), few):
                raise ValueError(f"少量损坏日志应逐个按字典序列出，实际 {_report(few_response)!r}")
            checked += 1
            for thread_id in ids:
                (root / f"{thread_id}.jsonl").write_bytes(DAMAGED_LOG)
            many = service.on_config_read({})
            if many.get("unreadableThreadCount") != total:
                raise ValueError(
                    f"内核计数应完整为 {total}，不随 id 截断，实际 {many.get('unreadableThreadCount')!r}")
            checked += 1
            if many.get("unreadableThreadIds") != ids[:cap]:
                raise ValueError(
                    f"内核 id 应按字典序截断到 {cap} 个，实际 {many.get('unreadableThreadIds')!r}")
            checked += 1
            for name in FOREIGN_NAMES:
                (root / name).write_bytes(DAMAGED_LOG)
            foreign = service.on_config_read({})
            if _report(foreign) != (total, ids[:cap]):
                raise ValueError(f"不符合会话 id 形状的文件名不得计入诊断，实际 {_report(foreign)!r}")
            checked += 1
            (root / f"{ids[0]}.jsonl").unlink()
            removed = service.on_config_read({})
            if _report(removed) != (total - 1, ids[1:cap + 1]):
                raise ValueError(f"删除损坏日志后不得残留在诊断中，实际 {_report(removed)!r}")
            checked += 1
        finally:
            if service._state != "stopped":
                service.close()
    if checked != KERNEL_EXPECTED:
        raise ValueError(f"内核配置读取断言数量不符：{checked}")
    payload = {"clean": clean, "few": few_response, "fewIds": few,
               "many": many, "manyIds": ids[:cap], "total": total}
    return checked, payload


def _check_behaviors() -> int:
    source = _read(HEALTH)
    if "\nimport " in f"\n{source}":
        raise ValueError(f"{HEALTH} 新增了导入，需要更新运行时驱动")
    checked, payload = _kernel_checks()
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "sessionIndexHealth.ts").write_text(source, encoding="utf-8")
        responses = folder / "kernel.json"
        responses.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        harness = folder / "harness.ts"
        harness.write_text(NODE_SCRIPT, encoding="utf-8")
        result = subprocess.run(
            ["node", str(harness), str(responses)], capture_output=True, text=True, timeout=120
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError("会话索引健康行为用例失败：" + detail[:400])
    if f"PASS {NODE_EXPECTED}" not in result.stdout:
        raise ValueError(f"会话索引健康行为用例数量不符：{result.stdout.strip()}")
    return checked + NODE_EXPECTED


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_session_index_health.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_session_index_health.py")
    if "共 42 项结构、37 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_session_index_health.py 检查 42 项结构、37 项行为")
    return 2


def check_session_index_health() -> tuple[int, int]:
    structure = _check_structure(_read(HEALTH))
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_session_index_health()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"会话索引健康核对失败，{error}", file=sys.stderr)
        return 2
    print(f"会话索引健康一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
