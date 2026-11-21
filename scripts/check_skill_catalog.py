#!/usr/bin/env python3
"""核对技能目录枚举的有界窗口与截断标记。

`SkillCatalog.scan` 通过 `_candidate_paths` 做有界目录枚举：根为符号链接时
拒绝，缺失按空目录处理，非目录与扫描失败如实报错；只保留字典序更小的候选，
第二项 `dropped` 区分「恰好顶到窗口」与「确有目录未检查」。`scan` 对代理项
目录名转 repr、对超长 id 截断后归入问题清单，`_read_bounded` 失败时给出
`_problem_reason`；有效技能与问题清单各自封顶，并以 `skillsTruncated` /
`problemsTruncated` / `candidatesTruncated` 如实说明截断。窗口按需翻倍且
不超过 `MAX_SKILL_SCAN_ENTRIES`。`list()` 只投影扫描结果。这里按源码顺序
固定这些边界。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = "harness/src/boss_harness/resources.py"

CANDIDATE_ORDER = (
    "def _candidate_paths(self, limit: int = MAX_SKILL_DESCRIPTORS) -> tuple[list[tuple[str, Path]], bool]:",
    "if self._root_is_symlink:",
    'raise ValueError("技能目录不能是符号链接；请改为工作区内的普通目录")',
    "observed = os.stat(self.root)",
    "except FileNotFoundError:",
    "return [], False",
    "except OSError:",
    'raise ValueError("无法读取技能目录；请检查目录权限后重试") from None',
    "if not stat.S_ISDIR(observed.st_mode):",
    'raise ValueError("技能目录不是普通目录")',
    "candidates: list[tuple[str, Path]] = []",
    "dropped = False",
    "entries = os.scandir(self.root)",
    "except FileNotFoundError:",
    "return [], False",
    "except OSError:",
    'raise ValueError("无法读取技能目录；请检查目录权限后重试") from None',
    "with entries:",
    "for entry in entries:",
    "if not entry.is_dir(follow_symlinks=False):",
    "except (OSError, RuntimeError):",
    'path = self.root / entry.name / "SKILL.md"',
    "candidate = (entry.name, path)",
    "if len(candidates) < limit:",
    "candidates.append(candidate)",
    "dropped = True",
    "largest = max(range(len(candidates)), key=lambda index: candidates[index][0])",
    "if entry.name < candidates[largest][0]:",
    "candidates[largest] = candidate",
    "return sorted(candidates, key=lambda candidate: candidate[0]), dropped",
)
SCAN_ORDER = (
    "def scan(self) -> dict:",
    "limit = self.MAX_SKILL_DESCRIPTORS",
    "while True:",
    "skills: list[dict] = []",
    "problems: list[dict] = []",
    "skills_dropped = False",
    "candidates, dropped = self._candidate_paths(limit)",
    "for skill_id, path in candidates:",
    'skill_id.encode("utf-8")',
    "except UnicodeEncodeError:",
    '"id": repr(skill_id)[:200],',
    '"reason": "目录名不是有效的 UTF-8，无法通过协议读取"})',
    "if len(skill_id) > self.MAX_EXISTING_SKILL_ID:",
    'problems.append({"id": skill_id[:self.MAX_EXISTING_SKILL_ID],',
    '"reason": f"目录名超过 {self.MAX_EXISTING_SKILL_ID} 个字符，无法按技能读取"})',
    "loaded = self._read_bounded(path)",
    "if loaded is None:",
    'problems.append({"id": skill_id, "reason": self._problem_reason(path)})',
    "source, byte_length, digest = loaded",
    "fields = self._fields(source)",
    "if len(skills) < self.MAX_SKILL_DESCRIPTORS:",
    "skills.append(self._descriptor(skill_id, fields, digest, byte_length))",
    "else:",
    "skills_dropped = True",
    "exhausted = not dropped",
    "fulfilled = (len(skills) >= self.MAX_SKILL_DESCRIPTORS",
    "and len(problems) >= self.MAX_SKILL_DESCRIPTORS)",
    "if exhausted or fulfilled or limit >= self.MAX_SKILL_SCAN_ENTRIES:",
    'return {"skills": skills, "problems": problems[:self.MAX_SKILL_DESCRIPTORS],',
    '**({"problemsTruncated": True}',
    "if len(problems) > self.MAX_SKILL_DESCRIPTORS else {}),",
    '**({"skillsTruncated": True} if skills_dropped else {}),',
    '**({} if exhausted else {"candidatesTruncated": True})}',
    "limit = min(limit * 2, self.MAX_SKILL_SCAN_ENTRIES)",
)
REASON_ORDER = (
    "def _problem_reason(cls, path: Path) -> str:",
    "observed = os.lstat(path)",
    "except FileNotFoundError:",
    'return "缺少 SKILL.md 文件"',
    "except OSError:",
    'return "无法读取 SKILL.md"',
    "if not stat.S_ISREG(observed.st_mode):",
    'return "SKILL.md 不是普通文件（可能是符号链接或目录）"',
    "if observed.st_size > cls.MAX_SKILL_BYTES:",
    'return f"SKILL.md 超过 {cls.MAX_SKILL_BYTES} 字节"',
    'with open(path, "rb") as handle:',
    "data = handle.read(cls.MAX_SKILL_BYTES + 1)",
    "except OSError:",
    'return "无法读取 SKILL.md"',
    "if len(data) > cls.MAX_SKILL_BYTES:",
    'return f"SKILL.md 超过 {cls.MAX_SKILL_BYTES} 字节"',
    'data.decode("utf-8")',
    "except UnicodeDecodeError:",
    'return "SKILL.md 不是有效的 UTF-8 文本"',
    'return "SKILL.md 不可读取"',
)
LIST_ORDER = (
    "def list(self) -> list[dict]:",
    'return self.scan()["skills"]',
)


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except OSError:
        raise ValueError(f"无法读取 {relative}") from None


def _method(tree: ast.Module, source: str, name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SkillCatalog":
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    segment = ast.get_source_segment(source, child)
                    if segment is not None:
                        return segment
    raise ValueError(f"缺少方法 SkillCatalog.{name}")


def _ordered(fragments: tuple[str, ...], text: str, label: str) -> int:
    position = -1
    for fragment in fragments:
        index = text.find(fragment, position + 1)
        if index < 0:
            raise ValueError(f"{label} 缺少或顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_skill_catalog() -> int:
    source = _read(RESOURCES)
    tree = ast.parse(source)
    candidates = _method(tree, source, "_candidate_paths")
    scan = _method(tree, source, "scan")
    reason = _method(tree, source, "_problem_reason")
    listing = _method(tree, source, "list")
    checked = _ordered(CANDIDATE_ORDER, candidates, RESOURCES)
    checked += _ordered(SCAN_ORDER, scan, RESOURCES)
    checked += _ordered(REASON_ORDER, reason, RESOURCES)
    checked += _ordered(LIST_ORDER, listing, RESOURCES)
    # 候选窗口：根符号链接拒绝、两次缺失早退、只保留字典序更小的 id。
    if candidates.count("if self._root_is_symlink:") != 1:
        raise ValueError(f"{RESOURCES} 的候选枚举必须拒绝符号链接根")
    checked += 1
    if candidates.count("return [], False") != 2:
        raise ValueError(f"{RESOURCES} 的候选枚举必须有两处缺失早退")
    checked += 1
    if candidates.count("if not entry.is_dir(follow_symlinks=False):") != 1:
        raise ValueError(f"{RESOURCES} 的候选枚举不得跟随符号链接目录")
    checked += 1
    if candidates.count("dropped = True") != 1:
        raise ValueError(f"{RESOURCES} 的候选枚举必须记录丢弃")
    checked += 1
    if candidates.count("if entry.name < candidates[largest][0]:") != 1:
        raise ValueError(f"{RESOURCES} 的候选窗口必须只在更小 id 时替换")
    checked += 1
    if candidates.count("return sorted(candidates, key=lambda candidate: candidate[0]), dropped") != 1:
        raise ValueError(f"{RESOURCES} 的候选枚举必须按 id 排序并返回丢弃标记")
    checked += 1
    # 扫描：截断标记只在各自条件出现，窗口严格翻倍且不超总上限。
    if scan.count("exhausted = not dropped") != 1:
        raise ValueError(f"{RESOURCES} 的扫描必须以丢弃标记判定是否枚举完毕")
    checked += 1
    if scan.count("len(problems) > self.MAX_SKILL_DESCRIPTORS") != 1:
        raise ValueError(f"{RESOURCES} 的问题截断必须严格大于清单上限")
    checked += 1
    if scan.count('**({"problemsTruncated": True}') != 1:
        raise ValueError(f"{RESOURCES} 的问题截断标记必须唯一")
    checked += 1
    if scan.count('**({"skillsTruncated": True} if skills_dropped else {})') != 1:
        raise ValueError(f"{RESOURCES} 的技能截断标记必须由丢弃状态决定")
    checked += 1
    if scan.count('**({} if exhausted else {"candidatesTruncated": True})') != 1:
        raise ValueError(f"{RESOURCES} 的候选截断标记必须由枚举完毕状态决定")
    checked += 1
    if scan.count("limit = min(limit * 2, self.MAX_SKILL_SCAN_ENTRIES)") != 1:
        raise ValueError(f"{RESOURCES} 的扫描窗口必须翻倍且不超过总上限")
    checked += 1
    if scan.count("if exhausted or fulfilled or limit >= self.MAX_SKILL_SCAN_ENTRIES:") != 1:
        raise ValueError(f"{RESOURCES} 的扫描必须有三种终止条件")
    checked += 1
    # 问题清单：代理项转 repr、超长 id 截断、读取失败归类。
    if scan.count("repr(skill_id)[:200]") != 1:
        raise ValueError(f"{RESOURCES} 的代理项 id 必须以 repr 截断展示")
    checked += 1
    if scan.count("skill_id[:self.MAX_EXISTING_SKILL_ID]") != 1:
        raise ValueError(f"{RESOURCES} 的超长 id 必须截断后进入问题清单")
    checked += 1
    if scan.count("self._problem_reason(path)") != 1:
        raise ValueError(f"{RESOURCES} 的读取失败必须归类原因")
    checked += 1
    if scan.count("self._descriptor(skill_id, fields, digest, byte_length)") != 1:
        raise ValueError(f"{RESOURCES} 的有效技能必须经描述投影")
    checked += 1
    if scan.count("problems[:self.MAX_SKILL_DESCRIPTORS]") != 1:
        raise ValueError(f"{RESOURCES} 的问题清单必须截断到上限")
    checked += 1
    # 原因归类：覆盖缺失、不可读、非普通文件、两次超限、非 UTF-8 与兜底。
    if reason.count('return "缺少 SKILL.md 文件"') != 1:
        raise ValueError(f"{RESOURCES} 的原因必须区分文件缺失")
    checked += 1
    if reason.count('return "无法读取 SKILL.md"') != 2:
        raise ValueError(f"{RESOURCES} 的原因必须有两处不可读归类")
    checked += 1
    if reason.count('return f"SKILL.md 超过 {cls.MAX_SKILL_BYTES} 字节"') != 2:
        raise ValueError(f"{RESOURCES} 的原因必须有两处超限归类")
    checked += 1
    if reason.count('return "SKILL.md 不是有效的 UTF-8 文本"') != 1:
        raise ValueError(f"{RESOURCES} 的原因必须区分非法文本")
    checked += 1
    if reason.count('return "SKILL.md 不可读取"') != 1:
        raise ValueError(f"{RESOURCES} 的原因必须有兜底")
    checked += 1
    # 列表只投影扫描结果，不重复枚举。
    if listing.count('return self.scan()["skills"]') != 1:
        raise ValueError(f"{RESOURCES} 的技能列表必须只投影扫描结果")
    checked += 1
    return checked


def main() -> int:
    try:
        checked = check_skill_catalog()
    except (ValueError, SyntaxError) as error:
        print(f"技能目录枚举核对失败，{error}", file=sys.stderr)
        return 2
    print(f"技能目录枚举一致：{checked} 项窗口、截断与原因校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
