#!/usr/bin/env python3
"""核对离线指令与默认领域提示的边界。

`tools/commands.py` 决定无模型时哪些只读指令可用、`/search` 如何取词，
以及领域工具缺席时的降级文案；`tools/recruitment.py` 承载默认身份与全部
领域规则。两者都不经模型即可影响工具调用与对外承诺，因此把指令表、
`/search` 的空参数拒绝、候选人查询参数形状与提示词预算固定下来。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = "harness/src/boss_harness/tools/commands.py"
RECRUITMENT = "harness/src/boss_harness/tools/recruitment.py"

COMMAND_FRAGMENTS = (
    '_READ_ONLY_COMMANDS: dict[str, tuple[str, str]] = {',
    '"/tools": ("boss_list_tools", "上游能力目录"),',
    '"/status": ("boss_status", "账号与连接健康度"),',
    '"/stats": ("boss_stats", "招聘与转化漏斗"),',
    '"/recommend": ("boss_recommend", "职位推荐"),',
    '"/jobs": ("boss_hr_jobs", "已发布职位"),',
    '"/chat": ("boss_hr_chat", "沟通消息"),',
    '"/candidates": ("boss_hr_candidates", "候选人搜索"),',
    "def _parse_command(stripped: str) -> tuple[str, str]:",
    "parts = stripped.split(maxsplit=1)",
    'if not parts:\n        return "", ""',
    'return parts[0], parts[1].strip() if len(parts) > 1 else ""',
    "def offline_reply(runner: Any, thread_id: str, text: str) -> str:",
    'command, argument = _parse_command(text.strip())',
    'entry = _READ_ONLY_COMMANDS.get(command)',
    "tool_name, title = entry",
    'arguments: dict[str, Any] = {"query": argument} if command == "/candidates" and argument else {}',
    "result = runner.execute_tool(thread_id, tool_name, arguments)",
    'return f"{title}：\\n{result.content}"',
    "if not runner.tool_bridge.available():",
    'return "内核已连通，但未找到可用的 boss 可执行文件，领域工具暂不可用。"',
    'return "当前未配置模型。可以使用 /tools、/status、/stats 等只读指令，或配置模型后继续任务。"',
)
SEARCH_ORDER = (
    'if command == "/search":',
    "if not argument:",
    'return "请提供检索关键词，例如 `/search Python`。未发出检索，也不会使用默认关键词。"',
    'result = runner.execute_tool(thread_id, "boss_search", {"keyword": argument})',
)
RECRUITMENT_FRAGMENTS = (
    'SYSTEM_PREAMBLE = "你是 BOSS Agent，一个面向招聘任务的垂直领域智能体内核（Harness）。"',
    'SYSTEM_PROMPT = f"{SYSTEM_PREAMBLE}\\n\\n{SYSTEM_INSTRUCTIONS}"',
    "def compose_system_prompt(preamble: str | None = None) -> str:",
    "if preamble is None:\n        return SYSTEM_PROMPT",
    "if (not isinstance(preamble, str) or not preamble.strip()",
    'or len(preamble.encode("utf-8")) > 16 * 1024',
    'or any(ord(char) < 32 and char not in "\\n\\r\\t" for char in preamble)):',
    'raise ValueError("prompt_preamble 必须是非空且不超过 16 KiB 的文本")',
    'return f"{preamble.strip()}\\n\\n{SYSTEM_INSTRUCTIONS}"',
    "boss_search：按关键词、page 页码及 city、salary 单选标签",
    "boss_hr_chat：查看与候选人的沟通列表及未读消息摘要（只读）",
    "boss_hr_greet：向指定推荐牛人发起首次打招呼（敏感写操作，需操作者明确批准）",
    "必须由系统门禁闸门获取用户批准后方可执行",
    "不自动重试或探测",
    "不得从空列表推断已查完，不得把单页结果称为全部结果",
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
        index = text.find(fragment)
        if index < 0 or index <= position:
            raise ValueError(f"{label} 缺少或首次出现顺序变化：{fragment}")
        position = index
    return len(fragments)


def check_domain_tools() -> int:
    commands = _read(COMMANDS)
    recruitment = _read(RECRUITMENT)
    checked = _expect(COMMAND_FRAGMENTS, commands, COMMANDS)
    # `/search` 必须先拒绝空参数再调用业务 CLI，避免默认关键词发起检索。
    checked += _ordered(SEARCH_ORDER, commands, COMMANDS)
    checked += _expect(RECRUITMENT_FRAGMENTS, recruitment, RECRUITMENT)
    # 反向断言：只读指令表不得收编写工具或把 /search 做成表项。
    if '"/search": (' in commands:
        raise ValueError(f"{COMMANDS} 的 /search 必须保留独立空参数分支")
    if "boss_hr_greet" in commands or "boss_greet" in commands:
        raise ValueError(f"{COMMANDS} 的离线指令不得包含写工具")
    if '{"keyword": argument}' not in commands:
        raise ValueError(f"{COMMANDS} 的检索关键词必须来自用户参数")
    if 'or "Python"' in commands or "or 'Python'" in commands:
        raise ValueError(f"{COMMANDS} 不得为 /search 提供默认关键词")
    # 反向断言：提示词预算按 UTF-8 字节计算，且不得跳过控制字符过滤。
    if "len(preamble) > 16 * 1024" in recruitment:
        raise ValueError(f"{RECRUITMENT} 的 preamble 预算必须按 UTF-8 字节计算")
    if 'ord(char) < 32' not in recruitment:
        raise ValueError(f"{RECRUITMENT} 的 preamble 必须拒绝控制字符")
    if "def compose_system_prompt(" not in recruitment or "SYSTEM_INSTRUCTIONS" not in recruitment:
        raise ValueError(f"{RECRUITMENT} 必须只替换身份并保留领域规则")
    return checked + 1


def main() -> int:
    try:
        checked = check_domain_tools()
    except ValueError as error:
        print(f"离线指令与领域提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"离线指令与领域提示一致：{checked} 项只读指令、检索与提示预算防护")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
