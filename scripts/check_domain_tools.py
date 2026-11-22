#!/usr/bin/env python3
"""核对离线指令与默认领域提示的边界。

`tools/commands.py` 决定无模型时哪些只读指令可用、`/search` 如何取词，
以及领域工具缺席时的降级文案；`tools/recruitment.py` 承载默认身份与全部
领域规则。两者都不经模型即可影响工具调用与对外承诺，因此把指令表、
`/search` 的空参数拒绝、候选人查询参数形状与提示词预算固定下来。
脚本另用合成 runner 实际执行离线回复与提示组合。
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = "harness/src/boss_harness/tools/commands.py"
RECRUITMENT = "harness/src/boss_harness/tools/recruitment.py"
sys.path.insert(0, str(ROOT / "harness/src"))

from boss_harness.tools.commands import (  # noqa: E402
    _READ_ONLY_COMMANDS,
    _parse_command,
    offline_reply,
)
from boss_harness.tools.recruitment import (  # noqa: E402
    SYSTEM_INSTRUCTIONS,
    SYSTEM_PREAMBLE,
    SYSTEM_PROMPT,
    compose_system_prompt,
)

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


class _Bridge:
    def __init__(self, available: bool) -> None:
        self._available = available

    def available(self) -> bool:
        return self._available


class _Result:
    def __init__(self, content: str) -> None:
        self.content = content


class _Runner:
    def __init__(self, *, available: bool = True, content: str = "结果正文") -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.tool_bridge = _Bridge(available)
        self.content = content

    def execute_tool(self, thread_id: str, tool_name: str, arguments: dict) -> _Result:
        self.calls.append((thread_id, tool_name, dict(arguments)))
        return _Result(self.content)


def _expect_value(actual, expected, label: str) -> int:
    if actual != expected:
        raise ValueError(f"离线指令与领域提示行为变化 {label}：期望 {expected!r}，实际 {actual!r}")
    return 1


def _expect_error(call, message: str, label: str) -> int:
    try:
        call()
    except ValueError as error:
        if str(error) != message:
            raise ValueError(
                f"离线指令与领域提示行为变化 {label}：期望 {message!r}，实际 "
                f"{str(error)!r}") from None
        return 1
    except Exception as error:
        raise ValueError(
            f"离线指令与领域提示行为变化 {label}：期望 ValueError，实际 "
            f"{type(error).__name__}") from None
    raise ValueError(f"离线指令与领域提示行为变化 {label}：未抛出错误")


def _behavior_checks() -> int:
    checked = 0
    checked += _expect_value(_parse_command(""), ("", ""), "空指令")
    checked += _expect_value(_parse_command("   "), ("", ""), "纯空白指令")
    checked += _expect_value(_parse_command("/tools"), ("/tools", ""), "无参数指令")
    checked += _expect_value(_parse_command("/candidates Python 后端"),
                             ("/candidates", "Python 后端"), "带参指令")
    checked += _expect_value(_parse_command("/search   关键词  "),
                             ("/search", "关键词"), "多空白参数")

    search_empty = "请提供检索关键词，例如 `/search Python`。未发出检索，也不会使用默认关键词。"
    runner = _Runner()
    checked += _expect_value(offline_reply(runner, "thread-1", "/search"),
                             search_empty, "/search 空参数提示")
    checked += _expect_value(runner.calls, [], "/search 空参数不调用工具")
    checked += _expect_value(offline_reply(runner, "thread-1", "  /search    "),
                             search_empty, "/search 空白参数提示")
    checked += _expect_value(runner.calls, [], "/search 空白参数不调用工具")

    reply = offline_reply(runner, "thread-1", "/search Python 后端")
    checked += _expect_value(runner.calls,
                             [("thread-1", "boss_search", {"keyword": "Python 后端"})],
                             "/search 透传关键词")
    checked += _expect_value(reply, "检索「Python 后端」：\n结果正文", "/search 回复")

    runner = _Runner(available=False)
    offline_reply(runner, "thread-1", "/search 关键词")
    checked += _expect_value(len(runner.calls), 1, "/search 不依赖桥接可用性")

    for command, (tool_name, title) in _READ_ONLY_COMMANDS.items():
        runner = _Runner(content=f"{command}-正文")
        reply = offline_reply(runner, "thread-2", command)
        checked += _expect_value(runner.calls, [("thread-2", tool_name, {})],
                                 f"{command} 映射")
        checked += _expect_value(reply, f"{title}：\n{command}-正文", f"{command} 标题")

    runner = _Runner()
    offline_reply(runner, "thread-1", "/candidates Python 后端")
    checked += _expect_value(runner.calls,
                             [("thread-1", "boss_hr_candidates", {"query": "Python 后端"})],
                             "/candidates 查询参数")
    runner = _Runner()
    offline_reply(runner, "thread-1", "/candidates   ")
    checked += _expect_value(runner.calls, [("thread-1", "boss_hr_candidates", {})],
                             "/candidates 空参数")

    runner = _Runner()
    checked += _expect_value(
        offline_reply(runner, "thread-1", "你好"),
        "当前未配置模型。可以使用 /tools、/status、/stats 等只读指令，或配置模型后继续任务。",
        "未配置模型提示")
    checked += _expect_value(runner.calls, [], "未知指令不调用工具")
    runner = _Runner(available=False)
    checked += _expect_value(
        offline_reply(runner, "thread-1", "你好"),
        "内核已连通，但未找到可用的 boss 可执行文件，领域工具暂不可用。",
        "桥接不可用提示")
    checked += _expect_value(runner.calls, [], "桥接不可用不调用工具")
    runner = _Runner()
    checked += _expect_value(
        offline_reply(runner, "thread-1", "/TOOLS"),
        "当前未配置模型。可以使用 /tools、/status、/stats 等只读指令，或配置模型后继续任务。",
        "命令大小写敏感")

    checked += _expect_value(len(_READ_ONLY_COMMANDS), 7, "只读指令数量")
    checked += _expect_value("/search" in _READ_ONLY_COMMANDS, False,
                             "只读表不含 /search")
    checked += _expect_value(
        any(tool == "boss_hr_greet" for tool, _ in _READ_ONLY_COMMANDS.values()), False,
        "只读表不含写工具")

    checked += _expect_value(compose_system_prompt(), SYSTEM_PROMPT, "默认提示")
    checked += _expect_value(SYSTEM_PROMPT.startswith(SYSTEM_PREAMBLE), True,
                             "默认提示首段")
    custom = compose_system_prompt("  自定义身份  ")
    checked += _expect_value(custom.startswith("自定义身份\n\n"), True, "自定义身份裁剪")
    checked += _expect_value(SYSTEM_INSTRUCTIONS in custom, True, "自定义仍保留领域规则")
    checked += _expect_value(SYSTEM_PREAMBLE in custom, False, "自定义替换默认身份")
    checked += _expect_value(
        "boss_hr_greet：向指定推荐牛人发起首次打招呼（敏感写操作，需操作者明确批准）" in custom,
        True, "写操作审批规则保留")

    message = "prompt_preamble 必须是非空且不超过 16 KiB 的文本"
    error_cases = (
        ("空串", ""),
        ("全空白", "   "),
        ("非字符串", 123),
        ("ASCII 超限", "a" * (16 * 1024 + 1)),
        ("UTF-8 超限", "你" * 5462),
        ("控制字符", "身份\x00"),
    )
    for label, value in error_cases:
        checked += _expect_error(lambda: compose_system_prompt(value), message, label)
    checked += _expect_value(compose_system_prompt("a" * (16 * 1024)).startswith("a" * 16),
                             True, "ASCII 预算边界允许")
    checked += _expect_value(compose_system_prompt("你" * 5461).startswith("你" * 5461),
                             True, "UTF-8 预算边界允许")
    checked += _expect_value(compose_system_prompt("身份\t\n\r").startswith("身份"), True,
                             "允许制表与换行")
    return checked


def main() -> int:
    try:
        checked = check_domain_tools()
        scenarios = _behavior_checks()
    except ValueError as error:
        print(f"离线指令与领域提示核对失败，{error}", file=sys.stderr)
        return 2
    print(f"离线指令与领域提示一致：{checked} 项只读指令、检索与提示预算防护、"
          f"{scenarios} 个行为场景")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
